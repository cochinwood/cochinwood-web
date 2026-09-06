"""Native section navigation for the shared inner-page shell.

Heading targets use the same source-preserving helper as blog articles. The
normalised hero is the sole insertion point; existing article copy stays intact.
"""
from html import escape, unescape
import re

from blog_navigation import enrich_article
from hero_layout import hero_end


SECTION_LABELS = {
    '/industries': ['Sectors', 'Manufacturing', 'Capabilities', 'Applications', 'Enquire'],
    '/export': ['Destinations', 'Products', 'Container loading', 'ISPM 15', 'Terms & documents', 'FAQs', 'Request quote', 'Order process'],
}
SPECIES_LABELS = {
    'where-it-grows': 'Origin', 'appearance-and-grain': 'Appearance',
    'weight-density-and-strength': 'Strength', 'working-gluing-and-finishing': 'Working & finishing',
    'durability-and-treatment': 'Durability', 'sustainability-and-legality': 'Sourcing',
    'faq': 'FAQs', 'references': 'References', 'related': 'Related species',
}


def _section_links(listing, path):
    anchors = re.findall(r'<a href="([^"]+)">(.*?)</a>', listing, re.S)
    custom = SECTION_LABELS.get(path, [])
    items = []
    for index, (href, source_label) in enumerate(anchors):
        full = unescape(re.sub(r'<[^>]+>', '', source_label)).strip()
        target = href.lstrip('#')
        label = full.rstrip('.:')
        if len(custom) == len(anchors):
            label = custom[index]
        elif path.startswith('/woods-we-use/'):
            label = SPECIES_LABELS.get(target, label)
            if target.startswith('what-'):
                label = 'Overview'
            elif target.startswith('how-cochin-wood-uses-'):
                label = 'Uses'
            elif target.startswith(('need-', 'ask-', 'request-')):
                label = 'Enquire'
        if len(label) > 48:
            label = ' '.join(label.split()[:7]).rstrip('.,:') + '…'
        items.append('<li><a href="' + escape(unescape(href), quote=True)
                     + '" title="' + escape(full, quote=True) + '">'
                     + escape(label) + '</a></li>')
    return ''.join(items), len(items)



def render_section_bar(links, *, label='Sections', nav_label='On this page', nav_class='', mode='sections'):
    """Shared shell for native section anchors or the blog's existing topic filters."""
    return ('<div class="cw-section-bar" data-section-mode="' + escape(mode, quote=True)
            + '"><div class="cw-section-bar__inner"><details class="cw-section-menu" open>'
            + '<summary><span>' + escape(label) + '</span><span class="cw-section-current">'
            + ('All posts' if mode == 'filters' else 'Choose a section') + '</span></summary>'
            + '<div class="cw-section-scroll"><button type="button" class="cw-section-scroll__button" data-section-direction="-1" aria-label="Previous sections" hidden>←</button>'
            + '<nav aria-label="' + escape(nav_label, quote=True) + '" class="' + escape(nav_class, quote=True)
            + '"><ol class="cw-section-links">' + links + '</ol></nav>'
            + '<button type="button" class="cw-section-scroll__button" data-section-direction="1" aria-label="More sections" hidden>→</button>'
            + '</div></details></div></div>')


def _context_markup(context):
    return ('<div class="cw-page-navigation"><div class="cw-page-navigation__inner">'
            + context + '</div></div>')


def add_page_navigation(body, path, *, context=""):
    """Return a page with a compact section menu after its recognised hero.

Indexes and blog articles already have their own discovery/contents navigation.
Contact stays focused on its form. Native details and anchors work without JS.
"""
    if path == '/products' and hero_end(body) is not None:
        families = [('#plywood-boards', 'Plywood & boards'), ('#packing-packaging', 'Packing cases & packaging'), ('#timber', 'Timber')]
        # Move the existing hero family choices into the same sticky shell.
        # Their destination IDs and the catalogue's subcollection anchors remain.
        body = re.sub(r'<nav\b[^>]*\bclass="cw-catalogue-jumps"[^>]*>.*?</nav>', '', body, count=1, flags=re.S)
        links = ''.join('<li><a href="' + href + '">' + escape(label) + '</a></li>' for href, label in families)
        end = hero_end(body)
        return body[:end] + (_context_markup(context) if context else '') + render_section_bar(links) + body[end:]
    excluded = path in {"/", "/products", "/blogs", "/woods-we-use", "/contact", "/404"} or path.startswith("/blogs/post/")
    end = hero_end(body)
    if excluded or end is None:
        if not context:
            return body
        insertion = end if end is not None else 0
        return body[:insertion] + _context_markup(context) + body[insertion:]
    enriched, toc, _ = enrich_article(body)
    listing = re.search(r'<ol class="cw-article-toc__list">(.*?)</ol>', toc, re.S)
    links, count = _section_links(listing.group(1), path) if listing else ('', 0)
    menu = ''
    if count >= 2:
        menu = render_section_bar(links)
    if not context and not menu:
        return enriched
    end = hero_end(enriched)
    # Context is deliberately outside the sticky row; long species/regional
    # breadcrumbs never increase its height or create a second sticky bar.
    parent = _context_markup(context) if context else ''
    return enriched[:end] + parent + menu + enriched[end:]


def parent_navigation(label, href):
    return ('<nav class="cw-section-parent" aria-label="Section navigation"><a href="'
            + escape(href, quote=True) + '"><span aria-hidden="true">←</span> '
            + escape(label) + '</a></nav>')
