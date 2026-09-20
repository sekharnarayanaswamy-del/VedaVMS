"""Baraha DOCX extraction, Vedic transliteration, and AST generator for VedaVMS.

Converts Baraha-encoded Vedic documents into a hierarchical JSON AST suitable for
multi-format rendering (HTML readers, PDF generation, or downstream verification).
"""

import os
import sys
import re
import json
import zipfile
import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

# Import transliteration engine
try:
    from .transliterate import baraha_to_devanagari, is_english_text, clean_baraha_english
except ImportError:
    try:
        from transliterate import baraha_to_devanagari, is_english_text, clean_baraha_english
    except ImportError:
        _cur = Path(__file__).resolve().parent
        for _p in [_cur, _cur.parent / "src"]:
            if str(_p) not in sys.path:
                sys.path.insert(0, str(_p))
        from transliterate import baraha_to_devanagari, is_english_text, clean_baraha_english

try:
    from .build_reader import format_vedic_html
except ImportError:
    try:
        from build_reader import format_vedic_html
    except ImportError:
        def format_vedic_html(t):
            return t

DOCX_NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def extract_docx_elements(docx_path: str | Path) -> list[tuple[str, any]]:
    """Extract ordered paragraphs ('p') and tables ('tbl') from Word (.docx) document."""
    docx_path = Path(docx_path)
    if not docx_path.exists():
        for cand in [
            Path("data/baraha") / docx_path,
            Path(__file__).parent.parent / "data/baraha" / docx_path,
            Path(__file__).parent.parent / docx_path,
            Path(__file__).parent / docx_path
        ]:
            if cand.exists():
                docx_path = cand
                break
        else:
            raise FileNotFoundError(f"Input document not found: {docx_path}")

    with zipfile.ZipFile(docx_path, 'r') as z:
        doc_xml = z.read('word/document.xml')

    root = ET.fromstring(doc_xml)
    body = root.find('.//w:body', DOCX_NS)
    elements = []

    for child in body:
        tag = child.tag.split('}')[-1]
        if tag == 'p':
            parts = []
            for node in child.iter():
                nt = node.tag.split('}')[-1]
                if nt == 't' and node.text:
                    parts.append(node.text)
                elif nt == 'tab':
                    parts.append('\t')
            t = ''.join(parts).strip()
            if t:
                elements.append(('p', t))
        elif tag == 'tbl':
            tbl_html = parse_docx_table_node(child)
            if tbl_html:
                elements.append(('tbl', tbl_html))

    return elements


def parse_docx_table_node(tbl_node) -> str:
    """Generic Word table parser with dynamic vMerge (rowspan) and gridSpan (colspan) handling."""
    raw_rows = []
    for r in tbl_node.findall('.//w:tr', DOCX_NS):
        raw_cells = []
        for c in r.findall('.//w:tc', DOCX_NS):
            tcPr = c.find('w:tcPr', DOCX_NS)
            vMerge = None
            gridSpan = 1
            if tcPr is not None:
                vm = tcPr.find('w:vMerge', DOCX_NS)
                if vm is not None:
                    vMerge = vm.attrib.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'continue')
                gs = tcPr.find('w:gridSpan', DOCX_NS)
                if gs is not None:
                    gridSpan = int(gs.attrib.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 1))

            text_parts = []
            for p in c.findall('.//w:p', DOCX_NS):
                p_text = ''.join(t.text for t in p.findall('.//w:t', DOCX_NS) if t.text).strip()
                if p_text:
                    text_parts.append(p_text)
            text = '<br>'.join(text_parts)
            raw_cells.append({
                'text': text,
                'vMerge': vMerge,
                'gridSpan': gridSpan
            })
        raw_rows.append(raw_cells)

    if not raw_rows:
        return ''

    num_rows = len(raw_rows)
    for r_idx in range(num_rows):
        for c_idx, cell in enumerate(raw_rows[r_idx]):
            if cell['vMerge'] == 'restart':
                span = 1
                for next_r in range(r_idx + 1, num_rows):
                    if c_idx < len(raw_rows[next_r]) and raw_rows[next_r][c_idx]['vMerge'] == 'continue':
                        span += 1
                    else:
                        break
                cell['rowSpan'] = span
            elif cell['vMerge'] == 'continue':
                cell['rowSpan'] = 0
            else:
                cell['rowSpan'] = 1

    r0 = raw_rows[0]
    r0_text = ' '.join(c['text'] for c in r0).lower()
    is_header = any(k in r0_text for k in ['serial', 'no.', 'name', 'month', 'star', 'padam', 'rasi', 'ruthu', 'ayanam'])

    html_out = ['<div class="table-responsive"><table class="vedic-table">']
    start_row = 0
    if is_header:
        html_out.append('<thead><tr>')
        for cell in r0:
            if cell['rowSpan'] == 0:
                continue
            attrs = []
            if cell['gridSpan'] > 1:
                attrs.append(f'colspan="{cell["gridSpan"]}"')
            if cell['rowSpan'] > 1:
                attrs.append(f'rowspan="{cell["rowSpan"]}"')
            attr_str = (' ' + ' '.join(attrs)) if attrs else ''
            html_out.append(f'<th{attr_str}>{cell["text"]}</th>')
        html_out.append('</tr></thead>')
        start_row = 1

    html_out.append('<tbody>')
    for r_idx in range(start_row, num_rows):
        html_out.append('<tr>')
        for cell in raw_rows[r_idx]:
            if cell['rowSpan'] == 0:
                continue
            attrs = []
            if cell['gridSpan'] > 1:
                attrs.append(f'colspan="{cell["gridSpan"]}"')
            if cell['rowSpan'] > 1:
                attrs.append(f'rowspan="{cell["rowSpan"]}"')
            if cell['rowSpan'] > 1:
                attrs.append('class="kumbha-center"')
            attr_str = (' ' + ' '.join(attrs)) if attrs else ''
            html_out.append(f'<td{attr_str}>{cell["text"]}</td>')
        html_out.append('</tr>')
    html_out.append('</tbody></table></div>')
    return ''.join(html_out)


def extract_docx_paragraphs(docx_path: str | Path) -> list[str]:
    """Extract raw paragraph text strings from DOCX document (backward compatible)."""
    elements = extract_docx_elements(docx_path)
    paras = []
    for el_type, val in elements:
        if el_type == 'p':
            paras.append(val)
        elif el_type == 'tbl':
            paras.append(val)
    return paras


def table_to_html(rows_or_html) -> str:
    """Format table into responsive HTML table markup (backward compatible)."""
    if isinstance(rows_or_html, str):
        return rows_or_html
    if not rows_or_html:
        return ""
    html = ['<div class="table-responsive" style="overflow-x:auto; margin:1.25rem 0;">'
            '<table class="vedic-table" style="width:100%; border-collapse:collapse; font-size:0.92rem;">']
    header_done = False
    for r_idx, row in enumerate(rows_or_html):
        if not header_done:
            html.append('<thead><tr style="background:#FFF3E0; border-bottom:2px solid #D84315;">')
            for cell in row:
                html.append(f'<th style="border:1px solid #EADDC9; padding:0.55rem 0.75rem; text-align:left; color:#7B1113; font-weight:600;">{cell}</th>')
            html.append('</tr></thead><tbody>')
            header_done = True
        else:
            bg = "#FFFDF9" if r_idx % 2 == 0 else "#FFFFFF"
            html.append(f'<tr style="background:{bg};">')
            for cell in row:
                html.append(f'<td style="border:1px solid #EADDC9; padding:0.45rem 0.75rem;">{cell}</td>')
            html.append('</tr>')
    html.append('</tbody></table></div>')
    return "".join(html)


def is_krama_line(text: str) -> bool:
    """Detect whether a line is a Krama patha paired chant."""
    t = text.strip()
    if not t:
        return False
    if is_english_text(t):
        return False
    if re.match(r'^(?:1[567]\b|\d+\.\d+)', t):
        return False
    if re.match(r'^[-=_\.]{3,}$', t):
        return False
    if 'bagavatE' in t.lower() or 'anuva' in t.lower() or 'krama' in t.lower():
        return False
    if ',' in t:
        return True
    if '\t' in t and len(t.split('\t')) >= 2:
        return True
    return False


def split_krama(text: str) -> tuple[str, str]:
    """Split a Krama line into Team 1 (Left column) and Team 2 (Right column)."""
    t = text.strip()
    if ',' in t:
        parts = t.split(',', 1)
    elif '\t' in t:
        parts = t.split('\t', 1)
    else:
        parts = [t, '']
    col1 = parts[0].strip()
    col2 = parts[1].strip().strip(',') if len(parts) > 1 else ''
    return col1, col2


def build_krama_table(rows: list[tuple[str, str]]) -> str:
    """Build a 2-column Krama patha HTML table matching canonical print layout."""
    html_lines = [
        '<div class="krama-table-container">',
        '  <table class="krama-table">',
        '    <tbody>'
    ]
    for col1, col2 in rows:
        d1 = baraha_to_devanagari(col1) if col1 else ''
        d2 = baraha_to_devanagari(col2) if col2 else ''
        h1 = format_vedic_html(d1) if d1 else '&nbsp;'
        h2 = format_vedic_html(d2) if d2 else '&nbsp;'
        html_lines.append(f'      <tr><td class="krama-cell">{h1}</td><td class="krama-cell">{h2}</td></tr>')
    html_lines.append('    </tbody>')
    html_lines.append('  </table>')
    html_lines.append('</div>')
    return '\n'.join(html_lines)


def preprocess_inline_citations(text: str) -> str:
    """Process </inline> and <inline> tags in Baraha lines, preserving citations as English text."""
    if '</inline>' not in text.lower() and '<inline>' not in text.lower():
        return text

    # 1. Explicit <inline>...</inline>
    def repl_explicit(m):
        content = m.group(1).strip()
        return f'<lang=eng><span class="inline-citation">{clean_baraha_english(content)}</span><lang=def>'
    text = re.sub(r'<inline>(.*?)</inline>', repl_explicit, text, flags=re.I)

    # 2. Parenthesized citation before </inline>, e.g. "tasya... || 3 (TA .6.12.3)</inline>"
    def repl_paren(m):
        prefix = m.group(1)
        cit = m.group(2).strip()
        return f'{prefix}<lang=eng><span class="inline-citation">{clean_baraha_english(cit)}</span><lang=def>'
    text = re.sub(r'^(.*?)((?:\([^\)]+\)|\[[^\]]+\]))\s*</inline>', repl_paren, text, flags=re.I)

    # 3. Standalone citation line with </inline>, e.g. "TB 3.10.5.1 for para 17 </inline>"
    def repl_bare(m):
        cit = m.group(1).strip()
        return f'<lang=eng><span class="inline-citation">{clean_baraha_english(cit)}</span><lang=def>'
    text = re.sub(r'^(.*?)\s*</inline>', repl_bare, text, flags=re.I)

    # Clean any remaining inline tags
    text = re.sub(r'</?inline>', '', text, flags=re.I)
    return text


def process_baraha_line(text: str, current_lang: str) -> tuple[str, str]:
    """Process text with <lang=eng> and <lang=def> tags according to current_lang state.
    Returns (rendered_text, new_current_lang).
    """
    text = preprocess_inline_citations(text)
    parts = re.split(r'(<lang=(?:eng|def)>)', text, flags=re.I)
    out = []
    lang = current_lang
    for p in parts:
        if not p:
            continue
        low = p.lower()
        if low == '<lang=eng>':
            lang = 'eng'
        elif low == '<lang=def>':
            lang = 'def'
        else:
            if lang == 'eng' or is_english_text(p):
                out.append(clean_baraha_english(p))
            else:
                out.append(baraha_to_devanagari(p))
    res = ''.join(out).strip()
    return res, lang


def normalize_citation(text: str) -> str:
    """Strip outer parenthesis if present and trim whitespace."""
    t = text.strip()
    if t.startswith('(') and t.endswith(')'):
        t = t[1:-1].strip()
    return t


def is_scriptural_citation(text: str) -> bool:
    """Check if a line immediately after a heading is a scriptural citation or attribution note."""
    if re.search(r'[#$|]', text) or re.search(r'</?inline>', text, re.I) or re.search(r'</?(?:i|em)\b', text, re.I):
        return False
    clean = text.strip('() \t*')
    if not clean:
        return False
    if re.match(r'^(?:T\.?[ABS]\.?|R\.?V\.?|Rig\s*V[Ee]da|TS|TB|TA|RV|EAK)\b', clean, re.I):
        return True
    if re.match(r'^(?:Exact\s+source|Starting\s+frOm\s+TB|To\s+bE\s+chanted|Rig\s*Vedic\s+convention|Part\s+\d+\s*\(|OrdEr\s+of\s+chanting|No\s+Definite\s+Source)', clean, re.I):
        return True
    if re.match(r'^(?:REf:|No\s+Ref\b)', clean, re.I):
        return True
    if re.search(r'\b(?:T\.?[ABS]\.?|R\.?V\.?|TS|TB|TA|RV)\s*[\d\.]+', clean, re.I) and ('/' in clean or 'for' in clean.lower()):
        return True
    return False


def parse_baraha_elements(
    elements: list[tuple[str, any]],
    chapter_regex: str = None,
    intro_start: str = None,
    intro_sections: dict = None
) -> list[dict]:
    """Single, unified Vedic element parser for standard and complex Baraha documents.
    Features:
    - Dynamic language mode tracking (<lang=eng>, <lang=def>).
    - Table preservation from Word XML.
    - Configuration-driven unnumbered intro sections.
    - Sequential chapter validation.
    - Automatic Krama 2-column table detection.
    """
    intro_sections = intro_sections or {}

    start_idx = 0
    if intro_start:
        for idx, el in enumerate(elements):
            if el[0] == 'p' and el[1].strip().lower() == intro_start.lower():
                start_idx = idx
                break

    ch_pattern = re.compile(chapter_regex, re.I) if chapter_regex and chapter_regex.strip() else None
    sec_regex = re.compile(r'^(\d+\.\d+(?:\.\d+)?)\.?\t?\s*(.*)')
    tb_regex = re.compile(r'^(T\.B\.\s*\d+\.\d+\.\d+\.\d+)')
    fallback_ch_regex = re.compile(r'^([1-9]|1\d|2\d)\.?\t?\s+([a-zA-Z].*)')

    chapters = []
    current_ch = None
    current_sec = None
    current_lang = 'def'

    # If document starts with an intro section, initialize Chapter 1 in English mode
    if start_idx > 0 or (elements and intro_start and elements[0][1].strip().lower() == intro_start.lower()):
        current_ch = {
            'num': 1,
            'title_raw': 'Introduction',
            'title_deva': '1. Introduction',
            'is_english': True,
            'sections': []
        }
        chapters.append(current_ch)
        current_lang = 'eng'

    i = start_idx
    while i < len(elements):
        el_type, val = elements[i]

        if el_type == 'tbl':
            if current_sec is not None:
                current_sec['content'].append(val)
                current_sec['content_deva'].append(val)
            elif current_ch is not None:
                current_sec = {
                    'num': f"{current_ch['num']}.{len(current_ch['sections'])+1}",
                    'title_raw': 'Table',
                    'title_deva': 'Table',
                    'ta_code': '',
                    'content': [val],
                    'content_deva': [val]
                }
                current_ch['sections'].append(current_sec)
            i += 1
            continue

        p = val.strip()
        if re.match(r'^[+\-*=_~#]{3,}$', p):
            i += 1
            continue

        p = re.sub(r'^[+\-*=_~#]{2,}\s*', '', p).strip()
        if not p:
            i += 1
            continue

        # Check if line contains </inline> or <i> forcing it to remain as body text (not heading/badge)
        is_forced_inline = bool(re.search(r'</?inline>', p, flags=re.I) or re.search(r'</?(?:i|em)\b', p, flags=re.I))

        low_p = p.lower()

        # Standalone language mode tags
        if low_p in ('<lang=eng>', '<lang=def>'):
            current_lang = 'eng' if low_p == '<lang=eng>' else 'def'
            i += 1
            continue

        # Skip intro title itself
        if intro_start and low_p == intro_start.lower() and current_ch and current_ch['num'] == 1 and not current_ch['sections']:
            i += 1
            continue

        # Check for unnumbered chapter 2 switch if preliminary section
        if low_p == 'pooja preparations' and current_ch and current_ch['num'] == 1:
            current_ch = {
                'num': 2,
                'title_raw': 'Pooja Preparations',
                'title_deva': '2. Pooja Preparations',
                'ta_code': '',
                'is_english': True,
                'sections': []
            }
            chapters.append(current_ch)
            current_sec = None
            i += 1
            continue

        # Check intro_sections mapping (for unnumbered headings in preliminary pages)
        if intro_sections and low_p in intro_sections:
            sec_full = intro_sections[low_p]
            parts = sec_full.split(' ', 1)
            s_num = parts[0]
            s_name = parts[1] if len(parts) > 1 else ''
            current_sec = {
                'num': s_num,
                'title_raw': s_name,
                'title_deva': s_name,
                'ta_code': '',
                'content': [],
                'content_deva': []
            }
            current_ch['sections'].append(current_sec)
            i += 1
            continue

        # Nakshatra items inside Chapter 19 MUST be captured as subsections
        if not is_forced_inline and current_ch and current_ch['num'] == 19:
            nak_m = re.match(r'^(\d+)\.?\s*(nakShatra[MH]?|paurNamAsi|amAvAsi|candramA|ahO|uShA|sUrya[H]?|aditi[H]?|viShNu[H]?|agni[H]?|anumatI|havyavAha)(.*)', p, re.I)
            if nak_m:
                item_num = nak_m.group(1)
                item_title = (nak_m.group(2) + nak_m.group(3)).strip()
                sec_num = f"19.{item_num}"
                sec_deva, current_lang = process_baraha_line(item_title, current_lang)
                current_sec = {
                    'num': sec_num,
                    'title_raw': item_title,
                    'title_deva': sec_deva,
                    'ta_code': '',
                    'content': [],
                    'content_deva': []
                }
                current_ch['sections'].append(current_sec)
                i += 1
                continue

        # Chapter heading check
        ch_m = (ch_pattern.match(p) if ch_pattern else fallback_ch_regex.match(p)) if not is_forced_inline else None
        if ch_m and not re.search(r'[q#$|]', p) and len(p) < 90:
            ch_num = int(ch_m.group(1))
            ch_raw_title = ch_m.group(2).strip() if ch_m.lastindex >= 2 and ch_m.group(2) else ''

            excluded_starts = (
                'nakShatraM', 'nakShatraH', 'OM', 'Oum', 'CatraM', 'vAdyaM', 'gItaM', 'aSvaM', 'rathaM',
                'namaH', 'svAhA', 'item no', 'purusha sukhtam'
            )
            is_valid = True
            if current_ch is not None and ch_num != current_ch['num'] + 1:
                is_valid = False
            elif any(ch_raw_title.lower().startswith(x.lower()) for x in excluded_starts):
                is_valid = False
            elif re.search(r'\b(namaH|svAhA|OM|Oum|CatraM|vAdyaM|gItaM|aSvaM|rathaM)\b', ch_raw_title, re.I):
                is_valid = False
            elif 'item no' in ch_raw_title.lower() or 'persons' in ch_raw_title.lower():
                is_valid = False

            if is_valid:
                # Transliterate title if Sanskrit, or keep as English
                if is_english_text(ch_raw_title) or (ch_num in (1, 2) and current_lang == 'eng'):
                    ch_raw_title = clean_baraha_english(ch_raw_title)
                    ch_deva = ch_raw_title
                else:
                    current_lang = 'def'
                    ch_deva = baraha_to_devanagari(ch_raw_title)

                current_ch = {
                    'num': ch_num,
                    'title_raw': ch_raw_title,
                    'title_deva': f"{ch_num}. {ch_deva}" if ch_deva else f"{ch_num}.",
                    'ta_code': '',
                    'is_english': is_english_text(ch_raw_title),
                    'sections': []
                }
                chapters.append(current_ch)
                current_sec = None
                i += 1
                continue

        # Numbered section check (e.g. 3.1, 16.1, 16.1.1 or T.B. 3.11.1.1)
        sm = sec_regex.match(p) if not is_forced_inline else None
        tb_m = tb_regex.match(p) if not is_forced_inline else None
        if (sm or tb_m) and current_ch:
            sec_num = sm.group(1) if sm else tb_m.group(1)
            sec_name = sm.group(2).strip() if sm else ''
            sec_deva, current_lang = process_baraha_line(sec_name, current_lang)
            clean_sec_name = re.sub(r'</?lang=[^>]+>', '', sec_name, flags=re.I).strip()
            if is_english_text(clean_sec_name):
                clean_sec_name = clean_baraha_english(clean_sec_name)
            current_sec = {
                'num': sec_num,
                'title_raw': clean_sec_name,
                'title_deva': sec_deva,
                'ta_code': sec_num if tb_m else '',
                'content': [],
                'content_deva': []
            }
            current_ch['sections'].append(current_sec)
            i += 1
            continue

        # Scriptural citation attribute immediately under section or chapter header before content
        if not is_forced_inline and is_scriptural_citation(p):
            cit = normalize_citation(p)
            if current_sec is not None and not current_sec.get('content'):
                if current_sec.get('ta_code'):
                    current_sec['ta_code'] += ' / ' + cit
                else:
                    current_sec['ta_code'] = cit
                i += 1
                continue
            elif current_ch is not None and not current_ch.get('sections'):
                if current_ch.get('ta_code'):
                    current_ch['ta_code'] += ' / ' + cit
                else:
                    current_ch['ta_code'] = cit
                i += 1
                continue

        # Content line
        line_deva, current_lang = process_baraha_line(p, current_lang)
        if not line_deva:
            i += 1
            continue

        if current_sec is not None:
            current_sec['content'].append(p)
            current_sec['content_deva'].append(line_deva)
        elif current_ch is not None:
            current_sec = {
                'num': str(current_ch['num']),
                'title_raw': current_ch['title_raw'],
                'title_deva': current_ch['title_deva'],
                'ta_code': current_ch.get('ta_code', ''),
                'content': [p],
                'content_deva': [line_deva],
                'is_intro': True
            }
            current_ch['sections'].append(current_sec)

        i += 1

    # Post-process Krama sections generically into 2-column tables
    for ch in chapters:
        ch_title = (ch.get('title_raw', '') + ' ' + ch.get('title_deva', '')).lower()
        ch_is_eng = ch.get('is_english', False) or ch.get('num') in (1, 2)
        if ch_is_eng:
            continue

        for sec in ch['sections']:
            sec_title = (sec.get('title_raw', '') + ' ' + sec.get('title_deva', '')).lower()
            if sec.get('is_english', False):
                continue

            # Krama patha is Vedic Sanskrit chanting specifically in Krama sections (Chapters 15, 16, 17)
            is_krama = (
                any(k in (ch_title + ' ' + sec_title) for k in ['krama', 'क्रम'])
                or (ch.get('num') in (15, 16, 17))
            )
            if not is_krama:
                continue

            non_empty = [l for l in sec['content'] if not re.match(r'^[-=_\.]{3,}$', l.strip())]
            krama_cnt = sum(1 for l in non_empty if is_krama_line(l))
            if krama_cnt == 0:
                continue

            new_c = []
            new_cd = []
            buf = []
            for raw_l in sec['content']:
                raw_s = raw_l.strip()
                if not raw_s or re.match(r'^[-=_\.]{3,}$', raw_s):
                    continue
                if is_krama_line(raw_s):
                    c1, c2 = split_krama(raw_s)
                    buf.append((c1, c2))
                else:
                    if buf:
                        t_html = build_krama_table(buf)
                        new_c.append(t_html)
                        new_cd.append(t_html)
                        buf = []
                    new_c.append(raw_s)
                    new_cd.append(baraha_to_devanagari(raw_s))
            if buf:
                t_html = build_krama_table(buf)
                new_c.append(t_html)
                new_cd.append(t_html)
            sec['content'] = new_c
            sec['content_deva'] = new_cd

    return chapters


def parse_siva_stuti_elements(elements: list[tuple[str, any]]) -> list[dict]:
    """Backward-compatible wrapper delegating to unified parse_baraha_elements."""
    intro_sections = {
        'purpose': '1.1 Purpose',
        'language and versions': '1.2 Language and Versions',
        'method of compilation': '1.3 Method of compilation',
        'acknowledgement': '1.4 Acknowledgement',
        'important notes': '1.5 Important Notes',
        'rudraikaadasini kumbha stapanam.': '1.6 RUDRAIKAADASINI KUMBHA STAPANAM.',
        'rudraikaadasini kumbha stapanam': '1.6 RUDRAIKAADASINI KUMBHA STAPANAM.',
        'some basics': '2.1 Some Basics',
        'forms of rudra japam': '2.2 Forms of Rudra Japam',
        'sadyo jaatham': '2.3 Sadyo Jaatham',
        'star (nakshatra) and rasi table:': '2.4 Star (Nakshatra) and Rasi Table:',
        'star (nakshatra) and rasi table': '2.4 Star (Nakshatra) and Rasi Table:',
        'days of the week:': '2.4.1 Days of the Week:',
        'days of the week': '2.4.1 Days of the Week:',
        'masam, ruthu, ayanam': '2.4.2 Masam, Ruthu, Ayanam'
    }
    return parse_baraha_elements(
        elements,
        chapter_regex=r'^([1-2]?\d)(?!\.\d)\.?\s*([a-zA-Z].*)$',
        intro_start='Introduction',
        intro_sections=intro_sections
    )


def parse_general_baraha_elements(elements: list[tuple[str, any]], chapter_regex: str = None) -> list[dict]:
    """Backward-compatible wrapper delegating to unified parse_baraha_elements."""
    return parse_baraha_elements(elements, chapter_regex=chapter_regex)


def parse_baraha_docx_to_ast(
    docx_path: str | Path,
    title: str = None,
    version: str = None,
    generated_at: str = None,
    chapter_regex: str = None,
    intro_start: str = None,
    intro_sections: dict = None
) -> tuple[dict, str]:
    """Parse Baraha DOCX document into standard VedaVMS hierarchical JSON AST."""
    elements = extract_docx_elements(docx_path)
    docx_name = Path(docx_path).name.lower()

    # Look up book config from config.json if available
    candidates = [
        Path(__file__).parent / "config.json",
        Path("src/config.json"),
        Path(__file__).parent.parent / "src" / "config.json",
    ]
    cfg_path = next((p for p in candidates if p.exists()), None)
    book_cfg = {}
    if cfg_path:
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                for b_info in cfg.get('books', {}).values():
                    if b_info.get('input_docx') and Path(b_info['input_docx']).name.lower() == docx_name:
                        book_cfg = b_info
                        break
        except Exception:
            book_cfg = {}

    ch_reg = chapter_regex or book_cfg.get('chapter_regex')
    i_start = intro_start or book_cfg.get('intro_start')
    i_sec = intro_sections or book_cfg.get('intro_sections')

    chapters = parse_baraha_elements(
        elements,
        chapter_regex=ch_reg,
        intro_start=i_start,
        intro_sections=i_sec
    )

    doc_title_sa = title or book_cfg.get('title_sanskrit') or book_cfg.get('title')
    if not doc_title_sa:
        first_p = elements[0][1] if elements and elements[0][0] == 'p' else ''
        if 'taittir' in first_p.lower() or 'upanishad' in first_p.lower():
            doc_title_sa = "तैत्तिरीयोपनिषत्"
        elif 'aranyaka' in first_p.lower():
            doc_title_sa = "तैत्तिरीयारण्यकम्"
        elif 'brahmana' in first_p.lower():
            doc_title_sa = "तैत्तिरीयब्राह्मणम्"
        elif 'siva' in docx_name or 'shiva' in docx_name:
            doc_title_sa = "शिव स्तुतिः"
        else:
            doc_title_sa = baraha_to_devanagari(first_p.strip()) or "Vedic Sanskrit Reader"

    sections = {}
    for ch in chapters:
        sec_key = f"section_{ch['num']}"
        sec_data = {
            'title': ch['title_deva'],
            'section_title': ch['title_deva'],
            'raw_title': ch['title_raw'],
            'ta_code': ch.get('ta_code', ''),
            'is_english': ch.get('is_english', False),
            'Count': '0',
            'subsections': {}
        }
        for sec in ch['sections']:
            sub_key = f"sub_sec_{sec['num'].replace('.', '_')}"
            title_text = sec['title_deva'].strip()
            if title_text.startswith(f"{sec['num']}.") or title_text.startswith(f"{sec['num']} ") or title_text == sec['num']:
                full_sub_title = title_text
            else:
                full_sub_title = f"{sec['num']} {title_text}".strip()
            sec_data['subsections'][sub_key] = {
                'title': sec['title_deva'],
                'sub_section_id': sec['num'],
                'header': {'header': full_sub_title},
                'ta_code': sec.get('ta_code', ''),
                'is_intro': sec.get('is_intro', False) or sec['num'] == str(ch['num']) or '.' not in sec['num'],
                'content_lines': sec.get('content_deva', sec.get('content', [])),
            }
        sec_data['Count'] = str(sum(
            len(sub.get('content_lines', []))
            for sub in sec_data['subsections'].values()
        ))
        sections[sec_key] = sec_data

    supersections = {
        'supersection_1': {
            'supersection_title': doc_title_sa,
            'sections': sections
        }
    }

    if not generated_at:
        generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ast_data = {
        'meta': {
            'title': doc_title_sa,
            'version': version or '1.0.0',
            'generated_at': generated_at,
            'source': str(docx_path)
        },
        'supersections': supersections
    }

    return ast_data, doc_title_sa


def ast_to_reader_chapters(ast_data: dict) -> list[dict]:
    """Convert AST dictionary into chapter list format expected by HTML reader generator."""
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
                    'is_intro': sub_data.get('is_intro', False) or sub_num == str(ch_num) or '.' not in sub_num,
                    'content_deva': content,
                    'content_raw': content
                })
            chapters.append({
                'num': ch_num,
                'title_deva': sec_title,
                'title_raw': raw_title,
                'ta_code': sec_data.get('ta_code', ''),
                'is_english': is_eng,
                'sections': sections
            })
    return chapters


def generate_reader_html_from_ast(ast_data: dict, output_path: str | Path, config: dict = None) -> Path:
    """Generate standalone interactive HTML reader from JSON AST data."""
    try:
        from .build_reader import generate_reader_html
    except ImportError:
        try:
            from build_reader import generate_reader_html
        except ImportError:
            _cur = Path(__file__).resolve().parent
            for _p in [_cur, _cur.parent / "src"]:
                if str(_p) not in sys.path:
                    sys.path.insert(0, str(_p))
            from build_reader import generate_reader_html

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not config:
        candidates = [
            Path(__file__).parent / "config.json",
            Path("src/config.json"),
            Path(__file__).parent.parent / "src" / "config.json",
        ]
        cfg_path = next((p for p in candidates if p.exists()), None)
        if cfg_path:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}

    doc_meta = ast_data.get('meta', {})
    doc_title = doc_meta.get('title', 'Vedic Sanskrit Reader')

    book_meta = None
    out_name = output_path.name
    for b_id, b_info in config.get('books', {}).items():
        if b_info.get('output_html') and Path(b_info['output_html']).name == out_name:
            book_meta = b_info
            break
        if b_info.get('title') == doc_title or b_info.get('title_sanskrit') == doc_title:
            book_meta = b_info
            break

    if not book_meta:
        book_meta = {
            'title': doc_title,
            'subtitle': "श्रीरुद्रम्, चमकम्, महान्यासः, पूजाविधानम्",
            'back_link': 'index.html',
            'back_label': '← Home'
        }

    chapters = ast_to_reader_chapters(ast_data)
    fonts = config.get('fonts', [])
    default_size = config.get('default_font_size_rem', 1.35)

    html_content = generate_reader_html(book_meta, chapters, fonts, default_size)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return output_path


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Baraha DOCX extraction, Vedic AST generator, and Reader for VedaVMS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate JSON AST
  python src/baraha_reader.py "data/baraha/Siva Stuti Baraha.docx" -o build/siva_stuti.json

  # Generate both JSON AST and Interactive HTML Reader
  python src/baraha_reader.py "data/baraha/Siva Stuti Baraha.docx" --html build/siva_stuti_sanskrit.html
        """
    )
    parser.add_argument('input_docx', help='Input Baraha .docx file')
    parser.add_argument('-o', '--output', default=None,
                        help='Output JSON AST file path')
    parser.add_argument('--html', default=None,
                        help='Output HTML reader file path')
    parser.add_argument('--title', default=None,
                        help='Custom Sanskrit/Devanagari title for the document')
    parser.add_argument('--config', default=None,
                        help='Path to config.json')

    args = parser.parse_args()

    input_path = Path(args.input_docx)
    if not input_path.exists():
        for cand in [Path("data/baraha") / input_path, Path(__file__).parent.parent / "data/baraha" / input_path]:
            if cand.exists():
                input_path = cand
                break
        else:
            print(f"[ERROR] Input file not found: {input_path}")
            sys.exit(1)

    print(f"\n[INFO] Reading Baraha DOCX: {input_path}")
    ast_data, doc_title = parse_baraha_docx_to_ast(input_path, title=args.title)

    supersec = ast_data['supersections']['supersection_1']
    sec_count = len(supersec['sections'])
    print(f"[INFO] Document Title: {doc_title}")
    print(f"[INFO] Extracted {sec_count} chapters:")
    for s_k, s_v in supersec['sections'].items():
        print(f"  {s_v['title']} ({len(s_v['subsections'])} sections)")

    # Save JSON AST if requested or by default if --html not sole target
    json_path = args.output
    if not json_path and not args.html:
        json_path = input_path.with_suffix('.json')

    if json_path:
        json_path = Path(json_path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(ast_data, f, ensure_ascii=False, indent=2)
        print(f"[INFO] JSON AST written to: {json_path} ({os.path.getsize(json_path):,} bytes)")

    # Generate HTML reader if requested
    if args.html:
        html_path = Path(args.html)
        print(f"[INFO] Generating standalone HTML reader: {html_path}")
        config_dict = None
        if args.config:
            with open(args.config, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
        out_html = generate_reader_html_from_ast(ast_data, html_path, config=config_dict)
        print(f"[INFO] HTML Reader successfully generated: {out_html} ({os.path.getsize(out_html):,} bytes)")


if __name__ == '__main__':
    main()

