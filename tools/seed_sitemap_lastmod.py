"""Seed sitemap <lastmod> where the pinned sitemap predates a page's own title or markup.

sitemap_lastmod.py keeps a page's published lastmod for as long as its content is
unchanged. The lastmods published before it existed came from source-file git dates,
so some are older than what the page now says: every product page kept 2026-09-06
after its Product markup changed on 2026-09-15.

This tool walks cf-live's first-parent history back from the pinned tree (LIVE_SHA)
and finds the publication in which each page's title, description, canonical, robots
and structured data last changed. Only publications made by this generator are
compared: output from before it took over cf-live (no "# built from" banner in
_headers) carries different markup for the same words. Body text is not walked:
its history mixes real edits with template changes (a reading-time byline added to
every article, rebuilt hero buttons), so it cannot date a page reliably.

A date is recorded only where it is later than the pinned sitemap's. build.py uses a
seed date only while the page still has exactly the seeded fingerprint, so a seed
entry can never date newer content. Once LIVE_SHA points at a publication built with
the seed, the published sitemap carries the same dates and the file can be deleted.

    python tools/seed_sitemap_lastmod.py           report only
    python tools/seed_sitemap_lastmod.py --write   write content/sitemap-lastmod-seed.json
"""
import argparse
from collections import defaultdict
import html
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import sitemap_lastmod as SL

SEED = ROOT / 'content' / 'sitemap-lastmod-seed.json'
BANNER = b'# built from '


def pinned_sha():
    source = (ROOT / 'build.py').read_text(encoding='utf-8')
    return re.search(r'^LIVE_SHA = "([0-9a-f]{40})"', source, re.M).group(1)


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True).stdout


def generator_commits(pin):
    """First-parent commits back from the pin, while each one's _headers carries this build's banner."""
    commits = git('rev-list', '--first-parent', pin).decode('ascii').split()
    batch = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT, capture_output=True, check=True,
                           input=''.join(f'{c}:_headers\n' for c in commits).encode('ascii')).stdout
    generated, i = set(), 0
    for commit in commits:
        nl = batch.index(b'\n', i)
        header = batch[i:nl].split(b' ')
        if header[-1] == b'missing' or len(header) != 3:
            break
        size = int(header[2])
        if BANNER not in batch[nl + 1:nl + 1 + size]:
            break
        generated.add(commit)
        i = nl + 1 + size + 1
    return generated


def _unescaped(value):
    if isinstance(value, str):
        return html.unescape(value)
    if isinstance(value, list):
        return [_unescaped(v) for v in value]
    if isinstance(value, dict):
        return {k: _unescaped(v) for k, v in value.items()}
    return value


def head_and_markup_dates(pin):
    published = SL.published_lastmods(pin, str(ROOT))
    if published is None:
        raise SystemExit(f'cannot read the sitemaps at {pin[:12]}; run `git fetch origin`')
    generated = generator_commits(pin)
    outputs = {SL.output_path(url): url for url in published}
    log = git('log', '--first-parent', '-m', '--raw', '--no-renames', '--no-abbrev',
              '--format=@%H %cs', pin, '--', '*.html').decode('utf-8')
    history, commit, date = defaultdict(list), None, None      # output path -> [(date, blob)], newest first
    for line in log.splitlines():
        if line.startswith('@'):
            commit, date = line[1:].split()
        elif line.startswith(':') and commit in generated:
            meta, path = line.split('\t', 1)
            if path in outputs:
                fields = meta.split()
                history[path].append((date, None if fields[4].startswith('D') else fields[3]))
    records = {}

    def record(blob):
        if blob not in records:
            text = git('cat-file', 'blob', blob).decode('utf-8')
            full = SL.content_record(text)
            records[blob] = (SL.fingerprint(text),
                             json.dumps(_unescaped([full['head'], full['schemas']]), sort_keys=True))
        return records[blob]

    result = {}
    for path, url in sorted(outputs.items()):
        entries = history.get(path)
        if not entries or entries[0][1] is None:
            continue
        fingerprint, current = record(entries[0][1])
        changed_at = None
        for (date, _blob), (_older_date, older_blob) in zip(entries, entries[1:]):
            if older_blob is None or record(older_blob)[1] != current:
                changed_at = date
                break
        # No generator-built version differs: nothing in this history can date the page later.
        lastmod = max(changed_at, published[url]) if changed_at else published[url]
        result[url] = {'fingerprint': fingerprint, 'lastmod': lastmod, 'published': published[url]}
    return result, len(generated)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    pin = pinned_sha()
    dates, generated = head_and_markup_dates(pin)
    later = {url: item for url, item in dates.items() if item['lastmod'] != item['published']}
    print(f'{len(dates)} pages at {pin[:12]} ({generated} generator publications compared): '
          f'{len(later)} published dates predate a later change to the page\'s title, description or markup')
    for url, item in sorted(later.items()):
        print(f'  {url}: published {item["published"]}, title/description/markup changed {item["lastmod"]}')
    if args.write:
        SEED.write_text(json.dumps({
            'description': 'Pages whose pinned sitemap lastmod predates a later change to their title, description or '
                           'structured data on cf-live. Written by tools/seed_sitemap_lastmod.py; sitemap_lastmod.py '
                           'uses a date only while the page keeps this fingerprint.',
            'pin': pin,
            'pages': {url: {'fingerprint': item['fingerprint'], 'lastmod': item['lastmod']}
                      for url, item in sorted(later.items())},
        }, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
        print('wrote', SEED.relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main()
