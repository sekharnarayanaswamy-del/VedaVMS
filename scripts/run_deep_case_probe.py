import concurrent.futures
import csv
import re
import urllib.error
import urllib.parse
import urllib.request
import time

BASE = "https://vedavms.in"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def probe_url(url: str) -> tuple[str, bool, int]:
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,application/pdf,*/*;q=0.8',
            'Connection': 'keep-alive',
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status == 200:
                length = int(resp.headers.get("Content-Length", 0))
                return url, True, length
    except Exception:
        pass
    return url, False, 0

# 1. Probe Latin files
print("=== Probing Latin (IAST) Files ===")
latin_candidates = [
    # Chamaka jatai Latin
    "docs/Latin/Chamaka Jatai Latin.pdf", "docs/latin/Chamaka Jatai Latin.pdf", "docs/Latin/Chamaka jatai Latin.pdf",
    "docs/Latin/Chamaka_Jatai_Latin.pdf", "docs/Latin/Chamaka%20Jatai%20Latin.pdf", "docs/Latin/Chamaka Jatai.pdf",
    
    # Rudra kramam Latin Column
    "docs/Latin/Rudra Kramam Latin Column.pdf", "docs/latin/Rudra Kramam Latin Column.pdf", "docs/Latin/Rudra kramam Latin Column.pdf",
    "docs/Latin/Rudra Kramam Column Latin.pdf", "docs/Latin/Rudra Kramam Column.pdf", "docs/Latin/Rudra_Kramam_Latin_Column.pdf",
    
    # abhisravanam Latin
    "docs/Latin/AbhisravaNam Latin.pdf", "docs/Latin/abhisravaNam Latin.pdf", "docs/latin/AbhisravaNam Latin.pdf",
    "docs/Latin/abhisravanam Latin.pdf", "docs/Latin/Abhisravanam Latin.pdf", "docs/Latin/AbhishravaNam Latin.pdf",

    # TS 1.1 Latin pada paatam (.docx vs .pdf vs .doc)
    "docs/Latin/TS 1.1 Latin Pada Paatam.docx", "docs/Latin/TS 1.1 Latin pada paatam.docx",
    "docs/Latin/TS 1.1 Latin Pada Paatam.pdf", "docs/Latin/TS 1.1 Latin pada paatam.pdf",
    "docs/Latin/TS 1.1 Latin Pada Paatam.doc", "docs/latin/TS 1.1 Latin Pada Paatam.pdf",
    "docs/Latin/TS 1.1 Latin Pada Patam.pdf", "docs/Latin/TS 1.1 Latin Pada Patam.docx",
]

for c in latin_candidates:
    url = f"{BASE}/{urllib.parse.quote(c)}"
    _, ok, length = probe_url(url)
    if ok:
        print(f"  FOUND: {c} ({length} bytes)")

# 2. Probe Sanskrit and Tamil single missing files
print("\n=== Probing Sanskrit & Tamil Single Files ===")
single_candidates = [
    # surya namaskaram Sanskrit
    "docs/TU/Surya Namaskaram Sanskrit.pdf", "docs/TU/surya namaskaram Sanskrit.pdf", "docs/TU/Surya namaskara mantrA Sanskrit.pdf",
    "docs/TU/surya namaskara mantrA Sanskrit.pdf", "docs/tu/Surya Namaskaram Sanskrit.pdf", "docs/TU/Surya%20Namaskaram%20Sanskrit.pdf",
    "docs/TU/surya_namaskaram_Sanskrit.pdf", "docs/TU/SuryaNamaskaramSanskrit.pdf", "docs/TU/surya namaskaram.pdf",
    "docs/TU/Surya Namaskara Mantram Sanskrit.pdf", "docs/TU/Surya Namaskaram - Sanskrit.pdf",
    
    # TS 4.5 Tamil Pada Paatam with Vaakyam
    "docs/TS4-Padam/TS 4.5 Tamil Pada Paatam with Vaakyam.pdf", "docs/TS4-Padam/TS 4.5 Tamil Pada Paatam With Vaakyam.pdf",
    "docs/TS4-Padam/TS 4.5 Tamil Pada Paatam with vaakyam.pdf", "docs/TS4-Padam/TS 4.5 Tamil Pada Paatam with Vakyam.pdf",
    "docs/ts4-padam/TS 4.5 Tamil Pada Paatam with Vaakyam.pdf", "docs/TS4-Padam/TS 4.5 Tamil Pada Paatam.pdf",
    "docs/TS4-Padam/TS 4.5 Tamil Pada Patam with Vaakyam.pdf", "docs/TS4-Padam/TS 4.5 Tamil Pada Patam.pdf",
    "docs/TS4-Padam/TS 4.5 Tamil Pada Paatam-with Vaakyam.pdf", "docs/TS4-Padam/TS 4.5 Tamil Pada Paatam (with Vaakyam).pdf"
]

for c in single_candidates:
    url = f"{BASE}/{urllib.parse.quote(c)}"
    _, ok, length = probe_url(url)
    if ok:
        print(f"  FOUND: {c} ({length} bytes)")

# 3. Probe Kanva Samhita Folder and files
print("\n=== Probing Kanva Samhita Variations ===")
kanva_candidates = []
kanva_folders = [
    "KanvaPRI", "kanvapri", "Kanvapri", "Kanva_PRI", "Kanva-PRI",
    "Kanva", "kanva", "KanvaSamhita", "kanvasamhita", "docs/KanvaPRI"
]
kanva_files = [
    "02Kanva Prayer.pdf", "02Kanva prayer.pdf", "02-Kanva-Prayer.pdf", "02 Kanva Prayer.pdf", "Kanva Prayer.pdf",
    "Kanva PRI A01.pdf", "Kanva PRI A1.pdf", "Kanva-PRI-A01.pdf", "Kanva_PRI_A01.pdf", "Kanva PRI 01.pdf", "Kanva A01.pdf"
]

for fld in kanva_folders:
    for fname in kanva_files:
        kanva_candidates.append(f"docs/{fld}/{fname}")

for c in kanva_candidates:
    url = f"{BASE}/{urllib.parse.quote(c)}"
    _, ok, length = probe_url(url)
    if ok:
        print(f"  FOUND: {c} ({length} bytes)")

# 4. Probe TA, TB, ekAgni Corrections
print("\n=== Probing TA, TB, ekAgni Corrections ===")
corr_candidates = [
    # TA Malayalam
    "docs/TA/TA 1-4 Malayalam corrections.pdf", "docs/TA/TA 1-4 Malayalam Corrections.pdf",
    "docs/TA/TA 5-6 Malayalam corrections.pdf", "docs/TA/TA 5-6 Malayalam Corrections.pdf",
    "docs/TA/TA 7-8 Malayalam corrections.pdf", "docs/TA/TA 7-8 Malayalam Corrections.pdf",
    "docs/TA/TA 1-4 Malayalam.pdf", "docs/ta/TA 1-4 Malayalam Corrections.pdf",
    
    # TB Malayalam
    "docs/TB/TB 1.1-1.4 Malayalam corrections.pdf", "docs/TB/TB 1.1-1.4 Malayalam Corrections.pdf",
    "docs/TB/TB 1.5-1.8 Malayalam corrections.pdf", "docs/TB/TB 1.5-1.8 Malayalam Corrections.pdf",
    "docs/TB/TB 2.1-2.4 Malayalam corrections.pdf", "docs/TB/TB 2.1-2.4 Malayalam Corrections.pdf",
    "docs/TB/TB 2.5-2.8 Malayalam corrections.pdf", "docs/TB/TB 2.5-2.8 Malayalam Corrections.pdf",
    "docs/TB/TB 3.1-3.6 Malayalam corrections.pdf", "docs/TB/TB 3.1-3.6 Malayalam Corrections.pdf",
    "docs/TB/TB 3.7-3.12 Malayalam corrections.pdf", "docs/TB/TB 3.7-3.12 Malayalam Corrections.pdf",

    # TA Tamil
    "docs/TA/TA 1-4 Tamil corrections.pdf", "docs/TA/TA 1-4 Tamil Corrections.pdf",
    "docs/TA/TA 5-6 Tamil corrections.pdf", "docs/TA/TA 5-6 Tamil Corrections.pdf",
    "docs/TA/TA 7-8 Tamil corrections.pdf", "docs/TA/TA 7-8 Tamil Corrections.pdf",

    # TB Tamil
    "docs/TB/TB 1.1-1.4 Tamil corrections.pdf", "docs/TB/TB 1.1-1.4 Tamil Corrections.pdf",
    "docs/TB/TB 1.5-1.8 Tamil corrections.pdf", "docs/TB/TB 1.5-1.8 Tamil Corrections.pdf",
    "docs/TB/TB 2.1-2.4 Tamil corrections.pdf", "docs/TB/TB 2.1-2.4 Tamil Corrections.pdf",
    "docs/TB/TB 2.5-2.8 Tamil corrections.pdf", "docs/TB/TB 2.5-2.8 Tamil Corrections.pdf",
    "docs/TB/TB 3.1-3.6 Tamil corrections.pdf", "docs/TB/TB 3.1-3.6 Tamil Corrections.pdf",
    "docs/TB/TB 3.7-3.12 Tamil corrections.pdf", "docs/TB/TB 3.7-3.12 Tamil Corrections.pdf",

    # ekAgni
    "docs/ekAgni/Ekaagni Kaandam Sanskrit Corrections.pdf", "docs/ekAgni/Ekaagni Kaandam Sanskrit corrections.pdf",
    "docs/ekAgni/Ekaagni Kaandam Tamil Corrections.pdf", "docs/ekAgni/Ekaagni Kaandam Tamil corrections.pdf",
    "docs/ekAgni/Ekaagni Kaandam Malayalam Corrections.pdf", "docs/ekAgni/Ekaagni Kaandam Malayalam corrections.pdf",
    "docs/ekAgni/Ekaagni Kaandam Sanskrit.pdf", "docs/ekagni/Ekaagni Kaandam Sanskrit Corrections.pdf",
    "docs/ekAgni/Ekagni Kaandam Sanskrit Corrections.pdf", "docs/ekAgni/Ekaagni_Kaandam_Sanskrit_Corrections.pdf"
]

for c in corr_candidates:
    url = f"{BASE}/{urllib.parse.quote(c)}"
    _, ok, length = probe_url(url)
    if ok:
        print(f"  FOUND: {c} ({length} bytes)")

# 5. Probe Kramam Corrections (TSK1 through TSK7)
print("\n=== Probing TSK Kramam Corrections ===")
tsk_samples = []
for k in range(1, 8):
    for lang in ["Sanskrit", "Tamil", "Malayalam"]:
        for p in range(1, 4):
            tsk_samples.extend([
                f"docs/TSK{k}-Kramam/TS {k}.{p} {lang} Krama paatam Corrections.pdf",
                f"docs/TSK{k}-Kramam/TS {k}.{p} {lang} Krama Paatam Corrections.pdf",
                f"docs/TSK{k}-Kramam/TS {k}.{p} {lang} krama paatam corrections.pdf",
                f"docs/TSK{k}-Kramam/TS {k}.{p} {lang} krama Paatam Corrections.pdf",
                f"docs/TSK{k}-Kramam/TS {k}.{p} {lang} Krama paatam corrections.pdf",
                f"docs/TSK{k}-Kramam/TS {k}.{p} {lang} Kramam Corrections.pdf",
                f"docs/TSK{k}-Kramam/TS {k}.{p} {lang} Kramam corrections.pdf",
                f"docs/TSK{k}-Kramam/TS {k}.{p} {lang} Krama Patam Corrections.pdf",
                f"docs/TSK{k}-Kramam/TS {k}.{p} {lang} krama patam corrections.pdf",
                f"docs/TS{k}-Kramam/TS {k}.{p} {lang} Krama paatam Corrections.pdf",
                f"docs/TSK{k}/TS {k}.{p} {lang} Krama paatam Corrections.pdf",
            ])

found_tsk = 0
for c in tsk_samples:
    url = f"{BASE}/{urllib.parse.quote(c)}"
    _, ok, length = probe_url(url)
    if ok:
        print(f"  FOUND: {c} ({length} bytes)")
        found_tsk += 1

print(f"\nProbing complete. Total TSK found: {found_tsk}")
