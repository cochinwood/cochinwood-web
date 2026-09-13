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
    comparison = '''<section class="cw-section cw-catalogue-compare" id="compare"><div class="cw-wrap">
      <div class="cw-section__head"><div><p class="cw-eyebrow">Quick comparison</p><h2>Choose by application.</h2></div>
        <p>Use this as a starting point, then confirm the exact grade, thickness, face and tolerance on the written quotation.</p></div>
      <div class="cw-compare-scroll"><table class="cw-compare-table"><caption class="sr-only">Cochin Wood product comparison</caption>
        <thead><tr><th scope="col">Product family</th><th scope="col">Suitable applications</th><th scope="col">Bond / grade</th><th scope="col">Core / surface</th><th scope="col">Thickness choices</th><th scope="col">Important limitation</th></tr></thead>
        <tbody>
          <tr><th scope="row"><a href="/packing-plywood">Packing-grade plywood</a></th><td>Cases, crates and pallets</td><td>MR; IS 303 when specified</td><td>Rubberwood or eucalyptus hardwood core; Okoume or Gurjan face options</td><td>6–18 mm typical; other sizes within the band to order</td><td>Minus tolerance; confirm the tolerance on the quote. Not for permanent wet service.</td></tr>
          <tr><th scope="row"><a href="/commercial-plywood">Commercial plywood</a></th><td>Dry interiors, furniture and cabinetry; BWR for humid rooms</td><td>IS 303 MR or BWR</td><td>Hardwood or mixed hardwood core; Gurjan / keruing faces</td><td>MR 4–25 mm; BWR 6–25 mm</td><td>Choose BWR for humidity. Marine plywood is a separate product.</td></tr>
          <tr><th scope="row"><a href="/marine-plywood">Marine plywood</a></th><td>Boatbuilding, hulls, decks and prolonged wet duty</td><td>IS 710 BWP; phenol-formaldehyde bond</td><td>Full hardwood, gap-free core veneers</td><td>4–25 mm</td><td>Confirm any BS 1088 requirement and the final construction on the quote.</td></tr>
          <tr><th scope="row"><a href="/film-faced-shuttering-plywood">Film-faced shuttering</a></th><td>Concrete formwork</td><td>IS 303 BWR; phenolic WBP</td><td>Full-hardwood core; phenolic film both faces</td><td>12, 15, 18, 21 and 25 mm</td><td>Working life depends on handling and edge care; state the pour programme.</td></tr>
          <tr><th scope="row"><a href="/container-flooring-plywood">Container flooring</a></th><td>Container floors and rolling cargo loads</td><td>IICL TB-001; phenol-formaldehyde WBP</td><td>Full hardwood core; phenolic film and anti-slip wire-mesh surface</td><td>28 mm (±0.5); 21/27/30 mm by request</td><td>Machining follows the container model drawing; verify the model before order.</td></tr>
          <tr><th scope="row"><a href="/chequered-anti-skid-plywood">Chequered anti-skid</a></th><td>Vehicle and trailer decks, scaffold platforms and walkways</td><td>Phenol-formaldehyde WBP</td><td>Marine / hardwood core; chequer or wire-mesh phenolic film</td><td>12–28 mm</td><td>Pattern, edges and final face construction are confirmed per quotation.</td></tr>
          <tr><th scope="row"><a href="/okoume-plywood">Okoume-faced plywood</a></th><td>Export packing faces, painted furniture and joinery</td><td>MR base to IS 303; BWR base and calibrated options on request</td><td>Okoume face; eucalyptus core for the calibrated option</td><td>6, 8, 12, 15 and 18 mm typical for MR packing</td><td>Okoume is a face option, not a bond grade. Confirm the base bond and calibration.</td></tr>
        </tbody>
      </table></div>
      <div class="cw-compare-actions"><p>Need a tighter tolerance, a calibrated panel or a custom size?</p><a class="cw-btn cw-btn--p" href="/contact#quote">Request a written specification</a><button type="button" class="cw-btn cw-btn--g" data-print-catalogue>Print this comparison</button></div>
    </div></section>'''
    for route in ('packing-plywood', 'commercial-plywood', 'marine-plywood',
                  'film-faced-shuttering-plywood', 'container-flooring-plywood',
                  'chequered-anti-skid-plywood', 'okoume-plywood'):
        comparison = comparison.replace(f'href="/{route}"', f'href="{href("/" + route)}"')
    comparison = comparison.replace('href="/contact#quote"', f'href="{href("/contact#quote")}"')
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
    {comparison}
    <section class="cw-band"><div class="cw-wrap cw-band__in"><div><h2>Start with what you’re making.</h2><p>Send the application and destination. We’ll help you choose a suitable material.</p></div><a class="cw-btn cw-btn--p" href="{href('/contact#quote')}">Help me choose →</a></div></section>'''
