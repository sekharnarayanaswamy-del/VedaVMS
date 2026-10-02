# Orphaned PDF Audit Report — VedaVMS (`public_html`)

**Generated:** 2026-10-02 20:50:00 IST  
**Target Host:** `https://vedavms.in`  
**Master Reference File:** `data/vedavms_documents.csv`

---

## Executive Summary

| Category | Count | Status | Notes |
|---|---:|:---:|---|
| **Active & Managed in CSV** | **1,576** | ✅ Healthy | All document & correction links return HTTP 200 OK |
| **Vedic Tutorial Articles (Hardcoded in `articles.html`)** | **13** | ✅ Active | Managed directly via `articles.html` |
| **Site Conventions PDF (Hardcoded in `convention.html`)** | **1** | ✅ Active | Managed directly via `convention.html` |
| **Historical Endorsement Letter (Consciously Dropped)** | **1** | ℹ️ Archived | `Letter from Kolatu.pdf` in Siksha directory |
| **Server Duplicate / Case-Variant Copies** | **7** | ℹ️ Mirror Aliases | Canonical versions are actively tracked in CSV |
| **TS 7.4 Ghanam Correction PDFs (Newly Added)** | **3** | ✅ Resolved | Added to CSV Rows 918–920 (`TSG 7.4`) |
| **Broken CSV Links (External / Legacy HTML Reference Links)** | **3** | ℹ️ External Links | 3 historical non-PDF links (`.htm`/`.html`) in Siksha/Parayanam |

---

## 1. Resolved: TS 7.4 Ghanam Corrections (Now in CSV)

These 3 correction PDFs physically exist on the server and have now been added to [`data/vedavms_documents.csv`](data/vedavms_documents.csv):

| # | Language | Section | Title | Live Correction URL |
|---|---|---|---|---|
| 1 | Malayalam | TS Samhita Ghanam | TS 7.4 Ghanam Malayalam | [`https://vedavms.in/docs/TSG7/TS%207.4%20Ghanam%20Malayalam%20Corrections.pdf`](https://vedavms.in/docs/TSG7/TS%207.4%20Ghanam%20Malayalam%20Corrections.pdf) |
| 2 | Sanskrit | TS Samhita Ghanam | TS 7.4 Ghanam Sanskrit | [`https://vedavms.in/docs/TSG7/TS%207.4%20Ghanam%20Sanskrit%20Corrections.pdf`](https://vedavms.in/docs/TSG7/TS%207.4%20Ghanam%20Sanskrit%20Corrections.pdf) |
| 3 | Tamil | TS Samhita Ghanam | TS 7.4 Ghanam Tamil | [`https://vedavms.in/docs/TSG7/TS%207.4%20Ghanam%20Tamil%20Corrections.pdf`](https://vedavms.in/docs/TSG7/TS%207.4%20Ghanam%20Tamil%20Corrections.pdf) |

---

## 2. Hardcoded Site Assets (Managed Outside CSV)

### A. Vedic Tutorial Articles (13 PDFs in `articles.html`)
These 13 PDFs are active tutorial downloads linked on [`articles.html`](articles.html):
1. [`/docs/articles/00Sanskrit Letters.pdf`](https://vedavms.in/docs/articles/00Sanskrit%20Letters.pdf) (371 KB)
2. [`/docs/articles/01ABasics of Veda Recital.pdf`](https://vedavms.in/docs/articles/01ABasics%20of%20Veda%20Recital.pdf) (685 KB)
3. [`/docs/articles/01Basics of Veda Swaras.pdf`](https://vedavms.in/docs/articles/01Basics%20of%20Veda%20Swaras.pdf) (278 KB)
4. [`/docs/articles/02Basics of Veda-Dheerga Swaritam.pdf`](https://vedavms.in/docs/articles/02Basics%20of%20Veda-Dheerga%20Swaritam.pdf) (300 KB)
5. [`/docs/articles/03Basics of Veda-Visarga Sandhi.pdf`](https://vedavms.in/docs/articles/03Basics%20of%20Veda-Visarga%20Sandhi.pdf) (524 KB)
6. [`/docs/articles/04Basics of Veda-Avagraha.pdf`](https://vedavms.in/docs/articles/04Basics%20of%20Veda-Avagraha.pdf) (533 KB)
7. [`/docs/articles/05Basics of Veda-Chandas.pdf`](https://vedavms.in/docs/articles/05Basics%20of%20Veda-Chandas.pdf) (194 KB)
8. [`/docs/articles/06Basics of Veda-Krama Paatam.pdf`](https://vedavms.in/docs/articles/06Basics%20of%20Veda-Krama%20Paatam.pdf) (192 KB)
9. [`/docs/articles/07Basics of Veda-Ghana Paatam.pdf`](https://vedavms.in/docs/articles/07Basics%20of%20Veda-Ghana%20Paatam.pdf) (175 KB)
10. [`/docs/articles/08Basics of Veda-Vowel Sandhi.pdf`](https://vedavms.in/docs/articles/08Basics%20of%20Veda-Vowel%20Sandhi.pdf) (540 KB)
11. [`/docs/articles/09Basics of Veda-Consonant Sandhi.pdf`](https://vedavms.in/docs/articles/09Basics%20of%20Veda-Consonant%20Sandhi.pdf) (610 KB)
12. [`/docs/articles/10Basics of Veda-Jata Paatam.pdf`](https://vedavms.in/docs/articles/10Basics%20of%20Veda-Jata%20Paatam.pdf) (216 KB)
13. [`/docs/articles/11Basics of Veda-Pada Paatam.pdf`](https://vedavms.in/docs/articles/11Basics%20of%20Veda-Pada%20Paatam.pdf) (1,131 KB)

### B. Transliteration Conventions (1 PDF in `convention.html`)
- [`/conventions.pdf`](https://vedavms.in/conventions.pdf) (132 KB)

---

## 3. Consciously Dropped Historical Document

- [`/docs/SIkShA/Letter from Kolatu.pdf`](https://vedavms.in/docs/SIkShA/Letter%20from%20Kolatu.pdf) (924 KB) — Historic endorsement letter; omitted from main document lists by editorial decision.

---

## 4. Server Duplicate & Directory Mirror Aliases (7 Files)

These files exist on the server as duplicate or case-variant copies; their canonical paths are actively managed in the Google Sheet:

| # | Server Mirror File | Size | Canonical CSV Tracked Path |
|---|---|---:|---|
| 1 | [`/docs/Shanti-Japam/Shanti Japam Telugu.pdf`](https://vedavms.in/docs/Shanti-Japam/Shanti%20Japam%20Telugu.pdf) | 745 KB | `/docs/telugu/Shanti Japam Telugu.pdf` |
| 2 | [`/docs/Telugu/AAK-Telugu.pdf`](https://vedavms.in/docs/Telugu/AAK-Telugu.pdf) | 617 KB | `/docs/kannada/AAK-Telugu.pdf` |
| 3 | [`/docs/Telugu/Chamaka Ghanam Telugu.pdf`](https://vedavms.in/docs/Telugu/Chamaka%20Ghanam%20Telugu.pdf) | 349 KB | `/docs/telugu/Chamaka Ghanam Telugu.pdf` |
| 4 | [`/docs/Telugu/Shanti Japam Telugu.pdf`](https://vedavms.in/docs/Telugu/Shanti%20Japam%20Telugu.pdf) | 745 KB | `/docs/telugu/Shanti Japam Telugu.pdf` |
| 5 | [`/docs/tsg6/TS 6.1 Ghanam Sanskrit.pdf`](https://vedavms.in/docs/tsg6/TS%206.1%20Ghanam%20Sanskrit.pdf) | 9,379 KB | `/docs/TSG6/TS 6.1 Ghanam Sanskrit.pdf` |
| 6 | [`/docs/tsg7/TS 7.1 Ghanam Sanskrit.pdf`](https://vedavms.in/docs/tsg7/TS%207.1%20Ghanam%20Sanskrit.pdf) | 2,711 KB | `/docs/TSG7/TS 7.1 Ghanam Sanskrit.pdf` |
| 7 | [`/docs/tsj7/TS 7.1 Jatai Sanskrit.pdf`](https://vedavms.in/docs/tsj7/TS%207.1%20Jatai%20Sanskrit.pdf) | 2,327 KB | `/docs/TSJ7/TS 7.1 Jatai Sanskrit.pdf` |
