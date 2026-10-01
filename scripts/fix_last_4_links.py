import csv

rows = []
with open("data/vedavms_documents.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        pdf_url = row.get("PDF_URL", "")
        
        # 1. Telugu exact matches
        if row.get("Language") == "Telugu":
            if "abhisravaNam" in pdf_url or "abhisravanam" in pdf_url:
                row["PDF_URL"] = "https://vedavms.in/docs/telugu/AbhisravaNam%20Telugu.pdf"
            if "Chamaka%20Kramam%20telugu%20Column.pdf" in pdf_url or "Chamaka Kramam telugu Column.pdf" in pdf_url:
                row["PDF_URL"] = "https://vedavms.in/docs/telugu/Chamaka%20Kramam%20Telugu%20Column.pdf"
            if "Rudra%20Kramam%20telugu%20Column.pdf" in pdf_url or "Rudra Kramam telugu Column.pdf" in pdf_url:
                row["PDF_URL"] = "https://vedavms.in/docs/telugu/Rudra%20Kramam%20Telugu%20Column.pdf"

        # 2. Kannada exact matches
        if row.get("Language") == "Kannada":
            if "abhisravaNam" in pdf_url or "abhisravanam" in pdf_url:
                row["PDF_URL"] = "https://vedavms.in/docs/kannada/AbhisravaNam%20Kannada.pdf"

        rows.append(row)

with open("data/vedavms_documents.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

import shutil
shutil.copy2("data/vedavms_documents.csv", "build/vedavms_documents.csv")
print("Updated data/vedavms_documents.csv and build/vedavms_documents.csv")
