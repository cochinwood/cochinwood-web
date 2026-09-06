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


def enhance_wood_hub(body, link, wood_path):
    """Inject controls and attributes only; retain the original cards/copy bytewise."""
    if 'data-wood-controls' in body:
        raise ValueError('Wood hub navigation must be applied only once')
    scan = HubScan(body)
    scan.feed(body)
    if len(scan.groups) != 3 or len(scan.cards) != 28:
        raise ValueError('Expected three wood groups and 28 species cards')
    edits, metadata = [], []
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


def render_species_navigation(metadata, current_path, link, wood_path='/woods-we-use'):
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
            + escape(item['group_label']) + '</a></nav>')
    neighbours = []
    for label, offset in [('Previous alphabetically', -1), ('Next alphabetically', 1)]:
        neighbour_index = index + offset
        if 0 <= neighbour_index < len(items):
            other = items[neighbour_index]
            neighbours.append('<a href="' + escape(other['url'], quote=True) + '"><span>' + label
                              + '</span><b>' + escape(other['name']) + '</b></a>')
    return back + '<nav class="cw-species-neighbours" aria-label="Species in alphabetical order">' + ''.join(neighbours) + '</nav>'
