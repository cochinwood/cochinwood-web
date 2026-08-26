#!/usr/bin/env python3
"""
Cochin Wood Industries — clean static-site builder (no external deps).

Source in this repo -> renders to dist/. Set SITE_BASE to deploy under a
subpath (e.g. /cochinwood-web for GitHub project Pages); leave empty for the
domain root (Cloudflare Pages at cochinwood.in).

    python build.py          # builds to dist/ at root ("")
    SITE_BASE=/cochinwood-web python build.py
"""
import os, re, json, shutil, html, urllib.parse, datetime, struct, hashlib

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

_files_used, _files_missing = {}, set()      # {public ref: source path on disk}

_MAGIC = [(b"\x89PNG\r\n\x1a\n", ".png"), (b"\xff\xd8\xff", ".jpg"), (b"GIF8", ".gif")]

def true_ext(path):
    """The extension the bytes actually deserve. Part of the Zoho asset set was
    converted to WebP but kept a .jpg name; browsers refuse to decode those, so
    the build renames on the way out rather than shipping an undecodable image."""
    with open(path, "rb") as fh: head = fh.read(16)
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP": return ".webp"
    for magic, ext in _MAGIC:
        if head.startswith(magic): return ext
    return os.path.splitext(path)[1].lower()

def register_file(ref, path):
    """Record a resolved asset and return the public ref it will be served at."""
    stem, ext = os.path.splitext(ref)
    real = true_ext(path)
    if real and real != ext.lower():
        if ext.lower() in (".jpeg",) and real == ".jpg":
            real = ext                                  # .jpeg/.jpg are the same thing
        else:
            warn(f"{ref} is really {real[1:].upper()} — serving it as {stem}{real}")
            ref = stem + real
    _files_used[ref] = path
    return ref

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

# Catalogue pages whose hero slot held a Zoho stock placeholder and for which we
# have real product photography. Anything not listed keeps no hero image.
PRODUCT_HERO = {
    "block-board-flush-doors": "/files/Product/block-board.jpg",
    "plywood-cable-drums":     "/files/Product/cable-drums.jpg",
    "plywood-boxes-crates":    "/files/Product/crates.jpg",
    "finger-joint-board":      "/files/Product/finger-joint.jpg",
    "plywood-pallets":         "/files/Product/pallets.jpg",
    "particle-board":          "/files/Product/particle-board.jpg",
    "sawn-timber":             "/files/Product/specialty-timbers.jpg",
}

def image_size(path):
    """(width, height) for PNG/JPEG/WebP, or None. Used to correct the width and
    height attributes so the browser reserves the right box and nothing shifts."""
    try:
        with open(path, "rb") as fh: d = fh.read(256 * 1024)
    except OSError:
        return None
    if d[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", d[16:24])
    if d[:4] == b"RIFF" and d[8:12] == b"WEBP":
        if d[12:16] == b"VP8 ":
            return struct.unpack("<HH", d[26:30])
        if d[12:16] == b"VP8L":
            b = struct.unpack("<I", d[21:25])[0]
            return ((b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1)
        if d[12:16] == b"VP8X":
            w = int.from_bytes(d[24:27], "little") + 1
            h = int.from_bytes(d[27:30], "little") + 1
            return (w, h)
        return None
    if d[:2] == b"\xff\xd8":                      # JPEG: walk the segment chain
        i = 2
        while i + 9 < len(d):
            if d[i] != 0xFF: i += 1; continue
            m = d[i + 1]
            if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7: i += 2; continue
            if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", d[i + 5:i + 9])
                return (w, h)
            seg = struct.unpack(">H", d[i + 2:i + 4])[0]
            if seg < 2: break
            i += 2 + seg
    return None

def _set_dims(tag, path):
    """Replace width/height on an <img> with the file's true pixel size."""
    size = image_size(path)
    if not size: return tag
    w, h = size
    tag = re.sub(r'\s(width|height)="[^"]*"', '', tag)
    return tag[:-1].rstrip() + f' width="{w}" height="{h}"' + ('/>' if tag.endswith('/>') else '>')

# Wrappers that exist only to hold one photo. Once a dead image is removed the
# wrapper is empty, and the CSS would leave a sized blank panel — so drop it too.
_EMPTY_WRAPPERS = [
    re.compile(r'<figure class="cwop-card">\s*</figure>', re.I),
    re.compile(r'<div class="cwp__hero-img">\s*</div>', re.I),
    re.compile(r'<div class="cw__hero-img">\s*</div>', re.I),
]

def _fix_img(tag, slug=None):
    """Return the <img> with a real source and true dimensions, or "" to drop it.

    A Zoho stock placeholder is swapped for genuine product photography where we
    have it, and dropped otherwise — it must never reach the site either way."""
    m = re.search(r'src="([^"]+)"', tag)
    if not m: return tag
    s = m.group(1)
    if "zohocdn.com" in s:
        repl = PRODUCT_HERO.get(slug)
        if not repl: return ""
        tag = tag.replace(s, repl)
        s = repl
    if s.startswith("/files/"):
        path = resolve_file(s)
        if not path:
            _files_missing.add(s)
            return ""
        pub = register_file(s, path)
        if pub != s: tag = tag.replace(s, pub)
        return _set_dims(tag, path)
    return tag

def prune_images(body, slug=None):
    """Resolve every image, then drop any wrapper left empty by a removal.

    Images are fixed in a single pass so a rewritten src is never re-examined."""
    body = re.sub(r'<img\b[^>]*>', lambda m: _fix_img(m.group(0), slug), body, flags=re.I)
    for pat in _EMPTY_WRAPPERS:
        body = pat.sub("", body)
    return body

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
  <a class="cw-hd__brand" href="{u('/')}"><img src="{u('/assets/icons/logo-80.png')}" alt="Cochin Wood Industries logo" width="40" height="40" decoding="async"><span style="display:block"><b>Cochin Wood Industries</b><span>Plywood Manufacturer &middot; Kochi</span></span></a>
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
    <div><h2 class="cw-ft__h">Products</h2>{prod}</div>
    <div><h2 class="cw-ft__h">Explore</h2><a href="{u('/products')}">All products</a><a href="{u('/wood-encyclopedia/')}">Wood Encyclopedia</a><a href="{u('/resources')}">Resources</a><a href="{u('/industries')}">Industries</a><a href="{u('/about')}">About</a><a href="{u('/faq')}">FAQ</a></div>
    <div><h2 class="cw-ft__h">Contact</h2><a href="tel:{CONTACT['phone_href']}">{CONTACT['phone_disp']}</a><a href="mailto:{CONTACT['email']}">{CONTACT['email']}</a><a href="https://maps.google.com/?q=Kuruppampady+Kerala" target="_blank" rel="noopener">{CONTACT['addr']}</a></div>
  </div>
  <div class="cw-ft__bar"><span>&copy; 2026 Cochin Wood Industries Pvt Ltd. Group established 1986.</span>
  <span><a href="{u('/privacy-policy')}" style="display:inline">Privacy</a> &middot; <a href="{u('/terms-and-conditions')}" style="display:inline">Terms</a></span></div>
</div></footer>'''

OG_IMAGE = LIVE + "/assets/og/cwi-og-share-1200x630.png"   # 1200x630 share card

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
           + ' <span class="cw-crumb__sep" aria-hidden="true">&rsaquo;</span> '.join(parts) + '</div></nav>')
    ld = ('<script type="application/ld+json">'
          + json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList",
                        "itemListElement": items}, separators=(",", ":")) + '</script>')
    return nav, ld

def esc(s):
    """Titles/descriptions arrive from three sources with inconsistent escaping
    (pages_meta.json, posts.json, and the encyclopedia <title> tags). Decode
    first so a pre-escaped '&amp;' does not ship as a literal '&amp;amp;'."""
    return html.escape(html.unescape(s or ""))

TITLE_MAX = 62          # roughly where Google truncates a result title

# Headlines the automatic rules cannot shorten without losing the point. Written
# for the search snippet only — each post keeps its full headline as the H1.
TITLE_OVERRIDES = {
    "Birch vs Okoume vs Gurjan: Pick the Right Face Veneer for Export Packing":
        "Birch vs Okoume vs Gurjan: Export Packing Veneers",
    "FOB Cochin vs FCA Mundra: Which Incoterm to Quote a GCC Plywood Buyer":
        "FOB Cochin vs FCA Mundra: Which Incoterm for GCC",
    "Plywood Cable Drum Flanges: IS 10418 Spec, Sizing & Sourcing Guide":
        "Plywood Cable Drum Flanges: IS 10418 Spec & Sizing",
    "Plywood Boxes for Machinery: Triple-Wall vs Reinforced Single-Wall":
        "Plywood Boxes: Triple-Wall vs Reinforced Single-Wall",
    "Okoume Plywood: Calibrated Export-Grade Panels, Built to Your Spec":
        "Okoume Plywood: Calibrated Export-Grade Panels",
    "ISPM-15 HT Stamp Validity & Re-Stamping Rules for Indian Exporters":
        "ISPM-15 HT Stamp Validity & Re-Stamping Rules",
    "Plywood Crate Sizing: Break-Bulk vs Container - Which Spec Wins?":
        "Plywood Crate Sizing: Break-Bulk vs Container",
}

def seo_title(title):
    """Fit a title into the search snippet without losing the words that sell it.

    Applied in order, stopping as soon as it fits: shorten or drop the brand
    suffix; on the species pages drop the redundant 'Wood' and 'Density'; drop a
    trailing parenthetical; drop the subtitle after the last colon. The visible
    H1 is untouched — this only governs the <title> tag."""
    head = html.unescape(title).split("|")[0].strip()
    head = TITLE_OVERRIDES.get(head, head)

    def fit(h):
        for suffix in (" | Cochin Wood Industries", " | Cochin Wood", ""):
            if len(h + suffix) <= TITLE_MAX: return h + suffix
        return None

    out = fit(head)
    if out: return out

    # "Gurjan / Keruing Wood (Dipterocarpus spp.): Properties, Density & Uses"
    m = re.match(r'^(.*?) Wood (\(.+?\)): Properties, Density & Uses$', head)
    if m:
        for cand in (f"{m.group(1)} {m.group(2)}: Properties & Uses",
                     f"{m.group(1)}: Properties & Uses"):
            out = fit(cand)
            if out: return out

    trimmed = re.sub(r'\s*\([^()]*\)\s*$', '', head)          # trailing parenthetical
    if trimmed != head:
        head = TITLE_OVERRIDES.get(trimmed, trimmed)          # an override may fit the shorter form
        out = fit(head)
        if out: return out

    if ": " in head:                                           # trailing subtitle
        stem = head.rsplit(": ", 1)[0].strip()
        if len(stem) >= 28:
            out = fit(stem)
            if out: return out

    warn(f"title still {len(head)} chars, no safe trim: {head}")
    return head

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
    page_title = seo_title(title)      # <title> is trimmed; og/twitter keep the full headline
    crumb_nav, crumb_ld = breadcrumbs(crumbs)
    # Several imported pages already render their own trail (cwp__crumb, cwg__crumb…);
    # drop our duplicate bar in that case.
    if not show_crumbs or re.search(r'class="[^"]*\b\w*__crumb\b', body):
        crumb_nav = ""
    # …and the encyclopedia pages ship their own BreadcrumbList too. Two of them on
    # one page is conflicting structured data, so emit ours only when there is none.
    if '"BreadcrumbList"' in body:
        crumb_ld = ""
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
<title>{esc(page_title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/png" sizes="32x32" href="{u('/assets/icons/favicon-32.png')}">
<link rel="icon" type="image/png" sizes="16x16" href="{u('/assets/icons/favicon-16.png')}">
<link rel="apple-touch-icon" href="{u('/assets/icons/apple-touch-icon.png')}">
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
<link rel="stylesheet" href="{u('/assets/' + ASSETS['bundle.css'])}">
{extra_head}</head>
<body class="{body_class}">
<a class="cw-skip" href="#main">Skip to content</a>
{header(path)}
{crumb_nav}
{body}
{footer()}
<a class="cw-wa" href="https://wa.me/{CONTACT['wa']}" target="_blank" rel="noopener" aria-label="Chat with us on WhatsApp"><svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" focusable="false"><path fill="currentColor" d="M.06 24l1.68-6.16A11.87 11.87 0 010 11.9C0 5.33 5.36 0 11.95 0a11.9 11.9 0 018.42 3.48 11.75 11.75 0 013.49 8.37c0 6.56-5.36 11.9-11.96 11.9-2 0-3.96-.5-5.7-1.45L.06 24zm6.6-3.8c1.68.99 3.28 1.58 5.4 1.58 5.45 0 9.9-4.42 9.9-9.87a9.8 9.8 0 00-2.9-6.99 9.9 9.9 0 00-7-2.9C6.6 2.02 2.15 6.44 2.15 11.9c0 2.2.62 3.85 1.67 5.57l-.99 3.6 3.83-.87zm11.6-5.5c-.08-.13-.28-.2-.58-.35-.3-.15-1.76-.86-2.03-.96-.27-.1-.47-.15-.67.15-.2.3-.77.96-.94 1.16-.17.2-.35.22-.65.07-.3-.15-1.25-.46-2.38-1.47-.88-.78-1.47-1.75-1.65-2.05-.17-.3-.02-.46.13-.6.14-.14.3-.36.45-.53.15-.18.2-.3.3-.5.1-.2.05-.38-.02-.53-.08-.15-.67-1.6-.92-2.2-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.8.37-.27.3-1.04 1.02-1.04 2.48s1.07 2.88 1.22 3.08c.15.2 2.1 3.2 5.08 4.49.71.3 1.26.49 1.7.63.71.22 1.36.19 1.87.12.57-.09 1.76-.72 2-1.41.25-.7.25-1.29.18-1.41z"/></svg></a>
<button class="cw-top" type="button" aria-label="Back to top" hidden>&uarr;</button>
<script src="{u('/assets/' + ASSETS['site.js'])}" defer></script>
</body>
</html>'''

_page_source = {}      # output path -> source file it was generated from

def write(path, content, src=None):
    fp = os.path.join(DIST, path)
    os.makedirs(os.path.dirname(fp) or DIST, exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f: f.write(content)
    _page_source[path] = src or "build.py"

_gitdate_cache = {}
def git_date(relpath):
    """Date of the last commit touching a source file, for a truthful <lastmod>.

    A sitemap that stamps every URL with today's build date tells crawlers the
    whole site changed on every deploy, which is not information."""
    if relpath not in _gitdate_cache:
        out = ""
        try:
            import subprocess
            out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", relpath],
                                 cwd=ROOT, capture_output=True, text=True, timeout=15).stdout.strip()
        except Exception:
            pass
        _gitdate_cache[relpath] = out or datetime.date.today().isoformat()
    return _gitdate_cache[relpath]

# ---------------- HOME ----------------
def home():
    cards = "".join(
        f'<a class="cw-card" href="{u("/"+s)}"><h2>{n}</h2><p>{d}</p><span class="cw-card__tag">View &rarr;</span></a>'
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
        f'<a class="cw-card" href="{u("/"+s)}"><h2>{n}</h2><p>{d}</p><span class="cw-card__tag">View &rarr;</span></a>'
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
    <div><h2>WhatsApp / Phone</h2><p><a href="tel:{CONTACT['phone_href']}">{CONTACT['phone_disp']}</a></p></div>
    <div><h2>Email</h2><p><a href="mailto:{CONTACT['email']}">{CONTACT['email']}</a></p></div>
    <div><h2>Works &amp; office</h2><p>{CONTACT['addr']}</p></div>
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
    write("wood-encyclopedia/index.html", src=os.path.join("content","encyclopedia","_hub.html"), content=base(title, desc, "/wood-encyclopedia", body,
          body_class="cw-encbody", crumbs=[("Home", "/"), ("Wood Encyclopedia", None)]))
    # species — the imported pages carry their own visible crumb, so emit schema only
    for s in slugs:
        title, desc, body = enc_extract(os.path.join(encdir, f"{s}.html"))
        body = enc_rewrite(body, slugs)
        write(f"wood-encyclopedia/{s}/index.html", src=os.path.join("content","encyclopedia",f"{s}.html"), content=
              base(title, desc, f"/wood-encyclopedia/{s}", body, body_class="cw-encbody",
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
def process_content(body, slug=None):
    # a couple of imported snippets carry their own <main>; the page shell provides
    # the landmark, so demote theirs rather than ship two
    body = re.sub(r'<main\b([^>]*)>', r'<section\1>', body)
    body = body.replace('</main>', '</section>')
    body = re.sub(r'<script\b[^>]*>.*?</script>', '', body, flags=re.S)   # drop any inline scripts
    body = re.sub(r'\son\w+="[^"]*"', '', body)                            # drop inline handlers
    return rewrite_links(prune_images(body, slug))

def build_content_pages():
    sdir = os.path.join(ROOT, "content", "pages")
    n = 0
    for slug, fname in PAGE_SNIPPETS.items():
        fp = os.path.join(sdir, fname)
        if not os.path.exists(fp): continue
        meta = PAGE_META.get(slug, {})
        content = process_content(open(fp, encoding="utf-8").read(), slug)
        title = meta.get("title") or slug.replace("-", " ").title() + " | Cochin Wood Industries"
        desc  = meta.get("desc") or ""
        body = f'<main class="cw-page"><div class="cw-wrap">{content}</div></main>'
        pname = dict((s, n_) for s, n_, _ in PRODUCTS).get(slug)
        if pname:
            crumbs = [("Home", "/"), ("Products", "/products"), (pname, None)]
        else:
            crumbs = [("Home", "/"), (title.split("|")[0].strip(), None)]
        write(f"{slug}/index.html", src=os.path.join("content","pages",fname), content=base(title, desc, "/"+slug, body,
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
    # The page opens on the "Our history" section label, so it carried no <h1> at
    # all — the only page on the site without one. The heading is hidden rather
    # than drawn so the layout is untouched.
    h1 = '<h1 class="cw-sr-only">About Cochin Wood Industries</h1>'
    body = f'<main class="cw-page"><div class="cw-wrap">{h1}{"".join(parts)}</div></main>'
    write("about/index.html", src=os.path.join("content","pages","about-operation.html"), content=base(meta.get("title","About Cochin Wood Industries"),
          meta.get("desc",""), "/about", body, body_class="cw-contentpage",
          crumbs=[("Home", "/"), ("About", None)]))
    return 1

def _blog_content(body):
    body = re.sub(r'<script\b[^>]*>.*?</script>', '', body, flags=re.S)
    body = re.sub(r'\son\w+="[^"]*"', '', body)
    return rewrite_links(prune_images(body))

BLOG_SRC = os.path.join("content", "blog", "posts.json")

def build_blog():
    fp = os.path.join(ROOT, BLOG_SRC)
    if not os.path.exists(fp): return 0
    posts = json.load(open(fp, encoding="utf-8"))
    live = [p for p in posts if p.get("html")]
    n, undated = 0, []
    for p in live:
        slug, title = p["slug"], (p.get("title") or slug)
        desc = p.get("desc", "")
        content = _blog_content(p["html"])
        short = esc(title.split('|')[0].strip())
        # "date": "YYYY-MM-DD" in posts.json. These are NOT invented: every post in the
        # cf-live mirror carries a real "datePublished" inside its BlogPosting JSON-LD,
        # and 155 of the 156 entries here were back-filled from it on 2026-08-26. Keeping
        # the same values matters at cutover — 155 posts changing datePublished on the day
        # we flip would read to Google as mass re-publication. The 156th, okoume-plywood,
        # exists only in this build and has no mirror page to take a date from.
        date = (p.get("date") or "").strip()
        if date and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
            warn(f"post {slug}: ignoring unparseable date {date!r}"); date = ""
        if not date: undated.append(slug)
        if date:
            _d = datetime.date.fromisoformat(date)
            # The day is formatted by hand because "%-d" is a glibc extension: it renders
            # fine in CI on Linux and raises ValueError on Windows, where this build also
            # gets run by hand. While no post had a date this branch never executed, so
            # the platform difference stayed invisible until the back-fill above.
            byline = (f'Cochin Wood Industries &middot; <time datetime="{date}">'
                      f'{_d.day} {_d.strftime("%B %Y")}</time>')
        else:
            byline = "Cochin Wood Industries"
        art = f'''<header class="cwg__hero"><div class="cwg__container">
  <h1 class="cwg__h1">{short}</h1>
  <p class="cwg__meta">{byline}</p>
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
                "mainEntityOfPage": f"{LIVE}/blogs/post/{slug}",
                **({"datePublished": date, "dateModified": date} if date else {})},
                separators=(",", ":")) + '</script>')
        write(f"blogs/post/{slug}/index.html", src=BLOG_SRC, content=
              base(title, desc, f"/blogs/post/{slug}", art, body_class="cw-encbody",
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
    if undated:
        warn(f"{len(undated)} of {len(live)} posts have no \"date\" — BlogPosting omits "
             f"datePublished, which Google wants for article rich results. Add "
             f"\"date\": \"YYYY-MM-DD\" to entries in {BLOG_SRC} to fill it in.")
    write("blogs/index.html", src=BLOG_SRC, content=base("Blog — Plywood Guides, Specs & Supply | Cochin Wood",
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
    def lastmod(url):
        rel = url[len(LIVE):].strip("/")
        return git_date(_page_source.get((rel + "/index.html").lstrip("/") or "index.html", "build.py"))
    items = "\n".join(f"  <url><loc>{u_}</loc><lastmod>{lastmod(u_)}</lastmod></url>" for u_ in urls)
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + items + '\n</urlset>\n')
    return len(urls)

def copy_referenced_files():
    copied = 0
    for ref, src in sorted(_files_used.items()):
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
        path = resolve_file(ref)
        if path:
            return f"url('{u(register_file(ref, path))}')"
        _files_missing.add(f"{ref}  (css: {name})")
        return "none"
    return re.sub(r"url\((['\"]?)(/files/[^)'\"]+)\1\)", sub, css)

_bundle_css = None
def css_bundle_content():
    """Concatenated CSS bundle. Memoised: the hash is needed before pages render,
    and _css_fix_urls() must only record its /files/ references once."""
    global _bundle_css
    if _bundle_css is None:
        src = os.path.join(ROOT, "assets")
        parts = []
        for name in CSS_BUNDLE:
            fp = os.path.join(src, name)
            if not os.path.exists(fp):
                warn(f"css bundle: missing {name}"); continue
            parts.append(f"/* --- {name} --- */\n" + _css_fix_urls(open(fp, encoding="utf-8").read(), name))
        _bundle_css = "\n".join(parts)
    return _bundle_css

# /assets/* is served immutable for a year, so the two files that actually change
# between deploys carry a content hash in their name. Without it a returning
# visitor keeps the old CSS/JS until the cache expires. Fonts already ship with
# hashed names; the logo and icons are versioned by hand when they change.
ASSETS = {"bundle.css": "bundle.css", "site.js": "site.js"}

def _digest(data):
    if isinstance(data, str): data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:8]

def fingerprint_assets():
    ASSETS["bundle.css"] = f"bundle.{_digest(css_bundle_content())}.css"
    jp = os.path.join(ROOT, "assets", "site.js")
    if os.path.exists(jp):
        ASSETS["site.js"] = f"site.{_digest(open(jp, 'rb').read())}.js"

def build_css_bundle():
    write("assets/" + ASSETS["bundle.css"], css_bundle_content())

def assets_and_meta():
    src = os.path.join(ROOT, "assets")
    dst = os.path.join(DIST, "assets")
    if os.path.exists(dst): shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("photos"))
    # publish site.js under its fingerprinted name so the immutable header is safe
    if ASSETS["site.js"] != "site.js":
        plain = os.path.join(dst, "site.js")
        if os.path.exists(plain):
            os.replace(plain, os.path.join(dst, ASSETS["site.js"]))
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
    fingerprint_assets()         # hashes must exist before any page references them
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
