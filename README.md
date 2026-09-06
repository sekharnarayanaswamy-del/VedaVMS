# VedaVMS Redesign & Document Automation

This repository contains tools, data snapshots, and redesign mockups for [VedaVMS](https://vedavms.in) — a digital repository for Vedic texts across multiple Indian languages (Sanskrit, Tamil, Malayalam, Kannada, Telugu, etc.).

---

## 📁 Repository Structure

```
vedavms/
├── generate_documents.py               # Main document page generator script
├── scripts/
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

### Regenerate Document Pages

The generator fetches the live pages from `vedavms.in`, parses document metadata, builds language filter tabs, and renders `build/documents.html` using `mockup/documents.html` as the design template:

```bash
# Generate build/documents.html directly from master CSV / Google Sheets
python generate_documents.py --source-csv data/vedavms_documents.csv

# Or generate directly from live Google Sheet CSV export URL
python generate_documents.py --source-csv "https://docs.google.com/spreadsheets/d/1O-pBNmfEhBEHsbR47T-pMlrW36BpGdoJdiwHpVjDDjs/export?format=csv&gid=548744990"

# Export current documents to CSV / JSON
python generate_documents.py --export-csv data/vedavms_documents.csv --export-json data/vedavms_documents.json

# Fetch live pages and generate build/documents.html (legacy scraper mode)
python generate_documents.py

# Offline mode (reuses cached pages from .cache/)
python generate_documents.py --offline

# Verify all emitted document links resolve against live site
python generate_documents.py --check
```

See [MAINTAINER_GUIDE.md](MAINTAINER_GUIDE.md) for non-technical maintainer workflow using Google Sheets and GitHub Actions staging deployment.

---

## 🎯 Project Goals

1. **Modern Responsive UI**: Clean, mobile-friendly interface with dark/light visual harmony and clear typography.
2. **Dynamic Search & Filtering**: Fast client-side search across 700+ Vedic PDFs, audio files, and video lessons by language, kanda, and title.
3. **Automated Maintenance**: Python scripts and Google Sheets + GitHub Actions pipeline to keep document indexes synchronized with live content without manual HTML editing.

