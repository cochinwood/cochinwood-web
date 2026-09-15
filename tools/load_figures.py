"""Vehicle-tied load figures on the built site: extract every one, then check them against each other.

    python tools/load_figures.py [--dist dist] [--out load-figures] [--load-pages FILE]

Read-only over a built dist/ (run python build.py first). Writes <out>/records.json (one record per
load figure) and <out>/flags.json (rule hits, per-class statistics, coverage). Paths default to the
repo root: dist/ and load-figures/ (git-ignored). Standard library only, like every other tool here.
It exits 0 whatever it finds: it is a detector for review, not a gate. The gates are the tests in
tools/test_content_claims.py (LoadFigureConsistencyTests), which reuse this extraction.

WHAT IT EXTRACTS
  Text surfaces, per page: the meta description; FAQPage JSON-LD questions and answers; visible
  blocks inside <main> (p, li, h1-h6, dt, dd, blockquote, figcaption, summary) split into sentences;
  every table row as cells with its column header and caption. Header, footer, nav, aside, related
  posts, tables of contents, privacy and WhatsApp widgets, scripts and buttons are dropped. FAQ
  answers are recognised by .faq-item / .cwf__q wrappers or by h3/h4 questions under an FAQ h2.
  Quantities: sheets/panels/boards, tonnes (tonnes, tonne, tons, ton, MT, t, -tonner), kg, sq ft,
  m3/cbm, crates/cases, pallets and "N containers' worth", as single values or ranges.
  Vehicle link, first match wins: a vehicle in the same sentence (nearest, a following one only
  after "per/in a/on a"), the previous or next sentence of the same section, the same FAQ answer or
  question; in tables the same cell, another cell of the same row, the column header, the caption.
  Vehicle class: container-20ft / container-40ft / container-40hc; truck-<N>ft, with -sxl or -mxl
  for 32 ft when the axle is named; truck-single-axle / truck-multi-axle with no length; trailer;
  truck-unspecified; other. "32-ft SXL or 22-ft container truck" keeps both as alt_classes.
  Thickness: stated right after the quantity, else the nearest "N mm" in the sentence, block or FAQ
  answer. Sheets are 8 x 4 ft (2.9768 m2) unless the sentence names another size.
  Conversion at the loading guide's 650 kg/m3: sheet kg = 2.9768 x t_mm/1000 x 650; sq ft x
  0.0929 m2 x t_mm/1000 x 650; m3 x 650; "N containers' worth" x 13.05 m3 (the site estimator's
  20 ft flat stack, 2 x 2,192 mm of 2.9768 m2 panels). Every record carries tonnes_low/high.
  Qualifiers stop a figure being read as a full vehicle load: threshold ("above 14 tonnes"),
  part-load, order-size, rating (payload, limit, ceiling, "of its 67 m3"), illustrative ("would",
  "at this density", division), non-plywood (tile, brass, transformers), per-item (per crate, point
  loads, static ratings) and mixed-component ("plus pallets").

RULES (flags.json)
  1   container sheet count above the loading guide's capacity-only ceiling, or 20 ft plywood tonnage
      above 21.45 t (33 m3 x 650) / 40 ft above 26.7 t
  1b  container sheet count above the site estimator's flat-stack count (assets/container-
      calculator.js defaults: 650 kg/m3, 26.7 t, 300 kg packing, 100 mm clearance; 20/40 ft only)
  2   same page, compatible vehicles, tonnage equivalents more than 15% apart
  2b  sheets paired with tonnes but no thickness: the implied thickness is outside 6-18 mm +/-15%
  3   cross-page outlier: a page's range outside the interquartile range of its class_detail
      (classes with 4+ pages); 3b pairwise more than 15% apart for smaller classes
  4   a vehicle name that is both single-axle and multi-axle ("multi-axle SXL"), or a container
      equipment code on a truck body
  5   sq ft or m3 paired with tonnes in the same sentence, more than 15% apart at 650 kg/m3 (or no
      thickness stated for the sq ft)
  Capacity rules (1-3, 5) skip threshold, part-load, order-size, illustrative, non-plywood, per-item
  and mixed-component records; containers also skip rating records. Known false positives: two
  stated truck sizes on one page read as a range (Khammam's 9 t and 16 t), and 32 ft trucks with the
  axle unstated grouped apart from the named axles.
"""
import argparse
import html as html_lib
import io
import json
import math
import os
import re
import statistics
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DENSITY = 650.0
SHEET_M2 = 2.44 * 1.22          # 2.9768
SQFT_M2 = 0.09290304
C20_M3, C40_M3, C40HC_M3 = 33.0, 67.0, 76.0
C20_T_SPACE = C20_M3 * DENSITY / 1000   # 21.45 t fills the 20 ft box
C40_PAYLOAD_KG = 26500.0
C40_T_MAX = 26.7


def sheet_kg(t_mm, area=SHEET_M2):
    return area * t_mm / 1000 * DENSITY


def ceiling_capacity(cls, t_mm):
    """Loading-guide capacity-only ceiling (sheets)."""
    if cls == 'container-20ft':
        return math.floor(C20_M3 / (SHEET_M2 * t_mm / 1000))
    if cls in ('container-40ft', 'container-40hc'):
        vol = C40_M3 if cls == 'container-40ft' else C40HC_M3
        return min(math.floor(C40_PAYLOAD_KG / sheet_kg(t_mm)), math.floor(vol / (SHEET_M2 * t_mm / 1000)))
    return None


def ceiling_estimator(cls, t_mm):
    """Site estimator (container-calculator.js) defaults: 650 kg/m3, 26.7 t payload,
    300 kg packing, 100 mm clearance; flat stacks under the 2,292 mm door."""
    box = {'container-20ft': (5900, 28130), 'container-40ft': (12032, 28750)}.get(cls)
    if not box:
        return None
    length, _ = box
    along = math.floor((length - 100 + 50) / (2440 + 50))
    across = math.floor((2340 - 100 + 50) / (1220 + 50))
    layers = math.floor((2292 - 100) / t_mm)
    layout = along * across * layers
    weight = math.floor((26.7 * 1000 - 300) / sheet_kg(t_mm))
    return min(layout, weight)


# ----------------------------------------------------------------- a small HTML tree (stdlib)
# The detector was first written against lxml.html; this tree keeps the same text/tail model so the
# extraction below reads the same text. As with lxml, removing a node drops its tail text.
VOID_TAGS = frozenset('area base br col embed hr img input link meta param source track wbr'.split())
_P_CLOSERS = frozenset('address article aside blockquote details dialog dir div dl fieldset figcaption figure footer '
                       'form h1 h2 h3 h4 h5 h6 header hgroup hr main menu nav ol p pre section table ul'.split())
_AUTO_CLOSE = {
    'p': _P_CLOSERS, 'li': frozenset(['li']), 'dt': frozenset(['dt', 'dd']), 'dd': frozenset(['dt', 'dd']),
    'td': frozenset(['td', 'th', 'tr', 'tbody', 'thead', 'tfoot']), 'th': frozenset(['td', 'th', 'tr', 'tbody', 'thead', 'tfoot']),
    'tr': frozenset(['tr', 'tbody', 'thead', 'tfoot']), 'thead': frozenset(['tbody', 'tfoot']),
    'tbody': frozenset(['tbody', 'tfoot']), 'option': frozenset(['option']),
}


class Node:
    __slots__ = ('tag', 'attrib', 'children', 'text', 'tail', 'parent')

    def __init__(self, tag, attrib=None, parent=None):
        self.tag, self.attrib, self.children, self.text, self.tail, self.parent = tag, attrib or {}, [], '', '', parent

    def get(self, key, default=None):
        return self.attrib.get(key, default)

    def __iter__(self):
        return iter(self.children)

    def iter(self, tag=None):
        stack = [self]
        while stack:
            node = stack.pop()
            if tag is None or node.tag == tag:
                yield node
            stack.extend(reversed(node.children))

    def iterancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def getparent(self):
        return self.parent

    def remove(self, child):
        self.children.remove(child)
        child.parent = None

    def text_content(self):
        parts = []

        def walk(node):
            if isinstance(node.tag, str):
                parts.append(node.text)
                for child in node.children:
                    walk(child)
                    parts.append(child.tail)
        walk(self)
        return ''.join(parts)

    def text_nodes(self):
        """lxml's ./descendant-or-self text(): text and descendant tails, not this node's own tail."""
        if isinstance(self.tag, str) and self.text:
            yield self.text
        for child in self.children:
            yield from child.text_nodes()
            if child.tail:
                yield child.tail


class Comment(Node):
    __slots__ = ()

    def __init__(self, data, parent):
        super().__init__(None, None, parent)
        self.text = data


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('#document')
        self.stack = [self.root]

    def _add(self, node):
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)

    def _auto_close(self, tag):
        while len(self.stack) > 1 and tag in _AUTO_CLOSE.get(self.stack[-1].tag, ()):
            self.stack.pop()

    def handle_starttag(self, tag, attrs):
        self._auto_close(tag)
        node = Node(tag, {k: ('' if v is None else v) for k, v in attrs})
        self._add(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self._auto_close(tag)
        self._add(Node(tag, {k: ('' if v is None else v) for k, v in attrs}))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        current = self.stack[-1]
        if current.children:
            current.children[-1].tail += data
        else:
            current.text += data

    def handle_comment(self, data):
        self._add(Comment(data, None))


def parse_html(markup):
    builder = _TreeBuilder()
    builder.feed(markup)
    builder.close()
    return builder.root


def fragment_text(markup):
    root = parse_html('<div>%s</div>' % markup)
    return next(n for n in root.children if n.tag == 'div').text_content()


# ----------------------------------------------------------------- text extraction
DROP_TAGS = frozenset(['script', 'style', 'noscript', 'template', 'svg', 'button', 'footer', 'nav', 'aside'])
DROP_CLASS_PARTS = ('cw-article-related', 'cw-article-navigation', 'cw-privacy', 'cw-page-navigation',
                    'cw-article-toc', 'cw-skip', 'cw-wa')
BLOCK_TAGS = {'p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'dt', 'dd', 'blockquote', 'figcaption', 'summary'}
FAQ_H2 = re.compile(r'(?i)\b(faq|frequently asked|questions)\b')


def dropped(node):
    if node.tag in DROP_TAGS:
        return True
    cls = node.get('class')
    if cls is None:
        return False
    if node.tag == 'header' and 'cw-hd' in cls:
        return True
    if node.tag == 'details' and 'cw-section-menu' in cls:
        return True
    return any(part in cls for part in DROP_CLASS_PARTS)


def norm(s):
    return ' '.join((s or '').replace(' ', ' ').split())


def own_text(el):
    """text of el excluding nested block/table descendants"""
    parts = [el.text or '']
    for ch in el:
        if not isinstance(ch.tag, str):
            parts.append(ch.tail or '')
            continue
        if ch.tag in BLOCK_TAGS or ch.tag in ('table', 'ul', 'ol', 'div', 'section'):
            parts.append(' ')
        else:
            parts.append(own_text(ch))
        parts.append(ch.tail or '')
    return ''.join(parts)


ABBR = re.compile(r'\b(approx|e\.g|i\.e|vs|No|Rs|Pvt|Ltd|Co|St|Dr|min|max|incl|est|ca)\.', re.I)


def split_sentences(text):
    prot = ABBR.sub(lambda m: m.group(0)[:-1] + '․', text)
    parts = re.split(r'(?<=[.!?])["”’)]?\s+(?=[A-Z0-9₹"“(\[~])', prot)
    out = []
    for p in parts:
        p = p.replace('․', '.').strip()
        if p:
            out.append(p)
    return out


def extract_units(path):
    with open(path, encoding='utf-8') as handle:
        return extract_units_from_html(handle.read())


def extract_units_from_html(raw):
    """Return list of text units: dict(source, kind, text, group, section, order; cells/header/caption for rows)."""
    doc = parse_html(raw)
    units = []
    # meta description
    md = [n.get('content') for n in doc.iter('meta') if n.get('name') == 'description' and n.get('content') is not None]
    if md:
        units.append({'source': 'meta', 'kind': 'block', 'text': norm(md[0]), 'group': 'meta'})
    # FAQPage JSON-LD
    for sc in doc.iter('script'):
        if sc.get('type') != 'application/ld+json':
            continue
        try:
            data = json.loads(sc.text or '')
        except Exception:
            continue
        stack = [data]
        while stack:
            d = stack.pop()
            if isinstance(d, list):
                stack.extend(d)
                continue
            if not isinstance(d, dict):
                continue
            if d.get('@type') == 'Question':
                q = norm(fragment_text(d.get('name', '')))
                ans = d.get('acceptedAnswer') or {}
                if isinstance(ans, list):
                    ans = ans[0] if ans else {}
                a = norm(fragment_text(ans.get('text') or ' '))
                units.append({'source': 'faq-jsonld', 'kind': 'faq', 'question': q, 'text': a, 'group': 'ld:' + q})
            for v in d.values():
                if isinstance(v, (dict, list)):
                    stack.append(v)
    for bad in [n for n in doc.iter() if isinstance(n.tag, str) and dropped(n)]:
        if bad.getparent() is not None:
            bad.getparent().remove(bad)
    for c in [n for n in doc.iter() if isinstance(n, Comment)]:
        if c.getparent() is not None:
            c.getparent().remove(c)
    root = next(doc.iter('main'), None) or next(doc.iter('body'), None) or doc

    # walk in document order
    section = ''
    in_faq_section = False
    cur_q = None
    order = 0
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if el.tag == 'table':
            rows = []
            header = []
            for tr in el.iter('tr'):
                cells = [norm(c.text_content()) for c in tr if isinstance(c.tag, str) and c.tag in ('td', 'th')]
                is_head = all(isinstance(c.tag, str) and c.tag == 'th' for c in tr if isinstance(c.tag, str)) and \
                    (tr.getparent().tag == 'thead' or not rows and not header)
                if is_head and not header:
                    header = cells
                else:
                    rows.append(cells)
            cap = norm(' '.join(t for c in el if c.tag == 'caption' for t in c.text_nodes()))
            for r in rows:
                units.append({'source': 'table', 'kind': 'row', 'cells': r, 'header': header, 'caption': cap,
                              'text': ' | '.join(r), 'group': 'table:%d' % order, 'section': section, 'order': order})
                order += 1
            continue
        if el.tag not in BLOCK_TAGS:
            continue
        if any(a.tag == 'table' for a in el.iterancestors()):
            continue
        t = norm(own_text(el))
        if not t:
            continue
        faq_item = None
        for a in el.iterancestors():
            cls = a.get('class') or ''
            if re.search(r'faq-item|cwf__q\b', cls):
                faq_item = a
                break
        if el.tag == 'h2':
            section = t
            in_faq_section = bool(FAQ_H2.search(t))
            cur_q = None
        if faq_item is not None:
            heads = [h for h in faq_item.iter() if isinstance(h.tag, str) and h.tag in ('h2', 'h3', 'h4', 'summary', 'dt')]
            q = norm(heads[0].text_content()) if heads else ''
            if heads and el is heads[0]:
                continue
            units.append({'source': 'faq', 'kind': 'faq', 'question': q, 'text': t, 'group': 'faqitem:%s' % q,
                          'section': section, 'order': order})
        elif in_faq_section and el.tag in ('h3', 'h4'):
            cur_q = t
            order += 1
            continue
        elif in_faq_section and cur_q and el.tag != 'h2':
            units.append({'source': 'faq', 'kind': 'faq', 'question': cur_q, 'text': t, 'group': 'faqsec:%s' % cur_q,
                          'section': section, 'order': order})
        else:
            if el.tag == 'h2' and in_faq_section:
                order += 1
                continue
            units.append({'source': 'body', 'kind': 'block', 'text': t, 'group': 'body', 'section': section,
                          'order': order, 'tag': el.tag})
        order += 1
    return units


# ----------------------------------------------------------------- patterns
NUM = r'\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?'
RANGE = re.compile(r'(?P<pre>~|≈|about |around |roughly |approximately |approx\. |close to |typically |some )?'
                   r'(?P<a>' + NUM + r')(?P<plus>\+)?'
                   r'(?:\s*(?:t|MT|tonnes?|tons?|kg|m3|m³|cbm|sq\.?\s?ft)?\s*(?:-|–|—|to|and)\s*(?P<b>' + NUM + r'))?'
                   r'(?P<plus2>\+)?')
UNIT_RE = [
    ('other', re.compile(r"\s*containers?['’]?\s+worth\b", re.I)),   # "4-5 containers' worth"
    ('sheets', re.compile(r'\s*(?:(?:plywood|packing(?:-grade)?(?: ply)?|full|standard|flat-packed|of)\s+)?(?:sheets?|panels?|boards?)\b', re.I)),
    ('tonnes', re.compile(r'(?:\s*|-)(?:metric\s+)?(?:tonnes?|tonners?|tons?|MT|t)\b(?!/|\s*(?:–|-)\s*\d)', re.I)),
    ('kg', re.compile(r'\s*kg\b(?!\s*/|\s*per\s*(?:m|cubic|sheet)|\s+a\s+sheet|\s+each)', re.I)),
    ('sqft', re.compile(r'\s*(?:sq\.?\s?ft\.?|sqft|square\s+feet|ft²|ft2)\b', re.I)),
    ('m3', re.compile(r'\s*(?:m3|m³|cbm|cubic\s+met(?:re|er)s?)(?![\w/])', re.I)),
    ('crates', re.compile(r'\s*(?:(?:standard|medium|finished|equipment|built-up|ISPM-15)\s+){0,3}(?:crates|cases)\b', re.I)),
    ('pallets', re.compile(r'\s*(?:ISPM-15\s+)?pallets\b', re.I)),
]
THICK = re.compile(r'(?<![\d.,])(\d{1,2}(?:\.\d)?)(?:\s*(?:-|–|to)\s*(\d{1,2}(?:\.\d)?))?\s*(?:mm|millimet)', re.I)

VEH = re.compile(
    r"(?ix)"
    r"(?:\b(?:single|multi)[- ]axle\b(?:\s+(?:\d{2}\s*(?:-|–)?\s*(?:ft|foot|feet)\b|SXL|MXL|full-load|full-body|covered|trucks?|trailers?|lorry|bodies))*"
    r"|\b\d{2}(?:/\d{2})?\s*(?:-|–)?\s*(?:ft|foot|feet|footers?)\b\.?(?:\s+(?:/\s*\d{2}\s*(?:-|–)?\s*ft\b|single[- ]axle|multi[- ]axle|SXL|MXL|GP|HC|HQ|high[- ]cube|standard|general[- ]purpose|dry|full[- ]body|full[- ]truck(?:[- ]load)?|full[- ]load|full|container(?:\s+trucks?)?|box|FCL|FTL|trucks?|trailers?|lorry|bodies|truckload|load|covered|open|multi-axle|single-axle))*"
    r"|\b\d{2}\s*(?:'|’|′)(?:\s*/\s*\d{2}\s*(?:'|’|′))?(?:\s+(?:FCL|GP|HC|HQ|containers?|box))*"
    r"|\b(?:20|40|45)\s*(?:GP|HC|HQ|DV)\b"
    r"|\bmulti-axle\s+\d{2}-tonners?\b|\b\d{2}-tonners?\b"
    r"|\b(?:SXL|MXL)\b"
    r"|\b(?:full[- ]truck(?:[- ]?loads?)?|truck[- ]?loads?|part[- ]truck|half[- ]truck|FTL|FCL)\b"
    r"|\b(?:container\s+trucks?|trucks?|lorry|lorries|trailers?)\b"
    r"|\bcontainers?\b|\bbox\b(?=[^.]{0,40}m³|’s|'s)"
    r")")
FORKLIFT = re.compile(r'(?i)forklift|pallet truck|hand truck')

PART = re.compile(r'(?i)part[- ]?loads?|part[- ]truck|partial|half[- ]?(?:a\s+)?(?:\d{2}-ft\s+)?(?:truck|load)|half-loads|\bLCL\b|\bLTL\b|\bPTL\b|consolidat(?!ion yard)|trial|pilot|co-load|piggyback|shared trucks|smaller (?:orders|pulls|indents|volumes|drop)')
THRESH_BEFORE = re.compile(r'(?i)(?:under|below|above|over|less than|more than|upwards? of|from|at least|beyond|exceed\w*|cross(?:es)?(?: about)?|anything above|economical from|efficient from|start to work above|minimum of|touches)\s*(?:about |around |roughly |~)?$')
THRESH_AFTER = re.compile(r'(?i)^\S*\s*(?:upwards?|and above|or more|-plus|plus\b|\+ )')
ORDER = re.compile(r'(?i)ordering|at a time|offtake is between|sheet range|\brange\b|a month|per month|monthly|per week|consumes|packing job')
RATING = re.compile(r'(?i)payload|road limit|weight limit|\blimit\b|\bcap\b|ceiling|gross volume|internal volume|of its|rated|tare|max(?:imum)? gross|permitted|highway|for the USA|for Israel|lower of')
ILLUS = re.compile(r'(?i)\bwould\b|suppose|occupies|already exceeds|at this density|illustrative|dividing|÷|not a claim')
NONPLY = re.compile(r'(?i)\btiles?\b|porcelain|brass|granite blocks|matti\b|bags inside|forklift|transformer|pressure vessel|cylinder head|bogie|castings|kg/m³ (?:air-dry|at roughly)|\bof it\b|server racks?|rack movement|of timber for|reconstructed ship')
PERITEM = re.compile(r'(?i)^(?:-|\s)?(?:tonne|ton|t)\s+(?:crate|transformer|pressure|forklift|cylinder|vessel|point|assembl)|apiece|per crate|\beach\b|single base|point loads?|a sheet|per sheet|sheet weighs|cases above|\bstatic\b|\bdynamic\b|load ratings?|unit load|pallets? (?:up to|rated)|engineering loads')
MIXED = re.compile(r'(?i)mixed loads?\s*—\s*say|plus pallets')


def to_float(s):
    return float(s.replace(',', ''))


def decimals_half_unit(s):
    s = s.replace(',', '')
    if '.' in s:
        return 0.5 * 10 ** -len(s.split('.')[1])
    return 0.5


def classify_vehicle(v):
    """-> (vehicle_class listed value, detail key, kind, lengths, axle)"""
    s = v.lower()
    lengths = [int(x) for x in re.findall(r'(?<!\d)(\d{2})(?=\s*(?:/\s*\d{2}\s*)?(?:-|–)?\s*(?:ft\b|foot\b|feet\b|footer|\'|’|′|gp\b|hc\b|hq\b|dv\b)|/\d{2}\s*(?:-|–)?\s*ft)', s)]
    lengths += [int(x) for x in re.findall(r'(?<!\d)\d{2}/(\d{2})\s*(?:-|–)?\s*ft', s)]
    lengths = sorted(set(lengths))
    single = bool(re.search(r'single[- ]axle|\bsxl\b', s))
    multi = bool(re.search(r'multi[- ]axle|\bmxl\b', s))
    tonner = re.search(r'(\d{2})-tonner', s)
    axle = 'single' if single and not multi else 'multi' if multi and not single else ('conflict' if single and multi else None)
    truckish = bool(re.search(r'truck|lorr|trailer|axle|sxl|mxl|ftl|full[- ]?body|tonner|bodies|covered|open', s))
    containerish = bool(re.search(r'container|fcl|\bbox\b|(?<![a-z])gp\b|(?<![a-z])hc\b|(?<![a-z])hq\b|high[- ]cube|general[- ]purpose|(?<![a-z])dv\b|\'|’|′', s)) and not re.search(r'container\s+trucks?', s)
    if truckish and not re.search(r'\bfcl\b', s):
        containerish = False
    if not truckish and not containerish and lengths:
        containerish = all(l in (20, 40, 45) for l in lengths)
        truckish = not containerish
    if containerish:
        hc = bool(re.search(r'(?<![a-z])hc\b|(?<![a-z])hq\b|high[- ]cube', s))
        if lengths == [20]:
            return 'container-20ft', 'container-20ft', 'container', lengths, None
        if lengths == [40]:
            k = 'container-40hc' if hc else 'container-40ft'
            return k, k, 'container', lengths, None
        return 'other', 'container-unspecified' if not lengths else 'container-' + '/'.join(map(str, lengths)), 'container', lengths, None
    # truck
    if tonner and not lengths:
        det = 'truck-%s-axle' % axle if axle in ('single', 'multi') else 'truck-unspecified'
        return (det if axle in ('single', 'multi') else 'truck-unspecified'), det, 'truck', lengths, axle
    if len(lengths) == 1:
        L = lengths[0]
        if L == 32:
            if axle == 'single':
                return 'truck-32ft-sxl', 'truck-32ft-sxl', 'truck', lengths, axle
            if axle == 'multi':
                return 'truck-32ft-mxl', 'truck-32ft-mxl', 'truck', lengths, axle
            if axle == 'conflict':
                k = 'truck-32ft-sxl' if re.search(r'\bsxl\b', s) else 'truck-32ft-mxl' if re.search(r'\bmxl\b', s) else 'truck-32ft'
                return k, k, 'truck', lengths, axle
            return 'truck-unspecified', 'truck-32ft', 'truck', lengths, axle
        if L in (14, 17, 19, 20, 22, 24):
            det = 'truck-%dft' % L + ('-' + axle if axle in ('single', 'multi') else '')
            return 'truck-%dft' % L, det, 'truck', lengths, axle
        if 'trailer' in s or L == 40:
            return 'trailer', 'trailer-%dft' % L, 'truck', lengths, axle
        return 'other', 'truck-%dft' % L, 'truck', lengths, axle
    if len(lengths) > 1:
        if axle in ('single', 'multi'):
            return 'truck-%s-axle' % axle, 'truck-%s-%s-axle' % ('/'.join(map(str, lengths)), axle), 'truck', lengths, axle
        return 'truck-unspecified', 'truck-' + '/'.join(map(str, lengths)), 'truck', lengths, axle
    if axle in ('single', 'multi'):
        return 'truck-%s-axle' % axle, 'truck-%s-axle' % axle, 'truck', lengths, axle
    if 'trailer' in s:
        return 'trailer', 'trailer', 'truck', lengths, axle
    return 'truck-unspecified', 'truck-unspecified', 'truck', lengths, axle


def find_vehicles(text):
    out = []
    for m in VEH.finditer(text):
        v = m.group(0).strip()
        ctx = text[max(0, m.start() - 12):m.end() + 8]
        if FORKLIFT.search(ctx):
            continue
        if re.fullmatch(r'(?i)box', v):
            continue
        after = text[m.end():m.end() + 30].lower()
        if re.search(r'(?i)containers?$', v) and re.match(
                r"^(?:'s)?\s*(?:-)?\s*(?:floor|flooring|lining|load estimator|loading|weight guide|weights?\b|planning|conversions|re-flooring|repair|model|pitch|equivalent|ports?\b|traffic|gateway|yard|depot|freight station|corporation|calculators?|stuffing|economics|packs|parcels|28 mm)", after):
            continue
        if re.search(r'(?i)container-equivalent|per-container', text[max(0, m.start() - 4):m.end() + 12]):
            continue
        if re.search(r'(?i)containers?$', v) and re.match(r"^(?:['’]\s*|\s+)worth\b|^,\s*cooperage", after):
            continue
        if re.search(r'(?i)trucks?$', v) and re.match(r'^\s*(?:bodies|bed)\b', after):
            continue
        # skip bare lengths that are clearly not vehicles (e.g. "8' x 4'")
        if re.fullmatch(r"\d{1,2}\s*['’′]", v) and re.search(r"\d\s*['’′]?\s*x\s*\d", text[max(0, m.start() - 6):m.end() + 6]):
            continue
        if re.fullmatch(r"\d{2}\s*['’′]", v) and int(re.match(r'\d+', v).group(0)) not in (20, 40, 45):
            continue
        out.append((m.start(), m.end(), v))
    # merge alternatives joined by or / "/"
    merged = []
    for s, e, v in out:
        if merged:
            ps, pe, pv = merged[-1]
            gap = text[pe:s]
            if re.fullmatch(r'\s*(?:or|/|and|,)?\s*(?:a\s+)?', gap) and len(gap) <= 6:
                merged[-1] = (ps, e, text[ps:e])
                continue
        merged.append((s, e, v))
    return merged


def alternatives(vtext):
    """split merged vehicle phrase into alternatives with distinct classes"""
    parts = re.split(r'\s+or\s+|(?<=[A-Za-z)])\s*/\s*(?=\d{2}\s*(?:-|–)?\s*(?:ft|foot))|\s+and\s+|,\s+', vtext)
    classes = []
    for p in parts:
        c = classify_vehicle(p)
        if c[1] not in [x[1] for x in classes]:
            classes.append(c)
    return classes


def find_quantities(text):
    out = []
    for m in RANGE.finditer(text):
        a = m.group('a')
        if m.start() > 0 and (text[m.start() - 1].isdigit() or text[m.start() - 1] in '.,'):
            continue
        if re.search(r'[x×]\s*$', text[:m.start('a')]):
            continue
        tail = text[m.end():m.end() + 60]
        unit = None
        um = None
        for name, rx in UNIT_RE:
            mm = rx.match(tail)
            if mm:
                unit, um = name, mm
                break
        if not unit:
            continue
        low = to_float(a)
        high = to_float(m.group('b')) if m.group('b') else low
        if high < low:
            continue
        if unit == 'tonnes' and re.match(r'\s*t\b', tail) and not re.match(r'\s*t\b\s*(?:payload|–|-|of|$|[,.;)])', tail):
            continue
        if unit in ('sheets', 'crates', 'pallets') and low < 20:
            continue
        if unit == 'kg' and high < 1000:
            continue
        # thickness "18 mm" false positives are excluded because unit list lacks mm
        qs = m.start('a')
        qe = m.end() + um.end()
        qtext = text[qs:m.end()].strip()
        out.append({'start': qs, 'end': qe, 'num_end': m.end(), 'unit': unit, 'low': low, 'high': high,
                    'quantity': qtext + ('+' if m.group('plus') and not qtext.endswith('+') else ''),
                    'plus': bool(m.group('plus') or m.group('plus2')), 'a_raw': a, 'b_raw': m.group('b') or a,
                    'unit_text': um.group(0).strip(' -')})
    return out


def nearest_thickness(text, pos):
    best = None
    for m in THICK.finditer(text):
        a = float(m.group(1))
        b = float(m.group(2)) if m.group(2) else a
        if not (3 <= a <= 40):
            continue
        d = abs(m.start() - pos)
        if best is None or d < best[0]:
            best = (d, (a + b) / 2, m.group(0))
    return best


def thickness_after(text, q):
    """thickness stated right after the quantity ("sheets of 12 mm", "sheets at 18mm", "sheets of 8 x 4 x 12 mm")"""
    if q['unit'] not in ('sheets', 'sqft', 'tonnes', 'm3'):
        return None
    tail = text[q['num_end']:q['num_end'] + 60]
    m = re.match(r"(?i)^\s*(?:sq\.?\s?ft\.?|sheets?|panels?|boards?|tonnes?|m3|m³)?\s*(?:of|at|in)?\s*(?:[\w'’×.-]+\s+){0,4}?(\d{1,2}(?:\.\d)?)\s*mm", tail)
    if m and 3 <= float(m.group(1)) <= 40:
        return (0, float(m.group(1)), m.group(0).strip())
    return None


def sheet_area(text):
    m = re.search(r"(?i)\b(8|7|6)\s*['’]?\s*(?:ft)?\s*[x×]\s*(4|3)\b(?!\s*(?:x|×)\s*\d{2}\s*mm)", text)
    if m and (m.group(1), m.group(2)) != ('8', '4'):
        return int(m.group(1)) * int(m.group(2)) * 0.09290304
    return SHEET_M2


def clause_around(sentence, s, e):
    # clause delimited by ; — ( ) or ", " (comma+space)
    left = max(sentence.rfind(d, 0, s) for d in [';', '—', '(', ')', ', ', ': '])
    rights = [sentence.find(d, e) for d in [';', '—', '(', ')', ', ']]
    rights = [r for r in rights if r >= 0]
    right = min(rights) if rights else len(sentence)
    return sentence[left + 1 if left >= 0 else 0:right]


def qualifiers(sentence, q, vehicle_in_sentence):
    s, e = q['start'], q['end']
    clause = clause_around(sentence, s, e)
    before = sentence[max(0, s - 40):s]
    quals = []
    if THRESH_BEFORE.search(before) or THRESH_AFTER.search(sentence[q['end']:q['end'] + 14]):
        quals.append('threshold')
    if PART.search(clause) or (PART.search(sentence[:s]) and not re.search(r'(?i)full', clause)
                               and not re.search(r'(?i)full', sentence[max(0, s - 90):s])):
        quals.append('part-load')
    if ORDER.search(clause):
        quals.append('order-size')
    if RATING.search(clause) or re.search(r'(?i)^\s*(?:-|–)?\s*(?:tonne|ton|t)\s+payload', sentence[q['num_end']:q['num_end'] + 20]):
        quals.append('rating')
    if ILLUS.search(sentence):
        quals.append('illustrative')
    if NONPLY.search(sentence):
        quals.append('non-plywood')
    if PERITEM.search(sentence[q['num_end']:q['num_end'] + 30]) or PERITEM.search(clause):
        quals.append('per-item')
    if MIXED.search(clause) or MIXED.search(sentence[max(0, s - 40):e + 20]):
        quals.append('mixed-component')
    if q['unit'] in ('tonnes', 'kg') and q['high'] <= (12 if q['unit'] == 'tonnes' else 12000) \
            and re.search(r'(?i)crate|\bcases?\b|pallet|assembl|skid', sentence) \
            and not re.search(r'(?i)truck|trailer|lorry|axle|\bFTL\b|\bFCL\b|\d\s*(?:-|–)?\s*(?:ft|foot)\b|\bMT\b', sentence) \
            and not re.search(r'(?i)of (?:finished )?plywood|plywood and|of packing ply', clause):
        quals.append('per-item')
    return quals


def clip(sentence, s, e, limit=300):
    if len(sentence) <= limit:
        return sentence
    mid = (s + e) // 2
    a = max(0, min(mid - limit // 2, len(sentence) - limit))
    return sentence[a:a + limit]


# ----------------------------------------------------------------- record building
def page_records(rel, units):
    recs = []
    sentences_by_unit = {i: split_sentences(units[i]['text']) for i in range(len(units)) if units[i]['kind'] != 'row'}

    def neighbours(i, k):
        """previous and next sentence (text) for sentence k of unit i"""
        sents = sentences_by_unit[i]
        prev = sents[k - 1] if k > 0 else None
        nxt = sents[k + 1] if k + 1 < len(sents) else None
        u = units[i]
        if prev is None and u['kind'] == 'block' and i - 1 >= 0 and units[i - 1]['kind'] == 'block' \
                and units[i - 1].get('section') == u.get('section') and u['source'] != 'meta':
            ps = sentences_by_unit.get(i - 1) or []
            prev = ps[-1] if ps else None
        if nxt is None and u['kind'] == 'block' and i + 1 < len(units) and units[i + 1]['kind'] == 'block' \
                and units[i + 1].get('section') == u.get('section') and u['source'] != 'meta':
            ns = sentences_by_unit.get(i + 1) or []
            nxt = ns[0] if ns else None
        return prev, nxt

    for i, u in enumerate(units):
        if u['kind'] == 'row':
            cells = u['cells']
            header = u['header'] or []
            row_veh = []
            for ci, c in enumerate(cells):
                for vs, ve, v in find_vehicles(c):
                    row_veh.append((ci, v))
            for ci, c in enumerate(cells):
                qs = find_quantities(c)
                colh = header[ci] if ci < len(header) else ''
                if not qs and re.fullmatch(NUM, c or '') and re.search(r'(?i)ceiling|sheets|count', colh):
                    qs = [{'start': 0, 'end': len(c), 'num_end': len(c), 'unit': 'sheets', 'low': to_float(c),
                           'high': to_float(c), 'quantity': c, 'plus': False, 'a_raw': c, 'b_raw': c, 'unit_text': ''}]
                for q in qs:
                    cv = find_vehicles(c)
                    link = None
                    specific_row = [v for ci2, v in row_veh if ci2 != ci and classify_vehicle(v)[1] not in ('container-unspecified', 'truck-unspecified')]
                    if cv:
                        before = [x for x in cv if x[0] <= q['start']]
                        vv = (before[-1] if before else cv[0])[2]
                        link = 'same-cell'
                        if classify_vehicle(vv)[1] in ('container-unspecified', 'truck-unspecified') and specific_row:
                            vv, link = specific_row[0], 'same-row'
                    elif find_vehicles(colh):
                        vv = find_vehicles(colh)[0][2]
                        link = 'column-header'
                    elif row_veh:
                        vv = row_veh[0][1]
                        link = 'same-row'
                    elif find_vehicles(u['caption']):
                        vv = find_vehicles(u['caption'])[0][2]
                        link = 'caption'
                    else:
                        continue
                    rowtext = ' | '.join(cells)
                    th = thickness_after(c, q) or nearest_thickness(c, q['start']) or nearest_thickness(rowtext, 0) or nearest_thickness(colh, 0)
                    quals = qualifiers(c, q, True)
                    if re.search(r'(?i)payload|ceiling|volume|limit|road', colh + ' ' + cells[0] + ' ' + u.get('caption', '')) \
                            or re.search(r'(?i)^destination', header[0] if header else ''):
                        quals.append('rating')
                    recs.append(make_rec(rel, 'table', c, q, vv, link, th, quals, c, header=colh, rowtext=rowtext))
            continue
        sents = sentences_by_unit[i]
        ctx_q = u.get('question', '')
        for k, sent in enumerate(sents):
            qs = find_quantities(sent)
            if not qs:
                continue
            veh_here = find_vehicles(sent)
            prev, nxt = neighbours(i, k)
            for q in qs:
                link = None
                vv = None
                if veh_here:
                    # nearest by distance, prefer preceding
                    best = None
                    for vs, ve, v in veh_here:
                        if vs <= q['start'] <= ve:
                            d = 0
                        elif ve <= q['start']:
                            d = q['start'] - ve
                        else:
                            gap = sent[q['end']:vs]
                            d = (vs - q['end']) * (0.4 if re.search(r'(?i)(?:\bper|\bin an?|\bon an?|\binto an?)\s+(?:[\w-]+\s+){0,2}$', gap) and len(gap) < 70 else 1.5)
                        if best is None or d < best[0]:
                            best = (d, v)
                    vv, link = best[1], 'same-sentence'
                elif prev and find_vehicles(prev):
                    vv, link = find_vehicles(prev)[-1][2], 'previous-sentence'
                elif nxt and find_vehicles(nxt):
                    vv, link = find_vehicles(nxt)[0][2], 'next-sentence'
                elif u['kind'] == 'faq':
                    whole = ' '.join(x['text'] for x in units if x.get('group') == u['group'])
                    fv = find_vehicles(whole) or find_vehicles(ctx_q)
                    if fv:
                        vv, link = fv[0][2], 'same-faq-answer'
                if not vv:
                    continue
                block_text = u['text']
                th = thickness_after(sent, q) or nearest_thickness(sent, q['start'])
                th_src = 'sentence'
                if not th:
                    if u['kind'] == 'faq':
                        whole = ' '.join(x['text'] for x in units if x.get('group') == u['group'])
                        th = nearest_thickness(whole, 0)
                    else:
                        th = nearest_thickness(block_text, block_text.find(sent) + q['start'])
                    th_src = 'block'
                quals = qualifiers(sent, q, bool(veh_here))
                r = make_rec(rel, u['source'], sent, q, vv, link, th, quals, block_text)
                r['thickness_from'] = th_src if th else None
                if u['kind'] == 'faq':
                    r['faq_question'] = ctx_q
                recs.append(r)
    return recs


def make_rec(rel, source, sentence, q, vehicle, link, th, quals, block_text, header=None, rowtext=None):
    vclass_text = vehicle
    if re.fullmatch(r"(?i)\d{2}(?:/\d{2})?\s*(?:-|–)?\s*(?:ft|foot|feet)\.?|\d{2}\s*['’′]", vehicle.strip()) \
            and re.search(r'(?i)truck|lorry|trailer|axle|\bFTL\b|\bSXL\b|\bMXL\b', sentence) \
            and not re.search(r'(?i)container(?!\s+truck)|\bFCL\b|\bGP\b|\bHC\b|\bbox\b', sentence):
        vclass_text = vehicle + ' truck'
    alts = alternatives(vclass_text)
    vc, detail, kind, lengths, axle = alts[0]
    thickness = th[1] if th else None
    area = sheet_area(sentence)
    unit = q['unit']
    lo, hi = q['low'], q['high']
    t_lo = t_hi = s_lo = s_hi = None
    if unit == 'sheets':
        s_lo, s_hi = lo, hi
        if thickness:
            t_lo, t_hi = lo * sheet_kg(thickness, area) / 1000, hi * sheet_kg(thickness, area) / 1000
    elif unit == 'tonnes':
        t_lo, t_hi = lo, hi
    elif unit == 'kg':
        t_lo, t_hi = lo / 1000, hi / 1000
    elif unit == 'sqft':
        if thickness:
            t_lo = lo * SQFT_M2 * thickness / 1000 * DENSITY / 1000
            t_hi = hi * SQFT_M2 * thickness / 1000 * DENSITY / 1000
        s_lo, s_hi = lo / 32.0, hi / 32.0
    elif unit == 'm3':
        t_lo, t_hi = lo * DENSITY / 1000, hi * DENSITY / 1000
    elif unit == 'other':
        # N containers' worth: one 20 ft box on the site estimator's flat-stack layout holds
        # 2 stacks x 2,192 mm x 2.9768 m2 = 13.05 m3 of panels (thickness-independent) = 8.48 t at 650 kg/m3
        per_box_t = 2 * 2.192 * SHEET_M2 * DENSITY / 1000
        t_lo, t_hi = lo * per_box_t, hi * per_box_t
    if kind == 'container' and unit in ('tonnes', 'kg', 'm3') and RATING.search(sentence):
        quals = list(quals) + ['rating']
    if unit == 'kg' and hi < 5000:
        quals = list(quals) + ['per-item']
    if unit in ('tonnes', 'kg', 'm3') and thickness and t_lo is not None:
        s_lo, s_hi = t_lo * 1000 / sheet_kg(thickness, area), t_hi * 1000 / sheet_kg(thickness, area)
    rec = {
        'page': rel, 'source': source, 'text': clip(sentence, q['start'], q['end']),
        'vehicle': vehicle, 'vehicle_class': vc, 'thickness_mm': thickness,
        'quantity': q['quantity'], 'unit': unit, 'low': lo, 'high': hi,
        'class_detail': detail, 'vehicle_kind': kind, 'axle': axle,
        'alt_classes': [a[1] for a in alts] if len(alts) > 1 else [],
        'link': link, 'qualifiers': sorted(set(quals)), 'plus': q['plus'],
        'tonnes_low': round(t_lo, 3) if t_lo is not None else None,
        'tonnes_high': round(t_hi, 3) if t_hi is not None else None,
        'sheet_equiv_low': round(s_lo, 1) if s_lo is not None else None,
        'sheet_equiv_high': round(s_hi, 1) if s_hi is not None else None,
        'thickness_text': th[2] if th else None,
        'sheet_area_m2': round(area, 4), 'low_raw': q['a_raw'], 'high_raw': q['b_raw'],
        'unit_text': q.get('unit_text', ''),
    }
    if header is not None:
        rec['column_header'] = header
        rec['row_text'] = rowtext
    if unit == 'sheets' and not thickness:
        rec['thickness_mm'] = None
        rec['tonnes_note'] = 'thickness unknown'
    return rec


# ----------------------------------------------------------------- rules
EXCL_CAPACITY = {'threshold', 'part-load', 'order-size', 'illustrative', 'non-plywood', 'per-item'}


def is_capacity(r, allow_rating=False):
    q = set(r['qualifiers'])
    if q & EXCL_CAPACITY:
        return False
    if 'mixed-component' in q:
        return False
    if 'rating' in q and not allow_rating:
        return False
    return True


def fmt_range(a, b, nd=1):
    if a is None:
        return 'n/a'
    return ('%.*f' % (nd, a)) if abs(a - b) < 1e-9 else ('%.*f-%.*f' % (nd, a, nd, b))


def compatible(a, b, page_recs):
    if a['vehicle_kind'] != b['vehicle_kind']:
        return False
    if a['alt_classes'] or b['alt_classes']:
        # alternative vehicles: compatible only if some alternative matches
        sa = set(a['alt_classes'] or [a['class_detail']])
        sb = set(b['alt_classes'] or [b['class_detail']])
        if not sa & sb:
            return False
        return True

    def spec(r):
        L = re.findall(r'(\d{2}(?:/\d{2})?)(?:ft|hc)', r['class_detail'])
        return (L[0] if L else None, r['axle'] if r['axle'] in ('single', 'multi') else None,
                'hc' if r['class_detail'].endswith('40hc') else None)
    sa, sb = spec(a), spec(b)
    for x, y in zip(sa, sb):
        if x and y and x != y:
            return False
    # a length-only vehicle ("32-foot truck") and an axle-only vehicle ("multi-axle 22-tonner") are not the same vehicle
    if (sa[0] and not sa[1] and sb[1] and not sb[0]) or (sb[0] and not sb[1] and sa[1] and not sa[0]):
        return False
    generic = lambda s: s == (None, None, None)
    if generic(sa) != generic(sb):
        fams = {spec(r) for r in page_recs if r['vehicle_kind'] == a['vehicle_kind'] and not generic(spec(r))}
        if len(fams) != 1:
            return False
    return True


def rules(records):
    flags = []
    by_page = {}
    for r in records:
        by_page.setdefault(r['page'], []).append(r)

    # rule 1 - containers above loading-guide ceilings
    for r in records:
        if r['vehicle_kind'] != 'container' or r['alt_classes']:
            continue
        q = set(r['qualifiers'])
        if q & {'threshold', 'part-load', 'order-size', 'non-plywood', 'per-item', 'illustrative'}:
            continue
        cls = r['class_detail']
        if cls not in ('container-20ft', 'container-40ft', 'container-40hc'):
            continue
        if r['unit'] == 'sheets':
            t = r['thickness_mm'] or 6.0
            ceil = ceiling_capacity(cls, t)
            if ceil and r['high'] > ceil:
                flags.append({'rule': '1-container-capacity-ceiling', 'pages': [r['page']],
                              'detail': '%s: %s sheets%s in %s exceeds the loading guide capacity-only ceiling of %d sheets (%s mm) | "%s"' % (
                                  r['source'], r['quantity'], ' of %g mm' % r['thickness_mm'] if r['thickness_mm'] else ' (thickness unstated; thinnest 6 mm ceiling used)',
                                  cls, ceil, t, r['text'])})
            est = ceiling_estimator(cls, r['thickness_mm']) if r['thickness_mm'] else None
            if est and r['high'] > est and 'rating' not in q:
                flags.append({'rule': '1b-container-above-site-estimator', 'pages': [r['page']],
                              'detail': '%s: %s sheets of %g mm in %s exceeds the site estimator flat-stack count of %d (%.2f-%.2f t at 650 kg/m3) | "%s"' % (
                                  r['source'], r['quantity'], r['thickness_mm'], cls, est, r['tonnes_low'] or 0, r['tonnes_high'] or 0, r['text'])})
        elif r['tonnes_high'] is not None and 'rating' not in q:
            half = decimals_half_unit(r['high_raw']) / (1000 if r['unit'] == 'kg' else 1) * (DENSITY / 1000 if r['unit'] == 'm3' else 1)
            limit = C20_T_SPACE if cls == 'container-20ft' else C40_T_MAX
            if r['unit'] == 'sqft' and r['thickness_mm'] is None:
                continue
            if r['tonnes_high'] - half > limit:
                flags.append({'rule': '1-container-tonnage', 'pages': [r['page']],
                              'detail': '%s: %s %s (%s t) in %s is above %.2f t (%s) | "%s"' % (
                                  r['source'], r['quantity'], r['unit'], fmt_range(r['tonnes_low'], r['tonnes_high'], 2), cls, limit,
                                  '33 m3 fills the 20 ft box at 650 kg/m3' if cls == 'container-20ft' else '40 ft payload 26.5-26.7 t', r['text'])})

    # rule 2 - self-contradiction on the same page (same vehicle, tonnage equivalents differ >15%)
    seen = set()
    for page, recs in by_page.items():
        cap = [r for r in recs if r['tonnes_low'] is not None and is_capacity(r, allow_rating=r['vehicle_kind'] == 'truck')]
        for i in range(len(cap)):
            for j in range(i + 1, len(cap)):
                a, b = cap[i], cap[j]
                if a['text'] == b['text'] and a['quantity'] == b['quantity']:
                    continue
                if a['text'] == b['text'] and {a['unit'], b['unit']} & {'sqft', 'm3'} and {a['unit'], b['unit']} & {'tonnes', 'kg'}:
                    continue  # reported under rule 5
                if a['text'] == b['text'] and a['unit'] == b['unit'] and a['unit'] in ('tonnes', 'kg', 'm3') \
                        and re.search(r'\bor\b', a['text'][min(a['text'].find(a['quantity']), a['text'].find(b['quantity'])):max(a['text'].find(a['quantity']), a['text'].find(b['quantity']))]):
                    continue  # "9-tonne or 16-tonne" - stated alternatives, not a contradiction
                if not compatible(a, b, recs):
                    continue
                lo_hi = sorted([(a['tonnes_low'], a['tonnes_high'], a), (b['tonnes_low'], b['tonnes_high'], b)], key=lambda x: x[1])
                (l1, h1, r1), (l2, h2, r2) = lo_hi
                if l2 <= h1:
                    continue
                ratio = l2 / h1 if h1 else float('inf')
                if ratio <= 1.15:
                    continue
                key = (page, r1['source'], r1['quantity'], r1['text'], r2['source'], r2['quantity'], r2['text'])
                if key in seen:
                    continue
                seen.add(key)
                if {r1['source'], r2['source']} == {'faq', 'faq-jsonld'} and r1['quantity'] == r2['quantity']:
                    continue
                flags.append({'rule': '2-same-page-contradiction', 'pages': [page],
                              'detail': '%s "%s" (%s %s%s = %s t) vs %s "%s" (%s %s%s = %s t): gap x%.2f | A: "%s" | B: "%s"' % (
                                  r1['source'], r1['vehicle'], r1['quantity'], r1['unit'], ' @%g mm' % r1['thickness_mm'] if r1['thickness_mm'] and r1['unit'] in ('sheets', 'sqft') else '',
                                  fmt_range(l1, h1), r2['source'], r2['vehicle'], r2['quantity'], r2['unit'],
                                  ' @%g mm' % r2['thickness_mm'] if r2['thickness_mm'] and r2['unit'] in ('sheets', 'sqft') else '',
                                  fmt_range(l2, h2), ratio, r1['text'], r2['text'])})
        # 2b implied thickness when sheets and tonnes are paired without a thickness
        sh = [r for r in recs if r['unit'] == 'sheets' and r['thickness_mm'] is None and is_capacity(r, True)]
        tn = [r for r in recs if r['unit'] in ('tonnes', 'm3') and is_capacity(r, True)]
        for s in sh:
            for t in tn:
                if s['text'] != t['text'] or not compatible(s, t, recs):
                    continue
                t_lo, t_hi = t['tonnes_low'], t['tonnes_high']
                th_min = t_lo * 1000 / s['high'] / (SHEET_M2 * DENSITY) * 1000
                th_max = t_hi * 1000 / s['low'] / (SHEET_M2 * DENSITY) * 1000
                if th_min > 18 * 1.15 or th_max < 6 / 1.15:
                    flags.append({'rule': '2b-implied-thickness', 'pages': [page],
                                  'detail': '%s %s tonnes paired with %s sheets implies %.1f-%.1f mm sheets at 650 kg/m3 | "%s"' % (
                                      t['source'], t['quantity'], s['quantity'], th_min, th_max, s['text'])})

    # rule 3 - cross-page outliers per class_detail
    per_class = {}
    for r in records:
        if r['tonnes_low'] is None or r['alt_classes'] or not is_capacity(r, allow_rating=r['vehicle_kind'] == 'truck'):
            continue
        per_class.setdefault(r['class_detail'], {}).setdefault(r['page'], []).append(r)
    class_stats = {}
    for cls, pages in per_class.items():
        mids = []
        ranges = {}
        for p, rs in pages.items():
            lo = min(x['tonnes_low'] for x in rs)
            hi = max(x['tonnes_high'] for x in rs)
            ranges[p] = (lo, hi, rs)
            mids.append((lo + hi) / 2)
        if len(mids) < 4:
            class_stats[cls] = {'pages': len(mids), 'note': 'fewer than 4 pages - pairwise test (3b) instead of IQR'}
            plist = sorted(ranges)
            for x in range(len(plist)):
                for y in range(x + 1, len(plist)):
                    (l1, h1, r1), (l2, h2, r2) = sorted([ranges[plist[x]], ranges[plist[y]]], key=lambda z: z[1])
                    if l2 > h1 and h1 > 0 and l2 / h1 > 1.15:
                        flags.append({'rule': '3b-cross-page-small-class', 'pages': [r1[0]['page'], r2[0]['page']],
                                      'detail': '%s (only %d pages): %s t on %s vs %s t on %s (x%.2f apart) | %s || %s' % (
                                          cls, len(mids), fmt_range(l1, h1), r1[0]['page'], fmt_range(l2, h2), r2[0]['page'], l2 / h1,
                                          ' / '.join('%s %s %s%s: "%s"' % (z['source'], z['quantity'], z['unit'], ' @%g mm' % z['thickness_mm'] if z['thickness_mm'] and z['unit'] in ('sheets', 'sqft') else '', z['text'][:150]) for z in r1),
                                          ' / '.join('%s %s %s%s: "%s"' % (z['source'], z['quantity'], z['unit'], ' @%g mm' % z['thickness_mm'] if z['thickness_mm'] and z['unit'] in ('sheets', 'sqft') else '', z['text'][:150]) for z in r2))})
            continue
        qs = statistics.quantiles(mids, n=4, method='inclusive')
        q1, med, q3 = qs[0], qs[1], qs[2]
        class_stats[cls] = {'pages': len(mids), 'q1': round(q1, 2), 'median': round(med, 2), 'q3': round(q3, 2)}
        for p, (lo, hi, rs) in ranges.items():
            if hi < q1 or lo > q3:
                flags.append({'rule': '3-cross-page-outlier', 'pages': [p],
                              'detail': '%s: page range %s t vs site median %.1f t, IQR %.1f-%.1f t (n=%d pages) | %s' % (
                                  cls, fmt_range(lo, hi), med, q1, q3, len(mids),
                                  ' || '.join('%s %s %s%s: "%s"' % (x['source'], x['quantity'], x['unit'],
                                                                    ' @%g mm' % x['thickness_mm'] if x['thickness_mm'] and x['unit'] in ('sheets', 'sqft') else '', x['text'][:160]) for x in rs))})

    # rule 4 - vehicle-name contradictions
    for r in records:
        v = r['vehicle'].lower()
        parts = re.split(r'\s+or\s+|\s*/\s*|\s+and\s+|,\s*', v)
        for p in parts:
            single = re.search(r'single[- ]axle|\bsxl\b', p)
            multi = re.search(r'multi[- ]axle|\bmxl\b', p)
            if single and multi:
                flags.append({'rule': '4-vehicle-name-contradiction', 'pages': [r['page']],
                              'detail': '"%s" names both a single-axle and a multi-axle body | "%s"' % (r['vehicle'], r['text'])})
            if re.search(r'container truck', p) is None and re.search(r'\b(?:gp|hc|hq)\b', p) and re.search(r'truck|axle|trailer', p):
                flags.append({'rule': '4-vehicle-name-contradiction', 'pages': [r['page']],
                              'detail': '"%s" mixes container equipment codes with a truck body | "%s"' % (r['vehicle'], r['text'])})
    return flags, class_stats


def scan_name_contradictions(rel, units):
    """rule 4 over every text unit, with or without a quantity"""
    out = []
    for u in units:
        txt = u['text'] if u['kind'] != 'row' else ' | '.join(u['cells'])
        for vs, ve, v in find_vehicles(txt):
            for p in re.split(r'\s+or\s+|\s*/\s*|\s+and\s+|,\s*', v.lower()):
                if re.search(r'single[- ]axle|\bsxl\b', p) and re.search(r'multi[- ]axle|\bmxl\b', p):
                    out.append({'rule': '4-vehicle-name-contradiction', 'pages': [rel],
                                'detail': '%s: "%s" names both a single-axle and a multi-axle body | "%s"' % (
                                    u['source'], v, clip(txt, vs, ve))})
    return out


def rule5(records):
    flags = []
    by_page = {}
    for r in records:
        by_page.setdefault(r['page'], []).append(r)
    for page, recs in by_page.items():
        skip = {'order-size', 'per-item', 'rating', 'non-plywood', 'threshold'}
        vol = [r for r in recs if r['unit'] in ('sqft', 'm3') and not set(r['qualifiers']) & skip]
        ton = [r for r in recs if r['unit'] in ('tonnes', 'kg') and not set(r['qualifiers']) & skip]
        for v in vol:
            for t in ton:
                if v['text'] != t['text'] or v['source'] != t['source']:
                    continue
                if v['unit'] == 'sqft' and v['thickness_mm'] is None:
                    flags.append({'rule': '5-volume-vs-tonnes', 'pages': [page],
                                  'detail': 'sq ft %s paired with %s t but no thickness stated - cannot check | "%s"' % (v['quantity'], t['quantity'], v['text'])})
                    continue
                vl, vh = v['tonnes_low'], v['tonnes_high']
                tl, th = t['tonnes_low'], t['tonnes_high']
                if vl is None:
                    continue
                if vh < tl:
                    ratio = tl / vh
                elif th < vl:
                    ratio = vl / th
                else:
                    continue
                if ratio > 1.15:
                    flags.append({'rule': '5-volume-vs-tonnes', 'pages': [page],
                                  'detail': '%s %s%s = %s t at 650 kg/m3 vs stated %s %s (%s t): x%.2f apart | vehicle "%s" | "%s"' % (
                                      v['quantity'], v['unit'], ' of %g mm' % v['thickness_mm'] if v['unit'] == 'sqft' else '',
                                      fmt_range(vl, vh, 2), t['quantity'], t['unit'], fmt_range(tl, th, 2), ratio, t['vehicle'], v['text'])})
    return flags


def scan_site(dist):
    """(records, rule-4 name flags, pages scanned) for every .html file under dist."""
    records, name_flags, pages = [], [], 0
    for dp, dn, fns in os.walk(dist):
        dn[:] = sorted(d for d in dn if d != '.git')
        for fn in sorted(fns):
            if not fn.endswith('.html'):
                continue
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, dist).replace('\\', '/')
            units = extract_units(p)
            pages += 1
            records.extend(page_records(rel, units))
            name_flags.extend(scan_name_contradictions(rel, units))
    records.sort(key=lambda r: (r['page'], {'meta': 0, 'body': 1, 'table': 2, 'faq': 3, 'faq-jsonld': 4}[r['source']]))
    return records, name_flags, pages


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--dist', default=os.path.join(ROOT, 'dist'), help='built site to read (default: <repo>/dist)')
    parser.add_argument('--out', default=os.path.join(ROOT, 'load-figures'), help='output directory (default: <repo>/load-figures)')
    parser.add_argument('--load-pages', help='optional JSON list of page paths expected to carry load figures (coverage report)')
    args = parser.parse_args(argv)
    if not os.path.isdir(args.dist):
        parser.error('no built site at %s: run python build.py first' % args.dist)
    out_stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    records, name_flags, pages = scan_site(args.dist)
    flags, stats = rules(records)
    flags += rule5(records)
    seen = set()
    allflags = []
    for f in flags + name_flags:
        k = (f['rule'], tuple(f['pages']), f['detail'])
        k2 = (f['rule'], tuple(f['pages'])) if f['rule'].startswith('4') else k
        if k2 in seen and f['rule'].startswith('4'):
            continue
        seen.add(k2)
        allflags.append(f)
    rec_pages = sorted({r['page'] for r in records})
    coverage = {'pages_scanned': pages, 'pages_with_records': len(rec_pages)}
    if args.load_pages:
        with open(args.load_pages, encoding='utf-8') as handle:
            load_pages = json.load(handle)
        coverage['load_pages_without_records'] = sorted(set(load_pages) - set(rec_pages))
        coverage['record_pages_not_in_load_pages'] = sorted(set(rec_pages) - set(load_pages))
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, 'records.json'), 'w', encoding='utf-8') as handle:
        json.dump(records, handle, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, 'flags.json'), 'w', encoding='utf-8') as handle:
        json.dump({'flags': allflags, 'class_stats': stats, 'coverage': coverage}, handle, ensure_ascii=False, indent=1)
    from collections import Counter
    print('pages', pages, 'records', len(records), 'flags', len(allflags), file=out_stream)
    for rule, count in sorted(Counter(f['rule'] for f in allflags).items()):
        print('  %-36s %d' % (rule, count), file=out_stream)
    print('wrote', os.path.join(args.out, 'records.json'), 'and flags.json', file=out_stream)
    out_stream.detach()
    return 0


if __name__ == '__main__':
    sys.exit(main())
