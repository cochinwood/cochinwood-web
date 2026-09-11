"""Synthetic ownership checks; no remote images or customer data."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from unique_imagery import owner_image, validate_ownership, read_manifest, read_assets, is_text_guide


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'content').mkdir()
        (self.root / 'assets/photos/files/Unique').mkdir(parents=True)
        self.data = b'synthetic image bytes for integrity test'
        (self.root / 'assets/photos/files/Unique/a.webp').write_bytes(self.data)
        self.asset = {'src': '/files/Unique/a.webp', 'alt': 'Synthetic test fixture',
                      'sha256': hashlib.sha256(self.data).hexdigest(),
                      'kind': 'test fixture', 'provenance': 'Synthetic unit test only'}
        self.manifest = {'owners': {'/blogs/post/a': {'asset_key': 'a', 'status': 'approved'}}}
        self.assets = {'assets': {'a': self.asset}}

    def save(self):
        read_manifest.cache_clear()
        read_assets.cache_clear()
        for name, value in [('unique-imagery', self.manifest), ('unique-imagery-assets', self.assets)]:
            (self.root / ('content/' + name + '.json')).write_text(json.dumps(value), encoding='utf-8')

    def test_exact_owner_and_query_normalization(self):
        self.save()
        self.assertEqual(owner_image('/blogs/post/a?q=ignored', self.root), self.asset)
        self.assertIsNone(owner_image('/blogs/post/other', self.root))
        self.assertEqual(validate_ownership(self.root), [])

    def test_pending_is_visible_in_release_gate_without_preview_placeholder(self):
        self.manifest['owners']['/blogs/post/a']['status'] = 'pending'
        self.save()
        self.assertIsNone(owner_image('/blogs/post/a', self.root))
        self.assertIn('pending', validate_ownership(self.root)[0])

    def test_renaming_same_bytes_does_not_evade_ownership(self):
        (self.root / 'assets/photos/files/Unique/b.webp').write_bytes(self.data)
        self.assets['assets']['b'] = dict(self.asset, src='/files/Unique/b.webp')
        self.manifest['owners']['/blogs/post/b'] = {'asset_key': 'b', 'status': 'approved'}
        self.save()
        self.assertIn('Identical photograph', validate_ownership(self.root)[0])

    def test_missing_and_changed_bytes_fail(self):
        self.save()
        path = self.root / 'assets/photos/files/Unique/a.webp'
        path.write_bytes(b'changed')
        self.assertIn('hash mismatch', validate_ownership(self.root)[0])
        path.unlink()
        self.assertIn('Missing source', validate_ownership(self.root)[0])

    def test_external_or_traversal_path_rejected(self):
        for src in ['https://example.com/a.webp', '/files/../../../outside.webp']:
            self.asset['src'] = src
            self.save()
            self.assertTrue(validate_ownership(self.root))

    def test_text_exception_cannot_hide_missing_technical_image(self):
        (self.root / 'content/blog').mkdir()
        (self.root / 'content/blog/topics.json').write_text(json.dumps({'posts': {'a': 'packing-export'}}), encoding='utf-8')
        self.manifest['owners']['/blogs/post/a'].update(kind='text_guide', reason='Attempted exemption')
        self.save()
        self.assertIn('restricted', validate_ownership(self.root)[0])

    def test_country_text_exception_requires_registered_source_and_category(self):
        (self.root / 'content/export/countries').mkdir(parents=True)
        (self.root / 'content/export/export.json').write_text(json.dumps({'countries': [{'slug': 'uae'}]}), encoding='utf-8')
        (self.root / 'content/export/countries/qatar.json').write_text(json.dumps({'slug': 'qatar'}), encoding='utf-8')
        for route in ('/export/uae', '/export/qatar'):
            self.manifest['owners'][route] = {'kind': 'text_guide', 'status': 'approved', 'category': 'country-export', 'reason': 'Approved source destination guide'}
        self.save()
        self.assertTrue(is_text_guide('/export/uae', self.root))
        self.assertTrue(is_text_guide('/export/qatar', self.root))
        self.assertEqual(validate_ownership(self.root), [])
        for route, category in (('/export/unregistered', 'country-export'), ('/export/uae', 'other'), ('/export', 'country-export')):
            with self.subTest(route=route, category=category):
                self.manifest['owners'][route] = {'kind': 'text_guide', 'status': 'approved', 'category': category, 'reason': 'Invalid exception'}
                self.save()
                self.assertTrue(any('restricted' in e for e in validate_ownership(self.root)))
                del self.manifest['owners'][route]

    def test_country_text_exception_requires_explicit_approval(self):
        (self.root / 'content/export').mkdir()
        (self.root / 'content/export/export.json').write_text(json.dumps({'countries': [{'slug': 'uae'}]}), encoding='utf-8')
        for status, reason in (('pending', 'Awaiting review'), ('approved', '')):
            self.manifest['owners']['/export/uae'] = {'kind': 'text_guide', 'status': status, 'category': 'country-export', 'reason': reason}
            self.save()
            self.assertTrue(any('approval and reason' in e for e in validate_ownership(self.root)))


if __name__ == '__main__':
    unittest.main()
