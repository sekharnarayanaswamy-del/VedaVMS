import concurrent.futures
import csv
import re
import urllib.parse
import urllib.request

BASE = "https://vedavms.in"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def probe_url(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,application/pdf,*/*;q=0.8',
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status == 200:
                return True
    except Exception:
        pass
    return False

# Read current CSV
with open("data/vedavms_documents.csv", "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Loaded {len(rows)} rows. Applying casing updates...")

updated_count = 0
for row in rows:
    pdf_url = row.get("PDF_URL", "")
    corr_url = row.get("Corrections_URL", "")

    # 1. Latin (IAST)
    if row.get("Language") == "Latin (IAST)":
        if "Chamaka%20jatai" in pdf_url or "Chamaka jatai" in pdf_url:
            row["PDF_URL"] = "https://vedavms.in/docs/Latin/Chamaka%20Jatai%20Latin.pdf"
            updated_count += 1
        if "Rudra%20kramam" in pdf_url or "Rudra kramam" in pdf_url:
            row["PDF_URL"] = "https://vedavms.in/docs/Latin/Rudra%20Kramam%20Latin%20Column.pdf"
            updated_count += 1
        if "abhisravaNam" in pdf_url or "abhisravanam" in pdf_url:
            row["PDF_URL"] = "https://vedavms.in/docs/Latin/AbhisravaNam%20Latin.pdf"
            updated_count += 1
        if "TS%201.1%20Latin" in pdf_url or "TS 1.1 Latin" in pdf_url:
            row["PDF_URL"] = "https://vedavms.in/docs/Latin/TS%201.1%20Latin%20Pada%20Paatam.docx"
            updated_count += 1

    # 2. Sanskrit Surya Namaskaram
    if row.get("Language") == "Sanskrit":
        if "surya%20namaskaram" in pdf_url or "surya namaskaram" in pdf_url:
            row["PDF_URL"] = "https://vedavms.in/docs/TU/Surya%20Namaskaram%20Sanskrit.pdf"
            updated_count += 1

    # 3. Corrections: TA, TB, ekAgni
    if corr_url:
        # TA Corrections (Capital Corrections)
        if "/docs/TA/" in corr_url and "corrections.pdf" in corr_url:
            row["Corrections_URL"] = corr_url.replace("corrections.pdf", "Corrections.pdf")
            updated_count += 1
        
        # TB Corrections (Capital Corrections)
        if "/docs/TB/" in corr_url and "corrections.pdf" in corr_url:
            row["Corrections_URL"] = corr_url.replace("corrections.pdf", "Corrections.pdf")
            updated_count += 1

        # ekAgni Corrections (lowercase corrections)
        if "/docs/ekAgni/" in corr_url and "Corrections.pdf" in corr_url:
            row["Corrections_URL"] = corr_url.replace("Corrections.pdf", "corrections.pdf")
            updated_count += 1

        # TSK1 to TSK7 Kramam Corrections (Standardize to 'Krama Paatam Corrections.pdf')
        if "/docs/TSK" in corr_url:
            # Replace all variations like 'krama paatam corrections', 'Krama paatam Corrections', etc.
            new_corr = corr_url
            new_corr = re.sub(r"[kK]rama\s*[pP]aatam\s*[cC]orrections\.pdf", "Krama%20Paatam%20Corrections.pdf", new_corr)
            new_corr = re.sub(r"[kK]rama%20[pP]aatam%20[cC]orrections\.pdf", "Krama%20Paatam%20Corrections.pdf", new_corr)
            new_corr = re.sub(r"krama%20Paatam%20Corrections\.pdf", "Krama%20Paatam%20Corrections.pdf", new_corr)
            new_corr = re.sub(r"Krama%20paatam%20corrections\.pdf", "Krama%20Paatam%20Corrections.pdf", new_corr)
            new_corr = re.sub(r"Krama%20paatam%20Corrections\.pdf", "Krama%20Paatam%20Corrections.pdf", new_corr)
            if new_corr != corr_url:
                row["Corrections_URL"] = new_corr
                updated_count += 1

# Save updated CSV
with open("data/vedavms_documents.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

import shutil
shutil.copy2("data/vedavms_documents.csv", "build/vedavms_documents.csv")
print(f"Applied {updated_count} casing corrections to data/vedavms_documents.csv and build/vedavms_documents.csv")
