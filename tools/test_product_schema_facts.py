"""Product JSON-LD on the product pages says only what the page itself says.

Run after python build.py, from the repository root with PYTHONPATH=. What this
proves, and what it cannot:

- dist/ carries the current PRODUCT_FACTS, so a stale build fails;
- a Product block holds only the keys product_schema() writes, so offers, price,
  availability, sku/mpn/gtin, hasCertification or award cannot slip in;
- every material and additionalProperty value appears verbatim inside ONE visible
  block of the page's <main> (a paragraph, list item, table cell, heading...), with
  hidden, aria-hidden, closed-dialog, template, noscript and svg content removed.

It cannot tell whether a verbatim value keeps its sentence's hedge ("on request",
"where specified"), or whether a name fits its value. That stays a human review
for every new PRODUCT_FACTS entry, as it was for the first 81 (15 Sep 2026).
"""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

import build

ROOT = Path(__file__).resolve().parents[1]
LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
PRODUCT_KEYS = {'@context', '@type', 'name', 'description', 'url', 'image', 'category',
                'brand', 'manufacturer', 'countryOfOrigin', 'material', 'additionalProperty'}
NESTED_KEYS = {'brand': {'@type', 'name'}, 'manufacturer': {'@id'},
               'countryOfOrigin': {'@type', 'name'}}
PROPERTY_KEYS = {'@type', 'name', 'value'}
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta',
        'source', 'track', 'wbr'}
SKIP = {'script', 'style', 'noscript', 'template', 'svg'}
BLOCKS = {'main', 'section', 'article', 'aside', 'header', 'footer', 'nav', 'div', 'figure',
          'figcaption', 'p', 'ul', 'ol', 'li', 'dl', 'dt', 'dd', 'table', 'caption', 'thead',
          'tbody', 'tfoot', 'tr', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote',
          'details', 'summary', 'form', 'fieldset', 'legend', 'label', 'button', 'dialog'}


class VisibleBlocks(HTMLParser):
    """Text of each innermost visible block inside <main>; inline tags pass through."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.saw_main, self.skip, self.stack, self.blocks = False, 0, [], []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        if self.skip:
            self.skip += 1
            return
        attrs = dict(attrs)
        inside = any(t == 'main' for t, _ in self.stack)
        if tag == 'main':
            self.saw_main = True
        elif inside and (tag in SKIP or 'hidden' in attrs or attrs.get('aria-hidden') == 'true'
                         or (tag == 'dialog' and 'open' not in attrs)):
            self.skip = 1
            return
        if tag in BLOCKS and (inside or tag == 'main'):
            self.stack.append((tag, []))
        elif self.stack:
            self.stack[-1][1].append(' ')

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if self.skip:
            self.skip -= 1
            return
        if tag in BLOCKS and self.stack:
            # close up to the matching block; a missing end tag closes its children
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    while len(self.stack) > i:
                        self.blocks.append(re.sub(r'\s+', ' ', ''.join(self.stack.pop()[1])).strip())
                    break
        elif self.stack:
            self.stack[-1][1].append(' ')

    def handle_data(self, data):
        if self.stack and not self.skip:
            self.stack[-1][1].append(data)


def visible_blocks(page):
    parser = VisibleBlocks()
    parser.feed(page)
    parser.close()
    return parser.saw_main, [b for b in parser.blocks if b]


class ProductSchemaFactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = {}
        for slug, _, _ in build.PRODUCTS:
            path = ROOT / 'dist' / f'{slug}.html'
            if not path.exists():
                raise AssertionError('Build dist before checking product schema')
            cls.pages[slug] = path.read_text(encoding='utf-8')

    def product(self, slug):
        blocks = [json.loads(b) for b in LD.findall(self.pages[slug])]
        products = [b for b in blocks if b.get('@type') == 'Product']
        self.assertEqual(len(products), 1, f'{slug} must carry exactly one Product block')
        return products[0]

    def test_product_block_holds_only_the_keys_product_schema_writes(self):
        for slug in self.pages:
            with self.subTest(slug=slug):
                product = self.product(slug)
                self.assertLessEqual(set(product), PRODUCT_KEYS)
                for key, allowed in NESTED_KEYS.items():
                    self.assertEqual(set(product[key]), allowed)
                for prop in product.get('additionalProperty', []):
                    self.assertEqual(set(prop), PROPERTY_KEYS)
                    self.assertEqual(prop['@type'], 'PropertyValue')

    def test_dist_carries_the_current_product_facts(self):
        for slug in self.pages:
            with self.subTest(slug=slug):
                facts = build.PRODUCT_FACTS.get(slug, {})
                product = self.product(slug)
                self.assertEqual(product.get('material'), facts.get('material'))
                expected = [{'@type': 'PropertyValue', 'name': n, 'value': v}
                            for n, v in facts.get('properties', [])]
                self.assertEqual(product.get('additionalProperty', []), expected)

    def test_every_added_fact_sits_in_one_visible_block(self):
        for slug, page in self.pages.items():
            product = self.product(slug)
            saw_main, blocks = visible_blocks(page)
            self.assertTrue(saw_main, f'{slug} has no <main> to check facts against')
            values = [product['material']] if 'material' in product else []
            values += [prop['value'] for prop in product.get('additionalProperty', [])]
            for value in values:
                with self.subTest(slug=slug, value=value):
                    self.assertIsInstance(value, str)
                    self.assertLessEqual(len(value), 120)
                    self.assertTrue(any(value in block for block in blocks),
                                    f'{value!r} is not inside one visible block of /{slug}')

    def test_facts_table_only_names_real_product_pages(self):
        slugs = {slug for slug, _, _ in build.PRODUCTS}
        self.assertLessEqual(set(build.PRODUCT_FACTS), slugs)
        for slug, facts in build.PRODUCT_FACTS.items():
            with self.subTest(slug=slug):
                self.assertLessEqual(set(facts), {'material', 'properties'})
                names = [n for n, _ in facts.get('properties', [])]
                self.assertEqual(len(names), len(set(names)), 'duplicate property name')


if __name__ == '__main__':
    unittest.main()
