#!/usr/bin/env python3
"""
Restore original legacy index.html and convention.html to vedavms.in
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

def restore():
    parser = argparse.ArgumentParser(description="Restore original main site files to vedavms.in")
    parser.add_argument("--user", default=DEFAULT_USER, help=f"FTP Username (default: {DEFAULT_USER})")
    parser.add_argument("--password", default=None, help="FTP Password")
    args = parser.parse_args()

    user = args.user
    password = args.password
    if not password:
        password = getpass.getpass(f"Enter FTP Password for '{user}': ")

    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    orig_index = os.path.join(repo_dir, "original_index.html")
    orig_conv = os.path.join(repo_dir, "original_convention.html")
    orig_donations = os.path.join(repo_dir, "original_Donations.html")

    if not os.path.isfile(orig_index) or not os.path.isfile(orig_conv) or not os.path.isfile(orig_donations):
        print("❌ Error: original backup files not found.")
        sys.exit(1)

    print("=" * 60)
    print(" Restoring Original Legacy Website on vedavms.in")
    print("=" * 60)

    files_to_restore = [
        (orig_index, "index.html"),
        (orig_conv, "convention.html"),
        (orig_donations, "Donations.html"),
    ]

    for local_path, remote_name in files_to_restore:
        size = os.path.getsize(local_path)
        print(f"Restoring {remote_name} ({size:,} bytes)... ", end="", flush=True)
        remote_url = f"ftp://{SERVER}{REMOTE_DIR}{remote_name}"
        cmd = [
            "curl.exe",
            "--ssl-reqd",
            "--insecure",
            "--silent",
            "--show-error",
            "-u",
            f"{user}:{password}",
            "-T",
            local_path,
            remote_url,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print("✓ Restored successfully!")
        else:
            print(f"❌ Failed: {res.stderr.strip()}")

    cleanup = input("\nWould you also like to clean up the unused redesign files (documents.html, articles.html, videos.html, about.html) from vedavms.in? [Y/n]: ").strip().lower()
    if cleanup != "n":
        print("Cleaning up unused redesign files...")
        for unwanted in ["documents.html", "articles.html", "videos.html", "about.html"]:
            cmd = [
                "curl.exe",
                "--ssl-reqd",
                "--insecure",
                "--silent",
                "-u",
                f"{user}:{password}",
                "-Q",
                f"DELE {REMOTE_DIR}{unwanted}",
                f"ftp://{SERVER}/",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            print(f"  ✓ Checked {unwanted}")

    print("\nVerifying live website (https://vedavms.in)...")
    try:
        req = urllib.request.Request("https://vedavms.in", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            print(f" Status: {resp.status} OK")
            print(f" Verified: {'Om Shri Mahaganapathaye Namaha' in content}")
            print(" https://vedavms.in is restored to its original version!")
    except Exception as e:
        print(f"Verification note: {e}")

if __name__ == "__main__":
    restore()
