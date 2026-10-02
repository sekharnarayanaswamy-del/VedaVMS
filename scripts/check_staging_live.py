import urllib.request
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = [
    'https://new.vedavms.in/index.html',
    'https://vedavms.in/new/index.html',
    'https://vedavms.in/index.html'
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

for url in urls:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = resp.read().decode('utf-8', 'ignore')
            foot = re.search(r'<footer[\s\S]*?</footer>', data)
            sub = re.search(r'<p class="section-subtitle">[^<]*</p>', data)
            print(f"=== {url} (HTTP {resp.status}) ===")
            if sub:
                print("  Subtitle:", sub.group(0))
            if foot:
                lines = foot.group(0).strip().splitlines()
                for line in lines[-4:]:
                    print("  Footer:", line.strip())
    except Exception as e:
        print(f"=== {url} === Error: {e}")
