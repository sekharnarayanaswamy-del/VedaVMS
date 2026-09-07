#!/usr/bin/env python3
"""
Generate mockup/documents.html from the live vedavms.in document pages.

The live site is a hand-maintained static site whose URL scheme has been stable
for years, but whose version labels drift as new editions replace old ones at
the same filename. Rather than hand-editing the redesigned page to keep up, this
reads the six live docs_*.html pages and re-emits the Documents page using the
mockup as a design template.

    python3 generate_documents.py                 # fetch live pages, write build/documents.html
    python3 generate_documents.py --offline       # reuse cached pages
    python3 generate_documents.py --check         # also verify every emitted link resolves

The mockup is the template and is never written to. Output goes to build/.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import concurrent.futures
import csv
import datetime
import html
import http.client
import io
import itertools
import json
import os
import re
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

BASE = "https://vedavms.in"
ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(ROOT, "mockup", "documents.html")
CACHE_DIR = os.path.join(ROOT, ".cache")
OUT_DEFAULT = os.path.join(ROOT, "build", "documents.html")

USER_AGENT = "vedavms-generator/1.0 (+static site regeneration)"
TIMEOUT = 30
RETRIES = 4
RETRY_WAIT = 2.0
# The origin is an old IIS box that resets connections when hit hard.
CHECK_WORKERS = 6

# key -> (live page, human label used in log output, tab display title)
LANGUAGES = [
    ("sanskrit",   "docs_sanskrit.html",   "Sanskrit",            "संस्कृत Sanskrit"),
    ("tamil",      "docs_tamil.html",      "Tamil",               "தமிழ் Tamil"),
    ("malayalam",  "docs_malayalam.html",  "Malayalam",           "മലയാളം Malayalam"),
    ("kannada",    "docs_kannada.html",    "Kannada",             "ಕನ್ನಡ Kannada"),
    ("telugu",     "docs_telugu.html",     "Telugu",              "తెలుగు Telugu"),
    ("english",    "docs_english.html",    "English",             "English"),
    ("tsj",        "docs_tsj.html",        "TS Jatai",            "TS Jatai (Pilot)"),
    ("tsg",        "docs_tsg.html",        "TS Ghanam",           "TS Ghanam (Pilot)"),
    ("siksha",     "docs_SikShA.html",     "SikShA & Lessons",    "SikShA & Lessons"),
    ("kanva",      "docs_Kanva.html",      "Kanva Samhita",       "Kanva Samhita"),
    ("inprogress", "docs_inprogress.html", "Pilot & In-Progress", "In Progress"),
    ("latin",      "docs_latin.html",      "Latin (IAST)",        "Latin (IAST)"),
]

# Icons follow the mockup's existing convention for these section names.
SECTION_ICONS = [
    (r"vedic books",            "\U0001F4DA"),  # books
    (r"krama\s*p[aA]tam",       "\U0001F503"),  # cycle
    (r"pada\s*p[aA]tam",        "\U0001F517"),  # link
    (r"br[aA]hma[nN]am",        "\U0001F4DC"),  # scroll
    (r"aranyakam",              "\U0001F332"),  # tree
    (r"samhit[aA]",             "\U0001F4D6"),  # open book
]
DEFAULT_ICON = "\U0001F4C4"  # page

# A section larger than this is split into per-kandam subsections when the
# document URLs carry a kandam number (TS4-Padam, TSK4-Kramam).
SPLIT_THRESHOLD = 30
KANDAM_RE = re.compile(r"/docs/TSK?(\d)-(?:Padam|Kramam)/", re.I)

MONTHS = {
    "jan": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr", "may": "May",
    "jun": "Jun", "jul": "Jul", "aug": "Aug", "sep": "Sep", "sept": "Sep",
    "oct": "Oct", "nov": "Nov", "dec": "Dec",
}
DATE_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*"
    r"(\d{1,2})\s*,?\s*(\d{4})\b",
    re.I,
)
VERSION_RE = re.compile(r"\b(?:version|ver|v)\s*\.?\s*(\d+(?:\.\d+)?)\b", re.I)
CORRECTION_RE = re.compile(r"correction", re.I)
PDF_LINK_RE = re.compile(
    r"<a\b[^>]*?href=\"([^\"]*?\.pdf)\"[^>]*>(.*?)</a>", re.I | re.S
)
# Innermost rows only: the site nests tables inside table cells, so a plain
# non-greedy <tr>...</tr> matches an outer row but stops at the inner row's
# closing tag, swallowing content that then never gets parsed.
ROW_RE = re.compile(r"<tr\b(?:(?!<tr\b)[\s\S])*?</tr>", re.I)
TAG_RE = re.compile(r"<[^>]+>")


# --------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------

@dataclass
class Doc:
    title: str
    url: str
    version: str = ""
    date: str = ""
    corrections: str = ""


@dataclass
class Section:
    title: str
    docs: list[Doc] = field(default_factory=list)
    subsections: list[Section] = field(default_factory=list)


# --------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------

def open_url(url: str, method: str = "GET"):
    """Open a URL, retrying briefly: the origin server drops connections."""
    last: Exception | None = None
    for attempt in range(RETRIES):
        req = urllib.request.Request(
            url, method=method, headers={"User-Agent": USER_AGENT}
        )
        try:
            return urllib.request.urlopen(req, timeout=TIMEOUT)
        except urllib.error.HTTPError:
            raise
        except Exception as exc:  # timeout, reset, DNS
            last = exc
            if attempt + 1 < RETRIES:
                time.sleep(RETRY_WAIT * (attempt + 1))
    raise last  # type: ignore[misc]


def fetch(url: str) -> str:
    with open_url(url) as resp:
        return resp.read().decode("utf-8", "replace")


def load_page(page: str, offline: bool) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    cached = os.path.join(CACHE_DIR, page)
    if offline:
        if not os.path.exists(cached):
            sys.exit(f"error: --offline but {cached} is missing; run once without it")
        with open(cached, encoding="utf-8") as fh:
            return fh.read()
    body = fetch(f"{BASE}/{page}")
    with open(cached, "w", encoding="utf-8") as fh:
        fh.write(body)
    return body


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

def text_of(fragment: str) -> str:
    """Strip tags and collapse whitespace, including non-breaking spaces."""
    txt = html.unescape(TAG_RE.sub(" ", fragment))
    txt = txt.replace(" ", " ")
    txt = unicodedata.normalize("NFC", txt)
    return re.sub(r"\s+", " ", txt).strip()


def absolutise(href: str) -> str:
    """Resolve a page-relative href and collapse the site's stray '//' typos."""
    href = html.unescape(href.strip())
    url = urllib.parse.urljoin(BASE + "/", href)
    parts = urllib.parse.urlsplit(url)
    path = re.sub(r"/{2,}", "/", parts.path)
    return urllib.parse.urlunsplit(parts._replace(path=path))


def split_meta(raw: str) -> tuple[str, str, str]:
    """Pull a version and a date out of a link label, returning the clean title."""
    title = text_of(raw)

    version = ""
    vm = VERSION_RE.search(title)
    if vm:
        version = "V" + vm.group(1)

    date = ""
    dm = DATE_RE.search(title)
    if dm:
        date = f"{MONTHS[dm.group(1).lower()]} {int(dm.group(2))}, {dm.group(3)}"

    # Remove the matched spans, longest-last so offsets stay valid.
    spans = [m.span() for m in (vm, dm) if m]
    for start, end in sorted(spans, reverse=True):
        title = title[:start] + title[end:]

    # Tidy the punctuation the removals leave behind.
    title = re.sub(r"\(\s*[,\-]?\s*\)", "", title)
    title = re.sub(r"\(\s*$", "", title)
    title = re.sub(r"^\s*\)", "", title)
    title = re.sub(r"\s+", " ", title)
    title = title.strip(" -–—,;:.")
    return title.strip(), version, date


def section_labels(page_html: str) -> list[tuple[int, str]]:
    """Locate section headings, in document order.

    The site marks sections two ways: an <h3>, or bare text sitting between a
    closing and an opening <table>. Some <h3> tags wrap a document link instead
    of a heading, so those are excluded.
    """
    found: list[tuple[int, str]] = []

    for m in re.finditer(r"<h([23])\b[^>]*>(.*?)</h\1>", page_html, re.I | re.S):
        inner = m.group(2)
        if PDF_LINK_RE.search(inner):
            continue
        label = text_of(inner)
        if label:
            found.append((m.start(), label))

    for m in re.finditer(
        r"</table>((?:\s|<br\s*/?>)*)([^<>\n][^<>]{3,90}?)((?:\s|<br\s*/?>)*)<table",
        page_html,
        re.I,
    ):
        label = text_of(m.group(2))
        if label:
            found.append((m.start(2), label))

    found.sort(key=lambda pair: pair[0])
    return found


def parse_page(page_html: str, lang_label: str) -> list[Section]:
    """Turn one live language page into ordered sections of documents."""
    labels = section_labels(page_html)

    # The <h2> is the language name, not a section; drop it and anything before
    # the first real section heading falls into a catch-all.
    labels = [(pos, text) for pos, text in labels
              if text.strip().lower() != lang_label.lower()]

    sections: list[Section] = []
    by_pos: list[tuple[int, Section]] = []
    for pos, text in labels:
        section = Section(title=text)
        sections.append(section)
        by_pos.append((pos, section))

    fallback = Section(title="Documents")

    def section_for(offset: int) -> Section:
        current = fallback
        for pos, section in by_pos:
            if pos <= offset:
                current = section
            else:
                break
        return current

    # A document may be linked from more than one row. Keep the first card for
    # it and let later rows enrich that same object, so a corrections link is
    # never lost just because its partner was a repeat.
    emitted: dict[str, Doc] = {}

    def add(url: str, label: str, target: Section) -> Doc:
        doc = emitted.get(url)
        if doc is None:
            title, version, date = split_meta(label)
            doc = Doc(
                title=title or urllib.parse.unquote(os.path.basename(url)),
                url=url, version=version, date=date,
            )
            emitted[url] = doc
            target.docs.append(doc)
        return doc

    def consume(fragment: str, offset: int) -> None:
        """Read one row (or one stray link) into the section covering `offset`."""
        links = PDF_LINK_RE.findall(fragment)
        if not links:
            return

        # The site often splits a single title across several anchors that all
        # point at the same PDF. Merge those back into one label.
        merged: list[tuple[str, str]] = []
        for href, label in links:
            url = absolutise(href)
            if merged and merged[-1][0] == url:
                merged[-1] = (url, merged[-1][1] + " " + label)
            else:
                merged.append((url, label))

        target = section_for(offset)
        pending: Doc | None = None

        for url, label in merged:
            is_correction = bool(
                CORRECTION_RE.search(text_of(label)) or CORRECTION_RE.search(url)
            )
            if is_correction and pending is not None and url not in emitted:
                if not pending.corrections:
                    pending.corrections = url
                    continue
                if pending.corrections == url:
                    continue
                # The row already contributed a corrections link, and a later
                # row may reference this document again. Give the extra one its
                # own card rather than overwriting and losing a link.
            pending = add(url, label, target)

    rows = list(ROW_RE.finditer(page_html))
    covered = [(m.start(), m.end()) for m in rows]

    events: list[tuple[int, str]] = [(m.start(), m.group(0)) for m in rows]

    # Links sitting in a cell beside a nested table belong to no innermost row.
    # Emit them individually rather than losing them.
    for link in PDF_LINK_RE.finditer(page_html):
        if not any(start <= link.start() < end for start, end in covered):
            events.append((link.start(), link.group(0)))

    for offset, fragment in sorted(events, key=lambda pair: pair[0]):
        consume(fragment, offset)

    if fallback.docs:
        sections.insert(0, fallback)

    return [s for s in sections if s.docs]


# --------------------------------------------------------------------------
# restructuring
# --------------------------------------------------------------------------

def subdivide(sections: list[Section]) -> list[Section]:
    """Break the very large Pada/Krama sections into per-kandam subsections.

    These run to 250+ documents on a single page, which is the exact problem the
    redesign set out to fix; an accordion holding 250 cards is still a wall. The
    kandam number is already in the URL, so the split costs nothing.
    """
    out: list[Section] = []
    for section in sections:
        if len(section.docs) <= SPLIT_THRESHOLD:
            out.append(section)
            continue

        groups: dict[str, list[Doc]] = {}
        for doc in section.docs:
            m = KANDAM_RE.search(doc.url)
            groups.setdefault(m.group(1) if m else "", []).append(doc)

        if len(groups) < 2:
            out.append(section)
            continue

        for key in sorted(groups, key=lambda k: (k == "", k)):
            docs = groups[key]
            title = f"{section.title} — Kandam {key}" if key else section.title
            out.append(Section(title=title, docs=docs))
    return out


KANDAM_NUM_RE = re.compile(r"kandam\s*(\d+)", re.I)
TS_NUM_RE = re.compile(r"TS\s*(\d+)\.", re.I)
URL_KANDAM_RE = re.compile(r"/TSK?(\d+)-(?:Padam|Kramam)/", re.I)


def extract_kandam_num(sec_title: str, doc: Doc | None = None) -> int | None:
    m = KANDAM_NUM_RE.search(sec_title)
    if m:
        return int(m.group(1))
    if doc:
        m = URL_KANDAM_RE.search(doc.url)
        if m:
            return int(m.group(1))
        m = TS_NUM_RE.search(doc.title)
        if m:
            return int(m.group(1))
    return None


def nest_hierarchical_sections(sections: list[Section]) -> list[Section]:
    """Nest Pada and Krama Kandam sections under top-level accordion containers."""
    out: list[Section] = []
    pada_sections: list[Section] = []
    krama_sections: list[Section] = []

    def is_pada(sec_title: str) -> bool:
        return bool(
            re.search(r"pada\s*p[aA]tam", sec_title, re.I)
            and re.search(r"samhit", sec_title, re.I)
        )

    def is_krama(sec_title: str) -> bool:
        return bool(
            re.search(r"krama\s*p[aA]tam", sec_title, re.I)
            and re.search(r"samhit", sec_title, re.I)
        )

    def build_container(container_title: str, matched_sections: list[Section]) -> Section:
        kandam_map: dict[int, list[Doc]] = {}
        for s in matched_sections:
            for d in s.docs:
                k = extract_kandam_num(s.title, d) or 1
                kandam_map.setdefault(k, []).append(d)
        subs = []
        for k in sorted(kandam_map.keys()):
            subs.append(Section(title=f"Kandam {k}", docs=kandam_map[k]))
        return Section(title=container_title, subsections=subs)

    for s in sections:
        if s.subsections:
            continue
        if is_pada(s.title):
            pada_sections.append(s)
        elif is_krama(s.title):
            krama_sections.append(s)

    pada_inserted = False
    krama_inserted = False

    for s in sections:
        if s.subsections:
            out.append(s)
            continue
        if is_pada(s.title):
            if not pada_inserted:
                out.append(build_container("TaittirIya SamhitA pada pAtam", pada_sections))
                pada_inserted = True
        elif is_krama(s.title):
            if not krama_inserted:
                out.append(build_container("TaittirIya SamhitA krama pAtam", krama_sections))
                krama_inserted = True
        else:
            out.append(s)

    return out


def icon_for(title: str) -> str:
    for pattern, icon in SECTION_ICONS:
        if re.search(pattern, title, re.I):
            return icon
    return DEFAULT_ICON


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


NUM_HIERARCHY_RE = re.compile(r"^(\d+)([A-Za-z]?)\s*[\)\.\-]\s*(.*)$")
LETTER_SUB_RE = re.compile(r"^([A-Za-z])\s*[\)\.\-]\s*(.*)$")

def apply_dynamic_numbering(sections: list[Section]) -> None:
    """Dynamically renumber hierarchical documents (e.g. 1), 1A), 2), 2A), 2B)) within each section.
    
    When a document is marked Hidden (like 1) Shanti Japam), the next document dynamically becomes 1),
    and sub-documents under it become 1A), 1B), preserving the hierarchy contiguously.
    """
    for section in sections:
        if section.subsections:
            apply_dynamic_numbering(section.subsections)
        numbered_count = sum(1 for doc in section.docs if NUM_HIERARCHY_RE.match(doc.title.strip()))
        if numbered_count < 2:
            continue

        major_map: dict[str, int] = {}
        next_major = 1
        last_assigned_major = 1

        for doc in section.docs:
            t = doc.title.strip()
            m = NUM_HIERARCHY_RE.match(t)
            if m:
                orig_major = m.group(1)
                sub_suffix = m.group(2).upper()
                clean_title = m.group(3).strip()

                if orig_major not in major_map:
                    major_map[orig_major] = next_major
                    next_major += 1

                assigned_major = major_map[orig_major]
                last_assigned_major = assigned_major
                prefix = f"{assigned_major}{sub_suffix})" if sub_suffix else f"{assigned_major})"
                doc.title = f"{prefix} {clean_title}"
            else:
                m_sub = LETTER_SUB_RE.match(t)
                if m_sub and major_map:
                    sub_suffix = m_sub.group(1).upper()
                    clean_title = m_sub.group(2).strip()
                    doc.title = f"{last_assigned_major}{sub_suffix}) {clean_title}"
                else:
                    # Default: treat unnumbered title as a new main book!
                    assigned_major = next_major
                    next_major += 1
                    last_assigned_major = assigned_major
                    clean_t = re.sub(r"\.pdf$", "", t, flags=re.I).strip()
                    doc.title = f"{assigned_major}) {clean_t}"


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def esc(text: str) -> str:
    return html.escape(text, quote=True)


def render_card(doc: Doc, indent: str) -> str:
    meta: list[str] = []
    if doc.version:
        meta.append(f'<span class="version-badge">{esc(doc.version)}</span>')
    if doc.date:
        meta.append(f"<span>{esc(doc.date)}</span>")
    meta_html = (
        f'\n{indent}        <div class="doc-meta">{"".join(meta)}</div>' if meta else ""
    )

    actions = [
        f'<a href="{esc(doc.url)}" target="_blank" rel="noopener" '
        f'class="dl-btn primary">\U0001F4C4 Download</a>'
    ]
    if doc.corrections:
        actions.append(
            f'<a href="{esc(doc.corrections)}" target="_blank" rel="noopener" '
            f'class="dl-btn secondary">Corrections</a>'
        )
    actions_html = "".join(f"\n{indent}        {a}" for a in actions)

    return (
        f'{indent}<div class="doc-card">\n'
        f'{indent}    <div class="doc-info">\n'
        f'{indent}        <div class="doc-title">{esc(doc.title)}</div>'
        f"{meta_html}\n"
        f"{indent}    </div>\n"
        f'{indent}    <div class="doc-actions">{actions_html}\n'
        f"{indent}    </div>\n"
        f"{indent}</div>"
    )


def render_section(section: Section, lang: str, index: int) -> str:
    count = len(section.docs) + sum(len(sub.docs) for sub in section.subsections)
    noun = "doc" if count == 1 else "docs"
    open_class = " open" if index == 0 else ""
    cat_id = f"cat-{lang}-{slugify(section.title)}"

    if section.subsections:
        sub_blocks = []
        for sub in section.subsections:
            sub_count = len(sub.docs)
            sub_noun = "doc" if sub_count == 1 else "docs"
            sub_id = f"subcat-{lang}-{slugify(section.title)}-{slugify(sub.title)}"
            sub_cards = "\n".join(render_card(doc, " " * 32) for doc in sub.docs)
            sub_html = (
                f'                    <div class="sub-category" id="{sub_id}">\n'
                f'                        <div class="sub-category-header" '
                f"onclick=\"this.parentElement.classList.toggle('open')\">\n"
                f'                            <h4>\U0001F4D6 {esc(sub.title)} '
                f'<span class="sub-category-count">{sub_count} {sub_noun}</span></h4>\n'
                f'                            <span class="sub-category-toggle">▼</span>\n'
                f'                        </div>\n'
                f'                        <div class="sub-category-content">\n'
                f'                            <div class="doc-grid">\n'
                f"{sub_cards}\n"
                f'                            </div>\n'
                f'                        </div>\n'
                f'                    </div>'
            )
            sub_blocks.append(sub_html)

        subs_rendered = "\n".join(sub_blocks)
        direct_cards = ""
        if section.docs:
            cards = "\n".join(render_card(doc, " " * 24) for doc in section.docs)
            direct_cards = (
                f'                <div class="doc-grid" style="margin-bottom:0.75rem;">\n'
                f"{cards}\n"
                f"                </div>\n"
            )

        return (
            f'        <div class="category{open_class}" id="{cat_id}">\n'
            f'            <div class="category-header" '
            f"onclick=\"this.parentElement.classList.toggle('open')\">\n"
            f"                <h3>{icon_for(section.title)} {esc(section.title)} "
            f'<span class="category-count">{count} {noun}</span></h3>\n'
            f'                <span class="category-toggle">▼</span>\n'
            f"            </div>\n"
            f'            <div class="category-content">\n'
            f"{direct_cards}"
            f'                <div class="sub-category-list">\n'
            f"{subs_rendered}\n"
            f"                </div>\n"
            f"            </div>\n"
            f"        </div>"
        )

    cards = "\n".join(render_card(doc, " " * 24) for doc in section.docs)
    return (
        f'        <div class="category{open_class}" id="{cat_id}">\n'
        f'            <div class="category-header" '
        f"onclick=\"this.parentElement.classList.toggle('open')\">\n"
        f"                <h3>{icon_for(section.title)} {esc(section.title)} "
        f'<span class="category-count">{count} {noun}</span></h3>\n'
        f'                <span class="category-toggle">▼</span>\n'
        f"            </div>\n"
        f'            <div class="category-content">\n'
        f'                <div class="doc-grid">\n'
        f"{cards}\n"
        f"                </div>\n"
        f"            </div>\n"
        f"        </div>"
    )


def render_language(lang: str, notes: str, sections: list[Section], first: bool) -> str:
    attrs = 'class="language-content active"' if first \
        else 'class="language-content" style="display:none;"'
    blocks = "\n\n".join(
        render_section(section, lang, i) for i, section in enumerate(sections)
    )
    parts = [f'        <!-- {lang.upper()} CONTENT (generated) -->',
             f'        <div id="content-{lang}" {attrs}>']
    if notes:
        parts.append(notes)
    parts.append(blocks)
    parts.append(f"        </div><!-- End {lang.title()} Content -->")
    return "\n".join(parts)


# --------------------------------------------------------------------------
# template splicing
# --------------------------------------------------------------------------

def extract_notes(template: str, lang: str) -> str:
    """Lift the hand-written 'Important Notes' block for a language.

    That copy is editorial, not derived from the live site, so it is carried
    through verbatim rather than regenerated.
    """
    start = template.find(f'id="content-{lang}"')
    if start == -1:
        return ""
    notes_at = template.find('<div class="important-notes">', start)
    if notes_at == -1:
        return ""
    end_marker = f"<!-- End {lang.title()} Content -->"
    limit = template.find(end_marker, start)
    if limit != -1 and notes_at > limit:
        return ""

    depth, i = 0, notes_at
    while i < len(template):
        m = re.compile(r"<div\b|</div>", re.I).search(template, i)
        if not m:
            break
        depth += 1 if m.group(0).lower().startswith("<div") else -1
        i = m.end()
        if depth == 0:
            return "        " + template[notes_at:i].strip()
    return ""


def splice(template: str, rendered: dict[str, str]) -> str:
    """Replace tab buttons and each language block in the template with its generated version."""
    out = template

    # 1. Dynamically rebuild the language-tabs bar
    tab_spans = []
    for i, (lang, _page, _label, tab_title) in enumerate(LANGUAGES):
        active_cls = " active" if i == 0 else ""
        tab_spans.append(
            f'        <span class="language-tab{active_cls}" onclick="showLanguage(\'{lang}\', event)" data-lang="{lang}">{tab_title}</span>'
        )
    tabs_html = '<div class="language-tabs">\n' + "\n".join(tab_spans) + '\n    </div>'

    out = re.sub(
        r'<div class="language-tabs">[\s\S]*?</div>',
        tabs_html,
        out,
        count=1,
    )

    # 2. Splice in each rendered language/section block
    all_blocks = []
    for lang, _page, _label, _title in LANGUAGES:
        all_blocks.append(rendered[lang])

    # Replace everything from the first content div to the end of the last content div
    content_pattern = re.compile(
        r'(?:<!--\s*[A-Z_0-9\s-]+CONTENT\s*\(generated\)\s*-->\s*)?'
        r'<div id="content-[a-z0-9_-]+"[\s\S]*?<!-- End [A-Za-z0-9_\s-]+ Content -->',
        re.I
    )
    
    # Find start of main content area
    main_match = re.search(r'<main class="main-content">', out)
    if main_match:
        main_start = main_match.end()
        main_end_match = re.search(r'</main>', out[main_start:])
        if main_end_match:
            main_end = main_start + main_end_match.start()
            new_main_content = "\n" + "\n\n".join(all_blocks) + "\n    "
            out = out[:main_start] + new_main_content + out[main_end:]
            return out

    # Fallback per-block splicing
    for lang, _page, _label, _title in LANGUAGES:
        open_at = out.find(f'<div id="content-{lang}"')
        if open_at != -1:
            line_start = out.rfind("\n", 0, open_at) + 1
            end_marker = f"<!-- End {lang.title()} Content -->"
            end_at = out.find(end_marker, open_at)
            if end_at != -1:
                end_at += len(end_marker)
                prev = out.rfind("<!--", 0, line_start)
                if prev != -1 and re.match(rf"<!--\s*{lang.upper()} CONTENT", out[prev:prev + 40], re.I):
                    line_start = out.rfind("\n", 0, prev) + 1
                out = out[:line_start] + rendered[lang] + out[end_at:]
    return out


def harden_tab_switching(page: str) -> str:
    """Pass the click event explicitly instead of reading the global `event`.

    The mockup's showLanguage() reads `event.target` from a function the inline
    handler calls, which resolves to `window.event`. That works in current
    Chrome and Firefox, but it is a deprecated non-standard global: it is
    undefined under a module script or any call that is not inside an event
    dispatch, and highlights whatever was clicked rather than the tab itself.
    Passing the event through, with a data-lang lookup as a fallback, removes
    the dependency without changing behaviour.
    """
    page = page.replace(
        "function showLanguage(lang) {",
        "function showLanguage(lang, evt) {",
    )
    page = page.replace(
        "event.target.classList.add('active');",
        "const tab = (evt && evt.currentTarget) ||\n"
        "                document.querySelector"
        "(`.language-tab[data-lang=\"${lang}\"]`);\n"
        "            if (tab) tab.classList.add('active');",
    )
    # Pass the event through from each tab, and tag it for the fallback lookup.
    def rewrite_tab(m: re.Match) -> str:
        lang = m.group(1)
        return (f"onclick=\"showLanguage('{lang}', event)\" data-lang=\"{lang}\"")

    page = re.sub(r"onclick=\"showLanguage\('([a-z]+)'\)\"", rewrite_tab, page)
    return page


# --------------------------------------------------------------------------
# link checking
# --------------------------------------------------------------------------

def check_links(urls: list[str], progress: bool = True) -> list[tuple[str, str]]:
    """HEAD every URL, reusing one keep-alive connection per worker.

    A fresh TLS handshake per link makes the origin server start resetting
    connections long before the run finishes, so each thread holds a single
    connection and only reconnects when one goes bad.
    """
    host = urllib.parse.urlsplit(BASE).netloc
    local = threading.local()
    done = itertools.count(1)

    def connection() -> http.client.HTTPSConnection:
        conn = getattr(local, "conn", None)
        if conn is None:
            conn = http.client.HTTPSConnection(host, timeout=TIMEOUT)
            local.conn = conn
        return conn

    def drop() -> None:
        conn = getattr(local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            local.conn = None

    def probe(url: str) -> tuple[str, str]:
        path = urllib.parse.urlsplit(url).path
        problem = "unknown"
        for attempt in range(RETRIES):
            try:
                conn = connection()
                conn.request("HEAD", path, headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "*/*",
                    "Connection": "keep-alive",
                })
                resp = conn.getresponse()
                resp.read()
                ctype = resp.headers.get("Content-Type", "")
                if resp.status == 200 and "pdf" in ctype.lower():
                    problem = ""
                else:
                    problem = f"{resp.status} {ctype or '?'}"
                break
            except Exception as exc:  # reset, timeout, bad state
                drop()
                problem = type(exc).__name__
                if attempt + 1 < RETRIES:
                    time.sleep(RETRY_WAIT * (attempt + 1))
        if progress:
            n = next(done)
            if n % 50 == 0 or n == len(urls):
                print(f"    {n}/{len(urls)}", flush=True)
        return url, problem

    bad: list[tuple[str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=CHECK_WORKERS) as pool:
        for url, problem in pool.map(probe, urls):
            if problem:
                bad.append((url, problem))
        drop()
    return bad


# --------------------------------------------------------------------------
# CSV / JSON export & import
# --------------------------------------------------------------------------

CSV_HEADERS = [
    "Language",
    "Section",
    "Title",
    "PDF_URL",
    "Version",
    "Date",
    "Corrections_URL",
    "Status",
    "Notes",
]


def export_to_csv(filepath: str, lang_sections: dict[str, list[Section]]) -> None:
    """Export parsed document hierarchy to a UTF-8 with BOM CSV for Google Sheets / Excel."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    lang_map = {key: label for key, _page, label, _tab in LANGUAGES}
    with open(filepath, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_HEADERS)
        for lang_key, sections in lang_sections.items():
            lang_name = lang_map.get(lang_key, lang_key)
            for section in sections:
                if section.subsections:
                    for sub in section.subsections:
                        for doc in sub.docs:
                            writer.writerow([
                                lang_name,
                                f"{section.title} — {sub.title}",
                                doc.title,
                                doc.url,
                                doc.version,
                                doc.date,
                                doc.corrections,
                                "Active",
                                "",
                            ])
                else:
                    for doc in section.docs:
                        writer.writerow([
                            lang_name,
                            section.title,
                            doc.title,
                            doc.url,
                            doc.version,
                            doc.date,
                            doc.corrections,
                            "Active",
                            "",
                        ])


def export_to_json(filepath: str, lang_sections: dict[str, list[Section]]) -> None:
    """Export parsed document hierarchy to structured JSON."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    lang_map = {key: {"label": label, "tab": tab} for key, _page, label, tab in LANGUAGES}
    data = {}
    for lang_key, sections in lang_sections.items():
        lang_sections_json = []
        for s in sections:
            sec_dict = {
                "title": s.title,
                "docs": [
                    {
                        "title": d.title,
                        "url": d.url,
                        "version": d.version,
                        "date": d.date,
                        "corrections": d.corrections,
                    }
                    for d in s.docs
                ],
            }
            if s.subsections:
                sec_dict["subsections"] = [
                    {
                        "title": sub.title,
                        "docs": [
                            {
                                "title": d.title,
                                "url": d.url,
                                "version": d.version,
                                "date": d.date,
                                "corrections": d.corrections,
                            }
                            for d in sub.docs
                        ],
                    }
                    for sub in s.subsections
                ]
            lang_sections_json.append(sec_dict)

        data[lang_key] = {
            "label": lang_map.get(lang_key, {}).get("label", lang_key),
            "tab": lang_map.get(lang_key, {}).get("tab", lang_key),
            "sections": lang_sections_json,
        }
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def load_from_csv(source: str) -> dict[str, list[Section]]:
    """Load documents from a local CSV file path or a Google Sheets / HTTP CSV export URL."""
    if source.startswith("http://") or source.startswith("https://"):
        content = fetch(source)
    else:
        with open(source, "r", encoding="utf-8-sig") as fh:
            content = fh.read()

    lookup: dict[str, str] = {}
    for key, _page, label, tab in LANGUAGES:
        lookup[key.lower()] = key
        lookup[label.lower()] = key
        lookup[tab.lower()] = key

    sections_by_lang: dict[str, dict[str, Section]] = {k: {} for k, _, _, _ in LANGUAGES}

    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        raw_lang = (
            row.get("Language")
            or row.get("language")
            or row.get("Supersection")
            or row.get("supersection")
            or row.get("SuperSection")
            or row.get("Super Section")
            or row.get("Category")
            or (list(row.values())[0] if row else "")
            or ""
        ).strip()
        lang_key = lookup.get(raw_lang.lower())
        if not lang_key:
            for candidate_key, _, candidate_label, candidate_tab in LANGUAGES:
                if (
                    candidate_key.lower() in raw_lang.lower()
                    or candidate_label.lower() in raw_lang.lower()
                    or candidate_tab.lower() in raw_lang.lower()
                ):
                    lang_key = candidate_key
                    break
        if not lang_key:
            continue

        status = (row.get("Status") or row.get("status") or "Active").strip()
        if status.lower() in ("hidden", "inactive", "draft", "deleted"):
            continue

        sec_title = (row.get("Section") or row.get("section") or "Documents").strip()
        title = (row.get("Title") or row.get("title") or "").strip()
        url = (
            row.get("PDF_URL")
            or row.get("pdf_url")
            or row.get("URL")
            or row.get("url")
            or ""
        ).strip()
        if not url and not title:
            continue
        if not url:
            url = "#"
        if not title:
            title = os.path.basename(url)

        version = (row.get("Version") or row.get("version") or "").strip()
        date = (row.get("Date") or row.get("date") or "").strip()
        corrections = (
            row.get("Corrections_URL") or row.get("corrections_url") or ""
        ).strip()

        doc = Doc(
            title=title,
            url=url,
            version=version,
            date=date,
            corrections=corrections,
        )

        if sec_title not in sections_by_lang[lang_key]:
            sections_by_lang[lang_key][sec_title] = Section(title=sec_title)
        sections_by_lang[lang_key][sec_title].docs.append(doc)

    out: dict[str, list[Section]] = {}
    for key, _, _, _ in LANGUAGES:
        out[key] = list(sections_by_lang[key].values())
    return out


# --------------------------------------------------------------------------
# Dynamic Recent Updates (Home Page)
# --------------------------------------------------------------------------

def parse_doc_date(date_str: str) -> datetime.datetime | None:
    if not date_str or not date_str.strip():
        return None
    d = date_str.strip()
    for fmt in ("%b %d, %Y", "%b %d %Y", "%B %d, %Y", "%d-%b-%Y", "%Y-%m-%d", "%b %Y", "%B %Y"):
        try:
            return datetime.datetime.strptime(d, fmt)
        except Exception:
            pass
    return None


LANG_ICONS = {
    "sanskrit": "🕉️",
    "tamil": "🪔",
    "malayalam": "🌴",
    "kannada": "📜",
    "telugu": "📜",
    "english": "📖",
    "tsj": "📑",
    "tsg": "📑",
    "siksha": "📖",
    "kanva": "📜",
    "inprogress": "⚙️",
    "latin": "Ā",
}


def get_recent_updates_grouped(lang_sections: dict[str, list[Section]], max_days: int = 90) -> list[dict]:
    """Group active document updates by Month -> Language collection."""
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(days=max_days)

    lang_map = {key: tab for key, _page, _label, tab in LANGUAGES}
    by_month: dict[tuple[str, str], dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    seen: set[tuple[str, str]] = set()

    for lang_key, sections in lang_sections.items():
        tab_title = lang_map.get(lang_key, lang_key)
        for sec in sections:
            all_sec_docs = list(sec.docs)
            for sub in sec.subsections:
                all_sec_docs.extend(sub.docs)
            for doc in all_sec_docs:
                if not doc.url or doc.url == "#":
                    continue
                dt = parse_doc_date(doc.date)
                if not dt:
                    continue
                if not (cutoff <= dt <= now + datetime.timedelta(days=2)):
                    continue
                key = (doc.title, doc.url)
                if key in seen:
                    continue
                seen.add(key)

                month_key = dt.strftime("%B %Y")
                sort_key = dt.strftime("%Y-%m")
                is_new = (now - dt).days <= 30 and dt <= now + datetime.timedelta(days=2)

                by_month[(sort_key, month_key)][lang_key].append({
                    "dt": dt,
                    "date_str": doc.date,
                    "title": doc.title,
                    "section": sec.title,
                    "version": doc.version,
                    "url": doc.url,
                    "is_new": is_new,
                    "lang_key": lang_key,
                    "lang_title": tab_title,
                })

    # Fallback if no updates exist in window
    if not by_month:
        all_candidates: list[dict] = []
        for lang_key, sections in lang_sections.items():
            tab_title = lang_map.get(lang_key, lang_key)
            for sec in sections:
                all_sec_docs = list(sec.docs)
                for sub in sec.subsections:
                    all_sec_docs.extend(sub.docs)
                for doc in all_sec_docs:
                    if not doc.url or doc.url == "#":
                        continue
                    dt = parse_doc_date(doc.date)
                    if not dt:
                        continue
                    key = (doc.title, doc.url)
                    if key in seen:
                        continue
                    seen.add(key)
                    all_candidates.append({
                        "dt": dt,
                        "date_str": doc.date,
                        "title": doc.title,
                        "section": sec.title,
                        "version": doc.version,
                        "url": doc.url,
                        "is_new": False,
                        "lang_key": lang_key,
                        "lang_title": tab_title,
                    })
        all_candidates.sort(key=lambda x: x["dt"], reverse=True)
        for cand in all_candidates[:10]:
            dt = cand["dt"]
            month_key = dt.strftime("%B %Y")
            sort_key = dt.strftime("%Y-%m")
            by_month[(sort_key, month_key)][cand["lang_key"]].append(cand)

    months_out = []
    for (sort_key, month_name), langs_dict in sorted(by_month.items(), reverse=True):
        total_in_month = sum(len(docs) for docs in langs_dict.values())
        lang_list = []
        for l_key, docs in langs_dict.items():
            docs.sort(key=lambda x: x["dt"], reverse=True)
            lang_list.append({
                "lang_key": l_key,
                "lang_title": docs[0]["lang_title"] if docs else l_key,
                "icon": LANG_ICONS.get(l_key, "📄"),
                "docs": docs,
            })
        months_out.append({
            "sort_key": sort_key,
            "month_name": month_name,
            "total_count": total_in_month,
            "languages": lang_list,
        })

    return months_out


def render_recent_updates_html(months_data: list[dict]) -> str:
    if not months_data:
        return '                <p style="text-align:center; color:#666; padding:1.5rem 0;">No updates in the last 3 months.</p>'

    month_blocks = []
    for m_idx, month in enumerate(months_data):
        m_name = month["month_name"]
        m_count = month["total_count"]
        m_noun = "update" if m_count == 1 else "updates"
        # First (latest) month is open by default
        open_cls = " open" if m_idx == 0 else ""
        m_id = f"updates-month-{slugify(m_name)}"

        sub_blocks = []
        for l_idx, lang_group in enumerate(month["languages"]):
            l_key = lang_group["lang_key"]
            l_title = lang_group["lang_title"]
            l_icon = lang_group["icon"]
            l_docs = lang_group["docs"]
            l_count = len(l_docs)
            l_noun = "update" if l_count == 1 else "updates"
            # In the first month, keep language sub-accordions open
            sub_open_cls = " open" if m_idx == 0 else ""
            sub_id = f"updates-{slugify(m_name)}-{slugify(l_key)}"

            items = []
            for u in l_docs:
                dt: datetime.datetime = u["dt"]
                month_day = dt.strftime("%b %d")
                year = dt.strftime("%Y")
                ver_html = f" {html.escape(u['version'])}" if u.get("version") else ""
                new_badge = ' <span class="new-badge">NEW</span>' if u.get("is_new") else ""

                card_html = (
                    f'                                    <a href="{html.escape(u["url"])}" target="_blank" class="update-item">\n'
                    f'                                        <div class="update-date">{month_day}<br>{year}</div>\n'
                    f'                                        <div class="update-info">\n'
                    f'                                            <h4>{html.escape(u["title"])}{ver_html}{new_badge}</h4>\n'
                    f'                                            <span>{html.escape(u["section"])}</span>\n'
                    f'                                        </div>\n'
                    f'                                    </a>'
                )
                items.append(card_html)

            cards_html = "\n".join(items)
            sub_html = (
                f'                        <div class="sub-category{sub_open_cls}" id="{sub_id}">\n'
                f'                            <div class="sub-category-header" onclick="this.parentElement.classList.toggle(\'open\')">\n'
                f'                                <h4>{l_icon} {html.escape(l_title)} <span class="sub-category-count">{l_count} {l_noun}</span></h4>\n'
                f'                                <span class="sub-category-toggle">▼</span>\n'
                f'                            </div>\n'
                f'                            <div class="sub-category-content">\n'
                f'                                <div class="updates-grid">\n'
                f"{cards_html}\n"
                f'                                </div>\n'
                f'                            </div>\n'
                f'                        </div>'
            )
            sub_blocks.append(sub_html)

        subs_rendered = "\n".join(sub_blocks)
        month_html = (
            f'                <div class="category{open_cls}" id="{m_id}">\n'
            f'                    <div class="category-header" onclick="this.parentElement.classList.toggle(\'open\')">\n'
            f'                        <h3>📅 {html.escape(m_name)} <span class="category-count">{m_count} {m_noun}</span></h3>\n'
            f'                        <span class="category-toggle">▼</span>\n'
            f'                    </div>\n'
            f'                    <div class="category-content">\n'
            f'                        <div class="sub-category-list">\n'
            f"{subs_rendered}\n"
            f'                        </div>\n'
            f'                    </div>\n'
            f'                </div>'
        )
        month_blocks.append(month_html)

    return "\n".join(month_blocks)


def generate_index_html(src_path: str, dst_path: str, lang_sections: dict[str, list[Section]]) -> int:
    with open(src_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    months_data = get_recent_updates_grouped(lang_sections, max_days=90)
    total_updates = sum(m["total_count"] for m in months_data)
    updates_html = render_recent_updates_html(months_data)

    # Replace <div class="updates-list">...</div>
    pattern = re.compile(r'(<div class="updates-list">)(.*?)(</div>\s*</div>\s*</section>)', re.DOTALL)
    if pattern.search(content):
        content = pattern.sub(rf'\1\n{updates_html}\n            \3', content)

    # Update subtitle with total count
    sub_pattern = re.compile(r'(<p class="section-subtitle">)[^<]*(</p>)')
    if sub_pattern.search(content):
        content = sub_pattern.sub(rf'\g<1>Latest document releases and corrections ({total_updates} updates in last 3 months)\g<2>', content)

    # Also update language card document counts dynamically
    for lang, sections in lang_sections.items():
        doc_count = sum(len(s.docs) + sum(len(sub.docs) for sub in s.subsections) for s in sections)
        card_pattern = re.compile(
            rf'(<a\s+href="documents\.html#{re.escape(lang)}"[^>]*>.*?<div class="count">)[^<]*(</div>)',
            re.DOTALL
        )
        content = card_pattern.sub(rf'\g<1>{doc_count} documents\g<2>', content)

    with open(dst_path, "w", encoding="utf-8") as fh:
        fh.write(content)

    return total_updates


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true",
                    help="use cached pages in .cache/ instead of fetching")
    ap.add_argument("--check", action="store_true",
                    help="verify every emitted PDF link returns 200 application/pdf")
    ap.add_argument("--source-csv", default="",
                    help="path or Google Sheets URL to load documents from CSV instead of scraping")
    ap.add_argument("--export-csv", default="",
                    help="path to export current extracted documents to CSV (e.g. for Google Sheets)")
    ap.add_argument("--export-json", default="",
                    help="path to export current extracted documents to JSON")
    ap.add_argument("--out", default=OUT_DEFAULT,
                    help=f"output path (default: {os.path.relpath(OUT_DEFAULT, ROOT)})")
    ap.add_argument("--template", default=TEMPLATE,
                    help="mockup page to use as the design template")
    args = ap.parse_args()

    with open(args.template, encoding="utf-8") as fh:
        template = fh.read()

    rendered: dict[str, str] = {}
    all_urls: list[str] = []
    lang_sections: dict[str, list[Section]] = {}
    total = 0

    if args.source_csv:
        print(f"  loading documents from CSV: {args.source_csv}")
        lang_sections = load_from_csv(args.source_csv)
        for i, (lang, _page, label, _tab_title) in enumerate(LANGUAGES):
            sections = lang_sections.get(lang, [])
            sections = nest_hierarchical_sections(sections)
            apply_dynamic_numbering(sections)
            lang_sections[lang] = sections
            notes = extract_notes(template, lang)
            rendered[lang] = render_language(lang, notes, sections, first=(i == 0))

            count = sum(len(s.docs) + sum(len(sub.docs) for sub in s.subsections) for s in sections)
            total += count
            for section in sections:
                all_docs = list(section.docs)
                for sub in section.subsections:
                    all_docs.extend(sub.docs)
                for doc in all_docs:
                    all_urls.append(doc.url)
                    if doc.corrections:
                        all_urls.append(doc.corrections)
            print(f"  {label:<10} {count:>4} documents in {len(sections):>2} sections")
    else:
        for i, (lang, page, label, _tab_title) in enumerate(LANGUAGES):
            source = load_page(page, args.offline)
            sections = subdivide(parse_page(source, label))
            sections = nest_hierarchical_sections(sections)
            apply_dynamic_numbering(sections)
            lang_sections[lang] = sections
            notes = extract_notes(template, lang)
            rendered[lang] = render_language(lang, notes, sections, first=(i == 0))

            count = sum(len(s.docs) + sum(len(sub.docs) for sub in s.subsections) for s in sections)
            total += count
            for section in sections:
                all_docs = list(section.docs)
                for sub in section.subsections:
                    all_docs.extend(sub.docs)
                for doc in all_docs:
                    all_urls.append(doc.url)
                    if doc.corrections:
                        all_urls.append(doc.corrections)
            print(f"  {label:<10} {count:>4} documents in {len(sections):>2} sections")

    if args.export_csv:
        export_to_csv(args.export_csv, lang_sections)
        print(f"  exported {total} documents to CSV: {args.export_csv}")

    if args.export_json:
        export_to_json(args.export_json, lang_sections)
        print(f"  exported {total} documents to JSON: {args.export_json}")

    page = harden_tab_switching(splice(template, rendered))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(page)

    # Generate dynamic index.html with Recent Updates (< 3 months old) and copy other companion pages
    build_dir = os.path.dirname(os.path.abspath(args.out))
    mockup_dir = os.path.join(ROOT, "mockup")
    copied_pages = []
    if os.path.exists(mockup_dir):
        for fname in os.listdir(mockup_dir):
            if fname.endswith(".html") and fname != "documents.html":
                src = os.path.join(mockup_dir, fname)
                dst = os.path.join(build_dir, fname)
                if fname == "index.html":
                    num_updates = generate_index_html(src, dst, lang_sections)
                    copied_pages.append(f"index.html ({num_updates} recent updates < 3 mo)")
                elif os.path.abspath(src) != os.path.abspath(dst):
                    import shutil
                    shutil.copy2(src, dst)
                    copied_pages.append(fname)

    unique = sorted(set(all_urls))
    print(f"\n  {total} documents, {len(unique)} unique PDF links")
    print(f"  wrote {os.path.relpath(args.out, ROOT)}")
    if copied_pages:
        print(f"  copied companion pages to build: {', '.join(copied_pages)}")

    if args.check:
        print(f"\n  checking {len(unique)} links ...")
        bad = check_links(unique)
        if bad:
            print(f"  {len(bad)} link(s) failed:")
            for url, problem in sorted(bad):
                print(f"    {problem:<12} {urllib.parse.unquote(url)}")
            return 1
        print("  all links return 200 application/pdf")

    return 0


if __name__ == "__main__":
    sys.exit(main())

