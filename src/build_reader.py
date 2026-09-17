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
from pathlib import Path
import xml.etree.ElementTree as ET

try:
    from .transliterate import baraha_to_devanagari
except ImportError:
    try:
        from transliterate import baraha_to_devanagari
    except ImportError:
        _cur = Path(__file__).resolve().parent
        for _p in [_cur, _cur.parent / "src", _cur.parent / "vedavms_html"]:
            if str(_p) not in sys.path:
                sys.path.insert(0, str(_p))
        from transliterate import baraha_to_devanagari

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
            if current_section:
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
    
    Mimics the optimal rendering in Jaimineeya Samavedam:
    - Wraps combining accent marks in zero-width positioned spans with elevated clearance
    - Ensures Visarga (ः) and Anusvara (ं) remain contiguous with the base syllable so
      no dotted circle (◌ः) is ever rendered by OpenType shapers (like Tiro Sanskrit)
    - Applies independent accent font-size, font-weight, and elevation across all fonts
    """
    if not text:
        return text

    # 1. Normalize ordering of accents and visarga/colon:
    # Placing visarga after an accent or </span> boundary causes the OpenType text shaper
    # to treat visarga as an orphaned mark without a base syllable, rendering U+25CC (◌ः).
    # Moving visarga before the accent ensures it attaches directly to the base syllable.
    text = re.sub(r'([\u0951\u0952\u1CDA]+)\s*([ः:])', r'ः\1', text)
    text = re.sub(r'(\([1-4]\))\s*([ः:])', r'ः\1', text)

    # 2. Wrap accents into zero-width styled spans
    # Svarita (U+0951)
    text = text.replace('\u0951', '<span class="accent-swarita">&#x0951;</span>')
    # Deergha Svarita (U+1CDA)
    text = text.replace('\u1CDA', '<span class="accent-deergha">&#x1CDA;</span>')
    # Anudatta (U+0952): handle double anudatta then single anudatta
    text = text.replace('\u0952\u0952', '<span class="accent-anudatta">&#x0952;&#x0952;</span>')
    text = text.replace('\u0952', '<span class="accent-anudatta">&#x0952;</span>')

    # Also handle ASCII / Baraha accent markers if any remain
    text = text.replace('(1)', '<span class="accent-swarita">&#x0951;</span>')
    text = text.replace('(2)', '<span class="accent-anudatta">&#x0952;</span>')
    text = text.replace('(3)', '<span class="accent-deergha">&#x1CDA;</span>')
    text = text.replace('(4)', '<span class="accent-deergha">&#x1CDA;</span>')

    # 3. Final safety: ensure no visarga or colon was pushed after a closing span
    text = re.sub(r'(<span class="accent-[^"]+">[^<]+</span>)\s*([ः:])', r'ः\1', text)

    return text


def generate_reader_html(book_meta: dict, chapters: list[dict], fonts: list[dict], default_font_size: float = 1.35) -> str:
    """Generate standalone responsive HTML reader with TOC navigation and typography controls."""
    title = book_meta.get("title", "Vedic Sanskrit Reader")
    subtitle = book_meta.get("subtitle", "कृष्ण यजुर्वेदीय आरण्यकम्")
    back_link = book_meta.get("back_link", "index.html")
    back_label = book_meta.get("back_label", "← Home")

    fonts_js = json.dumps(fonts, ensure_ascii=False)

    html_parts = []
    html_parts.append(f'''<!DOCTYPE html>
<html lang="sa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>{title} - Sanskrit Vedic Text</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+Devanagari:wght@400;500;600;700&family=Tiro+Devanagari+Sanskrit:ital@0;1&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        @font-face {{
            font-family: 'AdishilaVedic';
            src: local('AdishilaVedic'), url('fonts/AdishilaVedic.ttf') format('truetype');
            font-weight: 400 500;
            font-style: normal;
            font-display: swap;
            size-adjust: 135%;
        }}
        @font-face {{
            font-family: 'AdishilaVedic';
            src: local('AdishilaVedicBold'), local('AdishilaVedic-Bold'), url('fonts/AdishilaVedicBold.ttf') format('truetype');
            font-weight: 600 700;
            font-style: normal;
            font-display: swap;
            size-adjust: 135%;
        }}
        @font-face {{
            font-family: 'Adishila San';
            src: local('Adishila San'), url('fonts/AdishilaSan.ttf') format('truetype');
            font-weight: 400 500;
            font-style: normal;
            font-display: swap;
            size-adjust: 125%;
        }}
        @font-face {{
            font-family: 'Adishila San';
            src: local('Adishila San Bold'), local('AdishilaSan-Bold'), url('fonts/AdishilaSanBoldB.ttf') format('truetype');
            font-weight: 600 700;
            font-style: normal;
            font-display: swap;
            size-adjust: 125%;
        }}
        @font-face {{
            font-family: 'Adishila San';
            src: local('Adishila San Italic'), local('AdishilaSan-Italic'), url('fonts/AdishilaSanItalic.ttf') format('truetype');
            font-weight: 400 500;
            font-style: italic;
            font-display: swap;
            size-adjust: 125%;
        }}
        @font-face {{
            font-family: 'Adishila San';
            src: local('Adishila San Bold Italic'), local('AdishilaSan-BoldItalic'), url('fonts/AdishilaSanBoldItalic.ttf') format('truetype');
            font-weight: 600 700;
            font-style: italic;
            font-display: swap;
            size-adjust: 125%;
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
            --mantra-size: calc(var(--font-size) * 1.25);
            --swarita-bottom: 0.42em;
            --anudatta-bottom: 0.40em;
            --accent-font: 'AdishilaVedic', 'Noto Serif Devanagari', 'Tiro Devanagari Sanskrit', serif;
            --verse-font: 'Noto Serif Devanagari', 'Adishila San', 'Tiro Devanagari Sanskrit', serif;
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
            max-width: 1240px;
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

        .layout {{
            max-width: 1240px;
            margin: 1.75rem auto;
            padding: 0 1rem;
            display: grid;
            grid-template-columns: 290px 1fr;
            gap: 2rem;
            align-items: flex-start;
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
            color: var(--dark-brown);
            font-size: 1rem;
            flex: 1;
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
            padding-left: 0.85rem;
            overflow: hidden;
            max-height: 2000px;
            transition: max-height 0.3s ease;
        }}

        .toc-chapter.collapsed .toc-sub-list {{
            max-height: 0;
            padding-top: 0;
            padding-bottom: 0;
        }}

        .toc-sub-list li {{
            margin-bottom: 0.3rem;
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
            padding: 2.25rem 2.75rem;
            box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            --font-size: {default_font_size}rem;
            font-size: var(--font-size);
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
            font-size: 2.25rem;
            color: var(--maroon);
            margin-bottom: 0.5rem;
            letter-spacing: 0.5px;
        }}

        .main-title .sub-heading {{
            font-size: 1.15rem;
            color: var(--saffron);
            font-weight: 600;
        }}

        .chapter-container {{
            margin-bottom: 3.5rem;
        }}

        .chapter-heading {{
            background: linear-gradient(90deg, #7B1113 0%, #A52A2A 100%);
            color: white;
            padding: 0.9rem 1.6rem;
            border-radius: 8px;
            font-size: 1.5rem;
            margin-bottom: 1.75rem;
            font-family: 'Noto Serif Devanagari', serif;
            box-shadow: 0 3px 8px rgba(123,17,19,0.25);
        }}

        .anuvaka-block {{
            background: #FFFAF5;
            border: 1px solid #F0E6D8;
            border-left: 5px solid var(--saffron);
            border-radius: 8px;
            padding: 1.35rem 1.6rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        }}

        .anuvaka-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px dashed #E0D0C0;
            padding-bottom: 0.6rem;
            margin-bottom: 1.15rem;
        }}

        .anuvaka-num {{
            font-weight: 700;
            color: var(--maroon);
            font-size: 1.15rem;
            font-family: 'Noto Serif Devanagari', serif;
        }}

        .anuvaka-code {{
            font-size: 0.82rem;
            color: #777;
            background: #EFEFEF;
            padding: 0.2rem 0.55rem;
            border-radius: 4px;
            font-family: monospace;
        }}

        .verse-text {{
            font-family: var(--verse-font);
            font-weight: var(--verse-weight);
            font-size: var(--mantra-size, calc(var(--font-size) * 1.25));
            line-height: 2.2;
            letter-spacing: 0.015em;
            color: #111111;
            text-align: justify;
        }}

        .verse-p {{
            margin-bottom: 1.15rem;
            text-indent: 0;
        }}

        .verse-p:last-child {{
            margin-bottom: 0;
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
            left: 0;
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
            left: 0;
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
            left: 0;
            bottom: var(--swarita-bottom);
            isolation: isolate;
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
                font-size: 1.45rem;
                line-height: 1.35;
                word-break: break-word;
                overflow-wrap: break-word;
            }}

            .main-title .sub-heading {{
                font-size: 0.92rem;
            }}

            .chapter-container {{
                margin-bottom: 2.25rem;
            }}

            .chapter-heading {{
                font-size: 1.18rem;
                padding: 0.7rem 0.95rem;
                border-radius: 6px;
                margin-bottom: 1.25rem;
                word-break: break-word;
                overflow-wrap: break-word;
            }}

            .anuvaka-block {{
                padding: 0.95rem 0.85rem;
                margin-bottom: 1.25rem;
                border-left-width: 4px;
            }}

            .anuvaka-header {{
                margin-bottom: 0.85rem;
                padding-bottom: 0.45rem;
            }}

            .anuvaka-num {{
                font-size: 1rem;
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

        @page {{
            size: auto;
            margin: 15mm 18mm 15mm 18mm;
        }}

        @media print {{
            *, *::before, *::after {{
                box-sizing: border-box !important;
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
            .header, .toc-sidebar, .back-to-top, .modal-overlay {{
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
                    <button class="toggle-sidebar-btn" onclick="toggleSidebar()" title="Toggle Contents Panel (सूची)" id="sidebar-toggle-btn">☰ सूची</button>
                    <a href="{back_link}" class="btn-ctrl">{back_label}</a>
                </div>
            </div>
            <div class="controls">
                <button class="btn-ctrl" id="font-toggle-btn" onclick="toggleFont()" title="Toggle Sanskrit Font">Font: Noto Serif</button>
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
                <div class="toc-title">सूची (Contents)</div>
                <button class="toc-close-btn" onclick="closeMobileToc()" title="Close Contents" aria-label="Close">✕</button>
            </div>
            <ul class="toc-list">
''')

    for ch in chapters:
        ch_id = f"chapter-{ch['num']}"
        sub_sections = [
            s for s in ch["sections"]
            if not (s.get('is_intro') or (s['num'] == str(ch['num']) and (not s.get('title_raw') or s.get('title_raw') == ch.get('title_raw'))))
        ]
        has_subsections = len(sub_sections) > 0
        if has_subsections:
            html_parts.append(f'''                <li class="toc-chapter" id="toc-{ch_id}">
                    <div class="toc-ch-header" onclick="toggleTocChapter('toc-{ch_id}')">
                        <div class="toc-ch-title"><a href="#{ch_id}">{ch['title_deva']}</a></div>
                        <span class="toc-ch-toggle">▼</span>
                    </div>
                    <ul class="toc-sub-list">
''')
            for sec in sub_sections:
                sec_id = f"sec-{sec['num'].replace('.', '-')}"
                title_disp = f"{sec['num']} {sec['title_deva']}".strip()
                html_parts.append(f'                        <li><a href="#{sec_id}">{title_disp}</a></li>\n')
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
                <div class="sub-heading">{subtitle}</div>
            </div>
''')

    for ch in chapters:
        ch_id = f"chapter-{ch['num']}"
        html_parts.append(f'''            <section class="chapter-container" id="{ch_id}">
                <h2 class="chapter-heading">{ch['title_deva']}</h2>
''')
        for sec in ch["sections"]:
            sec_id = f"sec-{sec['num'].replace('.', '-')}"
            code_span = f'<span class="anuvaka-code">{sec["ta_code"]}</span>' if sec["ta_code"] else ''
            is_intro = sec.get('is_intro', False) or (sec['num'] == str(ch['num']) and (not sec.get('title_raw') or sec.get('title_raw') == ch.get('title_raw')))

            if is_intro:
                if code_span:
                    header_html = f'''                    <div class="anuvaka-header">
                        {code_span}
                    </div>'''
                else:
                    header_html = ''
            else:
                title_disp_deva = f"{sec['num']} {format_vedic_html(sec['title_deva'])}".strip()
                header_html = f'''                    <div class="anuvaka-header">
                        <span class="anuvaka-num">{title_disp_deva}</span>
                        {code_span}
                    </div>'''

            html_parts.append(f'''                <div class="anuvaka-block" id="{sec_id}">
{header_html}
                    <div class="verse-text">
''')
            for deva_line in sec["content_deva"]:
                html_parts.append(f'                        <p class="verse-p">{format_vedic_html(deva_line)}</p>\n')
            html_parts.append('''                    </div>
                </div>
''')
        html_parts.append('''            </section>
''')

    html_parts.append(f'''        </main>
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
                    .header, .toc-sidebar, .back-to-top, .modal-overlay {{
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
                        isolation: isolate !important;
                    }}
                    .accent-swarita {{ bottom: var(--swarita-bottom, 0.42em) !important; }}
                    .accent-anudatta {{ bottom: var(--anudatta-bottom, 0.40em) !important; }}
                    .accent-deergha {{ bottom: var(--swarita-bottom, 0.42em) !important; }}
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
            sec_title = sec_data.get('section_title', '')
            num_m = re.match(r'^(\d+)\.\s*(.*)', sec_title)
            ch_num = int(num_m.group(1)) if num_m else (len(chapters) + 1)

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
                    sub_num = f"{ch_num}.{len(sections)+1}"
                    sub_title = header
                ta_code = sub_data.get('ta_code', '')
                content = sub_data.get('content_lines', [])
                sections.append({
                    'num': sub_num,
                    'title_deva': sub_title,
                    'ta_code': ta_code,
                    'content_deva': content
                })
            chapters.append({
                'num': ch_num,
                'title_deva': sec_title,
                'sections': sections
            })
    return chapters


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

    print(f"\n--- Building '{book_id}' ---")
    print(f"Loading DOCX: {input_file}")
    raw_paras = extract_docx_paragraphs(input_file)
    print(f"Loaded {len(raw_paras)} paragraphs.")

    chapters = parse_chapters_and_sections(raw_paras, chapter_regex)
    print(f"Extracted {len(chapters)} chapters:")
    for ch in chapters:
        print(f"  Chapter {ch['num']}: {ch['title_deva']} ({len(ch['sections'])} sections)")

    html_content = generate_reader_html(book_meta, chapters, fonts, default_size)

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Successfully generated {out_path} ({os.path.getsize(out_path):,} bytes)")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate VedaVMS Sanskrit Vedic Readers from Baraha DOCX.")
    parser.add_argument("--book", type=str, default="taittiriya_upanishad", help="Book identifier from config.json")
    parser.add_argument("--all", action="store_true", help="Build all books in config.json")
    parser.add_argument("--config", type=str, default=None, help="Path to config.json")
    parser.add_argument("--input", type=str, default=None, help="Override input DOCX path")
    parser.add_argument("--output", type=str, default=None, help="Override output HTML path")

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

    if args.all:
        for b_id in config.get("books", {}):
            build_book(b_id, config)
    else:
        build_book(args.book, config, args.input, args.output)


if __name__ == "__main__":
    main()
