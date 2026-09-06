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

    password = args.password
    if not password:
        password = getpass.getpass("Enter FTP password for 'vedavmsi': ")

    server = "103.69.196.157"
    user = "vedavmsi"
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_file = os.path.join(repo_dir, "index.html")
    donations_file = os.path.join(repo_dir, "Donations.html")

    for path in [index_file, donations_file]:
        if not os.path.isfile(path):
            print(f"❌ Error: {path} not found")
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

        print(f"Uploading index.html ({os.path.getsize(index_file):,} bytes)... ", end="", flush=True)
        with open(index_file, "rb") as f:
            ftp.storbinary("STOR index.html", f)
        print("✓ Done!")

        print(f"Uploading Donations.html ({os.path.getsize(donations_file):,} bytes)... ", end="", flush=True)
        with open(donations_file, "rb") as f:
            ftp.storbinary("STOR Donations.html", f)
        print("✓ Done!")

        print("\nCleaning up unused redesign files from /httpdocs...")
        for unwanted in ["documents.html", "articles.html", "videos.html", "about.html"]:
            try:
                ftp.delete(unwanted)
                print(f"  ✓ Deleted {unwanted}")
            except Exception as ex:
                print(f"  - {unwanted}: {ex}")

        print("\n" + "=" * 60)
        print("🎉 ALL ACTIONS COMPLETED SUCCESSFULLY!")
        print("✓ Donations.html restored to legacy version.")
        print("✓ Redesign files removed from vedavms.in.")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        try:
            ftp.quit()
        except:
            pass

if __name__ == "__main__":
    main()
