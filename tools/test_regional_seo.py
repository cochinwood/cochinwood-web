"""Existing-market coverage and Google image-sitemap integration contracts."""
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from regional_seo import load_coverage, render_market_directory, render_regional_navigation, image_sitemap_xml, write_image_sitemap, SITEMAP_NS, IMAGE_NS
from site_preservation import Document


class CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coverage = load_coverage(ROOT)

    def test_all_existing_countries_and_cities_once(self):
        c = self.coverage
        self.assertEqual(c['counts']['approved_export_markets'], 28)
        self.assertEqual(c['counts']['city_guides'], 109)
        self.assertEqual(c['counts']['products'], 16)
        groups = c['domestic_groups'] + [g for country in c['countries'] for g in country['city_groups']]
        paths = [city['path'] for g in groups for city in g['cities']]
        self.assertEqual(len(paths), len(set(paths)))
        directory = render_market_directory(c)
        document = Document(directory)
        hrefs = [n.attrs['href'] for n in document.nodes if n.tag == 'a']
        self.assertTrue(all(hrefs.count(path) == 1 for path in paths))
        self.assertTrue(all(hrefs.count(country['path']) == 1 for country in c['countries']))

    def test_each_city_has_country_or_state_parent_and_no_self_link(self):
        c = self.coverage
        for group in c['domestic_groups'] + [g for country in c['countries'] for g in country['city_groups']]:
            for city in group['cities']:
                with self.subTest(city=city['name']):
                    nav = render_regional_navigation(city['path'], c)
                    self.assertIn('All supply markets', nav)
                    self.assertNotIn('href="' + city['path'] + '"', nav)
                    self.assertIn('/supply-markets#' if group['country_iso'] == 'IN' else '/export/', nav)
        self.assertEqual(render_regional_navigation('/marine-plywood', c), '')

    def test_directory_anchor_targets_exist(self):
        doc = Document(render_market_directory(self.coverage))
        ids = {n.attrs['id'] for n in doc.nodes if n.attrs.get('id')}
        anchors = [n.attrs['href'][1:] for n in doc.nodes if n.tag == 'a' and n.attrs.get('href', '').startswith('#')]
        self.assertTrue(set(anchors).issubset(ids))


class ImageSitemapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'files').mkdir()
        (self.root / 'files/Panel & wood.jpg').write_bytes(b'photo')
        (self.root / 'files/other.webp').write_bytes(b'other')

    def tearDown(self):
        self.temp.cleanup()

    def page(self, name, body, extra_head=''):
        route = '/' if name == 'index' else '/' + name
        (self.root / (name + '.html')).write_text('<link rel="canonical" href="https://www.cochinwood.in' + route + '">' + extra_head + '<header><img src="/files/logo.png"></header><main>' + body + '</main>', encoding='utf8')

    def test_canonical_lazy_images_are_deduplicated_and_xml_escaped(self):
        image = '<img src="/files/Panel%20%26%20wood.jpg" loading="lazy" width="800" height="600" alt="Panel">'
        self.page('index', image + image + '<img src="/files/other.webp" aria-hidden="true">')
        xml, report = image_sitemap_xml(self.root, 'https://www.cochinwood.in')
        tree = ET.fromstring(xml)
        images = tree.findall('.//{' + IMAGE_NS + '}loc')
        self.assertEqual(len(images), 1)
        self.assertIn('Panel%20&%20wood.jpg', images[0].text)
        self.assertEqual(report['image_placements'], 1)
        self.assertNotIn('image:caption', xml)
        self.assertNotIn('lastmod', xml)

    def test_noindex_pages_are_excluded_and_missing_images_fail(self):
        self.page('private', '<img src="/files/missing.jpg">', '<meta name="robots" content="noindex, follow">')
        self.page('public', '<img src="/files/missing.jpg">')
        xml, report = image_sitemap_xml(self.root, 'https://www.cochinwood.in')
        self.assertEqual(len(report['missing_images']), 1)
        self.assertEqual(report['missing_images'][0]['page'], 'https://www.cochinwood.in/public')
        with self.assertRaises(ValueError):
            write_image_sitemap(self.root, 'https://www.cochinwood.in')

    def test_duplicate_canonical_is_rejected(self):
        self.page('one', '<img src="/files/other.webp">')
        (self.root / 'two.html').write_bytes((self.root / 'one.html').read_bytes())
        with self.assertRaises(ValueError):
            image_sitemap_xml(self.root, 'https://www.cochinwood.in')


if __name__ == '__main__':
    unittest.main()
