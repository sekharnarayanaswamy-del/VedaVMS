#!/usr/bin/env python3
"""
Inspect directory tree via FTPS to locate the document root for new.vedavms.in
"""

import getpass
import argparse
from ftplib import FTP, FTP_TLS

class ReusedSessionFTP_TLS(FTP_TLS):
    def ntransfercmd(self, cmd, rest=None):
        conn, size = FTP.ntransfercmd(self, cmd, rest)
        if getattr(self, '_prot_p', False) and hasattr(self.sock, 'session'):
            conn = self.context.wrap_socket(
                conn,
                server_hostname=self.host,
                session=self.sock.session
            )
        return conn, size

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    password = args.password or getpass.getpass("Enter FTP password for 'vedavmsi': ")
    server = "103.69.196.157"
    user = "vedavmsi"

    ftp = ReusedSessionFTP_TLS()
    ftp.connect(server, 21, timeout=15)
    ftp.login(user, password)
    ftp.prot_p()

    print("\n✓ Logged in successfully!")
    print(f"Current working directory: {ftp.pwd()}")
    
    print("\n--- Listing at root '/' ---")
    ftp.cwd("/")
    entries = []
    ftp.retrlines("LIST", entries.append)
    for e in entries:
        print(" ", e)

    # If there is a subdomains or new folder, let's check
    for item in ["/subdomains", "/new.vedavms.in", "/httpdocs/new", "/httpdocs/subdomains"]:
        try:
            ftp.cwd(item)
            print(f"\n--- Found directory: {item} ---")
            sub_entries = []
            ftp.retrlines("LIST", sub_entries.append)
            for s in sub_entries:
                print("   ", s)
        except Exception:
            pass

if __name__ == "__main__":
    main()
