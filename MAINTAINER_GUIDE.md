# VedaVMS Website Maintenance Guide (Google Sheets Method)

This guide explains how non-technical maintainers can update documents on **VedaVMS** without writing code, running scripts, or managing web servers.

> 💡 **Looking for a fast, simple recipe?** See the **[Maintainer Cookbook](MAINTAINER_COOKBOOK.md)** for a 3-step guide to uploading PDFs and updating Google Sheets.

---

## 📋 Overview of the Process

```
1. Edit Google Sheet  ──>  2. Automated Sync (GitHub)  ──>  3. Live on Website
   (Add / Edit / Remove)      (Runs automatically / daily)       (new.vedavms.in)
```

---

## 🚀 Step 1: Initial Setup (One-Time)

1. Open [Google Sheets](https://sheets.google.com) and click **Blank Spreadsheet**.
2. Name the spreadsheet: `VedaVMS Document Master Database`.
3. Click **File** > **Import** > **Upload** and upload `data/vedavms_documents.csv` from this repository.
   - Choose **Replace spreadsheet**.
   - Click **Import data**.
4. Make the sheet readable by the generator:
   - Click the green **Share** button in the top right.
   - Under *General access*, change from *Restricted* to **Anyone with the link** (Role: **Viewer**).
   - Click **Done**.
5. Live Master Spreadsheet URL:
   `https://docs.google.com/spreadsheets/d/1O-pBNmfEhBEHsbR47T-pMlrW36BpGdoJdiwHpVjDDjs/edit?gid=548744990#gid=548744990`
6. The direct CSV export link is:
   `https://docs.google.com/spreadsheets/d/1O-pBNmfEhBEHsbR47T-pMlrW36BpGdoJdiwHpVjDDjs/export?format=csv&gid=548744990`

---

## 📝 Step 2: Day-to-Day Maintenance

### Adding a New Document
1. Open the **VedaVMS Document Master Database** Google Sheet.
2. Scroll to the relevant section (or add a row where you want it to appear).
3. Fill in the columns:
   - **Language**: Choose the language tab (e.g. `Sanskrit`, `Tamil`, `Telugu`, `Kannada`, `Malayalam`, `English`, `TS Jatai`, `TS Ghanam`, `SikShA & Lessons`, `Kanva Samhita`, `Pilot & In-Progress`, `Latin (IAST)`).
   - **Section**: The accordion heading (e.g. `Vedic Books by Subject`, `Taittiriya Samhita — Kandam 1`, `Pada Patam`, etc.).
   - **Title**: The display name of the document.
   - **PDF_URL**: The web link to the PDF file (e.g., `https://vedavms.in/docs/...` or Google Drive shared link).
   - **Version**: (Optional) e.g., `V1.0`, `V2.1`.
   - **Date**: (Optional) e.g., `Oct 31, 2026`.
   - **Corrections_URL**: (Optional) Link to errata or corrections PDF.
   - **Status**: Set to `Active`.
   - **Notes**: (Optional) Internal notes for your team.

### Updating an Existing Document (New Version / Errata)
- Find the document row.
- Update the **PDF_URL** with the new file URL.
- Update the **Version** (e.g. change `V1.0` to `V1.1`) and **Date**.
- If a corrections PDF was added or removed, update the **Corrections_URL**.

### Removing / Archiving a Document
- Instead of deleting the row, you can simply change **Status** from `Active` to `Hidden`.
- The document will immediately disappear from the website on the next build, while keeping your historical record safely preserved in the spreadsheet.

### Automatic Dynamic Numbering (Hierarchical)
- You **do not** need to manually renumber rows in the Google Sheet when hiding or adding documents.
- In numbered sections like *Vedic Books by Subject*, the build system dynamically assigns contiguous numbers (`1)`, `2)`, `3)`...) and preserves sub-document hierarchy (`1A)`, `2A)`, `2B)`...).
- **Example**: When `1) Shanti Japam` is set to `Hidden`, the next active book (`2) TaittirIyopanishat`) automatically displays as `1)`, its sub-book `2A) Surya namaskara` automatically becomes `1A)`, and `3) Udaka Shanti` becomes `2)`. If `Shanti Japam` is later unhidden, the numbering automatically shifts back.

---

## ⚡ Step 3: Publishing Changes to the Staging Site (`new.vedavms.in`)

There are three ways changes get published to staging:

### Method A: One-Command Sync from Laptop
If you want to immediately update the staging site directly from your computer without waiting for GitHub Actions:
```powershell
# Full fetch, regeneration, and upload:
python scripts/sync_staging.py

# Skip Google Sheets fetch and upload existing build/ folder immediately:
python scripts/sync_staging.py --skip-build
```
This command will:
1. Automatically fetch the latest data from the live Google Sheet.
2. Regenerate all files in `build/` (filtering out hidden items, applying dynamic hierarchical numbering, and formatting 760+ documents).
3. Upload all updated pages to `new.vedavms.in` (`/new.vedavms.in/`) using native Windows transfer tools (`curl.exe`).

### Method B: Automatic Nightly Update via GitHub
- Every night at 00:00 UTC (5:30 AM IST), GitHub Actions automatically downloads the Google Sheet, rebuilds the site, and deploys to `new.vedavms.in`.

### Method C: Instant Trigger via GitHub Actions (One-Click)
1. Go to the GitHub repository in your browser.
2. Click the **Actions** tab at the top.
3. In the left sidebar, click **Deploy to Staging (new.vedavms.in)**.
4. Click **Run workflow** > **Run workflow**.
5. Within ~1 minute, the build runs and publishes to staging.

---

## 🔒 Staging Server Configuration & Credentials

The staging site resides on the same Windows IIS / Plesk server as production, but in its own dedicated document root folder:

| Parameter | Setting | Description |
| :--- | :--- | :--- |
| **Server Host** | `103.69.196.157` | Plesk hosting server |
| **Protocol** | FTPS (FTP over TLS) | Port 21 with TLS Session Resumption |
| **Username** | `vedavmsi` | System FTP account |
| **Production Directory** | `/httpdocs/` | Serves the main live site (`vedavms.in`) |
| **Staging Directory** | `/new.vedavms.in/` | Serves the redesigned staging site (`new.vedavms.in`) |

### GitHub Secrets for Staging Pipeline:
Configure these in GitHub under **Settings > Secrets and variables > Actions**:
- `STAGING_FTP_SERVER`: `103.69.196.157`
- `STAGING_FTP_USERNAME`: `vedavmsi`
- `STAGING_FTP_PASSWORD`: `(your FTP password)`
- `STAGING_REMOTE_DIR`: `/new.vedavms.in/`

---

## 🧪 Testing & Regeneration Locally

```bash
# Full sync & deploy to new.vedavms.in in one step
python scripts/sync_staging.py

# Rebuild files locally only without uploading
python generate_documents.py --source-csv "https://docs.google.com/spreadsheets/d/1O-pBNmfEhBEHsbR47T-pMlrW36BpGdoJdiwHpVjDDjs/export?format=csv&gid=548744990"

# Rebuild using local fallback CSV
python generate_documents.py --source-csv data/vedavms_documents.csv
```
```
