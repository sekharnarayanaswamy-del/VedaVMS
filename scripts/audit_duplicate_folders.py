#!/usr/bin/env python3
"""
Server Folder Hierarchy & Duplicate Mirror Audit for VedaVMS

Takes the canonical folders and referenced filenames from data/vedavms_documents.csv
and checks which mirror folders (e.g. lowercase/uppercase variants like tsg7, tsk1-kramam, Telugu, etc.)
exist on the server with identical filenames.
"""

import os
import re
import csv
import json
import time
import posixpath
import urllib.parse
import urllib.request
import urllib.error
import concurrent.futures
from collections import defaultdict

BASE = "https://vedavms.in"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_candidate_mirror_folders(canonical_folder: str) -> list[str]:
    """Generate likely server mirror/duplicate folder paths for a canonical folder."""
    base_dir = posixpath.dirname(canonical_folder) # e.g. /docs
    fld_name = posixpath.basename(canonical_folder) # e.g. TSG1, TSK1-Kramam, telugu
    
    mirrors = set()
    
    # 1. Lowercase
    if fld_name != fld_name.lower():
        mirrors.add(f"{base_dir}/{fld_name.lower()}")
    
    # 2. Uppercase / Titlecase
    if fld_name != fld_name.capitalize():
        mirrors.add(f"{base_dir}/{fld_name.capitalize()}")
    if fld_name != fld_name.upper():
        mirrors.add(f"{base_dir}/{fld_name.upper()}")

    # 3. Specific known pattern variations
    # Kramam: TSK1-Kramam -> tsk1-kramam, TSK1-kramam, tsk1-Kramam, TSK1, tsk1
    m_kram = re.match(r'TSK(\d+)-Kramam', fld_name, re.I)
    if m_kram:
        k = m_kram.group(1)
        mirrors.add(f"{base_dir}/tsk{k}-kramam")
        mirrors.add(f"{base_dir}/TSK{k}-kramam")
        mirrors.add(f"{base_dir}/tsk{k}-Kramam")
        mirrors.add(f"{base_dir}/TSK{k}")
        mirrors.add(f"{base_dir}/tsk{k}")

    # Padam: TS1-Padam -> ts1-padam, TS1-padam, ts1-Padam, TS1, ts1
    m_pad = re.match(r'TS(\d+)-Padam', fld_name, re.I)
    if m_pad:
        k = m_pad.group(1)
        mirrors.add(f"{base_dir}/ts{k}-padam")
        mirrors.add(f"{base_dir}/TS{k}-padam")
        mirrors.add(f"{base_dir}/ts{k}-Padam")
        mirrors.add(f"{base_dir}/TS{k}")
        mirrors.add(f"{base_dir}/ts{k}")

    # Ghanam / Jatai: TSG1 -> tsg1, TSG_1, tsg_1
    m_g = re.match(r'TSG(\d+)', fld_name, re.I)
    if m_g:
        k = m_g.group(1)
        mirrors.add(f"{base_dir}/tsg{k}")
        mirrors.add(f"{base_dir}/tsg_{k}")

    m_j = re.match(r'TSJ(\d+)', fld_name, re.I)
    if m_j:
        k = m_j.group(1)
        mirrors.add(f"{base_dir}/tsj{k}")
        mirrors.add(f"{base_dir}/tsj_{k}")

    # Other known naming variants
    if fld_name.lower() in ["shiva-stuti", "siva-stuti"]:
        mirrors.add(f"{base_dir}/Shiva-Stuti")
        mirrors.add(f"{base_dir}/Siva-Stuti")
        mirrors.add(f"{base_dir}/shiva-stuti")
        mirrors.add(f"{base_dir}/siva-stuti")

    if fld_name.lower() in ["shanti-japam", "shanti_japam"]:
        mirrors.add(f"{base_dir}/Shanti-Japam")
        mirrors.add(f"{base_dir}/shanti-japam")
        mirrors.add(f"{base_dir}/Shanti_Japam")
        mirrors.add(f"{base_dir}/shanti_japam")

    if fld_name.lower() in ["siksha", "siksha"]:
        mirrors.add(f"{base_dir}/SIkShA")
        mirrors.add(f"{base_dir}/SikShA")
        mirrors.add(f"{base_dir}/siksha")
        mirrors.add(f"{base_dir}/SIKSHA")

    if fld_name.lower() in ["kanvapri", "kanva"]:
        mirrors.add(f"{base_dir}/KanvaPRI")
        mirrors.add(f"{base_dir}/kanvapri")
        mirrors.add(f"{base_dir}/Kanva")
        mirrors.add(f"{base_dir}/kanva")

    # Remove canonical itself
    mirrors.discard(canonical_folder)
    return sorted(mirrors)


def check_url_exists(url: str) -> tuple[str, int, int]:
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'application/pdf,*/*',
        'Connection': 'keep-alive'
    }
    try:
        req = urllib.request.Request(url, headers=headers, method='HEAD')
        with urllib.request.urlopen(req, timeout=10) as resp:
            clen = int(resp.headers.get("Content-Length", 0))
            return url, resp.status, clen
    except Exception:
        return url, 404, 0


def main():
    print("=" * 80)
    print("       VEDAVMS SERVER FOLDER HIERARCHY & DUPLICATE FOLDER AUDIT")
    print("=" * 80)

    # 1. Load canonical folders & their files from CSV
    canonical_data = defaultdict(list)
    csv_path = os.path.join('data', 'vedavms_documents.csv')
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            for col in ['PDF_URL', 'Corrections_URL']:
                u = r.get(col, '').strip()
                if u and u.endswith('.pdf'):
                    path = urllib.parse.unquote(urllib.parse.urlsplit(u).path)
                    folder = posixpath.dirname(path)
                    fname = posixpath.basename(path)
                    if fname not in canonical_data[folder]:
                        canonical_data[folder].append(fname)

    print(f"Loaded {len(canonical_data)} canonical folders containing {sum(len(v) for v in canonical_data.values())} distinct PDF files.")

    # 2. Build list of all candidate test URLs for mirror folders
    mirror_tests = [] # (canonical_folder, mirror_folder, filename, test_url)
    mirror_folders_by_canon = {}

    for c_folder, files in sorted(canonical_data.items()):
        cand_mirrors = get_candidate_mirror_folders(c_folder)
        mirror_folders_by_canon[c_folder] = cand_mirrors
        for m_folder in cand_mirrors:
            for fname in files:
                url = f"{BASE}{m_folder}/{urllib.parse.quote(fname)}"
                mirror_tests.append((c_folder, m_folder, fname, url))

    print(f"Generated {len(mirror_tests)} mirror file check requests across candidate folder variations.")
    print("Scanning server with 24 concurrent workers...")

    start = time.time()
    url_to_status = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
        future_map = {executor.submit(check_url_exists, item[3]): item for item in mirror_tests}
        done = 0
        total = len(mirror_tests)
        for f in concurrent.futures.as_completed(future_map):
            url, status, clen = f.result()
            url_to_status[url] = (status, clen)
            done += 1
            if done % 500 == 0 or done == total:
                print(f"  Checked {done}/{total} files ({time.time() - start:.1f}s)...")

    # 3. Analyze results by folder
    # mirror_folder -> list of matched files
    folder_results = defaultdict(lambda: {"canonical": "", "matched_files": [], "total_canonical_files": 0})

    for c_folder, m_folder, fname, url in mirror_tests:
        status, clen = url_to_status.get(url, (404, 0))
        folder_results[m_folder]["canonical"] = c_folder
        folder_results[m_folder]["total_canonical_files"] = len(canonical_data[c_folder])
        if status == 200:
            folder_results[m_folder]["matched_files"].append({
                "filename": fname,
                "size_kb": clen // 1024,
                "url": url
            })

    # Separate existing mirror folders vs non-existent
    active_duplicate_folders = {
        m_fld: data for m_fld, data in folder_results.items() if len(data["matched_files"]) > 0
    }

    print("\n" + "=" * 80)
    print("                     DUPLICATE FOLDERS AUDIT SUMMARY")
    print("=" * 80)
    print(f"Total Canonical Folders:                 {len(canonical_data)}")
    print(f"Candidate Mirror Folders Tested:         {len(folder_results)}")
    print(f"Active Duplicate / Mirror Folders Found: {len(active_duplicate_folders)}")
    print("=" * 80)

    if active_duplicate_folders:
        print("\nFlagged Duplicate Mirror Folders on Web Server:")
        for m_fld, data in sorted(active_duplicate_folders.items()):
            matched_count = len(data["matched_files"])
            canon_count = data["total_canonical_files"]
            pct = (matched_count / canon_count * 100) if canon_count else 0
            print(f"\n📂 Duplicate Folder: {m_fld}  -->  Canonical: {data['canonical']}")
            print(f"   Matches: {matched_count}/{canon_count} files ({pct:.0f}% mirror)")
            for mf in data["matched_files"][:5]:
                print(f"     - [{mf['size_kb']} KB] {mf['filename']}")
            if matched_count > 5:
                print(f"     ... and {matched_count - 5} more files")
    else:
        print("No duplicate mirror folders found on the server.")

    # Save detailed JSON & Markdown
    output_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S IST"),
        "active_duplicate_folder_count": len(active_duplicate_folders),
        "duplicate_folders": [
            {
                "mirror_folder": m_fld,
                "canonical_folder": data["canonical"],
                "duplicate_file_count": len(data["matched_files"]),
                "total_canonical_files": data["total_canonical_files"],
                "match_percentage": round(len(data["matched_files"]) / data["total_canonical_files"] * 100, 1),
                "files": data["matched_files"]
            }
            for m_fld, data in sorted(active_duplicate_folders.items())
        ]
    }

    with open('build/duplicate_folders_audit.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    # Markdown Report
    with open('DUPLICATE_FOLDERS_AUDIT_REPORT.md', 'w', encoding='utf-8') as f:
        f.write("# Duplicate Mirror Folders Audit Report — VedaVMS (`public_html`)\n\n")
        f.write(f"**Generated:** {output_data['timestamp']}  \n")
        f.write(f"**Target Web Server:** `https://vedavms.in`  \n")
        f.write(f"**Canonical Source:** `data/vedavms_documents.csv`\n\n")

        f.write("## Executive Summary\n\n")
        f.write(f"This audit checked the server hierarchy for duplicate/mirror folders (such as lowercase/uppercase folder variants) that contain identical copies of files tracked under canonical folders in `vedavms_documents.csv`.\n\n")
        f.write("| Metric | Value |\n")
        f.write("|---|---:|\n")
        f.write(f"| **Canonical Folders Tracked in CSV** | {len(canonical_data)} |\n")
        f.write(f"| **Mirror Folder Variations Tested** | {len(folder_results)} |\n")
        f.write(f"| **Active Duplicate / Mirror Folders Found** | **{len(active_duplicate_folders)}** |\n")
        total_dup_files = sum(len(d["matched_files"]) for d in active_duplicate_folders.values())
        f.write(f"| **Total Duplicate PDF Files in Mirror Folders** | **{total_dup_files}** |\n\n")

        f.write("## Flagged Duplicate Folders on Server\n\n")
        if active_duplicate_folders:
            f.write("| # | Duplicate Folder on Server | Canonical Folder in CSV | Files Matched | Mirror Ratio |\n")
            f.write("|---|---|---|---:|:---:|\n")
            for i, (m_fld, data) in enumerate(sorted(active_duplicate_folders.items()), 1):
                matched = len(data["matched_files"])
                canon = data["total_canonical_files"]
                pct = f"{matched/canon*100:.0f}%"
                f.write(f"| {i} | `/{m_fld.lstrip('/')}/` | `/{data['canonical'].lstrip('/')}/` | {matched} / {canon} | {pct} |\n")

            f.write("\n## Detailed File Breakdown by Duplicate Folder\n\n")
            for m_fld, data in sorted(active_duplicate_folders.items()):
                f.write(f"### `/{m_fld.lstrip('/')}/` (Mirror of `/{data['canonical'].lstrip('/')}/`)\n\n")
                f.write(f"Contains **{len(data['matched_files'])} duplicate files** identical to canonical `{data['canonical']}`:\n\n")
                f.write("| # | Duplicate File | Size | Live Link |\n")
                f.write("|---|---|---:|---|\n")
                for j, mf in enumerate(data["matched_files"], 1):
                    f.write(f"| {j} | `{mf['filename']}` | {mf['size_kb']} KB | [Open PDF]({mf['url']}) |\n")
                f.write("\n")
        else:
            f.write("No duplicate mirror folders found on the server.\n")

    print("\nSaved detailed JSON to build/duplicate_folders_audit.json")
    print("Saved Markdown report to DUPLICATE_FOLDERS_AUDIT_REPORT.md")


if __name__ == '__main__':
    main()
