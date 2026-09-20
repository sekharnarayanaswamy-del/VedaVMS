"""VedaVMS Post-Generation Audit Tool:
Compares the Table of Contents in reference PDF documents against the generated
HTML readers / ASTs, verifying structural integrity and flagging any differences.
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import Optional

try:
    import pypdf
except ImportError:
    pypdf = None


def extract_pdf_toc(pdf_path: str | Path) -> list[dict]:
    """Extract Table of Contents entries from a reference PDF document."""
    if pypdf is None:
        raise ImportError("pypdf is required to extract TOC from PDF files. Install via `pip install pypdf`.")

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    reader = pypdf.PdfReader(str(pdf_path))
    entries = []
    lines = []

    # Search for TOC pages within the first 15 pages
    for i in range(min(15, len(reader.pages))):
        t = reader.pages[i].extract_text()
        if any(k in t for k in ('Contents', 'Table of Contents', 'अनुक्रमणिका', 'सूची')):
            for pno in range(i, min(i + 15, len(reader.pages))):
                pt = reader.pages[pno].extract_text()
                if not re.search(r'(?:[\.\s]{3,})\s*\d+\s*$', pt, re.M):
                    if pno > i:
                        break
                for line in pt.split('\n'):
                    line = line.strip()
                    if line:
                        lines.append(line)
            break

    buffered_num = None
    buffered_title = ''
    for line in lines:
        if line.lower().startswith(('this replaces', 'this is now the current version')):
            continue
        m = re.match(r'^(\d+(?:\.\d+)*)\s+(.*?)(?:[\.\s]{2,})\s*(\d+)\s*$', line)
        if m:
            buffered_num = None
            buffered_title = ''
            raw_title = m.group(2).strip(' .')
            page_num = m.group(3)
            entries.append({
                'num': m.group(1),
                'title': raw_title,
                'page': int(page_num) if page_num and page_num.isdigit() else None
            })
            continue

        # Check if this starts an entry that wrapped across lines
        m_start = re.match(r'^(\d+(?:\.\d+)*)\s+(.*)$', line)
        if m_start:
            buffered_num = m_start.group(1)
            buffered_title = m_start.group(2).strip()
            continue

        # Check if this continues a buffered entry and ends with page number
        if buffered_num:
            m_end = re.match(r'^(.*?)(?:[\.\s]{2,})\s*(\d+)\s*$', line)
            if m_end:
                full_title = (buffered_title + ' ' + m_end.group(1)).strip(' .')
                page_num = m_end.group(2)
                entries.append({
                    'num': buffered_num,
                    'title': full_title,
                    'page': int(page_num) if page_num and page_num.isdigit() else None
                })
                buffered_num = None
                buffered_title = ''
            else:
                buffered_title += ' ' + line

    return entries


def extract_html_toc(html_path: str | Path) -> tuple[dict, list[dict]]:
    """Extract metadata and Table of Contents entries from generated HTML reader."""
    html_path = Path(html_path)
    if not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract metadata
    m_gen = re.search(r'<meta\s+name=["\']generated-at["\']\s+content=["\']([^"\']+)["\']', content, re.I)
    m_title = re.search(r'<title>([^<]+)</title>', content, re.I)
    stat = html_path.stat()

    meta = {
        'generated_at': m_gen.group(1) if m_gen else None,
        'title': m_title.group(1) if m_title else html_path.stem,
        'file_size': stat.st_size,
        'modified_at': stat.st_mtime
    }

    entries = []
    ch_matches = re.finditer(
        r'<section\s+class=["\']chapter-container["\']\s+id=["\']chapter-(\d+)["\']>\s*<h2\s+class=["\']chapter-heading["\']>(.*?)</h2>',
        content,
        re.S
    )
    for ch in ch_matches:
        ch_num = ch.group(1)
        raw_heading = ch.group(2).strip()
        clean_heading = re.sub(r'<span[^>]*>.*?</span>', '', raw_heading, flags=re.S).strip()
        entries.append({
            'num': ch_num,
            'title': clean_heading,
            'type': 'chapter'
        })

    sec_matches = re.finditer(
        r'<div\s+class=["\']anuvaka-block[^"\']*["\']\s+id=["\']sec-([^"\']+)["\']>(.*?)<div\s+class=["\']verse-text["\']',
        content,
        re.S
    )
    for sec in sec_matches:
        sec_id_raw = sec.group(1)
        sec_num = sec_id_raw.replace('-', '.')
        header_chunk = sec.group(2)
        title_m = re.search(r'<span\s+class=["\']anuvaka-num[^"\']*["\']>(.*?)</span>', header_chunk, re.S)
        sec_title = title_m.group(1).strip() if title_m else ''
        sec_title_clean = re.sub(r'<[^>]+>', '', sec_title).strip()
        if '.' in sec_num:
            entries.append({
                'num': sec_num,
                'title': sec_title_clean,
                'type': 'section'
            })

    return meta, entries


def audit_book(pdf_path: str | Path, html_path: str | Path, verbose: bool = False) -> dict:
    """Audit the generated HTML against the reference PDF TOC."""
    pdf_path = Path(pdf_path)
    html_path = Path(html_path)

    pdf_entries = extract_pdf_toc(pdf_path)
    html_meta, html_entries = extract_html_toc(html_path)

    pdf_chaps = [e for e in pdf_entries if '.' not in e['num']]
    pdf_secs = [e for e in pdf_entries if '.' in e['num']]

    html_chaps = [e for e in html_entries if '.' not in e['num']]
    html_secs = [e for e in html_entries if '.' in e['num']]

    # Handle single-chapter books where PDF TOC lists only 1.x subsections (e.g. Udaka Shanti ASCT)
    if not pdf_chaps and pdf_secs:
        implicit_ch_nums = sorted(list(set(e['num'].split('.')[0] for e in pdf_secs if e['num'].split('.')[0].isdigit())))
        if implicit_ch_nums == ['1']:
            pdf_chaps = [{'num': '1', 'title': '1. (Implicit Document Chapter)', 'type': 'chapter'}]

    pdf_ch_nums = [int(e['num']) for e in pdf_chaps if e['num'].isdigit()]
    html_ch_nums = [int(e['num']) for e in html_chaps if e['num'].isdigit()]

    missing_chapters = sorted(set(pdf_ch_nums) - set(html_ch_nums))
    extra_chapters = sorted(set(html_ch_nums) - set(pdf_ch_nums))

    pdf_sec_nums = set(e['num'] for e in pdf_secs)
    html_sec_nums = set(e['num'] for e in html_secs)

    missing_subsections = sorted(pdf_sec_nums - html_sec_nums)
    extra_subsections = sorted(html_sec_nums - pdf_sec_nums)

    differences = []
    notes = []
    if missing_chapters:
        differences.append(f"Missing chapters in HTML: {missing_chapters}")
    if extra_chapters:
        differences.append(f"Extra chapters in HTML: {extra_chapters}")
    if missing_subsections:
        differences.append(f"Missing subsections in HTML (present in PDF): {missing_subsections}")
        if '1.41' in missing_subsections:
            notes.append("In Udaka Shanti ASCT DOCX, section 1.13 is split into 1.13 and 1.13B, which causes subsequent numbering to offset by 1 (ending at 1.40 in HTML vs 1.41 in PDF).")

    if extra_subsections:
        if any(s.startswith('19.') for s in extra_subsections):
            notes.append("Shanti Japam Nakshatra Suktam includes 40 granular nakshatras (19.1–19.40) directly indexed in the HTML reader.")
        if any('T.B.3.11' in s for s in extra_subsections):
            notes.append("Taittiriya Upanishad Chapter 6 (Trinachiketam) includes 26 granular Taittiriya Brahmana mantras (T.B.3.11.x) directly indexed in the HTML reader.")
        elif any('T.B.' in s for s in extra_subsections):
            notes.append("Udaka Shanti includes 7 granular Taittiriya Brahmana mantras directly indexed in the HTML reader.")

    if missing_chapters or extra_chapters:
        status = "FAIL"
    elif missing_subsections:
        status = "WARNING"
    else:
        status = "PASS"

    return {
        'status': status,
        'pdf_path': str(pdf_path),
        'html_path': str(html_path),
        'generated_at': html_meta.get('generated_at'),
        'html_size_bytes': html_meta.get('file_size'),
        'pdf_chapter_count': len(pdf_chaps),
        'html_chapter_count': len(html_chaps),
        'pdf_subsection_count': len(pdf_secs),
        'html_subsection_count': len(html_secs),
        'missing_chapters': missing_chapters,
        'extra_chapters': extra_chapters,
        'missing_subsections': missing_subsections,
        'extra_subsections': extra_subsections,
        'differences': differences,
        'notes': notes
    }


import datetime


def format_audit_ascii(result: dict) -> str:
    """Format single book audit result as clean ASCII text."""
    status = result['status']
    status_icon = "✓ PASS" if status == "PASS" else ("⚠ WARNING" if status == "WARNING" else "✗ FAIL")

    out = []
    out.append("=" * 70)
    out.append(f"  VedaVMS POST-GENERATION TOC AUDIT REPORT: [{status_icon}]")
    out.append("=" * 70)
    out.append(f"  HTML Document    : {result['html_path']}")
    out.append(f"  Generated At     : {result.get('generated_at') or 'Unknown (missing meta)'}")
    out.append(f"  HTML File Size   : {result.get('html_size_bytes', 0):,} bytes")
    out.append(f"  Reference PDF    : {result['pdf_path']}")
    out.append("-" * 70)
    out.append(f"  PDF Chapters     : {result['pdf_chapter_count']}")
    out.append(f"  HTML Chapters    : {result['html_chapter_count']}")
    out.append(f"  PDF Subsections  : {result['pdf_subsection_count']}")
    out.append(f"  HTML Subsections : {result['html_subsection_count']}")
    out.append("-" * 70)

    if not result['differences'] and not result['extra_subsections']:
        out.append("  ✓ All chapters and subsections match the reference PDF exactly.")
    else:
        if result['missing_chapters']:
            out.append(f"  [MISSING CHAPTERS]   : {result['missing_chapters']}")
        if result['extra_chapters']:
            out.append(f"  [EXTRA CHAPTERS]     : {result['extra_chapters']}")
        if result['missing_subsections']:
            out.append(f"  [MISSING SUBSECTIONS]: {result['missing_subsections']}")
        if result['extra_subsections']:
            out.append(f"  [HTML SUBSECTIONS]   : {len(result['extra_subsections'])} additional granular subsections in HTML")
            if len(result['extra_subsections']) <= 10:
                out.append(f"                         ({', '.join(result['extra_subsections'])})")
            else:
                sample = ', '.join(result['extra_subsections'][:5])
                out.append(f"                         ({sample}, ... +{len(result['extra_subsections'])-5} more)")

    if result.get('notes'):
        out.append("-" * 70)
        for note in result['notes']:
            out.append(f"  ℹ NOTE: {note}")

    out.append("=" * 70 + "\n")
    return "\n".join(out)


def print_audit_report(result: dict) -> bool:
    """Print a clean, formatted ASCII audit report to console and return success boolean."""
    text = format_audit_ascii(result)
    print("\n" + text)
    return result['status'] != "FAIL"


def format_audit_markdown(results: list[dict]) -> str:
    """Format full multi-book audit results as GitHub Flavored Markdown."""
    now_str = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    lines = [
        "# VedaVMS Post-Generation TOC Audit Report",
        "",
        f"> **Generated at**: `{now_str}`",
        "",
        "## Summary",
        "",
        "| Document | Reference PDF | PDF Ch/Sec | HTML Ch/Sec | Status |",
        "| :--- | :--- | :---: | :---: | :---: |",
    ]
    for r in results:
        status_badge = "✅ PASS" if r['status'] == 'PASS' else ("⚠️ WARNING" if r['status'] == 'WARNING' else "❌ FAIL")
        html_name = Path(r['html_path']).name
        pdf_name = Path(r['pdf_path']).name
        ch_sec_pdf = f"{r['pdf_chapter_count']} / {r['pdf_subsection_count']}"
        ch_sec_html = f"{r['html_chapter_count']} / {r['html_subsection_count']}"
        lines.append(f"| [`{html_name}`]({html_name}) | `{pdf_name}` | {ch_sec_pdf} | {ch_sec_html} | {status_badge} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Book Details")
    lines.append("")

    for r in results:
        status_badge = "PASS" if r['status'] == 'PASS' else ("WARNING" if r['status'] == 'WARNING' else "FAIL")
        html_name = Path(r['html_path']).name
        pdf_name = Path(r['pdf_path']).name
        lines.append(f"### {html_name} `[{status_badge}]`")
        lines.append("")
        lines.append(f"- **HTML Document**: [`{r['html_path']}`]({html_name})")
        lines.append(f"- **Reference PDF**: `{r['pdf_path']}`")
        lines.append(f"- **Generated At**: `{r.get('generated_at') or 'Unknown'}`")
        lines.append(f"- **HTML File Size**: `{r.get('html_size_bytes', 0):,} bytes`")
        lines.append(f"- **Chapters**: PDF: `{r['pdf_chapter_count']}`, HTML: `{r['html_chapter_count']}`")
        lines.append(f"- **Subsections**: PDF: `{r['pdf_subsection_count']}`, HTML: `{r['html_subsection_count']}`")
        lines.append("")

        if not r['differences'] and not r['extra_subsections']:
            lines.append("✓ *All chapters and subsections match the reference PDF exactly.*")
            lines.append("")
        else:
            if r['missing_chapters']:
                lines.append(f"- **Missing Chapters**: `{r['missing_chapters']}`")
            if r['extra_chapters']:
                lines.append(f"- **Extra Chapters**: `{r['extra_chapters']}`")
            if r['missing_subsections']:
                lines.append(f"- **Missing Subsections**: `{r['missing_subsections']}`")
            if r['extra_subsections']:
                lines.append(f"- **Additional Granular HTML Subsections** ({len(r['extra_subsections'])}):")
                sample = ', '.join(f"`{s}`" for s in r['extra_subsections'][:15])
                if len(r['extra_subsections']) > 15:
                    sample += f", ... (+{len(r['extra_subsections'])-15} more)"
                lines.append(f"  {sample}")
            lines.append("")

        if r.get('notes'):
            for n in r['notes']:
                lines.append(f"> [!NOTE]\n> {n}\n")

        lines.append("")

    return "\n".join(lines)


def save_audit_reports(results: list[dict], out_dir: str | Path = 'build') -> tuple[Path, Path]:
    """Save audit report to build/audit_report.md and build/audit_report.txt."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / "audit_report.md"
    txt_path = out_dir / "audit_report.txt"

    md_content = format_audit_markdown(results)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    ascii_blocks = [format_audit_ascii(r) for r in results]
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(ascii_blocks))

    return md_path, txt_path



def main():
    parser = argparse.ArgumentParser(description="Audit generated HTML Vedic Reader TOC against reference PDF.")
    parser.add_argument("--book", type=str, default=None, help="Book identifier from config.json (e.g. shanti_japam)")
    parser.add_argument("--all", action="store_true", help="Audit all configured books with available PDFs")
    parser.add_argument("--pdf", type=str, default=None, help="Path to reference PDF")
    parser.add_argument("--html", type=str, default=None, help="Path to generated HTML reader")
    parser.add_argument("--config", type=str, default=None, help="Path to config.json")
    parser.add_argument("--verbose", action="store_true", help="Detailed itemized diff output")

    args = parser.parse_args()

    candidates = [
        Path(args.config) if args.config else None,
        Path("src/config.json"),
        Path(__file__).parent / "config.json",
        Path(__file__).parent.parent / "src" / "config.json"
    ]
    cfg_path = next((p for p in candidates if p and p.exists()), None)
    config = {}
    if cfg_path:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

    books_to_audit = []
    if args.pdf and args.html:
        books_to_audit.append(('custom', {'pdf_path': args.pdf, 'output_html': args.html}))
    elif args.all:
        for b_id, b_meta in config.get('books', {}).items():
            books_to_audit.append((b_id, b_meta))
    elif args.book:
        b_meta = config.get('books', {}).get(args.book)
        if not b_meta:
            print(f"[ERROR] Book '{args.book}' not found in configuration.", file=sys.stderr)
            sys.exit(1)
        books_to_audit.append((args.book, b_meta))
    else:
        b_meta = config.get('books', {}).get('shanti_japam')
        if b_meta:
            books_to_audit.append(('shanti_japam', b_meta))

    total_passed = 0
    total_audited = 0
    results = []

    for b_id, b_meta in books_to_audit:
        pdf_p = b_meta.get('pdf_path')
        if not pdf_p:
            title_simple = b_meta.get('title', '').split(',')[0].strip()
            for cand in [
                Path("data/pdf") / f"{title_simple} Sanskrit.pdf",
                Path("data/pdf") / f"{b_id.replace('_', ' ').title()} Sanskrit.pdf",
                Path("data/pdf") / f"{b_id.replace('_', ' ').capitalize()} Sanskrit.pdf"
            ]:
                if cand.exists():
                    pdf_p = str(cand)
                    break

        html_p = b_meta.get('output_html')
        if not pdf_p or not Path(pdf_p).exists():
            print(f"[SKIP] No reference PDF found for '{b_id}'")
            continue
        if not html_p or not Path(html_p).exists():
            print(f"[SKIP] HTML file '{html_p}' not found for '{b_id}'. Please generate it first.")
            continue

        total_audited += 1
        res = audit_book(pdf_p, html_p, verbose=args.verbose)
        passed = print_audit_report(res)
        results.append(res)
        if passed:
            total_passed += 1

    if results:
        md_p, txt_p = save_audit_reports(results, out_dir="build")
        print(f"[AUDIT] Audit reports saved to:")
        print(f"        - {md_p}")
        print(f"        - {txt_p}\n")

    if total_audited > 0 and total_passed < total_audited:
        sys.exit(1)


if __name__ == '__main__':
    main()
