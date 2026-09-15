"""Sitemap <lastmod> from each page's own content, compared with the published tree.

The build used to date a URL by the last commit that touched its source file. That
was wrong in both directions. A product page kept its old date when only its product
data and Product markup changed, because neither lives in the page's source file.
And all 157 articles share content/blog/posts.json, so a commit that reformats that
file, or a clone without its history, stamps one date on every article.

A page is dated by what it says instead. Its fingerprint covers what a reader or
crawler is told about that page:

  - <title>, meta description, meta robots and canonical;
  - its structured data, except the site-wide Organization and WebSite blocks, and
    without dateModified (a date) or image URLs (media);
  - the text and links inside <main>, as a set: moving a block is not a change.

Not content: header and footer, navigation (site_preservation.navigation), the
section switcher, hero buttons and breadcrumbs, other buttons, call-to-action bands,
figures with their captions, the species photo gallery, images and content-addressed
asset names. Those are template or media changes; they do not redate every page.

The previous publication is the record. For each page the build emits:

  - same fingerprint as the same page in the pinned production tree (LIVE_SHA):
    keep the lastmod that tree's sitemap already publishes, or the seed date in
    content/sitemap-lastmod-seed.json while the page keeps that seed's fingerprint;
  - changed, or not published there: the committer date of the source revision
    being built.

Both answers depend only on the pinned tree, the seed and the source revision, so
rebuilding the same revision gives the same sitemap, and an unchanged page keeps its
date until its content changes.
"""
import hashlib
import json
import re
import subprocess
from urllib.parse import urlsplit

from site_preservation import BLOCKS, Document, compact, hidden, navigation, within

SITE_WIDE_IDS = ('/#organization', '/#website')
SITEMAPS = ('sitemap-cms.xml', 'sitemap-post.xml')
NOT_CONTENT_TAGS = {'figure', 'button'}
NOT_CONTENT_CLASSES = {'cw-section-bar', 'cw-species-reference', 'cw-page-hero__media',
                       'cw-page-hero__actions', 'cw-page-hero__breadcrumbs'}
NOT_CONTENT_KEYS = {'dateModified', 'image', 'logo', 'thumbnailUrl'}


def output_path(url_path):
    """/ -> index.html, /export/chile -> export/chile.html (the flat layout build.write uses)."""
    return 'index.html' if url_path == '/' else url_path.strip('/') + '.html'


def _schema_content(value):
    if isinstance(value, dict):
        return {k: _schema_content(v) for k, v in value.items() if k not in NOT_CONTENT_KEYS}
    if isinstance(value, list):
        return [_schema_content(v) for v in value]
    return value


def _not_content(node):
    if not within(node, 'main') or within(node, 'head') or hidden(node) or navigation(node):
        return True
    for ancestor in node.ancestors():
        if ancestor.tag in NOT_CONTENT_TAGS:
            return True
        classes = (ancestor.attrs.get('class') or '').split()
        if NOT_CONTENT_CLASSES.intersection(classes) or any(c.endswith(('__cta', '-cta')) for c in classes):
            return True
    return False


def content_record(markup):
    """What the fingerprint hashes, for inspecting why a page was redated."""
    doc = Document(markup)
    head = []
    for node in doc.nodes:
        if node.tag == 'title':
            head.append(['title', node.text()])
        elif node.tag == 'meta' and node.attrs.get('name') in ('description', 'robots'):
            head.append([node.attrs['name'], node.attrs.get('content', '')])
        elif node.tag == 'link' and node.attrs.get('rel') == 'canonical':
            head.append(['canonical', node.attrs.get('href', '')])
    schemas = []
    for node in doc.nodes:
        if node.tag != 'script' or node.attrs.get('type') != 'application/ld+json':
            continue
        raw = ''.join(c for c in node.children if isinstance(c, str))
        try:
            data = json.loads(raw)
        except ValueError:
            data = {'INVALID_JSON': raw}
        if isinstance(data, dict) and str(data.get('@id', '')).endswith(SITE_WIDE_IDS):
            continue
        schemas.append(_schema_content(data))
    content, previous = [], None
    for node, value in doc.tokens:
        text = compact(value)
        if not text or _not_content(node):
            continue
        block = next((n for n in node.ancestors() if n.tag in BLOCKS), node)
        if block is previous:
            content[-1][1] = compact(content[-1][1] + ' ' + text)
        else:
            content.append([block.tag if block.tag in BLOCKS else 'text', text])
            previous = block
    links = [[node.attrs['href'], node.text()] for node in doc.nodes
             if node.tag == 'a' and node.attrs.get('href') and not _not_content(node)]
    return {'head': head, 'schemas': schemas, 'content': sorted(content), 'links': sorted(links)}


def fingerprint(markup):
    return hashlib.sha256(json.dumps(content_record(markup), ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def resolve(built, published_lastmod, published_fingerprint, change_date, seed=None):
    """{url_path: fingerprint} -> ({url_path: lastmod}, [url paths dated change_date]).

    seed: {url_path: {'fingerprint', 'lastmod'}}, applied only to a page that still
    has the seeded fingerprint."""
    seed = seed or {}
    dates, changed = {}, []
    for path in sorted(built):
        seeded = seed.get(path)
        kept = published_lastmod.get(path)
        if seeded and seeded.get('fingerprint') == built[path]:
            dates[path] = seeded['lastmod']
        elif kept and published_fingerprint.get(path) == built[path]:
            dates[path] = kept
        else:
            dates[path] = change_date
            changed.append(path)
    return dates, changed


def read_blobs(ref, root, paths):
    """{path: text or None} for files in a git tree, read as raw object bytes (no eol filters)."""
    paths = list(paths)
    if not paths:
        return {}
    try:
        run = subprocess.run(['git', 'cat-file', '--batch'], cwd=root, capture_output=True, timeout=300,
                             input=''.join(f'{ref}:{p}\n' for p in paths).encode('utf-8'))
    except (OSError, subprocess.SubprocessError):
        return {}
    if run.returncode != 0:
        return {}
    out, buf, i = {}, run.stdout, 0
    for path in paths:
        nl = buf.index(b'\n', i)
        header = buf[i:nl].split(b' ')
        if header[-1] == b'missing' or len(header) != 3:
            out[path], i = None, nl + 1
            continue
        size = int(header[2])
        out[path] = buf[nl + 1:nl + 1 + size].decode('utf-8')
        i = nl + 1 + size + 1
    return out


def published_lastmods(ref, root):
    """{url_path: lastmod} from the sitemaps committed at ref, or None if they cannot be read."""
    blobs = read_blobs(ref, root, SITEMAPS)
    if any(blobs.get(name) is None for name in SITEMAPS):
        return None
    result = {}
    for name in SITEMAPS:
        for loc, lastmod in re.findall(r'<url><loc>([^<]+)</loc><lastmod>([^<]+)</lastmod>', blobs[name]):
            result[urlsplit(loc).path or '/'] = lastmod
    return result


def revision_date(root, rev='HEAD'):
    try:
        out = subprocess.run(['git', 'log', '-1', '--format=%cs', rev], cwd=root,
                             capture_output=True, text=True, timeout=15).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return out if re.fullmatch(r'\d{4}-\d{2}-\d{2}', out) else None


def remote_tip(root, ref='origin/cf-live'):
    """The commit production currently serves, as this clone last fetched it, or None."""
    try:
        out = subprocess.run(['git', 'rev-parse', '--verify', '-q', ref + '^{commit}'], cwd=root,
                             capture_output=True, text=True, timeout=15).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return out if re.fullmatch(r'[0-9a-f]{40}', out) else None


def pin_drift_warning(pin, tip, redated):
    """A loud warning when production has moved past the pin, naming the URLs this build redated.

    A page published after LIVE_SHA differs from the pinned tree, so resolve() gives it the
    source revision's date on every build until the pin moves -- not the date it went live."""
    if not tip or tip == pin:
        return None
    if redated is None:
        listed = 'not computed, because the pinned tree could not be read'
    else:
        listed = f'{len(redated)}: ' + (', '.join(redated) if redated else 'none')
    return (f'SITEMAP LASTMOD: origin/cf-live is {tip[:12]} but LIVE_SHA is {pin[:12]}. Pages published after the pin '
            f'are compared with the older tree, so every build redates them to its own source revision until '
            f'LIVE_SHA moves. Review what cf-live published since the pin and move it before publishing. '
            f'URLs redated in this build, {listed}')


def lastmods(url_paths, read_built, ref, root, seed=None):
    """Date every page, or return None when the published tree or source date is unavailable."""
    change_date = revision_date(root)
    published = published_lastmods(ref, root)
    if change_date is None or published is None:
        return None
    outputs = {p: output_path(p) for p in url_paths}
    pinned = read_blobs(ref, root, outputs.values())
    built = {p: fingerprint(read_built(o)) for p, o in outputs.items()}
    before = {p: fingerprint(pinned[o]) for p, o in outputs.items() if pinned.get(o) is not None}
    dates, changed = resolve(built, published, before, change_date, seed)
    return dates, changed, change_date
