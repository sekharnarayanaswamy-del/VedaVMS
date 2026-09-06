#!/usr/bin/env python3
"""
Sync Google Sheets and deploy to new.vedavms.in (/new.vedavms.in).
Uses Windows native curl.exe for robust FTPS transfer to IIS, with fallback to Python ftplib.
"""

import os
import sys
import getpass
import argparse
import subprocess
import shutil
from ftplib import FTP, FTP_TLS

DEFAULT_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1O-pBNmfEhBEHsbR47T-pMlrW36BpGdoJdiwHpVjDDjs/export?format=csv&gid=548744990"
)

class ReusedSessionFTP_TLS(FTP_TLS):
    """Fallback Python FTPS with TLS session reuse."""
    def ntransfercmd(self, cmd, rest=None):
        conn, size = FTP.ntransfercmd(self, cmd, rest)
        if getattr(self, '_prot_p', False) and hasattr(self.sock, 'session'):
            conn = self.context.wrap_socket(
                conn,
                server_hostname=self.host,
                session=self.sock.session
            )
        conn.settimeout(120)
        return conn, size

def step_1_generate_build(sheet_url: str):
    print("\n" + "=" * 65)
    print(" [1/2] Fetching Google Sheet & Regenerating build/")
    print("=" * 65)
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gen_script = os.path.join(repo_dir, "generate_documents.py")

    cmd = [sys.executable, gen_script, "--source-csv", sheet_url]
    print(f"Running: python generate_documents.py --source-csv <Google Sheets>")
    result = subprocess.run(cmd, cwd=repo_dir)
    if result.returncode != 0:
        print("❌ Error: generate_documents.py failed!")
        sys.exit(result.returncode)
    print("✓ Successfully regenerated build/ from Google Sheets.")

def upload_via_curl(server: str, user: str, password: str, remote_dir: str, files_to_upload: list[str], build_dir: str):
    rdir = remote_dir.strip("/")
    print(f"\nUsing native curl transfer engine (Windows Schannel / IIS compatible)...")
    for filename in files_to_upload:
        filepath = os.path.join(build_dir, filename)
        filesize = os.path.getsize(filepath)
        print(f"  Uploading {filename:<20} ({filesize:>8,} bytes)... ", end="", flush=True)

        url = f"ftp://{server}/{rdir}/{filename}"
        cmd = [
            "curl.exe",
            "-k",
            "--ssl-reqd",
            "--ftp-pasv",
            "--ftp-create-dirs",
            "-T", filepath,
            url,
            "-u", f"{user}:{password}",
            "--silent",
            "--show-error"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Done")
        else:
            print(f"❌ Failed: {result.stderr.strip()}")
            raise RuntimeError(f"curl upload failed for {filename}: {result.stderr.strip()}")

def upload_via_ftplib(server: str, user: str, password: str, remote_dir: str, files_to_upload: list[str], build_dir: str):
    print(f"\nUsing Python ftplib engine...")
    ftp = ReusedSessionFTP_TLS()
    ftp.timeout = 120
    ftp.connect(server, 21, timeout=120)
    ftp.login(user, password)
    ftp.prot_p()
    ftp.set_pasv(True)
    ftp.cwd(remote_dir)

    for filename in files_to_upload:
        filepath = os.path.join(build_dir, filename)
        filesize = os.path.getsize(filepath)
        print(f"  Uploading {filename:<20} ({filesize:>8,} bytes)... ", end="", flush=True)
        with open(filepath, "rb") as f:
            ftp.storbinary(f"STOR {filename}", f, blocksize=65536)
        print("✓ Done")
    ftp.quit()

def step_2_upload_to_staging(server: str, user: str, password: str, remote_dir: str):
    print("\n" + "=" * 65)
    print(f" [2/2] Uploading build/ to new.vedavms.in ({remote_dir})")
    print("=" * 65)
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_dir = os.path.join(repo_dir, "build")

    files_to_upload = sorted([
        f for f in os.listdir(build_dir) if os.path.isfile(os.path.join(build_dir, f))
    ])

    # Check if curl is available
    has_curl = shutil.which("curl.exe") is not None or shutil.which("curl") is not None
    if has_curl:
        upload_via_curl(server, user, password, remote_dir, files_to_upload, build_dir)
    else:
        upload_via_ftplib(server, user, password, remote_dir, files_to_upload, build_dir)

    print("\n🎉 All files synced to new.vedavms.in successfully!")

def load_local_password(repo_dir: str) -> str | None:
    # 1. Check environment variables
    env_pass = os.environ.get("STAGING_FTP_PASSWORD") or os.environ.get("FTP_PASSWORD")
    if env_pass:
        return env_pass

    # 2. Check local .env file
    env_file = os.path.join(repo_dir, ".env")
    if os.path.isfile(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or not line or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k in ("STAGING_FTP_PASSWORD", "FTP_PASSWORD", "FTP_PASS"):
                        return v
        except Exception:
            pass

    # 3. Check .ftp_credentials or .ftp_pass file
    for name in (".ftp_credentials", ".ftp_pass"):
        cred_file = os.path.join(repo_dir, name)
        if os.path.isfile(cred_file):
            try:
                with open(cred_file, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                    if text:
                        return text
            except Exception:
                pass

    return None

def main():
    parser = argparse.ArgumentParser(description="Sync Google Sheets to new.vedavms.in")
    parser.add_argument("--password", default=None, help="FTP Password")
    parser.add_argument("--sheet-url", default=DEFAULT_SHEET_URL, help="Google Sheets CSV URL")
    parser.add_argument("--server", default="103.69.196.157", help="FTP Server host")
    parser.add_argument("--user", default="vedavmsi", help="FTP Username")
    parser.add_argument("--dir", default="/new.vedavms.in", help="Staging remote directory")
    parser.add_argument("--skip-build", action="store_true", help="Skip Google Sheets fetch")
    args = parser.parse_args()

    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Step 1: Build
    if not args.skip_build:
        step_1_generate_build(args.sheet_url)

    # Step 2: Upload
    password = args.password or load_local_password(repo_dir)
    if not password:
        password = getpass.getpass(f"\nEnter FTP password for '{args.user}': ")
    else:
        print(f"\n✓ Loaded FTP password automatically from local configuration.")

    step_2_upload_to_staging(args.server, args.user, password, args.dir)

if __name__ == "__main__":
    main()
