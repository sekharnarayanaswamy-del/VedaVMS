#!/usr/bin/env python3
"""
Test different Plesk/IIS FTP username format variants.
"""

import sys
import getpass
import argparse
from ftplib import FTP, FTP_TLS

def test_variants():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="103.69.196.157")
    parser.add_argument("--base-user", default=None)
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    server = args.server
    base_user = args.base_user
    if not base_user:
        base_user = input("Enter base username (e.g. vedavmsi): ").strip()
    
    # Strip @domain if user typed it in base_user
    clean_user = base_user.split("@")[0].split("|")[-1]

    password = args.password
    if not password:
        password = getpass.getpass(f"Enter FTP password for {clean_user}: ")

    variants = [
        clean_user,                                 # vedavmsi
        f"{clean_user}@vedavms.in",                 # vedavmsi@vedavms.in
        f"{clean_user}@new.vedavms.in",             # vedavmsi@new.vedavms.in
        f"vedavms.in|{clean_user}",                 # vedavms.in|vedavmsi (IIS pipe syntax)
        f"new.vedavms.in|{clean_user}",             # new.vedavms.in|vedavmsi
        f"103.69.196.157|{clean_user}",             # IP|vedavmsi
        f".\\{clean_user}",                         # .\vedavmsi
    ]

    print(f"\nTesting {len(variants)} username format variants against {server}...\n")

    for u in variants:
        print(f"Testing username: '{u}' ... ", end="", flush=True)
        # Test FTPS
        try:
            ftps = FTP_TLS()
            ftps.connect(server, 21, timeout=5)
            ftps.login(u, password)
            ftps.prot_p()
            print(f" SUCCESS! (via FTPS / TLS)")
            print(f"  Working format: '{u}'")
            print(f"  Initial Directory: {ftps.pwd()}")
            ftps.quit()
            return u, "FTPS"
        except Exception as e1:
            # Test Plain FTP
            try:
                ftp = FTP()
                ftp.connect(server, 21, timeout=5)
                ftp.login(u, password)
                print(f" SUCCESS! (via Plain FTP)")
                print(f"  Working format: '{u}'")
                print(f"  Initial Directory: {ftp.pwd()}")
                ftp.quit()
                return u, "FTP"
            except Exception as e2:
                print(f"Failed ({e2})")

    print("\n❌ None of the username variations succeeded.")
    print("Please verify the password in Plesk (Websites & Domains > FTP Access).")
    return None, None

if __name__ == "__main__":
    test_variants()
