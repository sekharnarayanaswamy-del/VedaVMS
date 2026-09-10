# VedaVMS Redesign & Document Automation

This repository contains tools, data snapshots, and redesign mockups for [VedaVMS](https://vedavms.in) — a digital repository for Vedic texts across multiple Indian languages (Sanskrit, Tamil, Malayalam, Kannada, Telugu, etc.).

---

## 📁 Repository Structure

```
vedavms/
├── src/                                # Baraha transliteration & Vedic Reader generator
│   ├── __init__.py
│   ├── transliterate.py                # Baraha to Devanagari Unicode transliterator
│   ├── build_reader.py                 # DOCX to interactive Vedic HTML reader generator
│   └── config.json                     # Multi-book configuration & font settings
├── generate_documents.py               # Main document page generator script
├── scripts/
│   ├── deploy_site.py                  # Unified deploy & rollback CLI (staging, production, backups)
│   ├── sync_staging.py                 # One-step Google Sheets fetch, build, and deploy to staging
│   ├── google_apps_script.js           # Apps Script for 1-click deploy from Google Sheets
│   ├── check_runs.py                   # GitHub Actions workflow run monitor
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
├── backups/                            # Local & pre-deploy server backup snapshots
├── data/                               # Snapshot texts and document metadata
│   └── vedavms_documents.csv           # Master documents database CSV
├── .github/workflows/
│   ├── deploy_staging.yml              # CI/CD automated staging deployment (new.vedavms.in)
│   └── deploy_production.yml           # CI/CD production promotion workflow (vedavms.in)
├── BARAHA_READER_GUIDE.md              # Guide for generating Vedic HTML readers from Baraha DOCX
├── MAINTAINER_GUIDE.md                 # Complete technical & maintainer manual
└── MAINTAINER_COOKBOOK.md              # 3-step quick recipe for everyday editors
```

---

## 🚀 Usage & Deployment CLI

### 1. Unified Deployment CLI (`scripts/deploy_site.py`)

Deploy directly from your laptop to Staging or Production, with automated pre-deploy backups and instant rollback support:

```bash
# Deploy to Staging (new.vedavms.in at /new.vedavms.in)
python scripts/deploy_site.py --staging

# Deploy to Live Production (vedavms.in at /httpdocs)
# Automatically downloads a pre-deploy backup snapshot before uploading!
python scripts/deploy_site.py --production

# Preview changes without modifying the server (Dry Run)
python scripts/deploy_site.py --production --dry-run

# List all available backup snapshots
python scripts/deploy_site.py --list-backups

# Interactive Rollback of Production
python scripts/deploy_site.py --rollback --production

# Instant Rollback to original pre-redesign baseline:
python scripts/deploy_site.py --rollback --production --snapshot backup_production_vedavms_in
```

### 2. One-Step Sync to Staging from Laptop
Fetches the live Google Sheet, regenerates all 980+ documents into `build/` (with dynamic hierarchical numbering), and deploys directly to the staging site:
```bash
# Full fetch, build, and deploy:
python scripts/sync_staging.py

# Or jump straight to uploading existing build/ files without rebuilding:
python scripts/sync_staging.py --skip-build
```

### 3. One-Click Deployment from Google Sheets
Maintainers can deploy directly from the spreadsheet without terminal access:
- **`🚀 VedaVMS` ➔ `1. 🚀 Publish to Staging (new.vedavms.in)`**: Builds and pushes to staging; logs timestamp in cell **`J2`**.
- **`🚀 VedaVMS` ➔ `2. 🌐 Push Staging to Production (vedavms.in)`**: Promotes build to live production; logs timestamp in cell **`J3`**.

---

### 4. Regenerate Document Pages Locally
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
- See **[BARAHA_READER_GUIDE.md](BARAHA_READER_GUIDE.md)** for complete details on generating standalone interactive Vedic HTML readers from Baraha sources.

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


