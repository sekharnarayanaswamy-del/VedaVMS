import concurrent.futures
import csv
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

BASE = "https://vedavms.in"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Load current CSV to get all rows
rows = []
with open("data/vedavms_documents.csv", "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Loaded {len(rows)} rows from data/vedavms_documents.csv")

def generate_url_variants(url: str) -> list[str]:
    """Generate various casing and path variants for a given URL."""
    parts = urllib.parse.urlsplit(url)
    path = parts.path
    
    # Extract directory and filename
    # e.g. /docs/TSK1-Kramam/TS 1.1 Tamil Krama paatam Corrections.pdf
    match = re.match(r"^(/docs/)([^/]+)/(.*)$", urllib.parse.unquote(path))
    if not match:
        return [url]
    
    prefix, folder, filename = match.groups()
    name_base, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
    
    folder_variants = list(set([
        folder,
        folder.lower(),
        folder.upper(),
        folder.capitalize(),
        folder.replace("-", "_"),
        folder.replace("_", "-"),
    ]))
    
    # For TSK folders: TSK1-Kramam, TSK1-kramam, TSK1_Kramam, tsk1-kramam, TS1-Kramam, TS1-kramam, etc.
    if re.match(r"TSK\d", folder, re.I):
        num = re.search(r"\d", folder).group(0)
        folder_variants.extend([
            f"TSK{num}-Kramam", f"TSK{num}-kramam", f"tsk{num}-kramam", f"TSK{num}_Kramam",
            f"TS{num}-Kramam", f"TS{num}-kramam", f"ts{num}-kramam", f"TSK{num}Kramam",
            f"TSK{num}", f"tsk{num}", f"TS{num}K", f"ts{num}k"
        ])
    
    if "kanva" in folder.lower():
        folder_variants.extend([
            "KanvaPRI", "kanvapri", "Kanvapri", "KANVAPRI", "Kanva_PRI", "kanva_pri",
            "Kanva", "kanva", "KANVA", "Kanva-PRI", "kanva-pri"
        ])

    if "baraha" in folder.lower():
        folder_variants.extend([
            "Baraha", "baraha", "BARAHA", "docs/Baraha", "Baraha/TSK", "Baraha/TSJ", "Baraha/TS"
        ])
        
    if "tu" in folder.lower():
        folder_variants.extend(["TU", "tu", "Tu", "Taittiriya_Upanishad", "Taittiriya-Upanishad"])

    if "ts4-padam" in folder.lower():
        folder_variants.extend(["TS4-Padam", "ts4-padam", "TS4-padam", "TS4_Padam", "ts4_padam", "TS4Padam", "TS-Padam/TS4"])

    # Filename variants
    name_variants = list(set([
        filename,
        filename.lower(),
        filename.upper(),
        filename.title(),
        # Common word casing in Vedic files:
        filename.replace("corrections", "Corrections"),
        filename.replace("Corrections", "corrections"),
        filename.replace("paatam", "Paatam"),
        filename.replace("Paatam", "paatam"),
        filename.replace("krama", "Krama"),
        filename.replace("Krama", "krama"),
        filename.replace("kramam", "Kramam"),
        filename.replace("Kramam", "kramam"),
        filename.replace("pada", "Pada"),
        filename.replace("Pada", "pada"),
        filename.replace("jatai", "Jatai"),
        filename.replace("Jatai", "jatai"),
        filename.replace("ghanam", "Ghanam"),
        filename.replace("Ghanam", "ghanam"),
        filename.replace("Sanskrit", "sanskrit"),
        filename.replace("sanskrit", "Sanskrit"),
        filename.replace("Tamil", "tamil"),
        filename.replace("tamil", "Tamil"),
        filename.replace("Malayalam", "malayalam"),
        filename.replace("malayalam", "Malayalam"),
        filename.replace("Kannada", "kannada"),
        filename.replace("kannada", "Kannada"),
        filename.replace("Telugu", "telugu"),
        filename.replace("telugu", "Telugu"),
        filename.replace("Latin", "latin"),
        filename.replace("latin", "Latin"),
        # Spacing / hyphens
        re.sub(r"\s+", " ", filename),
        filename.replace(" - ", " "),
        filename.replace(" ", "%20"),
        filename.replace(" ", "-"),
        filename.replace(" ", "_"),
    ]))

    # Extension variants
    ext_variants = [f".{ext}", f".{ext.lower()}", f".{ext.upper()}", f".{ext.capitalize()}"]
    if ext.lower() == "docx":
        ext_variants.extend([".doc", ".DOC", ".DOCX", ".docx", ".pdf", ".PDF"])
    if ext.lower() == "pdf":
        ext_variants.extend([".PDF", ".pdf"])

    all_generated = []
    for fld in set(folder_variants):
        for n in set(name_variants):
            n_clean = n
            for e in [".pdf", ".PDF", ".docx", ".DOCX", ".doc", ".DOC"]:
                if n_clean.endswith(e):
                    n_clean = n_clean[:-len(e)]
                    break
            for e in set(ext_variants):
                full_fname = n_clean + e
                quoted_fname = urllib.parse.quote(urllib.parse.unquote(full_fname))
                gen_url = f"{BASE}{prefix}{fld}/{quoted_fname}"
                all_generated.append(gen_url)
    
    return list(dict.fromkeys(all_generated))

def test_url_quick(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': USER_AGENT,
            'Accept': '*/*',
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200 and int(resp.headers.get("Content-Length", "1")) > 100:
                return True
    except Exception:
        pass
    return False

print("Script template ready.")
