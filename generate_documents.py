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
import concurrent.futures
import html
import http.client
import itertools
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


def icon_for(title: str) -> str:
    for pattern, icon in SECTION_ICONS:
        if re.search(pattern, title, re.I):
            return icon
    return DEFAULT_ICON


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


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
    count = len(section.docs)
    noun = "doc" if count == 1 else "docs"
    open_class = " open" if index == 0 else ""
    cat_id = f"cat-{lang}-{slugify(section.title)}"
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
# main
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true",
                    help="use cached pages in .cache/ instead of fetching")
    ap.add_argument("--check", action="store_true",
                    help="verify every emitted PDF link returns 200 application/pdf")
    ap.add_argument("--out", default=OUT_DEFAULT,
                    help=f"output path (default: {os.path.relpath(OUT_DEFAULT, ROOT)})")
    ap.add_argument("--template", default=TEMPLATE,
                    help="mockup page to use as the design template")
    args = ap.parse_args()

    with open(args.template, encoding="utf-8") as fh:
        template = fh.read()

    rendered: dict[str, str] = {}
    all_urls: list[str] = []
    total = 0

    for i, (lang, page, label, _tab_title) in enumerate(LANGUAGES):
        source = load_page(page, args.offline)
        sections = subdivide(parse_page(source, label))
        notes = extract_notes(template, lang)
        rendered[lang] = render_language(lang, notes, sections, first=(i == 0))

        count = sum(len(s.docs) for s in sections)
        total += count
        for section in sections:
            for doc in section.docs:
                all_urls.append(doc.url)
                if doc.corrections:
                    all_urls.append(doc.corrections)
        print(f"  {label:<10} {count:>4} documents in {len(sections):>2} sections")

    page = harden_tab_switching(splice(template, rendered))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(page)

    # Copy all other mockup pages (index, about, articles, videos) to build dir
    build_dir = os.path.dirname(os.path.abspath(args.out))
    mockup_dir = os.path.join(ROOT, "mockup")
    copied_pages = []
    for fname in os.listdir(mockup_dir):
        if fname.endswith(".html") and fname != "documents.html":
            src = os.path.join(mockup_dir, fname)
            dst = os.path.join(build_dir, fname)
            if os.path.abspath(src) != os.path.abspath(dst):
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
