import re
import os
import sys
import json
import zipfile
import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from src.transliterate import baraha_to_devanagari, is_english_text, clean_baraha_english
from src.build_reader import format_vedic_html, generate_reader_html

DOCX_NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def extract_tb_sections(docx_path="data/baraha/TB 3.7-3.12 Baraha.docx"):
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

    # Slice into 3.7, 3.8, 3.9
    tb_map = {'3.7': [], '3.8': [], '3.9': []}
    cur = None
    for p in paras:
        if re.match(r'^3\.7\b', p) and 'prapAThaka' in p:
            cur = '3.7'
        elif re.match(r'^3\.8\b', p) and 'prapAThaka' in p:
            cur = '3.8'
        elif re.match(r'^3\.9\b', p) and 'prapAThaka' in p:
            cur = '3.9'
        elif re.match(r'^3\.10\b', p) and ('prapAThaka' in p or 'praSna' in p):
            cur = '3.10'

        if cur in tb_map:
            tb_map[cur].append(p)

    return tb_map

def parse_tb_book_paras(raw_paras, book_prefix, main_title_deva, main_subtitle_deva):
    chapters = []
    
    # Chapter 1 container
    current_chapter = {
        'num': 1,
        'title_raw': main_title_deva,
        'title_deva': f"1. {main_title_deva}",
        'title_display_deva': f"1. {main_title_deva}",
        'title_display_raw': f"1. {main_title_deva}",
        'sections': []
    }
    chapters.append(current_chapter)

    current_section = None
    
    # Matches e.g. 3.7.1 anuvAkaM 1 - ... or 3.8.1 anuvAkaM 1 - ... but NOT 3.7.2.1 or T.B.3.7.1.1
    anuvaka_re = re.compile(rf'^{re.escape(book_prefix)}\.(\d+)(?!\.\d+)\s*(?:anuvAka[mM]\s*\d+\s*[-–:]?\s*)?(.*)', re.I)
    tb_num_re = re.compile(rf'^(?:T\.B\.)?{re.escape(book_prefix)}\.\d+\.\d+', re.I)

    for p in raw_paras:
        # Check if line is the top prapAthaka heading
        if re.match(rf'^{re.escape(book_prefix)}\s+taittirIya', p, re.I):
            continue
        
        # Check if line is a verse marker like 3.7.2.1 or T.B.3.7.1.1
        if tb_num_re.match(p):
            if current_section:
                current_section['content_raw'].append(p)
                current_section['content_deva'].append(p)
            continue

        # Check if line is an anuvaka heading e.g. 3.7.1 anuvAkaM 1 - darSapUrNa...
        an_m = anuvaka_re.match(p)
        if an_m and not re.search(r'[q#$|]', p):
            an_num = an_m.group(1)
            raw_title = an_m.group(2).strip()
            
            # Convert raw title to Devanagari
            if raw_title:
                deva_title = baraha_to_devanagari(raw_title)
                # Clean up any leading dashes
                deva_title = re.sub(r'^[-–:\s]+', '', deva_title).strip()
                display_title = f"{book_prefix}.{an_num} {deva_title}"
            else:
                display_title = f"{book_prefix}.{an_num} अनुवाकम् {an_num}"

            current_section = {
                'num': f"{book_prefix}.{an_num}",
                'title_raw': raw_title or f"anuvAkaM {an_num}",
                'title_deva': display_title,
                'ta_code': f"T.B. {book_prefix}.{an_num}",
                'content_raw': [],
                'content_deva': []
            }
            current_chapter['sections'].append(current_section)
            continue

        # Check for Korvai heading
        if 'prapATaka kOrvai' in p.lower() or 'prapaataka kOrvai' in p.lower():
            korvai_title = f"{book_prefix} प्रपाठक कोर्वै"
            current_section = {
                'num': f"{book_prefix}.K",
                'title_raw': p,
                'title_deva': korvai_title,
                'ta_code': '',
                'content_raw': [p],
                'content_deva': [baraha_to_devanagari(p)]
            }
            current_chapter['sections'].append(current_section)
            continue

        # Check for Samapta / conclusion
        if 'samAptaH' in p or 'samAptam' in p:
            if current_section:
                current_section['content_raw'].append(p)
                current_section['content_deva'].append(baraha_to_devanagari(p))
            continue

        # If no section opened yet, add as intro content in current chapter
        if current_section is None:
            if not current_chapter['sections']:
                current_section = {
                    'num': f"{book_prefix}.0",
                    'title_raw': 'Introduction',
                    'title_deva': f"{book_prefix}.0 उपोद्घातः",
                    'ta_code': '',
                    'content_raw': [p],
                    'content_deva': [baraha_to_devanagari(p)],
                    'is_intro': True
                }
                current_chapter['sections'].append(current_section)
            else:
                current_chapter['sections'][-1]['content_raw'].append(p)
                current_chapter['sections'][-1]['content_deva'].append(baraha_to_devanagari(p))
        else:
            current_section['content_raw'].append(p)
            current_section['content_deva'].append(baraha_to_devanagari(p))

    return chapters

def build_all_tb_readers():
    tb_map = extract_tb_sections()

    fonts = [
        {"label": "Adishila Vedic", "font": "'AdishilaVedic', 'Adishila San', 'Noto Serif Devanagari', serif", "weight": "500"},
        {"label": "Noto Serif", "font": "'Noto Serif Devanagari', 'Adishila San', 'Tiro Devanagari Sanskrit', serif", "weight": "500"},
        {"label": "Adishila San", "font": "'Adishila San', 'Noto Serif Devanagari', serif", "weight": "500"},
        {"label": "Tiro Sanskrit", "font": "'Tiro Devanagari Sanskrit', 'Adishila San', 'Noto Serif Devanagari', serif", "weight": "400"},
        {"label": "Noto Sans", "font": "'Noto Sans Devanagari', 'Adishila San', sans-serif", "weight": "500"}
    ]

    books_meta = [
        {
            'id': 'tb_3_7_achidram',
            'prefix': '3.7',
            'title': 'तैत्तिरीय ब्राह्मणे तृतीयाष्टके सप्तमः प्रपाठकः (अच्छिद्रं)',
            'title_sanskrit': 'अच्छिद्रं',
            'subtitle': 'कृष्ण यजुर्वेदीय तैत्तिरीय ब्राह्मणम् (TB 3.7)',
            'pdf_path': 'data/pdf/TB 3.7-3.12 Sanskrit.pdf',
            'filename': 'tb_3_7_achidram_sanskrit.html',
            'back_link': '../index.html',
            'back_label': '← Home'
        },
        {
            'id': 'tb_3_8_aswamedham_vaiswadevam',
            'prefix': '3.8',
            'title': 'तैत्तिरीय ब्राह्मणे तृतीयाष्टके अष्टमः प्रपाठकः (अश्वमेधं-वैश्वदेवम्)',
            'title_sanskrit': 'अश्वमेधं-वैश्वदेवम्',
            'subtitle': 'कृष्ण यजुर्वेदीय तैत्तिरीय ब्राह्मणम् (TB 3.8)',
            'pdf_path': 'data/pdf/TB 3.7-3.12 Sanskrit.pdf',
            'filename': 'tb_3_8_aswamedham_vaiswadevam_sanskrit.html',
            'back_link': '../index.html',
            'back_label': '← Home'
        },
        {
            'id': 'tb_3_9_aswamedham_havirdhanam',
            'prefix': '3.9',
            'title': 'तैत्तिरीय ब्राह्मणे तृतीयाष्टके नवमः प्रपाठकः (अश्वमेधं-हविर्धानम्)',
            'title_sanskrit': 'अश्वमेधं-हविर्धानम्',
            'subtitle': 'कृष्ण यजुर्वेदीय तैत्तिरीय ब्राह्मणम् (TB 3.9)',
            'pdf_path': 'data/pdf/TB 3.7-3.12 Sanskrit.pdf',
            'filename': 'tb_3_9_aswamedham_havirdhanam_sanskrit.html',
            'back_link': '../index.html',
            'back_label': '← Home'
        }
    ]

    for b in books_meta:
        raw_paras = tb_map[b['prefix']]
        chapters = parse_tb_book_paras(raw_paras, b['prefix'], b['title_sanskrit'], b['subtitle'])
        
        print(f"\n--- Generated {b['id']} ---")
        for ch in chapters:
            print(f"Chapter {ch['num']}: {len(ch['sections'])} sections (Anuvakams)")
            for sec in ch['sections'][:5]:
                print(f"  - {sec['num']}: {sec['title_deva']}")
            if len(ch['sections']) > 5:
                print(f"  ... and {len(ch['sections']) - 5} more sections")

        html_content = generate_reader_html(b, chapters, fonts, default_font_size=1.35)

        # Write to mockup/viewer and build/viewer
        for out_dir in ['mockup/viewer', 'build/viewer']:
            os.makedirs(out_dir, exist_ok=True)
            out_file = os.path.join(out_dir, b['filename'])
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"Saved: {out_file} ({os.path.getsize(out_file):,} bytes)")

if __name__ == '__main__':
    build_all_tb_readers()
