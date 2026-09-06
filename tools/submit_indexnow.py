"""Notify IndexNow only after exact published HTML verification; dry-run by default.

Official protocol: https://www.indexnow.org/documentation
Usage: python tools/submit_indexnow.py --dist dist --state <private receipt.json>
Add --submit only after publication. Repeating a successful run skips unchanged
HTML. Keep the state file across releases. HTTP 200/202 means received, not indexed.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)

def read_url(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'CWI-IndexNow-Publication-Check/1.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200 or response.geturl() != url:
            raise ValueError('Published URL must return direct HTTP 200: ' + url)
        return response.read()

def inventory(dist, host):
    urls = set()
    for sitemap in dist.glob('sitemap*.xml'):
        tree = ET.parse(sitemap)
        for entry in tree.findall('s:url/s:loc', NS):
            url = entry.text or ''
            parsed = urllib.parse.urlsplit(url)
            if parsed.scheme != 'https' or parsed.netloc != host or parsed.query or parsed.fragment:
                raise ValueError('Unexpected sitemap URL: ' + url)
            urls.add(url)
    if not urls:
        raise ValueError('No canonical URLs in sitemap files')
    output = {}
    for url in sorted(urls):
        route = urllib.parse.unquote(urllib.parse.urlsplit(url).path)
        relative = 'index.html' if route == '/' else route.lstrip('/') + '.html'
        file = (dist / relative).resolve()
        if not file.is_relative_to(dist) or not file.is_file():
            raise ValueError('Missing HTML for canonical URL: ' + url)
        output[url] = digest(file.read_bytes())
    return output

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path, default=ROOT / 'dist')
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--submit', action='store_true')
    parser.add_argument('--retry-uncertain', action='store_true', help='Explicitly retry a prior ambiguous request')
    args = parser.parse_args()
    config = json.loads((ROOT / 'content/indexnow.json').read_text(encoding='utf-8'))
    host = config['host']
    if host != 'www.cochinwood.in' or config['endpoint'] != 'https://api.indexnow.org/indexnow':
        raise ValueError('Only the approved public website and official endpoint are supported')
    key = (ROOT / config['key_file']).read_text(encoding='utf-8-sig').strip()
    if not re.fullmatch(r'[a-zA-Z0-9-]{8,128}', key):
        raise ValueError('Invalid public verification key')
    if config['key_location'] != f'https://{host}/{key}.txt':
        raise ValueError('Verification key must be at the approved host root')
    state = json.loads(args.state.read_text(encoding='utf-8')) if args.state.exists() else {'submitted': {}}
    changed = {url: sha for url, sha in inventory(args.dist.resolve(), host).items()
               if state.get('submitted', {}).get(url) != sha}
    print(json.dumps({'mode': 'submit' if args.submit else 'dry-run', 'changed_urls': len(changed),
                      'state': str(args.state), 'indexing_guaranteed': False}))
    if not args.submit or not changed:
        return
    if state.get('pending') and not args.retry_uncertain:
        raise ValueError('Prior request outcome may be uncertain; inspect receipt before --retry-uncertain')
    if read_url(config['key_location']).decode('utf-8-sig').strip() != key:
        raise ValueError('Live public key differs from the preserved source')
    def verify(item):
        url, sha = item
        if digest(read_url(url)) != sha:
            raise ValueError('Candidate differs from published HTML; no URLs submitted: ' + url)
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(verify, changed.items()))
    urls = list(changed)
    for offset in range(0, len(urls), 10000):
        batch = urls[offset:offset + 10000]
        payload = {'host': host, 'key': key, 'keyLocation': config['key_location'], 'urlList': batch}
        state['pending'] = {'urls': batch, 'started': datetime.now(timezone.utc).isoformat()}
        save(args.state, state)
        request = urllib.request.Request(config['endpoint'], data=json.dumps(payload).encode('utf-8'),
                                         headers={'Content-Type': 'application/json; charset=utf-8'}, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                status = response.status
        except urllib.error.HTTPError as error:
            state['last_error'] = {'status': error.code, 'at': datetime.now(timezone.utc).isoformat()}
            save(args.state, state)
            raise
        if status not in (200, 202):
            raise ValueError('Unexpected IndexNow response: ' + str(status))
        state.setdefault('submitted', {}).update({url: changed[url] for url in batch})
        state.pop('pending', None)
        state.pop('last_error', None)
        state.setdefault('receipts', []).append({'status': status, 'urls': batch,
                                               'at': datetime.now(timezone.utc).isoformat()})
        save(args.state, state)
        print(json.dumps({'received': len(batch), 'http_status': status,
                          'meaning': 'received; key validation pending' if status == 202 else 'received; not an indexing guarantee'}))

if __name__ == '__main__':
    main()
