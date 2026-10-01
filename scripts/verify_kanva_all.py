import urllib.request
import urllib.parse

print("Testing all 40 Kanva Samhita files in ALL CAPS...")
passed = 0
for i in range(1, 41):
    fname = f"KANVA PRI A{i:02d}.pdf"
    url = f"https://vedavms.in/docs/KanvaPRI/{urllib.parse.quote(fname)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req) as resp:
            print(f"  [200 OK] {fname} ({resp.headers.get('Content-Length')} bytes)")
            passed += 1
    except Exception as e:
        print(f"  [FAILED] {fname} -> {e}")

print(f"\nResult: {passed}/40 Kanva files verified 200 OK!")
