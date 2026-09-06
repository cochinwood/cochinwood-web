"""Text-first location preview keeps all exact destinations and authored content."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blog_directory import render_directory
from editorial_media import enhance_editorial_media, article_share_media
from hero_layout import parse_fragment
from unique_imagery import is_text_guide, read_manifest


class LocationGuideTests(unittest.TestCase):
    def test_only_exact_existing_location_guides_are_text_first(self):
        taxonomy = json.loads((ROOT / 'content/blog/topics.json').read_text(encoding='utf-8'))
        expected = {'/blogs/post/' + s for s, topic in taxonomy['posts'].items() if topic == 'city-supply'}
        actual = {p for p, value in read_manifest()['owners'].items() if value.get('kind') == 'text_guide'}
        self.assertEqual(len(expected), 109)
        self.assertEqual(actual, expected)
        for path in sorted(actual):
            self.assertTrue(is_text_guide(path))
            self.assertIsNone(article_share_media(path.rsplit('/', 1)[-1]))
            source = '<article class="cw-reading-content"><p>Existing introduction.</p><h2 id="specs">Existing specifications</h2><table><tr><td>Retained value</td></tr></table><a href="/contact">Enquire</a></article>'
            output = enhance_editorial_media(source, path, lambda item, **kw: '<img src="' + item['src'] + '">', lambda p: p)
            self.assertEqual(output, source + '<!-- data-editorial-pass="1" -->')

    def test_all_technical_article_images_remain_article_share_images(self):
        from unique_imagery import owner_image
        taxonomy = json.loads((ROOT / 'content/blog/topics.json').read_text(encoding='utf-8'))
        expected = {'/blogs/post/' + slug for slug, topic in taxonomy['posts'].items()
                    if topic != 'city-supply'}
        owners = {p: value for p, value in read_manifest()['owners'].items()
                  if p.startswith('/blogs/post/') and value.get('status') == 'approved'
                  and value.get('kind') != 'text_guide'}
        self.assertEqual(len(expected), 48)
        self.assertEqual(set(owners), expected)
        for path in owners:
            self.assertEqual(article_share_media(path.rsplit('/', 1)[-1])['src'], owner_image(path)['src'])

    def test_mixed_directory_preserves_counts_links_titles_and_technical_images(self):
        taxonomy = json.loads((ROOT / 'content/blog/topics.json').read_text(encoding='utf-8'))
        posts = json.loads((ROOT / 'content/blog/posts.json').read_text(encoding='utf-8'))
        output = render_directory(posts, taxonomy, lambda p: p, '<img src="/hero.webp">',
                                  thumbnail=lambda s: '<img src="/' + s + '.webp">')
        tree = parse_fragment(output)
        cards = [n for n in tree.nodes if n.tag == 'a' and 'data-blog-topic' in n.attrs]
        self.assertEqual(len(cards), len(posts))
        self.assertEqual({n.attrs['href'] for n in cards}, {'/blogs/post/' + p['slug'] for p in posts})
        location = [n for n in cards if n.attrs['data-blog-topic'] == 'city-supply']
        self.assertEqual(len(location), 109)
        for card in cards:
            images = [n for n in tree.nodes if n.tag == 'img' and card.contains(n)]
            self.assertEqual(len(images), 0 if card in location else 1)
            if card in location:
                self.assertIn('cw-blog-location-meta', tree.raw(card))
                self.assertIn('Read supply guide', tree.raw(card))
        self.assertIn('Tamil Nadu · India', output)
        self.assertIn('United Arab Emirates', output)


if __name__ == '__main__':
    unittest.main()
