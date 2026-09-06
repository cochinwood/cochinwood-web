"""Destination presentation and preservation tests; no build output or network writes."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import build as B
import export_section as E
from export_guide_preservation import BASELINE, signature, source_hashes
from hero_layout import parse_fragment
from unique_imagery import is_text_guide, owner_image, read_manifest


class ExportGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = {}
        def capture(path, content, src=None):
            if path.endswith('/index.html'):
                path = path[:-len('/index.html')] + '.html'
            # Apply the existing publication transformations in memory only.
            cls.pages['/' + path.removesuffix('.html')] = B.a11y_fixups(B.expand_canon(content, path))
        with patch.object(B, 'write', side_effect=capture):
            count = E.build()
        if count != 29:
            raise AssertionError('Expected Export hub plus exactly 28 country pages')
        cls.countries = {'/export/' + d['slug'] for d in E._load()['countries']}

    def test_only_source_countries_have_approved_text_guide_policy(self):
        actual = {p for p, item in read_manifest()['owners'].items()
                  if item.get('category') == 'country-export' and item.get('kind') == 'text_guide'}
        self.assertEqual(len(self.countries), 28)
        self.assertEqual(actual, self.countries)
        for route in self.countries:
            self.assertTrue(is_text_guide(route))
            self.assertIsNone(owner_image(route))
        self.assertFalse(is_text_guide('/export'))

    def test_all_country_heroes_are_compact_with_brand_sharing(self):
        loading_path = unquote(urlsplit(B.VISUAL_MEDIA['export_hero']['src']).path)
        for route in sorted(self.countries):
            with self.subTest(route=route):
                tree = parse_fragment(self.pages[route])
                hero = next(n for n in tree.nodes if 'cw-page-hero' in n.classes)
                self.assertIn('cw-page-hero--compact', hero.classes)
                self.assertEqual(hero.attrs.get('data-export-guide'), 'true')
                self.assertFalse(any(n.tag in {'img', 'picture', 'figure'} and hero.contains(n) for n in tree.nodes))
                self.assertEqual(sum(n.tag == 'h1' for n in tree.nodes), 1)
                self.assertEqual(sum('cw-page-hero__button' in n.classes for n in tree.nodes), 2)
                for node in tree.nodes:
                    if node.tag == 'img':
                        self.assertNotEqual(unquote(urlsplit(node.attrs.get('src', '')).path), loading_path)
                    if node.tag == 'meta' and (node.attrs.get('property') == 'og:image' or node.attrs.get('name') == 'twitter:image'):
                        self.assertEqual(node.attrs['content'], B.OG_IMAGE)

    def test_export_hub_keeps_its_shared_photo_hero(self):
        tree = parse_fragment(self.pages['/export'])
        hero = next(n for n in tree.nodes if 'cw-page-hero' in n.classes)
        self.assertNotIn('cw-page-hero--compact', hero.classes)
        self.assertNotIn('data-export-guide', hero.attrs)
        images = [n for n in tree.nodes if n.tag == 'img' and hero.contains(n)]
        self.assertEqual(len(images), 1)
        self.assertEqual(unquote(urlsplit(images[0].attrs['src']).path),
                         unquote(urlsplit(B.VISUAL_MEDIA['export_hero']['src']).path))
        self.assertEqual(images[0].attrs['loading'], 'eager')

    def test_all_original_copy_links_anchors_tables_and_metadata_are_preserved(self):
        baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
        self.assertEqual(set(self.pages), set(baseline['pages']))
        for route, markup in self.pages.items():
            with self.subTest(route=route):
                self.assertEqual(signature(markup), baseline['pages'][route])
        self.assertEqual(source_hashes(), baseline['source_files'])


if __name__ == '__main__':
    unittest.main()
