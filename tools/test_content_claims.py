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


if __name__ == '__main__':
    unittest.main()
