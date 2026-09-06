#!/usr/bin/env python3
"""Offline commerce review and gated Merchant export. Never submits or publishes."""
import argparse
import csv
import datetime
import hashlib
import html
import io
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
APPROVED_HOSTS = {'www.cochinwood.in', 'cochinwood.in'}
FAMILIES = {'prem_hw_gurjan', 'prem_marine_gurjan'}
FEED_FIELDS = ['id', 'title', 'description', 'link', 'image_link', 'availability',
               'price', 'condition', 'brand', 'gtin', 'mpn', 'identifier_exists',
               'item_group_id', 'size', 'shipping_label', 'unit_pricing_measure',
               'unit_pricing_base_measure']


def integer(value, minimum=0):
    return type(value) is int and minimum <= value <= 100_000_000


def words(value, maximum=5000):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum and not any(ord(x) < 32 for x in value)


def dated(value):
    try:
        return isinstance(value, str) and datetime.datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False


def money(paise):
    return f'{paise // 100}.{paise % 100:02d}'


def public_url(value):
    if not isinstance(value, str):
        return False
    try:
        u = urlsplit(value)
        return (u.scheme == 'https' and u.hostname in APPROVED_HOSTS
                and not u.username and not u.password and not u.fragment
                and u.port in (None, 443) and u.path not in ('', '/')
                and not any(x in u.path for x in ('commerce-preview', '/contact')))
    except ValueError:
        return False


def valid_gtin(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:\d{8}|\d{12}|\d{13}|\d{14})', value) or set(value) == {'0'}:
        return False
    digits = list(map(int, value))
    total = sum(n * (3 if i % 2 == 0 else 1) for i, n in enumerate(reversed(digits[:-1])))
    return (10 - total % 10) % 10 == digits[-1]


def issues(config, release=True):
    errors = []
    def need(ok, path, message):
        if not ok:
            errors.append({'field': path, 'required': message})
    if not isinstance(config, dict):
        return [{'field':'configuration', 'required':'Configuration must be a JSON object'}]
    for section in ('approval', 'tax', 'delivery', 'policies', 'payment', 'merchant'):
        need(isinstance(config.get(section), dict), section, 'Configuration section must be an object')
    products = config.get('products')
    need(isinstance(products, list) and all(isinstance(p, dict) for p in products), 'products', 'Products must be an array of objects')
    if errors:
        return errors
    rules = config['delivery'].get('rules')
    need(isinstance(rules, list) and all(isinstance(r, dict) for r in rules), 'delivery.rules', 'Delivery rules must be an array of objects')
    if errors:
        return errors
    need(config.get('schema_version') == 1, 'schema_version', 'Supported schema version 1')
    need(config.get('currency') == 'INR', 'currency', 'INR pricing')
    approval = config.get('approval', {})
    need(approval.get('status') == 'approved' and words(approval.get('approved_by')) and dated(approval.get('approved_at')),
         'approval', 'Company approval with approver and date')
    tax = config.get('tax', {})
    need(tax.get('approved') is True and tax.get('mode') == 'inclusive'
         and integer(tax.get('rate_basis_points')) and tax['rate_basis_points'] <= 10000,
         'tax', 'Approved tax-inclusive price and tax rate')
    products = config.get('products', [])
    need(isinstance(products, list) and bool(products), 'products', 'At least one approved variant')
    need(isinstance(products, list) and any(p.get('active') is True for p in products),
         'products.active', 'At least one active approved variant')
    seen = set()
    for p in products if isinstance(products, list) else []:
        sku = p.get('sku', '')
        prefix = f'products.{sku or "missing-sku"}'
        need(isinstance(sku, str) and bool(re.fullmatch(r'[a-z0-9_]{3,50}', sku)) and sku not in seen,
             prefix + '.sku', 'Unique stable SKU, up to 50 characters')
        if isinstance(sku, str): seen.add(sku)
        need(p.get('staff_product_key') in FAMILIES, prefix + '.staff_product_key', 'Approved proposed product family; no commercial/packing')
        need(p.get('product_identity_approved') is True, prefix + '.identity', 'Exact product identity approved')
        need(words(p.get('name'), 100) and words(p.get('description'), 5000) and words(p.get('brand'), 70),
             prefix + '.copy', 'Product name, description and genuine brand')
        need(words(p.get('size'), 100), prefix + '.size', 'Confirmed sheet size')
        need(type(p.get('active')) is bool, prefix + '.active', 'Explicit active or inactive selection')
        need(p.get('thickness_mm') in (12, 18) and type(p.get('thickness_mm')) is int
             and sku == f"{p.get('staff_product_key')}_{p.get('thickness_mm')}",
             prefix + '.thickness_mm', 'Selected 12 mm or 18 mm variant with matching SKU')
        dims = p.get('finished_dimensions_mm') or {}
        if not isinstance(dims, dict): dims = {}
        need(integer(dims.get('length'), 1) and integer(dims.get('width'), 1)
             and dims['length'] <= 5000 and dims['width'] <= 5000, prefix + '.dimensions', 'Confirmed finished dimensions')
        need(isinstance(p.get('tolerance_mm'), (int, float)) and not isinstance(p.get('tolerance_mm'), bool)
             and 0 <= p['tolerance_mm'] <= 10, prefix + '.tolerance_mm', 'Confirmed dimensional tolerance')
        need(integer(p.get('unit_price_paise'), 1), prefix + '.unit_price_paise', 'Positive tax-inclusive price in paise')
        need(integer(p.get('stock')) and p['stock'] <= 1_000_000, prefix + '.stock', 'Actual stock allocated to online sales, within supported limits')
        minimum, maximum = p.get('min_quantity'), p.get('max_quantity')
        need(integer(minimum, 1) and integer(maximum, 1) and minimum <= maximum <= 10000,
             prefix + '.quantity_limits', 'Approved minimum and maximum sheet quantity')
        need(p.get('identifiers_reviewed') is True, prefix + '.identifiers', 'Review real GTIN/MPN; never invent identifiers')
        gtin, mpn = p.get('gtin'), p.get('mpn')
        need(not gtin or valid_gtin(gtin), prefix + '.gtin', 'Valid genuine GTIN with correct checksum')
        need(mpn in (None, '') or words(mpn, 70), prefix + '.mpn', 'Genuine manufacturer part number')
        need(bool(gtin or mpn) or p.get('identifiers_not_assigned') is True,
             prefix + '.identifier_exists', 'Confirm identifiers are not assigned when absent')
        if release:
            need(public_url(p.get('product_url')), prefix + '.product_url', 'Live purchasable product URL on company domain')
            need(p.get('image_approved') is True and public_url(p.get('actual_product_photo_url')),
                 prefix + '.actual_product_photo_url', 'Approved exact-product photograph, not a generic preview')
    delivery = config.get('delivery', {})
    need(delivery.get('approved') is True and delivery.get('state') == 'Kerala'
         and delivery.get('country') == 'IN', 'delivery.approval', 'Approved Kerala-only delivery rules')
    rules = delivery.get('rules', [])
    need(bool(rules), 'delivery.rules', 'Exact serviceable postcode/quantity bands, freight and delivery windows')
    bands = {}
    rule_ids = set()
    for r in rules:
        rid = r.get('id')
        need(isinstance(rid, str) and rid and rid not in rule_ids, 'delivery.rule_id', 'Unique delivery rule ID')
        if isinstance(rid, str): rule_ids.add(rid)
        low, high = r.get('min_quantity'), r.get('max_quantity')
        valid_band = integer(low, 1) and integer(high, 1) and low <= high <= 10000
        need(valid_band, f'delivery.{rid}.quantity', 'Valid sheet quantity band')
        need(integer(r.get('shipping_paise')), f'delivery.{rid}.shipping_paise', 'Approved freight amount; zero only if explicitly free')
        need(integer(r.get('min_days')) and integer(r.get('max_days')) and r['min_days'] <= r['max_days'],
             f'delivery.{rid}.days', 'Approved earliest/latest delivery days')
        need(isinstance(r.get('postcodes'), list) and bool(r.get('postcodes')), f'delivery.{rid}.postcodes', 'Exact supported postcodes')
        for postcode in r.get('postcodes', []) if isinstance(r.get('postcodes'), list) else []:
            need(isinstance(postcode, str) and bool(re.fullmatch(r'\d{6}', postcode)), f'delivery.{rid}.postcode', 'Six-digit Indian postcode confirmed serviceable in Kerala')
            if valid_band:
                prior = bands.setdefault(str(postcode), [])
                need(not any(low <= b and high >= a for a, b in prior), f'delivery.{postcode}.overlap', 'Non-overlapping postcode/quantity rules')
                prior.append((low, high))
    # Each advertised minimum offer must be deliverable somewhere in the approved
    # service area. Buying additional goods cannot be a hidden condition of its price.
    for p in products:
        minimum = p.get('min_quantity')
        if p.get('active') is True and integer(minimum, 1):
            covered = any(isinstance(r.get('postcodes'), list) and r['postcodes']
                          and integer(r.get('min_quantity'), 1) and integer(r.get('max_quantity'), 1)
                          and r['min_quantity'] <= minimum <= r['max_quantity'] for r in rules)
            need(covered, f"products.{p.get('sku')}.delivery_coverage", 'The advertised minimum purchase must match an approved delivery rule')
    policies = config.get('policies', {})
    need(policies.get('approved') is True and policies.get('version'), 'policies.approval', 'Approved versioned online policies')
    for field in ('unloading', 'damage_reporting', 'cancellation', 'refunds'):
        need(words(policies.get(field)), f'policies.{field}', 'Company-approved service terms')
    if release:
        need(config.get('synthetic') is False, 'synthetic', 'Synthetic fixtures can never be submitted')
        for field in ('delivery_url', 'returns_url', 'cancellation_url'):
            need(public_url(policies.get(field)), f'policies.{field}', 'Published approved policy URL')
        payment = config.get('payment', {})
        for field in ('enabled', 'uat_passed', 'commercial_terms_approved'):
            need(payment.get(field) is True, f'payment.{field}', 'Verified bank integration and approved written terms')
        merchant = config.get('merchant', {})
        for field in ('enabled', 'checkout_verified', 'landing_pages_verified', 'shipping_verified', 'returns_verified'):
            need(merchant.get(field) is True, f'merchant.{field}', 'Recorded live launch verification')
    return errors


def records(config):
    """One source for feed and structured offers; minimum basket price is explicit."""
    rows, structured = [], []
    for p in config['products']:
        if not p.get('active', True):
            continue
        minimum = p['min_quantity']
        title = f"{p['name']} plywood — {p['size']} — {p['thickness_mm']} mm"
        if minimum > 1:
            title += f' — {minimum} sheets minimum'
        price = money(p['unit_price_paise'] * minimum)
        available = p['stock'] >= minimum
        row = dict(id=p['sku'], title=title, description=p['description'], link=p['product_url'],
                   image_link=p['actual_product_photo_url'], availability='in_stock' if available else 'out_of_stock',
                   price=price + ' INR', condition='new', brand=p['brand'], gtin=p.get('gtin') or '', mpn=p.get('mpn') or '',
                   identifier_exists='yes' if p.get('gtin') or p.get('mpn') else 'no', item_group_id=p['staff_product_key'],
                   size=f"{p['size']} × {p['thickness_mm']} mm", shipping_label='kerala-approved-postcodes',
                   unit_pricing_measure=f'{minimum} ct', unit_pricing_base_measure='1 ct')
        rows.append(row)
        product = {'@context':'https://schema.org', '@type':'Product', 'sku':p['sku'], 'name':title,
                   'description':p['description'], 'image':[p['actual_product_photo_url']],
                   'brand':{'@type':'Brand','name':p['brand']},
                   'offers':{'@type':'Offer','url':p['product_url'],'priceCurrency':'INR','price':price,
                             'availability':'https://schema.org/' + ('InStock' if available else 'OutOfStock'),
                             'itemCondition':'https://schema.org/NewCondition',
                             'eligibleQuantity':{'@type':'QuantitativeValue','minValue':minimum,'maxValue':p['max_quantity'],'unitCode':'H87'}}}
        if p.get('gtin'): product['gtin'] = p['gtin']
        if p.get('mpn'): product['mpn'] = p['mpn']
        structured.append(product)
    return rows, structured


def feed_xml(rows):
    ET.register_namespace('g', 'http://base.google.com/ns/1.0')
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    for k, v in {'title':'Cochin Wood approved online catalogue', 'link':'https://www.cochinwood.in/',
                 'description':'Approved purchasable plywood variants; Kerala delivery restrictions apply.'}.items():
        ET.SubElement(channel, k).text = v
    for row in rows:
        item = ET.SubElement(channel, 'item')
        for k, v in row.items():
            if v: ET.SubElement(item, '{http://base.google.com/ns/1.0}' + k).text = v
    return ET.tostring(rss, encoding='unicode', xml_declaration=True) + '\n'


def review_html(config, errors):
    esc = lambda v: html.escape(str(v if v is not None else 'Needs confirmation'))
    rows = ''.join('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in (
        p['sku'], p['name'], f"{p['size']} / {p['thickness_mm']} mm",
        '₹' + money(p['unit_price_paise']) if integer(p.get('unit_price_paise'), 1) else None,
        p.get('stock'), p.get('min_quantity'), p.get('max_quantity'))) + '</tr>' for p in config['products'])
    blockers = ''.join(f"<li><strong>{esc(e['field'])}</strong><br>{esc(e['required'])}</li>" for e in errors)
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Cochin Wood · Catalogue review</title>
<style>body{font:16px/1.65 system-ui;background:#faf9f7;color:#1b4332;margin:0}main{max-width:1120px;margin:auto;padding:32px 24px}h1{font-size:clamp(2rem,5vw,3rem);line-height:1.15}a{color:#007a5e}table{border-collapse:collapse;width:100%;min-width:780px}td,th{text-align:left;border-bottom:1px solid #ccd6ce;padding:12px}li{margin-bottom:12px;overflow-wrap:anywhere}.table{overflow:auto}.notice{padding:16px 20px;background:#e5efe9;border-left:4px solid #007a5e}h2{margin-top:40px}nav{display:flex;gap:24px}</style>
<main><nav><a href="/commerce-preview/">Shop preview</a><a href="/commerce-preview/staff.html">Staff preview</a></nav>
<h1>Review the online catalogue.</h1><p class="notice">Internal preparation. Purchasing and Google Shopping are disabled. Blank fields need company confirmation.</p>
<p>Premium Hardwood and Premium Marine plywood only. Proposed 8 × 4 ft sheets in 12 mm and 18 mm. Kerala delivery initially. Custom, bulk and export enquiries keep the quotation journey.</p>
<div class="table" role="region" aria-label="Proposed catalogue" tabindex="0"><table><thead><tr><th>SKU</th><th>Product</th><th>Proposed size</th><th>Price including tax</th><th>Online stock</th><th>Minimum</th><th>Maximum</th></tr></thead><tbody>''' + rows + '''</tbody></table></div>
<h2>Delivery and service terms</h2><p>Confirm exact postcodes, delivery charges by quantity, delivery windows, unloading responsibility, damage reporting, cancellation and refunds. A Kerala label alone does not establish serviceability.</p>
<h2>Launch requirements</h2><ul>''' + blockers + '''</ul><p>This checklist evaluates the supplied configuration. It does not certify bank activation, legal terms or Google's approval.</p></main></html>'''


def prepare(config_path, output, release=False):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    # Invalidate before reading/parsing/rendering anything; malformed input must
    # not leave old offers or a prior ready=true report eligible for publication.
    report = {'ready_for_merchant_export':False, 'submitted':False, 'errors':[]}
    def save_report():
        (output/'readiness.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8', newline='\n')
    save_report()
    for name in ('merchant-feed.xml', 'merchant-feed.tsv', 'product-offers.json'):
        (output/name).unlink(missing_ok=True)
    (output/'index.html').write_text('<!doctype html><meta name="robots" content="noindex,nofollow"><title>Catalogue review unavailable</title><h1>Catalogue review unavailable</h1><p>The current configuration has not passed review. No feed is ready.</p>', encoding='utf-8')
    try:
        raw = Path(config_path).read_bytes()
        config = json.loads(raw)
        errors = issues(config, release=True)
        report.update(config_sha256=hashlib.sha256(raw).hexdigest(), version=config.get('version') if isinstance(config, dict) else None,
                      synthetic=config.get('synthetic') if isinstance(config, dict) else None, errors=errors,
                      proposed_variants=len(config.get('products', [])) if isinstance(config, dict) and isinstance(config.get('products'), list) else 0)
        # A readable review is useful for structurally normal, incomplete proposals.
        page = review_html(config, errors)
        (output/'index.html').write_text(page, encoding='utf-8', newline='\n')
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        report['errors'].append({'field':'configuration', 'required':'Correct the unreadable or malformed configuration: ' + str(exc)})
        save_report()
        return report
    if release and not errors:
        rows, structured = records(config)
        (output/'merchant-feed.xml').write_text(feed_xml(rows), encoding='utf-8', newline='\n')
        buffer = io.StringIO(newline='')
        writer = csv.DictWriter(buffer, FEED_FIELDS, delimiter='\t', lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
        (output/'merchant-feed.tsv').write_text(buffer.getvalue(), encoding='utf-8', newline='\n')
        (output/'product-offers.json').write_text(json.dumps(structured, indent=2, ensure_ascii=False)+'\n', encoding='utf-8', newline='\n')
    report['ready_for_merchant_export'] = not errors
    save_report()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'commerce-preview/config/catalogue.proposed.json')
    parser.add_argument('--output', type=Path, default=ROOT/'commerce-preview/readiness')
    parser.add_argument('--release', action='store_true', help='Write local feed only if every company/payment/launch gate passes; never uploads')
    args = parser.parse_args()
    report = prepare(args.config, args.output, args.release)
    print(json.dumps({'readiness':str(args.output/'readiness.json'), 'blockers':len(report['errors']),
                      'feed_written':args.release and report['ready_for_merchant_export'], 'submitted':False}))
    raise SystemExit(2 if args.release and report['errors'] else 0)
