# VedaVMS Product Backlog & To-Do Tracking

This document tracks open architectural items, planned enhancements, and backlog tasks across the VedaVMS platform.

---

## 📌 Active Backlog Items

### 1. Atomic Chanting Padas & Chanting Layout Refinement (Input Sources & Line Formatting)
* **Status**: ⏸️ **Paused** (Pending review of upstream input files).
* **Target Area**: `src/build_reader.py` (`wrap_chant_padas`), `src/baraha_reader.py`, and Vedic HTML readers.
* **Context & Problem Statement**:
  * In books parsed from Word documents (e.g. *Udaka Shānti ASCT*, *Taittirīya Upaniṣad*, *Shānti Japam*), Anuvāka passages frequently lack internal `|` (daṇḍa) delimiters, unlike Taittirīya Brāhmaṇa (`AAK.brh`) which has disciplined punctuation after every 3–6 words.
  * In *Udaka Shanti ASCT* Section 1.2 (*Vedadhaya*), TS 1.1.1 is printed as an unbroken 43-word continuous block ending only with `|| 1`.
  * Because sentences exceeding 85 characters without daṇḍas fall back to `.chant-pada-long` (`white-space: normal`), browsers wrap words arbitrarily mid-compound across screen margins (e.g. `आप्यायद्धमघ्निया देवभाग` / `मूर्जस्वतीः`).
  * In addition, manual line breaks in Word without daṇḍas (e.g. `अग्निमीळे पुरोहितं-यज्ञस्य`) isolate lines, while padas with daṇḍas pack side-by-side (`देवमृत्विजं ।  होतारं रत्न धातमं ।`).
* **Next Steps / Action Items**:
  1. **Source File Audit**: Check if improved/standardized Baraha sources (`.docx` or `.brh`) can be obtained with canonical chanting daṇḍas (`|`) at authentic breath/pada boundaries matching Pathashala recitation.
  2. **Standardize Word Line Breaks**: Clean up manual line breaks in DOCX sources that split verses mid-sentence without daṇḍas.
  3. **Rendering Layout Enhancements** (to be revisited once sources are reviewed):
     - **Mode A (Flowing Atomic Padas)**: Smart word/avāntara boundary breaking for long passages without daṇḍas.
     - **Mode B (Traditional Chant-Line Mode)**: Each daṇḍa forces a new line (one breath/pada per line).
     - **Mode C (Interactive Header Toggle)**: Allow users to toggle between continuous prose and line-by-line chant view.

---

### 2. Intermediate JSON AST Pipeline Expansion
* **Status**: 🟡 In Progress.
* **Target Area**: `src/baraha_reader.py`, `src/build_reader.py`.
* **Summary**:
  - Successfully decoupled *Siva Stuti* to build reliably via `mockup/viewer/siva_stuti.json` AST.
  - Add `--from-json` CLI flag to `build_reader.py` to allow consuming pre-generated JSON ASTs across all books instead of parsing binary DOCX on every run.
  - Standardize JSON schema (`meta`, `supersections`, `sections`, `subsections`) across all books in `config.json`.

---

### 3. VedaVMS Team Collaboration & Workflow Sync
* **Status**: 📋 Scheduled.
* **Topics for Discussion**:
  - Source file lifecycle and document update policies.
  - Tooling and tech stack (Baraha sources, PDF generation, backup snapshots, and deployment).
