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

There are four ways changes get published to staging:

### Method A: One-Click Trigger from Google Sheets (Recommended for Maintainers)
Maintainers can publish changes directly from the Google Sheet without touching code or GitHub:
1. Open the [VedaVMS Google Sheet](https://docs.google.com/spreadsheets/d/1O-pBNmfEhBEHsbR47T-pMlrW36BpGdoJdiwHpVjDDjs/).
2. In the top menu, click **`🚀 VedaVMS`** ➔ **`Publish to Staging (new.vedavms.in)`**.
3. Confirm the prompt by clicking **Yes**.
4. A popup will confirm that GitHub Actions has started rebuilding the site, and updates will be live in 1–2 minutes.

### Method B: Instant Trigger via GitHub Actions (Web UI)
1. Go to the GitHub repository in your browser.
2. Click the **Actions** tab at the top.
3. In the left sidebar, click **Deploy to Staging (new.vedavms.in)**.
4. Click **Run workflow** > **Run workflow**.
5. Within ~1 minute, the build runs and publishes to staging.

### Method C: One-Command Sync from Laptop (Developer / Admin)
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

---

## 🛡️ Security Considerations & Access Control

Because the repository is public and multiple team members collaborate, the following safeguards are built in:

### 1. Repository Access & Protection
- **Read-Only to the Public**: Strangers can view and clone the repository, but **cannot** push commits, edit code, or run workflows.
- **Push Protection**: Only authenticated repository owners/collaborators with explicit write access can commit to `main`.
- **Pull Requests**: Pull requests opened by external contributors from forks **do not** have access to repository secrets and cannot trigger deployments.

### 2. Secret Encryption & Isolation
- **No Passwords in Git**: All FTP credentials reside in GitHub Secrets (encrypted with libsodium) and in the local gitignored `.env` file. Credentials never appear in plaintext or workflow logs (automatically masked as `***`).
- **Server Isolation**: Staging builds are strictly constrained to `/new.vedavms.in/`. The automated workflow has no access to modify the live production directory (`/httpdocs/`).

### 3. Google Sheets Access Control
- **General Access**: The Google Sheet's general link access must remain **Viewer**. This allows the automated build script to read CSV data while preventing random people from altering the sheet.
- **Maintainer Invitations**: Only specific, trusted maintainers should be added as **Editors** via their Google email addresses.

### 4. GitHub Personal Access Token (PAT) Security
- The token used by Google Sheets Apps Script must be kept secure.
- **Fine-Grained Scoping (Least Privilege)**: When creating or updating the token, scope it strictly to the `VedaVMS` repository with permissions restricted to **Actions: Read and write**.
- **Apps Script Properties**: To prevent spreadsheet editors from reading the token in plain text, store it in Apps Script **Project Settings ➔ Script Properties** rather than directly inside the JavaScript file.

---

## 📋 Administrator "To-Do" Checklist

Use this checklist to complete the autonomous setup:

- [ ] **1. Disable "Required Reviewers" for Staging**:
  - Go to **GitHub Repo ➔ Settings ➔ Environments ➔ `staging`**.
  - Under *Deployment protection rules*, uncheck or delete **Required reviewers**.
  - Click **Save protection rules**.
  - *(Outcome: Maintainers can trigger deploys from Google Sheets without waiting for your manual approval each time).*

- [ ] **2. Verify Google Sheet Sharing Settings**:
  - Open the [Google Sheet](https://docs.google.com/spreadsheets/d/1O-pBNmfEhBEHsbR47T-pMlrW36BpGdoJdiwHpVjDDjs/).
  - Click **Share** (top right).
  - Verify *General access* is **"Anyone with the link" ➔ Role: Viewer**.
  - Under *People with access*, add your content maintainers' Gmail addresses as **Editor**.

- [ ] **3. Install Apps Script in Google Sheet**:
  - In the sheet, go to **Extensions ➔ Apps Script**.
  - Paste the `triggerDeploy` script.
  - Insert your generated GitHub token (`GITHUB_TOKEN = 'ghp_...'`).
  - Save (`Ctrl + S`) and reload the sheet to verify the **`🚀 VedaVMS`** menu appears.

- [ ] **4. (Optional Future Hardening) Migrate Token to Script Properties**:
  - Once working smoothly, switch to a GitHub **Fine-grained Personal Access Token** scoped strictly to `VedaVMS` (`Actions: Read and write`).
  - In Apps Script, open **Project Settings (gear icon) ➔ Script Properties**.
  - Add property `GITHUB_TOKEN` with the token value.
  - Update the script to fetch it via `PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN')` so editors cannot view the token in the script editor.

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

