"""Market hierarchy and image discovery from approved, existing website data.

No build.py import and no external accounts/network calls. The generator owns
the page shell/CSS and calls these pure renderers; image sitemap runs after all
HTML and referenced assets have been written.
"""
from __future__ import annotations

from html import escape, unescape
import json
from pathlib import Path
import re
from urllib.parse import quote, unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

from site_preservation import Document, within, hidden

SITEMAP_NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
IMAGE_NS = 'http://www.google.com/schemas/sitemap-image/1.1'
DIRECTORY_PATH = '/supply-markets'


def slugify(value):
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')


def _plain(value):
    return Document(value).root.text()


def _product_paths():
    from catalogue_sections import PLYWOOD_GROUPS, PACKAGING
    return {'/' + slug for _, _, group in PLYWOOD_GROUPS for slug in group} | {'/' + slug for slug in PACKAGING} | {'/sawn-timber'}


def _product_references(source):
    products = _product_paths()
    return sorted({urlsplit(n.attrs['href']).path.rstrip('/') for n in Document(source).nodes
                   if n.tag == 'a' and n.attrs.get('href') and urlsplit(n.attrs['href']).path.rstrip('/') in products})


def load_coverage(root):
    """Return a validated 28-country/109-city matrix with observed product links.

    Market approval is inherited only from export-markets.json. City taxonomy
    groups already-published guides and is not evidence of a shipment. Product
    coverage means a source page links to that product, not territory stock.
    """
    root = Path(root)
    read = lambda relative: json.loads((root / relative).read_text(encoding='utf8'))
    approved = read('content/export-markets.json')
    taxonomy = read('content/regional-navigation.json')
    exports = read('content/export/export.json')['countries']
    exports += [json.loads(path.read_text(encoding='utf8')) for path in sorted((root / 'content/export/countries').glob('*.json'))]
    lanes = {item['slug']: item for item in exports}
    if len(lanes) != len(exports):
        raise ValueError('Duplicate export country source')
    posts = read('content/blog/posts.json')
    cities = {post['slug'].removeprefix('plywood-supply-to-'): post for post in posts if post['slug'].startswith('plywood-supply-to-')}
    groups, used = [], set()
    approved_isos = {country['iso'] for group in approved['groups'] for country in group['countries']}
    for group in taxonomy['city_groups']:
        if group['country_iso'] not in approved_isos | {approved['domestic']['iso']}:
            raise ValueError('City taxonomy contains an unapproved market')
        result = {'country_iso': group['country_iso'], 'region': group['region'],
                  'anchor': group['country_iso'].lower() + '-' + slugify(group['region']), 'cities': []}
        for slug in group['cities']:
            if slug in used or slug not in cities:
                raise ValueError('Duplicate or missing city guide: ' + slug)
            used.add(slug)
            post = cities[slug]
            label = unescape(post['title']).split('—')[0].split('–')[0].split('|')[0].strip()
            label = re.sub(r'^Plywood Supply to\s+', '', label, flags=re.I).strip()
            result['cities'].append({'slug': slug, 'name': label, 'path': '/blogs/post/' + post['slug'],
                                     'date': post.get('date'), 'product_paths': _product_references(post['html'])})
        result['cities'].sort(key=lambda item: item['name'].casefold())
        groups.append(result)
    if used != set(cities):
        raise ValueError('Unmapped existing city guides: ' + ', '.join(sorted(set(cities) - used)))
    countries = []
    for continent in approved['groups']:
        for country in continent['countries']:
            slug = taxonomy.get('country_slug_overrides', {}).get(country['iso'], slugify(country['name']))
            if slug not in lanes:
                raise ValueError('Approved market lacks its existing country page: ' + slug)
            body = root / 'content/export' / (slug + '.body.html')
            source = body.read_text(encoding='utf8') if body.exists() else ''
            lane = lanes[slug]
            city_groups = [g for g in groups if g['country_iso'] == country['iso']]
            products = _product_references(source)
            countries.append({'iso': country['iso'], 'name': country['name'], 'continent': continent['continent'],
                              'path': '/export/' + slug, 'slug': slug, 'city_groups': city_groups,
                              'city_count': sum(len(g['cities']) for g in city_groups),
                              'product_paths': products,
                              'content_signals': {'source_body': str(body.relative_to(root)).replace('\\', '/') if body.exists() else None,
                                                  'country_specific_body': bool(source.strip()), 'import_table_template': bool(lane.get('import')),
                                                  'has_source_references': bool(re.search(r'href=["\']https?://', source)),
                                                  'country_title': _plain(lane.get('title', ''))},
                              'review_opportunities': (['Existing country body has no direct product-detail link; review useful product connections.'] if not products else [])})
    if {c['slug'] for c in countries} != set(lanes):
        raise ValueError('Published country pages differ from the approved country list')
    return {'version': 1, 'directory_path': DIRECTORY_PATH,
            'meaning': 'Coverage of existing editorial guides and links; not stock, premises, shipment proof, search demand or ranking evidence.',
            'counts': {'approved_export_markets': len(countries), 'continents': len(approved['groups']),
                       'country_pages': len(lanes), 'city_guides': len(cities),
                       'domestic_city_guides': sum(len(g['cities']) for g in groups if g['country_iso'] == 'IN'),
                       'international_city_guides': sum(len(g['cities']) for g in groups if g['country_iso'] != 'IN'),
                       'products': len(_product_paths())},
            'countries': countries, 'domestic_groups': [g for g in groups if g['country_iso'] == 'IN'],
            'prioritization': 'Rank future content work using actual Search Console country/query data and qualified enquiries; no demand or conversion evidence is inferred from page counts.'}


def _anchor(path, label, link, *, current=False):
    active = ' aria-current="page"' if current else ''
    return f'<a href="{escape(link(path), quote=True)}"{active}>{escape(label)}</a>'


def _city_list(cities, link, current_path=''):
    return '<ul class="cw-market-links">' + ''.join('<li>' + _anchor(city['path'], city['name'], link, current=city['path'] == current_path) + '</li>' for city in cities) + '</ul>'


def render_market_directory(coverage, link=lambda path: path):
    """Directory BODY sections only; root supplies title/hero/meta/breadcrumbs."""
    continents = list(dict.fromkeys(country['continent'] for country in coverage['countries']))
    jumps = [('india', 'India')] + [('region-' + slugify(name), name) for name in continents]
    jump_html = ''.join('<li>' + _anchor('#' + anchor, label, link) + '</li>' for anchor, label in jumps)
    domestic = ''.join(
        f'<details class="cw-market-group" id="{escape(group["anchor"])}"><summary>{escape(group["region"])} <span>{len(group["cities"])} guides</span></summary>'
        + _city_list(group['cities'], link) + '</details>' for group in sorted(coverage['domestic_groups'], key=lambda g: g['region']))
    regions = []
    for continent in continents:
        countries = []
        for country in coverage['countries']:
            if country['continent'] != continent:
                continue
            head = '<h3>' + _anchor(country['path'], country['name'], link) + '</h3>'
            cities = [city for group in country['city_groups'] for city in group['cities']]
            city_html = '<details><summary>City and industrial-area guides</summary>' + _city_list(cities, link) + '</details>' if cities else ''
            countries.append(f'<li class="cw-market-country" id="market-{country["iso"].lower()}">{head}{city_html}</li>')
        regions.append(f'<section class="cw-market-region" id="region-{slugify(continent)}"><h2>{escape(continent)}</h2><ul class="cw-market-countries">{"".join(countries)}</ul></section>')
    return f'''<section class="cw-section cw-markets-intro"><div class="cw-wrap">
      <p>Find country import guidance, city buying notes and the product specifications for your enquiry. Supply terms, the shipment route and any destination requirements are confirmed in your quote.</p>
      <nav class="cw-market-jumps" aria-label="Browse supply guides by region"><ul>{jump_html}</ul></nav>
      <section class="cw-market-region" id="india"><h2>India</h2><p>Browse existing city and industrial-area guides by state or region.</p><div class="cw-market-domestic">{domestic}</div></section>
      {''.join(regions)}
      <section class="cw-market-enquiry"><h2>Build a clear requirement.</h2><p>Include the product or application, grade, dimensions, quantity and destination. For export enquiries, add the destination port and the documents your clearing agent needs.</p>
        <div class="cw-hero__cta">{_anchor('/products', 'Browse product specifications', link)} {_anchor('/contact#quote', 'Request a quote', link)}</div></section>
    </div></section>'''


def render_regional_navigation(path, coverage, link=lambda path: path):
    """Native hierarchy for export/city pages. Returns '' for unrelated pages.

    All added text lives in a semantic nav so preservation tooling records it
    separately. Related locations are within the same country/state, not an
    arbitrary cyclic next/previous article sequence.
    """
    root_link = _anchor(DIRECTORY_PATH, 'All supply markets', link)
    if path == '/export':
        return f'<nav class="cw-regional-navigation" aria-label="Supply market navigation">{root_link} <span>Country and city buying guides</span></nav>'
    country = next((c for c in coverage['countries'] if c['path'] == path), None)
    if country:
        cities = [city for group in country['city_groups'] for city in group['cities']]
        details = '<details><summary>City guides in ' + escape(country['name']) + '</summary>' + _city_list(cities, link) + '</details>' if cities else ''
        return f'<nav class="cw-regional-navigation" aria-label="Supply market navigation">{root_link} {_anchor("/export", "Export buying guide", link)}{details}</nav>'
    groups = coverage['domestic_groups'] + [g for c in coverage['countries'] for g in c['city_groups']]
    for group in groups:
        if not any(city['path'] == path for city in group['cities']):
            continue
        country = next((c for c in coverage['countries'] if c['iso'] == group['country_iso']), None)
        parent = _anchor(country['path'], country['name'] + ' import guide', link) if country else _anchor(DIRECTORY_PATH + '#' + group['anchor'], group['region'] + ' guides', link)
        related = [city for city in group['cities'] if city['path'] != path]
        details = '<details><summary>Other guides in ' + escape(group['region']) + '</summary>' + _city_list(related, link) + '</details>' if related else ''
        return f'<nav class="cw-regional-navigation" aria-label="Supply market navigation">{root_link} {parent}{details}</nav>'
    return ''


def image_sitemap_xml(dist, live):
    """Return (XML, report) for canonical, indexable HTML main-content images.

    Only local image paths that actually exist are indexed. Picture/srcset
    variants represent the same placement; the fallback img src is its stable
    discovery URL. No deprecated caption/title/geolocation tags, synthetic
    dates or duplicate image records within a page are emitted.
    """
    dist = Path(dist).resolve()
    live = live.rstrip('/')
    host = urlsplit(live).netloc.lower()
    local_hosts = {host, host.removeprefix('www.'), 'www.' + host.removeprefix('www.')}
    root = ET.Element('urlset', {'xmlns': SITEMAP_NS, 'xmlns:image': IMAGE_NS})
    report = {'pages': 0, 'image_placements': 0, 'unique_images': 0, 'skipped_pages_without_images': 0, 'missing_images': [], 'external_images': []}
    all_images = set()
    canonical_pages = set()
    for file in sorted(dist.rglob('*.html')):
        if file.name == '404.html':
            continue
        doc = Document(file.read_text(encoding='utf8'))
        canonical = next((n.attrs.get('href') for n in doc.nodes if n.tag == 'link' and n.attrs.get('rel') == 'canonical'), None)
        if not canonical or urlsplit(canonical).netloc.lower() not in local_hosts:
            continue
        if any(n.tag == 'meta' and n.attrs.get('name', '').lower() in {'robots', 'googlebot'} and 'noindex' in n.attrs.get('content', '').lower() for n in doc.nodes):
            continue
        if canonical in canonical_pages:
            raise ValueError('Duplicate canonical page in image sitemap: ' + canonical)
        canonical_pages.add(canonical)
        images = []
        for node in doc.nodes:
            if node.tag != 'img' or not within(node, 'main') or hidden(node) or node.attrs.get('aria-hidden') == 'true' or node.attrs.get('role') == 'presentation':
                continue
            src = node.attrs.get('src', '')
            parsed = urlsplit(urljoin(canonical, src))
            if not src or src.startswith('data:'):
                continue
            if parsed.netloc.lower() not in local_hosts:
                report['external_images'].append({'page': canonical, 'src': src})
                continue
            relative = unquote(parsed.path).lstrip('/')
            target = (dist / relative).resolve()
            if not target.is_relative_to(dist) or not target.is_file():
                report['missing_images'].append({'page': canonical, 'src': src})
                continue
            # Favicons/logos and tiny interface glyphs are not editorial images.
            if Path(relative).suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp', '.avif', '.gif', '.svg'} or re.search(r'(?:^|/)(?:logo|favicon|icon)[^/]*\.', relative, re.I):
                continue
            if node.attrs.get('width', '').isdigit() and node.attrs.get('height', '').isdigit() and max(int(node.attrs['width']), int(node.attrs['height'])) < 100:
                continue
            url = live + quote('/' + relative, safe='/~!$&()*+,;=:@-._')
            if url not in images:
                images.append(url)
        if not images:
            report['skipped_pages_without_images'] += 1
            continue
        if len(images) > 1000:
            raise ValueError('Image sitemap per-page limit exceeded: ' + canonical)
        entry = ET.SubElement(root, 'url')
        ET.SubElement(entry, 'loc').text = canonical
        for image in images:
            ET.SubElement(ET.SubElement(entry, 'image:image'), 'image:loc').text = image
        report['pages'] += 1
        report['image_placements'] += len(images)
        all_images.update(images)
    report['unique_images'] = len(all_images)
    ET.indent(root, space='  ')
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode') + '\n', report


def write_image_sitemap(dist, live):
    """Write sitemap-images.xml and return coverage; fail on missing local media.

    Root must include its URL in sitemap.xml and/or robots.txt separately.
    """
    xml, report = image_sitemap_xml(dist, live)
    if report['missing_images']:
        raise ValueError('Missing sitemap images: ' + json.dumps(report['missing_images']))
    (Path(dist) / 'sitemap-images.xml').write_text(xml, encoding='utf8', newline='\n')
    return report
