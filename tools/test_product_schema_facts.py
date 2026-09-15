"""Product JSON-LD on the product pages says only what the page itself says.

Run after python build.py. product_schema() in build.py deliberately carries no
offers, price, availability or invented catalogue identifiers, and every material
and additionalProperty value it adds must appear verbatim in the page's visible
<main> text. The markup can then never be stronger than what a buyer reads.
"""
import html
import json
import re
import unittest
from pathlib import Path

import build

ROOT = Path(__file__).resolve().parents[1]
LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
FORBIDDEN = {
    'offers', 'price', 'priceCurrency', 'priceSpecification', 'availability',
    'sku', 'mpn', 'gtin', 'gtin8', 'gtin12', 'gtin13', 'gtin14', 'productID',
    'aggregateRating', 'review',
}


def visible_main_text(page):
    main = re.search(r'<main\b.*?</main>', page, re.S)
    body = main.group(0) if main else page
    body = re.sub(r'<(script|style|noscript|svg|template)\b.*?</\1>', ' ', body, flags=re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', body)))


def keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from keys(value)


class ProductSchemaFactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = {}
        for slug, _, _ in build.PRODUCTS:
            path = ROOT / 'dist' / f'{slug}.html'
            if not path.exists():
                raise AssertionError('Build dist before checking product schema')
            cls.pages[slug] = path.read_text(encoding='utf-8')

    def products(self, slug):
        blocks = [json.loads(b) for b in LD.findall(self.pages[slug])]
        return [b for b in blocks if b.get('@type') == 'Product']

    def test_each_product_page_has_exactly_one_product_block(self):
        for slug in self.pages:
            with self.subTest(slug=slug):
                self.assertEqual(len(self.products(slug)), 1)

    def test_no_offer_price_availability_or_invented_identifier(self):
        for slug in self.pages:
            with self.subTest(slug=slug):
                found = FORBIDDEN & set(keys(self.products(slug)[0]))
                self.assertFalse(found, f'{slug} Product block carries {sorted(found)}')

    def test_every_added_fact_is_visible_on_the_page(self):
        for slug, page in self.pages.items():
            product = self.products(slug)[0]
            text = visible_main_text(page)
            values = [product['material']] if 'material' in product else []
            for prop in product.get('additionalProperty', []):
                self.assertEqual(prop.get('@type'), 'PropertyValue')
                self.assertTrue(prop.get('name'))
                values.append(prop['value'])
            for value in values:
                with self.subTest(slug=slug, value=value):
                    self.assertIsInstance(value, str)
                    self.assertLessEqual(len(value), 120)
                    self.assertIn(value, text)

    def test_facts_table_only_names_real_product_pages(self):
        slugs = {slug for slug, _, _ in build.PRODUCTS}
        self.assertLessEqual(set(build.PRODUCT_FACTS), slugs)


if __name__ == '__main__':
    unittest.main()
