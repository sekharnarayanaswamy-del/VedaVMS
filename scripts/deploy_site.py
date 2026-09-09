#!/usr/bin/env python3
"""
VedaVMS Site Deployment & Rollback Script

Deploys build/ artifacts to the server (FTPS) or rolls back to an archived snapshot.

Usage:
    # --- DEPLOYMENT ---
    # Deploy to Staging (new.vedavms.in)
    python scripts/deploy_site.py --staging
    python scripts/deploy_site.py --dir /new.vedavms.in

    # Deploy to Live Production (vedavms.in) with automatic pre-deploy backup
    python scripts/deploy_site.py --production
    python scripts/deploy_site.py --dir /httpdocs

    # Simulation / Dry Run
    python scripts/deploy_site.py --production --dry-run

    # --- ROLLBACK & ARCHIVES ---
    # List all available archived snapshots
    python scripts/deploy_site.py --list-backups

    # Roll back production (vedavms.in) to an archived snapshot
    python scripts/deploy_site.py --rollback --production

    # Roll back staging (new.vedavms.in) to a specific snapshot
    python scripts/deploy_site.py --rollback --staging --snapshot backup_production_vedavms_in
"""

import os
import sys
import glob
import time
import getpass
import argparse
import datetime
import urllib.request
from ftplib import FTP, FTP_TLS

class ReusedSessionFTP_TLS(FTP_TLS):
    """Reuses the TLS session on data connections to satisfy IIS FTP server requirements."""
    def ntransfercmd(self, cmd, rest=None):
        conn, size = FTP.ntransfercmd(self, cmd, rest)
        if getattr(self, '_prot_p', False) and hasattr(self.sock, 'session'):
            conn = self.context.wrap_socket(
                conn,
                server_hostname=self.host,
                session=self.sock.session
            )
        return conn, size


def load_env_credentials(repo_dir: str) -> str:
    """Attempt to load FTP password from environment variables or .env file."""
    env_pass = os.environ.get("FTP_PASSWORD") or os.environ.get("STAGING_FTP_PASSWORD") or os.environ.get("PROD_FTP_PASSWORD")
    if env_pass:
        return env_pass

    env_file = os.path.join(repo_dir, ".env")
    if os.path.isfile(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        if k.strip() in ("FTP_PASSWORD", "STAGING_FTP_PASSWORD", "PROD_FTP_PASSWORD"):
                            return v.strip().strip("'\"")
        except Exception:
            pass
    return ""


def get_available_snapshots(repo_dir: str) -> list[dict]:
    """Discover all local archived snapshots (original baseline + timestamped backups)."""
    snapshots = []

    # 1. Original legacy baseline
    baseline_dir = os.path.join(repo_dir, "backup_production_vedavms_in")
    if os.path.isdir(baseline_dir):
        files = [f for f in os.listdir(baseline_dir) if os.path.isfile(os.path.join(baseline_dir, f))]
        snapshots.append({
            "name": "backup_production_vedavms_in",
            "path": baseline_dir,
            "label": "Original Production Baseline (Pre-redesign legacy site)",
            "file_count": len(files),
            "files": files,
            "is_legacy": True,
        })

    # 2. Automated timestamped backups in backups/
    backups_dir = os.path.join(repo_dir, "backups")
    if os.path.isdir(backups_dir):
        for entry in sorted(os.listdir(backups_dir), reverse=True):
            full_path = os.path.join(backups_dir, entry)
            if os.path.isdir(full_path):
                files = [f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))]
                snapshots.append({
                    "name": entry,
                    "path": full_path,
                    "label": f"Automated Pre-Deploy Snapshot ({entry})",
                    "file_count": len(files),
                    "files": files,
                    "is_legacy": False,
                })

    return snapshots


def list_backups(repo_dir: str):
    """Print a clean table of all available archived snapshots."""
    snapshots = get_available_snapshots(repo_dir)
    print("\n" + "=" * 70)
    print("  📁 Available Archived Snapshots for Rollback")
    print("=" * 70)
    if not snapshots:
        print("  No local backup snapshots found.")
        print("=" * 70 + "\n")
        return

    for i, s in enumerate(snapshots, 1):
        print(f"  [{i}] {s['name']}")
        print(f"      Description : {s['label']}")
        print(f"      Files Count : {s['file_count']} files")
        print(f"      Folder Path : {os.path.relpath(s['path'], repo_dir)}")
        print()
    print("=" * 70 + "\n")


def backup_remote_files(ftp: FTP_TLS, remote_dir: str, backup_dest: str, files_to_backup: list[str]) -> int:
    """Download existing remote files before overwriting for safe rollback."""
    os.makedirs(backup_dest, exist_ok=True)
    backed_up = 0
    print(f"\n📦 Creating pre-deploy backup of '{remote_dir}' -> '{os.path.relpath(backup_dest)}'...")

    remote_filenames = []
    try:
        remote_filenames = ftp.nlst()
    except Exception:
        pass

    for filename in files_to_backup:
        match = next((f for f in remote_filenames if f.lower() == filename.lower() or f.endswith("/" + filename)), None)
        if match or not remote_filenames:
            dest_file = os.path.join(backup_dest, filename)
            try:
                with open(dest_file, "wb") as f:
                    ftp.retrbinary(f"RETR {filename}", f.write)
                filesize = os.path.getsize(dest_file)
                print(f"  ✓ Backed up {filename:<22} ({filesize:>8,} bytes)")
                backed_up += 1
            except Exception:
                if os.path.exists(dest_file):
                    os.remove(dest_file)
    return backed_up


def perform_rollback(args, repo_dir: str, target_dir: str, is_production: bool, site_label: str, site_url: str):
    """Execute rollback by restoring a selected snapshot to the target remote directory."""
    snapshots = get_available_snapshots(repo_dir)
    if not snapshots:
        print("❌ Error: No archived snapshots found in repository.")
        sys.exit(1)

    selected_snapshot = None
    if args.snapshot:
        # Match by name or path
        selected_snapshot = next(
            (s for s in snapshots if s["name"].lower() == args.snapshot.lower() or s["path"].lower() == args.snapshot.lower()),
            None
        )
        if not selected_snapshot:
            print(f"❌ Error: Snapshot '{args.snapshot}' not found. Run with --list-backups to view choices.")
            sys.exit(1)
    else:
        print("\n" + "=" * 70)
        print("  🔄 Select an Archived Snapshot to Restore")
        print("=" * 70)
        for i, s in enumerate(snapshots, 1):
            print(f"  [{i}] {s['name']} ({s['file_count']} files)")
            print(f"      {s['label']}")
        print("=" * 70)

        choice = input(f"\nEnter snapshot number [1-{len(snapshots)}] (default 1): ").strip()
        idx = int(choice) - 1 if choice.isdigit() and 1 <= int(choice) <= len(snapshots) else 0
        selected_snapshot = snapshots[idx]

    source_dir = selected_snapshot["path"]
    files_to_restore = [f for f in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f))]

    print("\n" + "=" * 70)
    print(f"  🚨 ROLLBACK TARGET: {site_label}")
    print(f"  Selected Snapshot : {selected_snapshot['name']}")
    print(f"  Snapshot Path     : {os.path.relpath(source_dir, repo_dir)}")
    print(f"  Files to Restore  : {len(files_to_restore)} files ({', '.join(sorted(files_to_restore)[:5])}...)")
    print(f"  Target Server     : {args.server}")
    print(f"  Remote Folder     : {target_dir}")
    print("=" * 70)

    if not args.dry_run:
        confirm = input(f"\n⚠️ Are you sure you want to RESTORE this snapshot to {target_dir}? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Rollback cancelled by user.")
            sys.exit(0)

    if args.dry_run:
        print("\n[DRY RUN] Would restore the following files to the remote server:")
        for f in sorted(files_to_restore):
            fp = os.path.join(source_dir, f)
            print(f"  - {f:<25} ({os.path.getsize(fp):>8,} bytes) -> {target_dir}/{f}")
        print("\n[DRY RUN] Rollback simulation complete. No remote files modified.")
        return

    password = args.password or load_env_credentials(repo_dir)
    if not password:
        password = getpass.getpass(f"Enter FTP password for user '{args.user}': ")

    print(f"\nConnecting to {args.server} via FTPS...")
    ftp = ReusedSessionFTP_TLS()
    try:
        ftp.connect(args.server, 21, timeout=25)
        ftp.login(args.user, password)
        ftp.prot_p()
        print("✓ Connected & Authenticated successfully!")

        print(f"Switching to remote directory '{target_dir}'...")
        ftp.cwd(target_dir)
        print(f"✓ Current working directory: {ftp.pwd()}")

        print(f"\n--- Uploading snapshot files to {target_dir} ---")
        for filename in sorted(files_to_restore):
            filepath = os.path.join(source_dir, filename)
            filesize = os.path.getsize(filepath)
            print(f"  Restoring {filename:<25} ({filesize:>8,} bytes)... ", end="", flush=True)
            with open(filepath, "rb") as f:
                ftp.storbinary(f"STOR {filename}", f)
            print("✓ Done")

        # If rolling back to the legacy baseline, optionally clean up redesign companion files
        if selected_snapshot.get("is_legacy"):
            cleanup_files = ["documents.html", "articles.html", "videos.html", "about.html", "vedavms_documents.csv"]
            print("\nCleaning up redesign-only files from legacy site...")
            for unwanted in cleanup_files:
                try:
                    ftp.delete(unwanted)
                    print(f"  ✓ Removed {unwanted}")
                except Exception:
                    pass

        print(f"\n🎉 Rollback to snapshot '{selected_snapshot['name']}' completed successfully!")

        if site_url:
            print(f"\nVerifying restored site: {site_url} ...")
            try:
                req = urllib.request.Request(site_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=12) as resp:
                    print(f"✓ HTTP Status: {resp.status} OK")
            except Exception as ex:
                print(f"  (Verification ping note: {ex})")

    except Exception as e:
        print(f"\n❌ Error during rollback: {e}")
        sys.exit(1)
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Deploy VedaVMS build files to target server folder or rollback to an archived snapshot.")
    parser.add_argument("--dir", default=None, help="Target remote folder (e.g. '/httpdocs' or '/new.vedavms.in')")
    parser.add_argument("--staging", action="store_true", help="Shortcut for --dir /new.vedavms.in (new.vedavms.in)")
    parser.add_argument("--production", "--live", action="store_true", help="Shortcut for --dir /httpdocs (vedavms.in)")
    parser.add_argument("--server", default="103.69.196.157", help="FTP Host (default: 103.69.196.157)")
    parser.add_argument("--user", default="vedavmsi", help="FTP Username (default: vedavmsi)")
    parser.add_argument("--password", default=None, help="FTP Password")
    parser.add_argument("--backup", action="store_true", help="Force pre-deploy backup snapshot of remote files")
    parser.add_argument("--no-backup", action="store_true", help="Skip pre-deploy backup snapshot")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deployed/restored without modifying server")

    # Rollback arguments
    parser.add_argument("--rollback", action="store_true", help="Restore site from an archived snapshot")
    parser.add_argument("--snapshot", default=None, help="Snapshot folder name or path to restore (used with --rollback)")
    parser.add_argument("--list-backups", "--backups", action="store_true", help="List all available archived snapshots and exit")

    args = parser.parse_args()
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Listing backups
    if args.list_backups:
        list_backups(repo_dir)
        return

    # Determine target directory
    target_dir = args.dir
    if args.production:
        target_dir = "/httpdocs"
    elif args.staging:
        target_dir = "/new.vedavms.in"

    if not target_dir:
        print("\nTarget folder not specified. Choose a target:")
        print("  1) Staging    (/new.vedavms.in  -> https://new.vedavms.in)")
        print("  2) Production (/httpdocs        -> https://vedavms.in)")
        print("  3) Custom path")
        choice = input("\nEnter choice [1/2/3] (default 1): ").strip()
        if choice == "2":
            target_dir = "/httpdocs"
        elif choice == "3":
            target_dir = input("Enter remote folder path (e.g. /httpdocs): ").strip()
        else:
            target_dir = "/new.vedavms.in"

    if not target_dir.startswith("/"):
        target_dir = "/" + target_dir

    is_production = target_dir.rstrip("/") == "/httpdocs"
    site_label = "Production (vedavms.in)" if is_production else f"Target Folder ({target_dir})"
    site_url = "https://vedavms.in" if is_production else ("https://new.vedavms.in" if "new.vedavms.in" in target_dir else "")

    # Execute Rollback mode if requested
    if args.rollback:
        perform_rollback(args, repo_dir, target_dir, is_production, site_label, site_url)
        return

    # Standard Deployment mode
    build_dir = os.path.join(repo_dir, "build")
    if not os.path.isdir(build_dir):
        print(f"❌ Error: build directory not found at {build_dir}. Please run 'python generate_documents.py' first.")
        sys.exit(1)

    files_to_upload = [f for f in os.listdir(build_dir) if os.path.isfile(os.path.join(build_dir, f))]
    if not files_to_upload:
        print(f"❌ Error: No files found in {build_dir}. Please run 'python generate_documents.py' first.")
        sys.exit(1)

    # Pre-deployment safeguard: check essential pages exist
    required_files = ["index.html", "documents.html"]
    for req in required_files:
        if req not in files_to_upload:
            print(f"❌ Safety Gate Abort: Required file '{req}' is missing from build/ directory.")
            sys.exit(1)

    print("=" * 65)
    print(f"  VedaVMS Deployment -> {site_label}")
    print(f"  Target Server: {args.server}")
    print(f"  Remote Folder: {target_dir}")
    print(f"  Files ({len(files_to_upload)}): {', '.join(sorted(files_to_upload))}")
    print("=" * 65)

    if is_production and not args.dry_run:
        confirm = input(f"\n⚠️ WARNING: You are deploying to LIVE PRODUCTION ({target_dir}).\nAre you sure you want to proceed? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Deployment cancelled by user.")
            sys.exit(0)

    if args.dry_run:
        print("\n[DRY RUN] Would deploy the following files:")
        for f in sorted(files_to_upload):
            fp = os.path.join(build_dir, f)
            print(f"  - {f:<22} ({os.path.getsize(fp):>8,} bytes) -> {target_dir}/{f}")
        print("\n[DRY RUN] Completed without making any changes.")
        return

    password = args.password or load_env_credentials(repo_dir)
    if not password:
        password = getpass.getpass(f"Enter FTP password for user '{args.user}': ")

    print(f"\nConnecting to {args.server} via FTPS...")
    ftp = ReusedSessionFTP_TLS()
    try:
        ftp.connect(args.server, 21, timeout=25)
        ftp.login(args.user, password)
        ftp.prot_p()
        print("✓ Connected & Authenticated successfully!")

        print(f"Switching to remote directory '{target_dir}'...")
        try:
            ftp.cwd(target_dir)
        except Exception as e:
            print(f"❌ Could not access directory '{target_dir}': {e}")
            print("Available directories under root '/':")
            ftp.cwd("/")
            ftp.retrlines("LIST")
            sys.exit(1)

        print(f"✓ Current working directory: {ftp.pwd()}")

        # Automated backup snapshot
        should_backup = (is_production or args.backup) and not args.no_backup
        if should_backup:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_clean = target_dir.strip("/").replace("/", "_") or "root"
            backup_dir = os.path.join(repo_dir, "backups", f"backup_{folder_clean}_{ts}")
            count = backup_remote_files(ftp, target_dir, backup_dir, files_to_upload)
            if count > 0:
                print(f"  ✓ Snapshot saved ({count} files). Rollback location: {backup_dir}")

        # Upload files
        print(f"\n--- Uploading build files to {target_dir} ---")
        for filename in sorted(files_to_upload):
            filepath = os.path.join(build_dir, filename)
            filesize = os.path.getsize(filepath)
            print(f"  Uploading {filename:<22} ({filesize:>8,} bytes)... ", end="", flush=True)
            with open(filepath, "rb") as f:
                ftp.storbinary(f"STOR {filename}", f)
            print("✓ Done")

        print(f"\n🎉 Deployment to {site_label} ({target_dir}) completed successfully!")

        if site_url:
            print(f"\nVerifying deployed site: {site_url} ...")
            try:
                req = urllib.request.Request(site_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=12) as resp:
                    print(f"✓ HTTP Status: {resp.status} OK")
            except Exception as ex:
                print(f"  (Verification ping note: {ex})")

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
