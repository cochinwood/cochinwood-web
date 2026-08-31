#!/usr/bin/env python3
"""
Cochin Wood Industries — clean static-site builder (no external deps).

Source in this repo -> renders to dist/. Set SITE_BASE to deploy under a
subpath (e.g. /cochinwood-web for GitHub project Pages); leave empty for the
domain root (Cloudflare Pages at cochinwood.in).

    python build.py          # builds to dist/ at root ("")
    SITE_BASE=/cochinwood-web python build.py
"""
import os, re, json, shutil, html, urllib.parse, datetime, struct, hashlib, sys

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
    # NOTE: "/okoume-plywood" -> "/blogs/post/okoume-plywood" was removed. /okoume-plywood
    # is a live, indexed commercial page; the blog post it pointed at exists only in this
    # build and has never been live. The redirect both hid the ported page and rewrote all
    # 14 in-content links away from it. Restore this line only if the owner decides that
    # URL really should move.
    "/packing-grade-plywood-spec-sheet":       "/blogs/post/packing-grade-plywood-spec-sheet",
}

# ---------------- the wood section ----------------
# The live site serves this section at /woods-we-use, and cf-live's hand-written
# _redirects already 301s /wood-encyclopedia and /wood-encyclopedia/* there. So
# the URL stays /woods-we-use and only the visible LABEL reads "Wood
# Encyclopedia" — the build does not move a URL that is already earning.
WOOD_PATH  = "/woods-we-use"          # the emitted path — do not change lightly
WOOD_LABEL = "Wood Encyclopedia"      # what a visitor reads in nav, crumbs, titles

ENC_DIR  = os.path.join(ROOT, "content", "encyclopedia")
HUB_SRC  = os.path.join(ENC_DIR, "_hub.html")
WAVE3_DIR = os.path.join(ROOT, "content", "encyclopedia-wave3")

def _load_manifest(path):
    if not os.path.exists(path):
        warn(f"species manifest missing: {os.path.relpath(path, ROOT)}"); return []
    return json.load(open(path, encoding="utf-8"))

def _species_manifest():
    """[(file stem, live /blogs/post/ slug, manifest entry, content subdir)] for
    every species, read off disk rather than typed out here -- a new species is
    wired in by dropping its file in and listing it, nothing else.

    Wave 1/2 (content/encyclopedia/<f>.html) are whole HTML pages. Their live
    slug comes from the hub's data-slug attributes, which cover all twenty;
    posts.json lists only fifteen and each page's own <link rel=canonical> is
    wrong for semul, so neither of those can be the source.

    Wave 3 (content/encyclopedia-wave3/<f>.body.html) are body fragments whose
    title and description live in posts3.json."""
    out, seen = [], set()
    meta = {e["file"]: e for e in _load_manifest(os.path.join(ENC_DIR, "posts.json"))}
    hub  = open(HUB_SRC, encoding="utf-8").read() if os.path.exists(HUB_SRC) else ""
    for f, slug in re.findall(
            r'<a class="cwe__card" href="([^"/]+)\.html" data-slug="/blogs/post/([^"]+)"', hub):
        if not os.path.exists(os.path.join(ENC_DIR, f + ".html")):
            warn(f"hub links {f}.html but content/encyclopedia/{f}.html does not exist")
            continue
        out.append((f, slug, meta.get(f, {}), "encyclopedia")); seen.add(f)
    for fp in sorted(os.listdir(ENC_DIR) if os.path.isdir(ENC_DIR) else []):
        f = fp[:-5]
        if fp.endswith(".html") and not fp.startswith("_") and f not in seen:
            warn(f"content/encyclopedia/{fp} is not on the hub -- it would build unlinked")
            out.append((f, "", meta.get(f, {}), "encyclopedia"))
    for e in _load_manifest(os.path.join(WAVE3_DIR, "posts3.json")):
        if os.path.exists(os.path.join(WAVE3_DIR, e["file"] + ".body.html")):
            out.append((e["file"], e.get("slug", ""), e, "encyclopedia-wave3"))
        else:
            warn(f"posts3.json lists {e['file']} but {e['file']}.body.html is missing")
    return out

SPECIES       = _species_manifest()
SPECIES_SLUGS = [f for f, _s, _e, _d in SPECIES]

# All 28 species are live today at /blogs/post/wood-<slug>. Moving them under the
# hub means every one of those URLs needs retargeting in content and a 301 on the
# way out; three were listed by hand, which left 25 stale cross-links shipping.
LEGACY_REDIRECTS.update({f"/blogs/post/{slug}": f"{WOOD_PATH}/{f}"
                         for f, slug, _e, _d in SPECIES if slug})

# OWNER-DECIDED, 31 Aug 2026. Neither legacy history nor a ported cf-live rule: the five regional
# and buyer-guide category pages are live and indexed today, this build does not emit them, and
# Edwin chose redirect-to-/blogs over rebuilding them -- nothing 404s, and they can be rebuilt
# later without undoing anything. The pagination wildcard replaces the one cf-live rule whose
# target was never built (see its settled entry in DROPPED_FROM_LIVE). Routed through
# LEGACY_REDIRECTS on purpose: that also rewrites in-content links, and a page's link and the
# slug's 301 must lead to the same place.
LEGACY_REDIRECTS.update({
    "/blogs/buyer-guides": "/blogs",
    "/blogs/buyer-guides/page/*": "/blogs",
    "/blogs/north-india": "/blogs",
    "/blogs/south-india": "/blogs",
    "/blogs/west-india": "/blogs",
    "/blogs/central-east-india": "/blogs",
})

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

# cf-live carries "Export" in the primary nav (between Industries and Resources)
# and in the footer's Company column. Both are kept: /export and its eight lanes
# are the commercial core, and without a nav entry they would be reachable only
# from the handful of commercial pages that happen to cross-link them.
NAV = [("Products", "/products", False), ("Industries", "/industries", False),
       ("Export", "/export", False), (WOOD_LABEL, WOOD_PATH, False),
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
    <div><h2 class="cw-ft__h">Explore</h2><a href="{u('/products')}">All products</a><a href="{u(WOOD_PATH)}">{WOOD_LABEL}</a><a href="{u('/resources')}">Resources</a><a href="{u('/industries')}">Industries</a><a href="{u('/export')}">Export</a><a href="{u('/about')}">About</a><a href="{u('/faq')}">FAQ</a></div>
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
  <a class="cw-btn cw-btn--p" href="{u(WOOD_PATH)}" style="background:var(--cw-green-700)">Open the encyclopedia &rarr;</a>
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
# Served at WOOD_PATH (/woods-we-use); labelled "Wood Encyclopedia" throughout.
def enc_extract(src):
    t = open(src, encoding="utf-8").read()
    title = re.search(r"<title>(.*?)</title>", t, re.S).group(1).strip()
    desc  = re.search(r'<meta name="description" content="(.*?)">', t, re.S)
    desc  = desc.group(1).strip() if desc else ""
    body  = t.split("</head>",1)[1]
    body  = body.split("<body>",1)[1].rsplit("</body>",1)[0]
    return title, desc, body

_ENC_URLS = None
def enc_url_map():
    """Old URL -> new URL for every hard-coded reference inside the imported
    pages. These live in JSON-LD (`mainEntityOfPage`, BreadcrumbList `item`) and
    in the hub's `data-slug` attributes -- none of which is an href or a src, so
    rewrite_links() never sees them and they were shipping stale."""
    global _ENC_URLS
    if _ENC_URLS is None:
        m = {"/wood-encyclopedia": WOOD_PATH}
        for f, slug, _e, _d in SPECIES:
            if slug: m["/blogs/post/" + slug] = f"{WOOD_PATH}/{f}"
            m["/wood-encyclopedia/" + f] = f"{WOOD_PATH}/{f}"   # deep links in the copy
        _ENC_URLS = sorted(m.items(), key=lambda kv: len(kv[0]), reverse=True)
    return _ENC_URLS

def enc_rewrite(body):
    # hub cards: okoume.html -> /woods-we-use/okoume
    for fslug in SPECIES_SLUGS:
        body = body.replace(f'href="{fslug}.html"', f'href="{WOOD_PATH}/{fslug}"')
    body = body.replace('href="index.html"', f'href="{WOOD_PATH}"')
    # absolute and root-relative forms, wherever they appear (JSON-LD included)
    for old, new in enc_url_map():
        body = body.replace(LIVE + old, LIVE + new)
        body = body.replace('"' + old + '"', '"' + new + '"')
    return rewrite_links(prune_images(body))       # rewrite_links() adds SITE_BASE

# --- wave 3: eight species that ship as body fragments, not whole pages -------
# content/encyclopedia-wave3/<file>.body.html has no <head>, no hero and no <h1>;
# title and description come from posts3.json. Everything below is assembled from
# those two sources -- none of it is authored copy.
_SCI_RE = re.compile(r'^(.*?) Wood \((.+?)\): ', re.S)

def _species_names(title):
    """'Anjili (Wild Jack) Wood (Artocarpus hirsutus): Properties...'
        -> ('Anjili (Wild Jack)', 'Artocarpus hirsutus')"""
    m = _SCI_RE.match(html.unescape(title))
    if not m:
        warn(f"wave3: cannot read a species name out of {title[:60]!r}")
        return title.split(":")[0].strip(), ""
    return m.group(1).strip(), m.group(2).strip()

def wave3_page(entry, sub):
    """(title, desc, body) for a wave-3 species, with the hero the fragment lacks."""
    fp = os.path.join(ROOT, "content", sub, entry["file"] + ".body.html")
    body = open(fp, encoding="utf-8").read()
    name, sci = _species_names(entry["title"])
    refs = len(re.findall(r'<li id="ref\d+"', body))
    meta = "Cochin Wood Industries"
    if refs: meta += f" &middot; Reviewed against {refs} sources"
    sci_html = ""
    if sci:
        sci_html = (' <span style="font-style:italic;font-weight:400;font-size:.62em;'
                    'color:#6b7a82">(' + esc(sci) + ')</span>')
    hero = (
      '<header class="cwg__hero">\n'
      '  <div class="cwg__container">\n'
      '    <nav class="cwg__crumb" aria-label="Breadcrumb"><a href="/">Home</a>'
      '<span class="cwg__crumb-sep" aria-hidden="true">&rsaquo;</span>'
      f'<a href="{WOOD_PATH}">{WOOD_LABEL}</a>'
      '<span class="cwg__crumb-sep" aria-hidden="true">&rsaquo;</span>'
      f'<span aria-current="page">{esc(name)}</span></nav>\n'
      f'    <p class="cwg__eyebrow">{WOOD_LABEL}</p>\n'
      f'    <h1 class="cwg__h1">{esc(name)}{sci_html}</h1>\n'
      f'    <p class="cwg__meta">{meta}</p>\n'
      '  </div>\n'
      '</header>\n\n')
    # the brand suffix every wave-1/2 <title> carries; seo_title() trims it back
    return entry["title"] + " | Cochin Wood", entry["summary"], hero + body

# --- hub cards for the wave-3 species ----------------------------------------
# The hub HTML predates these eight, so its grids hold no card for them and the
# pages would build with nothing linking to them. Which group each belongs to is
# taken from the lead use in its own posts3.json summary: kadam leads "plywood
# core veneer", venteak is "a teak substitute", the other six lead with packing
# cases, pallets or packing timber. Each value is the last card of that grid.
WAVE3_GROUP = {"kadam": "acacia-mangium",                        # veneer grid
               "casuarina": "pine", "subabul": "pine", "anjili": "pine",
               "matti": "pine", "irul": "pine", "pala": "pine",  # packing grid
               "venteak": "mahogany"}                            # Indian timbers grid

def _hub_add_cards(body, entries):
    """Insert a card for each wave-3 species after the last card of its group,
    anchored on that card's own href, which is unique in the file."""
    for f, entry in entries:
        anchor = WAVE3_GROUP.get(f)
        i = body.find(f'<a class="cwe__card" href="{anchor}.html"') if anchor else -1
        if i < 0:
            warn(f"hub: no anchor card for {f} -- it would build with nothing linking to it")
            continue
        j = body.index("</a>", i) + len("</a>")
        name, sci = _species_names(entry["title"])
        card = ('\n        <a class="cwe__card" href="' + f + '.html">\n'
                '          <p class="cwe__card-name">' + esc(name) + '</p>\n'
                '          <p class="cwe__card-sci">' + esc(sci) + '</p>\n'
                '          <span class="cwe__card-tag">Read</span>\n'
                '        </a>')
        body = body[:j] + card + body[j:]
    return body

def encyclopedia():
    encdir = os.path.join(ROOT, "content", "encyclopedia")
    wave3  = [(f, e) for f, _s, e, d in SPECIES if d == "encyclopedia-wave3"]
    # hub
    hub_src = os.path.join("content", "encyclopedia", "_hub.html")
    title, desc, body = enc_extract(os.path.join(ROOT, hub_src))
    body = enc_rewrite(_hub_add_cards(body, wave3))
    write(WOOD_PATH.strip("/") + "/index.html", src=hub_src,
          content=base(title, desc, WOOD_PATH, body, body_class="cw-encbody",
                       crumbs=[("Home", "/"), (WOOD_LABEL, None)]))
    # species -- the imported pages carry their own visible crumb, so emit schema only
    for f, _slug, entry, sub in SPECIES:
        if sub == "encyclopedia-wave3":
            src = os.path.join("content", sub, f + ".body.html")
            title, desc, body = wave3_page(entry, sub)
        else:
            src = os.path.join("content", sub, f + ".html")
            title, desc, body = enc_extract(os.path.join(encdir, f + ".html"))
        body = enc_rewrite(body)
        write(f"{WOOD_PATH.strip('/')}/{f}/index.html", src=src, content=
              base(title, desc, f"{WOOD_PATH}/{f}", body, body_class="cw-encbody",
                   show_crumbs=False,
                   crumbs=[("Home", "/"), (WOOD_LABEL, WOOD_PATH),
                           (title.split("|")[0].split("—")[0].strip(), None)]))
    return len(SPECIES) + 1

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
    # Commercial pages that exist on cf-live and were missing from this build.
    # Ported verbatim from each live page's Zoho code-snippet body; URLs unchanged.
    "packing-plywood":"packing-plywood.html",
    "rubberwood-plywood":"rubberwood-plywood.html",
    "rubberwood-plywood-container-weight":"rubberwood-plywood-container-weight.html",
    "okoume-plywood":"okoume-plywood.html",
    "plywood-factory":"plywood-factory.html",
    "plywood-manufacturer-india":"plywood-manufacturer-india.html",
    "plywood-manufacturer-kerala":"plywood-manufacturer-kerala.html",
    "plywood-price-guide":"plywood-price-guide.html",
    "perumbavoor-plywood-price-tracker":"perumbavoor-plywood-price-tracker.html",
    "company-verification":"company-verification.html",
    "export-process":"export-process.html",
    # The two legal pages cf-live serves that this build was missing (their meta
    # was already in pages_meta.json, bodies never ported). Each body is the
    # visible <section> of the live page (git show origin/cf-live:<slug>.html),
    # lifted verbatim 2026-08-31. cf-live also injects these same sections into
    # other pages for Google Merchant Center transparency, so the URLs matter.
    # /return-policy -> /return-refund-policy 301 comes back to life with this.
    "return-refund-policy":"return-refund-policy.html",
    "shipping-policy":"shipping-policy.html",
    # /blogs/gcc-export is the one blog taxonomy URL that is ported rather than
    # dropped: it is live, indexed, and linked from the /export hub, uae and oman
    # bodies. The file is the live page's content column lifted verbatim (H1,
    # intro snippet, all 21 post excerpts); the Zoho category/tag sidebar is
    # engine chrome and stays out -- five of its links (/blogs/south-india etc.)
    # point at taxonomy pages this build neither emits nor redirects.
    "blogs/gcc-export":"gcc-export.html",
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
        if not os.path.exists(fp):
            warn(f"page /{slug} NOT BUILT: content/pages/{fname} is missing or "
                 f"unreadable -- a URL this build is supposed to serve would "
                 f"silently vanish at cutover")
            continue
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
        else: warn(f"/about is missing its {f} section -- content/pages/{f} not found")
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
    if not os.path.exists(fp):
        warn(f"{BLOG_SRC} is missing -- the ENTIRE blog (157 live URLs) was "
             f"skipped, not built"); return 0
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
    # Posts allowed to have no "date", each with the why. Anything undated and
    # NOT in this dict is a mistake and gets the loud generic warning below.
    # Empty since 31 Aug 2026: the okoume-plywood post was dropped by owner decision -- one of
    # the two options its entry here offered. The dict stays so the next genuinely expected
    # case has somewhere to live rather than growing a new mechanism.
    EXPECTED_UNDATED = {}
    for slug in undated:
        why = EXPECTED_UNDATED.get(slug)
        if why:
            warn(f'post {slug} has no "date" — {why}')
        else:
            warn(f'post {slug} has no "date" — BlogPosting omits datePublished, which '
                 f'Google wants for article rich results. Add "date": "YYYY-MM-DD" to '
                 f'its entry in {BLOG_SRC}.')
    write("blogs/index.html", src=BLOG_SRC, content=base("Blog — Plywood Guides, Specs & Supply | Cochin Wood",
          "Plywood guides, standards, export-packing notes and city-by-city supply from Cochin Wood Industries.",
          "/blogs", body, crumbs=[("Home", "/"), ("Blog", None)]))
    return n

# ---------------- the export section ----------------
# /export plus eight country lanes. The pages are assembled in export_section.py
# rather than here -- they landed while four sessions were editing this file, and
# a hook merges where 250 lines would conflict. That module reads content/export/
# exactly the way wave3_page() reads content/encyclopedia-wave3/: a body fragment
# per page carrying no <head>, no hero and no <h1>, with the title, description,
# hero, H1, breadcrumb, canonical and schema all coming from export.json the way
# wave3 takes them from posts3.json. It renders through this module's base() and
# write(), so the pages land in the sitemap and _page_source like any other.

def build_export():
    """Render /export and its eight country lanes. Returns the page count.

    export_section says `import build`. Run as `python build.py`, this module is
    "__main__", so that import would execute build.py a SECOND time under the
    name "build" and hand export_section a module whose ASSETS had never been
    fingerprinted -- measured before this guard was added: the nine pages came
    out linking /assets/bundle.css, which no build emits, so all nine shipped
    unstyled. Publishing this module under its own name first makes both names
    resolve to the one live module. No-op when build.py is imported normally.
    """
    sys.modules.setdefault("build", sys.modules[__name__])
    import export_section
    return export_section.build()

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

# ---------------- redirects ----------------
# cf-live's _redirects is 99 hand-maintained rules; regenerating this file from
# LEGACY_REDIRECTS alone dropped 77 of them, silently, on the day of the cutover.
# The live file is carried here instead (git show origin/cf-live:_redirects, read
# 31 Aug 2026), comments and order intact, and every rule is re-checked at build
# time against the pages this build actually emits -- so a rule comes back on its
# own the day the page it points at is ported, and one that has gone stale is
# dropped with a reason rather than shipped as a redirect into a 404.
#
# CLOUDFLARE PAGES HONOURS ONLY THE FIRST 100 RULES. The build counts them and
# warns. Order below is load-bearing wherever the live file said so.
PORTED_REDIRECTS = """
# C-22, the soft 404. Pages strips .html, so /404.html 308s to /404 and the error
# page is served there with a 200 -- a page reading "This page isn't here" that
# tells every crawler it is fine. A 404 STATUS IN THIS FILE IS IGNORED (measured
# on cf-live: Pages honours 301/302/303/307/308 and nothing else), so the error
# page's own URL is sent home instead. FIRST IN THE FILE ON PURPOSE -- not for
# precedence, but so four more additions cannot push it past the 100-rule cut.
/404 / 301

# 21 doubled-segment URLs from GSC. Written explicitly because Cloudflare Pages
# silently drops the :splat form on this project (static destinations work fine).
# MUST STAY FIRST among the /blogs rules: _redirects is first-match-wins.
/blogs/post/post/plywood-supply-to-bengaluru /blogs/post/plywood-supply-to-bengaluru 301
/blogs/post/post/plywood-supply-to-chennai /blogs/post/plywood-supply-to-chennai 301
/blogs/post/post/plywood-supply-to-coimbatore /blogs/post/plywood-supply-to-coimbatore 301
/blogs/post/post/plywood-supply-to-davangere /blogs/post/plywood-supply-to-davangere 301
/blogs/post/post/plywood-supply-to-guntur /blogs/post/plywood-supply-to-guntur 301
/blogs/post/post/plywood-supply-to-hosur /blogs/post/plywood-supply-to-hosur 301
/blogs/post/post/plywood-supply-to-hubli-dharwad /blogs/post/plywood-supply-to-hubli-dharwad 301
/blogs/post/post/plywood-supply-to-hyderabad /blogs/post/plywood-supply-to-hyderabad 301
/blogs/post/post/plywood-supply-to-jeddah /blogs/post/plywood-supply-to-jeddah 301
/blogs/post/post/plywood-supply-to-jubail /blogs/post/plywood-supply-to-jubail 301
/blogs/post/post/plywood-supply-to-kakinada /blogs/post/plywood-supply-to-kakinada 301
/blogs/post/post/plywood-supply-to-karur /blogs/post/plywood-supply-to-karur 301
/blogs/post/post/plywood-supply-to-khammam /blogs/post/plywood-supply-to-khammam 301
/blogs/post/post/plywood-supply-to-khobar /blogs/post/plywood-supply-to-khobar 301
/blogs/post/post/plywood-supply-to-nellore /blogs/post/plywood-supply-to-nellore 301
/blogs/post/post/plywood-supply-to-riyadh /blogs/post/plywood-supply-to-riyadh 301
/blogs/post/post/plywood-supply-to-salem /blogs/post/plywood-supply-to-salem 301
/blogs/post/post/plywood-supply-to-sivakasi /blogs/post/plywood-supply-to-sivakasi 301
/blogs/post/post/plywood-supply-to-sohar /blogs/post/plywood-supply-to-sohar 301
/blogs/post/post/plywood-supply-to-tirupati /blogs/post/plywood-supply-to-tirupati 301
/blogs/post/post/plywood-supply-to-vizag /blogs/post/plywood-supply-to-vizag 301

# The wood section. /woods-we-use is the live URL and this build now emits it, so
# both live rules still hold. The species pages move under the hub with it: all
# 28 are live at /blogs/post/wood-<slug> and would otherwise 404. One wildcard
# costs one rule; 28 explicit rules do not fit under the 100-rule cut. It has to
# sit above the generic /blogs rules further down.
/wood-encyclopedia /woods-we-use 301
/wood-encyclopedia/* /woods-we-use 301
/blogs/post/wood-* /woods-we-use 301

/privacy /privacy-policy 301
/terms /terms-and-conditions 301
/about-us /about 301
/contact-us /contact 301

# --- 2026-07-07 audit fixes: old guide/page slugs -> live equivalents ---
# Sources also present in LEGACY_REDIRECTS are overridden by it below, so the
# 301 and the in-content link rewrite cannot disagree.
/guide-okoume-vs-gurjan /blogs/post/okoume-vs-gurjan-plywood 301
/guide-bwp-bwr-plywood-explained /blogs/post/bwr-vs-bwp-for-export-packing-when-mr-grade-will-fail-at-sea 301
/guide-is-710-vs-is-303 /blogs/post/how-to-read-a-plywood-grade-stamp 301
/guide-marine-plywood-thickness /blogs/post/marine-plywood-thickness-guide 301
/guide-rubberwood-plywood-explained /woods-we-use 301
/guide-plywood-boxes-ispm-15 /blogs/post/ispm-15-heat-treatment-vs-methyl-bromide 301
/guide-ispm-15-crate-cost /plywood-boxes-crates 301
/guide-plywood-for-packing-cases /commercial-plywood 301
/packing-grade-plywood-spec-sheet /blogs/post/packing-grade-plywood-spec-sheet 301
/plywood-pallets-crates-ahmedabad /plywood-pallets 301

# --- blog taxonomy ---
# The two tag rules that reach a product page must stay ABOVE the /blogs/tag/*
# wildcard: first match wins, and /blogs is the weaker destination.
/blogs/tag/film-faced-plywood /film-faced-shuttering-plywood 301
/blogs/tag/marine-plywood /marine-plywood 301
# This build emits no pagination and no tag pages, so both families collapse.
# NOTE: cf-live carries "never wildcard /blogs/page/* -- page/2..N ARE LIVE".
# That was true of cf-live. It is not true of this build, which emits /blogs and
# /blogs/post/<slug> and nothing else; the owner's call is that the 55 pagination
# and tag URLs go. These two rules replace 9 of the live ones.
/blogs/page/* /blogs 301
/blogs/tag/* /blogs 301
/blogs/author/* /blogs 301
/blogs/post/ /blogs 301
/blogs/Uncategorized /blogs 301
/blogs/insight /blogs 301
/blogs/plywood /blogs 301
/blog/* /blogs 301
# catch-all for every remaining /blogs/<anything>/feed
/blogs/feed /blogs 301
/blogs/*/feed /blogs 301

# --- 2026-07-28 GSC 404 sweep. Old keyword URLs -> best-matching money page ---
/best-plywood-suppliers-in-kerala /plywood-manufacturer-kerala 301
/plywood-suppliers-in-kochi /plywood-manufacturer-kerala 301
/plywood-manufacturers-in-perumbavoor /plywood-factory 301
/plywood-manufacturers-perumbavoor /plywood-factory 301
/plywood-price-kerala /plywood-price-guide 301
/marine-plywood-kerala /marine-plywood 301
/plywood-pallets-crates-mumbai /plywood-pallets 301
/plywood-pallets-crates-delhi-ncr /plywood-pallets 301
/guide-plywood-cable-drum-specifications /plywood-cable-drums 301
/sawn-timber-products /sawn-timber 301
/sawn_timber_products /sawn-timber 301
/engineered_wood_panels /products 301
/industrial-packaging /products 301
/return-policy /return-refund-policy 301

# --- legacy pre-migration paths ---
/Home / 301
/home / 301
/40 / 301
/our-process /about 301
/helpdesk /contact 301
/faq-1 /faq 301
/guides/ /resources 301

# --- removed posts -> nearest live page ---
/blogs/post/uae-s-green-building-standards-driving-plywood-innovation* /export/uae 301
/blogs/post/areas-we-serve-* /export 301
/blogs/post/gcc-s-humanitarian-leadership-* /export 301
/blogs/post/plywood-in-global-aviation-cargo-packaging /blogs 301
/blogs/post/plywood-in-global-e-commerce-warehousing* /blogs 301
/blogs/post/marine-plywood-in-global-yacht-interiors /marine-plywood 301
/blogs/post/plywood-in-smart-home-technology /blogs 301
/blogs/post/plywood-in-modular-healthcare-units-building-faster-safer-hospitals /blogs 301
/blogs/post/qatar-s-world-cup-legacy-plywood-in-sports-projects /export/qatar 301
/blogs/post/bahrain-s-tourism-push-plywood-in-resorts-interiors /export/bahrain 301
/blogs/post/plywood-in-urban-public-furniture1 /blogs 301
/blogs/post/plywood-in-space-robotics-testing-facilities /blogs 301
/blogs/post/plywood-in-international-expo-booths1 /blogs 301
/blogs/post/shuttering-plywood-in-renewable-energy-plants /film-faced-shuttering-plywood 301

# Thin 324-word duplicate of the 1532-word money page - consolidate. Holds only
# while /okoume-plywood is not yet built; the moment it is, this rule and
# LEGACY_REDIRECTS' /okoume-plywood entry point at each other, and the shadow
# check below drops whichever source has become a real page.
/blogs/post/okoume-plywood /okoume-plywood 301

# 603 explicit /dist/ rules once silently became 404s past the 100-rule cut. One
# wildcard costs one rule. :splat was tested live here and every path still 404'd.
/dist/* / 301

# /index.html is a duplicate of /. build.py exempts *.html sources from its
# "this source is a real page" check, because sending this one home is the point.
/index.html / 301
"""

# Rules NOT carried across from cf-live, and why. Recorded so the next person can
# see they were considered rather than missed. Settled entries print as ONE
# summary warning; an entry whose reason starts with "NEEDS OWNER" prints its
# own line until the owner rules on it.
DROPPED_FROM_LIVE = {
    "/CLAUDE.md /": "cf-live is served verbatim so its CLAUDE.md was downloadable; "
                    "the cutover serves dist/, which contains no such file",
    "/.github/* /": "same -- dist/ has no .github, so there is nothing to hide",
    "/files/Home/* /": "cf-live served nothing under /files/Home/; this build SERVES "
                       "/files/Home/home-1-hero.jpg there and the rule would 301 it away",
    "/files/home/* /": "the lowercase twin of the above, left out for the same reason",
    "/blogs/page/1 /blogs": "subsumed by the new /blogs/page/* wildcard",
    "/blogs/tag/india-suppliers /blogs": "subsumed by the new /blogs/tag/* wildcard",
    "/blogs/tag/interiors /blogs": "subsumed by the new /blogs/tag/* wildcard",
    "/blogs/tag/plywood-export/ /blogs": "subsumed by the new /blogs/tag/* wildcard",
    "/blogs/tag/uae/feed /blogs/tag/uae": "target never built; /blogs/tag/* catches it",
    "/blogs/tag/uttar-pradesh/feed /blogs/tag/uttar-pradesh":
        "target never built; /blogs/tag/* catches it",
    "/blogs/tag/andhra-pradesh/page/* /blogs/tag/andhra-pradesh":
        "target never built; /blogs/tag/* catches it",
    "/blogs/buyer-guides/feed /blogs/buyer-guides":
        "target never built; /blogs/*/feed catches it",
    "/blogs/north-india/feed /blogs/north-india":
        "target never built; /blogs/*/feed catches it",
    "/blogs/buyer-guides/page/* /blogs/buyer-guides":
        "settled 31 Aug 2026: Edwin ruled the five category pages and this "
        "pagination all redirect to /blogs. The replacement rules live in the "
        "owner-decided LEGACY_REDIRECTS.update() block near the top of this file",
}

# The seven sources where cf-live's 301 target and LEGACY_REDIRECTS disagree.
# Resolved, not open: LEGACY_REDIRECTS wins BY DESIGN, because it also rewrites
# the in-content links, and a page's links and its slug's 301 must agree (the
# 2026-07-07 audit's cf-live targets were nearest-page approximations; LEGACY's
# are the exact posts). Keyed by source -> the target cf-live sends today; if
# cf-live ever changes one, the stored value stops matching and the build goes
# back to warning loudly about that source.
EXPECTED_OVERRIDDEN = {
    "/guide-bwp-bwr-plywood-explained": "/blogs/post/bwr-vs-bwp-for-export-packing-when-mr-grade-will-fail-at-sea",
    "/guide-is-710-vs-is-303": "/blogs/post/how-to-read-a-plywood-grade-stamp",
    "/guide-ispm-15-crate-cost": "/plywood-boxes-crates",
    "/guide-plywood-boxes-ispm-15": "/blogs/post/ispm-15-heat-treatment-vs-methyl-bromide",
    "/guide-plywood-cable-drum-specifications": "/plywood-cable-drums",
    "/guide-plywood-for-packing-cases": "/commercial-plywood",
    "/guide-rubberwood-plywood-explained": "/woods-we-use",
}

REDIRECT_LIMIT = 100          # Cloudflare Pages honours only the first N rules

def _served_paths():
    """Every URL this build actually serves: each file, plus the clean directory
    URL of every index.html. Used so no redirect can shadow real content."""
    out = set()
    for r, _d, fs in os.walk(DIST):
        rel = os.path.relpath(r, DIST).replace(os.sep, "/")
        pre = "" if rel == "." else "/" + rel
        for f in fs:
            out.add(f"{pre}/{f}")
            if f == "index.html": out.add(pre or "/")
    return out

def _rule_re(src):
    """A _redirects source as a regex. Cloudflare's * spans slashes."""
    return re.compile("^" + ".*".join(re.escape(p) for p in src.split("*")) + "$")

def _parse_redirects(text):
    """-> [("#", comment) | ("r", src, dst, code)], order and comments preserved."""
    items = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            items.append(("#", ""))
        elif s.startswith("#"):
            items.append(("#", s))
        else:
            p = s.split()
            items.append(("r", p[0], p[1], p[2] if len(p) > 2 else "301"))
    return items

def build_redirects():
    """Merge the ported live rules with LEGACY_REDIRECTS, drop whatever no longer
    holds, report every drop, and emit. Returns the number of rules emitted."""
    items = _parse_redirects(PORTED_REDIRECTS)
    have  = {it[1] for it in items if it[0] == "r"}
    added = False

    # LEGACY_REDIRECTS also rewrites in-content links, so where it and the live
    # file disagree on a source the in-content target has to win -- otherwise a
    # link on the page and the 301 for the same slug lead to different places.
    overridden = []
    for src in sorted(LEGACY_REDIRECTS):
        dst = LEGACY_REDIRECTS[src]
        if src.startswith("/blogs/post/wood-"):
            continue                      # the /blogs/post/wood-* wildcard covers these
        if src in have:
            for i, it in enumerate(items):
                if it[0] == "r" and it[1] == src and it[2] != dst:
                    if EXPECTED_OVERRIDDEN.get(src) == it[2]:
                        overridden.append(src)     # known and resolved: one line below
                    else:
                        warn(f"redirect conflict on {src}: cf-live sends it to {it[2]}, "
                             f"LEGACY_REDIRECTS to {dst} -- using {dst}, which is what the "
                             f"in-content links already say. If that is the settled call, "
                             f"record it in EXPECTED_OVERRIDDEN")
                    items[i] = ("r", src, dst, "301")
        else:
            if not added:
                items.append(("#", ""))
                items.append(("#", "# --- LEGACY_REDIRECTS slugs cf-live never had a rule for ---"))
                added = True
            items.append(("r", src, dst, "301"))
    if overridden:
        warn(f"{len(overridden)} cf-live 301 targets rewritten to LEGACY_REDIRECTS' -- "
             f"by design, not drift: LEGACY_REDIRECTS also rewrites the in-content "
             f"links, and a page's links and its slug's 301 must agree. "
             f"EXPECTED_OVERRIDDEN in build.py lists each pair; a change on the "
             f"cf-live side turns the loud per-slug warning back on")

    served, out, seen, dropped = _served_paths(), [], set(), []
    def resolve(t):
        t = t.split("#")[0].split("?")[0]
        return t in served or (t.rstrip("/") or "/") in served

    for it in items:
        if it[0] == "#":
            out.append(it[1]); continue
        _k, src, dst, code = it
        if src in seen:
            dropped.append((src, dst, "duplicate source -- the earlier rule wins")); continue
        if not resolve(dst):
            dropped.append((src, dst, "target is not a page this build emits")); continue
        # a rule matching something we serve would take that page off the site
        if not src.endswith(".html"):
            hit = next((p for p in sorted(served) if _rule_re(src).match(p)), None)
            if hit:
                dropped.append((src, dst, f"would shadow {hit}, which this build serves"))
                continue
        seen.add(src); out.append(f"{src} {dst} {code}")

    n = sum(1 for l in out if l and not l.startswith("#"))
    # Drops that are the machinery working as designed, with the why to print.
    # Keyed (src, dst); anything not listed here still warns bare, as a surprise.
    # Empty since 31 Aug 2026: the thin okoume post is gone, so the consolidation 301 now
    # FIRES instead of idling, and there is nothing to explain. The dict stays for the next
    # pending case.
    EXPECTED_DROPPED = {}
    for src, dst, why in dropped:
        note = EXPECTED_DROPPED.get((src, dst))
        warn(f"redirect dropped: {src} -> {dst}  ({why})"
             + (f" -- {note}" if note else ""))
    open_drops = {r: w for r, w in DROPPED_FROM_LIVE.items()
                  if w.startswith("NEEDS OWNER")}
    settled = len(DROPPED_FROM_LIVE) - len(open_drops)
    if settled:
        warn(f"{settled} cf-live rules deliberately not carried across -- each was "
             f"considered, not missed: DROPPED_FROM_LIVE in build.py records every "
             f"one with its reason (target never built and a wildcard catches it, "
             f"subsumed by a new wildcard, or the rule would hide a file this "
             f"build serves)")
    for rule, why in sorted(open_drops.items()):
        warn(f"cf-live rule not carried across: {rule}  ({why})")
    if n > REDIRECT_LIMIT:
        warn(f"_redirects has {n} rules; Cloudflare Pages honours only the first "
             f"{REDIRECT_LIMIT}, so the last {n - REDIRECT_LIMIT} will never fire")
    elif n > REDIRECT_LIMIT - 5:
        # cf-live sat at 99 of 100 and 603 rules had already fallen off the end
        # once. Say so while there is still room to do something about it.
        warn(f"_redirects is at {n} of the {REDIRECT_LIMIT} rules Cloudflare Pages "
             f"honours — {REDIRECT_LIMIT - n} left before rules start being ignored")
    header = (f"# Generated by build.py -- do not hand-edit; change PORTED_REDIRECTS\n"
              f"# or LEGACY_REDIRECTS instead. {n} rules, of the {REDIRECT_LIMIT}\n"
              f"# Cloudflare Pages honours. Order is load-bearing: first match wins.\n")
    write("_redirects", header + "\n".join(out).strip("\n") + "\n")
    return n

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
    x = build_export()
    assets_and_meta()            # also discovers /files/ refs inside the CSS
    f = copy_referenced_files()  # so this must run after it
    for ref in sorted(_files_missing):
        warn(f"photo missing, reference removed: {ref}")
    sm = build_sitemap()
    # last: it checks every rule against the pages this build actually emitted,
    # /files/ assets included, so everything has to be on disk first
    rd = build_redirects()
    cnt = sum(len(fs) for _,_,fs in os.walk(DIST))
    print(f"BUILD OK  base='{BASE or '(root)'}'  {p} content pages + {n} wood pages + {x} export pages + {b} blog posts + {f} images  sitemap:{sm}  redirects:{rd}/{REDIRECT_LIMIT}  files: {cnt}")
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
