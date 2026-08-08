#!/usr/bin/env python3
"""
Cochin Wood Industries — clean static-site builder (no external deps).

Source in this repo -> renders to dist/. Set SITE_BASE to deploy under a
subpath (e.g. /cochinwood-web for GitHub project Pages); leave empty for the
domain root (Cloudflare Pages at cochinwood.in).

    python build.py          # builds to dist/ at root ("")
    SITE_BASE=/cochinwood-web python build.py
"""
import os, re, json, shutil, html, urllib.parse, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
BASE = os.environ.get("SITE_BASE", "").rstrip("/")   # "" or "/cochinwood-web"
LIVE = "https://www.cochinwood.in"                    # canonical production host
STRICT = os.environ.get("STRICT") == "1"              # fail the build on any warning
def u(path): return (BASE + path) if path.startswith("/") else path

WARNINGS = []
def warn(msg):
    if msg not in WARNINGS: WARNINGS.append(msg)

# Legacy Zoho slugs that inbound links, old sitemaps and in-content cross-links
# still point at. Rewritten in content at build time AND served as 301s so
# external inbound links keep their SEO value.
LEGACY_REDIRECTS = {
    "/guide-block-board-vs-plywood":           "/blogs/post/block-board-vs-plywood",
    "/guide-bwp-bwr-plywood-explained":        "/blogs/post/bwp-and-bwr-plywood-explained",
    "/guide-film-faced-plywood-pours":         "/blogs/post/how-many-pours-does-film-faced-plywood-last",
    "/guide-fob-cochin-explained":             "/blogs/post/fob-cochin-explained",
    "/guide-iicl-tb-001-container-flooring":   "/blogs/post/iicl-tb-001-container-flooring-plywood",
    "/guide-is-710-vs-is-303":                 "/blogs/post/is-710-vs-is-303-plywood",
    "/guide-ispm-15-crate-cost":               "/blogs/post/ispm-15-export-crate-cost",
    "/guide-marine-plywood-thickness":         "/blogs/post/marine-plywood-thickness-guide",
    "/guide-okoume-vs-gurjan":                 "/blogs/post/okoume-vs-gurjan-plywood",
    "/guide-plywood-boxes-ispm-15":            "/blogs/post/do-plywood-boxes-need-ispm-15",
    "/guide-plywood-cable-drum-specifications":"/blogs/post/plywood-cable-drum-specifications",
    "/guide-plywood-for-packing-cases":        "/blogs/post/plywood-for-packing-cases",
    "/guide-rubberwood-plywood-explained":     "/blogs/post/rubberwood-plywood-explained",
    "/okoume-plywood":                         "/blogs/post/okoume-plywood",
    "/packing-grade-plywood-spec-sheet":       "/blogs/post/packing-grade-plywood-spec-sheet",
    # encyclopedia moved out of /blogs/post/ into its own section
    "/blogs/post/wood-okoume-aucoumea-klaineana":     "/wood-encyclopedia/okoume",
    "/blogs/post/wood-eucalyptus":                    "/wood-encyclopedia/eucalyptus",
    "/blogs/post/wood-gurjan-keruing-dipterocarpus":  "/wood-encyclopedia/gurjan",
}

CONTACT = dict(email="sales@cochinwood.in", phone_disp="+91 95674 10175",
               phone_href="+919567410175", addr="Kuruppampady, Ernakulam, Kerala 683545",
               wa="919567410175")

# ---------------- photography ----------------
# Site photography is referenced as /files/... (the old Zoho paths). Look for the
# real files in the repo first, then in an external mirror checkout. Anything
# that resolves is copied into dist/; anything that does not is removed from the
# markup so a broken image never ships, and reported at the end of the build.
MIRROR_DIR = os.environ.get("MIRROR_DIR", os.path.join(os.path.dirname(ROOT), "cochinwood-site"))
PHOTO_ROOTS = [os.path.join(ROOT, "assets", "photos"), MIRROR_DIR]

_files_used, _files_missing = set(), set()

# Legacy Zoho asset paths whose real file already lives in the repo.
FILE_ALIASES = {"files/Logo/Cochin wood logo.png": os.path.join(ROOT, "assets", "logo.png")}

def resolve_file(ref):
    """/files/Product/x.jpg -> absolute source path on disk, or None."""
    rel = urllib.parse.unquote(ref.lstrip("/").split("?")[0])
    if rel in FILE_ALIASES: return FILE_ALIASES[rel]
    for rootdir in PHOTO_ROOTS:
        p = os.path.join(rootdir, rel)
        if os.path.isfile(p): return p
    return None

# Wrappers that exist only to hold one photo — drop the whole box when the photo
# is missing, otherwise the CSS leaves a sized empty panel behind.
_PHOTO_WRAPPERS = [
    (re.compile(r'<figure class="cwop-card">\s*<img\b[^>]*>\s*</figure>', re.I), "figure.cwop-card"),
    (re.compile(r'<div class="cwp__hero-img">\s*<img\b[^>]*>\s*</div>', re.I), "div.cwp__hero-img"),
    (re.compile(r'<div class="cw__hero-img">\s*<img\b[^>]*>\s*</div>', re.I), "div.cw__hero-img"),
]

def _img_is_dead(tag):
    src = re.search(r'src="([^"]+)"', tag)
    if not src: return None
    s = src.group(1)
    if "zohocdn.com" in s:
        return "Zoho stock placeholder"                      # never our photography
    if s.startswith("/files/"):
        if resolve_file(s):
            _files_used.add(s); return None
        _files_missing.add(s)
        return "missing source file"
    return None

def prune_images(body):
    """Remove images with no real source, plus their photo-only wrapper."""
    for pat, what in _PHOTO_WRAPPERS:
        def wrap(m):
            inner = re.search(r'<img\b[^>]*>', m.group(0), re.I)
            return "" if (inner and _img_is_dead(inner.group(0))) else m.group(0)
        body = pat.sub(wrap, body)
    return re.sub(r'<img\b[^>]*>', lambda m: "" if _img_is_dead(m.group(0)) else m.group(0), body, flags=re.I)

# ---------------- links ----------------
_LEGACY_RE = re.compile(r'((?:src|href)=")(' + "|".join(
    re.escape(k) for k in sorted(LEGACY_REDIRECTS, key=len, reverse=True)) + r')(?=["/#?])')

def rewrite_links(body):
    """Retarget legacy slugs, then make every same-origin link BASE-relative."""
    body = _LEGACY_RE.sub(lambda m: m.group(1) + LEGACY_REDIRECTS[m.group(2)], body)
    # absolute self-links -> root-relative so previews and SITE_BASE builds work
    body = re.sub(r'((?:src|href)=")https?://(?:www\.)?cochinwood\.in(?=[/"])', r'\1', body)
    body = re.sub(r'((?:src|href)=")/(?!/)', r'\1' + BASE + '/', body)
    return body

PRODUCTS = [
    ("commercial-plywood","Commercial Plywood","MR-grade plywood for furniture and general interior work."),
    ("marine-plywood","Marine Plywood","IS 710 BWP boil-proof plywood for boatyards and wet service."),
    ("film-faced-shuttering-plywood","Film-Faced Shuttering Plywood","Smooth phenolic-film ply for concrete formwork and repeat pours."),
    ("container-flooring-plywood","Container Flooring Plywood","Dense apitong/keruing-cored panels to the IICL container-floor spec."),
    ("bwr-hardwood-plywood","BWR Hardwood Plywood","Boiling-water-resistant hardwood ply for humid and coastal use."),
    ("chequered-anti-skid-plywood","Chequered Anti-Skid Plywood","Textured wire-mesh face for grip on ramps, decks and flooring."),
    ("plywood-boxes-crates","Plywood Boxes & Crates","Export packing cases and crates, ISPM-15 ready for heavy machinery."),
    ("plywood-pallets","Plywood Pallets","Two- and four-way ply and timber pallets for freight and storage."),
    ("block-board-flush-doors","Block Board & Flush Doors","Battened block board and flush doors for shutters and partitions."),
    ("finger-joint-board","Finger-Joint Board","Edge-glued solid-wood board for stable, wide worktops and panels."),
    ("particle-board","Particle Board","Economical engineered board for laminated furniture and interiors."),
    ("plywood-cable-drums","Plywood Cable Drums","IS 10418 flanges and drums for cable, wire and hose reels."),
    ("sawn-timber","Sawn Timber","Kiln-conditioned hardwood runners, scantlings and packing timber."),
]

NAV = [("Products", "/products", False), ("Industries", "/industries", False),
       ("Wood Encyclopedia", "/wood-encyclopedia/", False),
       ("Blog", "/blogs", False), ("Contact", "/contact", False)]

def header(path="/"):
    links = ""
    for label, p, external in NAV:
        href = LIVE + p if external else u(p)
        # mark the section the current page belongs to
        section = p.rstrip("/")
        cur = path == p or (section and (path == section or path.startswith(section + "/")))
        aria = ' aria-current="page"' if cur else ""
        links += f'<a href="{href}"{aria}>{label}</a>\n'
    return f'''<header class="cw-hd"><div class="cw-wrap cw-hd__in">
  <a class="cw-hd__brand" href="{u('/')}"><img src="{u('/assets/logo.png')}" alt="Cochin Wood Industries logo" width="40" height="40"><span style="display:block"><b>Cochin Wood Industries</b><span>Plywood Manufacturer &middot; Kochi</span></span></a>
  <button class="cw-burger" type="button" aria-label="Menu" aria-expanded="false" aria-controls="nav">&#9776;</button>
  <nav class="cw-nav" id="nav" aria-label="Primary">
    {links}<a class="cw-cta" href="{u('/contact')}">Get a quote</a>
  </nav>
</div></header>'''

def footer():
    prod = "".join(f'<a href="{u("/"+s)}">{n}</a>' for s,n,_ in PRODUCTS[:7])
    return f'''<footer class="cw-ft"><div class="cw-wrap">
  <div class="cw-ft__cols">
    <div class="cw-ft__brand"><b>Cochin Wood Industries</b><p>Plywood manufacturer in Kochi, Kerala — packing, Okoume and shuttering ply, shipped across India and exported. Part of a group manufacturing in Perumbavoor since 1986.</p></div>
    <div><h4>Products</h4>{prod}</div>
    <div><h4>Explore</h4><a href="{u('/products')}">All products</a><a href="{u('/wood-encyclopedia/')}">Wood Encyclopedia</a><a href="{u('/resources')}">Resources</a><a href="{u('/industries')}">Industries</a><a href="{u('/about')}">About</a><a href="{u('/faq')}">FAQ</a></div>
    <div><h4>Contact</h4><a href="tel:{CONTACT['phone_href']}">{CONTACT['phone_disp']}</a><a href="mailto:{CONTACT['email']}">{CONTACT['email']}</a><a href="https://maps.google.com/?q=Kuruppampady+Kerala" target="_blank" rel="noopener">{CONTACT['addr']}</a></div>
  </div>
  <div class="cw-ft__bar"><span>&copy; 2026 Cochin Wood Industries Pvt Ltd. Group established 1986.</span>
  <span><a href="{u('/privacy-policy')}" style="display:inline">Privacy</a> &middot; <a href="{u('/terms-and-conditions')}" style="display:inline">Terms</a></span></div>
</div></footer>'''

OG_IMAGE = LIVE + "/assets/logo.png"          # 1000x1000 brand mark

ORG_SCHEMA = '''<script type="application/ld+json">
{"@context":"https://schema.org","@type":["Organization","LocalBusiness"],"@id":"https://www.cochinwood.in/#organization","name":"Cochin Wood Industries","url":"https://www.cochinwood.in/","logo":"https://www.cochinwood.in/assets/logo.png","image":"https://www.cochinwood.in/assets/logo.png","email":"sales@cochinwood.in","telephone":"+919567410175","address":{"@type":"PostalAddress","streetAddress":"Kuruppampady","addressLocality":"Ernakulam","addressRegion":"Kerala","postalCode":"683545","addressCountry":"IN"},"parentOrganization":{"@type":"Organization","name":"Cochin Wood Group","foundingDate":"1986"},"areaServed":["IN","AE","VN"],"description":"Plywood manufacturer in Kochi, Kerala - packing, Okoume, marine and film-faced shuttering plywood, sawn timber and export crates."}
</script>'''

# Fonts used above the fold on every page — preloaded so the header does not reflow.
PRELOAD_FONTS = ["breeserif-4UaHrEJCrhhnVA3DgluA96rp5w.woff2",
                 "poppins-pxiEyp8kv8JHgFVrJJfecg.woff2"]

def breadcrumbs(crumbs):
    """crumbs = [(label, path|None)] -> (visible nav html, BreadcrumbList schema)."""
    if not crumbs: return "", ""
    parts, items = [], []
    for i, (label, p) in enumerate(crumbs):
        last = i == len(crumbs) - 1
        parts.append(f'<span aria-current="page">{esc(label)}</span>' if last or not p
                     else f'<a href="{u(p)}">{esc(label)}</a>')
        item = {"@type": "ListItem", "position": i + 1, "name": label}
        if p: item["item"] = LIVE + p
        items.append(item)
    nav = ('<nav class="cw-crumb" aria-label="Breadcrumb"><div class="cw-wrap">'
           + ' <span class="cw-crumb__sep">&rsaquo;</span> '.join(parts) + '</div></nav>')
    ld = ('<script type="application/ld+json">'
          + json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList",
                        "itemListElement": items}, separators=(",", ":")) + '</script>')
    return nav, ld

def esc(s):
    """Titles/descriptions arrive from three sources with inconsistent escaping
    (pages_meta.json, posts.json, and the encyclopedia <title> tags). Decode
    first so a pre-escaped '&amp;' does not ship as a literal '&amp;amp;'."""
    return html.escape(html.unescape(s or ""))

def seo_title(title):
    """Search results truncate near 60 characters. When a headline already fills
    that on its own, the ' | Cochin Wood Industries' suffix only pushes real
    words out of the snippet — so drop it rather than shipping a cut-off brand."""
    head = title.split("|")[0].strip()
    return head if len(head) > 55 else title

def product_schema(slug):
    """Product + Offer markup so the 13 catalogue pages are eligible for rich results."""
    row = next((r for r in PRODUCTS if r[0] == slug), None)
    if not row: return ""
    _, name, desc = row
    data = {"@context": "https://schema.org", "@type": "Product",
            "name": name, "description": desc,
            "url": LIVE + "/" + slug,
            "image": OG_IMAGE,
            "category": "Plywood, board and timber",
            "brand": {"@type": "Brand", "name": "Cochin Wood Industries"},
            "manufacturer": {"@id": LIVE + "/#organization"},
            "offers": {"@type": "Offer", "url": LIVE + "/contact",
                       "priceCurrency": "INR",
                       "availability": "https://schema.org/InStock",
                       "areaServed": ["IN", "AE", "VN"],
                       "seller": {"@id": LIVE + "/#organization"}}}
    return ('<script type="application/ld+json">'
            + json.dumps(data, separators=(",", ":")) + '</script>')

def base(title, desc, path, body, body_class="", extra_head="", crumbs=None,
         og_type="website", show_crumbs=True):
    canonical = LIVE + path
    crumb_nav, crumb_ld = breadcrumbs(crumbs)
    # Several imported pages already render their own trail (cwp__crumb, cwg__crumb…).
    # Keep the schema, drop our duplicate bar.
    if not show_crumbs or re.search(r'class="[^"]*\b\w*__crumb\b', body):
        crumb_nav = ""
    extra_head = ORG_SCHEMA + "\n" + crumb_ld + extra_head
    preloads = "\n".join(
        f'<link rel="preload" href="{u("/assets/fonts/"+f)}" as="font" type="font/woff2" crossorigin>'
        for f in PRELOAD_FONTS)
    if "<main" not in body:
        body = f'<main id="main">{body}</main>'
    else:
        body = body.replace("<main", '<main id="main"', 1)
    return f'''<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="{u('/assets/logo.png')}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="Cochin Wood Industries">
<meta property="og:locale" content="en_IN">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:alt" content="Cochin Wood Industries">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{OG_IMAGE}">
<meta name="theme-color" content="#1f5132">
{preloads}
<link rel="stylesheet" href="{u('/assets/bundle.css')}">
{extra_head}</head>
<body class="{body_class}">
<a class="cw-skip" href="#main">Skip to content</a>
{header(path)}
{crumb_nav}
{body}
{footer()}
<a class="cw-wa" href="https://wa.me/{CONTACT['wa']}" target="_blank" rel="noopener" aria-label="Chat with us on WhatsApp"><svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" focusable="false"><path fill="currentColor" d="M.06 24l1.68-6.16A11.87 11.87 0 010 11.9C0 5.33 5.36 0 11.95 0a11.9 11.9 0 018.42 3.48 11.75 11.75 0 013.49 8.37c0 6.56-5.36 11.9-11.96 11.9-2 0-3.96-.5-5.7-1.45L.06 24zm6.6-3.8c1.68.99 3.28 1.58 5.4 1.58 5.45 0 9.9-4.42 9.9-9.87a9.8 9.8 0 00-2.9-6.99 9.9 9.9 0 00-7-2.9C6.6 2.02 2.15 6.44 2.15 11.9c0 2.2.62 3.85 1.67 5.57l-.99 3.6 3.83-.87zm11.6-5.5c-.08-.13-.28-.2-.58-.35-.3-.15-1.76-.86-2.03-.96-.27-.1-.47-.15-.67.15-.2.3-.77.96-.94 1.16-.17.2-.35.22-.65.07-.3-.15-1.25-.46-2.38-1.47-.88-.78-1.47-1.75-1.65-2.05-.17-.3-.02-.46.13-.6.14-.14.3-.36.45-.53.15-.18.2-.3.3-.5.1-.2.05-.38-.02-.53-.08-.15-.67-1.6-.92-2.2-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.8.37-.27.3-1.04 1.02-1.04 2.48s1.07 2.88 1.22 3.08c.15.2 2.1 3.2 5.08 4.49.71.3 1.26.49 1.7.63.71.22 1.36.19 1.87.12.57-.09 1.76-.72 2-1.41.25-.7.25-1.29.18-1.41z"/></svg></a>
<button class="cw-top" type="button" aria-label="Back to top" hidden>&uarr;</button>
<script src="{u('/assets/site.js')}" defer></script>
</body>
</html>'''

def write(path, content):
    fp = os.path.join(DIST, path)
    os.makedirs(os.path.dirname(fp) or DIST, exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f: f.write(content)

# ---------------- HOME ----------------
def home():
    cards = "".join(
        f'<a class="cw-card" href="{u("/"+s)}"><h3>{n}</h3><p>{d}</p><span class="cw-card__tag">View &rarr;</span></a>'
        for s,n,d in PRODUCTS[:9])
    body = f'''
<section class="cw-hero"><div class="cw-wrap">
  <p class="cw-hero__ey">Plywood manufacturer &middot; Kochi, Kerala</p>
  <h1>Plywood, built to your spec.</h1>
  <p>Packing-grade, Okoume and film-faced shuttering plywood, sawn timber and export crates — manufactured to Cochin Wood specifications and shipped across India and abroad. Backed by a group manufacturing in Perumbavoor since 1986.</p>
  <div class="cw-hero__cta"><a class="cw-btn cw-btn--p" href="{u('/contact')}">Request a quote</a><a class="cw-btn cw-btn--g" href="{u('/products')}">See the range</a></div>
  <div class="cw-hero__strip">
    <div><b>40+ yrs</b><span>Group manufacturing since 1986</span></div>
    <div><b>Pan-India</b><span>Delivery + export (UAE, Vietnam)</span></div>
    <div><b>IS 710 / 303</b><span>Boil-proof &amp; MR grades</span></div>
  </div>
</div></section>

<section class="cw-sec"><div class="cw-wrap">
  <h2 class="cw-sec__h">Our plywood range</h2>
  <p class="cw-sec__lead">From bulk packing and Okoume panels to marine, shuttering and container-flooring plywood — sized, graded and pressed for the job.</p>
  <div class="cw-grid">{cards}</div>
  <p style="margin-top:24px"><a class="cw-card__tag" href="{u('/products')}">All 13 product lines &rarr;</a></p>
</div></section>

<section class="cw-sec cw-sec--soft"><div class="cw-wrap">
  <h2 class="cw-sec__h">Why Cochin Wood</h2>
  <div class="cw-feat">
    <div><h3>Made to specification</h3><p>Thickness, grade, glue line and face veneer built to your order — not off-the-shelf approximations.</p></div>
    <div><h3>Bulk &amp; export ready</h3><p>Container-load quantities, ISPM-15 packing and FOB Cochin pricing for overseas buyers.</p></div>
    <div><h3>Group since 1986</h3><p>Four decades of plywood manufacturing behind every order, out of Perumbavoor and Kochi.</p></div>
    <div><h3>Material guarantee</h3><p>Boil-proof and MR grades to IS 710 / IS 303, with test certificates and honest specs.</p></div>
  </div>
</div></section>

<section class="cw-sec"><div class="cw-wrap">
  <h2 class="cw-sec__h">Wood Encyclopedia</h2>
  <p class="cw-sec__lead">A working reference to the species behind plywood, packing and timber — density, hardness, workability and use, independently researched and cross-checked, with sources on every page.</p>
  <a class="cw-btn cw-btn--p" href="{u('/wood-encyclopedia/')}" style="background:var(--cw-green-700)">Open the encyclopedia &rarr;</a>
</div></section>

<section class="cw-band"><div class="cw-wrap cw-band__in">
  <div><h2>Tell us the grade, size and quantity.</h2><p>We'll quote within one business day — pan-India delivery or FOB Cochin for export.</p></div>
  <a class="cw-btn cw-btn--p" href="{u('/contact')}">Request a quote</a>
</div></section>'''
    write("index.html", base(
        "Plywood Manufacturer in Kochi, Kerala | Cochin Wood Industries",
        "Cochin Wood Industries manufactures packing, Okoume, marine and film-faced shuttering plywood, sawn timber and export crates in Kochi, Kerala. Group manufacturing since 1986. Pan-India delivery and export.",
        "/", body))

# ---------------- PRODUCTS ----------------
def products():
    cards = "".join(
        f'<a class="cw-card" href="{u("/"+s)}"><h3>{n}</h3><p>{d}</p><span class="cw-card__tag">View &rarr;</span></a>'
        for s,n,d in PRODUCTS)
    body = f'''
<section class="cw-sec"><div class="cw-wrap">
  <p class="cw-hero__ey" style="color:var(--cw-green-600)">Catalogue</p>
  <h1 class="cw-sec__h" style="font-size:clamp(1.9rem,4vw,2.8rem)">Plywood, board &amp; timber</h1>
  <p class="cw-sec__lead">Thirteen product lines, each manufactured to Cochin Wood specifications. Tell us the grade, thickness and quantity and we'll quote.</p>
  <div class="cw-grid">{cards}</div>
</div></section>
<section class="cw-band"><div class="cw-wrap cw-band__in">
  <div><h2>Not sure which grade you need?</h2><p>Send the application and destination — we'll recommend the panel and price it.</p></div>
  <a class="cw-btn cw-btn--p" href="{u('/contact')}">Request a quote</a>
</div></section>'''
    write("products/index.html", base(
        "Plywood Catalogue — Marine, Shuttering, Packing & More | Cochin Wood",
        "Cochin Wood Industries' full plywood catalogue: commercial, marine (IS 710), film-faced shuttering, container flooring, BWR hardwood, packing crates, pallets, block board and sawn timber.",
        "/products", body, crumbs=[("Home", "/"), ("Products", None)]))

# ---------------- CONTACT ----------------
PRODUCT_INTEREST = ["Commercial/Packing Grade","Wooden/Plywood Packing Case","Film Faced/Shuttering",
    "Premium/ISI/303/710","Calibrated/Modular","Container Flooring","Block Board/Flush Door","Timber/Runners/Planks"]
def contact():
    checks = "".join(f'<label><input type="checkbox" name="LEADCF35" value="{v}">{v}</label>' for v in PRODUCT_INTEREST)
    form = f'''<form action="https://crm.zoho.in/crm/WebToLeadForm" method="POST" accept-charset="UTF-8" class="cw-form" id="quote">
  <input type="hidden" name="xnQsjsdp" value="8c1293748fe2bcc59321f7d8a9f9f3bb0b51755eb854438a34">
  <input type="hidden" name="xmIwtLD" value="d40b1aef750a96dbf59cc4499048e10c3650bd8d72a9ade4a4">
  <input type="hidden" name="actionType" value="TGVhZHM=">
  <input type="hidden" name="returnURL" value="https://www.cochinwood.in/contact?sent=1#quote">
  <input class="cw-hp" type="text" name="cwq2_website" tabindex="-1" autocomplete="off" aria-hidden="true">
  <div class="cw-row">
    <div><label for="q-name">Name *</label><input id="q-name" type="text" name="Last Name" required></div>
    <div><label for="q-co">Company</label><input id="q-co" type="text" name="Company"></div>
  </div>
  <div class="cw-row">
    <div><label for="q-em">Work email *</label><input id="q-em" type="email" name="Email" required></div>
    <div><label for="q-ph">WhatsApp / phone *</label><input id="q-ph" type="tel" name="Phone" required></div>
  </div>
  <div><label>Product interest</label><div class="cw-checks">{checks}</div></div>
  <div><label for="q-port">Delivery location / port</label><input id="q-port" type="text" name="LEADCF4" placeholder="e.g. Kochi, or Jebel Ali, UAE"></div>
  <div><label for="q-msg">What do you need?</label><textarea id="q-msg" name="Description" placeholder="Grade, thickness, size, monthly quantity, delivery location"></textarea></div>
  <div><button class="cw-btn cw-btn--p" type="submit">Send enquiry</button>
  <p class="cw-note" style="margin:10px 0 0">Goes straight to our sales desk. We reply within one business day.</p></div>
</form>'''
    body = f'''
<section class="cw-sec"><div class="cw-wrap" style="max-width:820px">
  <p class="cw-hero__ey" style="color:var(--cw-green-600)">Get in touch</p>
  <h1 class="cw-sec__h" style="font-size:clamp(1.9rem,4vw,2.8rem)">Request a quote</h1>
  <p class="cw-sec__lead">Tell us the product, grade, thickness, quantity and delivery location — we reply within one business day with a price and lead time.</p>
  <div class="cw-feat" style="margin-bottom:8px">
    <div><h3>WhatsApp / Phone</h3><p><a href="tel:{CONTACT['phone_href']}">{CONTACT['phone_disp']}</a></p></div>
    <div><h3>Email</h3><p><a href="mailto:{CONTACT['email']}">{CONTACT['email']}</a></p></div>
    <div><h3>Works &amp; office</h3><p>{CONTACT['addr']}</p></div>
  </div>
  {form}
</div></section>'''
    write("contact/index.html", base(
        "Contact — Request a Plywood Quote | Cochin Wood Industries",
        "Contact Cochin Wood Industries, Kuruppampady, Ernakulam, Kerala. WhatsApp/phone +91 95674 10175 or sales@cochinwood.in for plywood quotes, pan-India and export.",
        "/contact", body, crumbs=[("Home", "/"), ("Contact", None)]))

# ---------------- WOOD ENCYCLOPEDIA (wrap existing clean pages in shared chrome) ----------------
def enc_extract(src):
    t = open(src, encoding="utf-8").read()
    title = re.search(r"<title>(.*?)</title>", t, re.S).group(1).strip()
    desc  = re.search(r'<meta name="description" content="(.*?)">', t, re.S)
    desc  = desc.group(1).strip() if desc else ""
    body  = t.split("</head>",1)[1]
    body  = body.split("<body>",1)[1].rsplit("</body>",1)[0]
    return title, desc, body

def enc_rewrite(body, slug_map):
    # hub cards: okoume.html -> /wood-encyclopedia/okoume ; species crumbs/related handled below
    for fslug in slug_map:
        body = body.replace(f'href="{fslug}.html"', f'href="{u("/wood-encyclopedia/"+fslug)}"')
    body = body.replace('href="/wood-encyclopedia"', f'href="{u("/wood-encyclopedia/")}"')
    body = body.replace('href="index.html"', f'href="{u("/wood-encyclopedia/")}"')
    return rewrite_links(prune_images(body))

def encyclopedia():
    slugs = ["okoume","gurjan","rubberwood","eucalyptus","poplar","birch",
             "meranti","gmelina","melia-dubia","acacia-mangium",
             "jackwood","mango","silver-oak","pine","semul",
             "teak","sheesham","sal","neem","mahogany"]
    encdir = os.path.join(ROOT, "content", "encyclopedia")
    # hub
    title, desc, body = enc_extract(os.path.join(encdir, "_hub.html"))
    body = enc_rewrite(body, slugs)
    write("wood-encyclopedia/index.html", base(seo_title(title), desc, "/wood-encyclopedia", body,
          body_class="cw-encbody", crumbs=[("Home", "/"), ("Wood Encyclopedia", None)]))
    # species — the imported pages carry their own visible crumb, so emit schema only
    for s in slugs:
        title, desc, body = enc_extract(os.path.join(encdir, f"{s}.html"))
        body = enc_rewrite(body, slugs)
        write(f"wood-encyclopedia/{s}/index.html",
              base(seo_title(title), desc, f"/wood-encyclopedia/{s}", body, body_class="cw-encbody",
                   show_crumbs=False,
                   crumbs=[("Home", "/"), ("Wood Encyclopedia", "/wood-encyclopedia/"),
                           (title.split("|")[0].split("—")[0].strip(), None)]))
    return len(slugs)+1

# ---------------- content pages (product + core, from clean snippets) ----------------
PAGE_META = json.load(open(os.path.join(ROOT, "content", "pages_meta.json"), encoding="utf-8"))
PAGE_SNIPPETS = {
    "commercial-plywood":"commercial-plywood.html","marine-plywood":"marine-plywood.html",
    "film-faced-shuttering-plywood":"film-faced-shuttering-plywood.html",
    "container-flooring-plywood":"container-flooring-plywood.html",
    "bwr-hardwood-plywood":"bwr-hardwood-plywood.html","chequered-anti-skid-plywood":"chequered-anti-skid-plywood.html",
    "block-board-flush-doors":"block-board-flush-doors.html","finger-joint-board":"finger-joint-board.html",
    "particle-board":"particle-board.html","plywood-boxes-crates":"plywood-boxes-crates.html",
    "plywood-pallets":"plywood-pallets.html","plywood-cable-drums":"plywood-cable-drums.html",
    "sawn-timber":"sawn-timber.html","faq":"faq.html","resources":"resources.html",
    "industries":"industries-LIVE-2026-06-11.html","privacy-policy":"privacy.html",
    "terms-and-conditions":"terms.html","llms":"llms.html",
}
def process_content(body):
    body = re.sub(r'<script\b[^>]*>.*?</script>', '', body, flags=re.S)   # drop any inline scripts
    body = re.sub(r'\son\w+="[^"]*"', '', body)                            # drop inline handlers
    return rewrite_links(prune_images(body))

def build_content_pages():
    sdir = os.path.join(ROOT, "content", "pages")
    n = 0
    for slug, fname in PAGE_SNIPPETS.items():
        fp = os.path.join(sdir, fname)
        if not os.path.exists(fp): continue
        meta = PAGE_META.get(slug, {})
        content = process_content(open(fp, encoding="utf-8").read())
        title = meta.get("title") or slug.replace("-", " ").title() + " | Cochin Wood Industries"
        desc  = meta.get("desc") or ""
        body = f'<main class="cw-page"><div class="cw-wrap">{content}</div></main>'
        pname = dict((s, n_) for s, n_, _ in PRODUCTS).get(slug)
        if pname:
            crumbs = [("Home", "/"), ("Products", "/products"), (pname, None)]
        else:
            crumbs = [("Home", "/"), (title.split("|")[0].strip(), None)]
        write(f"{slug}/index.html", base(title, desc, "/"+slug, body,
              body_class="cw-contentpage", crumbs=crumbs,
              extra_head=product_schema(slug) if pname else ""))
        n += 1
    return n

def build_about():
    sdir = os.path.join(ROOT, "content", "pages")
    parts = []
    for f in ("about-history.html", "about-operation.html"):
        fp = os.path.join(sdir, f)
        if os.path.exists(fp): parts.append(process_content(open(fp, encoding="utf-8").read()))
    if not parts: return 0
    meta = PAGE_META.get("about", {})
    body = f'<main class="cw-page"><div class="cw-wrap">{"".join(parts)}</div></main>'
    write("about/index.html", base(meta.get("title","About Cochin Wood Industries"),
          meta.get("desc",""), "/about", body, body_class="cw-contentpage",
          crumbs=[("Home", "/"), ("About", None)]))
    return 1

def _blog_content(body):
    body = re.sub(r'<script\b[^>]*>.*?</script>', '', body, flags=re.S)
    body = re.sub(r'\son\w+="[^"]*"', '', body)
    return rewrite_links(prune_images(body))

def build_blog():
    fp = os.path.join(ROOT, "content", "blog", "posts.json")
    if not os.path.exists(fp): return 0
    posts = json.load(open(fp, encoding="utf-8"))
    live = [p for p in posts if p.get("html")]
    n = 0
    for p in live:
        slug, title = p["slug"], (p.get("title") or slug)
        desc = p.get("desc", "")
        content = _blog_content(p["html"])
        short = esc(title.split('|')[0].strip())
        art = f'''<header class="cwg__hero"><div class="cwg__container">
  <h1 class="cwg__h1">{short}</h1>
  <p class="cwg__meta">Cochin Wood Industries</p>
</div></header>
<article class="cwg__body"><div class="cwg__container">{content}</div></article>
<section class="cwg__cta"><div class="cwg__wide cwg__cta-inner"><div><h2>Need a plywood quote?</h2><p>Tell us the grade, size and quantity — we'll price it within one business day.</p></div><a class="cwg__btn" href="{u('/contact')}">Request a quote</a></div></section>'''
        ld = ('<script type="application/ld+json">' + json.dumps({
                "@context": "https://schema.org", "@type": "BlogPosting",
                "headline": title.split("|")[0].strip(), "description": desc,
                "author": {"@id": LIVE + "/#organization"},
                "publisher": {"@id": LIVE + "/#organization"},
                "image": OG_IMAGE,
                "inLanguage": "en-IN",
                "isPartOf": {"@type": "Blog", "@id": LIVE + "/blogs"},
                "mainEntityOfPage": f"{LIVE}/blogs/post/{slug}"},
                separators=(",", ":")) + '</script>')
        write(f"blogs/post/{slug}/index.html",
              base(seo_title(title), desc, f"/blogs/post/{slug}", art, body_class="cw-encbody",
                   extra_head=ld, og_type="article",
                   crumbs=[("Home", "/"), ("Blog", "/blogs"), (title.split("|")[0].strip(), None)]))
        n += 1
    # blog index
    def card(p):
        t = (p.get("title") or p["slug"]).split("|")[0].strip()
        return f'<a href="{u("/blogs/post/"+p["slug"])}"><b>{esc(t)}</b><span>{esc((p.get("desc") or "")[:120])}</span></a>'
    cities = [p for p in live if p["slug"].startswith("plywood-supply")]
    articles = [p for p in live if not p["slug"].startswith("plywood-supply")]
    body = f'''<section class="cw-sec"><div class="cw-wrap">
  <p class="cw-hero__ey" style="color:var(--cw-green-600)">Blog</p>
  <h1 class="cw-sec__h" style="font-size:clamp(1.9rem,4vw,2.8rem)">Plywood guides, specs &amp; supply</h1>
  <p class="cw-sec__lead">Field notes on grades, standards, export packing and city-by-city supply from the Cochin Wood desk.</p>
  <div class="cw-blogtools">
    <label for="cw-blogsearch">Search {len(live)} posts</label>
    <input id="cw-blogsearch" type="search" autocomplete="off" placeholder="e.g. marine, ISPM-15, Kochi, IS 710">
    <p class="cw-blogcount" id="cw-blogcount" role="status" aria-live="polite"></p>
  </div>
  <div class="cw-blogindex">
    <h2>Guides &amp; articles ({len(articles)})</h2>
    <div class="cw-bloglist">{"".join(card(p) for p in articles)}</div>
    <h2>Plywood supply by city ({len(cities)})</h2>
    <div class="cw-bloglist">{"".join(card(p) for p in cities)}</div>
    <p id="cw-blogempty" hidden>No posts match that search. <a href="{u('/contact')}">Ask us directly</a> — we'll answer it.</p>
  </div>
</div></section>'''
    write("blogs/index.html", base("Blog — Plywood Guides, Specs & Supply | Cochin Wood",
          "Plywood guides, standards, export-packing notes and city-by-city supply from Cochin Wood Industries.",
          "/blogs", body, crumbs=[("Home", "/"), ("Blog", None)]))
    return n

def build_sitemap():
    urls = []
    for r, _, fs in os.walk(DIST):
        for f in fs:
            if f != "index.html": continue
            rel = os.path.relpath(os.path.join(r, f), DIST).replace(os.sep, "/")
            path = "/" if rel == "index.html" else "/" + rel[:-len("index.html")].rstrip("/")
            urls.append(LIVE + path)
    urls = sorted(set(urls))
    today = datetime.date.today().isoformat()
    items = "\n".join(f"  <url><loc>{u_}</loc><lastmod>{today}</lastmod></url>" for u_ in urls)
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + items + '\n</urlset>\n')
    return len(urls)

def copy_referenced_files():
    copied = 0
    for ref in sorted(_files_used):
        src = resolve_file(ref)
        if not src: continue
        dst = os.path.join(DIST, urllib.parse.unquote(ref.lstrip("/")))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst); copied += 1
    return copied

# ---------------- assets + meta ----------------
# One request instead of five; order preserved so cascade behaviour is unchanged.
CSS_BUNDLE = ["fonts.css", "site.css", "guide.css", "wood-enc.css", "shell.css", "components.css"]

def _css_fix_urls(css, name):
    """Resolve /files/... backgrounds; neutralise the ones with no source file."""
    def sub(m):
        ref = "/" + m.group(2).lstrip("/")
        if resolve_file(ref):
            _files_used.add(ref)
            return f"url('{u(ref)}')"
        _files_missing.add(f"{ref}  (css: {name})")
        return "none"
    return re.sub(r"url\((['\"]?)(/files/[^)'\"]+)\1\)", sub, css)

def build_css_bundle():
    src = os.path.join(ROOT, "assets")
    parts = []
    for name in CSS_BUNDLE:
        fp = os.path.join(src, name)
        if not os.path.exists(fp):
            warn(f"css bundle: missing {name}"); continue
        parts.append(f"/* --- {name} --- */\n" + _css_fix_urls(open(fp, encoding="utf-8").read(), name))
    write("assets/bundle.css", "\n".join(parts))

def assets_and_meta():
    src = os.path.join(ROOT, "assets")
    dst = os.path.join(DIST, "assets")
    if os.path.exists(dst): shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("photos"))
    build_css_bundle()
    open(os.path.join(DIST, ".nojekyll"), "w").close()
    # Cloudflare Pages headers (ignored by GitHub Pages, honoured by CF Pages)
    write("_headers",
        "/assets/*\n"
        "  Cache-Control: public, max-age=31536000, immutable\n"
        "/files/*\n"
        "  Cache-Control: public, max-age=31536000, immutable\n"
        "/*\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  X-Frame-Options: SAMEORIGIN\n"
        "  Strict-Transport-Security: max-age=31536000; includeSubDomains\n"
        "  Permissions-Policy: geolocation=(), camera=(), microphone=(), interest-cohort=()\n"
        "  Cross-Origin-Opener-Policy: same-origin\n")
    # 301s for the legacy Zoho slugs so inbound links and old SERP entries survive
    lines = [f"{old}  {new}  301" for old, new in sorted(LEGACY_REDIRECTS.items())]
    lines.append("/index.html  /  301")
    write("_redirects", "\n".join(lines) + "\n")
    write("404.html", base("Page not found | Cochin Wood Industries",
        "That page has moved or doesn't exist. Browse the plywood catalogue or ask us for a quote.", "/404",
        f'''<section class="cw-sec"><div class="cw-wrap" style="text-align:center;padding:60px 0">
  <h1 class="cw-sec__h">Page not found</h1>
  <p class="cw-sec__lead" style="margin:0 auto 24px">That page has moved or doesn't exist. Try one of these:</p>
  <p><a class="cw-btn cw-btn--p" href="{u('/')}">Back to home</a> <a class="cw-btn cw-btn--g" href="{u('/products')}">Plywood catalogue</a> <a class="cw-btn cw-btn--g" href="{u('/blogs')}">Blog</a> <a class="cw-btn cw-btn--g" href="{u('/contact')}">Request a quote</a></p>
</div></section>'''))
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {LIVE}/sitemap.xml\n")

def main():
    if os.path.exists(DIST): shutil.rmtree(DIST)
    os.makedirs(DIST)
    home(); products(); contact()
    n = encyclopedia()
    p = build_content_pages()
    p += build_about()
    b = build_blog()
    assets_and_meta()            # also discovers /files/ refs inside the CSS
    f = copy_referenced_files()  # so this must run after it
    for ref in sorted(_files_missing):
        warn(f"photo missing, reference removed: {ref}")
    sm = build_sitemap()
    cnt = sum(len(fs) for _,_,fs in os.walk(DIST))
    print(f"BUILD OK  base='{BASE or '(root)'}'  {p} content pages + {n} encyclopedia + {b} blog posts + {f} images  sitemap:{sm}  files: {cnt}")
    if WARNINGS:
        print(f"\n{len(WARNINGS)} WARNING(S):")
        for w in WARNINGS: print("  ! " + w)
        if _files_missing:
            print(f"\n  Drop the {len(_files_missing)} missing photo(s) into assets/photos/<same path>")
            print(f"  (or point MIRROR_DIR at a checkout that has them) and rebuild.")
        if STRICT:
            raise SystemExit("STRICT=1: failing the build on warnings")

if __name__ == "__main__":
    main()
