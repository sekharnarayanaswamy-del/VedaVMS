# VedaVMS Redesign & Document Automation

This repository contains tools, data snapshots, and redesign mockups for [VedaVMS](https://vedavms.in) — a digital repository for Vedic texts across multiple Indian languages (Sanskrit, Tamil, Malayalam, Kannada, Telugu, etc.).

---

## 📁 Repository Structure

```
vedavms/
├── generate_documents.py               # Main document page generator script
├── scripts/
│   ├── sync_staging.py                 # One-step Google Sheets fetch, build, and deploy to staging
│   ├── deploy_staging.py               # Direct deployment script for new.vedavms.in
│   ├── upload_donations.py             # Live production site restore/update utility
│   └── check_pages.py                  # Live page inspection utility
├── mockup/                             # Redesign mockup templates
│   ├── index.html
│   ├── documents.html
│   ├── articles.html
│   ├── videos.html
│   ├── convention.html
│   ├── donations.html
│   └── about.html
├── build/                              # Generated static pages ready for deployment
│   ├── index.html
│   ├── documents.html
│   ├── articles.html
│   ├── videos.html
│   ├── convention.html
│   ├── donations.html
│   └── about.html
├── data/                               # Snapshot texts and document metadata
│   ├── sanskrit_snapshot.txt
│   ├── tamil_docs.txt
│   ├── malayalam_docs.txt
│   ├── kannada_docs.txt
│   ├── telugu_docs.txt
│   ├── english_docs.txt
│   ├── tamil_videos_snapshot.txt
│   └── english_videos_snapshot.txt
├── vedavms-redesign-recommendations.md # Full redesign strategy & architecture report
└── current_status.pdf                  # Reference assessment of existing site
```

---

## 🚀 Usage

### 1. One-Step Sync to Staging (`new.vedavms.in`)
Fetches the live Google Sheet, regenerates all 980+ documents into `build/` (with dynamic hierarchical numbering), and deploys directly to the staging site:
```bash
# Full fetch, build, and deploy:
python scripts/sync_staging.py

# Or jump straight to uploading existing build/ files without rebuilding:
python scripts/sync_staging.py --skip-build
```

### 2. Regenerate Document Pages Locally
The generator fetches the live pages, local cache, or Google Sheets CSV, parses document metadata, builds language filter tabs, and renders `build/documents.html` using `mockup/documents.html` as the design template:

```bash
# Generate build/documents.html directly from master CSV / Google Sheets
python generate_documents.py --source-csv data/vedavms_documents.csv

# Or generate directly from live Google Sheet CSV export URL
python generate_documents.py --source-csv "https://docs.google.com/spreadsheets/d/1O-pBNmfEhBEHsbR47T-pMlrW36BpGdoJdiwHpVjDDjs/export?format=csv&gid=548744990"

# Export current scraped/parsed documents to CSV & JSON for Google Sheets
python generate_documents.py --offline --export-csv data/vedavms_documents.csv --export-json data/vedavms_documents.json

# Fetch live pages and generate build/documents.html (scraper mode)
python generate_documents.py

# Offline mode (reuses cached pages from .cache/)
python generate_documents.py --offline

# Verify all emitted document links resolve against live site
python generate_documents.py --check
```

- See **[MAINTAINER_COOKBOOK.md](MAINTAINER_COOKBOOK.md)** for a short recipe on uploading PDFs and updating Google Sheets.
- See **[MAINTAINER_GUIDE.md](MAINTAINER_GUIDE.md)** for the full maintainer workflow, technical architecture, and Google Sheets + GitHub Actions pipeline.

---

## 🎯 Catalog Structure (986 Documents Across 14 Tabs)

### Download by Language (6 Tabs)
- **Sanskrit** (131 docs): Vedic Books by Subject, Samhita, Brahmana, Aranyaka, Upanishads
- **Tamil** (125 docs): With errata / corrections tracking
- **Malayalam** (128 docs): With errata / corrections tracking
- **Kannada** (30 docs): Recensions
- **Telugu** (16 docs): Recensions
- **Latin (IAST)** (27 docs): Transliterated texts

### Pilot Projects & Special Editions (8 Tabs)
- **Row 1**:
  - **Baraha Source** (201 docs): Source `.docx` documents across 8 Kandam sections
  - **English** (3 docs): Explanatory texts
  - **TS Samhita Jatai** (132 docs): TS Jatai recitations
  - **TS Samhita Ghanam** (132 docs): TS Ghanam recitations
  - **Kanva Samhita** (44 docs): Kanva recensions
  - **Parayanam and References** (9 items): Classical text web references + TTD recitation spreadsheets
- **Row 2**:
  - **Ghana Sandhi** (7 docs): TS Gana Sandhi lessons
  - **Ghana Maala Pilot** (1 doc): Pilot project text

---

## 🎯 Key Design & Architectural Highlights

1. **Modern Responsive UI**: Clean, mobile-friendly interface with warm Vedic aesthetic, collapsible accordions, and refined typography.
2. **Dynamic Search & Filtering**: Fast client-side instant search across 980+ documents, audio recitations, and video lessons by language, kanda, and title.
3. **Automated Maintenance**: Python scripts and Google Sheets + GitHub Actions pipeline to keep document indexes synchronized with live content without manual HTML editing.
4. **Resilient CSV Sync**: Full bidirectional export (`--export-csv`) and import (`--source-csv`) supporting UTF-8 with BOM for Indic unicode.


