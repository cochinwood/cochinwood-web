"""Reviewed editorial and species imagery without replacing article prose.

Call enhance_editorial_media(body, path, image, link) before hero normalization.
All imagery is explicit in JSON. Missing references fail the build. Existing
published asset URLs remain byte-preserved; optimized assets have new URLs.
"""
from __future__ import annotations
import html
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit
from hero_layout import parse_fragment
from unique_imagery import owner_image, is_text_guide

ROOT = Path(__file__).resolve().parent
MEDIA = json.loads((ROOT / "content/editorial-media.json").read_text(encoding="utf-8"))
SPECIES = json.loads((ROOT / "content/species-media.json").read_text(encoding="utf-8"))
VISUAL = json.loads((ROOT / "content/visual-media.json").read_text(encoding="utf-8"))

LABEL_REPLACEMENTS = {
    "Warehouse illustration": "",
    "Illustrations of typical applications": "Materials at work",
    "Process illustration": "",
    "Material and workshop illustration.": "",
    "Material and production illustrations.": "Materials and production.",
    "Representative block board construction.": "Block board construction.",
    "Flush-door application illustration.": "Flush-door application.",
    "Material illustration.": "",
    "Representative panel;": "Panel specification:",
    "Illustration of container loading.": "",
    "Representative solid-wood board samples;": "Solid-wood boards:",
    "Representative product image": "Materials for your application",
    "Representative material illustrations.": "",
    "Representative Okoume-faced panel.": "Okoume-faced panel.",
    "Representative material and production imagery.": "Materials and production.",
    "Representative plywood image;": "Plywood specification:",
    "Representative production imagery;": "Production details:",
    "Representative rubberwood plywood.": "Rubberwood plywood.",
    "Representative sawn timber;": "Sawn timber:",
    "Representative rubberwood samples.": "Rubberwood samples.",
}


def clean_image_labels(body):
    """Only remove image-production language, never technical 'averages' prose."""
    for old, new in LABEL_REPLACEMENTS.items():
        body = body.replace(old, new)
    body = re.sub(r'<figcaption\b(?![^>]*\bid=)[^>]*>\s*</figcaption>|<span(?: class="cx-hero__credit")?>\s*</span>', '', body)
    def alt(match):
        value = html.unescape(match.group(1))
        value = re.sub(r"^(?:An? )?(?:illustration of |representative )", "", value, flags=re.I)
        value = re.sub(r"\s+illustration$", "", value, flags=re.I)
        return 'alt="' + html.escape(value[:1].upper() + value[1:], quote=True) + '"'
    return re.sub(r'alt="([^"]*)"', alt, body)


def _figure(item, image, link, *, css="cw-editorial-media", eager=False):
    tag = image(item, eager=eager, sizes="(max-width: 760px) 100vw, 66vw")
    if css == 'cw-species-media' and item.get('max_display_width') is not None:
        cap = item['max_display_width']
        if isinstance(cap, bool) or not isinstance(cap, (int, float)) or not 100 <= cap <= 2000:
            raise ValueError('Species max_display_width must be a number from 100 to 2000')
        style = f'max-width:{cap:g}px;width:100%;height:auto;object-fit:contain'
        tag = tag.replace('<img ', f'<img style="{style}" ', 1)
    # Vector diagrams carry explicit dimensions; the existing raster reader
    # deliberately does not parse SVG XML.
    if item.get("width") and not re.search(r"\bwidth=", tag):
        tag = tag.replace("<img ", f'<img width="{item["width"]}" height="{item["height"]}" ', 1)
    if item.get("mobile_src"):
        # Register the source through the same required-asset pipeline. Width
        # and height on the source reserve the alternate portrait aspect ratio.
        mobile = image({"src": item["mobile_src"], "alt": item["alt"]}, eager=eager)
        mobile_url = re.search(r'src="([^"]+)"', mobile).group(1)
        tag = ('<picture><source media="(max-width: 560px)" srcset="' + mobile_url
               + f'" width="{item["mobile_width"]}" height="{item["mobile_height"]}">' + tag + '</picture>')
    if item["src"].endswith(".svg"):
        tag = ('<a class="cw-diagram-link" href="' + html.escape(link(item["src"]), quote=True)
               + '" aria-label="Open full-size diagram: ' + html.escape(item.get("caption", item["alt"]), quote=True) + '">' + tag + '</a>')
    caption = html.escape(item.get("caption", ""))
    if item.get("source_url"):
        credit = html.escape(item.get("credit", "Source"))
        caption += (' <span class="cw-media-source">'
                    + '<a href="' + html.escape(item["source_url"], quote=True) + '">' + credit + '</a>')
        if item.get("license_url"):
            caption += (' · <a rel="license" href="' + html.escape(item["license_url"], quote=True)
                        + '">' + html.escape(item["license"]) + '</a>')
        elif item.get("license"):
            caption += ' · ' + html.escape(item["license"])
        caption += ' · Size/compression adapted.</span>'
    return (f'<figure class="{css}" data-reveal="image">' + tag
            + ('<figcaption>' + caption + '</figcaption>' if caption else '') + '</figure>')


def _scene(src):
    path = unquote(urlsplit(src).path)
    return path[path.index('/files/'):] if '/files/' in path else path


def _product_gallery(body, slug, image, link):
    """Replace redundant hero repeats and supplement detail/application views."""
    tree = parse_fragment(body)
    hero_scene = _scene(VISUAL["products"][slug]["src"])
    galleries = [n for n in tree.nodes if 'cwp__gallery' in n.classes]
    edits = []
    for gallery in galleries:
        for figure in (n for n in tree.nodes if n.tag == 'figure' and gallery.contains(n)):
            imgs = [n for n in tree.nodes if n.tag == 'img' and figure.contains(n)]
            if imgs and _scene(imgs[0].attrs.get('src', '')) == hero_scene:
                edits.append((figure.start, figure.end, ''))
    for a, b, value in sorted(edits, reverse=True):
        body = body[:a] + value + body[b:]
    tree = parse_fragment(body)
    seen = {_scene(n.attrs.get('src', '')) for n in tree.nodes if n.tag == 'img'}
    figures = []
    for key in MEDIA['product_galleries'][slug]:
        item = MEDIA['assets'][key]
        if _scene(item['src']) in seen:
            continue
        seen.add(_scene(item['src']))
        figures.append(_figure(item, image, link, css="cw-editorial-media"))
    if not figures:
        return body
    gallery = next((n for n in tree.nodes if 'cwp__gallery' in n.classes), None)
    if gallery:
        return body[:gallery.close_start] + ''.join(figures) + body[gallery.close_start:]
    section = ('<section class="cwp__section cw-product-media" id="material-details">'
               '<div class="cwp__container"><h2 class="cwp__h2">Material and application details</h2>'
               '<div class="cwp__gallery">' + ''.join(figures) + '</div></div></section>')
    # Keep the original commercial copy and CTA order; place useful media
    # immediately before the final existing CTA section where it is available.
    cta = next((n for n in tree.nodes if n.tag == 'section' and any('cta' in c for c in n.classes)), None)
    pos = cta.start if cta else len(body)
    return body[:pos] + section + body[pos:]


def article_lead(slug):
    unique = owner_image('/blogs/post/' + slug)
    if unique:
        return unique
    data = MEDIA['posts'].get(slug)
    return MEDIA['assets'][data['lead']] if data else None



def article_share_media(slug):
    """Social cards use a relevant raster; diagrams stay in the article body."""
    # A text-first guide has no article photograph. The shell deliberately
    # falls back to its branded card, rather than advertising a removed image.
    if is_text_guide('/blogs/post/' + slug):
        return None
    item = article_lead(slug)
    if not item or not item['src'].endswith('.svg'):
        return item
    lead = MEDIA['posts'][slug]['lead']
    raster = {'plywood-layers': 'commercial-plywood', 'board-cores': 'block-board-flush-doors',
              'panel-dimensions': 'material-range', 'packing-structure': 'packing-case',
              'load-planning': 'packing-case', 'specification-checklist': 'material-range',
              'drum-dimensions': 'plywood-cable-drums', 'floor-support': 'container-flooring-plywood'}
    return MEDIA['assets'][raster[lead]]


def enhance_editorial_media(body, path, image, link):
    body = clean_image_labels(body)
    if 'data-editorial-pass="1"' in body:
        return body
    slug = path.strip('/')
    if slug in MEDIA['product_galleries']:
        body = _product_gallery(body, slug, image, link)
    if slug.startswith('blogs/post/'):
        article_slug = slug.removeprefix('blogs/post/')
        data = MEDIA['posts'].get(article_slug)
        if data:
            tree = parse_fragment(body)
            article = next((n for n in tree.nodes if n.tag == 'article' and 'cw-reading-content' in n.classes), None)
            if not article:
                raise ValueError(f'No reading article for media: {path}')
            lead_item = article_lead(article_slug)
            lead = '' if is_text_guide(path) else _figure(lead_item, image, link, eager=True)
            pos = article.open_end
            body = body[:pos] + lead + body[pos:]
            # A former diagram lead remains useful content after a unique
            # photographic lead is approved; retain it without duplicating it.
            diagram_key = data.get('diagram')
            former_lead = MEDIA['assets'][data['lead']]
            if former_lead['src'].endswith('.svg') and lead_item['src'] != former_lead['src']:
                diagram_key = diagram_key or data['lead']
            if diagram_key:
                tree = parse_fragment(body)
                article = next(n for n in tree.nodes if n.tag == 'article' and 'cw-reading-content' in n.classes)
                first_heading = next((n for n in tree.nodes if n.tag == 'h2' and article.contains(n)), None)
                if first_heading:
                    pos = first_heading.start
                    diagram = _figure(MEDIA['assets'][diagram_key], image, link)
                    body = body[:pos] + diagram + body[pos:]
    if slug in MEDIA.get('page_media', {}):
        tree = parse_fragment(body)
        # A useful visual accompanies the existing introduction; policy and
        # machine-readable utility pages deliberately receive no decoration.
        heading = next((n for n in tree.nodes if n.tag == 'h2'), None)
        if heading:
            figure = _figure(MEDIA['assets'][MEDIA['page_media'][slug]], image, link)
            body = body[:heading.start] + figure + body[heading.start:]
    if slug.startswith('woods-we-use/'):
        species_slug = slug.rsplit('/', 1)[-1]
        entry = SPECIES.get(species_slug)
        if entry:
            tree = parse_fragment(body)
            hero = next((n for n in tree.nodes if 'cwg__hero' in n.classes or 'cw-page-hero' in n.classes), None)
            if not hero:
                raise ValueError(f'No species header for media: {path}')
            figures = ''.join(_figure(item, image, link, css="cw-species-media", eager=i == 0)
                              for i, item in enumerate(entry['images']))
            media = ('<section class="cw-species-reference" aria-label="Species reference images">'
                     + figures + '</section>')
            body = body[:hero.end] + media + body[hero.end:]
    # Resource cards and other contextual article links use the destination's
    # approved lead, just as the Blog directory does. Replace only the visual
    # node; preserve linked titles, descriptions and original destinations.
    tree = parse_fragment(body)
    replacements = []
    for anchor in (n for n in tree.nodes if n.tag == 'a' and n.attrs.get('href')):
        destination = urlsplit(html.unescape(anchor.attrs['href']))
        if destination.netloc not in ('', 'cochinwood.in', 'www.cochinwood.in'):
            continue
        approved = owner_image(destination.path)
        if not approved:
            continue
        visual = next((n for n in tree.nodes if n.tag in ('picture', 'img') and anchor.contains(n)), None)
        if visual:
            replacements.append((visual.start, visual.end, image(approved)))
    for start, end, replacement in sorted(replacements, reverse=True):
        body = body[:start] + replacement + body[end:]
    return body + '<!-- data-editorial-pass="1" -->'
