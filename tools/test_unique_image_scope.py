"""A Blog phase cannot conceal missing article imagery or claim a full release."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from check_unique_images import scope_report
from unique_imagery import read_assets, read_manifest


class ScopeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'content/blog').mkdir(parents=True)
        (self.root / 'assets/photos/files/test').mkdir(parents=True)
        self.owners, self.assets, self.taxonomy = {}, {}, {}
        for i in range(157):
            slug = 'article-' + str(i)
            route = '/blogs/post/' + slug
            self.taxonomy[slug] = 'city-supply' if i < 109 else 'packing-export'
            if i < 109:
                self.owners[route] = {'kind': 'text_guide', 'status': 'approved', 'reason': 'Explicit fixture location guide'}
            else:
                data = str(i).encode()
                src = '/files/test/' + slug + '.webp'
                (self.root / 'assets/photos' / src.lstrip('/')).write_bytes(data)
                self.assets[slug] = {'src': src, 'alt': slug, 'kind': 'fixture', 'provenance': 'Synthetic tests', 'sha256': hashlib.sha256(data).hexdigest()}
                self.owners[route] = {'asset_key': slug, 'status': 'approved'}
        for i in range(28):
            self.owners['/export/' + str(i)] = {'status': 'pending', 'category': 'country-export'}
        self.save()

    def save(self):
        read_manifest.cache_clear(); read_assets.cache_clear()
        for name, value in [('unique-imagery', {'owners': self.owners}), ('unique-imagery-assets', {'assets': self.assets}), ('blog/topics', {'posts': self.taxonomy})]:
            (self.root / ('content/' + name + '.json')).write_text(json.dumps(value), encoding='utf-8')

    def test_blog_pass_is_not_full_completion(self):
        report = scope_report(self.root, 'blog')
        self.assertTrue(report['passed'])
        self.assertEqual(len(report['included_owners']), 157)
        self.assertEqual(len(report['excluded_pending_owners']), 28)
        self.assertFalse(report['full_migration_complete'])
        self.assertFalse(scope_report(self.root)['passed'])

    def test_pending_article_cannot_be_excluded(self):
        self.owners['/blogs/post/article-109']['status'] = 'pending'
        self.save()
        self.assertFalse(scope_report(self.root, 'blog')['passed'])

    def test_wrong_text_mode_and_missing_owner_fail(self):
        self.owners['/blogs/post/article-109'].update(kind='text_guide', reason='Invalid exception')
        del self.owners['/blogs/post/article-110']
        self.save()
        self.assertFalse(scope_report(self.root, 'blog')['passed'])

    def test_same_original_recompressed_does_not_pass(self):
        for slug in ('article-109', 'article-110'):
            self.assets[slug]['source_sha256'] = 'same original source'
        self.save()
        self.assertTrue(any('Same original' in error for error in scope_report(self.root, 'blog')['errors']))

    def test_full_completion_requires_all_28_source_backed_country_decisions(self):
        (self.root / 'content/export').mkdir()
        (self.root / 'content/export/export.json').write_text(json.dumps({'countries': [{'slug': str(i)} for i in range(28)]}), encoding='utf-8')
        for i in range(28):
            self.owners['/export/' + str(i)].update(kind='text_guide', status='approved', reason='Reviewed compact country guide')
        self.save()
        report = scope_report(self.root)
        self.assertTrue(report['passed'])
        self.assertEqual(report['required_owners'], 185)
        self.assertTrue(report['full_migration_complete'])
        self.assertEqual(scope_report(self.root, 'blog')['required_owners'], 157)
        self.owners['/export/unregistered'] = self.owners.pop('/export/27')
        self.save()
        self.assertFalse(scope_report(self.root)['passed'])


if __name__ == '__main__':
    unittest.main()
