import urllib.request
import re

extra_pages = [
    ("docs_tsj.html", "Pilot Project - TS Samhita Jatai"),
    ("docs_tsg.html", "Pilot Project - TS Samhita Ghanam"),
    ("docs_SikShA.html", "SikShA and Lessons"),
    ("docs_Kanva.html", "Kanva Samhita Manuscript"),
    ("docs_inprogress.html", "Pilot Projects & in Progress"),
    ("docs_latin.html", "Latin (IAST)"),
    ("docs_baraha.html", "Baraha Source"),
]

for page, label in extra_pages:
    url = f"https://vedavms.in/{page}"
    try:
        with urllib.request.urlopen(url) as resp:
            content = resp.read().decode("utf-8", "replace")
        pdf_links = re.findall(r'<a\b[^>]*?href=["\']([^"\']+\.pdf)["\'][^>]*>(.*?)</a>', content, re.I | re.S)
        audio_links = re.findall(r'<a\b[^>]*?href=["\']([^"\']+\.(?:mp3|wav|ogg))["\'][^>]*>(.*?)</a>', content, re.I | re.S)
        print(f"\n=== {label} ({page}) ===")
        print(f"  Total PDF links found: {len(pdf_links)}")
        print(f"  Total Audio links found: {len(audio_links)}")
        for href, text in pdf_links[:5]:
            t = re.sub(r'<[^>]+>', '', text).strip()
            print(f"    PDF: {t} -> {href}")
    except Exception as e:
        print(f"\n=== {label} ({page}) === Error: {e}")
