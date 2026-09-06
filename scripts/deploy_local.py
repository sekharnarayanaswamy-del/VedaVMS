#!/usr/bin/env python3
"""
Deploy local build/ directory to VedaVMS staging server (new.vedavms.in)
using Windows native curl with FTPS (TLS).
"""

import os
import sys
import getpass
import argparse
import subprocess
import urllib.request

SERVER = "103.69.196.157"
DEFAULT_USER = "vedavmsi"
REMOTE_DIR = "/httpdocs/"

FILES_TO_UPLOAD = [
    "index.html",
    "documents.html",
    "convention.html",
    "donations.html",
    "articles.html",
    "videos.html",
    "about.html",
]

def deploy():
    parser = argparse.ArgumentParser(description="Deploy build/ files to new.vedavms.in")
    parser.add_argument("--user", default=DEFAULT_USER, help=f"FTP Username (default: {DEFAULT_USER})")
    parser.add_argument("--password", default=None, help="FTP Password")
    args = parser.parse_args()

    user = args.user
    password = args.password
    if not password:
        password = getpass.getpass(f"Enter FTP Password for '{user}': ")

    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_dir = os.path.join(repo_dir, "build")

    if not os.path.isdir(build_dir):
        print(f"❌ Error: build directory not found at {build_dir}")
        sys.exit(1)

    print("=" * 60)
    print(" Deploying VedaVMS to new.vedavms.in (FTPS)")
    print("=" * 60)
    print(f"Target: ftps://{SERVER}{REMOTE_DIR}")
    print(f"User:   {user}\n")

    uploaded = 0
    failed = 0

    for fname in FILES_TO_UPLOAD:
        fpath = os.path.join(build_dir, fname)
        if not os.path.isfile(fpath):
            print(f"  ⚠️ Skipping {fname} (not found in build/)")
            continue

        size = os.path.getsize(fpath)
        print(f"  Uploading {fname} ({size:,} bytes)... ", end="", flush=True)

        remote_url = f"ftp://{SERVER}{REMOTE_DIR}{fname}"
        cmd = [
            "curl.exe",
            "--ssl-reqd",
            "--insecure",
            "--silent",
            "--show-error",
            "-u",
            f"{user}:{password}",
            "-T",
            fpath,
            remote_url,
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.returncode == 0:
                print("✓ Success")
                uploaded += 1
            else:
                print(f"❌ Failed: {res.stderr.strip()}")
                failed += 1
        except Exception as e:
            print(f"❌ Error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    if failed == 0:
        print(f"🎉 Deployment Complete! {uploaded} files successfully uploaded.")
        print("\nVerifying live website (https://new.vedavms.in)...")
        try:
            req = urllib.request.Request("https://new.vedavms.in", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f" Live site status: {resp.status} OK")
                print(" URL: https://new.vedavms.in")
        except Exception as e:
            print(f" Note: Live check had an issue ({e}), please check in your browser.")
    else:
        print(f"⚠️ Deployment finished with {failed} failures.")
    print("=" * 60)

if __name__ == "__main__":
    deploy()
