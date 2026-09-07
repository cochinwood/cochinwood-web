"""Preserving enhancement for the existing wood hub; no article content rewrite."""
from html import escape
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit

GROUP_KEYS = ('veneer', 'packing', 'indian')


class HubScan(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.lines = [0] + [m.end() for m in re.finditer('\n', source)]
        self.groups = []
        self.cards = []
        self.group = None
        self.card = None
        self.capture = None

    def position(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()
        record = {'position': self.position(), 'tag': self.get_starttag_text(), 'attrs': attrs}
        if 'cwe__group' in classes:
            self.group = dict(record, label='')
            self.groups.append(self.group)
        if 'cwe__card' in classes and tag == 'a':
            self.card = dict(record, name='', botanical='', group=self.group)
            self.cards.append(self.card)
        if tag == 'h2' and self.group and not self.group['label']:
            self.capture = (tag, self.group, 'label')
        elif self.card and 'cwe__card-name' in classes:
            self.capture = (tag, self.card, 'name')
        elif self.card and 'cwe__card-sci' in classes:
            self.capture = (tag, self.card, 'botanical')

    def handle_data(self, data):
        if self.capture:
            _, record, key = self.capture
            record[key] += data

    def handle_endtag(self, tag):
        if self.capture and self.capture[0] == tag:
            _, record, key = self.capture
            record[key] = re.sub(r'\s+', ' ', record[key]).strip()
            self.capture = None
        if tag == 'a':
            self.card = None


def wood_card_sizes(scale=1.12):
    """Request sufficient pixels for the reviewed CSS crop, including on phones."""
    return (f'(max-width: 480px) min({370*scale:g}px, calc({100*scale:g}vw - {40*scale:g}px)), '
            f'(max-width: 900px) calc({44.5*scale:g}vw - {12*scale:g}px), '
            f'(max-width: 1199px) calc({29.666667*scale:g}vw - {16*scale:g}px), '
            f'(max-width: 1440px) calc({22.25*scale:g}vw - {18*scale:g}px), {300*scale:g}px')

# The index uses grain details; full identified specimens remain in each gallery.
# Birch is an end-grain reference, so its display crop must retain that distinction.
CARD_DETAIL_CROPS = {
    '/files/Species/birch-wood.webp': ('birch-end-grain', 'End-grain detail', 'Betula pendula', 1.75),
    '/files/Species/matti-wood.webp': ('matti-grain', 'Wood-grain detail', 'Terminalia crenulata', 2.8),
    '/files/Species/venteak-wood.webp': ('venteak-grain', 'Wood-grain detail', 'Lagerstroemia microcarpa', 2.5),
    '/files/Species/jackwood-wood.webp': ('jackwood-grain', 'Wood-grain detail', 'Artocarpus heterophyllus', 1.6),
}
# The complete 370px research figure is useful in its gallery but cannot provide
# a sharp close-up at the card's display size. Never invent detail by upscaling.
PENDING_GRAIN_PHOTOS = {'/files/Species/anjili-wood.webp'}
SPECIES_DISPLAY_ROTATIONS = {'/files/Species/neem-botanical.webp': 90}


def orient_species_image(tag, item):
    """Correct one photographed orientation in display, preserving source bytes."""
    if SPECIES_DISPLAY_ROTATIONS.get(item['src']) == 90:
        return '<span class="cw-species-image-turn" data-reference-rotation="90">' + tag + '</span>'
    return tag


def species_thumbnail(entry):
    """Prefer actual wood; botanical-only entries retain their truthful type."""
    images = entry.get('images', [])
    if not images:
        raise ValueError('Every species card needs an identified reference image')
    item = next((x for x in images if x.get('kind') != 'taxon-identified botanical reference'), images[0])
    for key in ('src', 'alt', 'kind', 'pictured_taxon', 'credit', 'license', 'source_url', 'sha256'):
        if not isinstance(item.get(key), str) or not item[key].strip():
            raise ValueError('Species thumbnail is missing verified metadata: ' + key)
    label = 'Tree reference' if item['kind'] == 'taxon-identified botanical reference' else 'Wood reference'
    return item, label


def _card_photo(entry, image):
    item, label = species_thumbnail(entry)
    if label == 'Tree reference' or item['src'] in PENDING_GRAIN_PHOTOS:
        inside = 'Botanical references inside' if label == 'Tree reference' else 'Wood reference inside'
        return ('<span class="cwe__card-photo cwe__card-photo--pending">'
                '<span>Grain photograph pending</span></span>'
                '<span class="cwe__card-photo-kind">' + inside + '</span>')
    crop = CARD_DETAIL_CROPS.get(item['src'])
    if crop:
        item = dict(item, alt=crop[1] + ' of ' + crop[2] + ' from an identified wood specimen')
    tag = image(item, eager=False, sizes=wood_card_sizes(crop[3] if crop else 1.12))
    if item.get('max_display_width') is not None:
        cap = item['max_display_width']
        if isinstance(cap, bool) or not isinstance(cap, (int, float)) or not 100 <= cap <= 2000:
            raise ValueError('Species image display cap must be from 100 to 2000 pixels')
        style = f'max-width:{cap:g}px'
        if item.get('width') and item.get('height'):
            style += f';max-height:{cap * item["height"] / item["width"]:g}px'
        tag = tag.replace('<img ', f'<img style="{style}" ', 1)
    # The whole card links to its species, where the complete source/licence
    # links remain next to the photograph. No nested anchors inside the card.
    detail = ' data-reference-detail="' + crop[0] + '"' if crop else ''
    label = crop[1] if crop else 'Wood-grain detail'
    return ('<span class="cwe__card-photo" data-reference-fit="cover"' + detail + '>' + tag + '</span>'
            '<span class="cwe__card-photo-kind">' + label + '</span>'
            '<span class="cwe__card-photo-credit">' + escape(item['credit'])
            + ' · ' + escape(item['license']) + '</span>')


def enhance_wood_hub(body, link, wood_path, *, image=None, species_media=None):
    """Add controls and verified photos; retain original card copy and links."""
    if (image is None) != (species_media is None):
        raise ValueError('Wood card images require both the image renderer and species records')
    if 'data-wood-controls' in body:
        raise ValueError('Wood hub navigation must be applied only once')
    scan = HubScan(body)
    scan.feed(body)
    if len(scan.groups) != 3 or len(scan.cards) != 28:
        raise ValueError('Expected three wood groups and 28 species cards')
    edits, metadata, image_hashes = [], [], set()
    for group, key in zip(scan.groups, GROUP_KEYS):
        group['key'] = key
        group['anchor'] = group['attrs'].get('id') or 'wood-group-' + key
        attributes = f' data-wood-group="{key}"'
        if not group['attrs'].get('id'):
            attributes += f' id="{group["anchor"]}"'
        edits.append((group['position'] + len(group['tag']) - 1, attributes))
    for card in scan.cards:
        group = card['group']
        if not group or not card['name']:
            raise ValueError('Every species card needs its original name and group')
        url = card['attrs'].get('href', '')
        if not url or not urlsplit(url).path.startswith(wood_path.rstrip('/') + '/'):
            raise ValueError('Species links must already be rewritten to the wood hub')
        metadata.append({'url': url, 'name': card['name'], 'botanical': card['botanical'],
                         'groupkey': group['key'], 'group_label': group['label'], 'group_anchor': group['anchor']})
        attributes = (' data-wood-card="' + group['key'] + '" data-wood-search="'
                      + escape(card['name'] + ' ' + card['botanical'], quote=True) + '"')
        edits.append((card['position'] + len(card['tag']) - 1, attributes))
        if species_media is not None:
            slug = urlsplit(url).path.rstrip('/').rsplit('/', 1)[-1]
            if slug not in species_media:
                raise ValueError('Missing verified image entry for species: ' + slug)
            item, _label = species_thumbnail(species_media[slug])
            if item['sha256'] in image_hashes:
                raise ValueError('A photograph cannot identify two different species cards')
            image_hashes.add(item['sha256'])
            edits.append((card['position'] + len(card['tag']), _card_photo(species_media[slug], image)))
    if len({item['url'] for item in metadata}) != 28:
        raise ValueError('Species navigation requires 28 distinct destinations')
    metadata.sort(key=lambda item: item['name'].casefold())
    filters = '<a href="#wood-browse" data-wood-filter="all" aria-current="true">All species</a>'
    filters += ''.join('<a href="#' + escape(g['anchor'], quote=True) + '" data-wood-filter="'
                       + g['key'] + '">' + escape(g['label']) + '</a>' for g in scan.groups)
    az = ''.join('<li><a href="' + escape(item['url'], quote=True) + '">' + escape(item['name'])
                 + '</a></li>' for item in metadata)
    controls = '''<div class="cw-wood-navigation" id="wood-browse" data-wood-controls>
      <div class="cw-wood-search"><label for="cw-wood-search">Find a wood species</label>
      <div class="cw-wood-search-row"><input id="cw-wood-search" type="search" autocomplete="off" placeholder="Common or botanical name"><button id="cw-wood-clear" type="button" hidden>Clear filters</button></div>
      <p id="cw-wood-count" role="status" aria-live="polite">28 species across three groups</p></div>
      <nav class="cw-wood-filters" aria-label="Wood categories">''' + filters + '''</nav>
      <details class="cw-wood-az"><summary>All 28 species, A–Z</summary><ul>''' + az + '''</ul></details>
      <p id="cw-wood-empty" hidden>No species match these filters. Try another name or clear the filters.</p>
    </div>'''
    edits.append((scan.groups[0]['position'], controls))
    for position, text in sorted(edits, key=lambda edit: edit[0], reverse=True):
        body = body[:position] + text + body[position:]
    return body, metadata


def enhance_species_reference_gallery(body):
    """Give the existing image collection a visible heading and a stable target."""
    from hero_layout import parse_fragment
    tree = parse_fragment(body)
    galleries = [n for n in tree.nodes if n.tag == 'section' and 'cw-species-reference' in n.classes]
    if len(galleries) != 1:
        raise ValueError('Expected one existing species reference gallery')
    if any(n.attrs.get('id') == 'species-images' for n in tree.nodes):
        raise ValueError('The species photo target must be unique')
    gallery = galleries[0]
    heading = '<h2 class="cw-species-reference__title" id="species-images">Photo references</h2>'
    return body[:gallery.open_end] + heading + body[gallery.open_end:]


def render_species_navigation(metadata, current_path, link, wood_path='/woods-we-use', *, photo_reference=False):
    """Return honest alphabetical neighbours and category/back links, without wrap."""
    path = urlsplit(current_path).path.rstrip('/')
    items = sorted(metadata, key=lambda item: item['name'].casefold())
    index = next((i for i, item in enumerate(items) if urlsplit(item['url']).path.rstrip('/') == path), None)
    if index is None:
        raise ValueError('Current wood page must exist in the hub metadata')
    item = items[index]
    href = lambda value: escape(link(value), quote=True)
    category = wood_path + '?group=' + item['groupkey'] + '#' + item['group_anchor']
    back = ('<nav class="cw-species-context" aria-label="Wood encyclopedia navigation"><a href="'
            + href(wood_path) + '">← All wood species</a><a href="' + href(category) + '">'
            + escape(item['group_label']) + '</a>'
            + ('<a href="#species-images">Photo references</a>' if photo_reference else '') + '</nav>')
    neighbours = []
    for label, offset in [('Previous alphabetically', -1), ('Next alphabetically', 1)]:
        neighbour_index = index + offset
        if 0 <= neighbour_index < len(items):
            other = items[neighbour_index]
            neighbours.append('<a href="' + escape(other['url'], quote=True) + '"><span>' + label
                              + '</span><b>' + escape(other['name']) + '</b></a>')
    return back + '<nav class="cw-species-neighbours" aria-label="Species in alphabetical order">' + ''.join(neighbours) + '</nav>'
