# VedaVMS Redesign & Document Automation

This repository contains tools, data snapshots, and redesign mockups for [VedaVMS](https://vedavms.in) — a digital repository for Vedic texts across multiple Indian languages (Sanskrit, Tamil, Malayalam, Kannada, Telugu, etc.).

---

## 📁 Repository Structure

```
vedavms/
├── src/                                # Baraha transliteration & Vedic Reader generator
│   ├── __init__.py
│   ├── transliterate.py                # Baraha to Devanagari Unicode transliterator
│   ├── baraha_reader.py                # DOCX to structured JSON AST extractor & parser
│   ├── build_reader.py                 # DOCX / AST to interactive Vedic HTML reader generator
│   └── config.json                     # Multi-book configuration & font settings
├── generate_documents.py               # Main static website & documents generator script
├── scripts/
│   ├── deploy_site.py                  # Unified deploy & rollback CLI (staging, production, backups)
│   ├── sync_staging.py                 # One-step Google Sheets fetch, build, and deploy to staging
│   ├── google_apps_script.js           # Google Sheet automation suite (menu, versioning, status logging)
│   ├── check_runs.py                   # GitHub Actions workflow run monitor
│   └── check_pages.py                  # Live page inspection utility
├── mockup/                             # Redesign mockup templates
│   ├── index.html                      # Portal homepage template
│   ├── documents.html                  # 14-tab documents catalog template
│   ├── articles.html                   # Dynamic articles template
│   ├── videos.html                     # Dynamic videos template
│   ├── convention.html                 # Conventions page
│   ├── donations.html                  # Donations page
│   ├── about.html                      # About page
│   └── viewer/                         # Standalone Vedic HTML reader templates
├── build/                              # Generated static production artifacts
│   ├── index.html                      # Live portal homepage
│   ├── documents.html                  # Master documents catalog
│   ├── version.txt                     # Plain-text semantic version endpoint
│   ├── fonts/                          # Bundled Vedic Adishila TTF web fonts
│   └── viewer/                         # Standalone readers (TU, Siva Stuti, TB 3.7-3.9, Udaka Shanti)
├── backups/                            # Local & pre-deploy server backup snapshots
├── fonts/                              # TrueType Vedic fonts (Adishila San, Vedic, etc.)
├── data/                               # Snapshot texts, version, and document metadata
│   ├── version.txt                     # Current catalog semantic version (e.g. 2.5.0)
│   └── vedavms_documents.csv           # Master documents database CSV
├── .github/workflows/
│   ├── deploy_staging.yml              # CI/CD automated staging deployment (new.vedavms.in)
│   └── deploy_production.yml           # CI/CD production deployment & release tagging (vedavms.in)
├── BARAHA_READER_GUIDE.md              # Guide for generating Vedic HTML readers from Baraha DOCX
├── MAINTAINER_GUIDE.md                 # Complete technical & maintainer manual
└── MAINTAINER_COOKBOOK.md              # 3-step quick recipe for everyday editors
```

---

## 🚀 Usage & Deployment CLI

### 🌐 Live Production Deployment Conditions (`vedavms.in`)
The live production web server (`vedavms.in` at remote directory `/public_html/`) is updated **only under 5 conditions**:
1. **Commit Message Flag on `main`**: Push to `main` with commit message containing `[prod]`, `[production]`, `[deploy:prod]`, or `prod:`.
2. **Google Sheets One-Click Publish**: Maintainer clicks **`🚀 VedaVMS` ➔ `🔴 Publish to Production (vedavms.in)`** (auto-increments patch version in cell **`J1`** and logs timestamp in cell **`J3`**).
3. **GitHub Actions Web UI**: Manually triggering **Deploy to Production (vedavms.in)** with `confirm_deploy = "DEPLOY"`.
4. **Repository Dispatch Webhook**: API `repository_dispatch` event of type `deploy_production` or `google_sheet_production_deploy`.
5. **Laptop CLI Command or Rollback**: Executing `python scripts/deploy_site.py --production` (or `python scripts/deploy_site.py --rollback --production`).

> 💡 **Default behavior**: Standard `git push origin main` without production tags automatically deploys to **Staging** ([`new.vedavms.in`](https://new.vedavms.in)), leaving live production untouched.

---

### 1. Unified Deployment CLI (`scripts/deploy_site.py`)

Deploy directly from your laptop to Staging or Production, with automated pre-deploy backups and instant rollback support:

```bash
# Deploy to Staging (new.vedavms.in at /public_html/new/)
python scripts/deploy_site.py --staging

# Deploy to Live Production (vedavms.in at /public_html/)
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
Fetches the live Google Sheet, regenerates all 980+ documents into `build/` (with dynamic hierarchical numbering and version stamping), and deploys directly to the staging site:
```bash
# Full fetch, build, and deploy:
python scripts/sync_staging.py

# Or jump straight to uploading existing build/ files without rebuilding:
python scripts/sync_staging.py --skip-build
```

### 3. One-Click Deployment & Semantic Versioning from Google Sheets
Maintainers can deploy directly from the spreadsheet without terminal access:
- **`🚀 VedaVMS` ➔ `🚀 Publish to Staging (new.vedavms.in)`**: Builds and pushes to staging; logs timestamp in cell **`J2`**.
- **`🚀 VedaVMS` ➔ `🔴 Publish to Production (vedavms.in)`**: Automatically increments the **Patch Version** (e.g. `v2.5.0` $\rightarrow$ `v2.5.1`), stamps all HTML pages and metadata, publishes to live production, pushes Git tag `v2.5.1`, and logs the timestamp in cell **`J3`**.
- **`🚀 VedaVMS` ➔ `🏷️ Set / Bump Catalog Version...`**: Manually sets custom major/minor versions.
- **`🚀 VedaVMS` ➔ `📋 Setup Sheet Status Headers (I1:J3)`**: Auto-configures and formats cells `I1:J3`.

### 4. Git Push Deployment Flags (Staging vs. Production)
When pushing commits to GitHub, you can target Staging or Production via your commit message:
- **Default (Staging - `new.vedavms.in`)**: Standard `git push origin main` automatically triggers deployment to **Staging** (`new.vedavms.in`).
  ```bash
  git commit -m "Update reader styles"
  git push origin main
  ```
- **Production (`vedavms.in`)**: Include `[prod]` or `[production]` in your commit message to deploy directly to live **Production**:
  ```bash
  git commit -m "Publish new readers [prod]"
  git push origin main
  ```


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


