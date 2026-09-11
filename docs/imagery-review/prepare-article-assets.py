"""Prepare reviewed built-in image outputs; never edits shared site manifests."""
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
from xml.sax.saxutils import escape
import hashlib
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / 'docs/imagery-review'
DEST = ROOT / 'assets/photos/files/Editorial-2026'
ORIGINALS = REVIEW / 'article-originals'
DATA = REVIEW / 'article-generation-progress.json'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

def main():
    completed = json.loads(DATA.read_text(encoding='utf-8'))['completed']
    captions = {p['slug']: p for p in json.loads((REVIEW / 'article-captions-2026-09-06.json').read_text(encoding='utf-8'))}
    manifest = json.loads((ROOT / 'content/unique-imagery.json').read_text(encoding='utf-8'))['owners']
    DEST.mkdir(parents=True, exist_ok=True)
    ORIGINALS.mkdir(parents=True, exist_ok=True)
    assets, owners, responsive, receipts = {}, {}, {}, []
    for item in completed:
        slug = item['slug']
        owner = '/blogs/post/' + slug
        assert manifest[owner]['category'] == 'editorial-guide'
        assert manifest[owner]['status'] == 'pending', 'Never replace a previously approved authentic image'
        key = manifest[owner]['asset_key']
        source = Path(item['source_path'])
        revision = item.get('revision', 1)
        original = ORIGINALS / (slug + (('-v' + str(revision)) if revision > 1 else '') + '.png')
        if not original.exists():
            shutil.copy2(source, original)
        assert digest(source) == digest(original)
        with Image.open(original) as raw:
            image = ImageOps.exif_transpose(raw).convert('RGB')
            width, height = image.size
        spec = captions[slug]
        metadata = ('<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            '<rdf:Description rdf:about="" xmlns:iptcExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:xmp="http://ns.adobe.com/xap/1.0/" '
            'iptcExt:DigitalSourceType="http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia" '
            'xmp:CreatorTool="OpenAI built-in image generation"><dc:description><rdf:Alt><rdf:li xml:lang="x-default">'
            + escape('Generated editorial concept. ' + spec['alt'] + ' Not documentary evidence of a named facility, actual shipment, species identity or certified test.')
            + '</rdf:li></rdf:Alt></dc:description></rdf:Description></rdf:RDF></x:xmpmeta>').encode('utf-8')
        group = []
        for target in sorted(set([320, 640, 960, width])):
            if target > width:
                continue
            path = DEST / (slug + ('' if target == width else '-' + str(target)) + '.webp')
            frame = image if target == width else image.resize((target, round(height * target / width)), Image.Resampling.LANCZOS)
            frame.save(path, 'WEBP', quality=84, method=6, xmp=metadata)
            with Image.open(path) as check:
                check.load()
                assert check.width == target
                assert b'trainedAlgorithmicMedia' in check.info.get('xmp', b'')
            src = '/files/Editorial-2026/' + path.name
            group.append({'src': src, 'width': target, 'sha256': digest(path)})
        master = group[-1]
        responsive[master['src']] = group
        asset = {'src': master['src'], 'alt': spec['alt'], 'caption': spec['caption'], 'width': width, 'height': height,
            'sha256': master['sha256'], 'kind': 'generated editorial material concept',
            'provenance': 'Generated with the built-in OpenAI image tool for this one article. Original PNG and creation credentials retained; WebP derivatives carry IPTC DigitalSourceType trainedAlgorithmicMedia. This is not documentary company, facility, shipment, species or certification evidence.',
            'prompt': item['prompt'], 'source_original': original.relative_to(ROOT).as_posix(), 'source_sha256': digest(original),
            'source_dimensions': [width, height], 'tool': 'built-in image_gen.imagegen',
            'digital_source_type': 'http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia',
            'reviewed': '2026-09-06; full output inspected for subject, material plausibility, unwanted labels and unrelated facility claims.',
            'adaptations': 'Proportional resizing and WebP compression only; no crop, recolouring, upscaling, object removal or pixel retouching.',
            'placement_reason': 'Unique material/application composition addressing the article title and source content.',
            'display_requirement': 'Preserve full image with proportional sizing; thumbnail reuse belongs only to this same article.',
            'owner': owner}
        history = item.get('revisions', []) + item.get('rejected_history', [])
        if history:
            asset['revision_history'] = []
            for i, prior in enumerate(history, 1):
                prior_source = Path(prior['source_path'])
                prior_copy = ORIGINALS / (slug + '-rejected-' + str(i) + '.png')
                if not prior_copy.exists():
                    shutil.copy2(prior_source, prior_copy)
                assert digest(prior_source) == digest(prior_copy)
                asset['revision_history'].append({**prior, 'source_original': prior_copy.relative_to(ROOT).as_posix(),
                    'source_sha256': digest(prior_copy)})
            asset['adaptations'] += ' Prior rejected generations and exact correction prompts are retained in the review archive.'
        assets[key] = asset
        owners[owner] = {**manifest[owner], 'status': 'approved'}
        receipts.append({'owner': owner, 'asset_key': key, 'source_sha256': digest(original), 'master': master,
            'width': width, 'height': height, 'candidates': len(group), 'webp_bytes': sum((DEST / Path(g['src']).name).stat().st_size for g in group)})
    assert len(assets) == len(completed)
    assert len({a['sha256'] for a in assets.values()}) == len(assets)
    write_json(REVIEW / 'article-intake-additions.json', {'version': 1, 'assets': assets})
    write_json(REVIEW / 'article-owner-additions.json', {'owners': owners})
    write_json(REVIEW / 'article-responsive-additions.json', responsive)
    write_json(REVIEW / 'article-integration-receipt.json', {'status': 'prepared; root integration and browser checks pending',
        'generated_and_inspected': len(assets), 'required': 44, 'shared_manifests_changed': False, 'originals_preserved': True,
        'candidate_count': sum(r['candidates'] for r in receipts), 'webp_bytes': sum(r['webp_bytes'] for r in receipts), 'items': receipts})
    ordered = sorted(assets.values(), key=lambda a: a['owner'])
    for start in range(0, len(ordered), 12):
        batch = ordered[start:start + 12]
        canvas = Image.new('RGB', (1500, ((len(batch) + 2) // 3) * 365), '#f4f1e9')
        draw = ImageDraw.Draw(canvas)
        for j, asset in enumerate(batch):
            x, y = (j % 3) * 500, (j // 3) * 365
            p = ROOT / 'assets/photos' / asset['src'].lstrip('/')
            with Image.open(p) as im:
                im.thumbnail((488, 320))
                canvas.paste(im, (x + (500 - im.width) // 2, y + (320 - im.height) // 2))
            title = manifest[asset['owner']]['title']
            words = title.split(); lines = ['']
            for word in words:
                if len(lines[-1]) + len(word) > 65:
                    lines.append(word)
                else:
                    lines[-1] += (' ' if lines[-1] else '') + word
            for k, line in enumerate(lines[:3]):
                draw.text((x + 8, y + 321 + k * 13), line, fill='#183d2e')
        canvas.save(REVIEW / ('article-contact-sheet-' + str(start // 12 + 1) + '.jpg'), quality=93)
    print(json.dumps({'prepared': len(assets), 'candidate_count': sum(r['candidates'] for r in receipts),
        'webp_bytes': sum(r['webp_bytes'] for r in receipts), 'sheets': (len(assets) + 11) // 12}))

if __name__ == '__main__':
    main()
