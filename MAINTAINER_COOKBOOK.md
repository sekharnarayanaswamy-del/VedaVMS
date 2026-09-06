# VedaVMS Maintainer Cookbook 📖
*A quick recipe for maintainers who upload PDF documents and update the Google Sheet.*

> 📌 **Note**: This cookbook covers the everyday workflow. For the complete system architecture, one-time setup, or server credentials, see **[MAINTAINER_GUIDE.md](MAINTAINER_GUIDE.md)**.

---

## 🍳 The 3-Step Recipe

```
Step 1: Upload PDF in Plesk  ──>  Step 2: Copy Link from Browser  ──>  Step 3: Paste in Google Sheet
```

---

### Step 1: Upload the PDF File

1. Log into **Plesk** (`https://103.69.196.157:8443`).
2. Go to **Websites & Domains** &rarr; **vedavms.in** &rarr; **File Manager**.
3. Open **`httpdocs`** &rarr; **`docs`** &rarr; open the relevant folder (e.g. `TU`, `sanskrit`, `Shiva-Stuti`, etc.).
4. Click the blue **+ (Upload)** button and select your PDF file.

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
1. Upload the new file to Plesk and copy its URL (Steps 1 & 2 above).
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

### 3. When Do Changes Go Live?
- **Automatically every night at 5:30 AM IST**.
- Or immediately if you click **"Run workflow"** under GitHub's **Actions** tab, or run `python scripts/sync_staging.py` from your laptop.
