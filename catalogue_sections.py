"""Catalogue families with native navigation and the existing product routes.

render_catalogue(link, visual_image, media, products, product_card) returns body
HTML. The generator owns the shell and the 16-product ItemList schema. Species
are choices within Sawn Timber, not additional product lines. Media must include
an inspected timber_species mapping; missing choices fail the build explicitly.
"""
from html import escape

PLYWOOD_GROUPS = (
    ('packing', 'Packing plywood', ('packing-plywood', 'okoume-plywood', 'rubberwood-plywood')),
    ('construction', 'Construction & demanding use', ('marine-plywood', 'film-faced-shuttering-plywood',
        'container-flooring-plywood', 'bwr-hardwood-plywood', 'chequered-anti-skid-plywood')),
    ('interiors', 'Interiors & joinery', ('commercial-plywood', 'block-board-flush-doors',
        'finger-joint-board', 'particle-board')),
)
PACKAGING = ('plywood-boxes-crates', 'plywood-pallets', 'plywood-cable-drums')
TIMBER = (
    ('eucalyptus', 'Eucalyptus'), ('rubberwood', 'Rubberwood'), ('acacia', 'Acacia'),
    ('mahogany', 'Mahogany'), ('jackwood', 'Jackwood'), ('silverwood', 'Silverwood'),
    ('specialty-timbers', 'Specialty timbers'),
)


def render_catalogue(link, visual_image, media, products, product_card):
    """Keep product identity stable while exposing all three families early."""
    routes = [slug for _, _, slugs in PLYWOOD_GROUPS for slug in slugs] + list(PACKAGING) + ['sawn-timber']
    if len(routes) != len(set(routes)) or set(routes) != {p[0] for p in products}:
        raise ValueError('Catalogue families must cover each existing product exactly once')
    species = media['timber_species']
    if set(species) != {slug for slug, _ in TIMBER}:
        raise ValueError('Catalogue requires the seven reviewed timber choices')
    href = lambda path: escape(link(path), quote=True)
    jumps = '''<nav class="cw-catalogue-jumps" aria-label="Product families">
      <a href="#plywood-boards"><span>01</span> Plywood &amp; boards <b aria-hidden="true">↓</b></a>
      <a href="#packing-packaging"><span>02</span> Packing cases &amp; packaging <b aria-hidden="true">↓</b></a>
      <a href="#timber"><span>03</span> Timber <b aria-hidden="true">↓</b></a>
    </nav>'''
    plywood = ''.join(
        f'<div class="cw-catalogue-subgroup" id="{key}"><h3>{escape(title)}</h3>'
        f'<div class="cw-product-grid">{"".join(product_card(slug, level=4) for slug in slugs)}</div></div>'
        for key, title, slugs in PLYWOOD_GROUPS
    )
    packaging = ''.join(product_card(slug) for slug in PACKAGING)
    timber_cards = ''.join(
        '<a class="cw-timber-choice" href="' + href('/sawn-timber') + '">'
        '<div class="cw-timber-choice__image">'
        + visual_image(species[slug], sizes='(max-width: 560px) 100vw, (max-width: 860px) 50vw, 25vw')
        + '</div><div class="cw-timber-choice__text"><h3>' + escape(label) + '</h3>'
        + '<span>' + ('Discuss your species' if slug == 'specialty-timbers' else 'Explore sawn timber')
        + ' <b aria-hidden="true">↗</b></span></div></a>'
        for slug, label in TIMBER
    )
    return f'''<section class="cw-hero cw-hero--light"><div class="cw-wrap"><div class="cw-hero__layout">
      <div class="cw-hero__content"><p class="cw-hero__ey">Plywood, packaging &amp; timber</p>
        <h1>The full <em>catalogue.</em></h1><p>Find the panel, packing case or timber your work needs.</p>
        {jumps}
      </div><figure class="cw-hero__media">{visual_image(media['catalogue_hero'], eager=True)}</figure>
    </div></div></section>
    <section class="cw-section cw-catalogue-family" id="plywood-boards"><div class="cw-wrap">
      <div class="cw-section__head"><div><p class="cw-eyebrow">01 / Plywood &amp; boards</p>
        <h2>Choose the right panel.</h2></div><p>Grades for packing, construction, furniture and joinery. Start with the application, then confirm the specification.</p></div>
      {plywood}
    </div></section>
    <section class="cw-section cw-catalogue-family cw-catalogue-family--packaging" id="packing-packaging"><div class="cw-wrap">
      <div class="cw-section__head"><div><p class="cw-eyebrow">02 / Packing cases &amp; packaging</p>
        <h2>Built around your cargo.</h2></div><p>Boxes, crates, pallets and cable drums. Discuss the load, dimensions and destination with our desk.</p></div>
      <div class="cw-product-grid">{packaging}</div>
      <p class="cw-catalogue-crosslink">Making your own cases? <a href="{href('/packing-plywood')}">Explore packing plywood →</a></p>
    </div></section>
    <section class="cw-section cw-catalogue-family" id="timber"><div class="cw-wrap">
      <span id="sawn-timber" class="cw-catalogue-anchor" aria-hidden="true"></span>
      <div class="cw-section__head"><div><p class="cw-eyebrow">03 / Timber</p>
        <h2>Start with the species.</h2></div><p>Six named species and specialty timber enquiries. Species, seasoning, dimensions and quantity are confirmed in the written specification.</p></div>
      <div class="cw-timber-grid">{timber_cards}</div>
      <p class="cw-catalogue-crosslink"><a href="{href('/sawn-timber')}">See sawn timber forms, specifications and ordering details →</a></p>
    </div></section>
    <section class="cw-band"><div class="cw-wrap cw-band__in"><div><h2>Start with what you’re making.</h2><p>Send the application and destination. We’ll help you choose a suitable material.</p></div><a class="cw-btn cw-btn--p" href="{href('/contact#quote')}">Help me choose →</a></div></section>'''
