import urllib.request
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

for label, url in [("Production", "https://vedavms.in/index.html"), ("Staging", "https://new.vedavms.in/index.html")]:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8', 'replace')
            
        months = re.findall(r'<div class="category-header"[^>]*>[\s\S]*?<h3>[\s\S]*?([A-Za-z]+\s+20\d\d)', content)
        subtitle = re.findall(r'<p class="section-subtitle">(.*?)</p>', content)
        print(f"\n=== {label} ({url}) ===")
        print(f"  Subtitle: {subtitle}")
        print(f"  Months: {months}")
    except Exception as e:
        print(f"\n=== {label} ({url}) === Error: {e}")
