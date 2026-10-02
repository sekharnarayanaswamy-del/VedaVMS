#!/usr/bin/env python3
"""
Comprehensive Orphaned PDF Audit for https://vedavms.in

Compares all PDF files hosted on vedavms.in (public_html) with data/vedavms_documents.csv.
Identifies:
1. Live PDFs in CSV (Matched & Active)
2. Live PDFs on server but NOT in CSV (Orphaned PDFs)
3. CSV URLs that are 404 (Missing PDFs)
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

def normalize_url(url: str) -> str:
    """Normalize URL path and encoding cleanly."""
    url = url.strip().split('?')[0].split('#')[0]
    if not url.startswith('http'):
        if url.startswith('/'):
            url = f"{BASE}{url}"
        else:
            url = f"{BASE}/{url}"
    parts = urllib.parse.urlsplit(url)
    raw_path = urllib.parse.unquote(parts.path)
    norm_path = posixpath.normpath(raw_path)
    if not norm_path.startswith('/'):
        norm_path = '/' + norm_path
    quoted_path = urllib.parse.quote(norm_path)
    return urllib.parse.urlunsplit(('https', 'vedavms.in', quoted_path, '', ''))

def load_csv_urls(csv_path: str):
    """Load all PDF and corrections URLs from master CSV."""
    csv_exact_urls = set()
    csv_norm_urls = set()
    csv_rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            csv_rows.append(r)
            pdf = r.get('PDF_URL', '').strip()
            if pdf:
                csv_exact_urls.add(pdf)
                csv_norm_urls.add(normalize_url(pdf))
            corr = r.get('Corrections_URL', '').strip()
            if corr:
                csv_exact_urls.add(corr)
                csv_norm_urls.add(normalize_url(corr))
    return csv_exact_urls, csv_norm_urls, csv_rows

def discover_all_candidate_urls():
    """Scrape and find every single PDF URL from all files in repository."""
    discovered = defaultdict(set) # norm_url -> set of source files
    
    for root, dirs, files in os.walk('.'):
        if '.git' in root or '.cache' in root:
            continue
        for f in files:
            if f.endswith(('.html', '.php', '.md', '.txt', '.py', '.json', '.csv')):
                fpath = os.path.join(root, f)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                        content = fh.read()
                    
                    # Full URLs
                    for m in re.findall(r'(https?://(?:www\.)?vedavms\.in/[^\s"\'()<>]+\.pdf)', content, re.I):
                        norm = normalize_url(m)
                        discovered[norm].add(fpath)
                        
                    # Relative URLs
                    for m in re.findall(r'href=["\'](/?[a-zA-Z0-9_\-\./%]+\.pdf)["\']', content, re.I):
                        if not m.startswith('http'):
                            norm = normalize_url(m)
                            discovered[norm].add(fpath)
                            
                    # Markdown links
                    for m in re.findall(r'\]\((/?[a-zA-Z0-9_\-\./%]+\.pdf)\)', content, re.I):
                        norm = normalize_url(m)
                        discovered[norm].add(fpath)
                except Exception:
                    pass
    return discovered

def check_url_status(url: str) -> tuple[str, int, int, str]:
    """Test URL on live server with HEAD / GET."""
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'application/pdf,*/*',
        'Connection': 'keep-alive'
    }
    # Try HEAD first
    try:
        req = urllib.request.Request(url, headers=headers, method='HEAD')
        with urllib.request.urlopen(req, timeout=12) as resp:
            clen = int(resp.headers.get("Content-Length", 0))
            ctype = resp.headers.get("Content-Type", "")
            return url, resp.status, clen, ctype
    except Exception:
        # Fallback to GET
        try:
            req = urllib.request.Request(url, headers=headers, method='GET')
            with urllib.request.urlopen(req, timeout=12) as resp:
                clen = int(resp.headers.get("Content-Length", 0))
                ctype = resp.headers.get("Content-Type", "")
                return url, resp.status, clen, ctype
        except urllib.error.HTTPError as e:
            return url, e.code, 0, str(e.reason)
        except Exception as e:
            return url, 0, 0, type(e).__name__

def main():
    csv_path = os.path.join('data', 'vedavms_documents.csv')
    print("1. Loading master CSV...", flush=True)
    csv_exact, csv_norm, csv_rows = load_csv_urls(csv_path)
    print(f"   Loaded {len(csv_rows)} rows from CSV ({len(csv_norm)} distinct normalized URLs).", flush=True)

    print("\n2. Discovering candidate PDF URLs across codebase & historical files...", flush=True)
    discovered_dict = discover_all_candidate_urls()
    print(f"   Discovered {len(discovered_dict)} unique candidate PDF URLs.", flush=True)

    # Combine all candidate URLs
    all_urls_to_test = set(discovered_dict.keys())
    for u in csv_norm:
        all_urls_to_test.add(u)

    print(f"\n3. Testing {len(all_urls_to_test)} candidate PDF URLs on live server https://vedavms.in ...", flush=True)
    start = time.time()
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(check_url_status, u): u for u in all_urls_to_test}
        done = 0
        for f in concurrent.futures.as_completed(futures):
            url, status, clen, ctype = f.result()
            results[url] = (status, clen, ctype)
            done += 1
            if done % 200 == 0 or done == len(all_urls_to_test):
                print(f"   Tested {done}/{len(all_urls_to_test)} URLs ({time.time() - start:.1f}s)...", flush=True)

    # Classify results
    live_in_csv = []
    orphaned_live = []
    csv_missing = []
    dead_candidate_urls = []

    for url, (status, clen, ctype) in results.items():
        is_in_csv = (url in csv_norm)

        if status == 200:
            if is_in_csv:
                live_in_csv.append((url, clen, list(discovered_dict.get(url, []))))
            else:
                orphaned_live.append((url, clen, list(discovered_dict.get(url, []))))
        else:
            if is_in_csv:
                csv_missing.append((url, status, list(discovered_dict.get(url, []))))
            else:
                dead_candidate_urls.append((url, status, list(discovered_dict.get(url, []))))

    print("\n" + "=" * 80, flush=True)
    print("                        AUDIT SUMMARY RESULTS", flush=True)
    print("=" * 80, flush=True)
    print(f"Total Unique URLs Tested:           {len(results)}", flush=True)
    print(f"✅ Live & Managed in CSV:            {len(live_in_csv)}", flush=True)
    print(f"⚠️  Live Orphaned PDFs (NOT in CSV):  {len(orphaned_live)}", flush=True)
    print(f"❌ Missing CSV URLs (404/Error):     {len(csv_missing)}", flush=True)
    print(f"🗑️  Historical Dead Links (404):      {len(dead_candidate_urls)}", flush=True)
    print("=" * 80, flush=True)

    # Group Orphaned PDFs by Category/Directory
    orphaned_by_dir = defaultdict(list)
    for u, clen, srcs in sorted(orphaned_live, key=lambda x: x[0]):
        unq_path = urllib.parse.unquote(urllib.parse.urlsplit(u).path)
        d = '/'.join(unq_path.split('/')[:-1])
        orphaned_by_dir[d].append({
            "url": u,
            "filename": os.path.basename(unq_path),
            "unquoted_path": unq_path,
            "size_bytes": clen,
            "size_kb": round(clen / 1024, 1) if clen else 0,
            "sources": srcs
        })

    # Save output to JSON
    output_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S IST"),
        "total_tested": len(results),
        "live_in_csv_count": len(live_in_csv),
        "orphaned_live_count": len(orphaned_live),
        "csv_missing_count": len(csv_missing),
        "orphaned_live_by_directory": {
            d: items for d, items in sorted(orphaned_by_dir.items())
        },
        "csv_missing": [
            {
                "url": u,
                "status": st,
                "sources": srcs
            }
            for u, st, srcs in sorted(csv_missing, key=lambda x: x[0])
        ]
    }

    with open('build/orphaned_pdf_audit.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    # Generate Detailed Markdown Report
    with open('ORPHANED_PDF_AUDIT_REPORT.md', 'w', encoding='utf-8') as f:
        f.write("# Orphaned PDF Audit Report — VedaVMS (`public_html`)\n\n")
        f.write(f"**Generated:** {output_data['timestamp']}  \n")
        f.write(f"**Target Host:** `https://vedavms.in`  \n")
        f.write(f"**Master Reference File:** `data/vedavms_documents.csv`\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write("| Category | Count | Status |\n")
        f.write("|---|---:|:---:|\n")
        f.write(f"| **Active & Managed in CSV** | **{len(live_in_csv)}** | ✅ Healthy |\n")
        f.write(f"| **Orphaned PDFs (Live on Server, Missing from CSV)** | **{len(orphaned_live)}** | ⚠️ Review Required |\n")
        f.write(f"| **Broken CSV Links (404/Error)** | **{len(csv_missing)}** | {'✅ None (100% verified)' if not csv_missing else '❌ Fix Required'} |\n")
        f.write(f"| **Historical Dead References** | **{len(dead_candidate_urls)}** | ℹ️ Inactive |\n\n")

        if csv_missing:
            f.write("## ❌ Broken CSV URLs (Action Required)\n\n")
            f.write("| # | URL in CSV | HTTP Status |\n")
            f.write("|---|---|---:|\n")
            for i, item in enumerate(output_data['csv_missing'], 1):
                f.write(f"| {i} | [`{item['url']}`]({item['url']}) | {item['status']} |\n")
            f.write("\n")

        f.write("## ⚠️ Orphaned PDFs by Directory\n\n")
        f.write("These files physically exist on the `https://vedavms.in` server, return **HTTP 200 OK**, but are **not present** in `data/vedavms_documents.csv`.\n\n")
        
        for directory, files in sorted(orphaned_by_dir.items()):
            total_size_kb = sum(f['size_kb'] for f in files)
            f.write(f"### `{directory}/` ({len(files)} files, {total_size_kb:.1f} KB total)\n\n")
            f.write("| # | File Name | Size | Live Link | Reference Sources |\n")
            f.write("|---|---|---:|---|---|\n")
            for i, file_info in enumerate(files, 1):
                fn = file_info['filename']
                size_str = f"{file_info['size_kb']} KB" if file_info['size_kb'] else "Unknown"
                srcs_str = ", ".join([os.path.basename(s) for s in file_info['sources'][:2]]) or "Server Asset"
                f.write(f"| {i} | `{fn}` | {size_str} | [Open PDF]({file_info['url']}) | {srcs_str} |\n")
            f.write("\n")

    print("\nSaved detailed JSON to build/orphaned_pdf_audit.json", flush=True)
    print("Saved detailed Markdown report to ORPHANED_PDF_AUDIT_REPORT.md", flush=True)

if __name__ == '__main__':
    main()
