"""Independent, ordered-content release manifest and exact-change comparison.

This checker reads completed static output; it never imports or runs build.py.
Navigation is recorded separately from substantive main content. New navigation,
images and pages are reported, while every removed/changed baseline value needs
an exact reviewed allowance. An allowance matches a full before/after delta hash,
not a regex, URL glob, count or broad exemption.

python site_preservation.py snapshot DIST --out baseline.json
python site_preservation.py compare baseline.json DIST --report report.json
python site_preservation.py compare baseline.json DIST --allow reviewed.json --report report.json
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
import difflib
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

VERSION = 1
VOID = set('area base br col embed hr img input link meta param source track wbr'.split())
HIDDEN = {'script', 'style', 'template', 'noscript'}
BLOCKS = set('h1 h2 h3 h4 h5 h6 p li dt dd th td figcaption summary label button option pre blockquote address legend'.split())
NAV_CLASSES = {'cw-page-navigation', 'cw-article-toc', 'cw-article-related', 'cw-article-next'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.zip', '.txt'}


def compact(value):
    return ' '.join(value.split())


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf8')).hexdigest()


@dataclass
class Node:
    tag: str
    attrs: dict
    parent: 'Node | None' = field(default=None, repr=False)
    children: list = field(default_factory=list, repr=False)

    def ancestors(self):
        node = self
        while node:
            yield node
            node = node.parent

    def text(self):
        return compact(' '.join(c if isinstance(c, str) else c.text() for c in self.children if isinstance(c, str) or c.tag not in HIDDEN))


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = Node('document', {})
        self.stack = [self.root]
        self.nodes = []
        self.tokens = []
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs), self.stack[-1])
        self.stack[-1].children.append(node)
        self.nodes.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)
        self.tokens.append((self.stack[-1], data))


def within(node, tag):
    return any(n.tag == tag for n in node.ancestors())


def navigation(node):
    return any(n.tag == 'nav' or NAV_CLASSES.intersection((n.attrs.get('class') or '').split()) for n in node.ancestors())


def hidden(node):
    # Deliberately do NOT treat CSS display:none or the hidden attr as harmless:
    # hiding existing copy still requires visual/accessibility checks separately.
    return any(n.tag in HIDDEN for n in node.ancestors())


def records(document, *, nav=False, outside_main=False):
    result = []
    previous = None
    for node, value in document.tokens:
        if within(node, 'main') == outside_main or within(node, 'head') or hidden(node) or navigation(node) != nav:
            continue
        block = next((n for n in node.ancestors() if n.tag in BLOCKS), node)
        if not compact(value):
            continue
        if previous is block:
            result[-1]['text'] = compact(result[-1]['text'] + ' ' + value)
        else:
            result.append({'tag': block.tag if block.tag in BLOCKS else 'text', 'text': compact(value)})
            previous = block
    return result


def local_path(url, live_hosts):
    parsed = urlsplit(url)
    if parsed.scheme not in ('', 'http', 'https') or (parsed.netloc and parsed.netloc.lower() not in live_hosts):
        return None
    if not parsed.path.startswith('/'):
        return None
    return unquote(parsed.path).lstrip('/')


def page_manifest(source):
    doc = Document(source)
    attrs = lambda n: {k: v for k, v in n.attrs.items() if k not in {'class', 'style'}}
    meta = {}
    for n in doc.nodes:
        if n.tag == 'meta' and (n.attrs.get('name') or n.attrs.get('property') or n.attrs.get('http-equiv')):
            key = n.attrs.get('name') or n.attrs.get('property') or n.attrs.get('http-equiv')
            meta.setdefault(key, []).append(n.attrs.get('content', ''))
    meta['title'] = [n.text() for n in doc.nodes if n.tag == 'title']
    meta['canonical'] = [n.attrs.get('href', '') for n in doc.nodes if n.tag == 'link' and n.attrs.get('rel') == 'canonical']
    meta['alternates'] = [attrs(n) for n in doc.nodes if n.tag == 'link' and n.attrs.get('rel') == 'alternate']
    schemas = []
    for n in doc.nodes:
        if n.tag == 'script' and n.attrs.get('type') == 'application/ld+json':
            raw = ''.join(c for c in n.children if isinstance(c, str))
            try:
                schemas.append(json.loads(raw))
            except json.JSONDecodeError:
                schemas.append({'INVALID_JSON': raw})
    tables = []
    for n in doc.nodes:
        if n.tag != 'table' or not within(n, 'main'):
            continue
        rows = []
        for row in doc.nodes:
            if row.tag != 'tr' or not any(a is n for a in row.ancestors()):
                continue
            rows.append([{'tag': c.tag, 'text': c.text(), 'colspan': c.attrs.get('colspan'), 'rowspan': c.attrs.get('rowspan')}
                         for c in row.children if isinstance(c, Node) and c.tag in {'td', 'th'}])
        tables.append(rows)
    forms = []
    for n in doc.nodes:
        if n.tag == 'form':
            controls = [{'tag': c.tag, 'attrs': attrs(c), 'text': c.text()}
                        for c in doc.nodes if c.tag in {'input', 'select', 'textarea', 'button', 'option'} and any(a is n for a in c.ancestors())]
            forms.append({'attrs': attrs(n), 'controls': controls})
    links = [{'href': n.attrs['href'], 'text': n.text(), 'download': n.attrs.get('download')}
             for n in doc.nodes if n.tag == 'a' and n.attrs.get('href') and within(n, 'main') and not navigation(n)]
    chrome_links = [{'href': n.attrs['href'], 'text': n.text(), 'download': n.attrs.get('download')}
                    for n in doc.nodes if n.tag == 'a' and n.attrs.get('href') and not within(n, 'main') and not navigation(n)]
    nav_links = [{'href': n.attrs['href'], 'text': n.text()} for n in doc.nodes if n.tag == 'a' and n.attrs.get('href') and navigation(n)]
    documents = [l for l in links + chrome_links + nav_links if Path(urlsplit(l['href']).path).suffix.lower() in DOCUMENT_EXTENSIONS or 'download' in l and l['download'] is not None]
    images = [attrs(n) for n in doc.nodes if n.tag == 'img' and within(n, 'main')]
    references = []
    for n in doc.nodes:
        for key in ('src', 'href', 'poster'):
            if n.attrs.get(key):
                references.append(n.attrs[key])
        if n.attrs.get('srcset'):
            references.extend(item.strip().split()[0] for item in n.attrs['srcset'].split(',') if item.strip())
    return {'content': records(doc), 'chrome_content': records(doc, outside_main=True),
            'navigation': records(doc, nav=True), 'tables': tables,
            'links': links, 'chrome_links': chrome_links, 'navigation_links': nav_links, 'downloads': documents,
            'images': images, 'metadata': meta, 'schemas': schemas, 'forms': forms,
            'ids': [n.attrs['id'] for n in doc.nodes if n.attrs.get('id')],
            'references': sorted(set(references))}


def route_for(relative):
    return '/' if relative == 'index.html' else '/' + relative[:-5]


def snapshot(directory):
    directory = Path(directory).resolve()
    files = {str(p.relative_to(directory)).replace('\\', '/'): {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
             for p in sorted(directory.rglob('*')) if p.is_file()}
    pages = {route_for(relative): page_manifest((directory / relative).read_text(encoding='utf8')) for relative in files if relative.endswith('.html')}
    for page in pages.values():
        hosts = {'cochinwood.in', 'www.cochinwood.in'}
        page['local_assets'] = sorted({p for ref in page['references'] if (p := local_path(ref, hosts)) and p in files and not p.endswith('.html')})
    redirects = (directory / '_redirects').read_text(encoding='utf8') if (directory / '_redirects').exists() else ''
    summary = {'files': len(files), 'html_routes': len(pages),
               'canonical_routes': sum(bool(p['metadata']['canonical']) and path != '/404' for path, p in pages.items()),
               'ordered_content_blocks': sum(len(p['content']) for p in pages.values()),
               'header_footer_blocks': sum(len(p['chrome_content']) for p in pages.values()),
               'tables': sum(len(p['tables']) for p in pages.values()),
               'table_rows': sum(len(t) for p in pages.values() for t in p['tables']),
               'schemas': sum(len(p['schemas']) for p in pages.values()),
               'forms': sum(len(p['forms']) for p in pages.values()),
               'download_links': sum(len(p['downloads']) for p in pages.values())}
    return {'version': VERSION, 'root': str(directory), 'summary': summary, 'files': files, 'pages': pages, 'redirects': redirects}


def sequence_delta(before, after):
    a, b = [digest(v) for v in before], [digest(v) for v in after]
    return [{'op': op, 'before_index': i, 'after_index': j, 'before': before[i:ii], 'after': after[j:jj]}
            for op, i, ii, j, jj in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes() if op != 'equal']


def counter_missing(before, after):
    counts = Counter(digest(item) for item in after)
    missing = []
    for item in before:
        key = digest(item)
        if counts[key]:
            counts[key] -= 1
        else:
            missing.append(item)
    return missing


def compare(baseline, candidate, allowances=None):
    allowances = allowances or {'changes': []}
    allowed = {item['id']: item for item in allowances.get('changes', []) if item.get('reason') and item.get('reviewed_by')}
    changes = []

    def change(route, field, before, after, *, informational=False):
        entry = {'route': route, 'field': field, 'before': before, 'after': after}
        entry['id'] = digest(entry)
        entry['status'] = 'addition' if informational else 'review_required'
        if entry['id'] in allowed:
            entry['status'] = 'reviewed'
            entry['reason'] = allowed[entry['id']]['reason']
            entry['reviewed_by'] = allowed[entry['id']]['reviewed_by']
        changes.append(entry)

    old, new = baseline['pages'], candidate['pages']
    for route in sorted(set(old) - set(new)):
        change(route, 'route_removed', route, None)
    for route in sorted(set(new) - set(old)):
        change(route, 'route_added', None, route, informational=True)
    for route in sorted(set(old) & set(new)):
        a, b = old[route], new[route]
        for field in ('content', 'chrome_content', 'tables', 'forms', 'schemas'):
            for delta in sequence_delta(a[field], b[field]):
                # Additions to substantive copy/specs/schema are reviewed too:
                # preserving old words alone cannot justify a new false claim.
                change(route, field, delta['before'], delta['after'])
        for key in sorted(set(a['metadata']) | set(b['metadata'])):
            if a['metadata'].get(key) != b['metadata'].get(key):
                change(route, 'metadata.' + key, a['metadata'].get(key), b['metadata'].get(key))
        for field in ('links', 'chrome_links', 'downloads', 'navigation_links', 'ids'):
            missing = counter_missing(a[field], b[field])
            if missing:
                change(route, field, missing, counter_missing(b[field], a[field]))
        if a['navigation'] != b['navigation']:
            change(route, 'navigation', a['navigation'], b['navigation'], informational=True)
        if a['images'] != b['images']:
            # Expected imagery scope; still requires a route-specific review.
            change(route, 'images', a['images'], b['images'])
        additions = counter_missing(b['links'], a['links'])
        if additions:
            change(route, 'links_added', [], additions, informational=True)
    if baseline['redirects'] != candidate['redirects']:
        change('*', 'redirects', baseline['redirects'], candidate['redirects'])
    for name, meta in baseline['files'].items():
        if name.endswith('.html') or (name.startswith('assets/') and Path(name).suffix in {'.css', '.js'}) or name in {'sitemap.xml', 'sitemap-cms.xml', 'sitemap-post.xml', '_redirects'}:
            continue
        current = candidate['files'].get(name)
        if current != meta:
            change('/' + name, 'file', meta, current)
    changed_assets = []
    for name in sorted(set(candidate['files']) | set(baseline['files'])):
        if name.startswith('assets/') and baseline['files'].get(name) != candidate['files'].get(name):
            changed_assets.append({'path': name, 'before': baseline['files'].get(name), 'after': candidate['files'].get(name)})
    seen = {c['id'] for c in changes}
    stale = sorted(set(allowed) - seen)
    pending = [c for c in changes if c['status'] == 'review_required']
    return {'version': VERSION, 'passed': not pending and not stale,
            'baseline_summary': baseline['summary'], 'candidate_summary': candidate['summary'],
            'summary': {'review_required': len(pending), 'reviewed': sum(c['status'] == 'reviewed' for c in changes),
                        'additions': sum(c['status'] == 'addition' for c in changes), 'stale_allowances': len(stale)},
            'changes': changes, 'changed_build_assets': changed_assets, 'stale_allowance_ids': stale}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    snap = commands.add_parser('snapshot')
    snap.add_argument('directory')
    snap.add_argument('--out', required=True)
    diff = commands.add_parser('compare')
    diff.add_argument('baseline')
    diff.add_argument('directory')
    diff.add_argument('--allow')
    diff.add_argument('--report', required=True)
    args = parser.parse_args()
    if args.command == 'snapshot':
        result = snapshot(args.directory)
        path = args.out
    else:
        baseline = json.loads(Path(args.baseline).read_text(encoding='utf8'))
        allowances = json.loads(Path(args.allow).read_text(encoding='utf8')) if args.allow else None
        result = compare(baseline, snapshot(args.directory), allowances)
        path = args.report
    Path(path).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(result['summary'], ensure_ascii=False))
    if args.command == 'compare' and not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
