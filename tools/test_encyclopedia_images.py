"""Focused image-directory checks with the verified records and no build side effects."""
import copy
import hashlib
import json
import sys
import unittest
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from encyclopedia_navigation import (HubScan, enhance_wood_hub, species_thumbnail,
                                     enhance_species_reference_gallery, render_species_navigation,
                                     orient_species_image)
from hero_layout import parse_fragment

MEDIA = json.loads((ROOT / 'content/species-media.json').read_text(encoding='utf-8'))


def fixture():
    slugs = list(MEDIA)
    groups = [slugs[:11], slugs[11:22], slugs[22:]]
    return '<main><h1>Original title</h1>' + ''.join(
        '<section class="cwe__group"><h2>Group ' + str(index) + '</h2><div class="cwe__grid">'
        + ''.join('<a class="cwe__card" href="/woods-we-use/' + slug + '">'
                  '<p class="cwe__card-name">' + escape(slug) + '</p>'
                  '<p class="cwe__card-sci">' + escape(MEDIA[slug]['scientific_name']) + '</p>'
                  '<span class="cwe__card-tag">Read</span></a>' for slug in group)
        + '</div></section>' for index, group in enumerate(groups)) + '</main>'


class EncyclopediaImageTests(unittest.TestCase):
    def renderer(self, item, **options):
        self.calls.append((item, options))
        return '<img src="' + escape(item['src'], quote=True) + '" alt="' + escape(item['alt'], quote=True) + '">'

    def setUp(self):
        self.calls = []

    def test_all_cards_keep_original_copy_and_destinations(self):
        original = fixture()
        result, metadata = enhance_wood_hub(original, lambda x: x, '/woods-we-use', image=self.renderer, species_media=MEDIA)
        before, after = HubScan(original), HubScan(result)
        before.feed(original)
        after.feed(result)
        self.assertEqual([(x['attrs']['href'], x['name'], x['botanical']) for x in before.cards],
                         [(x['attrs']['href'], x['name'], x['botanical']) for x in after.cards])
        self.assertEqual(len(metadata), 28)
        self.assertEqual(result.count('class="cwe__card-photo"'), 23)
        self.assertEqual(result.count('class="cwe__card-photo cwe__card-photo--pending"'), 5)
        self.assertEqual(result.count('>Wood-grain detail</span>'), 22)
        self.assertEqual(result.count('>End-grain detail</span>'), 1)
        self.assertEqual(result.count('>Botanical references inside</span>'), 4)
        self.assertEqual(len({x[0]['sha256'] for x in self.calls}), 23)
        for item, options in self.calls:
            self.assertFalse(options['eager'])
            self.assertIn('(max-width: 480px)', options['sizes'])
            self.assertIn(escape(item['credit']), result)
            self.assertIn(escape(item['license']), result)
        self.assertNotIn('/files/Species/anjili-wood.webp', result)
        self.assertEqual(result.count('data-reference-fit="cover"'), 23)
        self.assertIn('calc(280vw - 112px)', result if 'sizes=' in result else ' '.join(x[1]['sizes'] for x in self.calls))
        self.assertNotIn('data-reference-fit="contain"', result)
        self.assertNotIn('data-reference-rotation="90"', result)
        self.assertEqual(result.count('data-reference-detail="birch-end-grain"'), 1)
        tree = parse_fragment(result)
        for card in [n for n in tree.nodes if 'cwe__card' in n.classes]:
            pending = card.attrs['href'].rsplit('/', 1)[-1] in ['kadam', 'melia-dubia', 'neem', 'sal', 'anjili']
            self.assertEqual(len([n for n in tree.nodes if n.tag == 'img' and card.contains(n)]), 0 if pending else 1)
            self.assertFalse(any(n.tag == 'a' and n != card and card.contains(n) for n in tree.nodes))

    def test_missing_or_shared_photo_fails_instead_of_silent_empty_card(self):
        incomplete = copy.deepcopy(MEDIA)
        incomplete.pop('teak')
        with self.assertRaisesRegex(ValueError, 'Missing verified image'):
            enhance_wood_hub(fixture(), str, '/woods-we-use', image=self.renderer, species_media=incomplete)
        duplicated = copy.deepcopy(MEDIA)
        duplicated['teak']['images'] = duplicated['birch']['images']
        with self.assertRaisesRegex(ValueError, 'two different species'):
            enhance_wood_hub(fixture(), str, '/woods-we-use', image=self.renderer, species_media=duplicated)

    def test_reference_target_preserves_entire_gallery_and_copy(self):
        original = '<p>Original prose.</p><section class="cw-species-reference"><figure><img src="/a.webp"><figcaption>Original source and licence.</figcaption></figure></section><p>Original specifications.</p>'
        result = enhance_species_reference_gallery(original)
        added = '<h2 class="cw-species-reference__title" id="species-images">Photo references</h2>'
        self.assertEqual(result.replace(added, ''), original)
        with self.assertRaisesRegex(ValueError, 'unique'):
            enhance_species_reference_gallery(result)
        _, metadata = enhance_wood_hub(fixture(), str, '/woods-we-use')
        navigation = render_species_navigation(metadata, '/woods-we-use/teak', str, photo_reference=True)
        self.assertIn('href="#species-images">Photo references</a>', navigation)
        self.assertIn('← All wood species', navigation)

    def test_selected_records_exist_and_match_reviewed_bytes(self):
        tree_only = []
        for slug, entry in MEDIA.items():
            item, label = species_thumbnail(entry)
            asset = ROOT / 'assets/photos' / item['src'].lstrip('/')
            self.assertTrue(asset.is_file(), slug)
            self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(), item['sha256'], slug)
            if label == 'Tree reference':
                tree_only.append(slug)
        self.assertEqual(sorted(tree_only), ['kadam', 'melia-dubia', 'neem', 'sal'])

    def test_orientation_wrap_preserves_original_photo_markup(self):
        tag = '<img src="/files/Species/neem-botanical.webp" alt="Original tree reference">'
        wrapped = orient_species_image(tag, MEDIA['neem']['images'][0])
        self.assertIn(tag, wrapped)
        self.assertIn('data-reference-rotation="90"', wrapped)
        self.assertEqual(orient_species_image(tag, MEDIA['teak']['images'][0]), tag)


if __name__ == '__main__':
    unittest.main()
