# VedaVMS Maintainer Cookbook 📖
*A quick recipe for maintainers who upload PDF documents and update the Google Sheet.*

> 📌 **Note**: This cookbook covers the everyday workflow. For the complete system architecture, one-time setup, or server credentials, see **[MAINTAINER_GUIDE.md](MAINTAINER_GUIDE.md)**.

---

## 🍳 The 3-Step Recipe

```
Step 1: Upload PDF in Control Panel  ──>  Step 2: Copy Link from Browser  ──>  Step 3: Paste in Google Sheet
```

---

### Step 1: Upload the PDF File

1. Log into the **Web Hosting Control Panel** at [https://cp.controlpanel.systems](https://cp.controlpanel.systems) with your credentials (takes you to the **vedavms.in Control Panel** / File Manager) or connect via FTP.
2. Go to **File Manager** &rarr; **`public_html`** &rarr; **`docs`** &rarr; open the relevant folder (e.g. `TU`, `sanskrit`, `Shiva-Stuti`, `TB`, etc.).
3. Click the **Upload** button and select your PDF file.

---

### Step 2: Get the Link (Zero Typing)

1. Find your uploaded PDF in the list.
2. Click the three-dots menu **`...`** on the right side of the row.
3. Click **"Open in Browser"**.
4. The PDF opens in a new browser tab.
5. **Click the browser's address bar and copy the URL (`Ctrl + C`)**.

*(Example copied link: `https://vedavms.in/docs/sanskrit/JSV_Samhita.pdf`)*

---

### Step 3: Add to Google Sheets

Open the [VedaVMS Google Sheet](https://docs.google.com/spreadsheets/d/1O-pBNmfEhBEHsbR47T-pMlrW36BpGdoJdiwHpVjDDjs/edit?gid=548744990#gid=548744990) and add a row:

| Column | What to enter | Example |
| :--- | :--- | :--- |
| **Supersection** | Language name | `Sanskrit` |
| **Section** | Category heading | `Vedic Books by Subject` |
| **Title** | Clean name of the document | `JSV Samhita - Sanskrit` |
| **PDF_URL** | Paste the URL from Step 2 | `https://vedavms.in/docs/sanskrit/JSV_Samhita.pdf` |
| **Version** | Edition / Version number | `V1.0` |
| **Date** | Release date | `Sep 7, 2026` |
| **Corrections_URL** | (Optional) Errata PDF link | *(leave blank if none)* |
| **Status** | Set to `Active` | `Active` |

---

## 📝 Updating an Existing Document

If you are publishing a new edition or adding an errata/corrections PDF:
1. Upload the new file via the Control Panel and copy its URL (Steps 1 & 2 above).
2. In Google Sheets, find the existing row for that document:
   - Update **`PDF_URL`** with the new link.
   - Update **`Version`** (e.g. change `V1.0` &rarr; `V1.1`) and **`Date`**.
   - If there is an errata sheet, paste its link into **`Corrections_URL`**.

---

## 💡 Quick Rules for Maintainers

### 1. Document Numbering is 100% Automatic!
- You **do not** need to type `1)`, `2)`, `3)` in the title. The website automatically numbers all main books in order.
- If your document is a **sub-book** belonging to the book above it, simply prefix it with **`A)`**, **`B)`**, etc.  
  *(e.g., `A) Surya Namaskaram` automatically displays as `1A) Surya Namaskaram`).*

### 2. How to Temporarily Remove a Document
- **Never delete the row.** Simply change **Status** from `Active` to **`Hidden`**.
- The website will automatically hide it and renumber the remaining books seamlessly starting from `1)`.

### 3. Valid Supersection / Language Names
Use any of these 14 category names in the **`Supersection`** (or **`Language`**) column:
- **Languages**: `Sanskrit`, `Tamil`, `Malayalam`, `Kannada`, `Telugu`, `Latin (IAST)`
- **Special Editions**: `Baraha Source`, `English`, `TS Jatai`, `TS Ghanam`, `Kanva Samhita`, `Parayanam & References`, `Ghana Sandhi`, `Ghana Maala Pilot`

### 4. Bulk Data Migration & CSV Export
If you need to extract all documents into a fresh CSV spreadsheet:
```bash
python generate_documents.py --offline --export-csv data/vedavms_documents.csv
```
Import `data/vedavms_documents.csv` into Google Sheets via **File ➔ Import ➔ Upload**.

### 5. When Do Changes Go Live?
- **From Google Sheets**:
  - Click **`🚀 VedaVMS` ➔ `🚀 Publish to Staging (new.vedavms.in)`** to preview changes in 1–2 minutes (logs timestamp in cell **`J2`**).
  - Click **`🚀 VedaVMS` ➔ `🔴 Publish to Production (vedavms.in)`** after review to promote to live production. This automatically bumps the **Patch Version** (e.g. `v2.5.0` $\rightarrow$ `v2.5.1`) in cell **`J1`**, stamps the release across all HTML pages, and logs the timestamp in cell **`J3`**.
  - Click **`🚀 VedaVMS` ➔ `🏷️ Set / Bump Catalog Version...`** if you need to manually change or bump minor/major versions.
- **From GitHub Actions**: Go to **Actions** ➔ select **Deploy to Staging** or **Deploy to Production** ➔ click **Run workflow**.
- **From Laptop / CLI**: Run `python scripts/deploy_site.py --staging` or `python scripts/deploy_site.py --production` (with instant rollback via `python scripts/deploy_site.py --rollback --production`).

### 6. Recent Updates Rolling Window
- The **Recent Updates** feed automatically shows documents released in the last 90 days as well as documents with future release dates.
- Because VedaVMS is a static site, this rolling window is computed when the site is **built & published**. Deploying updates (via Google Sheets or GitHub) automatically refreshes the window for the current date.



