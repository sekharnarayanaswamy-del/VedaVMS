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

### 2. Unified Standalone HTML Viewer & Cross-Project Notes Component (VedaVMS, JSV, Gramageyaganam)
* **Status**: 📋 **Active / Backlog**
* **Target Area**: `vedavms` (`src/build_reader.py`), `jaimineeyasamavedam` (`src/renderers/html_common.py`), and `Converter-tools` (`gramageyaganam/src/generate_g1_html.py`).
* **Objective**:
  - Establish a single, shared, canonical standalone HTML viewer runtime and Post-It Notes / Bookmarks engine shared across **VedaVMS**, **Jaimineeya Samavedam (JSV)**, and **Gramageyaganam**.
  - Maximize code reuse across the three projects so enhancements and fixes made in one viewer propagate consistently to all, eliminating duplication and regression drift.
* **Core Capabilities to Unify**:
  1. **Autonomous Post-It Stationery & Bookmarks Entity System**:
     - Draggable sticky notes (`postit-entity`) with exact page coordinates and `localStorage` persistence.
     - Collapsible in-place folded tabs (`postit-inplace-tab`) with live preview tooltips.
     - Hover preview card (`postit-hover-card`) with safe auto-dismissal.
     - Bookmarks slide-out drawer (`bookmarks-drawer`) with live badge counts, full in-drawer editing (`textarea`), and direct jump navigation.
     - Immediate flush on close (`closeNote`) and debounce-protected auto-saving (`noteDebounce`) to ensure zero content loss.
     - Section-level bookmarking (`anuvaka-bm-btn`) with smooth, bounce-free scrolling.
     - Inline verse-level attachment buttons (`add-note-inline-btn`) and text selection tooltip (`selection-note-btn`).
  2. **Maximal HTML Standalone Viewer Code Reuse**:
     - Common header toolbar (`➕ Note`, `🔖 Notes`, Font Switcher, Font Zoom `A- / A+`, Fullscreen, Print modal).
     - Unified responsive 2-column reader layout (TOC sidebar with collapsible chapters/sections + main reading pane with mobile drawer toggle).
     - Unified Print CSS system (`@media print` clean book-layout formatting with UI button suppression).
     - Shared typography assets (`AdiShila Vedic`, `Noto Serif Devanagari`, `Tiro Sanskrit`, `Noto Sans`).
* **Implementation Plan**:
  - Extract common viewer assets (CSS, JS engine, toolbar controls, drawer templates) into a reusable shared module or package (e.g. `vedavms-viewer-core` or shared `html_common` library) consumed cleanly by all three repositories.

---

### 3. Intermediate JSON AST Pipeline Expansion (Closed / Deprecated)
* **Status**: ❌ **Closed / Deprecated** (Superseded by Direct Baraha SSOT Pipeline).
* **Target Area**: `src/baraha_reader.py`, `src/build_reader.py`.
* **Architectural Decision**:
  - Baraha source files (`.brh` / `.docx`) are the sole canonical **Single Source of Truth (SSOT)** in the VedaVMS correction workflow.
  - Converting from or maintaining static `.json` AST files introduces severe content drift: when an editor updates a Baraha source file, reading from an older JSON bypasses the correction completely.
  - The AST in `src/build_reader.py` operates strictly as an **ephemeral (in-memory)** compilation stage. Serialized JSON will never serve as a build input.
  - *Siva Stuti* was temporarily built via `siva_stuti.json` as an emergency stopgap due to malformed DOCX formatting, and will be migrated to clean direct Baraha input.

---

### 4. VedaVMS Team Collaboration & Workflow Sync
* **Status**: 📋 Scheduled.
* **Topics for Discussion**:
  - Source file lifecycle and document update policies.
  - Tooling and tech stack (Baraha sources, PDF generation, backup snapshots, and deployment).
---

## ✅ Recently Completed Items

### 4. Zero Dotted Circle Suppression & Multi-Script OpenType Auditing
* **Status**: ✅ **Completed & Deployed to Production**.
* **Target Area**: `src/transliterate.py`, `src/build_reader.py`, `src/audit_reader.py`.
* **Summary**:
  - **Freestanding Mark Suppression**: Added ` ‍` (NBSP + ZWJ) prefixing to Candrabindu / Anunāsika (`ँ` / `ഁ`), preventing OpenType layout shapers (HarfBuzz, DirectWrite, CoreText) from drawing fallback dotted circles (`◌`, `U+25CC`) on isolated marks.
  - **Malayalam Anusvara Attachment**: Fixed DOM tag boundary detachment where syllables like `स॒म्` transliterated to `സ` + `॒` + `ം`, resulting in `സ<span ...>ം` and triggering `◌ം`. Enforced that `[ംं]` always binds directly to the preceding consonant before accent spans (`സം<span class="accent-anudatta">&#x0952;</span>`).
  - **Multi-Script Automated Audit**: Integrated HarfBuzz OpenType layout shaping into `src/audit_reader.py` supporting both Devanagari (`AdishilaSan.ttf`) and Malayalam (`Nirmala.ttc`, `kartika.ttf`), along with structural DOM tag checks.
  - **Verification**: All 22 books report **0 [✓ PASS]** dotted circles and **100% TOC compliance** against authoritative reference PDFs in `build/audit_report.md`.
