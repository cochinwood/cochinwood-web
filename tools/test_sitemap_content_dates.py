"""Sitemap <lastmod> follows each page's own content; see sitemap_lastmod.py."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import sitemap_lastmod as SL

ORG = {'@context': 'https://schema.org', '@id': 'https://www.cochinwood.in/#organization',
       'sameAs': ['https://www.instagram.com/cochinwood/']}
PRODUCT = {'@context': 'https://schema.org', '@type': 'Product', 'name': 'Packing plywood',
           'additionalProperty': [{'@type': 'PropertyValue', 'name': 'Standard', 'value': 'IS 303'}]}


def page(main='<p>Packing plywood to IS 303.</p>', title='Packing plywood', desc='Packing plywood.',
         schemas=(ORG, PRODUCT), css='bundle.abc123.css', header='<header><a href="/">Home</a></header>',
         footer='<footer>Cochin Wood Industries</footer>', nav=''):
    ld = ''.join(f'<script type="application/ld+json">{json.dumps(s)}</script>' for s in schemas)
    return (f'<!doctype html><html><head><title>{title}</title><meta name="description" content="{desc}">'
            f'<link rel="canonical" href="https://www.cochinwood.in/packing-plywood">'
            f'<link rel="stylesheet" href="/assets/{css}">{ld}</head><body>{header}'
            f'<main id="main">{nav}{main}</main>{footer}</body></html>')


class FingerprintTests(unittest.TestCase):
    def test_site_chrome_assets_navigation_images_and_dates_are_not_content(self):
        base = SL.fingerprint(page())
        linked_org = dict(ORG, sameAs=ORG['sameAs'] + ['https://www.linkedin.com/company/cochin-wood-industries/'])
        for label, variant in {
                'site-wide Organization markup': page(schemas=(linked_org, PRODUCT)),
                'content-addressed stylesheet': page(css='bundle.def456.css'),
                'header links': page(header='<header><a href="/">Home</a><a href="/faq">FAQ</a></header>'),
                'footer text': page(footer='<footer>Cochin Wood Industries. CIN shown.</footer>'),
                'in-page navigation': page(nav='<nav class="cw-page-navigation"><a href="#x">Jump</a></nav>'),
                'image': page(main='<p>Packing plywood to IS 303.</p><img src="/files/new.webp" alt="Sheet">'),
                'figure caption': page(main='<p>Packing plywood to IS 303.</p><figure class="cw-editorial-media">'
                                            '<img src="/files/a.webp" alt=""><figcaption>Bundles.</figcaption></figure>'),
                'section switcher': page(nav='<div class="cw-section-bar"><details><summary>Sections</summary>'
                                             '<button type="button">More</button></details></div>'),
                'call-to-action band': page(main='<p>Packing plywood to IS 303.</p><section class="cwg__cta">'
                                                 '<h2>Need a plywood quote?</h2><a href="/contact">Request a quote</a></section>'),
                'species photo gallery': page(main='<p>Packing plywood to IS 303.</p><section class="cw-species-reference">'
                                                   '<h2>Photo references</h2></section>'),
                'hero buttons': page(main='<div class="cw-page-hero__actions"><a class="cw-page-hero__button" '
                                          'href="/contact#quote">Request a quote</a></div><p>Packing plywood to IS 303.</p>'),
                'structured-data image': page(schemas=(ORG, dict(PRODUCT, image='https://www.cochinwood.in/files/new.webp'))),
                'dateModified': page(schemas=(ORG, dict(PRODUCT, dateModified='2026-09-15'))),
        }.items():
            with self.subTest(label):
                self.assertEqual(SL.fingerprint(variant), base)

    def test_moving_a_block_is_not_a_content_change(self):
        # A template that moves the heading into a new hero wrapper keeps the same words.
        self.assertEqual(SL.fingerprint(page(main='<h1>Packing plywood</h1><p>To IS 303.</p>')),
                         SL.fingerprint(page(main='<div class="hero"><p>To IS 303.</p></div><h1>Packing plywood</h1>')))

    def test_copy_links_head_and_page_structured_data_are_content(self):
        base = SL.fingerprint(page())
        new_fact = dict(PRODUCT, additionalProperty=[{'@type': 'PropertyValue', 'name': 'Standard', 'value': 'IS 10418'}])
        for label, variant in {
                'Product markup only': page(schemas=(ORG, new_fact)),
                'visible copy': page(main='<p>Packing plywood to IS 710.</p>'),
                'title': page(title='Packing plywood sheets'),
                'meta description': page(desc='Packing plywood, 6 to 18 mm.'),
                'a link in the copy': page(main='<p>Packing plywood to <a href="/standards">IS 303</a>.</p>'),
        }.items():
            with self.subTest(label):
                self.assertNotEqual(SL.fingerprint(variant), base)


class ResolveTests(unittest.TestCase):
    def test_unchanged_keeps_its_published_date_changed_and_new_take_the_revision_date(self):
        dates, changed = SL.resolve({'/same': 'a', '/edited': 'b2', '/new': 'c'},
                                    {'/same': '2026-09-06', '/edited': '2026-09-06'},
                                    {'/same': 'a', '/edited': 'b1'}, '2026-09-15')
        self.assertEqual(dates, {'/same': '2026-09-06', '/edited': '2026-09-15', '/new': '2026-09-15'})
        self.assertEqual(changed, ['/edited', '/new'])

    def test_a_seed_date_applies_only_while_the_page_keeps_the_seeded_content(self):
        seed = {'/product': {'fingerprint': 'p', 'lastmod': '2026-09-15'},
                '/edited-since': {'fingerprint': 'old', 'lastmod': '2026-09-10'}}
        dates, changed = SL.resolve({'/product': 'p', '/edited-since': 'new'},
                                    {'/product': '2026-09-06', '/edited-since': '2026-09-06'},
                                    {'/product': 'p', '/edited-since': 'old'}, '2026-09-20', seed)
        self.assertEqual(dates, {'/product': '2026-09-15', '/edited-since': '2026-09-20'})
        self.assertEqual(changed, ['/edited-since'])


class PublishedTreeTests(unittest.TestCase):
    def git(self, root, *args, date=None):
        env = os.environ.copy()
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        subprocess.run(('git', *args), cwd=root, env=env, check=True, capture_output=True, text=True)

    def test_each_page_is_dated_by_its_own_change_and_rebuilds_are_identical(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.git(root, 'init', '-q')
            self.git(root, 'config', 'user.name', 'Sitemap Test')
            self.git(root, 'config', 'user.email', 'sitemap@example.invalid')
            self.git(root, 'config', 'core.autocrlf', 'false')
            published = {'product.html': page(), 'blogs/post/one.html': page(main='<p>One</p>'),
                         'blogs/post/two.html': page(main='<p>Two</p>')}
            for rel, markup in published.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(markup, encoding='utf-8', newline='\n')
            url = '  <url><loc>https://www.cochinwood.in{}</loc><lastmod>{}</lastmod></url>'
            (root / 'sitemap-cms.xml').write_text('<urlset>\n' + url.format('/product', '2026-09-06') + '\n</urlset>\n',
                                                  encoding='utf-8', newline='\n')
            (root / 'sitemap-post.xml').write_text('<urlset>\n' + url.format('/blogs/post/one', '2026-08-28') + '\n'
                                                   + url.format('/blogs/post/two', '2026-09-05') + '\n</urlset>\n',
                                                   encoding='utf-8', newline='\n')
            self.git(root, 'add', '-A')
            self.git(root, 'commit', '-qm', 'published tree', date='2026-09-12T12:00:00+0530')
            self.git(root, 'tag', 'published')
            (root / 'source.txt').write_text('source revision\n', encoding='utf-8')
            self.git(root, 'add', 'source.txt')
            self.git(root, 'commit', '-qm', 'source revision', date='2026-09-15T12:00:00+0530')

            built = {
                # only the Product markup changed: the page must be redated
                'product.html': page(schemas=(ORG, dict(PRODUCT, additionalProperty=[
                    {'@type': 'PropertyValue', 'name': 'Standard', 'value': 'IS 10418'}]))),
                # same article, new site chrome and asset hash: keeps its own date
                'blogs/post/one.html': page(main='<p>One</p>', css='bundle.new.css', footer='<footer>New</footer>'),
                'blogs/post/two.html': page(main='<p>Two, revised</p>'),
                'blogs/post/three.html': page(main='<p>Three</p>'),
            }
            urls = ['/product', '/blogs/post/one', '/blogs/post/two', '/blogs/post/three']
            result = SL.lastmods(urls, built.__getitem__, 'published', str(root))
            dates, changed, change_date = result
            self.assertEqual(change_date, '2026-09-15')
            self.assertEqual(dates, {'/product': '2026-09-15', '/blogs/post/one': '2026-08-28',
                                     '/blogs/post/two': '2026-09-15', '/blogs/post/three': '2026-09-15'})
            self.assertEqual(SL.lastmods(urls, built.__getitem__, 'published', str(root)), result)
            self.assertIsNone(SL.lastmods(urls, built.__getitem__, 'no-such-ref', str(root)))


if __name__ == '__main__':
    unittest.main()
