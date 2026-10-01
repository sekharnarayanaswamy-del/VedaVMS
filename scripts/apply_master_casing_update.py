import csv
import re
import shutil

# Load data/vedavms_documents.csv
with open("data/vedavms_documents.csv", "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Loaded {len(rows)} rows. Applying master casing fixes...")

updated_count = 0
for row in rows:
    pdf_url = row.get("PDF_URL", "")
    corr_url = row.get("Corrections_URL", "")
    lang = row.get("Language", "")

    # 1. Kanva Samhita (ALL CAPS)
    if lang == "Kanva Samhita":
        if "02Kanva%20Prayer.pdf" in pdf_url or "02Kanva Prayer.pdf" in pdf_url:
            row["PDF_URL"] = "https://vedavms.in/docs/KanvaPRI/02KANVA%20PRAYER.pdf"
            updated_count += 1
        else:
            match = re.search(r"Kanva%20PRI%20A(\d{1,2})\.pdf", pdf_url, re.I)
            if match:
                num = int(match.group(1))
                row["PDF_URL"] = f"https://vedavms.in/docs/KanvaPRI/KANVA%20PRI%20A{num:02d}.pdf"
                updated_count += 1

    # 2. Baraha Source (Capital 'Pada Paatam.docx')
    if lang == "Baraha Source":
        if "Pada%20paatam.docx" in pdf_url or "Pada paatam.docx" in pdf_url:
            row["PDF_URL"] = pdf_url.replace("Pada%20paatam.docx", "Pada%20Paatam.docx").replace("Pada paatam.docx", "Pada%20Paatam.docx")
            updated_count += 1

    # 3. Latin (IAST)
    if lang == "Latin (IAST)":
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

    # 4. Sanskrit Surya Namaskaram
    if lang == "Sanskrit":
        if "surya%20namaskaram" in pdf_url or "surya namaskaram" in pdf_url:
            row["PDF_URL"] = "https://vedavms.in/docs/TU/Surya%20Namaskaram%20Sanskrit.pdf"
            updated_count += 1

    # 5. Corrections across TA, TB, ekAgni, TSK
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
            new_corr = corr_url
            new_corr = re.sub(r"[kK]rama\s*[pP]aatam\s*[cC]orrections\.pdf", "Krama%20Paatam%20Corrections.pdf", new_corr)
            new_corr = re.sub(r"[kK]rama%20[pP]aatam%20[cC]orrections\.pdf", "Krama%20Paatam%20Corrections.pdf", new_corr)
            new_corr = re.sub(r"krama%20Paatam%20Corrections\.pdf", "Krama%20Paatam%20Corrections.pdf", new_corr)
            new_corr = re.sub(r"Krama%20paatam%20corrections\.pdf", "Krama%20Paatam%20Corrections.pdf", new_corr)
            new_corr = re.sub(r"Krama%20paatam%20Corrections\.pdf", "Krama%20Paatam%20Corrections.pdf", new_corr)
            if new_corr != corr_url:
                row["Corrections_URL"] = new_corr
                updated_count += 1

# Save updated CSV files
with open("data/vedavms_documents.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

shutil.copy2("data/vedavms_documents.csv", "build/vedavms_documents.csv")
print(f"Applied {updated_count} master casing updates.")
