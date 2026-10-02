import csv
import shutil

CSV_PATH = "data/vedavms_documents.csv"
BUILD_CSV = "build/vedavms_documents.csv"

with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

updated_count = 0
for r in rows:
    lang = r.get("Language", "").strip()
    title = r.get("Title", "").strip()
    
    # 1. Siva Stuti updates (Sep 30, 2026)
    if lang == "Baraha Source" and "Siva Stuti - Baraha Encoding" in title:
        r["Version"] = "V2.0"
        r["Date"] = "Sep 30, 2026"
        r["PDF_URL"] = "https://vedavms.in/docs/Baraha/Siva%20Stuti%20Baraha.docx"
        updated_count += 1
    elif lang == "Malayalam" and "Siva stuti - Malayalam" in title:
        r["Version"] = "V5.0"
        r["Date"] = "Sep 30, 2026"
        r["PDF_URL"] = "https://vedavms.in/docs/Shiva-Stuti/Siva%20Stuti%20Malayalam.pdf"
        r["Corrections_URL"] = "https://vedavms.in/docs/Shiva-Stuti/Siva%20Stuti%20Malayalam%20Corrections.pdf"
        updated_count += 1
    elif lang == "Sanskrit" and "Siva Stuti - Sanskrit" in title:
        r["Version"] = "V5.0"
        r["Date"] = "Sep 30, 2026"
        r["PDF_URL"] = "https://vedavms.in/docs/Shiva-Stuti/Siva%20Stuti%20Sanskrit.pdf"
        r["Corrections_URL"] = "https://vedavms.in/docs/Shiva-Stuti/Siva%20Stuti%20Sanskrit%20Corrections.pdf"
        updated_count += 1
    elif lang == "Tamil" and "Siva stuti - Tamil" in title:
        r["Version"] = "V5.0"
        r["Date"] = "Sep 30, 2026"
        r["PDF_URL"] = "https://vedavms.in/docs/Shiva-Stuti/Siva%20Stuti%20Tamil.pdf"
        r["Corrections_URL"] = "https://vedavms.in/docs/Shiva-Stuti/Siva%20Stuti%20Tamil%20Corrections.pdf"
        updated_count += 1

    # 2. TS 7.4 Jatai updates (August 31, 2026)
    elif lang == "TS Samhita Jatai" and title == "TS 7.4 Jatai Malayalam":
        r["Version"] = "Ver 1.0"
        r["Date"] = "Aug 31, 2026"
        r["PDF_URL"] = "https://vedavms.in/docs/TSJ7/TS%207.4%20Jatai%20Malayalam.pdf"
        r["Corrections_URL"] = "https://vedavms.in/docs/TSJ7/TS%207.4%20Jatai%20Malayalam%20Corrections.pdf"
        updated_count += 1
    elif lang == "TS Samhita Jatai" and title == "TS 7.4 Jatai Sanskrit":
        r["Version"] = "Ver 1.0"
        r["Date"] = "Aug 31, 2026"
        r["PDF_URL"] = "https://vedavms.in/docs/TSJ7/TS%207.4%20Jatai%20Sanskrit.pdf"
        r["Corrections_URL"] = "https://vedavms.in/docs/TSJ7/TS%207.4%20Jatai%20Sanskrit%20Corrections.pdf"
        updated_count += 1
    elif lang == "TS Samhita Jatai" and title == "TS 7.4 Jatai Tamil":
        r["Version"] = "Ver 1.0"
        r["Date"] = "Aug 31, 2026"
        r["PDF_URL"] = "https://vedavms.in/docs/TSJ7/TS%207.4%20Jatai%20Tamil.pdf"
        r["Corrections_URL"] = "https://vedavms.in/docs/TSJ7/TS%207.4%20Jatai%20Tamil%20Corrections.pdf"
        updated_count += 1

with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

shutil.copy2(CSV_PATH, BUILD_CSV)
print(f"Applied {updated_count} updates to {CSV_PATH} and {BUILD_CSV}")
