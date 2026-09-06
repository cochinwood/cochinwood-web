"""Explicit photograph ownership. Pending assignments never replace live media.

Release validation is deliberately stricter than preview rendering: every
required owner must be reviewed and available before this migration ships.
"""
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=8)
def read_manifest(root=ROOT):
    return json.loads((root / 'content/unique-imagery.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=8)
def read_assets(root=ROOT):
    path = root / 'content/unique-imagery-assets.json'
    return json.loads(path.read_text(encoding='utf-8')).get('assets', {}) if path.exists() else {}


def local_asset(root, src):
    parsed = urlsplit(src)
    if parsed.netloc or parsed.query or parsed.fragment or not parsed.path.startswith('/files/'):
        raise ValueError('Unique imagery requires a local /files/ source')
    relative = Path(unquote(parsed.path).lstrip('/'))
    base = (root / 'assets/photos').resolve()
    path = (base / relative).resolve()
    if not path.is_relative_to(base):
        raise ValueError('Image path escapes source assets')
    return path


def validate_asset(root, item):
    for field in ('src', 'alt', 'sha256', 'kind', 'provenance'):
        if not isinstance(item.get(field), str) or not item[field].strip():
            raise ValueError('Missing image field: ' + field)
    path = local_asset(root, item['src'])
    if path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp', '.avif'}:
        raise ValueError('A photograph assignment requires a raster source')
    if not path.is_file():
        raise ValueError('Missing source image: ' + item['src'])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != item['sha256']:
        raise ValueError('Source image hash mismatch: ' + item['src'])
    return digest


def owner_image(path, root=ROOT):
    owner = '/' + urlsplit(path).path.strip('/')
    assignment = read_manifest(root)['owners'].get(owner)
    if not assignment or assignment.get('status') != 'approved' or assignment.get('kind') == 'text_guide':
        return None
    item = read_assets(root).get(assignment['asset_key'])
    if item is None:
        raise ValueError('Approved imagery is absent from intake: ' + owner)
    validate_asset(root, item)
    return item


def is_text_guide(path, root=ROOT):
    owner = '/' + urlsplit(path).path.strip('/')
    assignment = read_manifest(root)['owners'].get(owner, {})
    if assignment.get('kind') != 'text_guide':
        return False
    taxonomy = json.loads((root / 'content/blog/topics.json').read_text(encoding='utf-8'))
    slug = owner.removeprefix('/blogs/post/')
    if not owner.startswith('/blogs/post/') or taxonomy['posts'].get(slug) != 'city-supply':
        raise ValueError('Text-first exception is restricted to existing location guides')
    if assignment.get('status') != 'approved' or not assignment.get('reason', '').strip():
        raise ValueError('Text-first exception requires explicit approval and reason')
    return True


def validate_ownership(root=ROOT):
    errors, hashes = [], {}
    assets = read_assets(root)
    for owner, assignment in read_manifest(root)['owners'].items():
        if assignment.get('kind') == 'text_guide':
            try:
                is_text_guide(owner, root)
            except (ValueError, FileNotFoundError, KeyError) as exc:
                errors.append(owner + ': ' + str(exc))
            continue
        if assignment.get('status') != 'approved':
            errors.append(owner + ': image assignment pending review')
            continue
        try:
            key = assignment['asset_key']
            if key not in assets:
                raise ValueError('Missing intake asset ' + key)
            digest = validate_asset(root, assets[key])
            if digest in hashes:
                raise ValueError('Identical photograph owned by ' + hashes[digest])
            hashes[digest] = owner
        except (ValueError, KeyError) as exc:
            errors.append(owner + ': ' + str(exc))
    return errors
