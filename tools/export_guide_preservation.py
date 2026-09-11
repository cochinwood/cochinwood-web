"""Exact authored-content baseline for the 28 destination guides and Export hub.

The baseline predates the approved removal of decorative country hero imagery.
Only hero media is omitted from the semantic comparison; copy, links, anchors,
tables, sharing metadata and structured data must remain unchanged.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from site_preservation import Document, HIDDEN

BASELINE = ROOT / 'tools/fixtures/export-guide-preservation-pr34.json'
BLOCKS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'td', 'th',
          'dt', 'dd', 'caption', 'figcaption', 'blockquote', 'pre'}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def signature(markup):
    doc = Document(markup)
    main = next(n for n in doc.nodes if n.tag == 'main')
    def included(node):
        ancestry = list(node.ancestors())
        return main in ancestry and not any(
            n.tag in HIDDEN or 'cw-page-hero__media' in n.attrs.get('class', '').split()
            for n in ancestry)
    data = {
        'blocks': [(n.tag, n.text()) for n in doc.nodes if included(n) and n.tag in BLOCKS],
        'links': [(n.attrs.get('href'), n.text()) for n in doc.nodes if included(n) and n.tag == 'a'],
        'anchors': [n.attrs['id'] for n in doc.nodes if included(n) and n.attrs.get('id')],
        'tables': [n.text() for n in doc.nodes if included(n) and n.tag == 'table'],
        'schemas': [json.loads(''.join(c for c in n.children if isinstance(c, str)))
                    for n in doc.nodes if n.tag == 'script' and n.attrs.get('type') == 'application/ld+json'],
        'metadata': [(n.tag, n.text() if n.tag == 'title' else n.attrs)
                     for n in doc.nodes if n.tag == 'title'
                     or (n.tag == 'link' and n.attrs.get('rel') == 'canonical')
                     or (n.tag == 'meta' and (n.attrs.get('name') in {'description', 'twitter:image'}
                                            or n.attrs.get('property', '').startswith('og:')))],
    }
    return {key: {'count': len(value), 'sha256': digest(value)} for key, value in data.items()}


def routes():
    data = json.loads((ROOT / 'content/export/export.json').read_text(encoding='utf-8'))
    slugs = {c['slug'] for c in data['countries']}
    for path in (ROOT / 'content/export/countries').glob('*.json'):
        slugs.add(json.loads(path.read_text(encoding='utf-8')).get('slug', path.stem))
    if len(slugs) != 28:
        raise ValueError('Expected exactly 28 source destination guides')
    return ['/export'] + ['/export/' + slug for slug in sorted(slugs)]


def inspect(dist):
    return {route: signature((dist / (route.lstrip('/') + '.html')).read_text(encoding='utf-8'))
            for route in routes()}


def source_hashes():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / 'content/export').rglob('*'))
            if p.is_file() and (p.suffix == '.json' or p.name.endswith('.body.html'))}


def compare(dist):
    baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
    current = inspect(dist)
    errors = []
    for route in sorted(set(baseline['pages']) | set(current)):
        before, after = baseline['pages'].get(route), current.get(route)
        if before != after:
            fields = [key for key in (before or after) if not before or not after or before.get(key) != after.get(key)]
            errors.append({'route': route, 'changed_fields': fields})
    if source_hashes() != baseline['source_files']:
        errors.append({'source_files': 'Export research, prose or source data changed'})
    return {'status': 'PASS' if not errors else 'FAIL', 'pages': len(current),
            'country_guides': len(current) - 1, 'errors': errors}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dist', type=Path, default=ROOT / 'dist')
    parser.add_argument('--capture', action='store_true', help='One-time capture; refuses an existing baseline')
    args = parser.parse_args()
    if args.capture:
        if BASELINE.exists():
            raise SystemExit('Refusing to overwrite the reviewed pre-change baseline')
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps({'description': 'PR34 output before country-guide hero removal; only decorative hero media excluded',
                                      'pages': inspect(args.dist), 'source_files': source_hashes()},
                                     indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
        print('Captured 29 pages and exact export source hashes')
    else:
        report = compare(args.dist)
        print(json.dumps(report, ensure_ascii=False))
        raise SystemExit(bool(report['errors']))
