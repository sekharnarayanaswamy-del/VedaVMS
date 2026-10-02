#!/usr/bin/env python3
"""
Exhaustive Combinatorial PDF Scanner & Fuzzer for https://vedavms.in

Generates all possible directory and filename variations across all Vedic categories,
scripts, numbers (Kandams/Prapathakas/Anuvakas), casing variants, and version suffixes,
then tests each against the live server to discover EVERY hidden/unreferenced PDF.
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

LANGUAGES = ["Sanskrit", "Tamil", "Malayalam", "Kannada", "Telugu", "Latin", "English"]

# Candidate folder mappings (Canonical -> List of case & naming variants)
FOLDER_VARIANTS = {
    "TSG": lambda k: [f"TSG{k}", f"tsg{k}", f"TSG_{k}", f"tsg_{k}", f"docs/TSG{k}", f"docs/tsg{k}"],
    "TSJ": lambda k: [f"TSJ{k}", f"tsj{k}", f"TSJ_{k}", f"tsj_{k}", f"docs/TSJ{k}", f"docs/tsj{k}"],
    "TSK": lambda k: [f"TSK{k}-Kramam", f"tsk{k}-kramam", f"TSK{k}-kramam", f"tsk{k}-Kramam", f"TSK{k}", f"tsk{k}"],
    "TSP": lambda k: [f"TS{k}-Padam", f"ts{k}-padam", f"TS{k}-padam", f"ts{k}-Padam", f"TS{k}", f"ts{k}"],
}

OTHER_FOLDERS = [
    "TB", "tb", "TA", "ta", "TU", "tu", "US", "us", "TS", "ts",
    "SIkShA", "SikShA", "siksha", "SIKSHA", "Baraha", "baraha",
    "kannada", "Kannada", "telugu", "Telugu", "Latin", "latin", "English", "english",
    "Shanti-Japam", "shanti-japam", "Shanti_Japam", "Shiva-Stuti", "shiva-stuti", "Siva-Stuti", "siva-stuti",
    "KanvaPRI", "kanvapri", "Kanva", "kanva", "abhishravaNa", "Abhisravana", "ekAgni", "Ekagni", "Pilot_Projects"
]

def generate_fuzz_urls():
    candidates = set()

    # 1. TS Samhita Padam, Kramam, Jatai, Ghanam across Kandams 1..7, Anuvakas 1..8
    # TS Kandam -> max anuvakas/prapathakas
    kandam_limits = {1: 8, 2: 6, 3: 5, 4: 7, 5: 7, 6: 6, 7: 5}

    for k, max_a in kandam_limits.items():
        for a in range(1, max_a + 1):
            # Padam
            for fld in FOLDER_VARIANTS["TSP"](k):
                for lang in LANGUAGES:
                    for sfx in ["", " with Vaakyam", " Pada Paatam", " Pada Paatam with Vaakyam", " Padam"]:
                        candidates.add(f"docs/{fld}/TS {k}.{a} {lang}{sfx}.pdf")
                        candidates.add(f"docs/{fld}/TS {k}.{a} {lang} Pada Paatam Corrections.pdf")
                        candidates.add(f"docs/{fld}/TS {k}.{a} {lang} Corrections.pdf")

            # Kramam
            for fld in FOLDER_VARIANTS["TSK"](k):
                for lang in LANGUAGES:
                    for sfx in ["", " Kramam", " Krama Paatam"]:
                        candidates.add(f"docs/{fld}/TS {k}.{a} Kramam {lang}.pdf")
                        candidates.add(f"docs/{fld}/TS {k}.{a} {lang} Kramam.pdf")
                        candidates.add(f"docs/{fld}/TS {k}.{a} {lang} Krama Paatam.pdf")
                        candidates.add(f"docs/{fld}/TS {k}.{a} {lang} Krama Paatam Corrections.pdf")
                        candidates.add(f"docs/{fld}/TS {k}.{a} {lang} Kramam Corrections.pdf")
                        candidates.add(f"docs/{fld}/TS {k}.{a} {lang} Corrections.pdf")

            # Jatai
            for fld in FOLDER_VARIANTS["TSJ"](k):
                for lang in LANGUAGES:
                    candidates.add(f"docs/{fld}/TS {k}.{a} Jatai {lang}.pdf")
                    candidates.add(f"docs/{fld}/TS {k}.{a} {lang} Jatai.pdf")
                    candidates.add(f"docs/{fld}/TS {k}.{a} Jatai {lang} Corrections.pdf")
                    candidates.add(f"docs/{fld}/TS {k}.{a} {lang} Jatai Corrections.pdf")
                    candidates.add(f"docs/{fld}/TS {k}.{a} {lang} Corrections.pdf")

            # Ghanam
            for fld in FOLDER_VARIANTS["TSG"](k):
                for lang in LANGUAGES:
                    candidates.add(f"docs/{fld}/TS {k}.{a} Ghanam {lang}.pdf")
                    candidates.add(f"docs/{fld}/TS {k}.{a} {lang} Ghanam.pdf")
                    candidates.add(f"docs/{fld}/TS {k}.{a} Ghanam {lang} Corrections.pdf")
                    candidates.add(f"docs/{fld}/TS {k}.{a} {lang} Ghanam Corrections.pdf")
                    candidates.add(f"docs/{fld}/TS {k}.{a} {lang} Corrections.pdf")

    # 2. Taittiriya Brahmanam, Aranyakam, Upanishad, Udaka Shanti, Shanti Japam across all folders
    for fld in OTHER_FOLDERS:
        for lang in LANGUAGES:
            # Shanti Japam
            candidates.add(f"docs/{fld}/Shanti Japam {lang}.pdf")
            candidates.add(f"docs/{fld}/Shanti Japam {lang} Corrections.pdf")
            candidates.add(f"docs/{fld}/Shanti_Japam_{lang}.pdf")
            
            # Udaka Shanti
            candidates.add(f"docs/{fld}/Udaka Shanti {lang}.pdf")
            candidates.add(f"docs/{fld}/Udaka Shanti {lang} Corrections.pdf")
            candidates.add(f"docs/{fld}/Udaka Shanti Anushangam {lang}.pdf")
            candidates.add(f"docs/{fld}/Udaka Shanti Anushangam {lang} Corrections.pdf")

            # Siva Stuti
            candidates.add(f"docs/{fld}/Siva Stuti {lang}.pdf")
            candidates.add(f"docs/{fld}/Shiva Stuti {lang}.pdf")
            candidates.add(f"docs/{fld}/Siva Stuti {lang} Corrections.pdf")
            candidates.add(f"docs/{fld}/Shiva Stuti {lang} Corrections.pdf")
            candidates.add(f"docs/{fld}/Siva Stuti {lang} with Svaram.pdf")

            # Rudra & Chamaka
            candidates.add(f"docs/{fld}/Rudra Ghanam {lang}.pdf")
            candidates.add(f"docs/{fld}/Chamaka Ghanam {lang}.pdf")
            candidates.add(f"docs/{fld}/Rudra Kramam {lang} Column.pdf")
            candidates.add(f"docs/{fld}/Chamaka Kramam {lang} Column.pdf")
            candidates.add(f"docs/{fld}/AAK-{lang}.pdf")
            candidates.add(f"docs/{fld}/AbhisravaNam {lang}.pdf")

            # Taittiriya Upanishad
            candidates.add(f"docs/{fld}/Taittiriya Upanishad {lang}.pdf")
            candidates.add(f"docs/{fld}/Taittiriya Upanishad {lang} Corrections.pdf")
            for tu_num in [1, 2, 3]:
                candidates.add(f"docs/{fld}/TU {tu_num} {lang}.pdf")
                candidates.add(f"docs/{fld}/TU {tu_num} {lang} Corrections.pdf")

            # Taittiriya Aranyakam (TA 1..8)
            for ta_num in range(1, 9):
                candidates.add(f"docs/{fld}/TA {ta_num} {lang}.pdf")
                candidates.add(f"docs/{fld}/TA {ta_num} {lang} Corrections.pdf")
                candidates.add(f"docs/{fld}/TA{ta_num} {lang}.pdf")

            # Taittiriya Brahmanam (TB 1.1 - 3.12)
            for b_k in [1, 2, 3]:
                for b_p in range(1, 13):
                    candidates.add(f"docs/{fld}/TB {b_k}.{b_p} {lang}.pdf")
                    candidates.add(f"docs/{fld}/TB {b_k}.{b_p} {lang} Corrections.pdf")
                    candidates.add(f"docs/{fld}/TB{b_k}.{b_p} {lang}.pdf")

            # TS Samhita Kandams (TS 1..7)
            for ts_k in range(1, 8):
                candidates.add(f"docs/{fld}/TS{ts_k} {lang}.pdf")
                candidates.add(f"docs/{fld}/TS {ts_k} {lang}.pdf")
                candidates.add(f"docs/{fld}/TS{ts_k} {lang} Pada Paatam.pdf")

    # Normalize all generated URLs
    full_urls = set()
    for rel in candidates:
        rel_clean = rel.lstrip('/')
        # Replace double slashes if any
        rel_clean = re.sub(r'/{2,}', '/', rel_clean)
        full_urls.add(f"{BASE}/{urllib.parse.quote(rel_clean)}")

    return full_urls

def check_single_url(url: str):
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
    print("1. Generating exhaustive candidate permutations across all folders & Vedic books...", flush=True)
    fuzz_urls = generate_fuzz_urls()
    print(f"   Generated {len(fuzz_urls)} total candidate URLs to probe.", flush=True)

    # Load master CSV
    csv_path = os.path.join('data', 'vedavms_documents.csv')
    csv_norm_urls = set()
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r.get('PDF_URL'):
                csv_norm_urls.add(r['PDF_URL'].strip())
                # Also unquoted lowercase
                csv_norm_urls.add(urllib.parse.unquote(r['PDF_URL'].strip()).lower())
            if r.get('Corrections_URL'):
                csv_norm_urls.add(r['Corrections_URL'].strip())
                csv_norm_urls.add(urllib.parse.unquote(r['Corrections_URL'].strip()).lower())

    print(f"\n2. Scanning server with 32 parallel workers...", flush=True)
    start = time.time()
    live_found = []
    done = 0
    total = len(fuzz_urls)

    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
        futures = {executor.submit(check_single_url, u): u for u in fuzz_urls}
        for f in concurrent.futures.as_completed(futures):
            url, status, clen = f.result()
            if status == 200 and clen > 0:
                live_found.append((url, clen))
            done += 1
            if done % 1000 == 0 or done == total:
                print(f"   Scanned {done}/{total} permutations | Found {len(live_found)} live PDFs ({time.time() - start:.1f}s)...", flush=True)

    print("\n" + "=" * 80, flush=True)
    print(f"Deep Fuzzing Scan Completed in {time.time() - start:.1f}s!", flush=True)
    print(f"Total Live PDFs Discovered by Fuzzer: {len(live_found)}", flush=True)

    # Classify against CSV
    fuzzer_in_csv = []
    fuzzer_orphaned = []

    for url, clen in sorted(live_found, key=lambda x: x[0]):
        unq_lower = urllib.parse.unquote(url).lower()
        if (url in csv_norm_urls) or (unq_lower in csv_norm_urls):
            fuzzer_in_csv.append((url, clen))
        else:
            fuzzer_orphaned.append((url, clen))

    print(f"✅ In Master CSV:            {len(fuzzer_in_csv)}", flush=True)
    print(f"⚠️  Orphaned / Unreferenced: {len(fuzzer_orphaned)}", flush=True)
    print("=" * 80, flush=True)

    if fuzzer_orphaned:
        print("\nDiscovered Orphaned / Mirror PDFs on Server:")
        for u, clen in fuzzer_orphaned:
            unq = urllib.parse.unquote(urllib.parse.urlsplit(u).path)
            print(f"  [{clen//1024:>5} KB] {unq} -> {u}")

    # Save to json
    with open('build/fuzzer_discovered_orphans.json', 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S IST"),
            "total_scanned": total,
            "total_live": len(live_found),
            "orphaned_count": len(fuzzer_orphaned),
            "orphaned_files": [
                {
                    "url": u,
                    "path": urllib.parse.unquote(urllib.parse.urlsplit(u).path),
                    "size_kb": clen // 1024
                }
                for u, clen in fuzzer_orphaned
            ]
        }, f, indent=2)

if __name__ == '__main__':
    main()
