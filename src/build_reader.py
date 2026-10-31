"""VedaVMS Reader Generator: Converts Baraha DOCX documents into standalone responsive Vedic HTML Readers.

Features:
- DOCX paragraph extraction via standard library (zipfile + xml.etree.ElementTree).
- Phonetic and Vedic svara transliteration via transliterate.py.
- Chapter and Anuvaka TOC navigation tree (desktop sticky sidebar & mobile off-canvas drawer).
- Dynamic font switcher (Noto Serif Devanagari, Tiro Devanagari Sanskrit, Noto Sans, Adishila San).
- Responsive header and font-size scaling controls (A+ / A-) preventing mobile overflow.
- Zero external package dependencies.
"""

import os
import sys
import re
import json
import zipfile
import argparse
import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

try:
    from .transliterate import baraha_to_devanagari, is_english_text
except ImportError:
    try:
        from transliterate import baraha_to_devanagari, is_english_text
    except ImportError:
        _cur = Path(__file__).resolve().parent
        for _p in [_cur, _cur.parent / "src", _cur.parent / "vedavms_html"]:
            if str(_p) not in sys.path:
                sys.path.insert(0, str(_p))
        from transliterate import baraha_to_devanagari, is_english_text

DOCX_NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def esc(text: str) -> str:
    """Escape text for HTML attribute values."""
    return text.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')


def extract_docx_paragraphs(docx_path: str | Path) -> list[str]:
    """Extract raw paragraphs from a Word (.docx) document."""
    docx_path = Path(docx_path)
    if not docx_path.exists():
        for cand in [Path("data/baraha") / docx_path, Path(__file__).parent.parent / "data/baraha" / docx_path, Path(__file__).parent.parent / docx_path, Path("vedavms_html") / docx_path, Path(__file__).parent / docx_path, Path(__file__).parent.parent / "vedavms_html" / docx_path]:
            if cand.exists():
                docx_path = cand
                break
        else:
            raise FileNotFoundError(f"Input document not found: {docx_path}")

    with zipfile.ZipFile(docx_path, 'r') as z:
        doc_xml = z.read('word/document.xml')

    root = ET.fromstring(doc_xml)
    paras = []
    for p in root.findall('.//w:p', DOCX_NS):
        parts = []
        for node in p.iter():
            tag = node.tag.split('}')[-1] if '}' in node.tag else node.tag
            if tag == 't' and node.text:
                parts.append(node.text)
            elif tag == 'tab':
                parts.append('\t')
        text = ''.join(parts).strip()
        if text:
            paras.append(text)

    return paras


def parse_chapters_and_sections(raw_paras: list[str], chapter_regex: str | None = None) -> list[dict]:
    """Parse raw paragraphs into structured chapters and anuvaka sections."""
    ch_pattern = re.compile(chapter_regex, re.I) if chapter_regex and chapter_regex.strip() else None

    chapters = []
    current_chapter = None
    current_section = None

    for p in raw_paras:
        ch_m = ch_pattern.match(p) if ch_pattern else None
        if ch_m and not re.search(r'[q#$|]', p):
            ch_num = int(ch_m.group(1))
            ch_raw_title = ch_m.group(2).strip() if ch_m.lastindex >= 2 and ch_m.group(2) else ''
            
            # Guard against non-forward chapter numbers, verse enumerations, and cross-references
            excluded_starts = (
                'nakShatraM', 'OM', 'Oum', 'CatraM', 'vAdyaM', 'gItaM', 'aSvaM', 'rathaM',
                'paurNamAsi', 'amAvAsi', 'candramA', 'ahO', 'uShA', 'nakShatraH',
                'sUryaH', 'aditiH', 'viShNuH', 'agniH', 'anumatI', 'havyavAhaH'
            )
            is_valid_new_chapter = True
            if current_chapter is not None and ch_num <= current_chapter['num']:
                is_valid_new_chapter = False
            elif any(ch_raw_title.startswith(x) for x in excluded_starts) or 'item No.' in ch_raw_title:
                is_valid_new_chapter = False

            if is_valid_new_chapter:
                ch_deva = baraha_to_devanagari(ch_raw_title) if ch_raw_title else ''
                current_chapter = {
                    'num': ch_num,
                    'title_raw': ch_raw_title,
                    'title_deva': f"{ch_num}. {ch_deva}" if ch_deva else f"{ch_num}.",
                    'title_display_deva': f"{ch_num}. {ch_deva}" if ch_deva else f"{ch_num}.",
                    'title_display_raw': f"{ch_num}. {ch_raw_title}" if ch_raw_title else f"{ch_num}.",
                    'sections': []
                }
                chapters.append(current_chapter)
                current_section = None
                continue

        sec_m = re.match(r'^(\d+\.\d+(?:\.\d+)?)\s*(.*)', p)
        tb_m = re.match(r'^(T\.B\.\d+\.\d+\.\d+\.\d+)', p)

        if current_chapter is None:
            # If no chapter matched yet or chapter_regex is blank, auto-initialize Chapter 1 at the first section
            if sec_m or tb_m or p.startswith('T.A.'):
                current_chapter = {
                    'num': 1,
                    'title_raw': 'Text',
                    'title_deva': '1. ग्रन्थः',
                    'title_display_deva': '1. ग्रन्थः',
                    'title_display_raw': '1. Text',
                    'sections': []
                }
                chapters.append(current_chapter)
            else:
                continue

        if sec_m:
            sec_num = sec_m.group(1)
            sec_name = sec_m.group(2).strip()
            sec_deva = baraha_to_devanagari(sec_name) if sec_name else ''
            current_section = {
                'num': sec_num,
                'title_raw': sec_name,
                'title_deva': sec_deva,
                'ta_code': '',
                'content_deva': [],
                'content_raw': []
            }
            current_chapter['sections'].append(current_section)
            continue
        elif current_chapter['num'] == 6 and tb_m:
            sec_num = tb_m.group(1)
            current_section = {
                'num': sec_num,
                'title_raw': '',
                'title_deva': '',
                'ta_code': sec_num,
                'content_deva': [],
                'content_raw': []
            }
            current_chapter['sections'].append(current_section)
            continue

        if p.startswith('T.A.'):
            if current_section and not current_section.get('content_raw') and not current_section.get('ta_code'):
                current_section['ta_code'] = p
                continue

        if current_section is not None:
            current_section['content_raw'].append(p)
            current_section['content_deva'].append(baraha_to_devanagari(p))
        elif current_chapter is not None:
            if not current_chapter['sections']:
                ch_title = current_chapter.get('title_raw', '')
                ch_deva = baraha_to_devanagari(ch_title) if ch_title else ''
                current_section = {
                    'num': str(current_chapter['num']),
                    'title_raw': ch_title,
                    'title_deva': ch_deva,
                    'ta_code': '',
                    'content_raw': [p],
                    'content_deva': [baraha_to_devanagari(p)],
                    'is_intro': True
                }
                current_chapter['sections'].append(current_section)
            else:
                current_chapter['sections'][-1]['content_raw'].append(p)
                current_chapter['sections'][-1]['content_deva'].append(baraha_to_devanagari(p))

    return chapters


def format_vedic_html(text: str) -> str:
    """Format Vedic Sanskrit text for HTML rendering.
    
    - Keeps Visarga (ः) contiguous with base syllable to eliminate dotted circles (◌ः) across all fonts (Tiro Sanskrit, Noto, etc.)
    - For syllables ending in Visarga, applies .accent-visarga with negative offset so the accent mark
      sits directly above/below the previous syllable without drifting past the visarga
    - Wraps combining accent marks in zero-width positioned spans with elevated clearance
    - Applies independent accent font-size, font-weight, and elevation across all fonts
    """
    if not text:
        return text

    # Pass through raw HTML (tables, custom blocks) as-is
    if text.startswith('<table') or text.startswith('<div') or text.startswith('<!--'):
        return text

    # Pass through pure English text as-is (only if no Indic or Vedic accents present)
    if not re.search(r'[\u0900-\u097F\u0D00-\u0D7F\u0951\u0952\u1CDA\uA8E0-\uA8FF]', text) and is_english_text(text):
        return text

    # 1. Normalize ASCII colons to Visarga (only outside HTML tags)
    text = re.sub(r':(?![^<]*>)', 'ः', text)

    # 2. Reorder accents that landed before Visarga so syllable + Visarga remain contiguous
    text = re.sub(r'([\u0951\u0952\u1CDA]+)\s*([ःഃ])', r'\2\1', text)

    # Stop shirorekha over visarga in Devanagari:
    # Insert &zwnj; before Devanagari Visarga (ः) when preceded by a Devanagari character,
    # so OpenType shaping terminates the top stroke over the previous syllable and leaves the visarga freestanding.
    text = re.sub(r'([\u0904-\u094F\u0955-\u097F])(?<!\u200c)(?<!&zwnj;)ः', r'\1&zwnj;ः', text)

    # 3. Accents following Visarga receive .accent-visarga to shift backwards over the syllable
    for vis in ('&zwnj;ः', 'ः', 'ഃ'):
        text = text.replace(f'{vis}\u0951', f'{vis}<span class="accent-swarita accent-visarga">&#x0951;</span>')
        text = text.replace(f'{vis}\u1CDA', f'{vis}<span class="accent-deergha accent-visarga">&#x1CDA;</span>')
        text = text.replace(f'{vis}\u0952\u0952', f'{vis}<span class="accent-anudatta accent-visarga">&#x0952;&#x0952;</span>')
        text = text.replace(f'{vis}\u0952', f'{vis}<span class="accent-anudatta accent-visarga">&#x0952;</span>')


    # 4. Standard accents (on syllables without Visarga)
    # Svarita (U+0951)
    text = text.replace('\u0951', '<span class="accent-swarita">&#x0951;</span>')
    # Deergha Svarita (U+1CDA)
    text = text.replace('\u1CDA', '<span class="accent-deergha">&#x1CDA;</span>')
    # Anudatta (U+0952): handle double anudatta then single anudatta
    text = text.replace('\u0952\u0952', '<span class="accent-anudatta">&#x0952;&#x0952;</span>')
    text = text.replace('\u0952', '<span class="accent-anudatta">&#x0952;</span>')

    return text


def wrap_chant_padas(html_text: str) -> str:
    """Wraps sentences ending with dandas (| or ||) in <span class="chant-pada">...</span>
    so that each phrase and its danda remain atomic and do not wrap arbitrarily mid-sentence.
    """
    if not html_text or '<table' in html_text or '<div class="korvai' in html_text:
        return html_text

    pattern = re.compile(
        r'([^।॥\n]+(?:[।॥]+(?:\s*[\d\.\u0966-\u096F]+)?(?:\s*[।॥]+)?))'
    )

    parts = []
    last_end = 0
    for match in pattern.finditer(html_text):
        chunk = match.group(0).strip()
        if chunk:
            chunk = re.sub(r'\s+([।॥])', r'&nbsp;\1', chunk)
            clean_text = re.sub(r'<[^>]+>', '', chunk)
            clean_text = re.sub(r'&#x[0-9a-fA-F]+;', '', clean_text)
            clean_text = clean_text.replace('&zwnj;', '').replace('&nbsp;', ' ')
            if len(clean_text) <= 85:
                parts.append(f'<span class="chant-pada">{chunk}</span>')
            else:
                parts.append(f'<span class="chant-pada chant-pada-long">{chunk}</span>')
        last_end = match.end()

    remainder = html_text[last_end:].strip()
    if remainder:
        remainder = re.sub(r'\s+([।॥])', r'&nbsp;\1', remainder)
        clean_rem = re.sub(r'<[^>]+>', '', remainder)
        clean_rem = re.sub(r'&#x[0-9a-fA-F]+;', '', clean_rem)
        clean_rem = clean_rem.replace('&zwnj;', '').replace('&nbsp;', ' ')
        if len(clean_rem) <= 85 and ('।' in remainder or '॥' in remainder):
            parts.append(f'<span class="chant-pada">{remainder}</span>')
        else:
            parts.append(f'<span class="chant-pada chant-pada-long">{remainder}</span>')

    return ' '.join(parts) if parts else html_text


def generate_reader_html(book_meta: dict, chapters: list[dict], fonts: list[dict], default_font_size: float = 1.35) -> str:
    """Generate standalone responsive HTML reader with TOC navigation and typography controls."""
    title = book_meta.get("title", "Vedic Sanskrit Reader")
    subtitle = book_meta.get("subtitle", "कृष्ण यजुर्वेदीय आरण्यकम्")
    back_link = book_meta.get("back_link", "index.html")
    back_label = book_meta.get("back_label", "← Home")
    generated_at = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    target_lang = book_meta.get("lang") or ("malayalam" if "malayalam" in str(book_meta.get("output_html", "")).lower() else "sanskrit")
    if target_lang == "malayalam":
        html_lang = "ml"
        title_suffix = "Malayalam Vedic Text"
        google_fonts_link = '<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+Malayalam:wght@400;500;600;700&family=Noto+Sans+Malayalam:wght@400;500;600;700&family=Gayathri:wght@400;700&family=Manjari:wght@400;700&family=Noto+Serif+Devanagari:wght@400;600;700&display=swap" rel="stylesheet">'
        sidebar_btn_text = "☰ സൂചിക"
        sidebar_title_text = "സൂചിക (Contents)"
        default_font_name = fonts[0]['label'] if fonts else 'Noto Serif Malayalam'
    else:
        html_lang = "sa"
        title_suffix = "Sanskrit Vedic Text"
        google_fonts_link = '<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+Devanagari:wght@400;500;600;700&family=Tiro+Devanagari+Sanskrit:ital@0;1&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap" rel="stylesheet">'
        sidebar_btn_text = "☰ सूची"
        sidebar_title_text = "सूची (Contents)"
        default_font_name = "Noto Serif"

    fonts_js = json.dumps(fonts, ensure_ascii=False)

    deity_img = book_meta.get("deity_image")
    deity_name = book_meta.get("deity_name", "Sacred Deity")
    deity_portrait_html = ""
    if deity_img:
        deity_portrait_html = f'''            <div class="deity-portrait-wrapper">
                <img src="../assets/images/devatas/{deity_img}" alt="{esc(deity_name)}" class="deity-portrait-img" loading="lazy">
            </div>\n'''

    html_parts = []
    html_parts.append(f'''<!DOCTYPE html>
<html lang="{html_lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="generator" content="VedaVMS Reader Generator">
    <meta name="generated-at" content="{generated_at}">
    <title>{title} - {title_suffix}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    {google_fonts_link}
    <style>
        @font-face {{
            font-family: 'AdishilaVedic';
            src: local('AdishilaVedic'), url('fonts/AdishilaVedic.ttf') format('truetype'), url('../fonts/AdishilaVedic.ttf') format('truetype'), url('/fonts/AdishilaVedic.ttf') format('truetype');
            font-weight: 400 500;
            font-style: normal;
            font-display: swap;
            size-adjust: 110%;
        }}
        @font-face {{
            font-family: 'AdishilaVedic';
            src: local('AdishilaVedicBold'), local('AdishilaVedic-Bold'), url('fonts/AdishilaVedicBold.ttf') format('truetype'), url('../fonts/AdishilaVedicBold.ttf') format('truetype'), url('/fonts/AdishilaVedicBold.ttf') format('truetype');
            font-weight: 600 700;
            font-style: normal;
            font-display: swap;
            size-adjust: 110%;
        }}
        @font-face {{
            font-family: 'Adishila San';
            src: local('Adishila San'), url('fonts/AdishilaSan.ttf') format('truetype'), url('../fonts/AdishilaSan.ttf') format('truetype'), url('/fonts/AdishilaSan.ttf') format('truetype');
            font-weight: 400 500;
            font-style: normal;
            font-display: swap;
            size-adjust: 115%;
        }}
        @font-face {{
            font-family: 'Adishila San';
            src: local('Adishila San Bold'), local('AdishilaSan-Bold'), url('fonts/AdishilaSanBoldB.ttf') format('truetype'), url('../fonts/AdishilaSanBoldB.ttf') format('truetype'), url('/fonts/AdishilaSanBoldB.ttf') format('truetype');
            font-weight: 600 700;
            font-style: normal;
            font-display: swap;
            size-adjust: 115%;
        }}
        @font-face {{
            font-family: 'Adishila San';
            src: local('Adishila San Italic'), local('AdishilaSan-Italic'), url('fonts/AdishilaSanItalic.ttf') format('truetype'), url('../fonts/AdishilaSanItalic.ttf') format('truetype'), url('/fonts/AdishilaSanItalic.ttf') format('truetype');
            font-weight: 400 500;
            font-style: italic;
            font-display: swap;
            size-adjust: 115%;
        }}
        @font-face {{
            font-family: 'Adishila San';
            src: local('Adishila San Bold Italic'), local('AdishilaSan-BoldItalic'), url('fonts/AdishilaSanBoldItalic.ttf') format('truetype'), url('../fonts/AdishilaSanBoldItalic.ttf') format('truetype'), url('/fonts/AdishilaSanBoldItalic.ttf') format('truetype');
            font-weight: 600 700;
            font-style: italic;
            font-display: swap;
            size-adjust: 115%;
        }}

        :root {{
            --saffron: #D84315;
            --maroon: #7B1113;
            --cream: #FFFDF9;
            --gold: #C68A1E;
            --dark-brown: #2D1E18;
            --white: #FFFFFF;
            --card-bg: #FFFFFF;
            --border-color: #EADDC9;
            --accent-bg: #FFF3E0;
            --font-size: {default_font_size}rem;
            --mantra-size: calc(var(--font-size) * 1.18);
            --swarita-bottom: 0.2em;
            --anudatta-bottom: -0.25em;
            --accent-offset: -0.10em;
            --visarga-offset: {'-1.1em' if target_lang == 'malayalam' else '-0.35em'};
            --accent-font: 'AdishilaVedic', 'Adishila San', 'Noto Serif Devanagari', 'Tiro Devanagari Sanskrit', serif;
            --verse-font: 'Adishila San', 'AdishilaVedic', 'Noto Serif Devanagari', 'Tiro Devanagari Sanskrit', serif;
            --verse-weight: 500;
        }}

        html {{
            scroll-behavior: smooth;
            scroll-padding-top: 5rem;
            overflow-x: clip;
            width: 100%;
            max-width: 100%;
        }}

        .chapter-container, .anuvaka-block, [id] {{
            scroll-margin-top: 5rem;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: var(--verse-font);
            font-weight: var(--verse-weight);
            background: var(--cream);
            color: var(--dark-brown);
            line-height: 2.1;
            font-size: var(--font-size);
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            overflow-x: clip;
            width: 100%;
            max-width: 100%;
            margin: 0;
            padding: 0;
            position: relative;
            min-height: 100vh;
        }}

        .header {{
            background: linear-gradient(135deg, #153E75 0%, #1D5296 50%, #2563A8 100%);
            color: white;
            padding: 0.75rem 1rem;
            text-align: center;
            border-bottom: 3px solid var(--gold);
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 3px 12px rgba(0,0,0,0.18);
        }}

        .header-content {{
            max-width: 1560px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.6rem;
        }}

        .header-main-bar {{
            display: flex;
            align-items: center;
            gap: 0.85rem;
        }}

        .logo {{
            font-family: 'Noto Serif Devanagari', serif;
            font-size: 1.55rem;
            font-weight: 700;
            color: white;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 0.45rem;
            flex-shrink: 0;
        }}

        .om-symbol {{
            color: #FFD54F;
            font-size: 1.75rem;
        }}

        .header-quick-actions {{
            display: flex;
            align-items: center;
            gap: 0.45rem;
        }}

        .controls {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.45rem;
        }}

        .zoom-controls {{
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
        }}

        .btn-ctrl {{
            background: rgba(255,255,255,0.18);
            color: white;
            border: 1px solid rgba(255,255,255,0.35);
            border-radius: 6px;
            padding: 0.38rem 0.75rem;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.9rem;
            transition: all 0.2s;
            text-decoration: none;
            font-family: sans-serif;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            white-space: nowrap;
        }}

        .btn-ctrl:hover {{
            background: rgba(255,255,255,0.32);
            transform: translateY(-1px);
        }}

        .bm-badge {{
            background: #FFD54F;
            color: #5C2C00;
            font-size: 0.72rem;
            font-weight: 700;
            border-radius: 10px;
            padding: 0.1rem 0.45rem;
            margin-left: 0.35rem;
            line-height: 1.2;
            display: inline-block;
        }}

        .btn-ctrl.active {{
            background: #FFD54F;
            color: #3E1B00;
            border-color: #FFE082;
        }}

        .layout {{
            max-width: 1560px;
            width: 100%;
            margin: 1.75rem auto;
            padding: 0 1rem;
            display: grid;
            grid-template-columns: 290px minmax(0, 1fr);
            gap: 1.5rem;
            align-items: flex-start;
            box-sizing: border-box;
        }}

        .toc-sidebar {{
            background: var(--white);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1.25rem;
            position: sticky;
            top: 5.5rem;
            max-height: calc(100vh - 7rem);
            overflow-y: auto;
            box-shadow: 0 4px 14px rgba(0,0,0,0.06);
        }}

        /* Suchi Drawer Backdrop */
        .toc-backdrop {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.55);
            backdrop-filter: blur(2px);
            z-index: 2400;
            opacity: 0;
            transition: opacity 0.25s ease;
        }}

        .toc-header-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--saffron);
            padding-bottom: 0.4rem;
            margin-bottom: 0.85rem;
        }}

        .toc-title {{
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--maroon);
            font-family: 'Noto Serif Devanagari', serif;
            margin: 0;
            padding: 0;
        }}

        .toc-close-btn {{
            display: none;
            align-items: center;
            justify-content: center;
            background: #F4ECE1;
            border: 1px solid var(--border-color);
            color: var(--maroon);
            font-size: 1.1rem;
            font-weight: 700;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.2s ease;
            line-height: 1;
        }}

        .toc-close-btn:hover {{
            background: var(--accent-bg);
            color: var(--saffron);
            border-color: var(--saffron);
        }}

        .toc-list {{
            list-style: none;
        }}

        .toc-chapter {{
            margin-bottom: 0.5rem;
        }}

        .toc-ch-header {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            cursor: pointer;
            padding: 0.3rem 0.4rem;
            border-radius: 4px;
            transition: background 0.15s;
        }}

        .toc-ch-header:hover {{
            background: var(--accent-bg);
        }}

        .toc-ch-title {{
            font-weight: 700;
            color: var(--maroon);
            font-size: 1.06rem;
            flex: 1;
            letter-spacing: 0.01em;
        }}

        .toc-ch-title a {{
            color: var(--maroon);
            text-decoration: none;
        }}

        .toc-ch-toggle {{
            font-size: 0.7rem;
            color: #888;
            transition: transform 0.2s;
        }}

        .toc-chapter.collapsed .toc-ch-toggle {{
            transform: rotate(-90deg);
        }}

        .toc-sub-list {{
            list-style: none;
            padding-left: 0.75rem;
            overflow: hidden;
            max-height: 30000px;
            transition: max-height 0.35s ease;
        }}

        .toc-chapter.collapsed .toc-sub-list {{
            max-height: 0 !important;
            padding-top: 0;
            padding-bottom: 0;
        }}

        .toc-sub-list li {{
            margin-bottom: 0.25rem;
        }}

        /* Level 2: Major section link (e.g. 3.1, 3.7, 11.2) */
        .toc-sub-list li.toc-level-2 {{
            margin-top: 0.45rem;
            margin-bottom: 0.2rem;
        }}

        .toc-sub-list li.toc-level-2 a {{
            color: #1F1F1F;
            font-size: 0.93rem;
            font-weight: 600;
            padding: 0.22rem 0.4rem;
        }}

        /* Level 3: Subsection link (e.g. 3.1.1, 3.1.4, 3.7.1) */
        .toc-sub-list li.toc-level-3 {{
            margin-bottom: 0.15rem;
            padding-left: 0.65rem;
            border-left: 1.5px solid #F0E2D2;
            margin-left: 0.4rem;
        }}

        .toc-sub-list li.toc-level-3 a {{
            color: #555555;
            font-size: 0.85rem;
            font-weight: 400;
            padding: 0.15rem 0.35rem;
        }}

        .toc-sub-list li.toc-level-3 a:hover {{
            color: var(--saffron);
            font-weight: 600;
        }}

        .toc-sub-list a {{
            color: #4A4A4A;
            text-decoration: none;
            font-size: 0.9rem;
            display: block;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            transition: all 0.15s;
        }}

        .toc-sub-list a:hover {{
            background: var(--accent-bg);
            color: var(--saffron);
            font-weight: 600;
        }}

        .toc-sub-list a.active {{
            background: #FFE8D1 !important;
            color: #B23600 !important;
            font-weight: 700 !important;
            border-left: 3.5px solid var(--saffron);
            padding-left: 0.6rem;
            border-radius: 0 4px 4px 0;
            box-shadow: 0 1px 3px rgba(216, 67, 21, 0.12);
        }}

        /* Active Chapter header in TOC */
        .toc-chapter.active-chapter > .toc-ch-header {{
            background: rgba(216, 67, 21, 0.08);
            border-radius: 6px;
            border-left: 3.5px solid var(--saffron);
            padding-left: 0.5rem;
        }}

        .toc-chapter.active-chapter > .toc-ch-header .toc-ch-title a {{
            color: var(--saffron);
            font-weight: 700;
        }}

        /* Standalone chapter active link */
        .toc-chapter.toc-single.active-chapter > .toc-ch-header {{
            background: #FFE8D1 !important;
            border-left: 3.5px solid var(--saffron) !important;
            box-shadow: 0 1px 3px rgba(216, 67, 21, 0.12);
        }}

        .toc-chapter.toc-single.active-chapter .toc-ch-title a {{
            color: #B23600 !important;
            font-weight: 700 !important;
        }}

        /* Collapsible sidebar styles */
        .layout.sidebar-collapsed {{
            grid-template-columns: 0 1fr;
            gap: 0;
        }}

        .layout.sidebar-collapsed .toc-sidebar {{
            width: 0;
            min-width: 0;
            padding: 0;
            overflow: hidden;
            border: none;
            opacity: 0;
            pointer-events: none;
        }}

        .toggle-sidebar-btn {{
            background: rgba(255,255,255,0.22);
            color: white;
            border: 1px solid rgba(255,255,255,0.45);
            border-radius: 6px;
            padding: 0.38rem 0.8rem;
            cursor: pointer;
            font-weight: 700;
            font-size: 0.9rem;
            transition: all 0.2s;
            font-family: sans-serif;
            white-space: nowrap;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
        }}

        .toggle-sidebar-btn:hover {{
            background: rgba(255,255,255,0.35);
            transform: translateY(-1px);
        }}

        .main-content {{
            background: var(--white);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1.75rem 2rem;
            box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            --font-size: {default_font_size}rem;
            font-size: var(--font-size);
            min-width: 0;
            max-width: 100%;
            box-sizing: border-box;
            overflow-wrap: break-word;
            word-break: normal;
        }}

        .back-to-top {{
            position: fixed;
            bottom: 1.75rem;
            right: 1.75rem;
            width: 44px;
            height: 44px;
            background: var(--saffron);
            color: white;
            border: none;
            border-radius: 50%;
            font-size: 1.25rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(216,67,21,0.35);
            opacity: 0;
            visibility: hidden;
            transition: all 0.25s ease;
            z-index: 999;
        }}
        .back-to-top.visible {{
            opacity: 1;
            visibility: visible;
        }}
        .back-to-top:hover {{
            background: var(--maroon);
            transform: translateY(-2px);
        }}

        .main-title {{
            text-align: center;
            margin-bottom: 2.5rem;
            padding-bottom: 1.25rem;
            border-bottom: 2px solid var(--gold);
        }}

        .main-title h1 {{
            font-family: 'Noto Serif Devanagari', serif;
            font-size: 2.6rem;
            color: var(--maroon);
            margin-bottom: 0.5rem;
            letter-spacing: 0.5px;
        }}

        .main-title .sub-heading,
        .main-title .subheading {{
            font-family: 'Noto Serif Devanagari', 'Adishila San', 'Tiro Devanagari Sanskrit', serif;
            font-size: 2rem;
            color: var(--saffron);
            font-weight: 600;
            line-height: 1.45;
            margin-bottom: 0.6rem;
        }}

        .main-title .generation-timestamp {{
            font-family: monospace, system-ui, -apple-system, sans-serif;
            font-size: 0.84rem;
            color: #8C7B70;
            margin-top: 0.45rem;
            letter-spacing: 0.03em;
        }}

        .chapter-container {{
            margin-bottom: 3.5rem;
            min-width: 0;
            max-width: 100%;
            box-sizing: border-box;
        }}

        .chapter-heading {{
            background: linear-gradient(90deg, #7B1113 0%, #A52A2A 100%);
            color: white;
            padding: 1.05rem 1.85rem;
            border-radius: 8px;
            font-size: calc(var(--font-size) * 1.34);
            font-weight: 700;
            margin-bottom: 2rem;
            font-family: 'Noto Serif Devanagari', serif;
            box-shadow: 0 4px 12px rgba(123,17,19,0.28);
            letter-spacing: 0.015em;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.75rem;
        }}

        .anuvaka-block {{
            background: #FFFAF5;
            border: 1px solid #F0E6D8;
            border-left: 5px solid var(--saffron);
            border-radius: 8px;
            padding: 1.25rem 1.4rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 6px rgba(0,0,0,0.03);
            min-width: 0;
            max-width: 100%;
            box-sizing: border-box;
            overflow-wrap: break-word;
            transition: all 0.2s ease;
        }}

        /* Level 2: Major section card (e.g. 3.1, 3.7, 11.2) */
        .anuvaka-block.level-2 {{
            border-left: 6.5px solid var(--maroon);
            background: #FFFDF9;
            margin-bottom: 2.25rem;
            border-top: 1px solid #EADDC9;
        }}

        /* Level 3: Subsection card (e.g. 3.1.1, 3.1.4, 3.7.1) */
        .anuvaka-block.level-3 {{
            border-left: 4.5px solid var(--saffron);
            background: #FFFAF5;
            margin-bottom: 1.75rem;
            margin-left: 0.75rem;
        }}

        .anuvaka-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px dashed #E0D0C0;
            padding-bottom: 0.65rem;
            margin-bottom: 1.15rem;
            gap: 0.75rem;
        }}

        .anuvaka-num {{
            font-family: 'Noto Serif Devanagari', serif;
            display: inline-block;
        }}

        /* Level 2: Major section heading */
        .anuvaka-num.level-2 {{
            font-size: calc(var(--font-size) * 1.08);
            font-weight: 700;
            color: var(--maroon);
            letter-spacing: 0.01em;
        }}

        /* Level 3: Subsection heading */
        .anuvaka-num.level-3 {{
            font-size: calc(var(--font-size) * 0.90);
            font-weight: 600;
            color: #8B2500;
        }}

        .anuvaka-code {{
            font-family: monospace, system-ui, -apple-system, sans-serif;
            font-size: 0.88rem;
            font-weight: 700;
            color: var(--saffron-dark, #b76e00);
            background: rgba(224, 86, 36, 0.08);
            border: 1.5px solid rgba(224, 86, 36, 0.3);
            padding: 0.22rem 0.65rem;
            border-radius: 5px;
            letter-spacing: 0.03em;
            margin-left: auto;
            text-align: right;
            white-space: nowrap;
        }}

        .dark-mode .anuvaka-code {{
            color: #f4a261;
            background: rgba(244, 162, 97, 0.14);
            border-color: rgba(244, 162, 97, 0.35);
        }}

        .chapter-heading .chapter-code {{
            font-size: 0.85rem;
            font-weight: 600;
            vertical-align: middle;
            margin-left: auto;
            display: inline-block;
            color: #333;
            background: #FFFDF9;
            box-shadow: 0 1px 3px rgba(0,0,0,0.18);
        }}

        .inline-citation {{
            font-size: 0.86em;
            color: #6B5B52;
            font-family: monospace;
            background: rgba(0, 0, 0, 0.045);
            padding: 0.1em 0.38em;
            border-radius: 3px;
            vertical-align: baseline;
            font-weight: normal;
        }}

        .inline-citation:empty {{
            display: none !important;
        }}
        /* Anuvaka Header Layout & Actions */
        .anuvaka-header-left {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}

        .anuvaka-header-right {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-shrink: 0;
            margin-left: auto;
        }}

        .anuvaka-header.anuvaka-header-intro {{
            border-bottom: none;
            margin-bottom: 0.35rem;
            padding-bottom: 0;
            justify-content: flex-end;
        }}

        .anuvaka-bm-btn {{
            background: #FAF5EE;
            border: 1px solid #D7C4B2;
            color: #795548;
            border-radius: 6px;
            padding: 0.22rem 0.55rem;
            font-size: 0.78rem;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.28rem;
            transition: all 0.2s ease;
            line-height: 1.2;
            font-family: system-ui, -apple-system, sans-serif;
            user-select: none;
        }}

        .anuvaka-bm-btn:hover {{
            background: #FFF3E0;
            border-color: var(--saffron);
            color: var(--saffron);
            transform: translateY(-1px);
        }}

        .anuvaka-bm-btn.active {{
            background: linear-gradient(135deg, #FFF9C4 0%, #FFF59D 100%);
            border-color: #FBC02D;
            color: #7F5000;
            box-shadow: 0 1px 4px rgba(251, 192, 45, 0.35);
            font-weight: 700;
        }}

        /* --- Autonomous Square Post-It Entity System --- */
        #postit-overlay-layer {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1200;
        }}

        .postit-entity {{
            position: absolute;
            width: 235px;
            min-height: 210px;
            max-height: 310px;
            padding: 0.7rem 0.85rem 0.65rem;
            border-radius: 5px;
            box-shadow: 2px 6px 20px rgba(0, 0, 0, 0.18), 0 1px 4px rgba(0, 0, 0, 0.1);
            pointer-events: auto;
            font-family: 'Noto Sans', system-ui, -apple-system, sans-serif;
            border: 1px solid rgba(0, 0, 0, 0.14);
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            transform: rotate(-0.5deg);
            transition: box-shadow 0.2s ease;
            animation: postitPop 0.18s cubic-bezier(0.16, 1, 0.3, 1);
        }}

        @keyframes postitPop {{
            from {{
                opacity: 0;
                transform: scale(0.9) rotate(-1.5deg);
            }}
            to {{
                opacity: 1;
                transform: scale(1) rotate(-0.5deg);
            }}
        }}

        .postit-entity.dragging {{
            transform: scale(1.03) rotate(0deg) !important;
            box-shadow: 5px 14px 32px rgba(0, 0, 0, 0.28) !important;
            cursor: grabbing !important;
            user-select: none;
            z-index: 2000 !important;
        }}

        .postit-entity:hover {{
            box-shadow: 3px 9px 24px rgba(0, 0, 0, 0.22);
        }}

        /* Themes */
        .postit-theme-yellow {{ background: #FEF9C3; border-color: #FDE047; color: #713F12; }}
        .postit-theme-saffron {{ background: #FFEDD5; border-color: #FDBA74; color: #7C2D12; }}
        .postit-theme-green {{ background: #DCFCE7; border-color: #86EFAC; color: #14532D; }}
        .postit-theme-rose {{ background: #FFE4E6; border-color: #FDA4AF; color: #881337; }}

        /* In-Place Collapsed Sticky Tab Flag */
        .postit-inplace-tab {{
            position: absolute;
            z-index: 1190;
            pointer-events: auto;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.22rem 0.65rem 0.22rem 0.5rem;
            border-radius: 4px 12px 12px 4px;
            font-size: 0.78rem;
            font-family: 'Noto Sans', system-ui, -apple-system, sans-serif;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 1px 3px 10px rgba(0, 0, 0, 0.16), 0 1px 3px rgba(0,0,0,0.1);
            transform: rotate(-1deg);
            transition: transform 0.18s ease, box-shadow 0.18s ease;
            user-select: none;
            border: 1px solid rgba(0,0,0,0.18);
            border-left: 4px solid #EAB308;
            white-space: nowrap;
            max-width: 220px;
            overflow: hidden;
            text-overflow: ellipsis;
            animation: postitPop 0.15s ease;
        }}
        .postit-inplace-tab:hover {{
            transform: scale(1.08) rotate(0deg);
            box-shadow: 2px 6px 16px rgba(0, 0, 0, 0.24);
            z-index: 1250;
        }}
        .postit-inplace-tab.postit-theme-yellow {{ border-left-color: #EAB308; }}
        .postit-inplace-tab.postit-theme-saffron {{ border-left-color: #F97316; }}
        .postit-inplace-tab.postit-theme-green {{ border-left-color: #22C55E; }}
        .postit-inplace-tab.postit-theme-rose {{ border-left-color: #F43F5E; }}
        .postit-inplace-tab.dragging {{
            opacity: 0.85;
            transform: scale(1.1) rotate(0deg) !important;
            cursor: grabbing !important;
            z-index: 2200 !important;
        }}
        .inplace-tab-pin {{
            font-size: 0.85rem;
            filter: drop-shadow(1px 1px 1px rgba(0,0,0,0.25));
            flex-shrink: 0;
        }}
        .inplace-tab-title {{
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .postit-entity-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px dashed rgba(0, 0, 0, 0.15);
            padding-bottom: 0.35rem;
            margin-bottom: 0.45rem;
            gap: 0.4rem;
            cursor: grab;
            user-select: none;
        }}

        .postit-drag-handle {{
            display: flex;
            align-items: center;
            gap: 0.35rem;
            overflow: hidden;
            flex: 1;
            min-width: 0;
        }}

        .postit-pin {{
            font-size: 1rem;
            filter: drop-shadow(1px 2px 1px rgba(0,0,0,0.25));
            flex-shrink: 0;
        }}

        .postit-entity-title {{
            font-size: 0.78rem;
            font-weight: 700;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            letter-spacing: 0.02em;
        }}

        .postit-entity-tools {{
            display: flex;
            align-items: center;
            gap: 0.25rem;
            flex-shrink: 0;
            cursor: default;
        }}

        .postit-color-picker {{
            display: flex;
            gap: 0.2rem;
            margin-right: 0.25rem;
        }}

        .color-btn {{
            width: 13px;
            height: 13px;
            border-radius: 50%;
            border: 1px solid rgba(0,0,0,0.25);
            cursor: pointer;
            padding: 0;
            transition: transform 0.15s ease;
        }}
        .color-btn:hover, .color-btn.active {{
            transform: scale(1.35);
            box-shadow: 0 0 0 1.5px #333;
        }}
        .color-yellow {{ background: #FDE047; }}
        .color-saffron {{ background: #FB923C; }}
        .color-green {{ background: #4ADE80; }}
        .color-rose {{ background: #FB7185; }}

        .postit-tool-btn {{
            background: transparent;
            border: none;
            cursor: pointer;
            font-size: 0.88rem;
            color: inherit;
            opacity: 0.65;
            padding: 0.1rem 0.28rem;
            border-radius: 3px;
            line-height: 1;
            transition: all 0.15s ease;
        }}
        .postit-tool-btn:hover {{
            opacity: 1;
            background: rgba(0,0,0,0.08);
        }}
        .postit-tool-del:hover {{
            color: #DC2626;
            background: rgba(220, 38, 38, 0.15);
        }}
        .postit-tool-close {{
            font-weight: 700;
        }}

        .postit-entity-body {{
            display: flex;
            flex-direction: column;
            flex: 1;
            min-height: 0;
        }}

        .postit-textarea {{
            width: 100%;
            flex: 1;
            min-height: 110px;
            border: none;
            background: transparent;
            resize: none;
            font-family: inherit;
            font-size: 0.88rem;
            line-height: 1.45;
            color: inherit;
            outline: none;
            box-sizing: border-box;
            padding: 0;
        }}
        .postit-textarea::placeholder {{
            color: inherit;
            opacity: 0.55;
            font-style: italic;
        }}

        .postit-footer-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.35rem;
            padding-top: 0.25rem;
            border-top: 1px dotted rgba(0, 0, 0, 0.15);
            font-size: 0.7rem;
            gap: 0.4rem;
        }}

        .postit-status {{
            opacity: 0.7;
        }}

        .postit-done-btn {{
            background: rgba(0, 0, 0, 0.08);
            border: 1px solid rgba(0, 0, 0, 0.15);
            color: inherit;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 0.18rem 0.55rem;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.15s ease;
            line-height: 1.2;
        }}
        .postit-done-btn:hover {{
            background: rgba(0, 0, 0, 0.16);
            transform: translateY(-1px);
        }}

        /* Verse line inline add button and pin markers */
        .verse-p {{
            position: relative;
            line-height: 2.2;
            word-break: keep-all;
        }}

        /* Option 1: Atomic Chanting Padas - Keeps sentence + danda together */
        .chant-pada {{
            display: inline-block;
            white-space: nowrap;
            margin-right: 0.35em;
            vertical-align: baseline;
        }}
        .chant-pada-long {{
            display: inline;
            white-space: normal;
        }}

        @media (max-width: 600px) {{
            .chant-pada {{
                display: inline;
                white-space: normal;
                margin-right: 0;
            }}
        }}
        .add-note-inline-btn {{
            background: transparent;
            border: none;
            color: #C07040;
            font-size: 0.78rem;
            cursor: pointer;
            opacity: 0;
            margin-left: 0.5rem;
            vertical-align: middle;
            transition: all 0.2s ease;
            padding: 0.1rem 0.3rem;
            border-radius: 4px;
            line-height: 1;
            user-select: none;
        }}
        .verse-p:hover .add-note-inline-btn {{
            opacity: 0.7;
            background: rgba(216, 67, 21, 0.08);
        }}
        .add-note-inline-btn:hover {{
            opacity: 1 !important;
            background: var(--saffron) !important;
            color: white !important;
            transform: scale(1.15);
        }}

        /* Pin badge when closed */
        .verse-pin-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            margin-left: 0.5rem;
            font-size: 0.76rem;
            font-family: system-ui, -apple-system, sans-serif;
            font-weight: 600;
            cursor: pointer;
            padding: 0.12rem 0.45rem;
            border-radius: 12px;
            vertical-align: middle;
            transition: all 0.15s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        }}
        .verse-pin-badge:hover {{
            transform: scale(1.1);
            box-shadow: 0 2px 8px rgba(0,0,0,0.22);
        }}
        .verse-pin-yellow {{ background: #FEF9C3; border: 1px solid #FDE047; color: #713F12; }}
        .verse-pin-saffron {{ background: #FFEDD5; border: 1px solid #FDBA74; color: #7C2D12; }}
        .verse-pin-green {{ background: #DCFCE7; border: 1px solid #86EFAC; color: #14532D; }}
        .verse-pin-rose {{ background: #FFE4E6; border: 1px solid #FDA4AF; color: #881337; }}


        /* Hover Preview Card for Notes */
        .postit-hover-card {{
            position: absolute;
            z-index: 99999;
            width: 220px;
            max-width: 85vw;
            padding: 0.65rem 0.8rem;
            border-radius: 6px;
            box-shadow: 2px 8px 24px rgba(0, 0, 0, 0.25), 0 2px 6px rgba(0, 0, 0, 0.12);
            pointer-events: none;
            font-family: 'Noto Sans', system-ui, -apple-system, sans-serif;
            font-size: 0.82rem;
            line-height: 1.45;
            transform: translateY(-4px) rotate(-0.5deg);
            transition: opacity 0.15s ease, transform 0.15s ease;
            opacity: 0;
            display: none;
            border: 1px solid rgba(0, 0, 0, 0.18);
        }}

        .postit-hover-card.visible {{
            opacity: 1;
            display: block;
            transform: translateY(0) rotate(-0.5deg);
        }}

        .hover-card-header {{
            display: flex;
            align-items: center;
            gap: 0.35rem;
            font-weight: 700;
            font-size: 0.76rem;
            border-bottom: 1px dashed rgba(0,0,0,0.18);
            padding-bottom: 0.25rem;
            margin-bottom: 0.35rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .hover-card-content {{
            word-break: break-word;
            white-space: pre-wrap;
            max-height: 160px;
            overflow: hidden;
        }}

        .postit-drag-handle {{
            cursor: move;
            cursor: grab;
        }}

        .postit-drag-handle:active {{
            cursor: grabbing;
        }}

        /* Floating Selection Note Button */
        .selection-note-btn {{
            position: absolute;
            z-index: 1300;
            background: var(--maroon);
            color: white;
            border: 1px solid var(--gold);
            border-radius: 16px;
            padding: 0.32rem 0.75rem;
            font-size: 0.78rem;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
            display: none;
            align-items: center;
            gap: 0.3rem;
            animation: postitPop 0.15s ease;
            white-space: nowrap;
        }}
        .selection-note-btn:hover {{
            background: var(--saffron);
            transform: scale(1.05);
        }}

                /* Bookmarks Slide-out Drawer */
        .bm-drawer-backdrop {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.45);
            backdrop-filter: blur(2px);
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.25s ease;
        }}

        .bm-drawer-backdrop.active {{
            display: block;
            opacity: 1;
        }}

        .bookmarks-drawer {{
            position: fixed;
            top: 0;
            right: 0;
            width: min(90vw, 380px);
            height: 100vh;
            background: #FFFDF9;
            box-shadow: -4px 0 24px rgba(0,0,0,0.22);
            z-index: 10001;
            transform: translateX(105%);
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            flex-direction: column;
            border-left: 2px solid var(--border-color);
        }}

        .bookmarks-drawer.active {{
            transform: translateX(0);
        }}

        .bm-drawer-header {{
            background: linear-gradient(135deg, #153E75 0%, #1D5296 100%);
            color: white;
            padding: 1.1rem 1.25rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--gold);
        }}

        .bm-drawer-title {{
            font-weight: 700;
            font-size: 1.05rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .bm-drawer-count {{
            background: #FFD54F;
            color: #3E1B00;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.12rem 0.5rem;
            border-radius: 12px;
        }}

        .bm-drawer-actions {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .btn-clear-all-bm {{
            background: rgba(255,255,255,0.18);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            border-radius: 4px;
            font-size: 0.72rem;
            padding: 0.25rem 0.5rem;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .btn-clear-all-bm:hover {{
            background: rgba(220, 38, 38, 0.85);
            border-color: #EF4444;
        }}

        .bm-drawer-close {{
            background: transparent;
            border: none;
            color: white;
            font-size: 1.2rem;
            cursor: pointer;
            padding: 0.2rem 0.4rem;
            line-height: 1;
            opacity: 0.85;
            transition: opacity 0.2s;
        }}

        .bm-drawer-close:hover {{
            opacity: 1;
        }}

        .bm-drawer-list {{
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }}

        .bm-card {{
            background: #FFFFFF;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            box-shadow: 0 2px 6px rgba(0,0,0,0.06);
            padding: 0.85rem;
            cursor: pointer;
            transition: all 0.2s ease;
            position: relative;
            border-left: 5px solid #FDE047;
        }}

        .bm-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        }}

        .bm-card.card-theme-yellow {{ border-left-color: #FDE047; }}
        .bm-card.card-theme-saffron {{ border-left-color: #FB923C; }}
        .bm-card.card-theme-green {{ border-left-color: #4ADE80; }}
        .bm-card.card-theme-rose {{ border-left-color: #FB7185; }}

        .bm-card-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.5rem;
            margin-bottom: 0.35rem;
        }}

        .bm-card-ch {{
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--saffron);
            text-transform: uppercase;
        }}

        .bm-card-del {{
            background: transparent;
            border: none;
            color: #9E9E9E;
            cursor: pointer;
            font-size: 0.85rem;
            padding: 0 0.25rem;
            line-height: 1;
            transition: color 0.15s;
        }}

        .bm-card-del:hover {{
            color: #DC2626;
        }}

        .bm-card-title {{
            font-size: 0.92rem;
            font-weight: 600;
            color: var(--maroon);
            margin-bottom: 0.35rem;
            font-family: 'Noto Serif Devanagari', serif;
        }}

        .bm-card-snippet {{
            font-size: 0.84rem;
            color: #5D4037;
            line-height: 1.4;
            background: #FAF7F2;
            padding: 0.4rem 0.55rem;
            border-radius: 4px;
            font-style: italic;
            border-left: 2px solid rgba(0,0,0,0.15);
            margin-bottom: 0.35rem;
            word-break: break-word;
        }}

        .bm-card-date {{
            font-size: 0.7rem;
            color: #8D6E63;
        }}

        .bm-empty-state {{
            text-align: center;
            padding: 3rem 1.5rem;
            color: #8D6E63;
        }}

        .bm-empty-icon {{
            font-size: 2.5rem;
            margin-bottom: 0.75rem;
            opacity: 0.7;
        }}

        .bm-empty-title {{
            font-weight: 700;
            font-size: 1rem;
            color: var(--dark-brown);
            margin-bottom: 0.5rem;
        }}

        .bm-empty-desc {{
            font-size: 0.85rem;
            line-height: 1.5;
        }}

        @keyframes anuvakaPulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(216, 67, 21, 0.6); }}
            50% {{ box-shadow: 0 0 0 8px rgba(216, 67, 21, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(216, 67, 21, 0); }}
        }}

        .anuvaka-highlight {{
            animation: anuvakaPulse 1.8s ease-out;
            border-color: var(--saffron) !important;
        }}

        .toc-bm-flag {{
            display: inline-block;
            margin-left: 0.35rem;
            font-size: 0.75rem;
            vertical-align: middle;
        }}

        .vedic-italic, i, em {{
            font-style: italic;
        }}

        .reader-footer {{
            margin-top: 3.5rem;
            padding: 1.5rem 0;
            border-top: 1px dashed #D6C2A8;
            text-align: center;
            font-size: 0.82rem;
            color: #8C7B70;
            font-family: monospace;
        }}

        .verse-text {{
            font-family: var(--verse-font);
            font-weight: var(--verse-weight);
            font-size: var(--mantra-size, calc(var(--font-size) * 1.18));
            line-height: 2.2;
            letter-spacing: 0.012em;
            color: #111111;
            text-align: left;
            overflow-wrap: break-word;
            word-break: normal;
            min-width: 0;
        }}

        .verse-p {{
            margin-bottom: 1.15rem;
            text-indent: 0;
            overflow-wrap: break-word;
            word-break: normal;
        }}

        .verse-p:last-child {{
            margin-bottom: 0;
        }}

        .verse-citation {{
            font-family: monospace, system-ui, -apple-system, sans-serif;
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--text-muted, #777);
            background: rgba(0, 0, 0, 0.04);
            border: 1px solid rgba(0, 0, 0, 0.12);
            padding: 0.14rem 0.52rem;
            border-radius: 4px;
            letter-spacing: 0.03em;
            display: table;
            margin-left: auto;
            margin-right: 0;
            margin-top: 1.25rem;
            margin-bottom: 0.4rem;
            text-align: right;
        }}

        .dark-mode .verse-citation {{
            color: #aaa;
            background: rgba(255, 255, 255, 0.06);
            border-color: rgba(255, 255, 255, 0.12);
        }}

        .verse-note {{
            font-family: system-ui, -apple-system, sans-serif;
            font-size: 0.95rem;
            color: var(--text-muted);
            margin: 0.4rem 0;
            font-style: italic;
        }}

        /* Korvai Box Styles */
        .korvai-box {{
            margin: 1.35rem 0 1.5rem 0;
            padding: 1.1rem 1.35rem;
            background: linear-gradient(135deg, rgba(255, 248, 238, 0.96) 0%, rgba(254, 242, 224, 0.92) 100%);
            border: 1.5px solid #d4a373;
            border-left: 6px solid var(--maroon, #800000);
            border-radius: 8px;
            box-shadow: 0 3px 10px rgba(128, 0, 0, 0.07);
            transition: all 0.2s ease;
        }}

        .dark-mode .korvai-box {{
            background: linear-gradient(135deg, rgba(45, 30, 25, 0.85) 0%, rgba(35, 25, 20, 0.92) 100%);
            border-color: #8c5a3c;
            border-left-color: #e07a5f;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.35);
        }}

        .korvai-box:hover {{
            box-shadow: 0 5px 16px rgba(128, 0, 0, 0.12);
        }}

        .korvai-header {{
            display: flex;
            align-items: center;
            margin-bottom: 0.65rem;
        }}

        .korvai-tag {{
            font-family: system-ui, -apple-system, sans-serif;
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--maroon, #800000);
            background: rgba(128, 0, 0, 0.09);
            padding: 0.22rem 0.65rem;
            border-radius: 4px;
        }}

        .dark-mode .korvai-tag {{
            color: #f4a261;
            background: rgba(244, 162, 97, 0.18);
        }}

        .korvai-body {{
            font-family: var(--verse-font);
            font-size: 0.75em;
            line-height: 1.85;
            color: var(--text-color, #2b2b2b);
            word-break: normal;
            overflow-wrap: break-word;
        }}

        .korvai-note .korvai-tag {{
            background: rgba(100, 100, 100, 0.1);
            color: var(--text-muted);
        }}

        /* Vedic Accent Mark Styles - Zero-width elevated positioning (mimicking Jaimineeya Samavedam) */
        .accent-swarita {{
            display: inline-block;
            width: 0;
            overflow: visible;
            font-family: var(--accent-font);
            color: inherit;
            font-weight: bold;
            font-size: 1.2em;
            position: relative;
            left: var(--accent-offset, -0.20em);
            bottom: var(--swarita-bottom);
            isolation: isolate;
        }}

        .accent-anudatta {{
            display: inline-block;
            width: 0;
            overflow: visible;
            font-family: var(--accent-font);
            color: inherit;
            font-weight: bold;
            font-size: 1.2em;
            position: relative;
            left: var(--accent-offset, -0.20em);
            bottom: var(--anudatta-bottom);
            isolation: isolate;
        }}

        .accent-deergha {{
            display: inline-block;
            width: 0;
            overflow: visible;
            font-family: var(--accent-font);
            color: inherit;
            font-weight: bold;
            font-size: 1.2em;
            position: relative;
            left: var(--accent-offset, -0.20em);
            bottom: var(--swarita-bottom);
            isolation: isolate;
        }}

        /* When accent follows Visarga (ः), shift backwards over the syllable to eliminate dotted circles & prevent drift */
        .accent-visarga {{
            left: var(--visarga-offset, -0.55em) !important;
        }}
        /* Vedic & General Tables */
        .table-responsive {{
            width: 100%;
            overflow-x: auto;
            margin: 1.25rem 0;
            -webkit-overflow-scrolling: touch;
        }}
        .vedic-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95rem;
            background: #FFFDF9;
            border: 1px solid #E0D0C0;
            border-radius: 6px;
            overflow: hidden;
        }}
        .vedic-table th {{
            background: #8B2500;
            color: white;
            padding: 0.65rem 0.85rem;
            font-weight: 600;
            text-align: left;
            border: 1px solid #7B1113;
            font-family: system-ui, -apple-system, sans-serif;
        }}
        .vedic-table td {{
            padding: 0.55rem 0.85rem;
            border: 1px solid #EAE0D5;
            color: #2D2D2D;
            line-height: 1.5;
        }}
        .vedic-table tr:nth-child(even) td {{
            background: #FDF9F3;
        }}
        .vedic-table tr:hover td {{
            background: #FFF2E5;
        }}

        /* Kumbha Stapanam Diagram Styles */
        .kumbha-diagram-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 2rem;
            align-items: center;
            justify-content: center;
            margin: 1.5rem 0;
            padding: 1.2rem;
            background: #FFFDF8;
            border: 1px solid #E8DCC8;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(139, 37, 0, 0.06);
        }}
        .kumbha-image-wrap {{
            flex: 1 1 360px;
            max-width: 480px;
            text-align: center;
        }}
        .kumbha-image {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            border: 1px solid #D6C4B0;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }}
        .kumbha-table-wrap {{
            flex: 1 1 340px;
            max-width: 460px;
            text-align: center;
        }}
        .direction-label {{
            font-weight: 700;
            font-size: 0.95rem;
            color: #8B2500;
            padding: 0.4rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .kumbha-table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 6px;
            margin: 0.5rem 0;
        }}
        .kumbha-cell {{
            background: #FFF5EB;
            border: 1.5px solid #D9A066;
            border-radius: 8px;
            padding: 0.75rem 0.5rem;
            text-align: center;
            font-size: 0.85rem;
            line-height: 1.35;
            color: #333;
            transition: all 0.2s;
            vertical-align: middle;
        }}
        .kumbha-cell strong {{
            color: #8B2500;
            font-size: 1.05rem;
        }}
        .kumbha-cell:hover {{
            background: #FFE8D1;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(216, 67, 21, 0.15);
        }}
        .kumbha-center {{
            background: linear-gradient(135deg, #FFF0E0 0%, #FFE3C2 100%) !important;
            border: 2px solid #C04000 !important;
            font-weight: 600;
            box-shadow: 0 3px 10px rgba(192, 64, 0, 0.18);
        }}
        .kumbha-center strong {{
            font-size: 1.25rem !important;
            color: #A00000 !important;
        }}
        .kumbha-center-badge {{
            font-size: 0.68rem;
            font-weight: 700;
            color: white;
            background: #C04000;
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        /* Krama Patha 2-Column Grid Table (matching canonical printed text) */
        .krama-table-container {{
            width: 100%;
            margin: 1.15rem 0 1.65rem 0;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }}
        .krama-table {{
            width: 100%;
            border-collapse: collapse;
            border: 1px solid #444444;
            background: #FFFFFF;
            table-layout: fixed;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        }}
        .krama-table td {{
            width: 50%;
            border: 1px solid #444444;
            padding: 0.6rem 0.95rem;
            vertical-align: middle;
            font-family: var(--verse-font);
            font-weight: var(--verse-weight);
            font-size: var(--mantra-size, calc(var(--font-size) * 1.15));
            line-height: 2.15;
            color: #111111;
            word-break: normal;
            overflow-wrap: break-word;
        }}
        .krama-table tr:hover td {{
            background: #FFFDF5;
        }}

        @media (max-width: 1100px) {{
            .layout {{
                grid-template-columns: 250px minmax(0, 1fr);
                gap: 1.15rem;
                padding: 0 0.75rem;
            }}
            .main-content {{
                padding: 1.35rem 1.6rem;
            }}
        }}

        @media (max-width: 850px) and (pointer: fine) {{
            .layout {{
                grid-template-columns: 220px minmax(0, 1fr);
                gap: 0.85rem;
                padding: 0 0.5rem;
            }}
            .main-content {{
                padding: 1.15rem 1.35rem;
            }}
        }}

        @media (max-width: 600px), (max-width: 850px) and (pointer: coarse), (max-height: 550px) and (orientation: landscape) and (pointer: coarse) {{
            .header {{
                padding: 0.45rem 0.6rem;
            }}

            .header-content {{
                flex-direction: column;
                align-items: stretch;
                gap: 0.35rem;
            }}

            .header-main-bar {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                width: 100%;
            }}

            .logo {{
                font-size: 1.25rem;
            }}

            .om-symbol {{
                font-size: 1.45rem;
            }}

            .header-quick-actions {{
                display: flex;
                align-items: center;
                gap: 0.35rem;
            }}

            .controls {{
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                align-items: center;
                gap: 0.3rem;
                width: 100%;
            }}

            .zoom-controls {{
                display: inline-flex;
                align-items: center;
                gap: 0.2rem;
            }}

            .btn-ctrl, .toggle-sidebar-btn {{
                padding: 0.3rem 0.52rem;
                font-size: 0.8rem;
                border-radius: 5px;
            }}

            #font-toggle-btn {{
                max-width: 125px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }}

            #font-size-val {{
                min-width: 36px !important;
                font-size: 0.78rem !important;
                padding: 0.1rem 0.25rem !important;
            }}

            .layout {{
                display: block !important;
                grid-template-columns: 1fr !important;
                width: 100% !important;
                max-width: 100% !important;
                margin: 0.75rem auto;
                padding: 0 0.5rem;
                box-sizing: border-box;
            }}

            /* Suchi Drawer for Mobile View */
            .toc-sidebar {{
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                bottom: 0 !important;
                width: min(85vw, 340px) !important;
                height: 100vh !important;
                max-height: 100vh !important;
                background: #FFFDF9 !important;
                border: none !important;
                border-right: 3px solid var(--saffron) !important;
                border-radius: 0 16px 16px 0 !important;
                box-shadow: 10px 0 35px rgba(0, 0, 0, 0.35) !important;
                z-index: 2500 !important;
                padding: 1.25rem 1rem 2.5rem 1.25rem !important;
                overflow-y: auto !important;
                -webkit-overflow-scrolling: touch;
                transform: translateX(-105%);
                transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1) !important;
                display: block !important;
                opacity: 1 !important;
                pointer-events: auto !important;
            }}

            body.mobile-toc-active {{
                overflow: hidden !important;
            }}

            body.mobile-toc-active .toc-backdrop {{
                display: block;
                opacity: 1;
            }}

            body.mobile-toc-active .toc-sidebar {{
                transform: translateX(0) !important;
            }}

            .toc-close-btn {{
                display: inline-flex;
            }}

            .main-content {{
                padding: 1.15rem 0.85rem;
                width: 100%;
                box-sizing: border-box;
                border-radius: 8px;
            }}

            .main-title {{
                margin-bottom: 1.75rem;
                padding-bottom: 0.85rem;
            }}

            .main-title h1 {{
                font-size: 1.65rem;
                line-height: 1.35;
                word-break: break-word;
                overflow-wrap: break-word;
            }}

            .main-title .sub-heading,
            .main-title .subheading {{
                font-size: 1.35rem;
                line-height: 1.4;
                margin-bottom: 0.45rem;
            }}

            .chapter-container {{
                margin-bottom: 2.25rem;
            }}

            .chapter-heading {{
                font-size: calc(var(--font-size) * 1.16);
                padding: 0.75rem 1rem;
                border-radius: 6px;
                margin-bottom: 1.25rem;
                word-break: break-word;
                overflow-wrap: break-word;
            }}

            .anuvaka-block {{
                padding: 0.95rem 0.85rem;
                margin-bottom: 1.25rem;
            }}

            .anuvaka-block.level-3 {{
                margin-left: 0.25rem;
            }}

            .anuvaka-header {{
                margin-bottom: 0.85rem;
                padding-bottom: 0.45rem;
            }}

            .anuvaka-num.level-2 {{
                font-size: calc(var(--font-size) * 0.98);
            }}

            .anuvaka-num.level-3 {{
                font-size: calc(var(--font-size) * 0.86);
            }}

            .verse-text {{
                font-size: calc(var(--font-size) * 0.95);
                line-height: 2.0;
                text-align: left;
            }}
        }}

        @media (max-height: 550px) and (orientation: landscape) {{
            .header {{
                padding: 0.25rem 0.55rem;
            }}
            .header-content {{
                flex-direction: row;
                justify-content: space-between;
                align-items: center;
                gap: 0.3rem;
                flex-wrap: wrap;
            }}
            .header-main-bar {{
                display: flex;
                align-items: center;
                gap: 0.3rem;
                width: auto;
            }}
            .logo {{
                font-size: 1.15rem;
            }}
            .controls {{
                display: flex;
                align-items: center;
                gap: 0.25rem;
                width: auto;
                flex-wrap: wrap;
            }}
            .btn-ctrl, .toggle-sidebar-btn {{
                padding: 0.25rem 0.45rem;
                font-size: 0.78rem;
            }}
            #font-toggle-btn {{
                max-width: 110px;
            }}
        }}

        @media (max-width: 420px) {{
            .header {{
                padding: 0.4rem 0.45rem;
            }}

            .btn-ctrl, .toggle-sidebar-btn {{
                padding: 0.28rem 0.42rem;
                font-size: 0.76rem;
            }}

            #font-toggle-btn {{
                max-width: 100px;
            }}

            .main-content {{
                padding: 0.95rem 0.65rem;
            }}
        }}

        /* Print Modal Styles */
        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.45);
            backdrop-filter: blur(2px);
            z-index: 2000;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .modal-card {{
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            max-width: 520px;
            width: 92%;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
            border: 1px solid var(--border-color);
            box-sizing: border-box;
            overflow: hidden;
        }}
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.75rem;
            margin-bottom: 1rem;
        }}
        .modal-header h3 {{
            color: var(--maroon);
            font-size: 1.25rem;
            font-family: 'Noto Serif Devanagari', serif;
        }}
        .close-modal-btn {{
            background: none;
            border: none;
            font-size: 1.25rem;
            cursor: pointer;
            color: #888;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
        }}
        .close-modal-btn:hover {{
            color: var(--maroon);
            background: #F5F0EB;
        }}
        .print-options {{
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
        }}
        .btn-print-opt {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.9rem 1.1rem;
            border: 1.5px solid var(--border-color);
            border-radius: 8px;
            background: #FFFDF9;
            cursor: pointer;
            text-align: left;
            transition: all 0.2s ease;
            width: 100%;
            box-sizing: border-box;
        }}
        .btn-print-opt:hover {{
            border-color: var(--saffron);
            background: #FFF8F0;
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(216, 67, 21, 0.12);
        }}
        .btn-print-opt.primary {{
            border-color: var(--saffron);
            background: #FFF5EC;
        }}
        .btn-opt-icon {{
            font-size: 1.5rem;
            flex-shrink: 0;
        }}
        .btn-opt-text strong {{
            display: block;
            color: var(--dark-brown);
            font-size: 1rem;
            margin-bottom: 0.2rem;
        }}
        .btn-opt-text span {{
            font-size: 0.82rem;
            color: #666;
        }}

        /* Centered Sacred Deity Portrait */
        .deity-portrait-wrapper {{
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 1.75rem auto 2.5rem;
        }}

        .deity-portrait-img {{
            max-width: 240px;
            width: 100%;
            height: auto;
            aspect-ratio: 1 / 1;
            object-fit: cover;
            border-radius: 12px;
            border: 2px solid var(--gold, #DAA520);
            box-shadow: 0 6px 20px rgba(78, 52, 46, 0.16);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}

        .deity-portrait-img:hover {{
            transform: scale(1.02);
            box-shadow: 0 8px 24px rgba(128, 0, 0, 0.22);
        }}

        @media (max-width: 600px) {{
            .deity-portrait-img {{
                max-width: 190px;
            }}
            .deity-portrait-wrapper {{
                margin: 1.25rem auto 2rem;
            }}
        }}

        @page {{
            size: auto;
            margin: 15mm 18mm 15mm 18mm;
        }}

        @media print {{
            *, *::before, *::after {{
                box-sizing: border-box !important;
            }}
            .chant-pada {{
                display: inline-block !important;
                white-space: nowrap !important;
                margin-right: 0.35em !important;
            }}
            .chant-pada-long {{
                display: inline !important;
                white-space: normal !important;
            }}
            html, body {{
                background: white !important;
                color: #111 !important;
                width: 100% !important;
                max-width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            .header, .toc-sidebar, .back-to-top, .modal-overlay, .deity-portrait-wrapper, .bookmarks-drawer, .bm-drawer-backdrop, .anuvaka-bm-btn, .postit-entity, .postit-inplace-tab, #postit-overlay-layer, .verse-pin-badge, .add-note-inline-btn, .selection-note-btn {{
                display: none !important;
            }}
            .layout {{
                display: block !important;
                width: 100% !important;
                max-width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
            }}
            .main-content {{
                box-shadow: none !important;
                border: none !important;
                padding: 0 !important;
                margin: 0 !important;
                width: 100% !important;
                max-width: 100% !important;
                box-sizing: border-box !important;
            }}
            .main-title {{
                text-align: center !important;
                margin-bottom: 2rem !important;
                padding-bottom: 1rem !important;
                border-bottom: 2px solid var(--maroon) !important;
            }}
            .chapter-container {{
                width: 100% !important;
                max-width: 100% !important;
                margin: 0 0 2.5rem 0 !important;
                padding: 0 !important;
                box-sizing: border-box !important;
            }}
            .chapter-heading {{
                break-after: avoid;
                page-break-after: avoid;
                margin: 1.5rem 0 1.2rem 0 !important;
                padding: 0.6rem 1rem !important;
                background: #7B1113 !important;
                color: white !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            .anuvaka-block {{
                box-sizing: border-box !important;
                width: calc(100% - 6px) !important;
                max-width: calc(100% - 6px) !important;
                margin: 0 3px 1.5rem 3px !important;
                padding: 1.1rem 1.3rem !important;
                background: #FFFAF5 !important;
                border: 1px solid #D0C0B0 !important;
                border-left: 5px solid var(--saffron) !important;
                border-radius: 6px !important;
                box-shadow: none !important;
                content-visibility: visible !important;
                contain-intrinsic-size: none !important;
                contain: none !important;
                break-inside: avoid;
                page-break-inside: avoid;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            .verse-text, .verse-p {{
                word-break: break-word !important;
                overflow-wrap: break-word !important;
            }}
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="header-main-bar">
                <a href="#" class="logo" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}}); return false;" title="Go to top of page">
                    <span class="om-symbol">ॐ</span>
                    <span>VedaVMS</span>
                </a>
                <div class="header-quick-actions">
                    <button class="toggle-sidebar-btn" onclick="toggleSidebar()" title="Toggle Contents Panel" id="sidebar-toggle-btn">{sidebar_btn_text}</button>
                    <a href="{back_link}" class="btn-ctrl">{back_label}</a>
                </div>
            </div>
            <div class="controls">
                <button class="btn-ctrl" id="btn-add-quick-note" onclick="createFloatingNote()" title="Create a new Post-It Note (or double-click anywhere in text)">➕ Note</button>
                <button class="btn-ctrl" id="bookmarks-toggle-btn" onclick="toggleBookmarksDrawer()" title="View Bookmarks & Post-It Notes">🔖 Notes <span id="bm-badge-count" class="bm-badge" style="display:none;">0</span></button>
                <button class="btn-ctrl" id="font-toggle-btn" onclick="toggleFont()" title="Toggle Font">Font: {default_font_name}</button>
                <div class="zoom-controls">
                    <button class="btn-ctrl" onclick="adjustFont(-1)" title="Decrease Font Size (A-)">A-</button>
                    <span id="font-size-val" onclick="resetFontSize()" style="font-size: 0.85rem; padding: 0.15rem 0.45rem; color: #FFF; font-family: monospace; font-weight: 600; min-width: 44px; text-align: center; display: inline-block; cursor: pointer; border-radius: 4px; background: rgba(255,255,255,0.14); transition: transform 0.15s ease;" title="Click to reset font size to 100%">100%</span>
                    <button class="btn-ctrl" onclick="adjustFont(1)" title="Increase Font Size (A+)">A+</button>
                </div>
                <button class="btn-ctrl" onclick="openPrintModal()" title="Print / Save PDF (Ctrl+P)">🖨️ Print</button>
                <button class="btn-ctrl" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}})" title="Go to top of page">▲ Top</button>
            </div>
        </div>
    </header>

    <div class="toc-backdrop" id="toc-backdrop" onclick="closeMobileToc()"></div>

    <div class="layout">
        <!-- Sidebar Navigation -->
        <aside class="toc-sidebar" id="toc-sidebar">
            <div class="toc-header-bar">
                <div class="toc-title">{sidebar_title_text}</div>
                <button class="toc-close-btn" onclick="closeMobileToc()" title="Close Contents" aria-label="Close">✕</button>
            </div>
            <ul class="toc-list">
''')

    # Filter out Chapter 0 (TOC) if present; TOC is handled solely by sidebar navigation pane
    chapters = [ch for ch in chapters if str(ch.get('num')) not in ('0', '0.0')]

    for ch in chapters:
        ch_id = f"chapter-{ch['num']}"
        sub_sections = [
            s for s in ch["sections"]
            if not (s.get('is_intro') or s['num'] == str(ch['num']) or '.' not in s['num'])
        ]
        has_subsections = len(sub_sections) > 0
        if has_subsections:
            html_parts.append(f'''                <li class="toc-chapter" id="toc-{ch_id}">
                    <div class="toc-ch-header" onclick="toggleTocChapter('toc-{ch_id}')">
                        <div class="toc-ch-title"><a href="#{ch_id}">{re.sub(r"[\t\s]+\d+$", "", ch["title_deva"]).strip()}</a></div>
                        <span class="toc-ch-toggle">▼</span>
                    </div>
                    <ul class="toc-sub-list">
''')
            for sec in sub_sections:
                sec_id = f"sec-{sec['num'].replace('.', '-')}"
                t_deva = sec['title_deva'].strip() if sec.get('title_deva') else ''
                # Remove any trailing tabs or page numbers
                t_deva = re.sub(r'[\t\s]+\d+$', '', t_deva).strip()
                if t_deva.startswith(f"{sec['num']}.") or t_deva.startswith(f"{sec['num']} ") or t_deva == sec['num']:
                    title_disp = t_deva
                else:
                    title_disp = f"{sec['num']} {t_deva}".strip()
                title_disp = re.sub(r'[\t\s]+\d+$', '', title_disp).strip()
                sec_parts = [p for p in sec['num'].split('.') if p.strip().isdigit()]
                lvl_class = "toc-level-3" if len(sec_parts) >= 3 else "toc-level-2"
                html_parts.append(f'                        <li class="{lvl_class}"><a href="#{sec_id}">{title_disp}</a></li>\n')
            html_parts.append('''                    </ul>
                </li>
''')
        else:
            html_parts.append(f'''                <li class="toc-chapter toc-single" id="toc-{ch_id}">
                    <div class="toc-ch-header">
                        <div class="toc-ch-title"><a href="#{ch_id}">{ch['title_deva']}</a></div>
                    </div>
                </li>
''')

    html_parts.append(f'''            </ul>
        </aside>

        <!-- Main Content -->
        <main class="main-content">
            <div class="main-title">
                <h1>{title}</h1>
                <div class="sub-heading subheading">{subtitle}</div>
                <div class="generation-timestamp">Generated: {generated_at}</div>
            </div>
{deity_portrait_html}''')

    for ch in chapters:
        ch_id = f"chapter-{ch['num']}"
        ch_code_span = f'<span class="anuvaka-code chapter-code">{esc(ch["ta_code"])}</span>' if ch.get("ta_code") else ''
        html_parts.append(f'''            <section class="chapter-container" id="{ch_id}">
                <h2 class="chapter-heading">{ch['title_deva']}{(" " + ch_code_span) if ch_code_span else ""}</h2>
''')
        for sec in ch["sections"]:
            sec_id = f"sec-{sec['num'].replace('.', '-')}"
            code_span = f'<span class="anuvaka-code">{esc(sec["ta_code"])}</span>' if sec.get("ta_code") else ''
            is_intro = sec.get('is_intro', False) or sec['num'] == str(ch['num']) or '.' not in sec['num'] or (not sec.get('title_raw') or sec.get('title_raw') == ch.get('title_raw'))
            sec_parts = [p for p in sec['num'].split('.') if p.strip().isdigit()]
            lvl_class = "level-3" if len(sec_parts) >= 3 else "level-2"

            if is_intro:
                header_html = f'''                    <div class="anuvaka-header anuvaka-header-intro">
                        <div class="anuvaka-header-left"></div>
                        <div class="anuvaka-header-right">
                            {code_span}
                            <button type="button" class="anuvaka-bm-btn" onclick="toggleAnuvakaBookmark('{sec_id}', event)" title="Bookmark / Add Post-It Note" aria-label="Bookmark this section">🔖 <span class="bm-btn-label">Note</span></button>
                        </div>
                    </div>'''
            else:
                t_deva = sec['title_deva'].strip() if sec.get('title_deva') else ''
                if t_deva.startswith(f"{sec['num']}.") or t_deva.startswith(f"{sec['num']} ") or t_deva == sec['num']:
                    title_disp_deva = format_vedic_html(t_deva)
                else:
                    title_disp_deva = f"{sec['num']} {format_vedic_html(t_deva)}".strip()
                header_html = f'''                    <div class="anuvaka-header">
                        <div class="anuvaka-header-left">
                            <span class="anuvaka-num {lvl_class}">{title_disp_deva}</span>
                        </div>
                        <div class="anuvaka-header-right">
                            {code_span}
                            <button type="button" class="anuvaka-bm-btn" onclick="toggleAnuvakaBookmark('{sec_id}', event)" title="Bookmark / Add Post-It Note" aria-label="Bookmark this section">🔖 <span class="bm-btn-label">Note</span></button>
                        </div>
                    </div>'''

            html_parts.append(f'''                <div class="anuvaka-block {lvl_class}" id="{sec_id}">
{header_html}
                    <div class="verse-text">
''')
            for p_idx, deva_line in enumerate(sec["content_deva"]):
                p_id = f"{sec_id}-p{p_idx}"
                if deva_line.startswith('<div class="korvai-box"'):
                    m = re.match(r'(<div class="korvai-box.*?>\s*<div class="korvai-header">.*?</div>\s*<div class="korvai-body">)(.*?)(</div>\s*</div>)', deva_line, re.DOTALL)
                    if m:
                        formatted_body = wrap_chant_padas(format_vedic_html(m.group(2).strip()))
                        html_parts.append(f'                        {m.group(1)}{formatted_body}{m.group(3)}\n')
                    else:
                        html_parts.append(f'                        {deva_line}\n')
                elif deva_line.startswith('<div') or deva_line.startswith('<table') or deva_line.startswith('<p'):
                    html_parts.append(f'                        {deva_line}\n')
                else:
                    html_parts.append(f'                        <p class="verse-p" id="{p_id}">{wrap_chant_padas(format_vedic_html(deva_line))}<button type="button" class="add-note-inline-btn" onclick="createNoteAtTarget(\x27{p_id}\x27, \x27\x27, event)" title="Attach Post-It Note here">📌+</button></p>\n')
            html_parts.append('''                    </div>
                </div>
''')
        html_parts.append('''            </section>
''')

    html_parts.append(f'''            <footer class="reader-footer">
                <div class="footer-meta">Generated: {generated_at} • VedaVMS Vedic Reader</div>
            </footer>
        </main>
    </div>

    <script>
        const defaultSize = {default_font_size};
        let currentSize = defaultSize;

        function updateFontSizeDisplay() {{
            const pct = Math.round((currentSize / defaultSize) * 100);
            const valEl = document.getElementById('font-size-val');
            if (valEl) {{
                valEl.textContent = pct + '%';
                valEl.style.transform = 'scale(1.18)';
                setTimeout(() => {{ valEl.style.transform = 'scale(1)'; }}, 150);
            }}
        }}

        function applyFontSize() {{
            const mainEl = document.querySelector('.main-content');
            if (mainEl) mainEl.style.setProperty('--font-size', currentSize + 'rem');
            document.documentElement.style.setProperty('--font-size', currentSize + 'rem');
            updateFontSizeDisplay();
            localStorage.setItem('reader-font-size', currentSize);
        }}

        function adjustFont(delta) {{
            currentSize = Math.max(0.9, Math.min(2.4, +(currentSize + (delta * 0.15)).toFixed(2)));
            applyFontSize();
        }}

        function resetFontSize() {{
            currentSize = defaultSize;
            applyFontSize();
        }}

        const fontList = {fonts_js};
        let currentFontIndex = 0;
        function setFont(idx) {{
            currentFontIndex = ((idx % fontList.length) + fontList.length) % fontList.length;
            const chosen = fontList[currentFontIndex];
            document.documentElement.style.setProperty('--verse-font', chosen.font);
            document.documentElement.style.setProperty('--verse-weight', chosen.weight);
            const btn = document.getElementById('font-toggle-btn');
            if (btn) btn.innerText = 'Font: ' + chosen.label;
            localStorage.setItem('reader-font-idx', currentFontIndex);
        }}
        function toggleFont() {{
            setFont(currentFontIndex + 1);
        }}

        function toggleTocChapter(id) {{
            const el = document.getElementById(id);
            if (!el) return;
            el.classList.toggle('collapsed');
            const collapsed = el.classList.contains('collapsed');
            const state = JSON.parse(localStorage.getItem('toc-chapters') || '{{}}');
            state[id] = collapsed;
            localStorage.setItem('toc-chapters', JSON.stringify(state));
        }}

        function isMobileView() {{
            const isTouch = window.matchMedia('(pointer: coarse)').matches;
            const isNarrow = window.innerWidth <= 600;
            const isTouchTablet = isTouch && window.innerWidth <= 850;
            const isTouchLandscape = isTouch && window.innerHeight <= 550 && window.matchMedia('(orientation: landscape)').matches;
            return isNarrow || isTouchTablet || isTouchLandscape;
        }}

        function closeMobileToc() {{
            document.body.classList.remove('mobile-toc-active');
            const btn = document.getElementById('sidebar-toggle-btn');
            if (btn) {{
                if (isMobileView()) {{
                    btn.textContent = '☰ सूची';
                }} else {{
                    const collapsed = document.querySelector('.layout')?.classList.contains('sidebar-collapsed');
                    btn.textContent = collapsed ? '☰' : '☰ सूची';
                }}
            }}
        }}

        function toggleSidebar() {{
            const btn = document.getElementById('sidebar-toggle-btn');
            if (isMobileView()) {{
                document.body.classList.toggle('mobile-toc-active');
                const isOpen = document.body.classList.contains('mobile-toc-active');
                if (btn) btn.textContent = isOpen ? '✕ सूची' : '☰ सूची';
            }} else {{
                const layout = document.querySelector('.layout');
                if (!layout) return;
                layout.classList.toggle('sidebar-collapsed');
                const collapsed = layout.classList.contains('sidebar-collapsed');
                sessionStorage.setItem('sidebar-collapsed', collapsed);
                if (btn) btn.textContent = collapsed ? '☰' : '☰ सूची';
            }}
        }}

        function handleLayoutChange() {{
            const isMobile = isMobileView();
            const btn = document.getElementById('sidebar-toggle-btn');
            const layout = document.querySelector('.layout');

            if (isMobile) {{
                if (layout) {{
                    layout.classList.remove('sidebar-collapsed');
                }}
                const isOpen = document.body.classList.contains('mobile-toc-active');
                if (btn) {{
                    btn.textContent = isOpen ? '✕ सूची' : '☰ सूची';
                }}
            }} else {{
                document.body.classList.remove('mobile-toc-active');
                const collapsed = sessionStorage.getItem('sidebar-collapsed') === 'true';
                if (layout) {{
                    if (collapsed) layout.classList.add('sidebar-collapsed');
                    else layout.classList.remove('sidebar-collapsed');
                }}
                if (btn) {{
                    btn.textContent = collapsed ? '☰' : '☰ सूची';
                }}
            }}
        }}

        /* Context-aware Suchi / Index Scroll Synchronization */
        let activeAnuvakaId = null;
        let isUserInteractingWithToc = false;

        /* Print Modal & High Performance Cached Printing */
        let currentActiveSectionId = null;
        let currentActiveSectionTitle = "";
        let currentActiveChapterId = null;
        let currentActiveChapterTitle = "";
        let currentActiveChapterCount = 0;
        const printSectionCache = new Map();

        function scrollSidebarToTarget(targetLink) {{
            const sidebar = document.querySelector('.toc-sidebar');
            if (!sidebar || isUserInteractingWithToc || !targetLink) return;
            if (isMobileView() && !document.body.classList.contains('mobile-toc-active')) return;
            const linkRect = targetLink.getBoundingClientRect();
            const sideRect = sidebar.getBoundingClientRect();
            const margin = Math.min(60, sideRect.height * 0.15);
            if (linkRect.top < sideRect.top + margin || linkRect.bottom > sideRect.bottom - margin) {{
                const currentScroll = sidebar.scrollTop;
                const offset = (linkRect.top - sideRect.top) - (sideRect.height / 2) + (linkRect.height / 2);
                sidebar.scrollTo({{
                    top: Math.max(0, currentScroll + offset),
                    behavior: 'smooth'
                }});
            }}
        }}

        let activeContextId = null;

        function updateActiveContext(activeEl) {{
            if (!activeEl) return;

            let chapterEl = activeEl.classList.contains('chapter-container') 
                ? activeEl 
                : activeEl.closest('.chapter-container');
            let sectionEl = activeEl.classList.contains('anuvaka-block') 
                ? activeEl 
                : activeEl.querySelector('.anuvaka-block');

            if (!chapterEl && sectionEl) {{
                chapterEl = sectionEl.closest('.chapter-container');
            }}
            if (!chapterEl) return;

            const chId = chapterEl.id;
            const contextKey = activeEl.id;
            if (contextKey === activeContextId) return;
            activeContextId = contextKey;

            const tocChItem = document.getElementById('toc-' + chId);

            // 1. Update Chapter Active State in TOC
            document.querySelectorAll('.toc-chapter.active-chapter').forEach(el => {{
                if (el !== tocChItem) el.classList.remove('active-chapter');
            }});
            document.querySelectorAll('.toc-ch-title a.active').forEach(el => el.classList.remove('active'));

            if (tocChItem) {{
                tocChItem.classList.add('active-chapter');

                // If standalone chapter (toc-single), highlight its link directly
                if (tocChItem.classList.contains('toc-single')) {{
                    const singleLink = tocChItem.querySelector('.toc-ch-title a');
                    if (singleLink) singleLink.classList.add('active');
                    document.querySelectorAll('.toc-sub-list a.active').forEach(el => el.classList.remove('active'));
                    scrollSidebarToTarget(singleLink || tocChItem);
                }} else {{
                    // Multi-section chapter: expand if collapsed
                    if (tocChItem.classList.contains('collapsed')) {{
                        tocChItem.classList.remove('collapsed');
                    }}
                }}
            }}

            // 2. Update Section / Subchapter Active State in TOC
            if (sectionEl) {{
                const secId = sectionEl.id;
                const targetSubLink = document.querySelector(`.toc-sub-list a[href="#${{secId}}"]`);

                document.querySelectorAll('.toc-sub-list a.active').forEach(el => {{
                    if (el !== targetSubLink) el.classList.remove('active');
                }});

                if (targetSubLink) {{
                    targetSubLink.classList.add('active');
                    scrollSidebarToTarget(targetSubLink);
                }} else if (tocChItem && !tocChItem.classList.contains('toc-single')) {{
                    const chLink = tocChItem.querySelector('.toc-ch-title a');
                    scrollSidebarToTarget(chLink || tocChItem);
                }}
            }} else if (tocChItem) {{
                const chLink = tocChItem.querySelector('.toc-ch-title a');
                scrollSidebarToTarget(chLink || tocChItem);
            }}
        }}

        function highlightAnuvakaInToc(targetId) {{
            const el = document.getElementById(targetId);
            if (el) updateActiveContext(el);
        }}

        function openPrintModal() {{
            const modal = document.getElementById('print-modal');
            const label = document.getElementById('current-section-print-name');
            if (currentActiveChapterTitle && label) {{
                label.innerText = currentActiveChapterTitle + (currentActiveChapterCount ? ` (${{currentActiveChapterCount}} anuvakas)` : '');
            }} else if (label) {{
                label.innerText = 'Print active Section/Chapter';
            }}
            if (modal) modal.style.display = 'flex';
        }}

        function closePrintModal() {{
            const modal = document.getElementById('print-modal');
            if (modal) modal.style.display = 'none';
        }}

        // Intercept Ctrl+P / Cmd+P to open fast print modal instead of freezing
        window.addEventListener('keydown', function(e) {{
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'p') {{
                e.preventDefault();
                openPrintModal();
            }}
            if (e.key === 'Escape') {{
                closePrintModal();
            }}
        }});

        function printHtmlContent(title, contentHtml) {{
            let iframe = document.getElementById('vms-print-frame');
            if (!iframe) {{
                iframe = document.createElement('iframe');
                iframe.id = 'vms-print-frame';
                iframe.style.position = 'fixed';
                iframe.style.left = '-9999px';
                iframe.style.top = '0';
                iframe.style.width = '800px';
                iframe.style.height = '1000px';
                iframe.style.border = 'none';
                document.body.appendChild(iframe);
            }}
            const doc = iframe.contentWindow.document;
            const mainStyle = document.querySelector('style') ? document.querySelector('style').innerHTML : '';
            doc.open();
            doc.write(`<!DOCTYPE html>
            <html lang="sa">
            <head>
                <meta charset="UTF-8">
                <title>${{title || document.title}}</title>
                <style>
                    ${{mainStyle}}
                    @page {{
                        size: auto;
                        margin: 15mm 18mm 15mm 18mm;
                    }}
                    *, *::before, *::after {{
                        box-sizing: border-box !important;
                    }}
                    html, body {{
                        background: white !important;
                        color: #111 !important;
                        padding: 0 !important;
                        margin: 0 !important;
                        width: 100% !important;
                        max-width: 100% !important;
                        font-size: 1.15rem;
                        -webkit-print-color-adjust: exact !important;
                        print-color-adjust: exact !important;
                    }}
                    .header, .toc-sidebar, .back-to-top, .modal-overlay, .bookmarks-drawer, .bm-drawer-backdrop, .anuvaka-bm-btn, .postit-entity, .postit-inplace-tab, #postit-overlay-layer, .verse-pin-badge, .add-note-inline-btn, .selection-note-btn {{
                        display: none !important;
                    }}
                    .layout {{
                        display: block !important;
                        width: 100% !important;
                        max-width: 100% !important;
                        margin: 0 !important;
                        padding: 0 !important;
                    }}
                    .print-container {{
                        width: 100% !important;
                        max-width: 100% !important;
                        margin: 0 auto !important;
                        padding: 0 3px !important;
                        box-sizing: border-box !important;
                    }}
                    .main-content {{
                        border: none !important;
                        box-shadow: none !important;
                        padding: 0 !important;
                        margin: 0 !important;
                        width: 100% !important;
                        max-width: 100% !important;
                    }}
                    .chapter-container {{
                        width: 100% !important;
                        max-width: 100% !important;
                        margin: 0 0 2.5rem 0 !important;
                        padding: 0 !important;
                        box-sizing: border-box !important;
                    }}
                    .chapter-heading {{
                        break-after: avoid;
                        page-break-after: avoid;
                        margin: 1.5rem 0 1.2rem 0 !important;
                        padding: 0.6rem 1rem !important;
                        background: #7B1113 !important;
                        color: white !important;
                        -webkit-print-color-adjust: exact !important;
                        print-color-adjust: exact !important;
                    }}
                    .anuvaka-block {{
                        box-sizing: border-box !important;
                        width: calc(100% - 6px) !important;
                        max-width: calc(100% - 6px) !important;
                        margin: 0 3px 1.5rem 3px !important;
                        padding: 1.1rem 1.3rem !important;
                        background: #FFFAF5 !important;
                        border: 1px solid #D0C0B0 !important;
                        border-left: 5px solid var(--saffron) !important;
                        border-radius: 6px !important;
                        box-shadow: none !important;
                        content-visibility: visible !important;
                        contain-intrinsic-size: none !important;
                        contain: none !important;
                        break-inside: avoid;
                        page-break-inside: avoid;
                        -webkit-print-color-adjust: exact !important;
                        print-color-adjust: exact !important;
                    }}
                    .verse-text, .verse-p {{
                        font-size: 1.35rem !important;
                        line-height: 2.1 !important;
                        word-break: break-word !important;
                        overflow-wrap: break-word !important;
                    }}
                    .accent-swarita, .accent-anudatta, .accent-deergha {{
                        display: inline-block !important;
                        width: 0 !important;
                        overflow: visible !important;
                        font-family: var(--accent-font) !important;
                        color: inherit !important;
                        font-weight: bold !important;
                        font-size: 1.2em !important;
                        position: relative !important;
                        left: var(--accent-offset, -0.20em) !important;
                        isolation: isolate !important;
                    }}
                    .accent-swarita {{ bottom: var(--swarita-bottom, 0.2em) !important; }}
                    .accent-anudatta {{ bottom: var(--anudatta-bottom, -0.25em) !important; }}
                    .accent-deergha {{ bottom: var(--swarita-bottom, 0.2em) !important; }}
                    .accent-visarga {{ left: var(--visarga-offset, -0.55em) !important; }}
                    @media print {{
                        body {{ margin: 0 !important; padding: 0 !important; }}
                    }}
                </style>
            </head>
            <body>
                <div class="print-container">
                    ${{contentHtml}}
                </div>
            </body>
            </html>`);
            doc.close();

            setTimeout(() => {{
                iframe.contentWindow.focus();
                iframe.contentWindow.print();
            }}, 120);
        }}

        function getSectionPrintableHtml(target) {{
            if (!target) return "";
            const targetId = target.id;
            if (printSectionCache.has(targetId)) {{
                return printSectionCache.get(targetId);
            }}
            const docTitleHtml = `<div style="text-align:center;margin-bottom:1.5rem;"><h1 style="font-size:1.55rem;color:#7B1113;margin-bottom:0.3rem;">॥ ${{document.title}} ॥</h1></div>`;
            let contentHtml = "";
            if (target.classList.contains('chapter-container')) {{
                contentHtml = docTitleHtml + target.outerHTML;
            }} else {{
                const parentChapter = target.closest('.chapter-container');
                const chTitleNode = parentChapter ? parentChapter.querySelector('.chapter-heading') : null;
                const chapterHeaderHtml = chTitleNode ? `<h2 class="chapter-heading" style="text-align:center;font-size:1.35rem;margin-bottom:1.2rem;color:#7B1113;border-bottom:2px solid #7B1113;padding-bottom:0.4rem;">${{chTitleNode.textContent.trim()}}</h2>` : '';
                contentHtml = docTitleHtml + chapterHeaderHtml + target.outerHTML;
            }}
            printSectionCache.set(targetId, contentHtml);
            return contentHtml;
        }}

        function printActiveChapter() {{
            closePrintModal();
            let target = null;
            if (currentActiveChapterId) {{
                target = document.getElementById(currentActiveChapterId);
            }}
            if (!target && currentActiveSectionId) {{
                const sec = document.getElementById(currentActiveSectionId);
                target = sec ? sec.closest('.chapter-container') : null;
            }}
            if (!target) {{
                target = document.querySelector('.chapter-container');
            }}
            if (!target) return;
            const printableHtml = getSectionPrintableHtml(target);
            const title = currentActiveChapterTitle || document.title;
            printHtmlContent(title, printableHtml);
        }}

        function printSelectedTarget() {{
            const select = document.getElementById('section-select-dropdown');
            if (!select || !select.value) return;
            const target = document.getElementById(select.value);
            if (!target) return;
            closePrintModal();
            const printableHtml = getSectionPrintableHtml(target);
            const title = (select.options[select.selectedIndex]?.text) || document.title;
            printHtmlContent(title, printableHtml);
        }}

        function printEntireDocument() {{
            closePrintModal();
            setTimeout(function() {{
                window.print();
            }}, 50);
        }}

        // --- Autonomous Post-It & Bookmarks Entity System ---
        const BM_STORAGE_KEY = 'vedavms_bm_' + (location.pathname.split('/').pop().replace('.html', '') || 'reader');

        function loadNotes() {{
            try {{
                const raw = localStorage.getItem(BM_STORAGE_KEY);
                return raw ? JSON.parse(raw) : {{}};
            }} catch (e) {{
                return {{}};
            }}
        }}

        function saveNotes(data) {{
            try {{
                localStorage.setItem(BM_STORAGE_KEY, JSON.stringify(data));
                updateBookmarksUI();
            }} catch (e) {{
                console.error('Failed to save notes', e);
            }}
        }}

        function findNearestTextTarget(docX, docY) {{
            const vpX = docX - window.scrollX;
            const vpY = docY - window.scrollY;
            if (vpX >= 0 && vpX <= window.innerWidth && vpY >= 0 && vpY <= window.innerHeight) {{
                const elAtPoint = document.elementFromPoint(vpX, vpY);
                if (elAtPoint) {{
                    const vp = elAtPoint.closest('.verse-p, .anuvaka-block');
                    if (vp && vp.id) return vp;
                }}
            }}
            const targets = document.querySelectorAll('.verse-p, .anuvaka-block');
            let bestEl = null;
            let minDist = Infinity;
            targets.forEach(el => {{
                const rect = el.getBoundingClientRect();
                const midY = window.scrollY + rect.top + (rect.height / 2);
                const dist = Math.abs(midY - docY);
                if (dist < minDist) {{
                    minDist = dist;
                    bestEl = el;
                }}
            }});
            return bestEl;
        }}

        function createFloatingNote() {{
            const scrollY = window.scrollY;
            const targetY = scrollY + Math.max(100, Math.round(window.innerHeight * 0.28));
            const contentEl = document.querySelector('.main-content');
            const contentRect = contentEl ? contentEl.getBoundingClientRect() : null;

            let targetX = 30;
            if (contentRect) {{
                targetX = Math.round(window.scrollX + contentRect.left + Math.min(220, contentRect.width * 0.35));
                if (targetX + 245 > window.innerWidth - 20) {{
                    targetX = Math.max(15, window.innerWidth - 260);
                }}
            }} else {{
                targetX = Math.max(15, Math.round(window.innerWidth / 2 - 120));
            }}

            const nearest = findNearestTextTarget(targetX + 40, targetY + 20);
            const targetId = nearest ? nearest.id : null;
            createNoteAtCoords(targetId, targetX, targetY, nearest ? '' : 'General Note');
        }}

        function createNoteAtCoords(targetId, posX, posY, titleOverride, initialSnippet) {{
            const data = loadNotes();
            const noteId = 'note_' + Date.now();

            let targetTitle = titleOverride || '';
            let targetSnippet = initialSnippet || '';

            const targetEl = targetId ? document.getElementById(targetId) : null;
            if (targetEl && !targetTitle) {{
                const chEl = targetEl.closest('.chapter-container');
                const chHeading = chEl ? chEl.querySelector('.chapter-heading') : null;
                const secEl = targetEl.closest('.anuvaka-block');
                const numNode = secEl ? secEl.querySelector('.anuvaka-num') : null;

                const chTitle = chHeading ? chHeading.textContent.trim() : '';
                const secTitle = numNode ? numNode.textContent.trim() : '';
                targetTitle = secTitle ? (chTitle ? chTitle + ' • ' + secTitle : secTitle) : (chTitle || targetId);

                if (!targetSnippet) {{
                    const text = targetEl.textContent.replace('📌+', '').trim();
                    targetSnippet = text.substring(0, 50) + (text.length > 50 ? '...' : '');
                }}
            }} else if (!targetTitle) {{
                targetTitle = 'Post-It Note';
            }}

            data[noteId] = {{
                id: noteId,
                targetId: targetId || '',
                targetTitle: targetTitle,
                targetSnippet: targetSnippet,
                color: 'yellow',
                text: '',
                posX: Math.round(posX),
                posY: Math.round(posY),
                isOpen: true,
                updatedAt: Date.now()
            }};

            saveNotes(data);

            setTimeout(() => {{
                const noteEl = document.getElementById('postit-entity-' + noteId);
                if (noteEl) {{
                    const ta = noteEl.querySelector('.postit-textarea');
                    if (ta) ta.focus();
                }}
            }}, 100);
        }}

        function createNoteAtTarget(targetId, initialSnippet, event) {{
            if (event) {{
                event.stopPropagation();
                event.preventDefault();
            }}

            let defaultTop = window.scrollY + 150;
            let defaultLeft = 20;

            const targetEl = targetId ? document.getElementById(targetId) : null;
            if (targetEl) {{
                const targetRect = targetEl.getBoundingClientRect();
                const contentEl = document.querySelector('.main-content');
                const contentRect = contentEl ? contentEl.getBoundingClientRect() : targetRect;

                defaultTop = Math.round(window.scrollY + targetRect.top);
                defaultLeft = Math.round(window.scrollX + contentRect.left + Math.min(220, contentRect.width * 0.35));
                if (defaultLeft + 245 > window.innerWidth - 20) {{
                    defaultLeft = Math.max(15, window.innerWidth - 260);
                }}
            }}

            createNoteAtCoords(targetId, defaultLeft, defaultTop, '', initialSnippet);
        }}

        function toggleAnuvakaBookmark(secId, event) {{
            if (event) {{
                event.stopPropagation();
                event.preventDefault();
            }}
            const data = loadNotes();
            const existingNote = Object.values(data).find(n => n.targetId === secId);
            if (existingNote) {{
                existingNote.isOpen = !existingNote.isOpen;
                saveNotes(data);
                if (existingNote.isOpen) {{
                    setTimeout(() => {{
                        const noteEl = document.getElementById('postit-entity-' + existingNote.id);
                        if (noteEl) {{
                            const ta = noteEl.querySelector('.postit-textarea');
                            if (ta) ta.focus();
                        }}
                    }}, 80);
                }}
            }} else {{
                createNoteAtTarget(secId, '', event);
            }}
        }}

        let wasDragMoved = false;

        function openNote(noteId, event) {{
            if (wasDragMoved) {{
                wasDragMoved = false;
                return;
            }}
            if (event) {{
                event.stopPropagation();
                event.preventDefault();
            }}
            const data = loadNotes();
            if (data[noteId]) {{
                data[noteId].isOpen = true;
                saveNotes(data);
                setTimeout(() => {{
                    const noteEl = document.getElementById('postit-entity-' + noteId);
                    if (noteEl) {{
                        const ta = noteEl.querySelector('.postit-textarea');
                        if (ta) ta.focus();
                    }}
                }}, 80);
            }}
        }}

        function closeNote(noteId) {{
            const data = loadNotes();
            if (data[noteId]) {{
                data[noteId].isOpen = false;
                saveNotes(data);
            }}
        }}

        function deleteNote(noteId) {{
            const data = loadNotes();
            if (data[noteId]) {{
                const hasText = data[noteId].text && data[noteId].text.trim().length > 0;
                if (!hasText || confirm('Delete this Post-It note?')) {{
                    delete data[noteId];
                    saveNotes(data);
                }}
            }}
        }}

        function setNoteColor(noteId, color) {{
            const data = loadNotes();
            if (data[noteId]) {{
                data[noteId].color = color;
                saveNotes(data);
            }}
        }}

        let noteDebounce = {{}};
        function updateNoteText(noteId, text) {{
            clearTimeout(noteDebounce[noteId]);
            const statusEl = document.getElementById('postit-status-' + noteId);
            if (statusEl) {{
                statusEl.textContent = 'Saving...';
                statusEl.style.opacity = '0.6';
            }}
            noteDebounce[noteId] = setTimeout(() => {{
                const data = loadNotes();
                if (data[noteId]) {{
                    data[noteId].text = text;
                    data[noteId].updatedAt = Date.now();
                    try {{
                        localStorage.setItem(BM_STORAGE_KEY, JSON.stringify(data));
                        const statusDone = document.getElementById('postit-status-' + noteId);
                        if (statusDone) {{
                            statusDone.textContent = 'Saved';
                            statusDone.style.opacity = '1';
                        }}
                        renderBookmarksDrawer();
                    }} catch (e) {{}}
                }}
            }}, 350);
        }}

        function clearAllBookmarks() {{
            if (confirm('Are you sure you want to remove all bookmarks and notes for this text?')) {{
                localStorage.removeItem(BM_STORAGE_KEY);
                updateBookmarksUI();
            }}
        }}

        function toggleBookmarksDrawer(force) {{
            const drawer = document.getElementById('bookmarks-drawer');
            const backdrop = document.getElementById('bm-drawer-backdrop');
            if (!drawer || !backdrop) return;
            const shouldOpen = force !== undefined ? force : !drawer.classList.contains('active');
            if (shouldOpen) {{
                closeMobileToc();
                closePrintModal();
                drawer.classList.add('active');
                backdrop.classList.add('active');
                renderBookmarksDrawer();
            }} else {{
                drawer.classList.remove('active');
                backdrop.classList.remove('active');
            }}
        }}

        function jumpToBookmark(noteId) {{
            toggleBookmarksDrawer(false);
            const data = loadNotes();
            const note = data[noteId];
            if (!note) return;

            note.isOpen = true;
            saveNotes(data);

            const target = note.targetId ? document.getElementById(note.targetId) : null;
            if (target) {{
                target.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                target.classList.add('anuvaka-highlight');
                setTimeout(() => {{ target.classList.remove('anuvaka-highlight'); }}, 2000);
            }} else if (note.posY) {{
                window.scrollTo({{ top: Math.max(0, note.posY - 100), behavior: 'smooth' }});
            }}

            setTimeout(() => {{
                const noteEl = document.getElementById('postit-entity-' + noteId);
                if (noteEl) {{
                    const ta = noteEl.querySelector('.postit-textarea');
                    if (ta) ta.focus();
                }}
            }}, 450);
        }}

        // --- Dragging Logic with Exact Page Coordinates ---
        let activeDragNote = null;
        let dragOffsetX = 0;
        let dragOffsetY = 0;

        function startDragNote(noteId, e) {{
            if (e.target.closest('.postit-entity-tools') || e.target.closest('button') || e.target.closest('textarea')) return;
            const noteEl = document.getElementById('postit-entity-' + noteId) || document.getElementById('postit-tab-' + noteId);
            if (!noteEl) return;
            activeDragNote = noteId;
            wasDragMoved = false;
            noteEl.classList.add('dragging');

            document.querySelectorAll('.postit-entity, .postit-inplace-tab').forEach(el => el.style.zIndex = '1200');
            noteEl.style.zIndex = '2100';

            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            const clientY = e.touches ? e.touches[0].clientY : e.clientY;

            const rect = noteEl.getBoundingClientRect();
            dragOffsetX = clientX - rect.left;
            dragOffsetY = clientY - rect.top;

            if (e.type !== 'touchstart') {{
                e.preventDefault();
            }}
        }}

        function onDragMove(e) {{
            if (!activeDragNote) return;
            const noteEl = document.getElementById('postit-entity-' + activeDragNote) || document.getElementById('postit-tab-' + activeDragNote);
            if (!noteEl) return;

            wasDragMoved = true;
            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            const clientY = e.touches ? e.touches[0].clientY : e.clientY;

            const docX = clientX + window.scrollX - dragOffsetX;
            const docY = clientY + window.scrollY - dragOffsetY;

            const maxLeft = Math.max(10, document.documentElement.scrollWidth - 120);
            const clampLeft = Math.max(10, Math.min(maxLeft, docX));
            const clampTop = Math.max(50, docY);

            noteEl.style.left = clampLeft + 'px';
            noteEl.style.top = clampTop + 'px';
            noteEl.style.right = 'auto';
        }}

        document.addEventListener('mousemove', onDragMove);
        document.addEventListener('touchmove', onDragMove, {{ passive: false }});

        function endDragNote() {{
            if (!activeDragNote) return;
            const noteEl = document.getElementById('postit-entity-' + activeDragNote) || document.getElementById('postit-tab-' + activeDragNote);
            if (noteEl) {{
                noteEl.classList.remove('dragging');
                if (wasDragMoved) {{
                    const data = loadNotes();
                    if (data[activeDragNote]) {{
                        const newX = parseInt(noteEl.style.left, 10);
                        const newY = parseInt(noteEl.style.top, 10);
                        data[activeDragNote].posX = newX;
                        data[activeDragNote].posY = newY;

                        // Auto-detect nearest verse or section under drop location
                        const nearest = findNearestTextTarget(newX + 40, newY + 20);
                        if (nearest && nearest.id) {{
                            data[activeDragNote].targetId = nearest.id;
                            const chEl = nearest.closest('.chapter-container');
                            const chHeading = chEl ? chEl.querySelector('.chapter-heading') : null;
                            const secEl = nearest.closest('.anuvaka-block');
                            const numNode = secEl ? secEl.querySelector('.anuvaka-num') : null;
                            const chTitle = chHeading ? chHeading.textContent.trim() : '';
                            const secTitle = numNode ? numNode.textContent.trim() : '';
                            data[activeDragNote].targetTitle = secTitle ? (chTitle ? chTitle + ' • ' + secTitle : secTitle) : (chTitle || nearest.id);
                            if (!data[activeDragNote].text) {{
                                const tText = nearest.textContent.replace('📌+', '').trim();
                                data[activeDragNote].targetSnippet = tText.substring(0, 50) + (tText.length > 50 ? '...' : '');
                            }}
                        }}
                        saveNotes(data);
                    }}
                }}
            }}
            activeDragNote = null;
        }}

        document.addEventListener('mouseup', endDragNote);
        document.addEventListener('touchend', endDragNote);

        // --- Double-Click Anywhere in Body Text to Drop Note ---
        document.addEventListener('dblclick', function(e) {{
            if (e.target.closest('.postit-entity') || e.target.closest('button') || e.target.closest('a') || e.target.closest('.bookmarks-drawer') || e.target.closest('.toc-sidebar') || e.target.closest('.header') || e.target.closest('.modal-overlay')) return;
            const targetP = e.target.closest('.verse-p, .anuvaka-block');
            const targetId = targetP ? targetP.id : null;
            const posX = Math.max(15, e.pageX - 30);
            const posY = Math.max(60, e.pageY - 20);
            createNoteAtCoords(targetId, posX, posY);
        }});

        // --- Hover Card Preview for Notes ---
        let hoverCardEl = null;

        function showHoverPreview(targetEl, title, text, color) {{
            if (!text && !title) return;
            if (!hoverCardEl) {{
                hoverCardEl = document.createElement('div');
                hoverCardEl.id = 'postit-hover-card';
                hoverCardEl.className = 'postit-hover-card';
                document.body.appendChild(hoverCardEl);
            }}

            hoverCardEl.className = 'postit-hover-card postit-theme-' + (color || 'yellow') + ' visible';
            hoverCardEl.innerHTML = `
                <div class="hover-card-header">
                    <span class="hover-card-pin">📌</span>
                    <span class="hover-card-title">${{escapeHtmlText(title || 'Note Preview')}}</span>
                </div>
                <div class="hover-card-content">${{escapeHtmlText(text || '(Empty note)')}}</div>
            `;

            const rect = targetEl.getBoundingClientRect();
            const cardWidth = 220;
            let left = window.scrollX + rect.left;
            if (left + cardWidth > window.innerWidth - 10) {{
                left = window.scrollX + rect.right - cardWidth;
            }}
            const top = window.scrollY + rect.bottom + 8;

            hoverCardEl.style.left = Math.max(10, left) + 'px';
            hoverCardEl.style.top = top + 'px';
        }}

        function hideHoverPreview() {{
            if (hoverCardEl) {{
                hoverCardEl.classList.remove('visible');
            }}
        }}

        document.addEventListener('mouseover', function(e) {{
            const btn = e.target.closest('[data-note-preview]');
            if (btn) {{
                const text = btn.getAttribute('data-note-preview');
                const color = btn.getAttribute('data-note-color') || 'yellow';
                const title = btn.getAttribute('data-note-title') || 'Note';
                showHoverPreview(btn, title, text, color);
            }}
        }});

        document.addEventListener('mouseout', function(e) {{
            const btn = e.target.closest('[data-note-preview]');
            if (btn) {{
                hideHoverPreview();
            }}
        }});

        // --- Selection Tooltip ---
        let selectionNoteBtn = null;
        document.addEventListener('mouseup', function(e) {{
            if (e.target.closest('.postit-entity') || e.target.closest('.bookmarks-drawer') || e.target.closest('.modal-overlay')) return;
            const sel = window.getSelection();
            const text = sel ? sel.toString().trim() : '';

            if (text.length >= 3) {{
                const range = sel.getRangeAt(0);
                const rect = range.getBoundingClientRect();
                if (!selectionNoteBtn) {{
                    selectionNoteBtn = document.createElement('button');
                    selectionNoteBtn.className = 'selection-note-btn';
                    selectionNoteBtn.innerHTML = '📌 Add Post-It';
                    document.body.appendChild(selectionNoteBtn);
                }}
                selectionNoteBtn.style.top = Math.round(window.scrollY + rect.bottom + 8) + 'px';
                selectionNoteBtn.style.left = Math.round(window.scrollX + rect.left) + 'px';
                selectionNoteBtn.style.display = 'inline-flex';

                selectionNoteBtn.onmousedown = function(ev) {{
                    ev.preventDefault();
                    ev.stopPropagation();
                    const node = range.commonAncestorContainer;
                    const parentP = node.nodeType === 1 ? node.closest('.verse-p, .anuvaka-block') : (node.parentElement ? node.parentElement.closest('.verse-p, .anuvaka-block') : null);
                    const targetId = parentP ? parentP.id : null;
                    selectionNoteBtn.style.display = 'none';
                    createNoteAtTarget(targetId, text);
                    sel.removeAllRanges();
                }};
            }} else {{
                if (selectionNoteBtn) selectionNoteBtn.style.display = 'none';
            }}
        }});

        function escapeHtmlText(str) {{
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');
        }}

        function updateBookmarksUI() {{
            const data = loadNotes();
            const notesList = Object.values(data);
            const count = notesList.length;

            const badge = document.getElementById('bm-badge-count');
            const bmBtn = document.getElementById('bookmarks-toggle-btn');
            if (badge) {{
                badge.textContent = count;
                badge.style.display = count > 0 ? 'inline-block' : 'none';
            }}
            if (bmBtn) {{
                if (count > 0) bmBtn.classList.add('active');
                else bmBtn.classList.remove('active');
            }}

            let overlay = document.getElementById('postit-overlay-layer');
            if (!overlay) {{
                overlay = document.createElement('div');
                overlay.id = 'postit-overlay-layer';
                document.body.appendChild(overlay);
            }}

            let overlayHtml = '';
            notesList.forEach(note => {{
                const color = note.color || 'yellow';
                const previewText = note.text ? note.text : '(Empty note)';
                const leftStyle = note.posX ? `left: ${{note.posX}}px;` : 'right: 25px;';
                const topStyle = note.posY ? `top: ${{note.posY}}px;` : 'top: 150px;';

                if (note.isOpen) {{
                    overlayHtml += `
                        <div class="postit-entity postit-theme-${{color}}" id="postit-entity-${{note.id}}" style="${{leftStyle}} ${{topStyle}}">
                            <div class="postit-entity-header" onmousedown="startDragNote('${{note.id}}', event)" ontouchstart="startDragNote('${{note.id}}', event)">
                                <div class="postit-drag-handle" title="Drag anywhere in text">
                                    <span class="postit-pin">📌</span>
                                    <span class="postit-entity-title" title="${{escapeHtmlText(note.targetTitle)}}">${{escapeHtmlText(note.targetTitle)}}</span>
                                </div>
                                <div class="postit-entity-tools">
                                    <div class="postit-color-picker" title="Change color">
                                        <button type="button" class="color-btn color-yellow ${{color === 'yellow' ? 'active' : ''}}" onclick="setNoteColor('${{note.id}}', 'yellow')" title="Yellow"></button>
                                        <button type="button" class="color-btn color-saffron ${{color === 'saffron' ? 'active' : ''}}" onclick="setNoteColor('${{note.id}}', 'saffron')" title="Saffron"></button>
                                        <button type="button" class="color-btn color-green ${{color === 'green' ? 'active' : ''}}" onclick="setNoteColor('${{note.id}}', 'green')" title="Green"></button>
                                        <button type="button" class="color-btn color-rose ${{color === 'rose' ? 'active' : ''}}" onclick="setNoteColor('${{note.id}}', 'rose')" title="Rose"></button>
                                    </div>
                                    <button type="button" class="postit-tool-btn postit-tool-del" onclick="deleteNote('${{note.id}}')" title="Delete note">🗑️</button>
                                    <button type="button" class="postit-tool-btn postit-tool-close" onclick="closeNote('${{note.id}}')" title="Close / Fold note in-place">✕</button>
                                </div>
                            </div>
                            <div class="postit-entity-body">
                                <textarea class="postit-textarea" placeholder="Add study note, chant count, commentary..." oninput="updateNoteText('${{note.id}}', this.value)">${{escapeHtmlText(note.text || '')}}</textarea>
                                <div class="postit-footer-bar">
                                    <span class="postit-status" id="postit-status-${{note.id}}">Saved</span>
                                    <button type="button" class="postit-done-btn" onclick="closeNote('${{note.id}}')" title="Fold to in-place tab">✔ Done</button>
                                </div>
                            </div>
                        </div>
                    `;
                }} else {{
                    overlayHtml += `
                        <div class="postit-inplace-tab postit-theme-${{color}}" id="postit-tab-${{note.id}}" style="${{leftStyle}} ${{topStyle}}" onclick="openNote('${{note.id}}', event)" onmousedown="startDragNote('${{note.id}}', event)" ontouchstart="startDragNote('${{note.id}}', event)" data-note-preview="${{escapeHtmlText(previewText)}}" data-note-title="${{escapeHtmlText(note.targetTitle)}}" data-note-color="${{color}}" title="Click to open Post-It note • Drag to move">
                            <span class="inplace-tab-pin">📌</span>
                            <span class="inplace-tab-title">${{escapeHtmlText(previewText.substring(0, 16))}}</span>
                        </div>
                    `;
                }}
            }});
            overlay.innerHTML = overlayHtml;

            document.querySelectorAll('.verse-pin-badge').forEach(el => el.remove());

            const targetsMap = {{}};
            notesList.forEach(note => {{
                if (note.targetId) {{
                    if (!targetsMap[note.targetId]) targetsMap[note.targetId] = [];
                    targetsMap[note.targetId].push(note);
                }}
            }});

            document.querySelectorAll('.anuvaka-block').forEach(sec => {{
                const secId = sec.id;
                const btn = sec.querySelector('.anuvaka-bm-btn');
                const secNotes = targetsMap[secId] || [];
                if (btn) {{
                    if (secNotes.length > 0) {{
                        btn.classList.add('active');
                        const anyOpen = secNotes.some(n => n.isOpen);
                        const noteWithText = secNotes.find(n => n.text && n.text.trim()) || secNotes[0];
                        const previewText = noteWithText && noteWithText.text ? noteWithText.text : '(Empty note)';

                        btn.title = '📌 ' + previewText;
                        btn.setAttribute('data-note-preview', previewText);
                        btn.setAttribute('data-note-color', noteWithText.color || 'yellow');
                        btn.setAttribute('data-note-title', noteWithText.targetTitle || 'Anuvaka Note');

                        if (anyOpen) {{
                            btn.innerHTML = '✕ <span class="bm-btn-label">Close Note</span>';
                        }} else {{
                            btn.innerHTML = '📌 <span class="bm-btn-label">View Note</span>';
                        }}
                    }} else {{
                        btn.classList.remove('active');
                        btn.removeAttribute('data-note-preview');
                        btn.title = 'Attach Post-It Note to this section (or double-click text)';
                        btn.innerHTML = '🔖 <span class="bm-btn-label">Note</span>';
                    }}
                }}
            }});

            Object.entries(targetsMap).forEach(([targetId, notes]) => {{
                const el = document.getElementById(targetId);
                if (el && el.classList.contains('verse-p')) {{
                    notes.forEach(note => {{
                        const badge = document.createElement('span');
                        const color = note.color || 'yellow';
                        const previewText = note.text ? note.text : '(Empty note)';
                        badge.className = `verse-pin-badge postit-theme-${{color}}`;
                        badge.title = '📌 ' + previewText;
                        badge.setAttribute('data-note-preview', previewText);
                        badge.setAttribute('data-note-color', color);
                        badge.setAttribute('data-note-title', note.targetTitle || 'Verse Note');
                        badge.innerHTML = `📌 <span class="badge-snip">${{escapeHtmlText(previewText.substring(0, 15))}}</span>`;
                        badge.onclick = (ev) => {{
                            ev.stopPropagation();
                            note.isOpen = !note.isOpen;
                            saveNotes(data);
                        }};
                        el.appendChild(badge);
                    }});
                }}
            }});

            renderBookmarksDrawer();
        }}

        function renderBookmarksDrawer() {{
            const listEl = document.getElementById('bm-drawer-list');
            const countEl = document.getElementById('bm-drawer-count');
            if (!listEl) return;

            const data = loadNotes();
            const entries = Object.values(data);
            if (countEl) countEl.textContent = entries.length;

            if (entries.length === 0) {{
                listEl.innerHTML = `
                    <div class="bm-empty-state">
                        <div class="bm-empty-icon">📌</div>
                        <div class="bm-empty-title">No Post-It Notes Yet</div>
                        <div class="bm-empty-desc">Attach a sticky note anywhere: click <strong>➕ Note</strong> in the top bar, double-click anywhere in the text, or click <strong>📌+</strong> beside any verse line.</div>
                    </div>
                `;
                return;
            }}

            entries.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));

            let html = '';
            entries.forEach(item => {{
                const color = item.color || 'yellow';
                const dateStr = item.updatedAt ? new Date(item.updatedAt).toLocaleDateString(undefined, {{ month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }}) : '';
                const snippet = item.text ? escapeHtmlText(item.text) : (item.targetSnippet ? '<span style="opacity:0.7;">Attached to: "' + escapeHtmlText(item.targetSnippet) + '"</span>' : '<span style="opacity: 0.6; font-style: italic;">(Empty note)</span>');

                html += `
                    <div class="bm-card card-theme-${{color}}" onclick="jumpToBookmark('${{item.id}}')">
                        <div class="bm-card-top">
                            <div class="bm-card-ch">${{escapeHtmlText(item.targetTitle || 'Note')}}</div>
                            <button type="button" class="bm-card-del" onclick="event.stopPropagation(); deleteNote('${{item.id}}')" title="Delete note">✕</button>
                        </div>
                        <div class="bm-card-snippet">${{snippet}}</div>
                        <div class="bm-card-date">${{dateStr}}</div>
                    </div>
                `;
            }});
            listEl.innerHTML = html;
        }}

        function populateSectionDropdown() {{
            const select = document.getElementById('section-select-dropdown');
            if (!select) return;
            select.innerHTML = '';

            const chGroup = document.createElement('optgroup');
            chGroup.label = "Chapters / Sections (Complete)";

            const anuvakaGroup = document.createElement('optgroup');
            anuvakaGroup.label = "Individual Anuvakas";

            document.querySelectorAll('.chapter-container').forEach(ch => {{
                const chHeading = ch.querySelector('.chapter-heading');
                const chTitle = chHeading ? chHeading.textContent.trim() : ch.id;
                const count = ch.querySelectorAll('.anuvaka-block').length;

                const chOpt = document.createElement('option');
                chOpt.value = ch.id;
                chOpt.textContent = `${{chTitle}} (${{count}} anuvakas)`;
                chGroup.appendChild(chOpt);

                ch.querySelectorAll('.anuvaka-block').forEach(sec => {{
                    const numEl = sec.querySelector('.anuvaka-num');
                    const codeEl = sec.querySelector('.anuvaka-code');
                    const secTitle = numEl ? numEl.textContent.trim() : (codeEl ? codeEl.textContent.trim() : 'प्रारम्भः (Intro)');
                    const secOpt = document.createElement('option');
                    secOpt.value = sec.id;
                    secOpt.textContent = `${{chTitle}} - ${{secTitle}}`;
                    anuvakaGroup.appendChild(secOpt);
                }});
            }});

            select.appendChild(chGroup);
            select.appendChild(anuvakaGroup);
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            populateSectionDropdown();

            const firstCh = document.querySelector('.chapter-container');
            if (firstCh) {{
                currentActiveChapterId = firstCh.id;
                const chHeading = firstCh.querySelector('.chapter-heading');
                currentActiveChapterTitle = chHeading ? chHeading.textContent.trim() : firstCh.id;
                currentActiveChapterCount = firstCh.querySelectorAll('.anuvaka-block').length;
            }}

            // IntersectionObserver for tracking active Chapter and Anuvaka during scroll
            const navObserver = new IntersectionObserver((entries) => {{
                let bestEntry = null;
                let minDistance = Infinity;

                entries.forEach(entry => {{
                    if (entry.isIntersecting) {{
                        const dist = Math.abs(entry.boundingClientRect.top - 85);
                        if (dist < minDistance) {{
                            minDistance = dist;
                            bestEntry = entry;
                        }}
                    }}
                }});

                if (bestEntry) {{
                    updateActiveContext(bestEntry.target);
                    const secNode = bestEntry.target.classList.contains('anuvaka-block') 
                        ? bestEntry.target 
                        : bestEntry.target.querySelector('.anuvaka-block');
                    if (secNode) {{
                        currentActiveSectionId = secNode.id;
                        const numNode = secNode.querySelector('.anuvaka-num');
                        const codeNode = secNode.querySelector('.anuvaka-code');
                        if (numNode) {{
                            currentActiveSectionTitle = numNode.textContent.trim();
                        }} else if (codeNode) {{
                            currentActiveSectionTitle = codeNode.textContent.trim();
                        }} else {{
                            currentActiveSectionTitle = currentActiveChapterTitle || "";
                        }}
                    }}
                    const parentCh = bestEntry.target.closest('.chapter-container') || (bestEntry.target.classList.contains('chapter-container') ? bestEntry.target : null);
                    if (parentCh) {{
                        currentActiveChapterId = parentCh.id;
                        const chHeading = parentCh.querySelector('.chapter-heading');
                        currentActiveChapterTitle = chHeading ? chHeading.textContent.trim() : parentCh.id;
                        currentActiveChapterCount = parentCh.querySelectorAll('.anuvaka-block').length;
                    }}
                }}
            }}, {{ rootMargin: '-75px 0px -70% 0px', threshold: 0 }});

            document.querySelectorAll('.chapter-container, .anuvaka-block').forEach(el => navObserver.observe(el));

            // Direct click on Suchi item immediately highlights and smoothly scrolls to target
            document.querySelectorAll('.toc-sub-list a, .toc-ch-title a').forEach(link => {{
                link.addEventListener('click', function(e) {{
                    if (isMobileView()) {{
                        closeMobileToc();
                    }}
                    const href = this.getAttribute('href');
                    if (href && href.startsWith('#')) {{
                        const targetId = href.slice(1);
                        const target = document.getElementById(targetId);
                        if (target) {{
                            e.preventDefault();
                            target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                            if (history.pushState) {{
                                history.pushState(null, '', href);
                            }}
                            updateActiveContext(target);
                            const secNode = target.classList.contains('anuvaka-block') 
                                ? target 
                                : target.querySelector('.anuvaka-block');
                            if (secNode) {{
                                currentActiveSectionId = secNode.id;
                                const numNode = secNode.querySelector('.anuvaka-num');
                                const codeNode = secNode.querySelector('.anuvaka-code');
                                if (numNode) {{
                                    currentActiveSectionTitle = numNode.textContent.trim();
                                }} else if (codeNode) {{
                                    currentActiveSectionTitle = codeNode.textContent.trim();
                                }} else {{
                                    currentActiveSectionTitle = currentActiveChapterTitle || "";
                                }}
                            }}
                            const parentCh = target.closest('.chapter-container') || (target.classList.contains('chapter-container') ? target : null);
                            if (parentCh) {{
                                currentActiveChapterId = parentCh.id;
                                const chHeading = parentCh.querySelector('.chapter-heading');
                                currentActiveChapterTitle = chHeading ? chHeading.textContent.trim() : parentCh.id;
                                currentActiveChapterCount = parentCh.querySelectorAll('.anuvaka-block').length;
                            }}
                        }}
                    }}
                }});
            }});

            // Close mobile Suchi on Escape key
            document.addEventListener('keydown', function(e) {{
                if (e.key === 'Escape') {{
                    closeMobileToc();
                    closePrintModal();
                    toggleBookmarksDrawer(false);
                }}
            }});

            function onOrientationOrResize() {{
                handleLayoutChange();
                // Ensure viewport zoom and scaling reset cleanly on mobile orientation switch
                const viewportMeta = document.querySelector('meta[name="viewport"]');
                if (viewportMeta) {{
                    viewportMeta.setAttribute('content', 'width=device-width, initial-scale=1.0, viewport-fit=cover');
                }}
            }}

            // Trap window resize
            window.addEventListener('resize', onOrientationOrResize);

            // Trap mobile device orientation change (both legacy and modern APIs)
            window.addEventListener('orientationchange', function() {{
                setTimeout(onOrientationOrResize, 50);
                setTimeout(onOrientationOrResize, 150);
                setTimeout(onOrientationOrResize, 350);
            }});

            if (window.screen && window.screen.orientation) {{
                window.screen.orientation.addEventListener('change', function() {{
                    setTimeout(onOrientationOrResize, 50);
                    setTimeout(onOrientationOrResize, 150);
                    setTimeout(onOrientationOrResize, 350);
                }});
            }}

            const mqlPortrait = window.matchMedia('(orientation: portrait)');
            if (mqlPortrait.addEventListener) {{
                mqlPortrait.addEventListener('change', onOrientationOrResize);
            }} else if (mqlPortrait.addListener) {{
                mqlPortrait.addListener(onOrientationOrResize);
            }}

            const sidebar = document.querySelector('.toc-sidebar');
            if (sidebar) {{
                let tocTimeout;
                sidebar.addEventListener('wheel', () => {{
                    isUserInteractingWithToc = true;
                    clearTimeout(tocTimeout);
                    tocTimeout = setTimeout(() => {{ isUserInteractingWithToc = false; }}, 1500);
                }}, {{ passive: true }});
            }}

            // Synchronize initial layout state based on screen orientation and width
            handleLayoutChange();
            const tocState = JSON.parse(localStorage.getItem('toc-chapters') || '{{}}');
            for (const [id, isCollapsed] of Object.entries(tocState)) {{
                if (isCollapsed) {{
                    const el = document.getElementById(id);
                    if (el) el.classList.add('collapsed');
                }}
            }}
            const savedFont = localStorage.getItem('reader-font-idx');
            if (savedFont !== null) {{
                setFont(parseInt(savedFont, 10) || 0);
            }}
            const savedSize = localStorage.getItem('reader-font-size');
            if (savedSize !== null) {{
                currentSize = parseFloat(savedSize) || defaultSize;
                applyFontSize();
            }} else {{
                updateFontSizeDisplay();
            }}
            updateBookmarksUI();
        }});

        window.addEventListener('scroll', function() {{
            const btn = document.getElementById('back-to-top');
            if (btn) {{
                if (window.scrollY > 350) btn.classList.add('visible');
                else btn.classList.remove('visible');
            }}
        }});
    </script>
    <button id="back-to-top" class="back-to-top" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}})" title="Go to top of page">▲</button>

    <!-- Autonomous Post-It Notes Layer -->
    <div id="postit-overlay-layer"></div>

    <!-- Bookmarks & Post-It Notes Drawer -->
    <div class="bm-drawer-backdrop" id="bm-drawer-backdrop" onclick="toggleBookmarksDrawer(false)"></div>
    <aside class="bookmarks-drawer" id="bookmarks-drawer" aria-label="Bookmarks and Study Notes">
        <div class="bm-drawer-header">
            <div class="bm-drawer-title">
                <span>🔖 Bookmarks &amp; Notes</span>
                <span class="bm-drawer-count" id="bm-drawer-count">0</span>
            </div>
            <div class="bm-drawer-actions">
                <button type="button" class="btn-clear-all-bm" onclick="clearAllBookmarks()" title="Clear all bookmarks in this text">Clear All</button>
                <button type="button" class="bm-drawer-close" onclick="toggleBookmarksDrawer(false)" title="Close" aria-label="Close">✕</button>
            </div>
        </div>
        <div class="bm-drawer-list" id="bm-drawer-list"></div>
    </aside>

    <!-- Print Options Modal -->
    <div id="print-modal" class="modal-overlay" style="display: none;" onclick="if(event.target === this) closePrintModal();">
        <div class="modal-card">
            <div class="modal-header">
                <h3>🖨️ Print / Save PDF</h3>
                <button class="close-modal-btn" onclick="closePrintModal()" title="Close">✕</button>
            </div>
            <div class="modal-body">
                <p style="margin-bottom: 1rem; color: #555; font-size: 0.92rem; line-height: 1.5;">
                    Large documents take time to paginate. Choose your print scope below:
                </p>
                <div class="print-options">
                    <button class="btn-print-opt primary" onclick="printActiveChapter()">
                        <span class="btn-opt-icon">⚡</span>
                        <div class="btn-opt-text">
                            <strong>Print Current Section/Chapter</strong>
                            <span id="current-section-print-name">Print active Section/Chapter</span>
                        </div>
                    </button>

                    <div style="background: #FFFDF9; border: 1.5px solid var(--border-color); border-radius: 8px; padding: 0.75rem 1rem; box-sizing: border-box; width: 100%;">
                        <label style="font-weight: 600; font-size: 0.92rem; color: var(--dark-brown); display: block; margin-bottom: 0.35rem;">
                            Select Specific Section / Chapter:
                        </label>
                        <div style="display: flex; gap: 0.5rem; align-items: center; width: 100%; box-sizing: border-box;">
                            <select id="section-select-dropdown" style="flex: 1; min-width: 0; padding: 0.45rem; border: 1px solid #CCC; border-radius: 6px; font-family: inherit; font-size: 0.9rem; box-sizing: border-box;">
                            </select>
                            <button type="button" class="btn-ctrl" style="background: var(--saffron); color: white; border: none; padding: 0.45rem 0.85rem; cursor: pointer; white-space: nowrap; flex-shrink: 0;" onclick="printSelectedTarget()">Print</button>
                        </div>
                    </div>

                    <button class="btn-print-opt" onclick="printEntireDocument()">
                        <span class="btn-opt-icon">📖</span>
                        <div class="btn-opt-text">
                            <strong>Print Entire Document</strong>
                            <span>All chapters and sections (full text)</span>
                        </div>
                    </button>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
''')

    return "".join(html_parts)


def ast_to_chapters(ast_data: dict) -> list[dict]:
    """Convert AST structure into chapters format for generate_reader_html."""
    supersections = ast_data.get('supersections', ast_data.get('supersection', {}))
    chapters = []
    for ss_key, ss_data in supersections.items():
        if ss_key == 'count':
            continue
        for sec_key, sec_data in ss_data.get('sections', {}).items():
            if sec_key == 'count':
                continue
            sec_title = sec_data.get('title') or sec_data.get('section_title', '')
            num_m = re.match(r'^(\d+)\.\s*(.*)', sec_title)
            ch_num = int(num_m.group(1)) if num_m else (len(chapters) + 1)
            raw_title = sec_data.get('raw_title', '')
            is_eng = sec_data.get('is_english', False)

            sections = []
            for sub_key, sub_data in sec_data.get('subsections', {}).items():
                if sub_key == 'count':
                    continue
                header = sub_data.get('header', {}).get('header', '')
                h_m = re.match(r'^(\d+\.\d+(?:\.\d+)?)\s*(.*)', header)
                if h_m:
                    sub_num = h_m.group(1)
                    sub_title = h_m.group(2).strip()
                else:
                    sub_num = sub_data.get('sub_section_id', f"{ch_num}.{len(sections)+1}")
                    sub_title = sub_data.get('title', header)
                ta_code = sub_data.get('ta_code', '')
                content = sub_data.get('content_lines', [])
                sections.append({
                    'num': sub_num,
                    'title_deva': sub_title,
                    'title_raw': sub_title,
                    'ta_code': ta_code,
                    'content_deva': content,
                    'content_raw': content
                })
            chapters.append({
                'num': ch_num,
                'title_deva': sec_title,
                'title_raw': raw_title,
                'is_english': is_eng,
                'sections': sections
            })
    return chapters


def convert_docx_direct(
    input_file: str | Path,
    output_file: str | Path = None,
    book_meta: dict = None,
    config: dict = None,
    title: str = None,
    subtitle: str = None,
    chapter_regex: str = None
) -> Path:
    """Directly convert any Baraha or Vedic Word (.docx) document into a standalone interactive Vedic HTML Reader."""
    input_path = Path(input_file)
    if not input_path.exists():
        for cand in [
            Path("data/baraha") / input_path,
            Path("data/docx") / input_path,
            Path(__file__).parent.parent / "data/baraha" / input_path,
            Path(__file__).parent.parent / "data/docx" / input_path,
            Path(__file__).parent.parent / input_path,
            Path(__file__).parent / input_path,
        ]:
            if cand.exists():
                input_path = cand
                break
        else:
            raise FileNotFoundError(f"Input document not found: {input_path}")

    if config is None:
        cfg_candidates = [
            Path(__file__).parent / "config.json",
            Path("src/config.json"),
            Path("vedavms_html/config.json"),
            Path(__file__).parent.parent / "src" / "config.json",
        ]
        cfg_p = next((p for p in cfg_candidates if p.exists()), None)
        if cfg_p:
            with open(cfg_p, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {}

    book_meta = dict(book_meta or {})
    fonts = config.get("fonts", [])
    default_size = config.get("default_font_size_rem", 1.35)

    doc_title = title or book_meta.get("title_sanskrit") or book_meta.get("title")
    doc_subtitle = subtitle or book_meta.get("subtitle") or "कृष्ण यजुर्वेदीय आरण्यकम् (वेदमन्त्राः सस्वराः)"
    ch_reg = chapter_regex or book_meta.get("chapter_regex")

    if not output_file:
        slug = input_path.stem.lower().replace(" ", "_").replace("-", "_")
        if not slug.endswith("_sanskrit"):
            slug += "_sanskrit"
        output_file = Path("build/viewer") / f"{slug}.html"
    out_path = Path(output_file)

    print(f"\n--- Direct Document Conversion ---")
    print(f"Loading Document: {input_path}")
    print(f"Target HTML:  {out_path}")

    try:
        from .baraha_reader import parse_baraha_docx_to_ast, ast_to_reader_chapters
    except ImportError:
        from baraha_reader import parse_baraha_docx_to_ast, ast_to_reader_chapters

    ast_data, extracted_title = parse_baraha_docx_to_ast(input_path, title=doc_title, chapter_regex=ch_reg)
    final_title = doc_title or extracted_title or input_path.stem

    book_meta.setdefault("title", final_title)
    book_meta.setdefault("title_sanskrit", final_title)
    book_meta.setdefault("subtitle", doc_subtitle)
    book_meta.setdefault("back_link", "../index.html")
    book_meta.setdefault("back_label", "← Home")
    book_meta["input_docx"] = str(input_path)
    book_meta["output_html"] = str(out_path)

    chapters = ast_to_reader_chapters(ast_data)

    ch_filter = book_meta.get("chapter_filter")
    if ch_filter:
        filtered = [ch for ch in chapters if str(ch.get('num')) == str(ch_filter)]
        if filtered:
            chapters = filtered
            # Clean up English summary/intro notes for dedicated book readers
            chapters[0]['sections'] = [s for s in chapters[0]['sections'] if not str(s.get('num', '')).endswith('.D')]
            sec_filter = book_meta.get("section_filter")
            if sec_filter:
                chapters[0]['sections'] = [s for s in chapters[0]['sections'] if s.get('num') in sec_filter]

    target_lang = book_meta.get("lang") or ("malayalam" if "malayalam" in str(out_path).lower() else "sanskrit")
    if target_lang == "malayalam":
        try:
            from .transliterate import deva_to_malayalam
        except ImportError:
            from transliterate import deva_to_malayalam
        for k in ['title', 'title_sanskrit', 'subtitle']:
            if k in book_meta and book_meta[k]:
                book_meta[k] = deva_to_malayalam(book_meta[k])
        mal_chapters = []
        for ch in chapters:
            mal_ch = dict(ch)
            mal_ch['title_deva'] = deva_to_malayalam(ch['title_deva'])
            mal_ch['sections'] = []
            for sec in ch['sections']:
                mal_sec = dict(sec)
                mal_sec['title_deva'] = deva_to_malayalam(sec['title_deva'])
                mal_sec['content_deva'] = [deva_to_malayalam(line) for line in sec.get('content_deva', [])]
                mal_ch['sections'].append(mal_sec)
            mal_chapters.append(mal_ch)
        chapters = mal_chapters
        fonts = [
            {
                "label": "Noto Serif Malayalam",
                "font": "'Noto Serif Malayalam', 'Kartika', 'Gayathri', 'Noto Serif Devanagari', 'Siddhanta', serif",
                "weight": "500"
            },
            {
                "label": "Gayathri",
                "font": "'Gayathri', 'Noto Serif Malayalam', 'Noto Serif Devanagari', serif",
                "weight": "700"
            },
            {
                "label": "Noto Sans Malayalam",
                "font": "'Noto Sans Malayalam', 'Noto Sans Devanagari', sans-serif",
                "weight": "500"
            },
            {
                "label": "Manjari",
                "font": "'Manjari', 'Noto Sans Malayalam', 'Noto Sans Devanagari', sans-serif",
                "weight": "400"
            }
        ]

    print(f"Extracted {len(chapters)} chapter(s):")
    for ch in chapters:
        print(f"  Chapter {ch['num']}: {ch['title_deva']} ({len(ch['sections'])} sections)")

    html_content = generate_reader_html(book_meta, chapters, fonts, default_size)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    mockup_viewer_dir = Path("mockup/viewer")
    if mockup_viewer_dir.exists():
        with open(mockup_viewer_dir / out_path.name, "w", encoding="utf-8") as f:
            f.write(html_content)

    print(f"[SUCCESS] Standalone HTML Reader generated: {out_path} ({os.path.getsize(out_path):,} bytes)")

    # Post-generation audit check if reference PDF exists
    try:
        try:
            from .audit_reader import audit_book, print_audit_report
        except ImportError:
            from audit_reader import audit_book, print_audit_report

        pdf_p = book_meta.get('pdf_path')
        if not pdf_p:
            title_simple = book_meta.get('title', '').split(',')[0].strip()
            for cand in [
                Path("data/pdf") / f"{title_simple} Sanskrit.pdf",
                Path("data/pdf") / f"{input_path.stem}.pdf"
            ]:
                if cand.exists():
                    pdf_p = str(cand)
                    break
        if pdf_p and Path(pdf_p).exists():
            print(f"[AUDIT] Running post-generation TOC audit against {pdf_p}...")
            audit_res = audit_book(pdf_p, out_path)
            print_audit_report(audit_res)
    except Exception as e:
        print(f"[AUDIT NOTICE] PDF audit check skipped: {e}")

    return out_path


def build_book(book_id: str, config: dict, input_override: str = None, output_override: str = None) -> Path:
    """Build reader HTML for a given book configuration."""
    books = config.get("books", {})
    if book_id not in books:
        raise ValueError(f"Book '{book_id}' not found in configuration. Available: {list(books.keys())}")

    book_meta = books[book_id]
    input_file = input_override or book_meta.get("input_docx")
    output_file = output_override or book_meta.get("output_html")
    chapter_regex = book_meta.get("chapter_regex") or ""
    fonts = config.get("fonts", [])
    default_size = config.get("default_font_size_rem", 1.35)

    is_direct = book_meta.get("direct", False) or book_meta.get("mode") == "direct" or book_meta.get("converter") == "direct"
    if is_direct:
        return convert_docx_direct(
            input_file,
            output_file,
            book_meta=book_meta,
            config=config,
            chapter_regex=chapter_regex
        )

    print(f"\n--- Building '{book_id}' ---")
    print(f"Loading DOCX: {input_file}")

    if book_id.startswith("tb_"):
        try:
            from .baraha_reader import extract_tb_sections, parse_tb_book_paras
        except ImportError:
            from baraha_reader import extract_tb_sections, parse_tb_book_paras
        
        prefix = "3.7" if "3_7" in book_id else ("3.8" if "3_8" in book_id else ("3.9" if "3_9" in book_id else "3.7"))
        tb_map = extract_tb_sections(input_file)
        raw_paras = tb_map.get(prefix, [])
        chapters = parse_tb_book_paras(raw_paras, prefix, book_meta.get("title_sanskrit", ""), book_meta.get("subtitle", ""))
    else:
        try:
            from .baraha_reader import parse_baraha_docx_to_ast, ast_to_reader_chapters
        except ImportError:
            from baraha_reader import parse_baraha_docx_to_ast, ast_to_reader_chapters
        ast_data, _ = parse_baraha_docx_to_ast(input_file, title=book_meta.get("title_sanskrit"))
        chapters = ast_to_reader_chapters(ast_data)

    print(f"Extracted {len(chapters)} chapters:")
    for ch in chapters:
        print(f"  Chapter {ch['num']}: {ch['title_deva']} ({len(ch['sections'])} sections)")

    html_content = generate_reader_html(book_meta, chapters, fonts, default_size)

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    mockup_viewer_dir = Path("mockup/viewer")
    if mockup_viewer_dir.exists():
        with open(mockup_viewer_dir / out_path.name, "w", encoding="utf-8") as f:
            f.write(html_content)

    print(f"Successfully generated {out_path} ({os.path.getsize(out_path):,} bytes)")

    # Post-generation audit check between reference PDF index and generated HTML
    try:
        try:
            from .audit_reader import audit_book, print_audit_report
        except ImportError:
            from audit_reader import audit_book, print_audit_report

        pdf_p = book_meta.get('pdf_path')
        if not pdf_p:
            title_simple = book_meta.get('title', '').split(',')[0].strip()
            for cand in [
                Path("data/pdf") / f"{title_simple} Sanskrit.pdf",
                Path("data/pdf") / f"{book_id.replace('_', ' ').title()} Sanskrit.pdf",
                Path("data/pdf") / f"{book_id.replace('_', ' ').capitalize()} Sanskrit.pdf"
            ]:
                if cand.exists():
                    pdf_p = str(cand)
                    break
        if pdf_p and Path(pdf_p).exists():
            print(f"[AUDIT] Running post-generation TOC audit against {pdf_p}...")
            audit_res = audit_book(pdf_p, out_path)
            print_audit_report(audit_res)
    except Exception as e:
        print(f"[AUDIT NOTICE] PDF audit check skipped: {e}")

    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate VedaVMS Sanskrit Vedic Readers from Baraha DOCX.")
    parser.add_argument("docx_file", nargs="?", default=None, help="Optional direct input DOCX file to convert")
    parser.add_argument("--direct", type=str, default=None, help="Directly convert a DOCX file to an HTML reader without book ID")
    parser.add_argument("--book", type=str, default=None, help="Book identifier from config.json")
    parser.add_argument("--all", action="store_true", help="Build all books in config.json")
    parser.add_argument("--config", type=str, default=None, help="Path to config.json")
    parser.add_argument("--input", type=str, default=None, help="Override input DOCX path")
    parser.add_argument("--output", type=str, default=None, help="Override output HTML path")
    parser.add_argument("--title", type=str, default=None, help="Document title for direct conversion")
    parser.add_argument("--subtitle", type=str, default=None, help="Document subtitle for direct conversion")
    parser.add_argument("--batch", type=str, default=None, help="Directory or glob pattern to convert multiple Baraha files in batch")
    parser.add_argument("--lang", type=str, default=None, choices=["sanskrit", "malayalam"], help="Target language/script (sanskrit or malayalam)")
    parser.add_argument("--chapter", type=str, default=None, help="Filter to specific chapter number (e.g. 3.7, 3.8)")

    args = parser.parse_args()

    # Locate config file
    if args.config:
        config_path = Path(args.config)
    else:
        candidates = [
            Path(__file__).parent / "config.json",
            Path("src/config.json"),
            Path("vedavms_html/config.json"),
            Path(__file__).parent.parent / "src" / "config.json",
        ]
        config_path = next((p for p in candidates if p.exists()), Path("src/config.json"))

    if not config_path.exists():
        print(f"Error: Configuration file not found at {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    built_paths = []
    batch_target = args.batch or (args.docx_file if args.docx_file and Path(args.docx_file).is_dir() else None)
    direct_target = args.direct or (args.docx_file if args.docx_file and args.docx_file.lower().endswith((".docx", ".brh", ".txt")) else None)
    if batch_target:
        p = Path(batch_target)
        if p.is_dir():
            files = sorted(list(p.glob("*.brh")) + list(p.glob("*.txt")) + list(p.glob("*.docx")))
        else:
            import glob
            files = [Path(x) for x in sorted(glob.glob(batch_target))]
        print(f"\n=== Batch Processing {len(files)} Baraha Document(s) ===")
        for f in files:
            try:
                built_paths.append(convert_docx_direct(
                    f,
                    config=config
                ))
            except Exception as ex:
                print(f"[ERROR] Failed to convert {f}: {ex}")
    elif direct_target:
        cli_meta = {}
        if args.lang: cli_meta["lang"] = args.lang
        if args.chapter: cli_meta["chapter_filter"] = args.chapter
        built_paths.append(convert_docx_direct(
            direct_target,
            output_file=args.output,
            config=config,
            title=args.title,
            subtitle=args.subtitle,
            book_meta=cli_meta if cli_meta else None
        ))
    elif args.all:
        for b_id in config.get("books", {}):
            built_paths.append(build_book(b_id, config))
    else:
        book_id = args.book or "taittiriya_upanishad"
        built_paths.append(build_book(book_id, config, args.input, args.output))

    # Save comprehensive audit reports to build/audit_report.md and build/audit_report.txt
    try:
        try:
            from .audit_reader import audit_book, save_audit_reports
        except ImportError:
            from audit_reader import audit_book, save_audit_reports

        audit_results = []
        for b_id, b_meta in config.get("books", {}).items():
            pdf_p = b_meta.get("pdf_path")
            html_p = b_meta.get("output_html")
            if pdf_p and Path(pdf_p).exists() and html_p and Path(html_p).exists():
                audit_results.append(audit_book(pdf_p, html_p))

        if audit_results:
            md_p, txt_p = save_audit_reports(audit_results, out_dir="build")
            print(f"\n[AUDIT] Saved latest audit reports to:")
            print(f"        - {md_p}")
            print(f"        - {txt_p}\n")
    except Exception as e:
        print(f"[AUDIT NOTICE] Could not save audit report files: {e}")


if __name__ == "__main__":
    main()
