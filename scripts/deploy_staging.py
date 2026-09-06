#!/usr/bin/env python3
"""
Deploy build/ artifacts directly to staging (new.vedavms.in at /new.vedavms.in) via FTPS.
"""

import os
import sys
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
    parser = argparse.ArgumentParser(description="Deploy to new.vedavms.in")
    parser.add_argument("--password", default=None, help="FTP Password")
    parser.add_argument("--server", default="103.69.196.157", help="FTP Host")
    parser.add_argument("--user", default="vedavmsi", help="FTP Username")
    parser.add_argument("--dir", default="/new.vedavms.in", help="Staging remote directory")
    args = parser.parse_args()

    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    password = args.password
    if not password:
        env_pass = os.environ.get("STAGING_FTP_PASSWORD") or os.environ.get("FTP_PASSWORD")
        env_file = os.path.join(repo_dir, ".env")
        if not env_pass and os.path.isfile(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if "=" in line and not line.strip().startswith("#"):
                            k, v = line.strip().split("=", 1)
                            if k.strip() in ("STAGING_FTP_PASSWORD", "FTP_PASSWORD"):
                                env_pass = v.strip().strip("'\"")
                                break
            except Exception:
                pass
        password = env_pass or getpass.getpass(f"Enter FTP password for '{args.user}': ")

    build_dir = os.path.join(repo_dir, "build")

    if not os.path.isdir(build_dir):
        print(f"❌ Error: build directory not found at {build_dir}")
        sys.exit(1)

    files_to_upload = [f for f in os.listdir(build_dir) if os.path.isfile(os.path.join(build_dir, f))]
    if not files_to_upload:
        print(f"❌ Error: No files found in {build_dir}")
        sys.exit(1)

    print(f"\nTargeting Staging: {args.server} -> {args.dir}")
    print(f"Files to deploy ({len(files_to_upload)}): {', '.join(files_to_upload)}")

    print(f"\nConnecting to {args.server} via FTPS...")
    ftp = ReusedSessionFTP_TLS()
    try:
        ftp.connect(args.server, 21, timeout=20)
        ftp.login(args.user, password)
        ftp.prot_p()
        print("✓ Connected & Authenticated successfully!")

        print(f"Switching to remote directory '{args.dir}'...")
        try:
            ftp.cwd(args.dir)
        except Exception as e:
            print(f"❌ Could not cwd to '{args.dir}': {e}")
            print("Listing root directory '/' to verify available folders:")
            ftp.cwd("/")
            ftp.retrlines("LIST")
            sys.exit(1)

        print(f"✓ Current remote directory: {ftp.pwd()}")

        print("\n--- Uploading build files to new.vedavms.in ---")
        for filename in sorted(files_to_upload):
            filepath = os.path.join(build_dir, filename)
            filesize = os.path.getsize(filepath)
            print(f"  Uploading {filename:<20} ({filesize:>8,} bytes)... ", end="", flush=True)
            with open(filepath, "rb") as f:
                ftp.storbinary(f"STOR {filename}", f)
            print("✓ Done")

        print("\n🎉 Deployment to new.vedavms.in completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during deployment: {e}")
        sys.exit(1)
    finally:
        try:
            ftp.quit()
        except Exception:
            pass

if __name__ == "__main__":
    main()
