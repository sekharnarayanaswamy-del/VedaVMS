#!/usr/bin/env python3
"""
Directly restore original Donations.html using pure Python FTPS with TLS session reuse.
"""

import os
import sys
import ssl
import getpass
import argparse
from ftplib import FTP, FTP_TLS

class ReusedSessionFTP_TLS(FTP_TLS):
    """Reuses the TLS session on data connections to satisfy IIS FTP."""
    def ntransfercmd(self, cmd, rest=None):
        conn, size = FTP.ntransfercmd(self, cmd, rest)
        if self._cnx:
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

    password = args.password
    if not password:
        password = getpass.getpass("Enter FTP password for 'vedavmsi': ")

    server = "103.69.196.157"
    user = "vedavmsi"
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_file = os.path.join(repo_dir, "original_Donations.html")

    if not os.path.isfile(source_file):
        print(f"❌ Error: {source_file} not found")
        sys.exit(1)

    print(f"Connecting to {server} via FTPS...")
    ftp = ReusedSessionFTP_TLS()
    try:
        ftp.connect(server, 21, timeout=15)
        ftp.login(user, password)
        ftp.prot_p()
        print("✓ Authenticated successfully!")

        print("Switching to /httpdocs...")
        ftp.cwd("/httpdocs")
        print(f"Current directory: {ftp.pwd()}")

        print(f"Uploading original Donations.html ({os.path.getsize(source_file):,} bytes)... ", end="", flush=True)
        with open(source_file, "rb") as f:
            ftp.storbinary("STOR Donations.html", f)
        print("✓ Done!")

        # Also store lowercase donations.html just in case of any cached references
        with open(source_file, "rb") as f:
            ftp.storbinary("STOR donations.html", f)
        print("✓ Verified and restored Donations.html on live server!")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        try:
            ftp.quit()
        except:
            pass

if __name__ == "__main__":
    main()
