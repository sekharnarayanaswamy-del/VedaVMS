# VedaVMS Website Maintenance Guide (Google Sheets Method)

This guide explains how non-technical maintainers can update documents on **VedaVMS** without writing code, running scripts, or managing web servers.

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

---

## ⚡ Step 3: Publishing Changes to the Staging Site (`new.vedavms.in`)

There are two ways changes get published:

1. **Automatic Nightly Update**:
   - Every night at 5:30 AM IST, GitHub Actions automatically downloads the Google Sheet and refreshes `new.vedavms.in`.
2. **Instant Manual Publish (Optional One-Click Trigger)**:
   - Go to the GitHub repository page in your browser.
   - Click the **Actions** tab at the top.
   - In the left sidebar, click **Deploy to Staging (new.vedavms.in)**.
   - Click **Run workflow** > **Run workflow**.
   - Within 1–2 minutes, the updated pages are generated and published to staging.

---

## 🔒 Managing Staging Credentials in GitHub (For Administrator)

To enable automated FTP/SFTP deployment to `new.vedavms.in`, add these Secrets in your GitHub repository (**Settings > Secrets and variables > Actions > New repository secret**):

| Secret Name | Description | Example |
| :--- | :--- | :--- |
| `GOOGLE_SHEET_CSV_URL` | Live Google Sheet CSV URL | `https://docs.google.com/spreadsheets/d/.../export?format=csv` |
| `STAGING_FTP_SERVER` | FTP / SFTP Server Host | `ftp.vedavms.in` or `new.vedavms.in` |
| `STAGING_FTP_USERNAME` | FTP Username | `staging_user` |
| `STAGING_FTP_PASSWORD` | FTP Password | `********` |
| `STAGING_REMOTE_DIR` | Directory path on server | `/public_html` or `/staging` |

---

## 🧪 Testing Locally (For Developers)

To test the generator locally with the spreadsheet or CSV file:

```bash
# Generate from local CSV
python generate_documents.py --source-csv data/vedavms_documents.csv

# Generate directly from live Google Sheet CSV URL
python generate_documents.py --source-csv "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/export?format=csv"
```
