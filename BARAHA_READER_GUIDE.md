# Vedic HTML Reader Generator from Baraha Sources

This guide documents the tools and workflow for converting Baraha ASCII `.docx` files into standalone, responsive, interactive Vedic HTML readers with authentic Devanagari typography and chant svara notation.

---

## 🏛️ System Architecture

The generator lives in the [`src/`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/src) package:

```
src/
├── __init__.py          # Package exports
├── transliterate.py     # Standalone Baraha -> Devanagari Unicode transliteration engine
├── baraha_reader.py     # DOCX to structured JSON AST extractor & parser
├── build_reader.py      # DOCX / AST section extractor & interactive HTML reader generator
└── config.json          # Multi-book definitions, regex rules, and font options
```

## 📂 Dual Baraha Format Support (.docx & .brh)

The VedaVMS engine provides first-class, concurrent support for **both Baraha source formats**:

| Dimension | Modern Direct Baraha (`.brh` / `.txt`) | Legacy Word Baraha (`.docx`) |
| :--- | :--- | :--- |
| **File Type** | Raw UTF-8 / ASCII text file | Compressed Word OpenXML package |
| **Parsing Engine** | Native line & regex parser (`parse_aak_brh()`) | Native XML extractor (`extract_docx_paragraphs()`) |
| **External Dependencies**| Zero (Standard Python library) | Zero (uses `zipfile` + `xml.etree.ElementTree`) |
| **Slicing & Filtering** | Native multi-chapter slicing (`--chapter 3.7`) | Regex-based section splitting |
| **Granular Invocations**| Fully indexes Dhyānam & preliminary passages (`.D`)| Index markers in brackets / headings |
| **Git Diff Visibility** | 100% human-readable text line diffs | Binary diff (opaque zip archive) |
| **Current Books in Prod**| 17 books (`AAK.brh` $
ightarrow$ TB 3.7 to 3.12 Sanskrit & Malayalam) | 5 books (Taittiriya Upanishad, Udaka Shanti, Shanti Japam, etc.) |

### Why We Support Both Formats
1. **Preserving Legacy Investments**: The historical VedaVMS corpus has valuable `.docx` files containing carefully typeset Baraha ASCII text. These can continue to be built without converting them first.
2. **Modernization via Direct `.brh`**: Newer editions (like `AAK.brh`) use direct `.brh` files because they are plain-text, version-controlled directly in Git, faster to compile, and immune to Word document corruption.
3. **Unified Transliteration**: Both formats feed into the exact same transliteration engine (`src/transliterate.py`). Svara accent positioning, zero dotted circle prevention, Visarga rules, and Option 1 atomic chanting padas are guaranteed to behave identically across both formats.

### Key Modules:

1. **[`src/transliterate.py`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/src/transliterate.py)**:
   * Pure Python transliterator converting Baraha ASCII phonetic scheme to Devanagari Unicode.
   * Parses Vedic swaras, nasals, punctuation, and applies canonical Unicode normalizations.
   * Guarantees **zero dotted circles** by ordering combining accents after base consonants, Visarga, or Anusvara.

2. **[`src/build_reader.py`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/src/build_reader.py)**:
   * Extracts raw paragraphs from Word `.docx` documents using Python standard library (`zipfile` + `xml.etree.ElementTree`).
   * No third-party dependencies required (no `python-docx` needed).
   * Segments paragraphs into structured chapters, anuvakas, and verses.
   * Generates the standalone HTML reader page with responsive navigation, typography controls, and interactive persistent bookmarks & Post-It study notes.

3. **[`src/config.json`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/src/config.json)**:
   * Declarative JSON configuration decoupling book metadata and chapter regexes from generator code.

---

## 🔡 Transliteration & Svara Encoding Reference

| Baraha Token | Unicode Character | Name / Function | Devanagari Example |
| :--- | :--- | :--- | :--- |
| `q` or `@an` | `॒` (U+0952) | Anudatta (bottom horizontal line) | `miqtraH` / `mi@antraH` $\rightarrow$ `मि॒त्रः` |
| `#` or `@sv` | `॑` (U+0951) | Svarita / Udatta (top vertical stroke) | `SannO#` / `SannO@sv` $\rightarrow$ `शन्नो॑` |
| `$` or `@ds` | `᳚` (U+1CDA) | Deergha Svarita (double vertical stroke) | `vyA$KyA` / `vyA@dsKyA` $\rightarrow$ `व्या᳚ख्या` |
| `&` or `@av` | `ऽ` (U+093D) | Avagraha | `tE &gnE` / `tE @avgnE` $\rightarrow$ `ते ऽग्ने` |
| `~ru`, `~rU` | `ऋ`, `ॠ` / `ृ`, `ॄ` | Vocalic R (independent & matra) | `~rujISha`, `k~ruShNa` $\rightarrow$ `ऋजीष`, `कृष्ण` |
| `(gm)`, `(gm~)` | `ꣳ` (U+A8F3) | Candrabindu Virama (Vedic Gum) | `(gm)` $\rightarrow$ `ꣳ` |
| `(gg)` | `ꣴ` (U+A8F4) | Devanagari Sign Ring Anusvara | `pA~NktA(gg)#` $\rightarrow$ `पा~ण्क्ताꣴ॑` |
| `~M` | `\u00A0ँ` (U+0901) | Candrabindu (with non-breaking space) | `SaM ~Mvaru#NaH` $\rightarrow$ `शं ँवरु॑णः` |
| `\|` / `\|\|` | `।` / `॥` | Danda / Double Danda | `\|` $\rightarrow$ `।`, `\|\|` $\rightarrow$ `॥` |
| `^` | `\u200C` | Zero-Width Non-Joiner (ZWNJ) | Prevents ligature forming |

### Canonical Normalization Rules:
* **Accent & Visarga Ordering**: In Baraha, `#H` or `qH` is reordered to `H#` / `Hq` (`ः॑` / `ः॒`) so the accent attaches properly to the Visarga without rendering a dotted circle.
* **Accent & Anusvara Ordering**: Accents immediately following `M` attach to the Anusvara (`ं॑` / `ं॒`).
* **Consecutive Virama Cleanup**: Duplicate viramas (`््`) are collapsed.
* **Whitespace & Accent Detachment**: Accents separated by whitespace or punctuation are stripped to prevent orphaned accent glyphs.
* **Alphanumeric Code Preservation**: Parenthesized combinations of letters and numbers (e.g. `(26B)`, `(9B)`, `(A26)`) are recognized as reference codes and preserved in English without Devanagari transliteration.
* **Swara Matra Duration Preservation**: Numerals in braces/parentheses such as `(3)` or `(2)` (e.g., `हा(3)`, `दो(2)`) represent matra duration for swaras and are preserved without being replaced or dropped.
* **Korvai & Inline Tag Protection**: Lines containing `Korvai`, `Special Korvai`, `Prapaataka Korvai`, or tagged with `</inline>` / `<inline>` are preserved in their original English form (e.g. `Special Korvai` instead of `स्पेचिअल् खोर्वै`).

---

## 📐 Vedic Structural Hierarchy & Terminology

In traditional Vedic taxonomy and the VedaVMS digital reader architecture, the structural tiers map as follows:

```
Book / Kāṇḍa (Level 1)
 └── Chapter / Prapāṭhaka / Praśna (Level 2)
      └── Anuvāka / Subsection (Level 3)
           └── Verse / Mantra / Pada (Level 4)
```

| Hierarchy Level | Traditional Vedic Term | Digital / Reader Term | Description |
| :--- | :--- | :--- | :--- |
| **Level 1** | **Kāṇḍa / Aṣṭaka** (काण्ड / अष्टक) | **Book** | The major volume or division (e.g., Kāṇḍa 3 of Taittirīya Brāhmaṇa). |
| **Level 2** | **Prapāṭhaka / Praśna** (प्रपाठक / प्रश्न) | **Chapter** | The overarching thematic discourse or chapter (e.g., Praśna 7: *Achidram*). |
| **Level 3** | **Anuvāka** (अनुवाक) | **Subsection** | The primary chant section containing a specific set of mantras. In technical audits, **Subsection $\equiv$ Anuvāka**. |
| **Level 4** | **Rik / Mantra / Pada** (ऋक् / मन्त्र / पद) | **Verse Paragraph** | Individual chant sentences and phrases bounded by daṇḍas (`।` / `॥`). |

### Concrete Example from Achidram (`TB 3.7`)

* **Book Level**: Taittirīya Brāhmaṇa, 3rd Aṣṭaka (`तृतीयाष्टकम्`)
* **Chapter Level (Level 2)**: `3.7` — तैत्तिरीय ब्राह्मणे तृतियाष्टके सप्तमः प्रपाठकः (अच्छिद्रं) (*Prapāṭhaka 7: Achidram*)
* **Subsection Level (Level 3 - Anuvāka)**:
  * `3.7.1` (Anuvāka 1): दर्शपूर्णमासेष्टिविषयाणि कानि चित्प्रायश्चित्तानि
  * `3.7.2` (Anuvāka 2): अग्निहोत्रसाम्नाय्यसाधारणानि प्रायश्चित्तानि
  * `...`
  * `3.7.14` (Anuvāka 14): दीक्षोपसत्सु प्रायश्चित्तविशेषाः
* **Verse Level (Level 4 - Pada)**:
  * Atomic chant units inside Anuvāka 3.7.1:
    `<span class="chant-pada">सुमित्रा न आप ओषधयः सन्तु दुर्मित्रास्तस्मै भूयासुः...&nbsp;।</span>`

### Role of `.brh` vs. Reference PDFs:
* **Can we work with the hierarchy directly from `.brh`?**  
  **Yes, completely.** The `.brh` file contains all chapter markers, section numbers (`3.7.1`, `3.7.2`), mantra text, and svara accents. It is the self-contained, canonical **Single Source of Truth** for the entire text hierarchy.
* **Do we need to look into the PDF anymore?**  
  **No.** The reference PDF is only an external static benchmark used by `src/audit_reader.py` for optional post-generation verification. The HTML generator does not depend on the PDF in any way.

---

## 🚀 CLI Usage & Commands

All scripts run with pure Python 3 (standard library only):

### 1. Build Readers from Config
```bash
# Build the default configured book (Taittiriya Upanishad)
python src/build_reader.py

# Build all books configured in src/config.json
python src/build_reader.py --all

# Build specific books by ID defined in src/config.json
python src/build_reader.py --book taittiriya_upanishad
python src/build_reader.py --book aak                     # Sanskrit Reader
python src/build_reader.py --book aak_malayalam           # Malayalam Transliteration Reader
python src/build_reader.py --book tb_complete

# Direct File to HTML Reader Conversion (.brh, .txt, or .docx):
python src/build_reader.py "data/baraha/AAK.brh"
python src/build_reader.py "data/baraha/AAK.brh" --lang malayalam --output "build/viewer/aak_malayalam.html"
python src/build_reader.py "data/baraha/Taittiriya Upanishad Baraha.docx"
python src/build_reader.py --direct "data/baraha/AAK.brh" --output "build/viewer/aak_sanskrit.html"

# Batch Process an Entire Directory or Glob of Baraha Files:
python src/build_reader.py --batch "data/baraha/"
python src/build_reader.py --batch "data/baraha/*.brh"
python src/build_reader.py "data/baraha/"
```

### Direct Conversion in `src/config.json`:
Any book entry in [`src/config.json`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/src/config.json) can specify `"direct": true` to use the unified direct conversion pipeline:
```json
"tb_complete": {
  "title": "तैत्तिरीय ब्राह्मणम् (तृतीय काण्डम्, प्रपाठक ७ - १२)",
  "title_sanskrit": "तैत्तिरीय ब्राह्मणम् ३.७ - ३.१२",
  "subtitle": "कृष्ण यजुर्वेदीय तैत्तिरीय ब्राह्मणम् (अच्छिद्रं, अश्वमेधं, काठकम्)",
  "input_docx": "data/baraha/TB 3.7-3.12 Baraha.docx",
  "output_html": "build/viewer/tb_complete_sanskrit.html",
  "pdf_path": "data/pdf/TB 3.7-3.12 Sanskrit.pdf",
  "direct": true,
  "chapter_regex": "^(3\\.(?:[7-9]|1[0-2]))\\t?\\s+(.*(?:prapAThaka|praSna).*)$",
  "back_link": "../index.html",
  "back_label": "← Home"
}
```

### 2. Output Location & Directory Structure
All generated readers and the HTML viewer hub are located in the dedicated `/viewer/` subfolder:
- Directory Hub: [`build/viewer/html_viewer.html`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/build/viewer/html_viewer.html) (or `build/viewer/index.html`)
- Taittiriya Upanishad: [`build/viewer/taittiriya_upanishad_sanskrit.html`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/build/viewer/taittiriya_upanishad_sanskrit.html)
- Shiva Stuti: [`build/viewer/siva_stuti_sanskrit.html`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/build/viewer/siva_stuti_sanskrit.html)
- Shanti Japam: [`build/viewer/shanti_japam_sanskrit.html`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/build/viewer/shanti_japam_sanskrit.html)
- Udaka Shanti: [`build/viewer/udaka_shanti_sanskrit.html`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/build/viewer/udaka_shanti_sanskrit.html)
- Udaka Shanti Anushangam: [`build/viewer/udaka_shanti_anushangam_sanskrit.html`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/build/viewer/udaka_shanti_anushangam_sanskrit.html)
- TB 3.7 (अच्छिद्रं): [`build/viewer/tb_3_7_achidram_sanskrit.html`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/build/viewer/tb_3_7_achidram_sanskrit.html)
- TB 3.8 (अश्वमेधं-वैश्वदेवम्): [`build/viewer/tb_3_8_aswamedham_vaiswadevam_sanskrit.html`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/build/viewer/tb_3_8_aswamedham_vaiswadevam_sanskrit.html)
- TB 3.9 (अश्वमेधं-हविर्धानम्): [`build/viewer/tb_3_9_aswamedham_havirdhanam_sanskrit.html`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/build/viewer/tb_3_9_aswamedham_havirdhanam_sanskrit.html)

### 3. Multi-Prapāṭhaka Slicing Support (Taittiriya Brahmana)
For composite source documents containing multiple prapāṭhakas in a single DOCX (such as `data/baraha/TB 3.7-3.12 Baraha.docx`), [`src/baraha_reader.py`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/src/baraha_reader.py) and [`src/build_reader.py`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/src/build_reader.py) automatically slice the source document into individual prapāṭhaka sections with exact Anuvaka Table of Contents matching canonical reference PDFs.

### 4. Override Paths on the Fly
```bash
python src/build_reader.py --input data/baraha/Taittiriya\ Upanishad\ Baraha.docx --output build/viewer/taittiriya_upanishad_sanskrit.html
```

### 5. Test Transliteration Standalone
```bash
python src/transliterate.py
```

---

## 📖 How to Add a New Vedic Book

To configure a new book (e.g., *Taittiriya Aranyakam*):

1. Place your Baraha `.docx` source file in `data/baraha/` (e.g. `data/baraha/ta_baraha.docx`).
2. Add a new book entry in [`src/config.json`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/src/config.json):

```json
{
  "books": {
    "taittiriya_aranyakam": {
      "title": "तैत्तिरीय आरण्यकम्",
      "subtitle": "कृष्ण यजुर्वेदीय तैत्तिरीय आरण्यकम् (सस्वरम्)",
      "input_docx": "data/baraha/ta_baraha.docx",
      "output_html": "build/viewer/taittiriya_aranyakam_sanskrit.html",
      "pdf_path": "data/pdf/Taittiriya Aranyakam Sanskrit.pdf",
      "back_link": "../index.html",
      "back_label": "← Home",
      "chapter_regex": "^([1-6])(?!\\.)\\s*(.*(?:prashna|aranya).*)$"
    }
  }
}
```

3. Run the generator:
```bash
python src/build_reader.py --book taittiriya_aranyakam
```

---

## 🎨 Interactive Reader Features

The generated HTML reader provides:
* **Responsive Navigation Header**: Streamlined controls across desktop and mobile devices. On mobile screens (≤ 850px), the header cleanly groups branding and essential navigation (`☰ सूची` and `← Home`) into a top bar with dedicated font switcher and zoom controls (`A-`, `100%`, `A+`, `🖨️ Print`, `▲ Top`) centered below to prevent horizontal overflow.
* **Sidebar Table of Contents (सूची / TOC)**: 
  * **Desktop**: Hierarchical Chapter and Anuvaka navigation panel alongside the text, collapsible via `☰ सूची`.
  * **Mobile**: Off-canvas slide-out drawer with a darkened backdrop and quick-close button (`✕`). Tapping any chapter or anuvaka link jumps directly to the target verse and automatically closes the drawer.
* **Dynamic Font Switcher**: Toggles between curated Vedic fonts loaded from Google Fonts and local packages:
  * *Noto Serif Devanagari* (Default)
  * *Tiro Devanagari Sanskrit*
  * *Noto Sans Devanagari*
  * *Adishila San* (Local true-type Vedic font)
* **Mobile-Responsive Layout**: Prevents squishing and layout breaking on small screens; verses render in full-width typography.
* **Print Stylesheet**: Hides navigation headers and controls when printing or saving as PDF (`Ctrl+P` / `Cmd+P`).

---

## 📋 Refactoring Roadmap & To-Do Items: Intermediate JSON AST

To decouple binary DOCX extraction from HTML/PDF rendering across VedaVMS, the project supports generating an intermediate JSON AST:

### Status
- [x] **`src/baraha_reader.py` added**: Standalone DOCX $\rightarrow$ JSON AST parser moved from the JSV research branch to VedaVMS.
- [x] Tested with `tu_baraha.docx` $\rightarrow$ `tu_baraha.json` (6 sections, complete Devanagari verse hierarchy).

### To-Do
1. **Optionally Decouple `build_reader.py`**:
   - Add a `--from-json` CLI flag to `build_reader.py` (e.g. `python src/build_reader.py --from-json tu_baraha.json`).
   - Allow `build_reader.py` to consume the pre-generated JSON AST directly instead of parsing raw OpenXML `.docx` on every run.
2. **Schema Standardization for VedaVMS Books**:
   - Verify that all books in `config.json` (Taittiriya Upanishad, Taittiriya Brahmana, Aranyakam, etc.) produce consistent JSON schemas with `meta`, `supersections`, `sections`, and `subsections`.
3. **Multi-Format Downstream Target Support**:
   - Use the JSON AST as the single source of truth for generating future targets (e.g., XeLaTeX/PDF booklets, EPUB, or search indexes) without re-parsing DOCX files.

### For discussion with VedaVMS team
We should have a session to demo their workflow:  
- Tools and technology: Working with sources,tools, pdf generation, documentation, backups, etc.
- Content related: Document update policies and pratices.

---

## 📌 Product Backlog & To-Do Items

### 1. Atomic Chanting Padas & Chanting Layout Refinement (Input Sources & Line Formatting)

> [!NOTE]
> **Status**: Paused pending review of upstream input files. Documented as open To-Do item for future enhancement.

#### Problem Context (Identified in Udaka Shanti ASCT & Other DOCX Books)
* **Punctuation Discrepancy**: Unlike Taittirīya Brāhmaṇa (AAK.brh), which contains disciplined | (daṇḍa) delimiters after every 3–6 words, legacy Word .docx documents (e.g., Udaka Shanti ASCT Baraha.docx) frequently feature entire Anuvāka passages (such as TS 1.1.1 continuous text in Section 1.2 *Vedadhaya*) without any internal | daṇḍas, terminating only with || 1.
* **Current Fallback Limitation**: Because wrap_chant_padas relies on । and ॥ to identify atomic units, sentences exceeding 85 characters without internal daṇḍas fall back to .chant-pada-long (white-space: normal). The browser then wraps text arbitrarily mid-compound across screen margins (e.g., आप्यायद्धमघ्निया देवभाग / मूर्जस्वतीः).
* **Inconsistent Line Breaks**: Some source documents contain manual line breaks mid-sentence without daṇḍas (e.g. अग्निमीळे पुरोहितं-यज्ञस्य), causing isolated fragments on individual lines, while adjacent padas with daṇḍas pack side-by-side (देवमृत्विजं ।  होतारं रत्न धातमं ।).

#### Backlog Items & Action Plan
1. **Source File Audit & Improvement**:
   - Check if improved/standardized Baraha .docx or .brh source files can be obtained with canonical chanting daṇḍas (|) at authentic breath/pada boundaries (matching traditional Veda Pathashala recitation and AAK.brh).
   - Standardize accidental carriage returns / line breaks across Word documents before parsing.
2. **Rendering Layout Enhancements (To be implemented once sources are reviewed)**:
   - **Mode A: Flowing Atomic Padas**: Refine fallback wrapping so long continuous blocks wrap only at word/avāntara boundaries rather than breaking arbitrary syllables.
   - **Mode B: Traditional Chant-Line Mode**: Option to format every daṇḍa (। / ॥) on its own visual line (one breath/pada per line).
   - **Mode C: User Toggle**: Provide an interactive header switch (Chant View: Pada | Flow) allowing students to switch between continuous prose and line-by-line chant practice.

