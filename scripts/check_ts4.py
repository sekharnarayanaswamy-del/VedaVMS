import urllib.request
import urllib.parse

print("Checking TS4-Padam files...")
for i in range(1, 8):
    for f in [
        f"TS 4.{i} Tamil Pada Paatam.pdf",
        f"TS 4.{i} Tamil Pada Paatam with Vaakyam.pdf",
        f"TS 4.{i} Tamil.pdf"
    ]:
        url = f"https://vedavms.in/docs/TS4-Padam/{urllib.parse.quote(f)}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req) as resp:
                print(f"200 OK: {f} ({resp.headers.get('Content-Length')} bytes)")
        except Exception:
            pass
