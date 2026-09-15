"""Guard customer-facing specifications, certification claims and loading limits.

Run after python build.py. Checks include metadata/JSON-LD, not just visible prose.
"""
import html
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Rows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.current = []

    def handle_data(self, value):
        if self.current is not None:
            self.current.append(value)

    def handle_endtag(self, tag):
        if tag == 'tr' and self.current is not None:
            self.rows.append(' '.join(self.current))
            self.current = None


class ContentClaimsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        posts = json.loads((ROOT / 'content/blog/posts.json').read_text(encoding='utf-8'))
        cls.posts = {p['slug']: p for p in posts}
        cls.pages = {p.stem: p.read_text(encoding='utf-8')
                     for p in (ROOT / 'dist/blogs/post').glob('*.html')}
        if not cls.pages:
            raise AssertionError('Build dist before checking published claims')

    def test_no_unsupported_product_certification_in_any_published_surface(self):
        unsupported = re.compile(
            r'FDA[- ](?:grade|traceable|acceptable)|food[- ]contact[- ]safe|'
            r'Class[- ]?9 UN[- ]spec|EV battery.pack crates \(UN-spec\)|'
            r'MIL[- ]spec (?:sealed|moisture.barrier) crates</td>|'
            r'mil-spec heat-treated cases|certificates (?:that )?satisfy (?:USFDA|EMA)', re.I)
        for name, page in self.pages.items():
            with self.subTest(page=name):
                self.assertIsNone(unsupported.search(html.unescape(page)))

    def test_pharma_faq_does_not_conflate_plant_health_with_product_approval(self):
        for city in ('hyderabad', 'vizag'):
            page = self.pages['plywood-supply-to-' + city]
            self.assertNotIn('USFDA-acceptable', page)
            self.assertIn('does not certify pharmaceutical', page)
            self.assertIn('Packaging made wholly from processed plywood is exempt', page)
            for block in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', page, re.S):
                json.loads(block)
                self.assertNotRegex(block, r'FDA[- ](?:grade|traceable|acceptable)')

    def test_thin_board_product_rows_are_not_structural_container_floors(self):
        for slug, post in self.posts.items():
            if not slug.startswith('plywood-supply-to-'):
                continue
            rows = Rows()
            rows.feed(post['html'])
            for row in rows.rows:
                if (re.search(r'\b(?:6|8|9|10|12|14|15|16|18|20|21|25)\s*mm', row)
                        and re.search(r'container.{0,12}floor', row, re.I)):
                    with self.subTest(slug=slug, row=row):
                        self.assertRegex(row.lower(), r'lining|liner|dunnage|load.spreading|supplementary|sacrificial|28\s*mm')

    def test_replacement_floor_prose_cannot_reintroduce_known_thin_substitutes(self):
        for slug in ('pipavav', 'nashik', 'ludhiana', 'rourkela', 'manama', 'jeddah'):
            text = self.posts['plywood-supply-to-' + slug]['html']
            self.assertIn('28 mm', text)
        all_posts = '\n'.join(p['html'] for p in self.posts.values())
        for phrase in ('18 mm BWR is the standard call',
                       'packing-grade 18 mm sheet often does the job',
                       'we supply 18 mm plywood flooring panels'):
            self.assertNotIn(phrase, all_posts)

    def test_returns_search_description_matches_existing_claim_windows(self):
        page = (ROOT / 'dist/return-refund-policy.html').read_text(encoding='utf-8')
        self.assertNotIn('7-day returns', page)
        self.assertIn('within 3 days', page)
        self.assertIn('within 14 days', page)
        self.assertIn('No change-of-mind returns', page)

    def test_loading_table_respects_each_capacity_ceiling(self):
        page = self.posts['20ft-container-plywood-loading-sheet-count-by-thickness-weight-limited']['html']
        rows = Rows()
        rows.feed(page)
        count = 0
        for row in rows.rows:
            fields = re.fullmatch(r'(\d+) mm ([\d.]+) kg ([\d,]+) ([\d,]+) ([\d,]+)', row)
            if not fields:
                continue
            thickness = int(fields[1])
            panel_volume = 2.44 * 1.22 * thickness / 1000
            for sheets, payload, volume in zip(fields.groups()[2:], (28000, 26500, 26500), (33, 67, 76)):
                sheets = int(sheets.replace(',', ''))
                self.assertLessEqual(sheets * panel_volume, volume)
                self.assertLessEqual(sheets * panel_volume * 650, payload)
            count += 1
        self.assertEqual(count, 8)
        self.assertIn('upper bound, not a quantity that can necessarily be loaded', page)
        self.assertIn('does not, by itself, switch', page)
        for old in ('Past about 20 mm, the geometry flips', '~1,225 sheets', 'freight drops by close to 40%'):
            self.assertNotIn(old, page)

    # Weight alone never sets the sheet count, whatever container a sentence names. The site's
    # own estimator (assets/container-calculator.js) takes the lower of the weight and layout
    # ceilings, and a flat-stacked 40 ft box is layout-bound at every offered thickness at
    # 650 kg/m3 (12 mm: 728 by layout against 1,136 by weight). The loading guide only says
    # 26.5 t occupies about 40.8 m3, "below its gross internal volume". No qualifier, and no
    # timber-page exemption, excuses a claim that weight decides.
    WEIGHT_ALONE = re.compile(
        r"weighs? out|cubes? out|weighbridge sets|sets the sheet count|cube never|not (?:just )?the cube|"
        r"weight (?:alone )?decides|decides it, not volume|not (?:by )?volume|not (?:by )?space|kilograms, not cubic|"
        r"binding constraint is kilograms|(?<![/-])\bweight-limited\b(?! to volume-limited)|fills? up by weight|"
        r"weight first|payload first|with space (?:still showing|to spare)|set by weight|space the sheets take|"
        r"(?:reach|hit)\w*\s+(?:the|its|that|a)\s+(?:container'?s?\s+)?(?:permitted\s+)?(?:payload|weight)\b[^.]*?before|"
        r"loaded to (?:the |your destination.s )?(?:road )?weight limit|weight question, not a volume", re.I)
    LIGHTER_ADDS_SHEETS = re.compile(r"lighter[^.]*(?:more (?:usable )?sheets|adds? sheets)|"
                                     r"more (?:usable )?sheets[^.]*(?:before it hits|same booking)", re.I)
    ONLY_WHEN_WEIGHT_BINDS = re.compile(r"(?:only |)(?:when|where) weight (?:rather than the sheet layout )?is the binding limit", re.I)

    def test_no_page_says_weight_alone_sets_the_sheet_count(self):
        for name, sentences in published_sentences().items():
            for sentence in sentences:
                if self.WEIGHT_ALONE.search(sentence):
                    with self.subTest(page=name, sentence=sentence[:180]):
                        self.fail('loading claim says weight alone sets the count')
        everything = '\n'.join(s for sentences in published_sentences().values() for s in sentences)
        for old in (r'28 tonnes? (?:of cargo )?for a 40 ft', r'22-24 tonnes of packing-grade ply',
                    r'Sheet Count by Thickness \(Weight-Limited\)'):
            self.assertNotRegex(everything, old)

    def test_a_lighter_panel_adds_sheets_only_when_weight_binds(self):
        for name, sentences in published_sentences().items():
            for sentence in sentences:
                if sentence.endswith('?'):
                    continue        # a question ("Does a lighter core always mean more sheets?") claims nothing
                if self.LIGHTER_ADDS_SHEETS.search(sentence) and not self.ONLY_WHEN_WEIGHT_BINDS.search(sentence):
                    with self.subTest(page=name, sentence=sentence[:180]):
                        self.fail('lighter panel promised more sheets without the weight condition')

    def test_worked_sheet_counts_state_the_layout_ceiling(self):
        pallet = ' '.join(published_sentences()['blogs/post/pallet-vs-loose-container-loading-plywood-exports.html'])
        self.assertIn('weight ceiling loaded loose is 26,500 ÷ 30 ≈ 883 sheets', pallet)
        self.assertIn('layout ceiling of about 564 sheets', pallet)

    def test_no_page_implies_military_or_dangerous_goods_packing_certification(self):
        # Owner confirmation, 10 Sep 2026: no MIL-spec, UN/Class 9 or FDA certification.
        unsupported = re.compile(r'\bMIL[- ]?(?:spec|STD)\b|defen[cs]e[- ](?:spec|grade)\b|military packing standards?\b|'
                                 r'ammunition[- ]grade|OFB packing standard|Class[- ]?9 dangerous[- ]goods crates', re.I)
        for name, sentences in published_sentences().items():
            for sentence in sentences:
                with self.subTest(page=name):
                    self.assertIsNone(unsupported.search(sentence), sentence[:200])
        for city in ('chennai', 'hyderabad'):
            self.assertIn('hold no military packing certification',
                          ' '.join(published_sentences()['blogs/post/plywood-supply-to-' + city + '.html']))


class Surface(HTMLParser):
    """What a reader or crawler is told: visible text, meta content and JSON-LD strings."""
    BREAKS = {'p', 'li', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'br', 'figcaption', 'title'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip, self.ld = [], 0, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.ld = []
        elif tag in ('script', 'style'):
            self.skip += 1
        elif tag == 'meta' and attrs.get('content'):
            self.parts.extend(('\n', attrs['content'], '\n'))
        elif tag in self.BREAKS:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag == 'script' and self.ld is not None:
            def walk(value):
                if isinstance(value, dict):
                    for item in value.values():
                        walk(item)
                elif isinstance(value, list):
                    for item in value:
                        walk(item)
                elif isinstance(value, str):
                    self.parts.extend(('\n', value, '\n'))
            walk(json.loads(''.join(self.ld)))
            self.ld = None
        elif tag in ('script', 'style') and self.skip:
            self.skip -= 1
        elif tag in self.BREAKS:
            self.parts.append('\n')

    def handle_data(self, data):
        if self.ld is not None:
            self.ld.append(data)
        elif not self.skip:
            self.parts.append(data)


_SENTENCES = {}


def published_sentences():
    if not _SENTENCES:
        for path in sorted((ROOT / 'dist').rglob('*.html')):
            parser = Surface()
            parser.feed(path.read_text(encoding='utf-8'))
            text = ''.join(parser.parts)
            _SENTENCES[path.relative_to(ROOT / 'dist').as_posix()] = [
                s.strip() for line in text.split('\n') for s in re.split(r'(?<=[.!?])\s+', line) if s.strip()]
    return _SENTENCES


if __name__ == '__main__':
    unittest.main()
