#!/usr/bin/env python3
"""
Python FTP/FTPS Deployer for VedaVMS.
Connects via FTPS/FTP to the remote web server, checks directories, creates target path if missing,
and synchronizes files from the local build folder with full diagnostic logging.
"""

import os
import sys
import ssl
import ftplib
import argparse
from pathlib import Path


class ExplicitFTP_TLS(ftplib.FTP_TLS):
    """Explicit FTPS client with TLS session reuse support for data connections."""
    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(
                conn,
                server_hostname=self.host,
                session=self.sock.session
            )
        return conn, size


def connect_ftp(host, user, passwd, port=21, timeout=30, force_plain=False):
    """Attempt FTPS connection first, fallback to standard FTP if needed."""
    if force_plain:
        print(f"Connecting via standard FTP to {host}:{port} as {user} ...")
        ftp = ftplib.FTP(timeout=timeout)
        ftp.connect(host, port)
        ftp.login(user, passwd)
        ftp.set_pasv(True)
        print("  Connected via standard FTP.")
        return ftp

    print(f"Connecting to FTP server: {host}:{port} as {user} ...")
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        ftp = ExplicitFTP_TLS(context=ctx, timeout=timeout)
        ftp.connect(host, port)
        ftp.login(user, passwd)
        ftp.prot_p()
        ftp.set_pasv(True)
        print("  Connected securely via FTPS (Explicit TLS).")
        return ftp
    except Exception as e:
        print(f"  FTPS connection warning: {e}. Trying standard FTP...")
        ftp = ftplib.FTP(timeout=timeout)
        ftp.connect(host, port)
        ftp.login(user, passwd)
        ftp.set_pasv(True)
        print("  Connected via standard FTP.")
        return ftp


def ensure_remote_dir(ftp, remote_path):
    """Ensure remote path exists by traversing and creating folders recursively."""
    parts = [p for p in remote_path.strip("/").split("/") if p]
    ftp.cwd("/")
    current = ""
    for part in parts:
        current = f"{current}/{part}"
        try:
            ftp.cwd(current)
        except Exception:
            print(f"  Directory '{current}' not found. Attempting to create...")
            try:
                ftp.mkd(current)
                ftp.cwd(current)
                print(f"  Created '{current}' successfully.")
            except Exception as mkd_err:
                print(f"  Notice on mkd('{current}'): {mkd_err}. Trying relative path '{part}'...")
                try:
                    ftp.mkd(part)
                    ftp.cwd(part)
                    print(f"  Created relative '{part}' successfully.")
                except Exception as rel_err:
                    print(f"  Could not create '{current}': {rel_err}")
                    raise


def upload_directory(ftp, local_dir, remote_dir):
    """Upload all files from local_dir to remote_dir."""
    local_path = Path(local_dir)
    if not local_path.exists():
        raise FileNotFoundError(f"Local build directory not found: {local_dir}")

    print(f"\nNavigating to remote directory: {remote_dir}")
    ensure_remote_dir(ftp, remote_dir)

    print("\nRoot directory listing on FTP server:")
    try:
        ftp.cwd("/")
        root_items = []
        ftp.retrlines("LIST", root_items.append)
        for item in root_items[:20]:
            print(f"  {item}")
        if len(root_items) > 20:
            print(f"  ... and {len(root_items) - 20} more items")
    except Exception as list_err:
        print(f"  Could not list root directory: {list_err}")

    print(f"\nStarting file synchronization to '{remote_dir}'...")
    ftp.cwd(remote_dir)

    uploaded_count = 0
    for root, dirs, files in os.walk(local_path):
        rel_dir = os.path.relpath(root, local_path)
        if rel_dir == ".":
            target_remote = remote_dir.rstrip("/")
        else:
            target_remote = f"{remote_dir.rstrip('/')}/{rel_dir.replace(os.sep, '/')}"

        ensure_remote_dir(ftp, target_remote)
        ftp.cwd(target_remote)

        for fname in sorted(files):
            file_path = os.path.join(root, fname)
            with open(file_path, "rb") as f:
                ftp.storbinary(f"STOR {fname}", f)
            uploaded_count += 1
            if uploaded_count % 10 == 0 or uploaded_count == len(files):
                print(f"  Uploaded ({uploaded_count}) files...")

    print(f"\nSuccessfully deployed {uploaded_count} files to {remote_dir}!")


def main():
    parser = argparse.ArgumentParser(description="VedaVMS FTP Deployer")
    parser.add_argument("--server", default=os.getenv("FTP_SERVER", "ftp.vedavms.in"))
    parser.add_argument("--username", default=os.getenv("FTP_USERNAME", "vedavmsi"))
    parser.add_argument("--password", default=os.getenv("FTP_PASSWORD", ""))
    parser.add_argument("--server-dir", default=os.getenv("FTP_REMOTE_DIR", "/new/"))
    parser.add_argument("--local-dir", default="./build/")
    parser.add_argument("--port", type=int, default=21)
    args = parser.parse_args()

    # Clean server host
    server = args.server
    for prefix in ["ftps://", "ftp://", "http://", "https://"]:
        if server.startswith(prefix):
            server = server[len(prefix):]
    server = server.split("/")[0].split(":")[0].strip()
    if not server or server == "185.151.30.169":
        server = "ftp.vedavms.in"

    if not args.password:
        print("Error: FTP password is empty. Set FTP_PASSWORD environment variable or --password.")
        sys.exit(1)

    try:
        ftp = connect_ftp(server, args.username, args.password, port=args.port)
        upload_directory(ftp, args.local_dir, args.server_dir)
        try:
            ftp.quit()
        except Exception:
            ftp.close()
    except Exception as err:
        print(f"\nFTPS upload encountered an issue: {err}. Retrying with plain FTP connection...")
        ftp_plain = connect_ftp(server, args.username, args.password, port=args.port, force_plain=True)
        try:
            upload_directory(ftp_plain, args.local_dir, args.server_dir)
        finally:
            try:
                ftp_plain.quit()
            except Exception:
                ftp_plain.close()


if __name__ == "__main__":
    main()
