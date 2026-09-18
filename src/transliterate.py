"""Baraha transliteration to Devanagari Unicode converter with full Vedic accent support.

Supports:
- Consonants and conjuncts (including ~g, ~G, ~j, ~J, kSh, GY)
- Vowels and matras
- Vedic accents:
    q -> U+0952 (Anudatta: bottom horizontal line ॒)
    # -> U+0951 (Svarita: top vertical stroke ॑)
    $ -> U+1CDA (Deergha Svarita: double vertical stroke ᳚)
- Vedic nasal glyphs:
    (gm), (gM), (gm~) -> U+A8F3 (ꣳ DEVANAGARI SIGN CANDRABINDU VIRAMA)
    (gg)              -> U+1CFA (ᳺ VEDIC SIGN DOUBLE ANUSVARA ANTARGOMUKHA)
    ~M                -> U+00A0 U+0901 (NBSP + Candrabindu ँ)
- Symbols & Punctuation:
    & -> ऽ (Avagraha)
    | -> । (Danda)
    || -> ॥ (Double Danda)
    ^ -> ZWNJ (Zero Width Non-Joiner)
- Canonical normalization: ensures zero dotted circles around Visarga (ः) and Anusvara (ं).
"""

import re
import unicodedata

CONSONANTS = {
    'k': 'क्', 'kh': 'ख्', 'K': 'ख्', 'g': 'ग्', 'gh': 'घ्', 'G': 'घ्', '~g': 'ङ्', '~G': 'ङ्',
    'c': 'च्', 'ch': 'च्', 'Ch': 'छ्', 'C': 'छ्', 'j': 'ज्', 'jh': 'झ्', 'J': 'झ्', '~j': 'ञ्', '~J': 'ञ्',
    'T': 'ट्', 'Th': 'ठ्', 'TH': 'ठ्', 'D': 'ड्', 'Dh': 'ढ्', 'DH': 'ढ्', 'N': 'ण्',
    't': 'त्', 'th': 'थ्', 'd': 'द्', 'dh': 'ध्', 'n': 'न्',
    'p': 'प्', 'ph': 'फ्', 'P': 'फ्', 'Pr': 'प्र्', 'b': 'ब्', 'bh': 'भ्', 'B': 'भ्', 'm': 'म्',
    'y': 'य्', 'Y': 'य्', 'r': 'र्', 'l': 'ल्', 'v': 'व्', 'V': 'व्', 'w': 'व्', 'W': 'व्',
    'S': 'श्', 'sh': 'श्', 'Sh': 'ष्', 'shh': 'ष्', 's': 'स्', 'h': 'ह्', 'L': 'ळ्',
    'x': 'क्ष्', 'kSh': 'क्ष्', 'j~j': 'ज्ञ्', 'GY': 'ज्ञ्',
}

VOWEL_SIGNS = {
    'a': '',
    'A': 'ा', 'aa': 'ा',
    'i': 'ि',
    'I': 'ी', 'ee': 'ी',
    'u': 'ु',
    'U': 'ू', 'oo': 'ू',
    'Ru': 'ृ', 'ru': 'ृ',
    'RU': 'ॄ',
    'e': 'े', 'E': 'े',
    'ai': 'ै',
    'o': 'ो', 'O': 'ो',
    'au': 'ौ',
}

INDEPENDENT_VOWELS = {
    'a': 'अ',
    'A': 'आ', 'aa': 'आ',
    'i': 'इ',
    'I': 'ई', 'ee': 'ई',
    'u': 'उ',
    'U': 'ऊ', 'oo': 'ऊ',
    'Ru': 'ऋ', 'ru': 'ऋ',
    'RU': 'ॠ',
    'e': 'ए', 'E': 'ए',
    'ai': 'ऐ',
    'o': 'ओ', 'O': 'ओ',
    'au': 'औ',
}

CONSONANT_KEYS = sorted(CONSONANTS.keys(), key=len, reverse=True)
VOWEL_KEYS = sorted(VOWEL_SIGNS.keys(), key=len, reverse=True)


ENGLISH_CORE_STOPWORDS = {
    'the', 'is', 'are', 'was', 'were', 'of', 'in', 'to', 'for', 'and', 'with', 
    'this', 'that', 'from', 'by', 'as', 'at', 'not', 'be', 'or', 'on', 'your',
    'which', 'there', 'having', 'other', 'another', 'same', 'such', 'only',
    'will', 'shall', 'may', 'can', 'cannot', 'could',
    'should', 'would', 'these', 'those', 'them', 'they', 'their', 'its',
    'you', 'we', 'our', 'us', 'who', 'whom', 'whose', 'all', 'both', 'each',
    'more', 'between', 'during', 'after', 'before', 'below', 'above', 'also',
    'upto', 'into', 'out', 'up', 'down', 'over', 'under', 'again', 'then',
    'here', 'there', 'when', 'where', 'why', 'how', 'than',
    'a', 'an', 'per',
}

ENGLISH_METADATA_WORDS = {
    'please', 'note', 'notes', 'users', 'document', 'confirm', 'method', 'methods', 
    'first', 'second', 'third', 'fourth', 'fifth', 'details', 'appendix', 'split', 
    'combined', 'chanting', 'full', 'text', 'concised', 'formed', 'adding', 
    'word', 'part', 'see', 'explains', 'trial', 'practice', 'order', 
    'customary', 'continuous', 'continous', 'vary', 'convention', 'conventions', 'appearing', 
    'case', 'proceed', 'chapter', 'capter', 'general', 'generally', 
    'one', 'get', 'proper', 'doing', 'meaning', 
    'students', 'rule', 'rules', 'version', 'dated', 'copies', 'published', 
    'book', 'books', 'kindly', 'notify', 'mail', 'errors', 'corrections',
    'given', 'incorporated', 
    'item', 'items', 'introduction', 'purpose', 'ends', 'optional', 'additional',
    'coding', 'phonetic', 'special', 'care', 'uses',
    'sound', 'capital', 'letters', 'matches',
    'nasal', 'visargam', 'symbols', 'represents', 'separately',
    'without', 'joining', 'conjunct', 'consonants',
    'inadvertent', 'deletions', 'source', 'code', 'needs', 'formatting',
    'differ', 'requiring', 'precise', 'perform', 'performed', 'final', 'software',
    'output', 'form', 'lot', 'issues', 'arise', 'places', 'tab',
    'character', 'divide', 'information', 'tables', 'exist',
    'original', 'publication', 'dt', 'respect', 'base', 'file',
    'available', 'availability', 'depending', 'reciting', 'idols', 'deities',
    'cleaned', 'decorated', 'count', 'paucity', 'beneficial',
    'section', 'sections', 'number', 'numbers', 'change',
    'para', 'paras', 'no', 'ref', 'refs', 'expansion', 'reference', 'references',
    'recite', 'mind', 'starting', 'total', 'homas', 'followed', 'gives', 'final',
    'archana', 'archanaas', 'puja', 'pooja', 'time', 'table', 'translation', 'meaning',
    'scholars', 'separate', 'different', 'conveyed', 'direct', 'experience',
    'poetic', 'called', 'seen', 'lord', 'base', 'dated', 'source', 'dec', 'jan', 'nov',
    'point', 'performing', 'included', 'include', 'includes', 'sloka', 'following',
    'ts', 'tb', 'ta', 'rv', 'sv', 'av', 'apmb', 'ms', 'ks', 'sb', 'vs', 'eak',
    'etc', 'sukhtam', 'sukhtams', 'sukhtham', 'panchakam', 'times', 'round',
    'rig', 'veda', 'vedas', 'khila', 'kaandam', 'kanda', 'sruti', 'sruthi',
    'rutvik', 'abhishekam', 'recital', 'conduct', 'known', 'definite', 'exact',
    'shanti', 'japam', 'shiva', 'stuti',
}

ALL_ENGLISH_WORDS = ENGLISH_CORE_STOPWORDS | ENGLISH_METADATA_WORDS

CITATION_RE = re.compile(
    r'\b(?:TS|TB|TA|RV|SV|AV|APMB|ApMB|EAK|MS|KS|SB|VS)\b|\b(?:T\.S|T\.B|T\.A|R\.V|S\.V|A\.V|A\.P\.M\.B)\.?',
    re.I
)


def normalize_glued_citation_tokens(text: str) -> str:
    """Normalize tokens where Baraha typos glued English words to citations or numbers.
    e.g. 'toTS 1.2.14.7' -> 'to TS 1.2.14.7', 'to53' -> 'to 53', 'inTS' -> 'in TS'.
    """
    text = re.sub(r'\b(to|in|from)(TS|TB|TA|RV|SV|AV|APMB|ApMB|MS|KS|SB|VS|EAK|T\.S|T\.B|T\.A|R\.V)', r'\1 \2', text, flags=re.I)
    text = re.sub(r'\b(to|upto|para|item)(\d+)\b', r'\1 \2', text, flags=re.I)
    return text


def clean_baraha_english(text: str) -> str:
    """Clean Baraha idiosyncrasies in English text (like capitalized E and O)."""
    text = re.sub(r'</?lang=[^>]+>', '', text).strip()
    text = normalize_glued_citation_tokens(text)
    def fix_word(m):
        w = m.group(0)
        if w.isupper():
            return w
        # Keep acronyms or citations like 'TS', 'TB', 'TA' uppercase
        if w.lower() in {'ts', 'tb', 'ta', 'rv', 'sv', 'av', 'apmb', 'ms', 'ks', 'sb', 'vs', 'eak'}:
            return w.upper()
        if w.lower() in {'no', 'ref', 'para', 'item'}:
            return w.capitalize() if w[0].isupper() else w.lower()
        low = w.lower()
        return low.capitalize() if w[0].isupper() else low
    return re.sub(r'\b[A-Za-z]+[EO][A-Za-z]*\b', fix_word, text)


def is_english_text(text: str) -> bool:
    """Check if an entire line/paragraph or title is English/citation and should NOT be transliterated."""
    if not text:
        return False
    t = re.sub(r'</?lang=[^>]+>', '', text).strip()
    if '<lang=eng>' in t.lower():
        return True

    # 1. Explicit documentation header patterns
    if re.match(r'^(?:Notes for Users|Coding is more|Special care|Confirm corrections|Kindly notify|Document source|Lot of issues|dt\s+\d|~\w\s+is\s+nasal|H\s+is\s+visargam|\^\^\s+symbol|Base\s+(?:file|source)|Vedic/Swara|Vedic/)', t, re.I):
        return True

    t_norm = normalize_glued_citation_tokens(t)

    # 2. Entire line in parentheses / brackets: check inside content
    inner = re.sub(r'^[\(\[\{]\s*(.*?)\s*[\)\]\}](?:\s*<lang=def>)?$', r'\1', t_norm).strip()
    target = inner if inner != t_norm else t_norm

    raw_words = re.findall(r'[a-zA-Z]+', target)
    clean_words = [w.lower() for w in raw_words]
    if clean_words and all(w in ALL_ENGLISH_WORDS for w in clean_words):
        return True

    # 3. Vedic scriptural citation / reference lines (e.g. TS 5.6.1.1, TB 1.4.8.1 (for Para No. 1 to 6), T.A.6.31.1)
    if '||' not in target:
        if CITATION_RE.search(target) or re.search(r'\bRig\s+V[Ee]da\b', target, re.I):
            stripped = CITATION_RE.sub(' ', target)
            stripped = re.sub(r'\bRig\s+V[Ee]da\b', ' ', stripped, flags=re.I)
            stripped = re.sub(r'\b\d+[a-z]?\b', ' ', stripped, flags=re.I)
            stripped = re.sub(r'[\d\.\,\:\;\-\/\(\)\[\]\{\}\"\'\&\+\*\\]', ' ', stripped)
            rem_words = [w.lower() for w in stripped.split()]
            if not rem_words or all(w in ALL_ENGLISH_WORDS for w in rem_words):
                return True

        # Reference-only lines (e.g. "No Ref available for 1...", "(Starting from TB 3.1.1, for item no. 1 to 40)")
        if re.search(r'\b(?:ref|no\s+ref|available|upto\s+para|for\s+para|for\s+item|para\s+no|item\s+no|starting\s+fr[oO]m)\b', target, re.I):
            stripped = re.sub(r'\b\d+[a-z]?\b', ' ', target, flags=re.I)
            stripped = re.sub(r'[\d\.\,\:\;\-\/\(\)\[\]\{\}\"\'\&\+\*\\]', ' ', stripped)
            rem_words = [w.lower() for w in stripped.split()]
            if all(w in ALL_ENGLISH_WORDS for w in rem_words):
                return True

    # 4. English list items: e.g. "1. Purusha Sukhtam", "2. Uttara Naaraayanam"
    if re.match(r'^\d+\.\s+[A-Za-z\s]+(?:Sukhtam|Sukhtham|Naaraayanam|Panchakam)', target, re.I):
        return True

    # 5. General English prose / sentence detection
    core_matches = sum(1 for w in clean_words if w in ENGLISH_CORE_STOPWORDS)
    total_matches = sum(1 for w in clean_words if w in ALL_ENGLISH_WORDS)

    if core_matches >= 4:
        return True

    # Without Sanskrit danda or accents:
    if not re.search(r'[#$\|]', target):
        if len(clean_words) >= 3 and (core_matches >= 3 or (core_matches >= 2 and total_matches / len(clean_words) >= 0.30)):
            return True
        if len(clean_words) == 1 and clean_words[0] in {'appendix', 'introduction', 'purpose', 'methods', 'method', 'details', 'notes', 'note'}:
            return True
        if len(clean_words) == 2 and total_matches == 2 and clean_words[0] in {'split', 'combined', 'appendix', 'chanting', 'first', 'second', 'third'}:
            return True

    return False


def normalize_parasavarna_sandhi(text: str) -> str:
    """Normalize word-boundary phonetic parasavarna spellings to canonical printed Anusvara (M).

    In spoken Vedic recitation and phonetic transcription, word-final anusvara before a stop consonant
    is often realized as the class nasal (e.g. 'kaqvi~g ka#vIqnAM' for 'क॒विं क॑वी॒नाम्' or
    'gaqNAnA$n tvA' for 'ग॒णानां᳚ त्वा'). In traditional printed texts, however, word-boundary anusvara
    is standardly printed with the Anusvara dot (ं), and the chanter applies the sandhi orally.
    """
    # 1. Word-final ~g / ~G before velar (k, kh, g, gh)
    def repl_velar(m):
        base = m.group(1)
        acc = m.group(2)
        rest = m.group(3)
        pure = re.sub(r'[q#$]', '', base).lower()
        if pure in {'prA~g', 'viShva~g', 'pratya~g', 'anva~g', 'tirya~g', 'udya~g'}:
            return m.group(0)
        base_clean = base[:-2]
        return f'{base_clean}M{acc}{rest}'

    text = re.sub(r'(\b[a-zA-Z]+~[gG])([q#$]*)(\s+[kKgG])', repl_velar, text)

    # 2. Word-final ~j / ~J before palatal (c, ch, j, jh)
    def repl_palatal(m):
        base = m.group(1)
        acc = m.group(2)
        rest = m.group(3)
        base_clean = base[:-2]
        return f'{base_clean}M{acc}{rest}'

    text = re.sub(r'(\b[a-zA-Z]+~[jJ])([q#$]*)(\s+[cCjJ])', repl_palatal, text)

    # 3. Known phonetic sandhi cases where anusvara was typed as 'n' before dental
    text = re.sub(r'\b(gaqNAnA)(\$?|\#?|q?)n\s+(tvA)', r'\g<1>\g<2>M \g<3>', text)
    text = re.sub(r'\b(madhu#matI)n\s+(dEqvEBya)', r'\g<1>M \g<2>', text)
    text = re.sub(r'\b(vijya)qn\s+(dhanu)', r'\g<1>qM \g<2>', text)

    return text


def baraha_to_devanagari(text: str) -> str:
    """Convert Baraha ASCII transliteration text into Devanagari Unicode with Vedic svara notation."""
    if not text:
        return ""

    text = normalize_parasavarna_sandhi(text)

    # If line has an English prefix transitioning via <lang=def> to Sanskrit (e.g. Note... <lang=def> mantra)
    if '<lang=def>' in text.lower() and '<lang=eng>' not in text.lower():
        parts = re.split(r'<lang=def>', text, flags=re.I, maxsplit=1)
        if is_english_text(parts[0]):
            return (clean_baraha_english(parts[0]) + ' ' + baraha_to_devanagari(parts[1].strip())).strip()

    # Do not transliterate pure English text to Devanagari
    if is_english_text(text):
        return clean_baraha_english(text)

    # 1. Pre-normalize Sacred OM, Vedic nasal glyphs and symbols first so nested parens don't break
    text = re.sub(r'\b(Oum|OUM|OM|Oum_|OM_|oUM)\b', 'ॐ', text)
    text = text.replace('ओउम्', 'ॐ')
    text = re.sub(r'\(gm~?\)', '\uA8F3', text, flags=re.I)
    text = re.sub(r'\(gg\)', '\u1CFA', text, flags=re.I)
    text = text.replace('~M', '\u00A0\u0901')
    text = text.replace('&', 'ऽ')
    text = text.replace('||', '॥')
    text = text.replace('|', '।')
    text = re.sub(r'\^+', '\u200C', text)

    # Normalize glued tokens
    text = normalize_glued_citation_tokens(text)

    # Protect English tokens, tags, parentheticals, and phrases
    placeholders = []

    def repl_clean_eng(m):
        placeholders.append(clean_baraha_english(m.group(0)))
        return f'\uE000{len(placeholders)-1}\uE001'

    def repl_eng(m):
        placeholders.append(m.group(0))
        return f'\uE000{len(placeholders)-1}\uE001'

    # Normalize Devanagari Roman numeral artifacts if present
    dev_roman_replacements = [
        ('3 इ)', '3 i)'), ('3 इ.', '3 i.'),
        ('1 इ)', '1 i)'), ('2 इ)', '2 i)'), ('4 इ)', '4 i)'), ('5 इ)', '5 i)'),
        ('इइइ)', 'iii)'), ('इइ)', 'ii)'), ('इ)', 'i)'),
        ('इव्)', 'iv)'), ('व्)', 'v)'), ('वि)', 'vi)'),
        ('विइ)', 'vii)'), ('विइइ)', 'viii)'), ('इक्ष्)', 'ix)'), ('क्ष्)', 'x)'),
        ('इइइ.', 'iii.'), ('इइ.', 'ii.'), ('इ.', 'i.'),
        ('इव्.', 'iv.'), ('व्.', 'v.'), ('वि.', 'vi.'),
    ]
    for k, v in dev_roman_replacements:
        text = text.replace(k, v)

    # Protect Roman numeral list item markers e.g. "i)", "ii)", "iii)", "iv)", "v)", "vi)", "3 i)", "3 ii)", "1 i."
    def repl_roman_list(m):
        prefix = m.group(1)
        marker = m.group(2)
        placeholders.append(marker)
        return f'{prefix}\uE000{len(placeholders)-1}\uE001'

    text = re.sub(
        r'(?i)(^|[\s\(\[\|\॥\t])((\d+\s+)?(?:i{1,4}|iv|v|vi{1,3}|ix|x|xi{1,3}|xii)[\)\.])(?=\s|$)',
        repl_roman_list,
        text
    )

    # Protect English prefix before mantra, e.g. "Expansion of ..."
    def repl_prefix_exp(m):
        placeholders.append(clean_baraha_english(m.group(1)) + ' ')
        return f'\uE000{len(placeholders)-1}\uE001'
    text = re.sub(r'^(Expansion\s+of\s+)', repl_prefix_exp, text, flags=re.I)

    # <lang=eng> blocks
    def repl_lang_eng(m):
        content = clean_baraha_english(m.group(1))
        placeholders.append(content)
        return f'\uE000{len(placeholders)-1}\uE001'

    text = re.sub(r'<lang=eng>(.*?)(?:<lang=def>|$)', repl_lang_eng, text, flags=re.I | re.S)
    text = re.sub(r'</?lang=[^>]+>', '', text)

    # Check for suffix English note after danda: e.g. "... || (Additional chanting Ends)" or "... | This Expansion is appearing in TS 3.3.11.3"
    def repl_post_danda(m):
        danda = m.group(1)
        suffix = m.group(2)
        if is_english_text(suffix) or suffix.strip().lower() in ENGLISH_CORE_STOPWORDS or suffix.strip().lower() in ALL_ENGLISH_WORDS:
            placeholders.append(' ' + clean_baraha_english(suffix))
            return f'{danda}\uE000{len(placeholders)-1}\uE001'
        return m.group(0)

    text = re.sub(r'([।॥])\s+([A-Za-z0-9\(\[\"\'].*)$', repl_post_danda, text)

    # Parenthesized content handler: generalized Baraha Sanskrit vs English
    def repl_paren(m):
        open_b = m.group(1)
        inside = m.group(2).strip()
        close_b = m.group(3)

        # Handle alternate chant notes starting with "Or " / "or "
        m_or = re.match(r'^(Or|or|OR)\s+(.*)$', inside, re.S)
        if m_or:
            rest = m_or.group(2).strip()
            rest_deva = baraha_to_devanagari(rest)
            placeholders.append(open_b + "Or " + rest_deva + close_b)
            return f'\uE000{len(placeholders)-1}\uE001'

        # 1. Any Vedic svara accents, anudatta q, or special symbols -> SANSKRIT
        if re.search(r'[#$\uA8F3\u1CFA]', inside) or re.search(r'[a-zA-Z]q', inside) or re.search(r'(~[gGjJM]|\&|\^)', inside):
            return m.group(0)

        # 2. Citations or citation ranges -> ENGLISH
        if CITATION_RE.search(inside) or re.search(r'\bRig\s+V[Ee]da\b', inside, re.I):
            w = [x.lower() for x in re.findall(r'[a-zA-Z]+', inside)]
            if all(x in ALL_ENGLISH_WORDS or x in {'ts', 'tb', 'ta', 'rv', 'sv', 'av', 'apmb', 'eak', 'ms', 'ks', 'sb', 'vs'} for x in w):
                placeholders.append(open_b + clean_baraha_english(inside) + close_b)
                return f'\uE000{len(placeholders)-1}\uE001'

        if re.match(r'^(?:for|upto|in|to)\s+(?:para|item)\b', inside, re.I):
            placeholders.append(open_b + clean_baraha_english(inside) + close_b)
            return f'\uE000{len(placeholders)-1}\uE001'
        if re.match(r'^item\s+no\.?\b', inside, re.I):
            placeholders.append(open_b + clean_baraha_english(inside) + close_b)
            return f'\uE000{len(placeholders)-1}\uE001'
        if re.match(r'^\d+\s+(?:to|-)\s+\d+$', inside, re.I):
            placeholders.append(open_b + clean_baraha_english(inside) + close_b)
            return f'\uE000{len(placeholders)-1}\uE001'
        if re.match(r'^\d+\s+tim[Ee]s?\b', inside, re.I):
            placeholders.append(open_b + clean_baraha_english(inside) + close_b)
            return f'\uE000{len(placeholders)-1}\uE001'
        if re.match(r'^(?:fOr|for)\s+.*kalaSa', inside, re.I):
            placeholders.append(open_b + clean_baraha_english(inside) + close_b)
            return f'\uE000{len(placeholders)-1}\uE001'

        # 3. Word-based English check
        words = [x.lower() for x in re.findall(r'[a-zA-Z]+', inside)]
        if words:
            core_count = sum(1 for x in words if x in ENGLISH_CORE_STOPWORDS)
            eng_count = sum(1 for x in words if x in ALL_ENGLISH_WORDS)

            if core_count >= 2:
                placeholders.append(open_b + clean_baraha_english(inside) + close_b)
                return f'\uE000{len(placeholders)-1}\uE001'
            if len(words) >= 2 and eng_count == len(words):
                placeholders.append(open_b + clean_baraha_english(inside) + close_b)
                return f'\uE000{len(placeholders)-1}\uE001'
            if len(words) == 1 and words[0] in {'method', 'methods', 'round', 'pooja', 'in', 'optional', 'see', 'ends'}:
                placeholders.append(open_b + clean_baraha_english(inside) + close_b)
                return f'\uE000{len(placeholders)-1}\uE001'

        # 4. Baraha Sanskrit phonetic / morphological markers
        if re.search(r'[a-zA-Z]H\b', inside) or re.search(r'[a-zA-Z]M\b', inside):
            return m.group(0)
        if re.search(r'(?:^|[a-z])R[uU]', inside):
            return m.group(0)
        if re.search(r'[a-z][A-Z]', inside):
            return m.group(0)

        # Default: if is_english_text is true, protect it, else transliterate as Sanskrit
        if is_english_text(inside):
            placeholders.append(open_b + clean_baraha_english(inside) + close_b)
            return f'\uE000{len(placeholders)-1}\uE001'

        return m.group(0)

    text = re.sub(r'([\(\[])([^\)\]]+)([\)\]])', repl_paren, text)

    # Standalone scriptural citation codes e.g. TS 5.6.1.1, TB 1.4.8.1, T.A.6.58.1, RV.10.173.5, EAK 1.9.5, T.S. 5-4-8-1
    text = re.sub(
        r'\b(?:TS|TB|TA|RV|SV|AV|APMB|ApMB|MS|KS|SB|VS|EAK)\b\s*[\d\.\,\-]+(?:[a-z]|\b)',
        repl_clean_eng,
        text,
        flags=re.I
    )
    text = re.sub(
        r'\b(?:T\.S|T\.B|T\.A|R\.V|S\.V|A\.V|A\.P\.M\.B)\.?\s*[\d\.\,\-]+(?:[a-z]|\b)',
        repl_clean_eng,
        text,
        flags=re.I
    )
    # Standalone letter+digit codes e.g. A1, A7, T.A.1.2.3, T.B.3.11.7.1
    text = re.sub(r'\b[A-Za-z]\d+\b', repl_eng, text)
    text = re.sub(r'\b[A-Z]\.[A-Z0-9\.]+\b', repl_eng, text)
    # Standalone citation prefix without numbers if remaining
    text = re.sub(r'\b(?:TS|TB|TA|RV|SV|AV|APMB|ApMB|MS|KS|SB|VS|EAK)\b', repl_eng, text)

    # Citation phrases e.g. "for Para No. 1 to 6", "for item NO. 124 to 129", "for para 15a", "upto Para 53"
    text = re.sub(
        r'\b(?:for|upto|to|in)\s+(?:para|item|Para|Item)\s+(?:no\.?|nO\.?|NO\.?)?\s*[\d\s\,\-toand]+',
        repl_clean_eng,
        text,
        flags=re.I
    )
    text = re.sub(
        r'\b(?:No\s+Ref\s+available|Ref)\s+.*?(?=[।॥\/]|$)',
        repl_clean_eng,
        text,
        flags=re.I
    )

    # Standalone English structural words
    text = re.sub(
        r'\b(Details|of|in|First|Second|Third|Fourth|Fifth|Method|Methods|Appendix|Chanting|Split|Combined|Introduction|Purpose|Chapter|Section|Optional|Additional|Ends|Rig|Vedic|Convention|Skywards|Scholars)\b',
        repl_clean_eng,
        text,
        flags=re.I
    )

    # 1. Clean whitespace before combining tokens in Baraha source
    text = re.sub(r'\s+([q#$HM]+)', r'\1', text)

    # 2. Compound symbols (~g, ~j, j~j, GY, kSh) are natively handled by CONSONANTS dictionary

    # 3. Ensure Visarga (H) is contiguous with the syllable, followed by accent marker
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
            out.append('॒')  # U+0952 Anudatta
            i += 1
            continue
        elif text[i] == '#':
            out.append('॑')  # U+0951 Svarita
            i += 1
            continue
        elif text[i] == '$':
            out.append('᳚')  # U+1CDA Deergha Svarita
            i += 1
            continue
        elif text[i] == 'H':
            out.append('ः')  # U+0903 Visarga
            i += 1
            continue
        elif text[i] == 'M':
            out.append('ं')  # U+0902 Anusvara
            i += 1
            continue
        elif text[i] == '\u200C':
            out.append('\u200C')
            i += 1
            continue
        elif text[i] in ' \t\n\r।,॥():-0123456789.[]{}/\\+*\uA8F3\uA8F2\uA8F4\u1CFA\u00A0\u0901\u0950':
            out.append(text[i])
            i += 1
            continue

        # Match consonant
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

        # Match independent vowel
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

    # 4. Canonical Normalization to ensure ZERO dotted circles:
    # 4a. Deduplicate consecutive viramas:
    res = re.sub(r'\u094D+', '्', res)
    # 4b. Visarga (ः) must precede any combining Vedic accent:
    res = re.sub(r'([\u0951\u0952\u1CDA])(ः)', r'\2\1', res)
    # 4c. Anusvara (ं) must precede any combining Vedic accent:
    res = re.sub(r'([\u0951\u0952\u1CDA])(ं)', r'\2\1', res)
    # 4d. Candrabindu (ँ) directly after whitespace -> convert space to non-breaking space
    res = re.sub(r'\s+ँ', '\u00A0ँ', res)
    # 4e. Accents should not follow punctuation or whitespace without a base:
    res = re.sub(r'([ \t\n।,॥\(\)\[\]\{\}\-])([\u0951\u0952\u1CDA]+)', r'\1', res)
    # 4f. Alternate chant notation (Or ...) in English:
    res = re.sub(r'\(\s*ओर्\s*', '(Or ', res)

    return res


if __name__ == '__main__':
    tests = [
        "SannO# miqtraH SaM ~Mvaru#NaH | SannO# BavatvaryaqmA |",
        "Sannaq indrOq bRuhaqspati#H | SannOq viShNu#rurukraqmaH |",
        "namOq brahma#NE | nama#stE vAyO | tvamEqva praqtyakShaqM brahmA#si |",
        "tvamEqva praqtyakShaqM brahma# vadiShyAmi | RuqtaM ~Mva#diShyAmi | saqtyaM ~Mva#diShyAmi |",
        "SIkShAM ~MvyA$KyAsyAqmaH | varNaqH svaraH | mAtrAq balaM | sAma# santAqnaH |",
        "pA~NktA(gg)# sOmaH |",
        "OM SAntiqH SAntiqH SAnti#H ||",
    ]
    for t in tests:
        print(f"Baraha: {t}")
        print(f"Deva:   {baraha_to_devanagari(t)}\n")
