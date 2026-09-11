import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WebsiteBacklogRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        posts = json.loads((ROOT / 'content/blog/posts.json').read_text(encoding='utf-8'))
        cls.posts = {post['slug']: post['html'] for post in posts}

    def test_archived_regions_cannot_restore_face_rate_delta(self):
        archive = (ROOT / 'content/blog/mirror_regions.json').read_text(encoding='utf-8')
        self.assertNotIn('₹/sqft delta (vs Gurjan baseline)', archive)
        self.assertNotIn('<td>+₹4.50</td><td>+₹2.80</td>', archive)

    def test_reported_location_markup_is_well_formed_at_source(self):
        tiruppur = self.posts['plywood-supply-to-tiruppur']
        self.assertNotIn('</h3<p>', tiruppur)
        self.assertIn('</h3><p>A standard 32-foot full-body', tiruppur)

        for slug in ('plywood-supply-to-muscat', 'plywood-supply-to-ras-al-khaimah'):
            with self.subTest(slug=slug):
                article = self.posts[slug]
                self.assertEqual(article.count('<thead>'), article.count('</thead>'))
                self.assertNotIn('<thead><tbody>', article)

    def test_aurangabad_capacity_uses_weight_and_axle_evidence(self):
        article = self.posts['plywood-supply-to-aurangabad']
        for unsupported in ('32-ft single-axle', '~16 t / ~9,000 sq.ft',
                            '~9 t / ~5,000 sq.ft'):
            self.assertNotIn(unsupported, article)
        self.assertIn('22.1–24.3 kg before packaging', article)
        self.assertIn('approved axle configuration', article)
        self.assertIn('packed weighment', article)


if __name__ == '__main__':
    unittest.main()
