"""Guard customer-facing specifications, certification claims and loading limits.

Run after python build.py. Checks include metadata/JSON-LD, not just visible prose.
"""
import html
import json
import math
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
        r"loaded to (?:the |your destination.s )?(?:road )?weight limit|weight question, not a volume|"
        # near-synonyms
        r"weight governs|payload (?:decides|governs|sets the)|"
        # tonnage and "to the weight cap" loading claims: a container is loaded WITHIN its limits
        r"(?:containers?|box(?:es)?)\b[^.]{0,20}loaded (?:to|at) (?:about )?\d|loaded (?:to|at) about \d|"
        r"(?:^|\bload(?:ed|s|ing)? )to the lower of the (?:ship-line )?payload|"
        r"(?:built|loading|loaded|load|planned) to (?:the |its |CSC and )?(?:container.s |destination )?(?:road )?(?:weight|payload)|"
        r"loaded to the limit", re.I)
    BOX_MENTION = re.compile(r"\b(20|40)[- ]?(?:ft|foot|feet)\b|\b(20|40)['’′]|\b(40) ?HC\b", re.I)
    GUIDE_SLUG = '20ft-container-plywood-loading-sheet-count-by-thickness-weight-limited'
    PLYWOOD_TONNAGE = re.compile(r"(\d+(?:\.\d+)?)(?:\s*(?:to|-|–|—)\s*(\d+(?:\.\d+)?))?\s*(?:tonnes|tons|MT|t)\s+of\s+"
                                 r"(?:(?:mixed|finished|bare|packing-grade|packing|commercial|sheet)\s+)*(?:plywood|ply\b|sheet stock)", re.I)
    PAIR_SHEETS = re.compile(r"(\d[\d,]*)\s*(?:(?:to|-|–|—)\s*(\d[\d,]*)\s*)?(?:full\s+)?sheets\s+(?:of\s+|at\s+)?(\d+(?:\.\d+)?)\s?mm", re.I)
    PAIR_TONNES = re.compile(r"(\d+(?:\.\d+)?)(?:\s*(?:to|-|–|—)\s*(\d+(?:\.\d+)?))?\s*(?:tonnes|tons|MT)\b", re.I)

    @classmethod
    def boxes_in(cls, sentence):
        return [(m.start(), next(g for g in m.groups() if g)) for m in cls.BOX_MENTION.finditer(sentence)]

    @classmethod
    def guide_planning(cls):
        """(20ft internal volume in m3, planning density in kg/m3), read from the loading guide itself."""
        page = cls.posts[cls.GUIDE_SLUG]['html']
        volume = float(re.search(r'20ft general purpose</td>\s*<td>(\d+(?:\.\d+)?) m', page).group(1))
        density = float(re.search(r'illustrative density of (\d+) kg', page).group(1))
        return volume, density

    def test_twenty_foot_plywood_tonnage_fits_the_box(self):
        # 33 m3 x 650 kg/m3 = 21.45 t is the most plywood a 20 ft box can hold at the guide's density,
        # whatever its payload; the guide rounds to one decimal, so the limit is 21.5 t.
        volume, density = self.guide_planning()
        limit = math.ceil(volume * density / 100) / 10
        for name, sentences in published_sentences().items():
            for sentence in sentences:
                boxes = self.boxes_in(sentence)
                for load in self.PLYWOOD_TONNAGE.finditer(sentence):
                    before = [box for at, box in boxes if at < load.start()]
                    box = before[-1] if before else (boxes[0][1] if boxes else None)
                    if box != '20':
                        continue
                    with self.subTest(page=name, sentence=sentence[:180]):
                        self.assertLessEqual(float(load.group(2) or load.group(1)), limit)

    def test_sheet_counts_agree_with_their_own_tonnage(self):
        # "800-900 sheets at 12 mm" is 18.6-20.9 t at the guide's density, not "8-9 tonnes".
        # The sheet range's mass must overlap the stated tonnage range widened by 15 per cent.
        _volume, density = self.guide_planning()
        for name, sentences in published_sentences().items():
            for sentence in sentences:
                sheets, tonnes = self.PAIR_SHEETS.search(sentence), self.PAIR_TONNES.search(sentence)
                if not (sheets and tonnes):
                    continue
                sheet_kg = 2.44 * 1.22 * float(sheets.group(3)) / 1000 * density
                mass_low = int(sheets.group(1).replace(',', '')) * sheet_kg / 1000
                mass_high = int((sheets.group(2) or sheets.group(1)).replace(',', '')) * sheet_kg / 1000
                stated_low, stated_high = float(tonnes.group(1)), float(tonnes.group(2) or tonnes.group(1))
                with self.subTest(page=name, sentence=sentence[:180]):
                    self.assertTrue(mass_high >= stated_low * 0.85 and mass_low <= stated_high * 1.15,
                                    f'{mass_low:.1f}-{mass_high:.1f} t of sheets against {stated_low}-{stated_high} t stated')

    # Rates are never published (owner decision 28 Jul 2026, 9d903cac; re-applied 8 Sep,
    # policy-and-image-decisions-2026-09-08.md). A rupee amount may stay only if it is not a CWI
    # trade price and cannot be combined with a sheet count or tonnage to derive one: the categories
    # that record keeps are third-party costs, cargo values, the cable-drum fumigation-risk figure and
    # macro statistics. Each surviving amount is listed with its reason.
    RUPEE_VALUE = re.compile(r'₹\s?\d|\bRs\.?\s?\d|\bINR\s?\d|\d[\d,.]*\+?\s?INR\b|\b(?:lakhs?|crores?)\b|'
                             r'\b\d[\d,.]*\s?rupees?\b|thousand rupees', re.I)
    REVIEWED_RUPEE_AMOUNTS = (
        ('blogs/post/bwr-vs-bwp-for-export-packing-when-mr-grade-will-fail-at-sea.html', 'costs a few thousand rupees per panel',
         'third-party NABL laboratory test fee'),
        ('blogs/post/fob-cochin-for-plywood-exporters-what-s-included-what-s-extra.html', 'save ₹4,000-₹8,000 per shipment in avoided storage',
         'third-party CFS storage charges avoided'),
        ('blogs/post/ispm-15-ht-stamp-validity-india-exporters-2026.html',
         "at a third-party treatment yard's rate of roughly 600 to 1,200 INR per cubic metre", 'third-party heat-treatment yard charge'),
        ('blogs/post/mundra-vs-pipavav-for-plywood-exporters-which-port-which-cost.html', '+₹400 to Mundra', 'third-party road haulage delta'),
        ('blogs/post/mundra-vs-pipavav-for-plywood-exporters-which-port-which-cost.html', '+₹350 to Mundra', 'third-party road haulage delta'),
        ('blogs/post/mundra-vs-pipavav-for-plywood-exporters-which-port-which-cost.html', '+₹900 to Mundra', 'third-party road haulage delta'),
        ('blogs/post/mundra-vs-pipavav-for-plywood-exporters-which-port-which-cost.html', '+₹600 to Mundra', 'third-party road haulage delta'),
        ('blogs/post/mundra-vs-pipavav-for-plywood-exporters-which-port-which-cost.html', 'cheaper by ₹15,000–₹20,000 per truck',
         'third-party line-haul difference'),
        ('blogs/post/mundra-vs-pipavav-for-plywood-exporters-which-port-which-cost.html', 'within ₹3,000–₹5,000 per box',
         'third-party reefer pricing difference'),
        ('blogs/post/mundra-vs-pipavav-for-plywood-exporters-which-port-which-cost.html', 'save ₹40,000+ per shipment',
         'third-party CHA routing saving'),
        # No CWI cargo value: Mundra's "loads under Rs 15 lakh of cargo value" beside its 25-tonne crossover
        # gave a unit price (about Rs 60/kg) and was removed on 15 Sep. An amount that combines with a CWI
        # quantity on the same page into a CWI unit price does not belong here, whatever its reason says.
        ('blogs/post/plywood-boxes-for-machinery-triple-wall-vs-reinforced-single-wall.html', 'Cargo value is ≥ ₹50 lakh',
         "the customer's cargo value"),
        ('blogs/post/plywood-cable-drum-flanges-is-10418-spec-sizing-sourcing-guide.html', 'not a risk worth saving ₹400 on',
         'the fumigation-risk figure the 8 Sep record keeps'),
        ('blogs/post/plywood-supply-to-coimbatore.html', '₹40,000 crore in knitwear exports', 'macro export statistic'),
        ('blogs/post/plywood-supply-to-delhi-ncr.html', '₹15,000 crore a year', 'macro export statistic'),
        ('blogs/post/plywood-supply-to-guntur.html', 'hundreds of crores of FCV leaf', 'macro trade statistic'),
        ('blogs/post/plywood-supply-to-guntur.html', '1.5 lakh bags', 'a count of bags, not money'),
        ('blogs/post/plywood-supply-to-karur.html', 'Rs 8,000-crore mark', 'macro export statistic'),
        ('blogs/post/plywood-supply-to-tiruppur.html', 'Rs 30,000 crore worth of knitwear', 'macro export statistic'),
        ('blogs/post/plywood-supply-to-tiruchirapalli.html', '₹2,200-₹2,800 each way', 'third-party highway tolls'),
        ('blogs/post/plywood-supply-to-vizag.html', '₹65,000 crore cumulative exports', 'macro export statistic'),
    )
    FOREIGN_MONEY = re.compile(r"(?:US\$|\$|\bUSD|\bEUR|€|\bAED|\bSAR|\bQAR|\bOMR|\bKWD|\bBHD|\bGBP|£)\s?\d[\d,.]*(?![\d,.]|\s?x\s?\d)"
                               r"|\b\d[\d,.]*\s?(?:USD|EUR|AED|SAR|QAR|OMR|KWD|BHD|GBP|dollars?|dirhams?|riyals?)\b", re.I)
    REVIEWED_FOREIGN_AMOUNTS = (
        ('blogs/post/mundra-vs-pipavav-for-plywood-exporters-which-port-which-cost.html',
         '$250–$320 ex-Mundra, $280–$340 ex-Pipavav', 'third-party ocean freight to Jebel Ali'),
        ('blogs/post/plywood-supply-to-hyderabad.html', '$5.9 billion in pharma exports', 'macro export statistic'),
        ('blogs/post/plywood-supply-to-jubail.html', 'SAR 525 billion', 'macro investment statistic'),
        ('blogs/post/plywood-supply-to-jubail.html', 'SAR 67.5 billion', 'macro investment statistic'),
        ('export/tanzania.html', 'subject to a USD 250 minimum', 'third-party pre-shipment inspection fee'),
    )

    @classmethod
    def money_outside_review(cls, page, sentence):
        """Money amounts left in a published sentence once its reviewed amounts are taken out."""
        remainder, used = sentence, set()
        for reviewed_page, amount, _reason in cls.REVIEWED_RUPEE_AMOUNTS + cls.REVIEWED_FOREIGN_AMOUNTS:
            if reviewed_page == page and amount in remainder:
                remainder = remainder.replace(amount, ' ')
                used.add((reviewed_page, amount))
        left = [m.group(0) for pattern in (cls.RUPEE_VALUE, cls.FOREIGN_MONEY) for m in pattern.finditer(remainder)]
        return left, used

    def test_no_money_trade_value_is_published(self):
        used = set()
        for name, sentences in published_sentences().items():
            for sentence in sentences:
                left, found = self.money_outside_review(name, sentence)
                used |= found
                if left:
                    with self.subTest(page=name, sentence=sentence[:180]):
                        self.fail(f'money amount outside the reviewed lists: {left}')
        reviewed = {(page, amount) for page, amount, _r in self.REVIEWED_RUPEE_AMOUNTS + self.REVIEWED_FOREIGN_AMOUNTS}
        self.assertEqual(reviewed - used, set(), 'a reviewed amount no longer appears; remove it from the list')

    # A table column headed by a rate, price or cost, or by a currency or price unit, carries no figures:
    # CWI rate cards read "On request". Two columns carry numbers that are not CWI prices.
    PRICED_HEADER = re.compile(r"\b(?:rates?|prices?|pricing|costs?)\b|₹|\bRs\b|\bINR\b|/\s?sq\.?\s?ft|per\s+sq\.?\s?ft|"
                               r"per sheet|per cft|/\s?cft|\bUSD\b|\$", re.I)
    REVIEWED_PRICED_COLUMNS = (
        ('blogs/post/mundra-vs-pipavav-for-plywood-exporters-which-port-which-cost.html', 'Cost delta (₹/MT)',
         'third-party road haulage deltas, the same amounts as the reviewed rupee list'),
        ('blogs/post/ispm-15-ht-stamp-validity-india-exporters-2026.html', 'Typical cost impact',
         'the figures are days and hours of delay, not money'),
    )

    @staticmethod
    def priced_numeric_cells(markup):
        """[(header, cell)] for every figure in a table column whose header names a price, rate, cost or currency."""
        found = []
        for table in re.findall(r'<table\b.*?</table>', markup, re.S | re.I):
            rows = [[' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', cell)).split())
                     for cell in re.findall(r'<t[hd]\b[^>]*>(.*?)</t[hd]>', row, re.S | re.I)]
                    for row in re.findall(r'<tr\b.*?</tr>', table, re.S | re.I)]
            if not rows:
                continue
            for column, header in enumerate(rows[0]):
                if ContentClaimsTests.PRICED_HEADER.search(header):
                    found.extend((header, row[column]) for row in rows[1:]
                                 if column < len(row) and re.search(r'\d', row[column]))
        return found

    def test_price_columns_in_tables_carry_no_figures(self):
        reviewed = {(page, header) for page, header, _reason in self.REVIEWED_PRICED_COLUMNS}
        used = set()
        for path in sorted((ROOT / 'dist').rglob('*.html')):
            name = path.relative_to(ROOT / 'dist').as_posix()
            for header, cell in self.priced_numeric_cells(path.read_text(encoding='utf-8')):
                if (name, header) in reviewed:
                    used.add((name, header))
                    continue
                with self.subTest(page=name, header=header, cell=cell):
                    self.fail('a price, rate or cost column carries a figure')
        self.assertEqual(reviewed - used, set(), 'a reviewed price column no longer exists; remove it from the list')

    def test_price_detectors_fail_a_deliberately_broken_copy(self):
        left, _used = self.money_outside_review('blogs/post/plywood-supply-to-jubail.html',
                                                'Industrial investment in Jubail crossed SAR 525 billion; 12 mm packing ply is USD 14.50 per sheet.')
        self.assertEqual(left, ['USD 14.50'])
        self.assertEqual(self.money_outside_review('blogs/post/plywood-supply-to-goa.html', 'EUR 1200x800 mm pallets.')[0], [])
        self.assertEqual(self.money_outside_review('blogs/post/plywood-supply-to-aurangabad.html',
                                                   'A full truckload (around ₹6-8 lakh of mixed packing ply).')[0], ['₹6', 'lakh'])
        broken = ('<table><thead><tr><th>Thickness</th><th>Rate (Rs/sq.ft)</th></tr></thead><tbody>'
                  '<tr><td>12 mm</td><td>33.50</td></tr><tr><td>18 mm</td><td>On request</td></tr></tbody></table>'
                  '<table><tr><th>Heavy CKD/SKD plywood crates</th><th>Chennai auto OEM lines</th></tr><tr><td>18 mm</td><td>2 t</td></tr></table>')
        self.assertEqual(self.priced_numeric_cells(broken), [('Rate (Rs/sq.ft)', '33.50')])
    SHEET_FIGURE = re.compile(r"(\d[\d,]*)\s*(?:(?:to|-|–|—)\s*(\d[\d,]*)\s*)?(?:full\s+)?sheets"
                              r"(?:\s+(?:of\s+)?(\d+(?:\.\d+)?)\s?mm)?", re.I)

    @classmethod
    def guide_ceilings(cls):
        """{box: {thickness: capacity-only ceiling}} read from the loading guide's own table, plus its formula.

        The guide states the rule: the smaller of payload / sheet weight and internal volume / sheet
        volume, at 650 kg/m3, for 2440 x 1220 mm sheets, 33 m3 / 28,000 kg (20ft) and 67 m3 / 26,500 kg
        (40ft). The formula is checked against every published row before it is used for other thicknesses."""
        page = cls.posts['20ft-container-plywood-loading-sheet-count-by-thickness-weight-limited']['html']
        rows = Rows()
        rows.feed(page)
        table = {}
        for row in rows.rows:
            fields = re.fullmatch(r'(\d+) mm ([\d.]+) kg ([\d,]+) ([\d,]+) ([\d,]+)', row)
            if fields:
                table[int(fields[1])] = {'20': int(fields[3].replace(',', '')), '40': int(fields[4].replace(',', ''))}

        def formula(box, thickness):
            volume = 2.44 * 1.22 * thickness / 1000
            space, payload = {'20': (33, 28000), '40': (67, 26500)}[box]
            return int(min(payload / (volume * 650), space / volume))
        for thickness, ceilings in table.items():
            for box, published in ceilings.items():
                assert formula(box, thickness) == published, (box, thickness, published)
        return table, formula

    def test_container_sheet_counts_stay_within_the_guide_ceilings(self):
        # Any sheet figure in a sentence that names a 20 ft or 40 ft box: above the thinnest published
        # row's ceiling for that box it fails outright ("1,800-2,200 sheets depending on thickness");
        # with a stated thickness it must not exceed that thickness's ceiling ("650 sheets of 18 mm").
        table, formula = self.guide_ceilings()
        thinnest = min(table)
        for name, sentences in published_sentences().items():
            for sentence in sentences:
                boxes = self.boxes_in(sentence)
                if not boxes:
                    continue
                for figure in self.SHEET_FIGURE.finditer(sentence):
                    before = [box for at, box in boxes if at < figure.start()]
                    box = before[-1] if before else boxes[0][1]
                    high = int((figure.group(2) or figure.group(1)).replace(',', ''))
                    limit = table[thinnest][box]
                    if figure.group(3):
                        limit = min(limit, formula(box, float(figure.group(3))))
                    with self.subTest(page=name, sentence=sentence[:180]):
                        self.assertLessEqual(high, limit, f'{high} sheets in a {box} ft box exceeds the guide ceiling {limit}')
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

    def test_loading_guide_keeps_its_search_title(self):
        # The article's headline gained "Payload and Space"; its <title> must stay the phrase
        # cf-live serves (103efa27), not collapse to "20ft Container Plywood Loading".
        page = (ROOT / 'dist/blogs/post/20ft-container-plywood-loading-sheet-count-by-thickness-weight-limited.html'
                ).read_text(encoding='utf-8')
        title = re.search(r'<title>([^<]*)</title>', page).group(1)
        self.assertEqual(title, '20ft Container Plywood Loading: Sheet Count by Thickness')
        self.assertLessEqual(len(title), 62)

    def test_pallet_article_headline_and_title_name_both_ceilings(self):
        page = (ROOT / 'dist/blogs/post/pallet-vs-loose-container-loading-plywood-exports.html').read_text(encoding='utf-8')
        self.assertEqual(re.search(r'<title>([^<]*)</title>', page).group(1),
                         'Pallet vs Loose Plywood Loading: Weight and Layout Ceilings')
        self.assertIn('>Pallet vs Loose Container Loading for Plywood: Weight and Layout Ceilings</h1>', page)
        self.assertNotIn('Weight-Limit Tradeoff', page)

    def test_worked_sheet_counts_state_the_layout_ceiling(self):
        pallet = ' '.join(published_sentences()['blogs/post/pallet-vs-loose-container-loading-plywood-exports.html'])
        self.assertIn('weight ceiling loaded loose is 26,500 ÷ 30 ≈ 883 sheets', pallet)
        self.assertIn('layout ceiling of about 564 sheets', pallet)

    # Owner confirmation, 10 Sep 2026: the group holds no MIL-spec, UN/Class 9 or FDA
    # certification. No page may name a defence unit as a customer, claim a defence or
    # ordnance track record, or imply dangerous-goods packaging. A sentence using one of
    # these terms passes only as an exact, reviewed sentence below, with the reason.
    DEFENCE_OR_DANGEROUS_GOODS = re.compile(
        r'ordnance|\bOF[BKT]\b|ammunition|defen[cs]e[- ](?:grade|spec|packing)|military|\bMIL[- ]|hazardous|'
        r'dangerous[- ]goods|Class[- ]?9|UN[- ]spec|FDA[- ]grade|Sukhoi|\bHAL\b|\bBEL\b|'
        # defence packing offers that avoid the words above ("defence dispatch boxes")
        r'dispatch box|defen[cs]e[^.]{0,40}(?:box|case|crate|packing|dispatch)|'
        r'(?:box|case|crate|packing)e?s?[^.]{0,30}defen[cs]e', re.I)
    # A defence packing OFFER anywhere in the sentence, however far apart the words are. A neutral
    # description of local industry ("... sub-assemblies all move in wooden cases") has no offer cue.
    DEFENCE_TERM = re.compile(r'defen[cs]e|ordnance|military', re.I)
    PACKING_NOUN = re.compile(r'\b(?:box|boxes|case|cases|crate|crates|packing|packag(?:e|es|ing)|pallets?|skids?)\b', re.I)
    OFFER_CUE = re.compile(r'\bwe (?:build|supply|offer|deliver|make|ship|quote|recommend|pick)\b|\btypical\b[^.]*\buse\b|'
                           r'\bpick\b|\brecommended\b|\bdefault for\b|\bsized for\b|\bbuilt to\b', re.I)
    REVIEWED_SENTENCES = {
        ('export/nigeria.html',
         'Nigeria requires SONCAP (Standards Organisation of Nigeria Conformity Assessment Programme) for plywood and other '
         'wood panels — they fall outside SON’s narrow exemption list (food, medicines, raw-material chemicals for '
         'manufacturers, military equipment, contraband, and most used goods), so the general rule applies.'):
            'quotes the import regulator’s exemption list; says nothing about our products',
        ('woods-we-use/venteak.html',
         'It is used for packing cases, tea-chest battens, ammunition boxes, plywood and veneer, door and window frames.'):
            'cited trade uses of the species',
        ('woods-we-use/venteak.html',
         'On fastening, there is no dedicated nailing rating in the sources, but its long service in packing cases, crates and '
         'ammunition boxes shows it holds nails and screws well enough in use — provided you work with well-seasoned material '
         'and pre-bore near ends and edges on the denser sections to avoid splitting.1'):
            'cited trade uses of the species',
        ('woods-we-use/venteak.html',
         'The standard references list benteak for packing cases, tea-chest battens, ammunition and explosive boxes, and wooden '
         'cases and crates, as well as class-I plywood, veneers and blockboard.1 That is a strong fit for anyone building export '
         'crates or panel-based packaging: it gives real strength and nail-holding at a weight below teak.'):
            'cited trade uses of the species',
        ('woods-we-use/venteak.html',
         'It saws and machines cleanly, it is peeled for class-I plywood and veneers, and it holds fastenings well enough for '
         'crates and ammunition boxes.'):
            'cited trade uses of the species',
        ('blogs/post/plywood-supply-to-chennai.html',
         "Defence and aerospace tier-1s feeding BEL and HAL use moisture-barrier lined crates; we build the plywood case to the "
         "buyer's drawing and moisture specification, and hold no military packing certification."):
            'describes local demand and states that we hold no military packing certification',
        ('blogs/post/plywood-supply-to-chennai.html',
         'We are not a UN-certified packaging manufacturer, so if the consignment needs a UN-marked Class-9 package, that '
         'certification has to come from a certified packer; we build the timber work to the drawing they issue.'):
            'states that we are not UN-certified',
        ('blogs/post/plywood-supply-to-hyderabad.html',
         "Exporters in the defence cluster at the city's edge ship in sealed crates with desiccant cavities; we build the timber "
         "case and the desiccant cavity to the buyer's drawing, and hold no military packing certification."):
            'states that we hold no military packing certification',
        ('blogs/post/plywood-supply-to-tiruchirapalli.html',
         'Ordnance Factory Tiruchirapalli (OFT) — small-arms production at Thiruvarambur.'):
            'names a local unit; states no relationship or packing claim',
        ('blogs/post/plywood-supply-to-tiruchirapalli.html',
         "We build to the buyer's drawing and hold no military packing certification."):
            'non-certification statement',
        ('blogs/post/plywood-supply-to-jabalpur.html',
         "We hold no military packing certification; any defence packing specification is certified by the buyer's approved packer."):
            'non-certification statement',
    }

    def is_defence_packing_offer(self, sentence):
        return bool(self.DEFENCE_TERM.search(sentence) and self.PACKING_NOUN.search(sentence)
                    and self.OFFER_CUE.search(sentence))

    def test_defence_offer_window_spans_the_whole_sentence_but_not_local_descriptions(self):
        # Offers the 40-character window cannot see, and descriptions it must leave alone.
        for offer in ('We build heavy bolted cases for defence vehicle sub-assemblies and support equipment programmes.',
                      'Pick BWR with Gurjan face for captive returnable packaging and long-life defence vehicle sub-assembly work.',
                      'Typical use: engineering outloads and anything the ordnance units around the city ship in crates.'):
            with self.subTest(offer=offer):
                self.assertTrue(self.is_defence_packing_offer(offer))
        neutral = ('Railway coach interior fit-out parts, defence vehicle sub-assemblies and support equipment all move '
                   'in bolted, ISPM-15 stamped wooden cases.')
        self.assertFalse(self.is_defence_packing_offer(neutral))

    def test_no_page_implies_military_or_dangerous_goods_packing_certification(self):
        seen = set()
        for name, sentences in published_sentences().items():
            for sentence in sentences:
                offer = (self.DEFENCE_TERM.search(sentence) and self.PACKING_NOUN.search(sentence)
                         and self.OFFER_CUE.search(sentence))
                if not (self.DEFENCE_OR_DANGEROUS_GOODS.search(sentence) or offer):
                    continue
                if (name, sentence) in self.REVIEWED_SENTENCES:
                    seen.add((name, sentence))
                    continue
                with self.subTest(page=name, sentence=sentence[:200]):
                    self.fail('defence, ordnance or dangerous-goods wording outside the reviewed sentences')
        self.assertEqual(set(self.REVIEWED_SENTENCES) - seen, set(), 'a reviewed sentence no longer exists; remove it')
        for city in ('chennai', 'hyderabad', 'tiruchirapalli', 'jabalpur'):
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
