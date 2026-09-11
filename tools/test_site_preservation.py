"""Meaningful loss/reorder and exact-review tests, independent of the builder."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from site_preservation import compare, page_manifest, snapshot


FIXTURE = '''<!doctype html><html><head><title>Panel guide</title>
<link rel="canonical" href="https://www.cochinwood.in/guide"><meta name="description" content="Choose a panel.">
<script type="application/ld+json">{"@type":"Product","name":"Marine panel"}</script></head><body>
<nav><a href="/products">Products</a></nav><main><nav><a href="/">Home</a></nav>
<h1>Marine <em>plywood</em>.</h1><p>Specify 18 mm BWP for this application.</p>
<table><tr><th>Grade</th><th>Thickness</th></tr><tr><td>BWP</td><td>18 mm</td></tr></table>
<p>Confirm the written specification.</p><a href="/files/spec.pdf" download>Download specification</a>
<img src="/files/panel.jpg" width="800" height="600" alt="Panel edge">
<form action="/api/lead" method="post" data-pack="quote"><label>Quantity<input name="quantity" required></label>
<select name="grade"><option value="bwp">BWP</option></select><button type="submit">Send</button></form>
<style>.hidden{content:"fake text"}</style><script>"ignore this"</script></main></body></html>'''


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'files').mkdir()
        (self.root / 'files/spec.pdf').write_bytes(b'%PDF-original-spec')
        (self.root / 'files/panel.jpg').write_bytes(b'original-photo')
        (self.root / '_redirects').write_text('/old /guide 301\n')
        self.write(FIXTURE)
        self.baseline = snapshot(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, source):
        (self.root / 'guide.html').write_text(source, encoding='utf8')

    def test_unchanged_baseline_passes(self):
        self.assertTrue(compare(self.baseline, snapshot(self.root))['passed'])

    def test_order_is_preserved_even_when_word_counts_match(self):
        source = FIXTURE.replace('<p>Specify 18 mm BWP for this application.</p>', '')
        source = source.replace('<p>Confirm the written specification.</p>', '<p>Confirm the written specification.</p><p>Specify 18 mm BWP for this application.</p>')
        self.write(source)
        result = compare(self.baseline, snapshot(self.root))
        self.assertFalse(result['passed'])
        self.assertTrue(any(c['field'] == 'content' for c in result['changes']))

    def test_specification_cell_mutation_is_explicit(self):
        self.write(FIXTURE.replace('<td>18 mm</td>', '<td>12 mm</td>'))
        changes = compare(self.baseline, snapshot(self.root))['changes']
        self.assertTrue(any(c['field'] == 'tables' for c in changes))

    def test_download_and_original_photo_hashes_cannot_disappear(self):
        (self.root / 'files/spec.pdf').unlink()
        (self.root / 'files/panel.jpg').write_bytes(b'replaced')
        changes = compare(self.baseline, snapshot(self.root))['changes']
        self.assertEqual({c['route'] for c in changes if c['field'] == 'file'}, {'/files/spec.pdf', '/files/panel.jpg'})

    def test_metadata_form_schema_and_reference_mutations_fail(self):
        variants = [
            ('Choose a panel.', 'Cheap plywood.', 'metadata.description'),
            ('name="quantity" required', 'name="quantity"', 'forms'),
            ('"name":"Marine panel"', '"name":"Fake panel"', 'schemas'),
            ('href="/files/spec.pdf"', 'href="/files/wrong.pdf"', 'downloads'),
        ]
        for before, after, field in variants:
            with self.subTest(field=field):
                self.write(FIXTURE.replace(before, after))
                result = compare(self.baseline, snapshot(self.root))
                self.assertFalse(result['passed'])
                self.assertTrue(any(c['field'] == field for c in result['changes']))

    def test_exact_review_is_not_a_blanket_caption_exemption(self):
        self.write(FIXTURE.replace('Panel edge', 'Plywood edge and face'))
        report = compare(self.baseline, snapshot(self.root))
        approvals = {'changes': [{'id': c['id'], 'reviewed_by': 'test reviewer', 'reason': 'Reviewed the exact replacement image description.'} for c in report['changes']]}
        self.assertTrue(compare(self.baseline, snapshot(self.root), approvals)['passed'])
        self.write(FIXTURE.replace('Panel edge', 'Unreviewed species claim'))
        self.assertFalse(compare(self.baseline, snapshot(self.root), approvals)['passed'])

    def test_navigation_addition_does_not_mask_copy_removal(self):
        added = FIXTURE.replace('<main>', '<main><nav><a href="/supply-markets">Supply markets</a></nav>')
        self.write(added)
        self.assertTrue(compare(self.baseline, snapshot(self.root))['passed'])
        self.write(added.replace('<p>Confirm the written specification.</p>', ''))
        self.assertFalse(compare(self.baseline, snapshot(self.root))['passed'])

    def test_scripts_and_style_are_not_substantive_copy(self):
        page = page_manifest(FIXTURE)
        self.assertNotIn('fake text', json.dumps(page['content']))
        self.assertNotIn('ignore this', json.dumps(page['content']))
        self.assertIn('Marine plywood .', json.dumps(page['content']))

    def test_footer_contact_copy_is_preserved_separately(self):
        old = FIXTURE.replace('</body>', '<footer><p>Call +91 95674 10175</p></footer></body>')
        self.write(old)
        baseline = snapshot(self.root)
        self.write(old.replace('+91 95674 10175', '+91 00000 00000'))
        changes = compare(baseline, snapshot(self.root))['changes']
        self.assertTrue(any(c['field'] == 'chrome_content' for c in changes))

    def test_route_removal_redirect_change_and_font_loss_fail(self):
        (self.root / 'assets').mkdir()
        (self.root / 'assets/font.woff2').write_bytes(b'font')
        baseline = snapshot(self.root)
        (self.root / 'assets/font.woff2').unlink()
        (self.root / 'guide.html').unlink()
        (self.root / '_redirects').write_text('/old /wrong 301\n')
        fields = {c['field'] for c in compare(baseline, snapshot(self.root))['changes']}
        self.assertTrue({'route_removed', 'redirects', 'file'}.issubset(fields))


if __name__ == '__main__':
    unittest.main()
