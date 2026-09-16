"""Guard customer-facing specifications, certification claims and loading limits.

Run after python build.py. Checks include metadata/JSON-LD, not just visible prose. Set CWI_DIST to point
the checks of published pages at another built tree, such as a saved build from before a content change.
"""
import html
import json
import math
import os
import re
import statistics
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = Path(os.environ.get('CWI_DIST') or ROOT / 'dist')
sys.path.insert(0, str(Path(__file__).resolve().parent))
import load_figures as LF  # noqa: E402  tools/load_figures.py, reused by LoadFigureConsistencyTests


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
                     for p in (DIST / 'blogs/post').glob('*.html')}
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
        page = (DIST / 'return-refund-policy.html').read_text(encoding='utf-8')
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
        # 16 Sep: the triple-wall crate's "Cargo value is >= Rs 50 lakh" sat directly under this comment
        # and was the same shape -- a customer cargo value on a page that also published a CWI cost
        # premium. Hedged, and removed from here. Four more went with it: the CFS storage saving, the
        # treatment-yard rate per cubic metre, the cable-drum Rs 400 and the Salem-Trichy tolls. Each was
        # admitted as "a third party's money", which is true and is not sufficient: all four named a cost
        # inside something CWI quotes, so the reader could put them against a CWI quantity on the same page.
        ('blogs/post/plywood-supply-to-coimbatore.html', '₹40,000 crore in knitwear exports', 'macro export statistic'),
        ('blogs/post/plywood-supply-to-delhi-ncr.html', '₹15,000 crore a year', 'macro export statistic'),
        ('blogs/post/plywood-supply-to-guntur.html', 'hundreds of crores of FCV leaf', 'macro trade statistic'),
        ('blogs/post/plywood-supply-to-guntur.html', '1.5 lakh bags', 'a count of bags, not money'),
        ('blogs/post/plywood-supply-to-karur.html', 'Rs 8,000-crore mark', 'macro export statistic'),
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

    # NOTHING HERE GUARDED A RATIO UNTIL 16 SEP 2026, and that is the hole every sweep fell through.
    # The two reviewed lists above catch money. They cannot catch "Okoume sits about 15-25% above
    # commercial packing on price", which names no currency and still gives a competitor CWI's internal
    # price relationship -- one quote for either product unlocks the other. Eleven figures of this shape
    # were live on 16 Sep, on pages three previous sweeps had already passed.
    #
    # The rule this encodes: a percentage or multiple in the same sentence as a cost word needs a reason
    # on this list. Government and carrier rates have one. A relationship between two things CWI sells
    # does not, and is never publishable.
    # BOTH halves must be present, and the second is deliberately narrow. A percentage alone is not a
    # leak: the export guides are full of government duty and GST rates, which are the destination's
    # own published figures and must stay. What makes a ratio dangerous is being COMPARATIVE -- a
    # number saying one thing CWI sells costs more or less than another. The first version of this
    # rule also matched "Triple-wall" (a product name) and "1100 x 1200 mm" (a sheet size), which is
    # why the multiples below must sit within a clause of the word cost or price.
    RELATIVE_FIGURE = re.compile(r"\d+(?:[.,]\d+)?\s?(?:%|per\s?cent|percent)|"
                                 r"\b(?:twice|half again|three times)\b|"
                                 r"\b(?:doubles?|doubled|triples?|tripled|halves|halved)\b"
                                 r"(?=[^.]{0,60}\b(?:cost|price)\b)", re.I)
    COST_WORD = re.compile(r"\bcheaper\b|\bdearer\b|\bcostlier\b|more expensive|less expensive|"
                           r"cost premium|premium over|premium (?:is|of|above)|\bsaves?\b|\bsaving\b|"
                           r"reduces? (?:the )?(?:landed )?cost|adds? [^.]{0,30}cost|of panel cost|"
                           r"of the cost|landed cost|goes up by|above [^.]{0,40}on price|than road|"
                           r"\bdiscount\b|\bmarkup\b|\buplift\b", re.I)
    REVIEWED_RELATIVE_FIGURES = (
        ('blogs/post/ispm-15-ht-stamp-validity-india-exporters-2026.html', 'more than 20 percent of the solid-wood content',
         'a share of the timber in a crate, not of its price'),
        ('export/haiti.html', "That schedule\u2019s overall simple average is 4.9% of CIF value",
         "Haiti's own published tariff schedule; the buyer pays it to Haitian customs, and nothing about "
         'CWI price follows from it'),
        ('export/south-africa.html', 'Import VAT is 15%',
         'the South African statutory VAT rate and its Added Tax Value formula, both published by SARS'),
    )

    @classmethod
    def relative_outside_review(cls, page, sentence):
        """A ratio stated beside a cost word, unless this page has a recorded reason for it."""
        if not (cls.RELATIVE_FIGURE.search(sentence) and cls.COST_WORD.search(sentence)):
            return None, set()
        used = set()
        for reviewed_page, fragment, _reason in cls.REVIEWED_RELATIVE_FIGURES:
            if page.endswith(reviewed_page) and fragment in sentence:
                used.add((reviewed_page, fragment))
                return None, used
        return cls.RELATIVE_FIGURE.search(sentence).group(0), used

    def test_no_relative_cost_figure_is_published(self):
        """A percentage or multiple attached to cost is a price relationship, published or not in rupees."""
        used = set()
        for name, sentences in published_sentences().items():
            for sentence in sentences:
                left, found = self.relative_outside_review(name, sentence)
                used |= found
                if left:
                    with self.subTest(page=name, sentence=sentence[:180]):
                        self.fail(f'a cost ratio outside the reviewed list: {left}')
        reviewed = {(page, frag) for page, frag, _r in self.REVIEWED_RELATIVE_FIGURES}
        self.assertEqual(reviewed - used, set(), 'a reviewed ratio no longer appears; remove it from the list')

    # A table column headed by a rate, price or cost, or by a currency or price unit, carries no figures:
    # CWI rate cards read "On request". Two columns carry numbers that are not CWI prices.
    # 16 Sep 2026: this pattern used to stop at "rate/price/cost/currency", and the BWR-vs-BWP table
    # published "13-25 percent" and "55-73 percent" under a column headed "Premium over MR" for weeks.
    # The rate column beside it had been redacted to "On request", so the guard read the redacted column,
    # found no digit, and passed -- while the column holding the ratio was never inspected. A word that
    # names a DIFFERENCE between prices is a priced header; it is worth more to a competitor than the
    # price itself, because it needs only one quote to unlock.
    # "Premium" is two different words on this site. "Premium HD film-faced" and "premium packing"
    # describe a GRADE, and their columns hold thicknesses and sheet sizes; "Premium over MR" and
    # "Cost premium (vs ...)" describe a PRICE DIFFERENCE. Matching the bare word flagged eight
    # product tables and would have taught the next reader to ignore this test, so only the price
    # sense is matched -- "cost premium" arrives through `costs?` already.
    PRICED_HEADER = re.compile(r"\b(?:rates?|prices?|pricing|costs?|deltas?|savings?|discounts?|"
                               r"markups?|uplifts?|cheaper|dearer|costlier)\b|"
                               r"\bpremium\s+(?:over|vs\.?|versus|above)\b|"
                               r"₹|\bRs\b|\bINR\b|"
                               r"/\s?sq\.?\s?ft|per\s+sq\.?\s?ft|per sheet|per cft|/\s?cft|\bUSD\b|\$", re.I)
    # A ROW LABEL IS NOT A COLUMN HEADER, and it must be judged more narrowly. A header sits above a
    # column of like values, so "Cost" there means the column holds costs. A first cell sits beside a
    # row and is just as likely to NAME A PRODUCT: "Low-cost panel" labels a grade whose row holds
    # pour counts, and the bare word "cost" flagged it. What the transposed leak actually looked like
    # was "Cost premium (vs single-wall baseline)" -- a stated DIFFERENCE between prices. So a row
    # label qualifies only on an explicit price-difference phrase, a currency, or a price unit.
    PRICED_ROW_LABEL = re.compile(r"cost premium|price premium|premium\s+(?:over|vs\.?|versus|above)|"
                                  r"\b(?:deltas?|savings?|discounts?|markups?|uplifts?)\b|"
                                  r"cost per\b|price per\b|rate per\b|"
                                  r"₹|\bRs\b|\bINR\b|\bUSD\b|\$|"
                                  r"/\s?sq\.?\s?ft|per\s+sq\.?\s?ft|per sheet|per cft|/\s?cft", re.I)
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
            # A TABLE CAN BE TRANSPOSED, and one on this site was. The triple-wall crate comparison
            # ran its metrics down the first column -- "Cost premium (vs single-wall baseline)" was a
            # ROW LABEL, not a header -- so the loop above inspected zero columns on it and "+38-45%"
            # published unguarded. Read the first cell of every row as a header too.
            for row in rows[1:]:
                if len(row) < 2:
                    continue
                label = row[0]
                if ContentClaimsTests.PRICED_ROW_LABEL.search(label):
                    found.extend((label, cell) for cell in row[1:] if re.search(r'\d', cell))
        return found

    def test_price_columns_in_tables_carry_no_figures(self):
        reviewed = {(page, header) for page, header, _reason in self.REVIEWED_PRICED_COLUMNS}
        used = set()
        for path in sorted(DIST.rglob('*.html')):
            name = path.relative_to(DIST).as_posix()
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
        page = (DIST / 'blogs/post/20ft-container-plywood-loading-sheet-count-by-thickness-weight-limited.html'
                ).read_text(encoding='utf-8')
        title = re.search(r'<title>([^<]*)</title>', page).group(1)
        self.assertEqual(title, '20ft Container Plywood Loading: Sheet Count by Thickness')
        self.assertLessEqual(len(title), 62)

    def test_pallet_article_headline_and_title_name_both_ceilings(self):
        page = (DIST / 'blogs/post/pallet-vs-loose-container-loading-plywood-exports.html').read_text(encoding='utf-8')
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


_LOAD_FIGURES = {}


def site_load_figures():
    """(records, vehicle-name flags) from tools/load_figures.py over the built tree, read once per run."""
    if not _LOAD_FIGURES:
        records, names, _pages = LF.scan_site(str(DIST))
        _LOAD_FIGURES.update(records=records, names=names)
    return _LOAD_FIGURES['records'], _LOAD_FIGURES['names']


def published_guide_planning():
    """(20ft internal volume in m3, planning density in kg/m3) as the built loading guide states them."""
    page = (DIST / ('blogs/post/' + ContentClaimsTests.GUIDE_SLUG + '.html')).read_text(encoding='utf-8')
    volume = float(re.search(r'20ft general purpose</td>\s*<td>(\d+(?:\.\d+)?) m', page).group(1))
    density = float(re.search(r'illustrative density of (\d+) kg', page).group(1))
    return volume, density


class LoadFigureConsistencyTests(unittest.TestCase):
    """Load figures checked against each other: across sentences, surfaces, pages and vehicle classes.

    ContentClaimsTests compares a sheet count with a tonnage only inside one sentence and reads only the
    plural units. These tests reuse tools/load_figures.py, which links every load figure on the built site
    to its vehicle, thickness and tonnage at the loading guide's 650 kg/m3, and marks the figures that are
    not a vehicle load (thresholds, part-loads, order sizes, ratings, per-crate weights, other cargo).
    Set CWI_DIST to run them against another built tree, such as the build from before a content change.
    """
    LOW, HIGH = 0.85, 1.15      # the tolerance test_sheet_counts_agree_with_their_own_tonnage already allows
    # The site's own anchor puts neighbouring truck classes about x1.35 apart (Kota: 32 ft single-axle
    # 15-16 MT, 32 ft multi-axle 21 MT), so a figure more than x1.3 from its class median is another vehicle.
    CLASS_BAND = 1.3
    NOT_A_LOAD = frozenset(['threshold', 'part-load', 'order-size', 'illustrative', 'non-plywood', 'per-item',
                            'mixed-component'])

    @classmethod
    def setUpClass(cls):
        cls.records, cls.name_flags = site_load_figures()
        if not cls.records:
            raise AssertionError('Build dist before checking published load figures')

    @staticmethod
    def vehicle_load(record):
        return record['tonnes_low'] is not None and LF.is_capacity(record, allow_rating=record['vehicle_kind'] == 'truck')

    @staticmethod
    def describe(record):
        thickness = ' of %g mm' % record['thickness_mm'] if record['unit'] in ('sheets', 'sqft') and record['thickness_mm'] else ''
        tonnes = ' = %.1f-%.1f t' % (record['tonnes_low'], record['tonnes_high']) if record['tonnes_low'] is not None else ''
        return '%s "%s": %s %s%s%s | %s' % (record['source'], record['vehicle'], record['quantity'],
                                            record.get('unit_text') or record['unit'], thickness, tonnes, record['text'][:160])

    @staticmethod
    def synthetic_records(body):
        markup = ('<html><head><meta name="description" content="Synthetic page."></head><body><main>%s</main>'
                  '</body></html>' % body)
        return LF.page_records('synthetic.html', LF.extract_units_from_html(markup))

    @staticmethod
    def stated_tonnage(record):
        return record['unit'] in ('tonnes', 'kg', 'm3', 'other')

    SINGULAR_UNIT = re.compile(r'(?:metric\s+)?(?:tonne|ton|tonner|MT|t)', re.I)

    @classmethod
    def singular_tonnage(cls, record):
        return record['unit'] == 'tonnes' and bool(cls.SINGULAR_UNIT.fullmatch(record.get('unit_text') or ''))

    @classmethod
    def disagreements(cls, records, stated, same_text):
        """(sheet figure, stated figure) pairs on one page, for compatible vehicles, whose tonnages disagree.

        stated(record) picks the other side of each pair; same_text=False leaves out a pair inside one sentence
        or one table cell, which test_sheet_counts_agree_with_their_own_tonnage already reads."""
        by_page, found, seen = {}, [], set()
        for record in records:
            if cls.vehicle_load(record):
                by_page.setdefault(record['page'], []).append(record)
        for recs in by_page.values():
            for sheet in (r for r in recs if r['unit'] == 'sheets'):
                for other in (r for r in recs if r['unit'] != 'sheets' and stated(r)):
                    if not same_text and (sheet['source'], sheet['text']) == (other['source'], other['text']):
                        continue
                    if {sheet['source'], other['source']} == {'faq', 'faq-jsonld'}:
                        continue        # an answer's JSON-LD copy is checked as a surface of its own
                    if not LF.compatible(sheet, other, recs):
                        continue
                    if (sheet['tonnes_high'] >= other['tonnes_low'] * cls.LOW
                            and sheet['tonnes_low'] <= other['tonnes_high'] * cls.HIGH):
                        continue
                    key = (sheet['page'], sheet['source'], sheet['text'], sheet['quantity'],
                           other['source'], other['text'], other['quantity'])
                    if key not in seen:
                        seen.add(key)
                        found.append((sheet, other))
        return found

    def test_sheet_and_tonnage_figures_agree_across_sentences_faq_answers_and_table_cells(self):
        """Gap (a): a sheet count and a tonnage for one vehicle were compared only inside a single sentence.

        Split across sentences or list items ("32 ft single-axle for full loads (~440 sheets of 12 mm)" beside
        "a single-driver 20-ton truck"), between the body and an FAQ answer ("full truckloads of 4-5 containers'
        worth of sheets" against "a full single-axle truck (about 600-700 sheets of 12 mm)"), or across the cells
        of one table row, the two figures were never set against each other."""
        broken = self.synthetic_records(
            '<h2>Lane</h2><p>A 32-ft single-axle truck carries about 15 tonnes of plywood.</p>'
            '<table><thead><tr><th>Vehicle</th><th>Capacity</th><th>Sheets</th></tr></thead><tbody>'
            '<tr><td>32-ft single-axle</td><td>15 tonnes</td><td>1,000 sheets of 12 mm</td></tr></tbody></table>'
            '<h2>FAQ</h2><h3>How much fits in one truck?</h3><p>One 32-ft single-axle truck takes about 1,000 sheets of 12 mm.</p>')
        pairs = {(sheet['source'], other['source']) for sheet, other in self.disagreements(broken, self.stated_tonnage, False)}
        self.assertIn(('table', 'table'), pairs, 'two cells of one table row')
        self.assertIn(('faq', 'body'), pairs, 'an FAQ answer against the body')
        consistent = self.synthetic_records(
            '<h2>Lane</h2><p>A 32-ft single-axle truck carries about 15 tonnes of plywood.</p>'
            '<table><thead><tr><th>Vehicle</th><th>Capacity</th><th>Sheets</th></tr></thead><tbody>'
            '<tr><td>32-ft single-axle</td><td>15 tonnes</td><td>650 sheets of 12 mm</td></tr></tbody></table>'
            '<h2>FAQ</h2><h3>How much fits in one truck?</h3><p>One 32-ft single-axle truck takes about 650 sheets of 12 mm.</p>')
        self.assertEqual(self.disagreements(consistent, self.stated_tonnage, False), [])
        for sheet, other in self.disagreements(self.records, self.stated_tonnage, False):
            with self.subTest(page=sheet['page'], sheets=sheet['text'][:100], stated=other['text'][:100]):
                self.fail('sheet figure disagrees with the tonnage stated elsewhere for the same vehicle: %s || %s'
                          % (self.describe(sheet), self.describe(other)))

    AREA_VOLUME_SKIP = frozenset(['order-size', 'per-item', 'rating', 'non-plywood', 'threshold', 'part-load',
                                  'illustrative', 'mixed-component'])

    @classmethod
    def area_volume_disagreements(cls, records):
        """(sq ft or m3 figure, tonnage, reason) on one page, in one sentence or for compatible vehicles."""
        by_page, found = {}, []
        for record in records:
            if not set(record['qualifiers']) & cls.AREA_VOLUME_SKIP:
                by_page.setdefault(record['page'], []).append(record)
        for recs in by_page.values():
            for measure in (r for r in recs if r['unit'] in ('sqft', 'm3')):
                for tonnage in (r for r in recs if r['unit'] in ('tonnes', 'kg')):
                    together = (measure['source'], measure['text']) == (tonnage['source'], tonnage['text'])
                    if not together and ({measure['source'], tonnage['source']} == {'faq', 'faq-jsonld'}
                                         or not LF.compatible(measure, tonnage, recs)):
                        continue
                    if measure['tonnes_low'] is None:
                        if together:
                            found.append((measure, tonnage, 'an area paired with tonnes must state the thickness'))
                        continue
                    if (measure['tonnes_high'] >= tonnage['tonnes_low'] * cls.LOW
                            and measure['tonnes_low'] <= tonnage['tonnes_high'] * cls.HIGH):
                        continue
                    found.append((measure, tonnage, '%.1f-%.1f t at %g kg/m3' % (
                        measure['tonnes_low'], measure['tonnes_high'], LF.DENSITY)))
        return found

    def test_area_and_volume_figures_agree_with_their_tonnage(self):
        """Gap (b): square feet and cubic metres were never converted to weight.

        "Full-load orders of 18-22 tonnes (roughly 9,000-11,000 sq.ft of 18 mm plywood)" is 9.8-12.0 t at
        650 kg/m3 and the stated 18 mm, not 18-22 t; "12-15 m3" on a truck said to carry 20 tonnes is 7.8-9.8 t."""
        self.assertEqual(published_guide_planning()[1], LF.DENSITY, 'the detector converts at the guide density')
        broken = self.synthetic_records(
            '<p>A 32-ft single-axle truck suits full-load orders of 18-22 tonnes (roughly 9,000-11,000 sq.ft of 18 mm plywood).</p>'
            '<p>A full 22-ft truck carries 12-15 m³ of plywood. That 22-ft truck carries about 20 tonnes of plywood.</p>')
        self.assertEqual(sorted(m['unit'] for m, _t, _why in self.area_volume_disagreements(broken)), ['m3', 'sqft'])
        consistent = self.synthetic_records(
            '<p>A 32-ft single-axle truck suits full-load orders of 10-12 tonnes (roughly 9,000-11,000 sq.ft of 18 mm plywood).</p>'
            '<p>A full 22-ft truck carries 12-15 m³ of plywood, about 8-9 tonnes.</p>')
        self.assertEqual(self.area_volume_disagreements(consistent), [])
        for measure, tonnage, why in self.area_volume_disagreements(self.records):
            with self.subTest(page=measure['page'], figure=measure['text'][:120]):
                self.fail('%s: %s || %s' % (why, self.describe(measure), self.describe(tonnage)))

    TONNAGE_ANY = re.compile(r"(\d+(?:\.\d+)?)(?:\s*(?:to|-|–|—)\s*(\d+(?:\.\d+)?))?\s*-?\s*"
                             r"((?:metric\s+)?(?:tonnes?|tonners?|tons?|MT|t))\b(?![/’'-]\w)", re.I)
    PLYWOOD_TONNAGE_ANY = re.compile(TONNAGE_ANY.pattern + r"\s+(?:payload\s+)?of\s+"
                                     r"(?:(?:mixed|finished|bare|packing-grade|packing|commercial|sheet)\s+)*(?:plywood|ply\b|sheet stock)", re.I)
    RATING_AFTER = re.compile(r"\s*(?:payload|cap|limit|ceiling|rating)\b(?!\s+of\s+(?:plywood|ply\b))", re.I)
    COUNTERFACTUAL = re.compile(r"\bwould (?:need|take|require)\b|\bagainst its\b", re.I)

    def test_singular_and_abbreviated_tonnage_units_are_checked(self):
        """Gap (c): the tonnage checks read 'tonnes' and 'tons' only (and 'MT' or 't' only before "of plywood").

        A load written with the singular 'tonne' or 'ton', or as 't' or 'MT' ("a single-driver 20-ton truck",
        "32 ft / 16 MT"), was never compared with a sheet count, and "a 28-tonne payload of plywood" in a
        20 ft box was never held to the 21.5 t that fills its 33 m3."""
        for phrase, value in (('a 20-tonne truck', '20'), ('16 t of plywood', '16'), ('32 ft / 9 MT', '9'),
                              ('a single-driver 20-ton truck', '20'), ('a 22-tonner', '22')):
            with self.subTest(phrase=phrase):
                self.assertEqual(self.TONNAGE_ANY.search(phrase).group(1), value)
        self.assertEqual(self.PLYWOOD_TONNAGE_ANY.search('In a 20 ft box, a 28-tonne payload of plywood').group(1), '28')
        for body in ('<p>A 9 MT 22-ft truck carries 700 sheets of 12 mm.</p>',
                     '<ul><li><strong>Transit time:</strong> 14-18 hours door-to-door for a single-driver 20-ton truck.</li>'
                     '<li><strong>Vehicle:</strong> 32 ft single-axle for full loads (~440 sheets of 12 mm).</li></ul>'):
            with self.subTest(synthetic=body[:60]):
                self.assertEqual(len(self.disagreements(self.synthetic_records(body), self.singular_tonnage, True)), 1)
        # every page: a singular or abbreviated tonnage against the sheet figures for the same vehicle
        for sheet, other in self.disagreements(self.records, self.singular_tonnage, True):
            with self.subTest(page=sheet['page'], sheets=sheet['text'][:100], stated=other['text'][:100]):
                self.fail('sheet figure disagrees with a tonnage written "%s": %s || %s'
                          % (other['unit_text'], self.describe(sheet), self.describe(other)))
        # every sentence: the same two checks ContentClaimsTests makes, with the unit spellings they miss
        volume, density = published_guide_planning()
        limit = math.ceil(volume * density / 100) / 10
        for name, sentences in published_sentences().items():
            for sentence in sentences:
                sheets = ContentClaimsTests.PAIR_SHEETS.search(sentence)
                loads = [m for m in self.TONNAGE_ANY.finditer(sentence)
                         if not self.RATING_AFTER.match(sentence, m.end())]
                if sheets and loads:
                    sheet_kg = LF.sheet_kg(float(sheets.group(3)))
                    mass_low = int(sheets.group(1).replace(',', '')) * sheet_kg / 1000
                    mass_high = int((sheets.group(2) or sheets.group(1)).replace(',', '')) * sheet_kg / 1000
                    stated_low, stated_high = float(loads[0].group(1)), float(loads[0].group(2) or loads[0].group(1))
                    with self.subTest(page=name, sentence=sentence[:180]):
                        self.assertTrue(mass_high >= stated_low * self.LOW and mass_low <= stated_high * self.HIGH,
                                        f'{mass_low:.1f}-{mass_high:.1f} t of sheets against {stated_low}-{stated_high} t stated')
                if self.COUNTERFACTUAL.search(sentence):
                    continue        # "a 28-tonne payload of plywood would need about 43 m3 against its 33 m3"
                boxes = ContentClaimsTests.boxes_in(sentence)
                for load in self.PLYWOOD_TONNAGE_ANY.finditer(sentence):
                    before = [box for at, box in boxes if at < load.start()]
                    box = before[-1] if before else (boxes[0][1] if boxes else None)
                    if box == '20':
                        with self.subTest(page=name, sentence=sentence[:180]):
                            self.assertLessEqual(float(load.group(2) or load.group(1)), limit)

    BAND_LABEL = {'truck-up-to-24ft': '19-24 ft truck', 'truck-32ft-sxl': '32 ft single-axle',
                  'truck-32ft-mxl': '32 ft multi-axle', 'truck-32ft': '32 ft truck, axle not named',
                  'container-20ft': '20 ft container', 'container-40ft': '40 ft container', 'container-40hc': '40 ft high-cube'}

    @classmethod
    def band_class(cls, record):
        detail = record['class_detail']
        if detail in cls.BAND_LABEL:
            return detail
        short = re.fullmatch(r'truck-(\d{2}(?:/\d{2})*)(?:ft)?(?:-single|-multi)?(?:-axle)?', detail)
        if short and all(19 <= int(length) <= 24 for length in short.group(1).split('/')):
            return 'truck-up-to-24ft'
        return None     # an axle with no length, or no vehicle size at all, names no class

    @classmethod
    def class_bands(cls, records):
        """{class: (low t, high t, pages)}: the median of each page's tonnage range for the class, x/÷ CLASS_BAND.

        A 32 ft truck whose axle is not named may be either body, so its band runs from the single-axle low
        to the multi-axle high."""
        ranges = {}
        for record in records:
            key = cls.band_class(record)
            if key and not record['alt_classes'] and cls.vehicle_load(record):
                low, high = ranges.setdefault(key, {}).get(record['page'], (math.inf, -math.inf))
                ranges[key][record['page']] = (min(low, record['tonnes_low']), max(high, record['tonnes_high']))
        medians = {key: statistics.median((low + high) / 2 for low, high in pages.values()) for key, pages in ranges.items()}
        bands = {}
        for key, median in medians.items():
            around = [medians[c] for c in ('truck-32ft-sxl', 'truck-32ft-mxl') if c in medians] if key == 'truck-32ft' else []
            around = around or [median]
            bands[key] = (min(around) / cls.CLASS_BAND, max(around) * cls.CLASS_BAND, len(ranges[key]))
        return bands

    def test_load_figures_for_one_vehicle_class_agree_across_pages(self):
        """Gap (d): each page was checked on its own, so one vehicle class could carry any figure.

        A 22-ft truck was "around 6 tonnes" on one page and "1,000-1,200 sheets of 12 mm" (23-28 t) on another;
        a 32 ft single-axle ran from 9 t to 25 t; a 32-foot truck "roughly 28-30 tonnes"; a 20 ft box took
        "roughly 280 sheets of 12 mm" (6.5 t) on one page and "380 to 420 sheets at 18mm" (13-15 t) on another."""
        bands = self.class_bands(self.records)
        checked = 0
        for record in self.records:
            key = self.band_class(record)
            if not key or record['alt_classes'] or not self.vehicle_load(record):
                continue
            checked += 1
            low, high, pages = bands[key]
            if record['tonnes_low'] < low - 1e-9 or record['tonnes_high'] > high + 1e-9:
                with self.subTest(page=record['page'], vehicle_class=self.BAND_LABEL[key], figure=record['text'][:120]):
                    self.fail('%s is outside the %s band %.1f-%.1f t (median of %d pages, x/÷%g)'
                              % (self.describe(record), self.BAND_LABEL[key], low, high, pages, self.CLASS_BAND))
        self.assertGreaterEqual(checked, 10, 'the class check found almost no vehicle-tied load figures; is dist built?')

    DEFERS = re.compile(r'stated with the quote|stated on the proforma invoice|proforma invoice states', re.I)
    WITHHELD = (('tonnes', re.compile(r'\btonnage\b', re.I)), ('sheets', re.compile(r'\bcount\b', re.I)),
                ('m3', re.compile(r'\bvolume\b', re.I)))
    RATING_NAME = re.compile(r'tonners?', re.I)     # "multi-axle 22-tonners take 3-4 days" names a truck, not a load

    @classmethod
    def withheld_units(cls, units):
        """The load units a page defers: "the tonnage and sheet count ... are stated with the quote" -> tonnes, sheets."""
        found = set()
        for unit in units:
            for sentence in LF.split_sentences(unit['text']):
                if cls.DEFERS.search(sentence):
                    found.update(name for name, word in cls.WITHHELD if word.search(sentence))
        return found

    @classmethod
    def withheld_but_stated(cls, records, units_of):
        """(record, withheld units): a vehicle load in a unit the same page says is stated only with the quote."""
        by_page, found = {}, []
        for record in records:
            if (record['unit'] in ('sheets', 'tonnes', 'm3') and cls.vehicle_load(record)
                    and not cls.RATING_NAME.fullmatch(record.get('unit_text') or '')):
                by_page.setdefault(record['page'], []).append(record)
        for page, recs in sorted(by_page.items()):
            withheld = cls.withheld_units(units_of(page))
            found.extend((record, sorted(withheld)) for record in recs if record['unit'] in withheld)
        return found

    def test_a_load_deferred_to_the_quote_is_not_also_stated(self):
        """Gap (h): hedging one sentence left the page's other figures unread. Cuttack's body said "the tonnage and
        sheet count depend on the truck and thickness and are stated with the quote" while its FAQ still gave "a full
        single-axle truck (about 600-700 sheets of 12 mm)"; Bhopal's body said the same beside the FAQ's "around 18
        tonnes of plywood (roughly one 32-ft truck densely loaded)". The figures agree; the page contradicts itself."""
        def page(body):
            markup = ('<html><head><meta name="description" content="Synthetic page."></head><body><main>%s</main>'
                      '</body></html>' % body)
            return LF.page_records('synthetic.html', LF.extract_units_from_html(markup)), LF.extract_units_from_html(markup)

        def flagged(body):
            records, units = page(body)
            return {(record['source'], record['unit']) for record, _ in self.withheld_but_stated(records, lambda _: units)}

        deferred = ('<p>A 32-foot single-axle full truck takes 5-7 days. This is the right answer for full truckloads of '
                    'sheets; the tonnage and sheet count depend on the truck and thickness and are stated with the quote.</p>')
        self.assertEqual(flagged(deferred + '<h2>FAQ</h2><h3>What is the minimum order?</h3><p>Practically, a full '
                                 'single-axle truck (about 600-700 sheets of 12 mm in 8x4 ft, or equivalent mix).</p>'),
                         {('faq', 'sheets')}, 'Cuttack: a deferred sheet count stated in an FAQ answer')
        self.assertEqual(flagged(deferred + '<h2>FAQ</h2><h3>What is the minimum order?</h3><p>For full-truck road, around '
                                 '18 tonnes of plywood (roughly one 32-ft truck densely loaded).</p>'),
                         {('faq', 'tonnes')}, 'Bhopal: a deferred tonnage stated in an FAQ answer')
        self.assertEqual(flagged('<p>A 32-ft single-axle truck is best for full-load orders of 18-22 tonnes; the sheet count '
                                 'depends on the truck and thickness and is stated with the quote.</p>'), set(),
                         'a tonnage beside a deferred sheet count is not a contradiction')
        self.assertEqual(flagged('<p>A 32-foot single-axle truck clears the run in 56-72 hours. Multi-axle 22-tonners on the '
                                 'same lane take 3-4 days.</p><h2>FAQ</h2><h3>What is the minimum order?</h3><p>One full '
                                 '32-foot truck; the tonnage and sheet count depend on the truck and thickness and are '
                                 'stated with the quote.</p>'), set(), 'a truck named by its rating states no load')
        self.assertEqual(flagged('<p>A 32-foot single-axle full truck takes 5-7 days. This is the right answer for full '
                                 "truckloads of sheets, each loaded within the truck's permitted payload.</p><h2>FAQ</h2>"
                                 '<h3>What is the minimum order?</h3><p>Practically, a full single-axle truck (about 600-700 '
                                 'sheets of 12 mm in 8x4 ft, or equivalent mix).</p>'), set(), 'a payload clause defers nothing')
        found = self.withheld_but_stated(self.records, lambda page: LF.extract_units(str(DIST / page)))
        for record, withheld in found:
            with self.subTest(page=record['page'], figure=record['text'][:120]):
                self.fail('%s: the page says its %s are stated with the quote' % (self.describe(record), ' and '.join(withheld)))

    AXLE_CONFLICT = re.compile(
        r"(?:\bsingle[- ]axle|\bSXL)\b(?:\s+(?!(?:or|and|to|vs|versus)\b)[\w’'-]+)?\s+(?:multi[- ]axle|MXL)\b|"
        r"(?:\bmulti[- ]axle|\bMXL)\b(?:\s+(?!(?:or|and|to|vs|versus)\b)[\w’'-]+)?\s+(?:single[- ]axle|SXL)\b", re.I)

    def test_no_vehicle_name_is_both_single_axle_and_multi_axle(self):
        """Gap (e): nothing read vehicle names. "A 32-foot multi-axle SXL" (SXL is a single-axle body) and "a 32-ft
        single-axle multi-axle" name two different trucks as one, so their load figures belong to neither class."""
        for name in ('a 32-foot multi-axle SXL carries', 'a 32-ft single-axle multi-axle carrying', 'a multi-axle 32-ft SXL'):
            with self.subTest(contradictory=name):
                self.assertRegex(name, self.AXLE_CONFLICT)
        for name in ('a 32-ft single-axle or multi-axle truck', 'single-axle and/or multi-axle trailers',
                     '32-ft single-axle and multi-axle trailers', 'single-axle / multi-axle', 'a 32-foot SXL'):
            with self.subTest(alternatives=name):
                self.assertNotRegex(name, self.AXLE_CONFLICT)
        for name, sentences in published_sentences().items():
            for sentence in sentences:
                found = self.AXLE_CONFLICT.search(sentence)
                if found:
                    with self.subTest(page=name, sentence=sentence[:180]):
                        self.fail('vehicle named both single-axle and multi-axle: "%s"' % found.group(0))
        rule_four = [flag for flag in LF.rules(self.records)[0] if flag['rule'].startswith('4')]
        for flag in self.name_flags + rule_four:
            with self.subTest(page=flag['pages'][0], detail=flag['detail'][:160]):
                self.fail(flag['detail'])

    @staticmethod
    def published_estimator():
        """(containers, sheet mm, form defaults, page) as the site publishes its container estimator."""
        page = (DIST / 'rubberwood-plywood-container-weight.html').read_text(encoding='utf-8')
        script = (DIST / re.search(r'src="/?(assets/container-calculator[^"]*\.js)"', page).group(1)).read_text(encoding='utf-8')
        containers = {size: {key: int(value) for key, value in re.findall(r'(\w+):(\d+)', body)}
                      for size, body in re.findall(r"'(20|40)':\s*\{([^}]*)\}", script)}
        sheet = tuple(int(v) for v in re.search(r'sheet = \{length:(\d+),width:(\d+)\}', script).groups())
        defaults = {field: float(re.search(r'id="cwi-calc-%s"[^>]*\bvalue="([\d.]+)"' % field, page).group(1))
                    for field in ('density', 'payload', 'packing', 'clearance')}
        return containers, sheet, defaults, page

    @staticmethod
    def estimator_count(box, sheet, thickness, defaults):
        """calculate() in assets/container-calculator.js: flat lengthwise stacks, 100 mm clearance, 50 mm gaps."""
        along = (box['length'] - 100 + 50) // (sheet[0] + 50)
        across = (min(box['width'], box['doorWidth']) - 100 + 50) // (sheet[1] + 50)
        layers = math.floor((min(box['height'], box['doorHeight']) - defaults['clearance']) / thickness)
        mass = sheet[0] / 1000 * (sheet[1] / 1000) * (thickness / 1000) * defaults['density']
        weight = math.floor((defaults['payload'] * 1000 - defaults['packing']) / mass)
        return min(weight, along * across * layers)

    def test_typical_container_sheet_counts_stay_within_the_estimator_flat_stack(self):
        """Gap (f): container sheet counts were held only to the guide's capacity-only ceilings (615 sheets of 18 mm
        in a 20 ft box), which leave out pallets, dunnage and sheet fit. The site's own estimator flat-stacks 242
        sheets of 18 mm in a 20 ft box, yet FAQ answers gave "roughly 320-360" and "roughly 380 to 420" as the load."""
        containers, sheet, defaults, page = self.published_estimator()

        def count(size, thickness):
            return self.estimator_count(containers[size], sheet, thickness, defaults)
        self.assertEqual((count('20', 12), count('40', 12)), (364, 728))
        self.assertIn('364 sheets in a 20ft standard container or 728 in a 40ft', html.unescape(page))
        for thickness in (12, 18):
            self.assertEqual(count('20', thickness), LF.ceiling_estimator('container-20ft', thickness))
            self.assertEqual(count('40', thickness), LF.ceiling_estimator('container-40ft', thickness))
        for record in self.records:
            if (record['vehicle_kind'] != 'container' or record['class_detail'] not in ('container-20ft', 'container-40ft')
                    or record['unit'] != 'sheets' or not record['thickness_mm'] or record['alt_classes']
                    or set(record['qualifiers']) & (self.NOT_A_LOAD | {'rating'})):
                continue
            limit = count(record['class_detail'][len('container-'):len('container-') + 2], record['thickness_mm'])
            if record['high'] > limit:
                with self.subTest(page=record['page'], figure=record['text'][:140]):
                    self.fail('%s exceeds the estimator flat-stack count of %d sheets' % (self.describe(record), limit))

    STATISTIC = re.compile(
        r"(?P<cur>₹|\bRs\.?|\bINR\b|US\$|\$|\bUSD\b|\bSAR\b|\bAED\b|\bQAR\b)\s?(?P<num>\d[\d,]*(?:\.\d+)?)[\s-]?"
        r"(?P<scale>crores?|lakhs?|billion|million)\b(?P<rest>[^.;:,()—–]*)"
        r"|(?P<pct>\d+(?:\.\d+)?)\s?%\s+of\s+(?:India|the world|the country)[’']s\s+(?P<prest>[^.;:,()—–]*)", re.I)
    SCALE = {'crore': 1e7, 'lakh': 1e5, 'billion': 1e9, 'million': 1e6}
    CURRENCY = {'₹': 'INR', 'rs': 'INR', 'rs.': 'INR', 'inr': 'INR', '$': 'USD', 'us$': 'USD', 'usd': 'USD',
                'sar': 'SAR', 'aed': 'AED', 'qar': 'QAR'}
    STAT_STOP = frozenset('about and around cumulative did each every export exports for from india indian into its '
                          'mark out over per recent roughly share that the total value worth year years'.split())

    @classmethod
    def statistics_by_subject(cls, sentences_by_page, places):
        """{(place, subject word, unit): {page: {value}}} for money totals and national or world shares."""
        found = {}
        for page, sentences in sentences_by_page.items():
            for sentence in set(sentences):
                for match in cls.STATISTIC.finditer(sentence):
                    window = sentence[max(0, match.start() - 160):match.end()]
                    named = {p for p in places if re.search(r'\b%s\b' % re.escape(p), window, re.I)}
                    if not named:
                        continue
                    if match.group('pct'):
                        unit, value, rest = '%', float(match.group('pct')), match.group('prest')
                    else:
                        unit = cls.CURRENCY[match.group('cur').lower()]
                        value = float(match.group('num').replace(',', '')) * cls.SCALE[match.group('scale').lower().rstrip('s')]
                        rest = match.group('rest')
                    words = [w for w in re.findall(r'[a-z][a-z-]{2,}', rest.lower())[:6] if w not in cls.STAT_STOP]
                    for place in named:
                        for subject in (w for w in words if w not in place.split()):
                            found.setdefault((place, subject, unit), {}).setdefault(page, set()).add(float('%.3g' % value))
        return found

    def test_a_statistic_has_one_value_across_pages(self):
        """Gap (g): nothing compared a figure between pages. Tiruppur's annual knitwear exports were "somewhere
        around Rs 30,000 crore" on the Tiruppur page and "roughly ₹40,000 crore ... in FY25" on the Coimbatore page."""
        places = {m.group(1).replace('-', ' ') for m in (
            re.fullmatch(r'(?:blogs/post/plywood-supply-to-|export/)([a-z-]+)\.html', path.relative_to(DIST).as_posix())
            for path in DIST.rglob('*.html')) if m}
        broken = self.statistics_by_subject(
            {'a.html': ['Tiruppur ships somewhere around Rs 30,000 crore worth of knitwear out of India every year.'],
             'b.html': ['And Tiruppur, 55 km east, did roughly ₹40,000 crore in knitwear exports in FY25.']}, {'tiruppur'})
        self.assertEqual(broken[('tiruppur', 'knitwear', 'INR')], {'a.html': {3e11}, 'b.html': {4e11}})
        for (place, subject, unit), pages in sorted(self.statistics_by_subject(published_sentences(), places).items()):
            values = list(pages.items())
            clash = [(p, q) for i, (p, vp) in enumerate(values) for q, vq in values[i + 1:] if vp.isdisjoint(vq)]
            if clash:
                with self.subTest(place=place, subject=subject, unit=unit):
                    self.fail('one statistic, different values: %s' % '; '.join(
                        '%s %s' % (page, sorted(v)) for page, v in sorted(pages.items())))


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
        for path in sorted(DIST.rglob('*.html')):
            parser = Surface()
            parser.feed(path.read_text(encoding='utf-8'))
            text = ''.join(parser.parts)
            _SENTENCES[path.relative_to(DIST).as_posix()] = [
                s.strip() for line in text.split('\n') for s in re.split(r'(?<=[.!?])\s+', line) if s.strip()]
    return _SENTENCES


if __name__ == '__main__':
    unittest.main()
