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

# Try importing from local transliterate module
try:
    from .transliterate import baraha_to_devanagari
except ImportError:
    try:
        from transliterate import baraha_to_devanagari
    except ImportError:
        _cur = Path(__file__).resolve().parent
        for _p in [_cur, _cur.parent / "src"]:
            if str(_p) not in sys.path:
                sys.path.insert(0, str(_p))
        try:
            from transliterate import baraha_to_devanagari
        except ImportError:
            # Standalone fallback definition if transliterate.py not present
            CONSONANTS = {
                'k': 'क्', 'kh': 'ख्', 'K': 'ख्', 'g': 'ग्', 'gh': 'घ्', 'G': 'घ्', '~g': 'ङ्', '~G': 'ङ्',
                'c': 'च्', 'ch': 'च्', 'Ch': 'छ्', 'C': 'छ्', 'j': 'ज्', 'jh': 'झ्', 'J': 'झ्', '~j': 'ञ्', '~J': 'ञ्',
                'T': 'ट्', 'Th': 'ठ्', 'TH': 'ठ्', 'D': 'ड्', 'Dh': 'ढ्', 'DH': 'ढ्', 'N': 'ण्',
                't': 'त्', 'th': 'थ्', 'd': 'द्', 'dh': 'ध्', 'n': 'न्',
                'p': 'प्', 'ph': 'फ्', 'P': 'फ्', 'b': 'ब्', 'bh': 'भ्', 'B': 'भ्', 'm': 'म्',
                'y': 'य्', 'r': 'र्', 'l': 'ल्', 'v': 'व्', 'w': 'व्',
                'S': 'श्', 'sh': 'श्', 'Sh': 'ष्', 'shh': 'ष्', 's': 'स्', 'h': 'ह्', 'L': 'ळ्',
                'x': 'क्ष्', 'kSh': 'क्ष्', 'j~j': 'ज्ञ्', 'GY': 'ज्ञ्',
            }

            VOWEL_SIGNS = {
                'a': '', 'A': 'ा', 'aa': 'ा', 'i': 'ि', 'I': 'ी', 'ee': 'ी',
                'u': 'ु', 'U': 'ू', 'oo': 'ू', 'Ru': 'ृ', 'ru': 'ृ', 'RU': 'ॄ',
                'e': 'े', 'E': 'े', 'ai': 'ै', 'o': 'ो', 'O': 'ो', 'au': 'ौ',
            }

            INDEPENDENT_VOWELS = {
                'a': 'अ', 'A': 'आ', 'aa': 'आ', 'i': 'इ', 'I': 'ई', 'ee': 'ई',
                'u': 'उ', 'U': 'ऊ', 'oo': 'ऊ', 'Ru': 'ऋ', 'ru': 'ऋ', 'RU': 'ॠ',
                'e': 'ए', 'E': 'ए', 'ai': 'ऐ', 'o': 'ओ', 'O': 'ओ', 'au': 'औ',
            }

            CONSONANT_KEYS = sorted(CONSONANTS.keys(), key=len, reverse=True)
            VOWEL_KEYS = sorted(VOWEL_SIGNS.keys(), key=len, reverse=True)

            def baraha_to_devanagari(text: str) -> str:
                if not text:
                    return ""
                placeholders = []
                def repl_eng(m):
                    placeholders.append(m.group(0))
                    return f'\uE000{len(placeholders)-1}\uE001'

                if re.search(r'\b(Korvai|Padam|Prapaataka|Series|Dasinis|Special|First and Last|Notes for Users)\b', text, re.I):
                    return text

                text = re.sub(r'\([A-Za-z]+\d+[a-z]?\)', repl_eng, text)
                text = re.sub(r'\b[A-Za-z]\d+\b', repl_eng, text)
                text = re.sub(r'\b[A-Z]\.[A-Z0-9\.]+\b', repl_eng, text)

                text = re.sub(r'\s+([q#$HM]+)', r'\1', text)
                text = text.replace('~g', 'ङ्').replace('~G', 'ङ्').replace('~j', 'ञ्').replace('~J', 'ञ्')
                text = re.sub(r'\(gm~?\)', '\uA8F3', text, flags=re.I)
                text = re.sub(r'\(gg\)', '\u1CFA', text, flags=re.I)
                text = text.replace('~M', '\u00A0\u0901')
                text = text.replace('&', 'ऽ').replace('||', '॥').replace('|', '।')
                text = re.sub(r'\^+', '\u200C', text)

                text = re.sub(r'([q#$]+)H', r'H\1', text)
                text = re.sub(r'([q#$]+)M', r'M\1', text)

                out = []
                i = 0
                n = len(text)
                while i < n:
                    if text[i] == '\uE000':
                        end_p = text.find('\uE001', i)
                        if end_p != -1:
                            idx = int(text[i + 1:end_p])
                            out.append(placeholders[idx])
                            i = end_p + 1
                            continue

                    if text[i] == 'q':
                        out.append('॒')
                        i += 1
                        continue
                    elif text[i] == '#':
                        out.append('॑')
                        i += 1
                        continue
                    elif text[i] == '$':
                        out.append('᳚')
                        i += 1
                        continue
                    elif text[i] == 'H':
                        out.append('ः')
                        i += 1
                        continue
                    elif text[i] == 'M':
                        out.append('ं')
                        i += 1
                        continue
                    elif text[i] == '\u200C':
                        out.append('\u200C')
                        i += 1
                        continue
                    elif text[i] in ' \t\n\r।,॥():-0123456789.[]{}~/\\+*\uA8F3\uA8F2\uA8F4\u1CFA\u00A0\u0901':
                        out.append(text[i])
                        i += 1
                        continue

                    matched_c = None
                    for c in CONSONANT_KEYS:
                        if text.startswith(c, i):
                            matched_c = c
                            break

                    if matched_c:
                        i += len(matched_c)
                        matched_v = None
                        for v in VOWEL_KEYS:
                            if text.startswith(v, i):
                                matched_v = v
                                break

                        if matched_v:
                            i += len(matched_v)
                            cons_char = CONSONANTS[matched_c][:-1]
                            v_sign = VOWEL_SIGNS[matched_v]
                            out.append(cons_char + v_sign)
                        else:
                            out.append(CONSONANTS[matched_c])
                        continue

                    matched_v = None
                    for v in VOWEL_KEYS:
                        if text.startswith(v, i):
                            matched_v = v
                            break

                    if matched_v:
                        i += len(matched_v)
                        out.append(INDEPENDENT_VOWELS[matched_v])
                        continue

                    out.append(text[i])
                    i += 1

                res = ''.join(out)
                res = re.sub(r'\u094D+', '्', res)
                res = re.sub(r'([\u0951\u0952\u1CDA])(ः)', r'\2\1', res)
                res = re.sub(r'([\u0951\u0952\u1CDA])(ं)', r'\2\1', res)
                res = re.sub(r'\s+ँ', '\u00A0ँ', res)
                res = re.sub(r'([ \t\n।,॥\(\)\[\]\{\}\-])([\u0951\u0952\u1CDA]+)', r'\1', res)
                return res


DOCX_NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def extract_docx_paragraphs(docx_path: str | Path) -> list[str]:
    """Extract raw paragraphs from a Word (.docx) document using standard library zipfile."""
    docx_path = Path(docx_path)
    if not docx_path.exists():
        raise FileNotFoundError(f"Input DOCX file not found: {docx_path}")

    with zipfile.ZipFile(docx_path, 'r') as z:
        doc_xml = z.read('word/document.xml')

    root = ET.fromstring(doc_xml)
    paras = []
    for p in root.findall('.//w:p', DOCX_NS):
        text = ''.join([n.text for n in p.findall('.//w:t', DOCX_NS) if n.text]).strip()
        if text:
            paras.append(text)

    return paras


def parse_baraha_docx_to_ast(
    docx_path: str | Path,
    title: str = None,
    version: str = None,
    generated_at: str = None,
    chapter_regex: str = None
) -> tuple[dict, str]:
    """
    Parses a Baraha-encoded Word DOCX document into a structured AST.
    
    Returns:
        (ast_data, doc_title_sa)
    """
    raw_paras = extract_docx_paragraphs(docx_path)
    
    # Default chapter regex covers standard Upanishad / Aranyakam / Brahmana numbering
    ch_pattern = re.compile(
        chapter_regex or r'^([1-6])(?!\.)\s*(.*(?:vall[iI]|nArAyaN|aruNa|triNAcikE|kANDa|ashtaka|adhyAya|prapathaka).*)$',
        re.I
    )

    chapters = []
    current_chapter = None
    current_section = None

    for p in raw_paras:
        ch_m = ch_pattern.match(p)
        if ch_m:
            ch_num = int(ch_m.group(1))
            ch_raw_title = ch_m.group(2).strip()
            ch_deva = baraha_to_devanagari(ch_raw_title)
            current_chapter = {
                'num': ch_num,
                'title_raw': ch_raw_title,
                'title_deva': f"{ch_num}. {ch_deva}",
                'sections': []
            }
            chapters.append(current_chapter)
            current_section = None
            continue

        if current_chapter is None:
            continue

        sec_m = re.match(r'^(\d+\.\d+(?:\.\d+)?)\s*(.*)', p)
        tb_m = re.match(r'^(T\.B\.\d+\.\d+\.\d+\.\d+)', p)

        if sec_m:
            sec_num = sec_m.group(1)
            sec_name = sec_m.group(2).strip()
            sec_deva = baraha_to_devanagari(sec_name) if sec_name else ''
            current_section = {
                'num': sec_num,
                'title_deva': sec_deva,
                'ta_code': '',
                'content': []
            }
            current_chapter['sections'].append(current_section)
            continue
        elif current_chapter['num'] == 6 and tb_m:
            sec_num = tb_m.group(1)
            current_section = {
                'num': sec_num,
                'title_deva': '',
                'ta_code': sec_num,
                'content': []
            }
            current_chapter['sections'].append(current_section)
            continue

        # Check for inline TA codes like (TA 2.1.1)
        ta_match = re.search(r'\((?:TA|T\.A\.)\s*(\d+\.\d+\.\d+)\)', p)
        if current_section is not None:
            if ta_match and not current_section['ta_code']:
                current_section['ta_code'] = ta_match.group(1)

            # Skip pure chapter/anuvaka labels that match section heading
            clean_p = p.strip()
            if clean_p and not re.match(r'^\d+\.\d+\s*$', clean_p):
                current_section['content'].append(clean_p)

    # Resolve document title
    if title:
        doc_title_sa = title
    else:
        # Check first paragraph for document title
        first_p = raw_paras[0] if raw_paras else ''
        if 'taittir' in first_p.lower() or 'upanishad' in first_p.lower():
            doc_title_sa = "तैत्तिरीयोपनिषत्"
        elif 'aranyaka' in first_p.lower():
            doc_title_sa = "तैत्तिरीयारण्यकम्"
        elif 'brahmana' in first_p.lower():
            doc_title_sa = "तैत्तिरीयब्राह्मणम्"
        else:
            doc_title_sa = baraha_to_devanagari(first_p.strip()) or "तैत्तिरीयोपनिषत्"

    sections = {}
    for ch in chapters:
        sec_key = f"section_{ch['num']}"
        sec_data = {
            'title': ch['title_deva'],
            'raw_title': ch['title_raw'],
            'Count': '0',
            'subsections': {}
        }
        for sec in ch['sections']:
            sub_key = f"sub_sec_{sec['num'].replace('.', '_')}"
            full_sub_title = f"{sec['num']} {sec['title_deva']}".strip()
            sec_data['subsections'][sub_key] = {
                'title': sec['title_deva'],
                'sub_section_id': sec['num'],
                'header': {'header': full_sub_title},
                'ta_code': sec.get('ta_code', ''),
                'content_lines': sec['content'],
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


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert Baraha DOCX to JSON AST for VedaVMS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/baraha_reader.py tu_baraha.docx
  python src/baraha_reader.py tu_baraha.docx -o tu_baraha.json
        """
    )
    parser.add_argument('input_docx', help='Input Baraha .docx file')
    parser.add_argument('-o', '--output', default=None,
                        help='Output JSON file path (default: same name as input with .json extension)')
    parser.add_argument('--title', default=None,
                        help='Custom Sanskrit/Devanagari title for the document')

    args = parser.parse_args()

    input_path = Path(args.input_docx)
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_suffix('.json')

    ast_data, doc_title = parse_baraha_docx_to_ast(
        input_path, title=args.title
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ast_data, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Converted: {input_path} -> {output_path}")
    print(f"[INFO] Title: {doc_title}")
    print(f"[INFO] Sections: {len(ast_data['supersections']['supersection_1']['sections'])}")
