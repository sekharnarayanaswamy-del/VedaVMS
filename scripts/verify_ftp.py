#!/usr/bin/env python3
"""
Standalone FTP / FTPS Connection and Diagnostic Tool for VedaVMS.
Tests connectivity, authentication, SSL/TLS negotiation, directory listing,
and optional file deployment.
"""

import os
import sys
import ssl
import getpass
from ftplib import FTP, FTP_TLS, error_perm

class ReusedSessionFTP_TLS(FTP_TLS):
    """Subclass of FTP_TLS that reuses the TLS session on data connections.
    Required by Windows IIS FTP servers to prevent data connection timeouts.
    """
    def ntransfercmd(self, cmd, rest=None):
        conn, size = FTP.ntransfercmd(self, cmd, rest)
        if getattr(self, '_prot_p', False) and hasattr(self.sock, 'session'):
            conn = self.context.wrap_socket(
                conn,
                server_hostname=self.host,
                session=self.sock.session
            )
        return conn, size

def test_ftp():
    print("=" * 60)
    print(" VedaVMS FTP / FTPS Diagnostic & Deployment Utility")
    print("=" * 60)

    import argparse
    parser = argparse.ArgumentParser(description="VedaVMS FTP Verification Tool")
    parser.add_argument("--server", default=None, help="FTP Server host")
    parser.add_argument("--port", type=int, default=21, help="FTP Port")
    parser.add_argument("--user", default=None, help="FTP Username")
    parser.add_argument("--password", default=None, help="FTP Password")
    parser.add_argument("--dir", default=None, help="Remote Directory")
    parser.add_argument("--deploy", action="store_true", help="Automatically upload build/ files if test passes")
    args = parser.parse_args()

    server = args.server or input("FTP Server [default: 103.69.196.157]: ").strip() or "103.69.196.157"
    port = args.port
    user = args.user or input("FTP Username: ").strip()
    if not user:
        print("Username is required.")
        return

    if args.password:
        password = args.password
    else:
        print("Note: Password characters are intentionally hidden while typing/pasting.")
        try:
            password = getpass.getpass("FTP Password: ")
        except Exception:
            password = input("FTP Password (visible): ")

    remote_dir = args.dir or input("Remote Directory [default: /httpdocs]: ").strip() or "/httpdocs"

    print("\n--- Step 1: Testing Connection & Protocol ---")
    ftp = None
    protocol_used = None

    # Try FTPS (FTP over explicit TLS) first
    try:
        print(f"Connecting to {server}:{port} via FTPS (FTP_TLS)...")
        ftp_tls = ReusedSessionFTP_TLS()
        ftp_tls.connect(server, port, timeout=15)
        ftp_tls.login(user, password)
        ftp_tls.prot_p()  # Switch data connection to TLS
        print(" Connected and authenticated successfully via FTPS (secure TLS)!")
        ftp = ftp_tls
        protocol_used = "FTPS"
    except Exception as e_tls:
        print(f" FTPS attempt info: {e_tls}")
        print("Trying standard plain FTP...")
        try:
            ftp_plain = FTP()
            ftp_plain.connect(server, port, timeout=15)
            ftp_plain.login(user, password)
            print(" Connected and authenticated successfully via Plain FTP!")
            ftp = ftp_plain
            protocol_used = "FTP"
        except Exception as e_plain:
            print(f"❌ Plain FTP failed: {e_plain}")
            print("\nTroubleshooting Tips:")
            print("1. Check username/password.")
            print("2. In Plesk, try username with domain: e.g., 'username@new.vedavms.in'.")
            print("3. Check if server firewall permits port 21 and passive port range.")
            return

    try:
        print(f"\n--- Step 2: Checking Working Directory ---")
        current_pwd = ftp.pwd()
        print(f"Current initial directory: {current_pwd}")

        print(f"Attempting to switch to target directory: '{remote_dir}'...")
        try:
            ftp.cwd(remote_dir)
            print(f" Successfully navigated to: {ftp.pwd()}")
        except error_perm as e:
            print(f"⚠️ Could not CWD to '{remote_dir}': {e}")
            print(f"  Note: If your Plesk FTP user home directory is already configured to 'httpdocs',")
            print(f"  the target directory should be '/' rather than '/httpdocs'.")
            use_root = input("  Would you like to test with '/' (root)? [Y/n]: ").strip().lower()
            if use_root != "n":
                ftp.cwd("/")
                print(f"  Current directory is now: {ftp.pwd()}")

        print("\n--- Step 3: Directory Contents (First 15 items) ---")
        items = []
        ftp.retrlines("LIST", items.append)
        for line in items[:15]:
            print(" ", line)
        if len(items) > 15:
            print(f"  ... and {len(items) - 15} more files.")

        print("\n--- Step 4: Write Permission Test ---")
        test_filename = "vedavms_connection_test.tmp"
        from io import BytesIO
        ftp.storbinary(f"STOR {test_filename}", BytesIO(b"VedaVMS FTP Test Successful"))
        print(f" Created test file: {test_filename}")
        ftp.delete(test_filename)
        print(f" Cleaned up test file: {test_filename}")

        print("\n" + "=" * 60)
        print(" ALL CHECKS PASSED!")
        print(f"Protocol: {protocol_used}")
        print(f"Working Directory: {ftp.pwd()}")
        print("=" * 60)

        if args.deploy:
            deploy_now = "y"
        else:
            deploy_now = input("\nWould you like to upload all files from local 'build/' to the server right now? [y/N]: ").strip().lower()
        if deploy_now == "y":
            build_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build")
            if not os.path.exists(build_dir):
                print(f"Build directory not found at: {build_dir}")
                return
            print(f"\nUploading files from {build_dir} to {ftp.pwd()}...")
            for fname in os.listdir(build_dir):
                fpath = os.path.join(build_dir, fname)
                if os.path.isfile(fpath):
                    size = os.path.getsize(fpath)
                    print(f"  Uploading {fname} ({size:,} bytes)...", end="", flush=True)
                    with open(fpath, "rb") as f:
                        ftp.storbinary(f"STOR {fname}", f)
                    print(" done.")
            print("\n Deployment complete! All files have been uploaded.")

    except Exception as e:
        print(f"\n❌ Error during operations: {e}")
    finally:
        try:
            ftp.quit()
        except:
            pass

if __name__ == "__main__":
    test_ftp()
