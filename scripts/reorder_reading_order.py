import csv
import os
import re
import shutil
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "vedavms_documents.csv")
BUILD_CSV = os.path.join(ROOT, "build", "vedavms_documents.csv")

def doc_sort_key(row: dict):
    title = (row.get("Title") or "").strip()
    tl = title.lower()
    
    # 1. Indexes and Introductory Reference material come FIRST (at top of section)
    if "index" in tl and "alpha" in tl:
        return (0, 1, 0, 0, 0, title)
    if "index" in tl and ("dasini" in tl or "panchaati" in tl or "panchati" in tl or "panchat" in tl):
        return (0, 2, 0, 0, 0, title)
    if "index" in tl:
        return (0, 3, 0, 0, 0, title)
    if "notes and symbols" in tl:
        return (0, 4, 0, 0, 0, title)
    if "prayer" in tl:
        return (0, 5, 0, 0, 0, title)
    if "first and last" in tl:
        return (0, 6, 0, 0, 0, title)
    if "comparison" in tl:
        return (0, 7, 0, 0, 0, title)
        
    # 2. Ashtakam / Prapatakam (Brahmanam)
    # e.g. ashtakam 1 - prapAtakam 1-4
    m_ash = re.search(r'ashtakam\s*(\d+)', tl)
    if m_ash:
        ash_num = int(m_ash.group(1))
        m_prap = re.search(r'prap[aā]t[aā]k?am\s*(\d+)(?:\s*-\s*(\d+))?', tl)
        p1 = int(m_prap.group(1)) if m_prap else 0
        p2 = int(m_prap.group(2)) if m_prap and m_prap.group(2) else p1
        return (1, ash_num, p1, p2, 0, title)
        
    # 3. Aranyakam Prapatakam
    # e.g. prapAtam 1 - 4
    m_ar_prap = re.search(r'prap[aā]t[aā]m?\s*(\d+)(?:\s*-\s*(\d+))?', tl)
    if m_ar_prap:
        p1 = int(m_ar_prap.group(1))
        p2 = int(m_ar_prap.group(2)) if m_ar_prap.group(2) else p1
        return (1, 0, p1, p2, 0, title)

    # 4. Samhita Kandam (e.g. kANDam 1 or Kandam 1)
    m_kan = re.search(r'k[aā]ndam\s*(\d+)', tl)
    if m_kan:
        kan_num = int(m_kan.group(1))
        return (1, kan_num, 0, 0, 0, title)

    # 5. TS X.Y (Pada, Krama, Jata, Ghana)
    m_ts = re.search(r'TS\s*(\d+)\.(\d+)', title, re.I)
    if m_ts:
        k = int(m_ts.group(1))
        p = int(m_ts.group(2))
        return (1, k, p, 0, 0, title)

    # 6. Numbered items: 1), 2), 2A), 3), 3A)
    m_num = re.match(r'^(\d+)([A-Za-z]?)\)', title)
    if m_num:
        n = int(m_num.group(1))
        sub = m_num.group(2) or ''
        sub_ord = ord(sub.upper()[0]) if sub else 0
        return (1, n, sub_ord, 0, 0, title)

    # 7. Kanva A01 - A40
    m_kanva = re.search(r'A(\d+)', title, re.I)
    if m_kanva:
        return (1, int(m_kanva.group(1)), 0, 0, 0, title)

    return (2, 0, 0, 0, 0, title)


def main():
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"Read {len(rows)} rows from {CSV_PATH}")

    # Group by (Language, Section) while preserving Section appearance order
    grouped = defaultdict(list)
    section_order = []
    
    for r in rows:
        key = (r["Language"], r["Section"])
        if key not in grouped:
            section_order.append(key)
        grouped[key].append(r)

    reordered_rows = []
    for key in section_order:
        sec_rows = grouped[key]
        sorted_sec_rows = sorted(sec_rows, key=doc_sort_key)
        reordered_rows.extend(sorted_sec_rows)

    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reordered_rows)

    if os.path.exists(BUILD_CSV):
        shutil.copy2(CSV_PATH, BUILD_CSV)

    print(f"Successfully reordered {len(reordered_rows)} rows in reading order.")

if __name__ == "__main__":
    main()
