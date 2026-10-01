#!/usr/bin/env python3
"""
Deep Live Webpage Scrape & Link Audit for https://vedavms.in

Fetches the actual HTML pages directly from the live web server:
1. https://vedavms.in/
2. https://vedavms.in/documents.html
3. https://vedavms.in/about.html
4. https://vedavms.in/articles.html
5. https://vedavms.in/videos.html

Extracts EVERY SINGLE <a href="..."> link physically present on those live pages,
and tests every link to identify ANY broken links (404, 403, 500, etc.).
"""

import concurrent.futures
import html
import re
import urllib.error
import urllib.parse
import urllib.request
import time
from collections import defaultdict

BASE = "https://vedavms.in"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

PAGES_TO_AUDIT = [
    "index.html",
    "documents.html",
    "about.html",
    "articles.html",
    "videos.html"
]

def absolutise(base_url: str, href: str) -> str:
    href = href.strip()
    if href.startswith("mailto:") or href.startswith("tel:") or href.startswith("javascript:") or href == "#":
        return ""
    url = urllib.parse.urljoin(base_url, href)
    parts = urllib.parse.urlsplit(url)
    path = re.sub(r"/{2,}", "/", parts.path)
    # quote spaces properly
    path = urllib.parse.quote(urllib.parse.unquote(path))
    return urllib.parse.urlunsplit(parts._replace(path=path))

def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode('utf-8', 'replace')

def check_link(url: str) -> tuple[str, int, str, int]:
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,application/pdf,*/*;q=0.8',
            'Connection': 'keep-alive'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_len = int(resp.headers.get("Content-Length", 0))
            return url, resp.status, resp.headers.get("Content-Type", ""), content_len
    except urllib.error.HTTPError as e:
        return url, e.code, str(e.reason), 0
    except Exception as e:
        return url, 0, type(e).__name__, 0

def main():
    print("=" * 70)
    print("  DEEP AUDIT OF ACTUAL LIVE HTML PAGES ON VEDAVMS.IN")
    print("=" * 70)
    
    all_discovered_links: dict[str, list[str]] = defaultdict(list) # url -> list of source pages

    for page in PAGES_TO_AUDIT:
        page_url = f"{BASE}/{page}"
        print(f"\nFetching live page: {page_url} ...")
        try:
            content = fetch_html(page_url)
            # Find all <a href="...">
            raw_hrefs = re.findall(r'<a\b[^>]*?href=["\']([^"\']+)["\']', content, re.I)
            print(f"  Found {len(raw_hrefs)} total anchor links on {page}")
            for href in raw_hrefs:
                abs_url = absolutise(page_url, href)
                if abs_url:
                    all_discovered_links[abs_url].append(page)
        except Exception as e:
            print(f"  [ERROR] Failed to fetch {page_url}: {e}")

    total_unique_links = len(all_discovered_links)
    print(f"\nTotal unique links extracted across all live pages: {total_unique_links}")
    print("Testing each link across 12 concurrent workers...\n")

    results = []
    broken_links = []
    passed_count = 0
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(check_link, url): url for url in all_discovered_links.keys()}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            url, status, ctype, clen = future.result()
            results.append((url, status, ctype, clen))
            done += 1
            if done % 100 == 0 or done == total_unique_links:
                print(f"  Checked {done}/{total_unique_links} ({done/total_unique_links*100:.1f}%)")
            if status == 200:
                passed_count += 1
            else:
                broken_links.append((url, status, ctype, all_discovered_links[url]))

    elapsed = time.time() - start_time
    print(f"\nAudit completed in {elapsed:.1f} seconds.")
    print("=" * 70)
    print(f"  RESULTS:")
    print(f"  Passed (200 OK):  {passed_count} / {total_unique_links} ({(passed_count/total_unique_links)*100:.1f}%)")
    print(f"  Broken Links:     {len(broken_links)} / {total_unique_links}")
    print("=" * 70)

    if broken_links:
        print(f"\n[!] LIST OF ALL BROKEN LINKS PHYSICALLY ON THE LIVE SITE:\n")
        for url, status, error, sources in sorted(broken_links, key=lambda x: (x[1], x[0])):
            decoded_url = urllib.parse.unquote(url)
            src_str = ", ".join(sorted(set(sources)))
            print(f"  HTTP {status} [{error}] on ({src_str}):\n    {decoded_url}\n")
    else:
        print("\n[SUCCESS] 100% of all links on the live website are working perfectly!")

if __name__ == "__main__":
    main()
