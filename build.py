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

# ---- EVERY TEXT BYTE THIS BUILD EMITS IS LF, ON EVERY PLATFORM ---------------
#
# THE PUBLISHED BYTES MUST BE THE BUILT BYTES, and until this block existed they
# were not. dist/ is committed to cf-live, cf-live carries no .gitattributes, and
# this machine has core.autocrlf=true set system-wide (C:/Program Files/Git/etc/
# gitconfig), so `git add -A` renormalised every CRLF text file on the way into
# the index. Measured on 8fc64aad: of 607 files, dist/assets/site.f14bf457.js
# went in 3,801 -> 3,704 bytes (97 CRLF) and dist/assets/fonts.css 6,560 -> 6,407
# (153 CRLF). Cloudflare Pages then served the 3,704-byte file under a name whose
# hash describes the 3,801-byte one, pinned max-age=31536000, immutable, from all
# 253 pages -- and the tree the preflight had certified was not the tree that got
# published.
#
# THE SAME DEFECT MADE THE BUILD MACHINE-LOCAL. The two files above are copied
# and hashed as raw bytes, and their raw bytes are a property of how the checkout
# was made: CRLF here, LF on any autocrlf=false clone (Linux, CI, a colleague's
# machine). Same commit, two different asset names, two different _headers, 253
# different pages -- a different 607-file tree from the reviewed one. The
# preflight's "two builds byte-identical" check runs both builds on ONE machine,
# so it can never see this; check 12 below now can.
#
# The rule is git's own, deliberately, so that `git add` has nothing left to do:
# a file with a NUL byte in its first 8,000 is binary and passes through
# untouched, everything else has CRLF folded to LF. That NUL test is not
# pedantry -- assets/logo.png, assets/og/cwi-og-share-1200x630.png and four
# .woff2 faces contain incidental CR LF byte pairs inside compressed data, and
# rewriting those would corrupt the file while leaving it looking present.
# Lone CR is left alone for the same reason: git does not touch it either, and
# matching git exactly is the whole point.
def is_binary(data):
    """git's own text/binary test: NUL in the first 8,000 bytes."""
    return b"\x00" in data[:8000]

def lf(data):
    """The bytes git would store for `data` -- i.e. what Pages will serve."""
    return data if is_binary(data) else data.replace(b"\r\n", b"\n")

def read_lf(path):
    with open(path, "rb") as fh: return lf(fh.read())

def copy_lf(src, dst):
    """shutil.copy's contract, minus the platform in the output bytes."""
    with open(dst, "wb") as fh: fh.write(read_lf(src))

# ---------------- WHERE THE COMPANY SHIPS: one list, one place ----------------
#
# content/export-markets.json is the ONLY place the country list, the country
# count and the continent count are written down. Every page that states or
# implies where Cochin Wood ships now carries a token instead of a typed number
# or a typed list, and this block expands them at write() time.
#
# WHY IT EXISTS. Before this the same fact was typed out in a dozen places --
# the /about FAQ, the Organization schema's areaServed, the home trust strip,
# /export-process, /faq, /industries, /marine-plywood, four product and
# capability pages and two meta descriptions -- and no two agreed. The audit of
# 2 Sep 2026 found the ruled list in exactly one of them. Copy said "five
# continents", the schema named three countries, /export-process dropped Kuwait
# and Bahrain, and four pages sold "Southeast Asia" as a region rather than
# naming the markets in it. A sixth version of the list is now impossible to
# create by editing copy, because the copy no longer has a list in it to edit.
#
# tools/check_site.py independently derives the continent count from the FAQ
# answer's own words and enforces it against every page's copy, so the data and
# the prose are checked against each other on every run rather than trusted.
EXPORT_MARKETS_SRC = os.path.join("content", "export-markets.json")

def _load_export_markets():
    fp = os.path.join(ROOT, EXPORT_MARKETS_SRC)
    if not os.path.exists(fp):
        warn(f"{EXPORT_MARKETS_SRC} is missing -- every page's export-market claim, the "
             f"Organization schema's areaServed and the continent count all come from it")
        return {"domestic": {"name": "India", "iso": "IN"}, "groups": []}
    return json.load(open(fp, encoding="utf-8"))

EXPORT_MARKETS = _load_export_markets()

def _prose(c):    return c.get("prose") or c["name"]
def _oxford(xs):
    """a, b and c -- the house style everywhere else on the site."""
    xs = list(xs)
    if not xs: return ""
    if len(xs) == 1: return xs[0]
    return ", ".join(xs[:-1]) + " and " + xs[-1]

EXPORT_GROUPS    = EXPORT_MARKETS.get("groups", [])
EXPORT_COUNTRIES = [c for g in EXPORT_GROUPS for c in g.get("countries", [])]
EXPORT_ISO       = ([EXPORT_MARKETS["domestic"]["iso"]]
                    + [c["iso"] for c in EXPORT_COUNTRIES])
CONTINENT_COUNT  = len(EXPORT_GROUPS)
_NUMWORD = {1: "one", 2: "two", 3: "three", 4: "four",
            5: "five", 6: "six", 7: "seven", 8: "eight"}

def _group_phrase(g):
    names = _oxford(_prose(c) for c in g.get("countries", []))
    # "Australia in Australia" is silly, and naming Oceania alongside Australia
    # would count that one continent twice in check_site.py -- see the JSON's
    # _why_no_oceania note. The flag is set on that group and only that group.
    if g.get("sole_country_is_the_continent"): return names
    return f"{names} in {g['continent']}"

def _export_sentence():
    if not EXPORT_GROUPS: return ""
    dom = EXPORT_MARKETS["domestic"]["name"]
    return (f"We supply {dom} domestically and export to "
            + "; ".join(_group_phrase(g) for g in EXPORT_GROUPS[:-1])
            + "; and " + _group_phrase(EXPORT_GROUPS[-1]) + ".")

# Named for use INSIDE build.py's own f-strings. A {{CWI_...}} token written in
# an f-string collapses to single braces before write() ever sees it, so the
# token silently ships to the page -- which is exactly what happened to the home
# trust strip on the first cut of this. Interpolate these instead; the tokens are
# for the content files, which are not f-strings.
N_EXPORT_COUNTRIES = str(len(EXPORT_COUNTRIES))
N_CONTINENTS_WORD  = _NUMWORD.get(CONTINENT_COUNT, str(CONTINENT_COUNT))

CANON = {
    "{{CWI_EXPORT_MARKETS}}":       _export_sentence(),
    "{{CWI_EXPORT_COUNTRY_LIST}}":  _oxford(_prose(c) for c in EXPORT_COUNTRIES),
    "{{CWI_EXPORT_COUNTRY_COUNT}}": N_EXPORT_COUNTRIES,
    "{{CWI_EXPORT_CONTINENTS}}":    N_CONTINENTS_WORD,
}

# Both brace depths on purpose: `{{CWI_X}}` is an unknown token, and `{CWI_X}` is
# a known one that an f-string ate on the way here. Either would reach a buyer as
# literal braces, and neither is visible to check_site.py.
_UNEXPANDED = re.compile(r"\{\{?CWI_[A-Z_]+\}?\}")

def expand_canon(text, where=""):
    """Substitute the canonical export-market tokens. Called from write(), so it
    reaches page copy, meta descriptions and JSON-LD alike from one place."""
    for tok, val in CANON.items():
        if tok in text: text = text.replace(tok, val)
    left = _UNEXPANDED.search(text)
    if left:
        warn(f"{where or '(output)'} still contains {left.group(0)} -- either the token is not "
             f"in build.py's CANON map or an f-string halved its braces; the page would ship "
             f"the literal braces to a buyer")
    return text

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

# addr is the principal place of business exactly as it reads on the GST
# certificate, and word for word as /company-verification already publishes it.
# It used to say "Kuruppampady, Ernakulam, Kerala 683545" here and in the
# Organization schema below -- a different place, on all 252 pages, against the
# one address a buyer can actually check on the GST portal.
CONTACT = dict(email="sales@cochinwood.in", phone_disp="+91 95674 10175",
               phone_href="+919567410175",
               addr="15-236/B, Thoppilan Building, Vattakattupady, Rayamangalam, "
                    "Perumbavoor, Ernakulam, Kerala 683542, India",
               wa="919567410175")

# Copied from /company-verification (content/pages/company-verification.html),
# which is where the site publishes them for a buyer to check on the MCA and GST
# portals. Kept here so /contact can state them without the two pages drifting.
GSTIN = "32AAJCC9689H1Z5"
CIN   = "U20219KL2021PTC072862"

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
# hero_image() reads this same map for the Product schema's "image" and for the
# page's og:image, so a page that already carries its own photo is listed here
# too even though it needs no swap.
# The "Plywood Product Photos" refs are %20-encoded because that is the form the
# already-shipping /bwr-hardwood-plywood hero uses, and copy_referenced_files()
# unquotes the ref again on the way to dist.
# Still heroless: container-flooring-plywood (never photographed), and
# packing/okoume/rubberwood-plywood -- their photos exist beside these, but those
# three bodies are cwg__hero pages with no <img> for this map to swap.
PRODUCT_HERO = {
    # The three mirror-built pages (packing, okoume, rubberwood) carry no <img> of
    # their own: their cwg__ template has no image slot, so _fix_img has nothing to
    # swap. They are named here anyway, because hero_image() registers the file
    # independently of the body -- that is what puts the real product photo into
    # their Product schema and og:image instead of the generic share banner. The
    # visible on-page photo still needs an image slot adding to that template.
    "packing-plywood":         "/files/Plywood%20Product%20Photos/cwi-packing-plywood.webp",
    "okoume-plywood":          "/files/Plywood%20Product%20Photos/cwi-okoume-plywood.webp",
    "rubberwood-plywood":      "/files/Plywood%20Product%20Photos/cwi-rubberwood-plywood.webp",
    "marine-plywood":          "/files/Plywood%20Product%20Photos/cwi-marine-plywood.webp",
    "commercial-plywood":      "/files/Plywood%20Product%20Photos/cwi-commercial-plywood.webp",
    # brown film face rather than the red alternative shot: it is the default
    # shuttering face buyers picture, and it does not read as the same panel as
    # the maroon chequered hero below.
    "film-faced-shuttering-plywood": "/files/Plywood%20Product%20Photos/cwi-film-faced-brown.webp",
    "chequered-anti-skid-plywood":   "/files/Plywood%20Product%20Photos/cwi-anti-skid.webp",
    # Not a placeholder swap: /bwr-hardwood-plywood's body already carries this
    # exact file. It is named here so the schema and the share card get the
    # photo the page shows, like every other row.
    "bwr-hardwood-plywood":    "/files/Plywood%20Product%20Photos/cwi-bwr-hardwood-plywood.webp",
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

def hero_image(slug):
    """(absolute url, width, height) of the photo a product page actually shows.

    One generic share card used to be the og:image on all 252 pages AND the
    "image" inside every Product block, so /plywood-pallets handed Google and
    every chat unfurl a banner while the page beside it rendered a real
    photograph of pallets. PRODUCT_HERO already names that photograph; this
    turns it into the absolute URL the schema and og:image need, and measures it
    so og:image:width and og:image:height are stated rather than guessed.
    Returns None where the page has no photo of its own -- the generic card is
    the honest fallback there, not somebody else's product."""
    ref = PRODUCT_HERO.get(slug)
    if not ref: return None
    path = resolve_file(ref)
    if not path:
        _files_missing.add(ref)
        return None
    # registered here as well as in prune_images, so the file still ships if the
    # page body ever stops carrying the <img> that referenced it
    pub = register_file(ref, path)
    w, h = image_size(path) or (None, None)
    return (LIVE + pub, w, h)

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

# The catalogue, the homepage grid (first 9) and the footer column (first 7) all
# read this list, so order is editorial: the biggest lines lead. Packing, Okoume
# and rubberwood ply were built as pages but left off this list, which meant the
# three grades the copy calls our largest were reachable from no index at all.
PRODUCTS = [
    ("packing-plywood","Packing Plywood","MR packing grade to IS 303 in 6-18mm for cases, crates and pallets."),
    ("okoume-plywood","Okoume Plywood","Pale Okoume-faced packing panels and calibrated E1 board for joinery."),
    ("rubberwood-plywood","Rubberwood Plywood","Plantation-hardwood MR panels, lighter per container than dense ply."),
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

# The one company profile that exists. It is written once and used twice -- the
# Organization schema's sameAs and the footer link -- because a profile Google is
# told about but a reader cannot reach is half a fact. A LinkedIn company page
# and a Google Business Profile were both recommended by the 4 Sep 2026 audit and
# NEITHER HAS BEEN CREATED: a sameAs pointing at a 404 is worse than an absent
# one, so nothing is guessed here until those pages actually exist.
INSTAGRAM_URL = "https://www.instagram.com/cochinwood/"

def footer():
    prod = "".join(f'<a href="{u("/"+s)}">{n}</a>' for s,n,_ in PRODUCTS[:7])
    # The three column labels used to be <h2>. That put three headings into the
    # outline of all 252 pages that describe no content -- on the homepage they
    # were 3 of its 16 H2s -- and a screen reader reading the heading list heard
    # "Products / Explore / Contact" as if they ranked with the page's own
    # sections. They are labels for link groups, so each column is a <nav> named
    # by aria-label and the label itself is a <p>. .cw-ft__h is a class rule
    # (font, size, weight and margin are all set on it), so the <p> renders
    # exactly as the <h2> did.
    #
    # THE EXPLORE COLUMN CARRIES THE TWO TRUST PAGES, because it is the only
    # link list on all 252 pages. /company-verification -- the registrations a
    # buyer can check on the MCA and GST portals without asking us -- was linked
    # from no top-level page at all; the case-studies post had exactly one
    # inbound link, from /blogs, so the only customer proof on the site was
    # three clicks from anywhere. Nine links is the most this column should
    # carry; anything further needs a trim first, not another entry.
    return f'''<footer class="cw-ft"><div class="cw-wrap">
  <div class="cw-ft__cols">
    <div class="cw-ft__brand"><b>Cochin Wood Industries</b><p>Plywood manufacturer in Kochi, Kerala — packing, Okoume and shuttering ply, shipped across India and exported. Part of a group manufacturing in Perumbavoor since 1986.</p></div>
    <nav aria-label="Products"><p class="cw-ft__h">Products</p>{prod}</nav>
    <nav aria-label="Explore"><p class="cw-ft__h">Explore</p><a href="{u('/products')}">All products</a><a href="{u(WOOD_PATH)}">{WOOD_LABEL}</a><a href="{u('/resources')}">Resources</a><a href="{u('/blogs/post/case-studies')}">Case studies</a><a href="{u('/industries')}">Industries</a><a href="{u('/export')}">Export</a><a href="{u('/about')}">About</a><a href="{u('/company-verification')}">Company verification</a><a href="{u('/faq')}">FAQ</a></nav>
    <nav aria-label="Contact"><p class="cw-ft__h">Contact</p><a href="tel:{CONTACT['phone_href']}">{CONTACT['phone_disp']}</a><a href="mailto:{CONTACT['email']}">{CONTACT['email']}</a><a href="https://maps.google.com/?q=Thoppilan+Building+Vattakattupady+Rayamangalam+Perumbavoor+Kerala+683542" target="_blank" rel="noopener">{CONTACT['addr']}</a><a href="{INSTAGRAM_URL}" target="_blank" rel="noopener">Instagram</a></nav>
  </div>
  <div class="cw-ft__bar"><span>&copy; 2026 Cochin Wood Industries Pvt Ltd. Group established 1986.</span>
  <span><a href="{u('/privacy-policy')}" style="display:inline">Privacy</a> &middot; <a href="{u('/terms-and-conditions')}" style="display:inline">Terms</a></span></div>
</div></footer>'''

OG_IMAGE = LIVE + "/assets/og/cwi-og-share-1200x630.png"   # 1200x630 share card
# Measured, not read off the filename: og:image:width and og:image:height were
# absent on all 252 pages, and an unfurl that has to fetch the image before it
# can size the card often just drops the card. (None, None) emits neither tag
# rather than stating a size we could not confirm.
OG_IMAGE_SIZE = image_size(os.path.join(ROOT, "assets", "og",
                                        "cwi-og-share-1200x630.png")) or (None, None)

# The LocalBusiness "image" was the same PNG as its "logo" -- a mark on a white
# square, which is what Google shows when it wants a picture of the premises.
# This is the warehouse aisle already published on /about, so the schema and the
# page agree and copy_referenced_files() already ships the file.
ORG_IMAGE_REF = "/files/Enhanced%20Factory%20Photos/factory_08.jpg"
_org_img_src = resolve_file(ORG_IMAGE_REF)
if _org_img_src:
    # registered independently of /about's markup: the schema names this file on
    # every one of the 252 pages, so it must ship even if that page's photo set
    # is ever re-cut
    register_file(ORG_IMAGE_REF, _org_img_src)
else:
    warn(f"the Organization schema's image {ORG_IMAGE_REF} is not on disk -- "
         f"every page would declare a LocalBusiness photo that 404s")

# areaServed is the machine-readable half of the same fact the copy states, so
# it comes off the same list. It used to read ["IN","AE","VN"] on all 233 pages
# -- India, the UAE and Vietnam -- which told Google the company serves three
# countries while the page beside it claimed five continents. ISO 3166-1
# alpha-2, one code per market, India first.
AREA_SERVED = json.dumps(EXPORT_ISO, separators=(",", ":"))

# The PostalAddress was wrong twice over: the wrong place (Kuruppampady 683545,
# not the address on the GST certificate) and the wrong shape -- "Kuruppampady"
# is a locality, not a street, and Ernakulam is the district, not the locality.
# streetAddress now carries the building and the village it stands in,
# addressLocality is the town a courier or a Google Business listing matches on,
# and addressRegion stays the state. Ernakulam is dropped rather than
# mis-slotted: the district is not a PostalAddress field, and the human-readable
# line in the footer still says it.
ORG_SCHEMA = '''<script type="application/ld+json">
{"@context":"https://schema.org","@type":["Organization","LocalBusiness"],"@id":"https://www.cochinwood.in/#organization","name":"Cochin Wood Industries","url":"https://www.cochinwood.in/","logo":"https://www.cochinwood.in/assets/logo.png","image":"''' + LIVE + ORG_IMAGE_REF + '''","email":"sales@cochinwood.in","telephone":"+919567410175","address":{"@type":"PostalAddress","streetAddress":"15-236/B, Thoppilan Building, Vattakattupady, Rayamangalam","addressLocality":"Perumbavoor","addressRegion":"Kerala","postalCode":"683542","addressCountry":"IN"},"parentOrganization":{"@type":"Organization","name":"Cochin Wood Group","foundingDate":"1986"},"areaServed":''' + AREA_SERVED + ''',"sameAs":["''' + INSTAGRAM_URL + '''"],"description":"Plywood manufacturer in Kochi, Kerala - packing, Okoume, marine and film-faced shuttering plywood, sawn timber and export crates."}
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
        # RAW text for the JSON-LD, HTML-escaped text only for the visible span
        # above. json.dumps does its own escaping, so a label that arrived
        # already escaped -- pages_meta.json and posts.json both carry '&amp;' --
        # shipped a literal "Packing Plywood Factory &amp; Manufacturer" inside
        # the block on ten pages.
        item = {"@type": "ListItem", "position": i + 1, "name": html.unescape(label)}
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
        # A head that already names the brand takes no brand suffix. Without this, a title
        # carried over verbatim from the live site -- "Request a Plywood Quote · Cochin Wood
        # Industries" -- comes out as "... Cochin Wood Industries | Cochin Wood", saying the
        # company name twice inside Google's 62 characters and spending them on nothing. The
        # suffix exists to ADD the brand to a title that lacks it, not to repeat one it has.
        if "Cochin Wood" in h:
            return h if len(h) <= TITLE_MAX else None
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
    """Product markup so every catalogue page is eligible for rich results.

    THERE IS DELIBERATELY NO offers NODE. It used to declare priceCurrency INR
    and InStock with no price, priceSpecification or sku beside them, which the
    Rich Results Test and Search Console both score as an ERROR, not a warning:
    all 13 Product blocks failed validation, so the markup bought nothing. Cochin
    Wood quotes every order and publishes no list price, so there is no number to
    put there, and inventing one to satisfy a validator would put a false price
    on the page. A bare Product -- name, description, image, brand, category,
    url -- is valid, and it is everything we can honestly state."""
    row = next((r for r in PRODUCTS if r[0] == slug), None)
    if not row: return ""
    _, name, desc = row
    hero = hero_image(slug)
    data = {"@context": "https://schema.org", "@type": "Product",
            "name": name, "description": desc,
            "url": LIVE + "/" + slug,
            # the photograph this page shows, falling back to the share card only
            # where the page has no photo of its own
            "image": hero[0] if hero else OG_IMAGE,
            "category": "Plywood, board and timber",
            "brand": {"@type": "Brand", "name": "Cochin Wood Industries"},
            "manufacturer": {"@id": LIVE + "/#organization"}}
    return ('<script type="application/ld+json">'
            + json.dumps(data, separators=(",", ":")) + '</script>')

def base(title, desc, path, body, body_class="", extra_head="", crumbs=None,
         og_type="website", show_crumbs=True, self_url=True):
    canonical = LIVE + path
    page_title = seo_title(title)      # <title> is trimmed; og/twitter keep the full headline
    # A page that shows a real photograph shares that photograph. The generic card
    # is the fallback, not the default -- see hero_image().
    hero = hero_image(path.strip("/"))
    og_image, og_w, og_h = hero if hero else (OG_IMAGE, *OG_IMAGE_SIZE)
    dims = ""
    if og_w and og_h:
        dims = (f'\n<meta property="og:image:width" content="{og_w}">'
                f'\n<meta property="og:image:height" content="{og_h}">')
    # /404 is served at every unknown path AND redirected to / at its own address,
    # so it has no URL of its own to claim: a canonical and an og:url naming /404
    # both point at a 301. noindex says the same thing to a crawler that ignores
    # the status code.
    self_tags = (f'<link rel="canonical" href="{canonical}">'
                 if self_url else '<meta name="robots" content="noindex, follow">')
    og_url_tag = f'\n<meta property="og:url" content="{canonical}">' if self_url else ""
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
{self_tags}
<link rel="icon" type="image/png" sizes="32x32" href="{u('/assets/icons/favicon-32.png')}">
<link rel="icon" type="image/png" sizes="16x16" href="{u('/assets/icons/favicon-16.png')}">
<link rel="apple-touch-icon" href="{u('/assets/icons/apple-touch-icon.png')}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="Cochin Wood Industries">
<meta property="og:locale" content="en_IN">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">{og_url_tag}
<meta property="og:image" content="{og_image}">{dims}
<meta property="og:image:alt" content="Cochin Wood Industries">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{og_image}">
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
<script src="{u('/assets/' + ASSETS['site.js'])}" defer></script>{beacon_tag()}
</body>
</html>'''

_page_source = {}      # output path -> source file it was generated from

# Three accessibility repairs that belong to no single page. Every table, icon
# and separator on this site arrives inside imported HTML -- product snippets,
# export bodies, blog posts -- so there is no one template to fix: the 1,031
# <th> live in ~60 source files and the icons in 26 more. Doing it here, on the
# way out, is the one edit that reaches all of them, and each rule is written so
# that running it twice changes nothing.
#
# The \b is load-bearing: without it "<th" also matches the "<thead>" the header
# cells are nested in, and every table on the site loses its head.
_TH_NO_SCOPE  = re.compile(r'<th\b(?![^>]*\bscope=)([^>]*)>')
_ROW_TH       = re.compile(r'(<tr\b[^>]*>\s*)<th\b(?![^>]*\bscope=)([^>]*)>')
_THEAD        = re.compile(r'<thead\b.*?</thead>', re.S)
# An <svg> that opens a link or a button may be that control's only content, and
# hiding it would leave the control with no name at all. There is none today --
# the WhatsApp float is the one such icon and it is already labelled -- so this
# is a guard against a future one, not a fix for a present one.
_SVG_OPENS_CONTROL = re.compile(r'<(?:a|button)\b[^>]*>\s*$')
_SVG_NO_ARIA       = re.compile(r'<svg\b(?![^>]*\baria-)([^>]*)>')
# The separators the imported heroes draw between meta items: a bullet a screen
# reader otherwise reads aloud between every pair. Same fix the breadcrumb
# separators already carry.
_META_SEP = re.compile(r'<span class="(sep|cw__hero-meta-sep)">')

def a11y_fixups(doc):
    # a <th> in the head names its column; anywhere else it opens its row and
    # names the cells beside it. Both table shapes on this site are covered:
    # .cwg__table has a <thead>, .cwp__table is all row headers.
    doc = _THEAD.sub(lambda m: _TH_NO_SCOPE.sub(r'<th scope="col"\1>', m.group(0)), doc)
    doc = _ROW_TH.sub(r'\1<th scope="row"\2>', doc)
    out, i = [], 0
    for m in _SVG_NO_ARIA.finditer(doc):
        out.append(doc[i:m.start()])
        if _SVG_OPENS_CONTROL.search(doc[max(0, m.start() - 400):m.start()]):
            out.append(m.group(0))     # leave it: it may be the control's name
        else:
            attrs = m.group(1).replace(' focusable="false"', '')
            out.append(f'<svg aria-hidden="true" focusable="false"{attrs}>')
        i = m.end()
    doc = "".join(out) + doc[i:]
    return _META_SEP.sub(r'<span class="\1" aria-hidden="true">', doc)

def write(path, content, src=None):
    # cf-live commits FLAT files -- about.html, export/qatar.html,
    # blogs/post/<slug>.html -- so live answers /about with a direct 200. A
    # <slug>/index.html layout makes Cloudflare Pages answer 308 -> /about/
    # instead: an extra hop on every one of 200+ page views, and an SEO
    # self-contradiction, because every canonical (and the sitemap) names the
    # non-slash form, so each canonical URL would itself redirect. Parity with
    # live's served status codes is restored here, in one place, rather than at
    # nine call sites: every page rendered as <slug>/index.html lands on disk as
    # <slug>.html. Only the site root keeps index.html.
    if path.endswith("/index.html"):
        path = path[:-len("/index.html")] + ".html"
    # The single choke point for the canonical export-market list. Every byte
    # this build emits passes through here, so page copy, meta descriptions and
    # JSON-LD all get the same expansion from the same data with no call site
    # able to forget.
    content = expand_canon(content, path)
    if path.endswith(".html"):
        content = a11y_fixups(content)
    fp = os.path.join(DIST, path)
    os.makedirs(os.path.dirname(fp) or DIST, exist_ok=True)
    # newline pinned: in text mode a Windows build silently CRLFs every emitted
    # byte, so a locally-built dist differs from CI's and from live (both LF).
    with open(fp, "w", encoding="utf-8", newline="\n") as f: f.write(content)
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
    # The nine cards sit inside the "Our plywood range" section, whose own <h2>
    # is their heading -- so each card title is one level below it, not beside
    # it. As <h2> they were 9 of the homepage's 16 H2s and buried the three that
    # actually name sections.
    cards = "".join(
        f'<a class="cw-card" href="{u("/"+s)}"><h3>{n}</h3><p>{d}</p><span class="cw-card__tag">View &rarr;</span></a>'
        for s,n,d in PRODUCTS[:9])
    # The H1 states what the company is; the slogan opens the lede. It was the
    # other way round -- "Plywood, built to your spec." carried the whole
    # heading weight of the homepage while the term the page is actually
    # searched for sat in an eyebrow paragraph, which is not a heading at all.
    body = f'''
<section class="cw-hero"><div class="cw-wrap">
  <h1>Plywood manufacturer in Kochi, Kerala</h1>
  <p>Plywood, built to your spec. Packing-grade, Okoume and film-faced shuttering plywood, sawn timber and export crates — manufactured to Cochin Wood specifications and shipped across India and abroad. Backed by a group manufacturing in Perumbavoor since 1986.</p>
  <div class="cw-hero__cta"><a class="cw-btn cw-btn--p" href="{u('/contact')}">Request a quote</a><a class="cw-btn cw-btn--g" href="{u('/products')}">See the range</a></div>
  <div class="cw-hero__strip">
    <div><b>40+ yrs</b><span>Group manufacturing since 1986</span></div>
    <div><b>Pan-India</b><span>Delivery + export to {N_EXPORT_COUNTRIES} countries</span></div>
    <div><b>IS 710 / 303</b><span>Boil-proof &amp; MR grades</span></div>
  </div>
</div></section>

<section class="cw-sec"><div class="cw-wrap">
  <h2 class="cw-sec__h">Our plywood range</h2>
  <p class="cw-sec__lead">From bulk packing and Okoume panels to marine, shuttering and container-flooring plywood — sized, graded and pressed for the job.</p>
  <div class="cw-grid">{cards}</div>
  <p style="margin-top:24px"><a class="cw-card__tag" href="{u('/products')}">All 16 product lines &rarr;</a></p>
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
        "Plywood Manufacturer & Exporter in India | Cochin Wood",
        "Marine, shuttering, packing and Okoume plywood from the Cochin Wood group in Perumbavoor, Kerala — factory-direct, pan-India delivery and export.",
        "/", body))

# ---------------- PRODUCTS ----------------
def products():
    cards = "".join(
        f'<a class="cw-card" href="{u("/"+s)}"><h2>{n}</h2><p>{d}</p><span class="cw-card__tag">View &rarr;</span></a>'
        for s,n,d in PRODUCTS)
    # Same swap as the homepage: the H1 names the page ("Plywood catalogue"),
    # the label that used to be the eyebrow is gone and the old H1 opens the
    # lede. The cards keep their <h2> here -- on this page they ARE the
    # sections, sitting directly under the H1 with no section heading above
    # them, which is not true of the homepage.
    body = f'''
<section class="cw-sec"><div class="cw-wrap">
  <h1 class="cw-sec__h" style="font-size:clamp(1.9rem,4vw,2.8rem)">Plywood catalogue — marine, shuttering, packing and more</h1>
  <p class="cw-sec__lead">Plywood, board &amp; timber. Sixteen product lines, each manufactured to Cochin Wood specifications. Tell us the grade, thickness and quantity and we'll quote.</p>
  <div class="cw-grid">{cards}</div>
</div></section>
<section class="cw-band"><div class="cw-wrap cw-band__in">
  <div><h2>Not sure which grade you need?</h2><p>Send the application and destination — we'll recommend the panel and price it.</p></div>
  <a class="cw-btn cw-btn--p" href="{u('/contact')}">Request a quote</a>
</div></section>'''
    # Every one of the sixteen product pages describes itself as a Product and the
    # page that indexes them said nothing at all, so nothing in the markup joined
    # them into one catalogue. Names and URLs only, in the editorial order the
    # cards are drawn in, and read from PRODUCTS -- the same list the cards come
    # from, so the schema and the page cannot fall out of step. No prices here for
    # the same reason product_schema() gives none: there are none to state.
    ld = ('<script type="application/ld+json">' + json.dumps(
            {"@context": "https://schema.org", "@type": "ItemList",
             "name": "Plywood catalogue",
             "itemListOrder": "https://schema.org/ItemListOrderAscending",
             "numberOfItems": len(PRODUCTS),
             "itemListElement": [{"@type": "ListItem", "position": i + 1,
                                  "name": html.unescape(n), "url": LIVE + "/" + s}
                                 for i, (s, n, _d) in enumerate(PRODUCTS)]},
            separators=(",", ":")) + '</script>')
    write("products/index.html", base(
        "Plywood Catalogue — Marine, Shuttering, Packing & More | Cochin Wood",
        # Leads with packing and Okoume because they lead the catalogue now; the
        # old text listed neither and ran to 187 rendered characters, past where
        # Google truncates a description.
        "Cochin Wood Industries' plywood catalogue: packing, Okoume, commercial, marine (IS 710), film-faced shuttering, BWR hardwood and sawn timber.",
        "/products", body, crumbs=[("Home", "/"), ("Products", None)], extra_head=ld))

# ---------------- CONTACT ----------------
# (posted value, visible label). The VALUE is what the Worker stores, so it is the live page's
# vocabulary verbatim and not ours to tidy. Live splits BWP marine (IS 710) from BWR hardwood
# (IS 303); the retired CRM webform had one "Premium/ISI/303/710" picklist entry that collapsed the
# two, and the IS 710 / IS 303 distinction was lost on every lead that used it.
PRODUCT_INTEREST = [
    ("Commercial/Packing Grade",      "Commercial / packing-grade ply"),
    ("Wooden/Plywood Packing Case",   "Boxes, crates &amp; pallets"),
    ("Film Faced/Shuttering",         "Film-faced shuttering"),
    ("BWP Marine Plywood - IS 710",   "BWP marine plywood"),
    ("BWR Hardwood Plywood - IS 303", "BWR hardwood plywood"),
    ("Calibrated/Modular",            "Calibrated furniture ply"),
    ("Container Flooring",            "Container flooring"),
    ("Block Board/Flush Door",        "Block board &amp; flush doors"),
    ("Timber/Runners/Planks",         "Sawn timber &amp; runners"),
]

INCOTERMS = ["Delivered within India", "Ex-works Perumbavoor", "FCA Cochin", "FOB Cochin",
             "CFR destination port", "CIF destination port"]

# PUBLIC by design -- a Turnstile sitekey is meant to be read out of the page, and this is the same
# key the live page serves. The matching secret lives only in the Worker (env.TURNSTILE_SECRET) and
# is the only half that decides anything; nothing on this page is trusted by the server on its own.
TURNSTILE_SITEKEY = "0x4AAAAAAEC9o-zON82Wc-NR"

# Ported from the live page (git show origin/cf-live:contact.html). Every branch is load-bearing and
# none of the reasons are guessable from the code alone:
#
#   * cwq2TsFail / the /ts-fail beacon is the ONLY thing that can report Turnstile refusing real
#     buyers. The hourly server-side probe is waved past the Turnstile gate on purpose, and an
#     automated browser is never issued a token, so no server-side check can see this.
#   * The noload block covers what the error-callback cannot: if challenges.cloudflare.com never
#     serves at all, the callback is never registered and the page would report nothing. onerror
#     CALLS noload rather than setting a flag -- the inline block runs in the same task as the async
#     tag above it, so a flag would read undefined every time and the branch would be dead.
#   * The submit gate STOPS a post that has no Turnstile token. Without it the buyer submits, the
#     Worker rejects, and the page still shows "Request received": the success card keys off nothing
#     but ?sent=1, so a server-side rejection has no way to reach the buyer.
#
# NOT ported: live still carries an unreachable `configured = false` WhatsApp-fallback branch that
# reads the retired CRM field names (Last Name / Company / Email / Phone). It cannot run -- the
# endpoint is ours and always answers -- and every field it reads is gone from this form, so
# carrying it across would reimport the exact stale vocabulary this rebuild exists to remove.
QUOTE_JS = r'''<script>
  /* Global because Turnstile resolves the callback by name off window. Says nothing to the buyer
     and returns nothing, so Turnstile's own retry behaviour is left exactly as it was -- this
     reports, it does not interfere. sendBeacon so a page the visitor is leaving still sends it.
     Nothing personal is sent: the error code and nothing else. */
  window.cwq2TsFail = function (code) {
    try {
      var u = 'https://www.cochinwood.in/ts-fail?c=' +
              encodeURIComponent(String(code == null ? 'unknown' : code).slice(0, 24));
      if (navigator.sendBeacon) navigator.sendBeacon(u);
      else fetch(u, { method: 'POST', mode: 'no-cors', keepalive: true });
    } catch (e) { /* a monitor must never break the form it is watching */ }
  };
  /* Fifteen seconds rather than something snappier: the alarm this feeds judges over a day, and a
     buyer on 3G in a yard is a real visitor whose script is merely slow. A false "did not load" is
     worse than a late one. `noload` (conclusive, from onerror) and `noload_to` (a timeout, which an
     ad-blocker also produces) are deliberately different codes -- telling a blocked visitor apart
     from a CDN outage is the server's job, and folding them together would train the alarm to be
     ignored. */
  (function () {
    var sent = false;
    function noload(why) { if (sent) return; sent = true; window.cwq2TsFail(why); }
    window.cwq2TsNoload = function () { noload('noload'); };
    if (window.cwq2TsDead) noload('noload');
    else setTimeout(function () {
      if (window.turnstile) return;                     // it loaded; nothing to report
      noload(window.cwq2TsDead ? 'noload' : 'noload_to');
    }, 15000);
  })();
</script>
<script>
  (function () {
    var f = document.getElementById('cwq2-form');
    if (!f) return;
    var loadedAt = Date.now();

    /* The Worker answers a saved enquiry with a 302 to /contact?sent=1#quote, so this is what the
       buyer sees after submitting. A FAILED save is answered by the Worker's own page instead and
       never redirects here, which is why this branch can assume success. */
    if (/[?&]sent=1/.test(window.location.search)) {
      f.innerHTML = '<div class="cw-form__ok" aria-live="polite">' +
        '<h2>Request received.</h2>' +
        '<p>Our export desk replies within one business day. In a hurry?</p>' +
        '<a class="cw-btn cw-btn--p" href="https://wa.me/919567410175">Message the desk on WhatsApp</a></div>';
      var q = document.getElementById('quote');
      if (q) q.scrollIntoView();
      return;
    }

    f.addEventListener('submit', function (e) {
      var err = document.getElementById('cwq2-error');
      err.style.display = 'none';

      // spam gates: honeypot + minimum fill time
      if (f.querySelector('[name="cwq2_website"]').value || (Date.now() - loadedAt) < 3000) {
        e.preventDefault();
        err.textContent = 'Please review your details and try again.';
        err.style.display = 'block';
        return;
      }

      /* Verification gate. Turnstile's error callback only fires a beacon: it never tells the buyer
         and never blocks the post. Stop before a rejected submission is thanked, say so plainly,
         and offer a channel that always works. */
      var ts = f.querySelector('[name="cf-turnstile-response"]');
      if (!ts || !ts.value) {
        e.preventDefault();
        err.innerHTML = 'Verification has not finished, so this cannot be sent yet. ' +
          'Give it a moment and press the button again — or reach the export desk ' +
          'directly on <a href="https://wa.me/919567410175">WhatsApp</a> or ' +
          '<a href="mailto:sales@cochinwood.in">sales@cochinwood.in</a>.';
        err.style.display = 'block';
        try { err.scrollIntoView({ block: 'center', behavior: 'smooth' }); } catch (x) {}
        return;
      }

      /* Fold the packed fields into description. The Worker reads name, company, email, phone,
         products, destination and description and NOTHING ELSE -- spec_grade, quantity and incoterm
         are posted and dropped on the floor without this, so this loop is the only reason thickness,
         quantity and quote basis reach the lead book at all. */
      var desc = f.querySelector('[name="description"]');
      var extra = [];
      f.querySelectorAll('[data-pack]').forEach(function (el) {
        if (el.value.trim()) extra.push(el.getAttribute('data-pack') + ': ' + el.value.trim());
      });
      var other = f.querySelector('[data-other]');
      if (other && other.checked) extra.push('Product: other / not sure');
      if (extra.length) desc.value = extra.join('\n') + (desc.value ? '\n\n' + desc.value : '');
    });
  })();
</script>'''

def contact():
    checks = "".join(f'<label><input type="checkbox" name="products" value="{v}">{lab}</label>'
                     for v, lab in PRODUCT_INTEREST)
    # NAMED, so the tick survives a native post. This box used to carry data-other and nothing else,
    # which made it the one product answer that existed only if JavaScript ran: the packer in
    # QUOTE_JS folds it into `description`, so with JS blocked, broken or still parsing, the buyer
    # ticked a box that reached nobody and got the ordinary thank-you for it.
    # `products` is the name the other nine post under, and the Worker joins every repeat of it into
    # one "Products:" line (api-worker.js webLead(), the gAll() helper) -- free text at that end, not
    # a picklist, so an unrecognised value cannot fail a lead. The nine chips joined are 223
    # characters against the Worker's 300-char cap and this adds 18, so a buyer who ticks everything
    # is still not truncated. data-other stays for the packer, whose line is now belt-and-braces
    # rather than the only carrier.
    checks += ('<label><input type="checkbox" name="products" value="Other / not sure" data-other>'
               'Other / not sure</label>')
    incoterms = "".join(f"<option>{i}</option>" for i in INCOTERMS)
    # ABSOLUTE, not root-relative, and matched by tools/check_site.py. The Worker is bound to
    # www.cochinwood.in/web-lead and cochinwood.in/web-lead as explicit routes; a plain form POST is
    # a top-level navigation and not subject to CORS, so this keeps working from a preview origin
    # (the buyer simply lands back on the production contact page).
    #
    # THE TEN TICK BOXES ARE ONE QUESTION, so they are one <fieldset> with a <legend> that says
    # which. They used to sit in a plain <div> under an orphan <label> -- a <label> with no `for`
    # and no control inside it labels nothing at all -- and with no role=group or aria-labelledby
    # anywhere else on the page, so a screen reader announced ten unrelated checkboxes and never
    # said what the group was asking. The inline reset is not decoration: a fieldset arrives with a
    # 2px groove border, its own side margins and padding, and a min-width of min-content that can
    # stop this grid column shrinking on a phone. The legend repeats by hand what `.cw-form label`
    # already gives every other question, because that rule selects labels and a legend is not one.
    #
    # And the asterisk is explained once, above the fields it applies to: seven labels carry one and
    # nothing on the page said what it meant.
    form = f'''<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer onerror="window.cwq2TsDead=1;window.cwq2TsNoload&amp;&amp;window.cwq2TsNoload()"></script>
<form class="cw-form" id="cwq2-form" method="POST" action="https://www.cochinwood.in/web-lead" accept-charset="UTF-8">
  <!-- honeypot: real buyers never see this -->
  <div class="cw-hp" aria-hidden="true"><label for="q-web">Leave this field empty</label><input id="q-web" type="text" name="cwq2_website" tabindex="-1" autocomplete="off"></div>
  <p class="cw-note" style="margin:0">Fields marked * are required.</p>
  <div class="cw-row">
    <div><label for="q-name">Name *</label><input id="q-name" type="text" name="name" autocomplete="name" required></div>
    <div><label for="q-co">Company *</label><input id="q-co" type="text" name="company" autocomplete="organization" required></div>
  </div>
  <div class="cw-row">
    <div><label for="q-em">Work email *</label><input id="q-em" type="email" name="email" autocomplete="email" required></div>
    <div><label for="q-ph">WhatsApp / phone *</label><input id="q-ph" type="tel" name="phone" autocomplete="tel" required></div>
  </div>
  <fieldset style="border:0;margin:0;padding:0;min-width:0"><legend style="font-size:.86rem;font-weight:600;color:var(--cw-green-800);margin:0 0 6px;padding:0">What do you need?</legend><div class="cw-checks">{checks}</div></fieldset>
  <div class="cw-row">
    <div><label for="q-spec">Thickness / grade *</label><input id="q-spec" type="text" name="spec_grade" placeholder="e.g. 18 mm BWP, IS 710" data-pack="Thickness / grade" required></div>
    <div><label for="q-qty">Quantity *</label><input id="q-qty" type="text" name="quantity" placeholder="e.g. 2 &times; 40ft containers" data-pack="Quantity" required></div>
  </div>
  <div class="cw-row">
    <div><label for="q-port">Delivery city / destination port *</label><input id="q-port" type="text" name="destination" placeholder="e.g. Kochi, or Jebel Ali, UAE" required></div>
    <div><label for="q-inco">Quote basis</label><select id="q-inco" name="incoterm" data-pack="Quote basis"><option value="">Not sure — advise me</option>{incoterms}</select></div>
  </div>
  <div><label for="q-msg">Anything else</label><textarea id="q-msg" name="description" placeholder="Sizes, monthly volume, timing…"></textarea></div>
  <div class="cf-turnstile" data-sitekey="{TURNSTILE_SITEKEY}" data-theme="light" data-error-callback="cwq2TsFail" style="margin:0 0 14px"></div>
  <p class="cw-form__err" id="cwq2-error" role="alert"></p>
  <div><button class="cw-btn cw-btn--p" type="submit">Send enquiry</button>
  <p class="cw-note" style="margin:10px 0 0">Goes straight to our sales desk. We reply within one business day.</p></div>
</form>
{QUOTE_JS}'''
    # id="quote" lives on the SECTION, exactly as live has it: ~20 pages link to /contact#quote, and
    # the Worker's own 302 target ends in #quote. It used to sit on the <form>, which the success
    # handler replaces the innards of -- and getElementById('quote').scrollIntoView() has to survive
    # that swap to put the confirmation in front of the buyer.
    #
    # THE PAGE NOW IDENTIFIES THE SELLER. A buyer asked for a 50% advance reads /contact before
    # anything else, and it carried a phone number, an email and a town: no street address, no
    # GSTIN, no CIN and no route to /company-verification, which is where all of that is already
    # published and checkable on the MCA and GST portals. GSTIN and CIN are the constants copied
    # from that page, not new claims, and the heading matches its wording -- "principal place of
    # business", which is what the GST certificate calls this address. No opening hours: none have
    # been given, and inventing them here would be the same defect in a new place.
    # The registration line is styled inline because .cw-note is only dressed by `.cw-form .cw-note`
    # and this paragraph sits outside the form.
    body = f'''
<section class="cw-sec" id="quote"><div class="cw-wrap" style="max-width:820px">
  <p class="cw-hero__ey" style="color:var(--cw-green-600)">Get in touch</p>
  <h1 class="cw-sec__h" style="font-size:clamp(1.9rem,4vw,2.8rem)">Request a quote</h1>
  <p class="cw-sec__lead">Tell us the product, grade, thickness, quantity and delivery location — we reply within one business day with a price and lead time.</p>
  <div class="cw-feat" style="margin-bottom:8px">
    <div><h2>WhatsApp / Phone</h2><p><a href="tel:{CONTACT['phone_href']}">{CONTACT['phone_disp']}</a></p></div>
    <div><h2>Email</h2><p><a href="mailto:{CONTACT['email']}">{CONTACT['email']}</a></p></div>
    <div><h2>Principal place of business</h2><p>{CONTACT['addr']}</p></div>
  </div>
  <p class="cw-note" style="margin:0 0 18px;font-size:.82rem;color:var(--cw-ink-600,#4A4A4A)">Cochin Wood Industries Private Limited &middot; GSTIN {GSTIN} &middot; CIN {CIN} &middot; <a href="{u('/company-verification')}">Verify our registrations</a></p>
  {form}
</div></section>'''
    write("contact/index.html", base(
        "Request a Plywood Quote · Cochin Wood Industries",
        "Contact Cochin Wood Industries, Perumbavoor, Ernakulam, Kerala. WhatsApp/phone +91 95674 10175 or sales@cochinwood.in for plywood quotes, pan-India and export.",
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
        warn(f"cannot read a species name out of {title[:60]!r}")
        return title.split(":")[0].strip(), ""
    return m.group(1).strip(), m.group(2).strip()

# One formula for all 28 species <title> tags. Half of them used to reach the
# search results with words their own og:title still carried, because eight are
# longer than TITLE_MAX and seo_title()'s generic shortener picked a different
# casualty on each: "Wood" and "Density" on rubberwood, the BOTANICAL NAME on
# matti and pala -- the one thing a species page is looked up by. Deciding the
# trim order here means every species is trimmed the same way, and because the
# result already fits, seo_title() passes it through untouched and og:title (the
# same string) can no longer say something the <title> does not.
SPECIES_TITLE_TAIL = ": Properties, Density & Uses"

def species_title(raw):
    """'<Common name> Wood (<Botanical>): Properties, Density & Uses'.

    Trimmed, in this order, only as far as it must be to fit TITLE_MAX: the
    doubled word where the common name already ends in "wood" (Rubberwood,
    Jackwood); then the second common name in brackets ("Anjili (Wild Jack)"
    -> "Anjili"), which is the only part no one searches on its own; then
    ", Density". The botanical name is never dropped."""
    name, sci = _species_names(raw)
    if not sci:
        return raw                       # _species_names() has already warned

    def build(n, tail):
        # "Rubberwood Wood", "Jackwood Wood" -- the source titles say it twice
        return f'{n}{"" if n.lower().endswith("wood") else " Wood"} ({sci}){tail}'

    alias_free = re.sub(r'\s*\([^()]*\)\s*$', '', name)
    for cand in (build(name, SPECIES_TITLE_TAIL),
                 build(alias_free, SPECIES_TITLE_TAIL),
                 build(alias_free, ": Properties & Uses")):
        if len(cand) <= TITLE_MAX:
            return cand
    warn(f"species title is {len(cand)} chars after every trim: {cand}")
    return cand

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

def wave3_article_ld(entry, src, title):
    """The Article + about:Thing block a wave-3 page has no way to carry itself.

    All twenty wave-1/2 species ship one inside the page they are imported from.
    The eight fragments are body-only and carry nothing but their FAQPage, so
    eight of the twenty-eight species reached a machine reader as an untyped
    page -- the same content, described as if it were nothing in particular.

    Built from the two sources the page itself is built from, so it cannot state
    something the page does not: the headline is the <title> as emitted, the
    description is the meta description, and the Thing is the botanical name the
    hero already prints. The org @id is the one ORG_SCHEMA defines on every page.

    NO datePublished: posts3.json records none, and inventing one would put a
    false date on a data sheet. The one date this repository does know is when
    the fragment last changed, which is dateModified and which comes from the
    same git_date() the sitemap's <lastmod> uses -- so the two can never
    disagree about the same file."""
    # _SCI_RE directly rather than _species_names(): this title has already been
    # through that function twice by the time we get here, and a third pass would
    # only repeat its warning on a species it cannot read a name out of.
    m = _SCI_RE.match(html.unescape(entry["title"]))
    data = {"@context": "https://schema.org", "@type": "Article",
            "headline": html.unescape(title),
            "description": html.unescape(entry["summary"]),
            "dateModified": git_date(src),
            "author":    {"@id": LIVE + "/#organization"},
            "publisher": {"@id": LIVE + "/#organization"},
            "mainEntityOfPage": f"{LIVE}{WOOD_PATH}/{entry['file']}"}
    if m:
        data["about"] = {"@type": "Thing", "name": m.group(2).strip()}
    return ('<script type="application/ld+json">'
            + json.dumps(data, separators=(",", ":")) + '</script>')

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
        # both waves state the title the same way, and short enough that
        # seo_title() has nothing left to cut -- see species_title()
        title = species_title(title)
        body = enc_rewrite(body)
        # The twenty imported pages bring their own Article+Thing with them; the
        # eight fragments cannot, so theirs is emitted here. All 28 carry one.
        art = wave3_article_ld(entry, src, title) if sub == "encyclopedia-wave3" else ""
        write(f"{WOOD_PATH.strip('/')}/{f}/index.html", src=src, content=
              base(title, desc, f"{WOOD_PATH}/{f}", body, body_class="cw-encbody",
                   show_crumbs=False, extra_head=art,
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

_LD_BLOCK = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

def faq_ld(raw, where):
    """The FAQPage block out of an imported page body, ready for extra_head.

    Parsed and re-serialised rather than copied across: a block that does not
    parse would ship as broken JSON-LD on a live page with nothing to say so,
    and this turns that into a build warning instead. The {{CWI_...}} tokens
    inside it survive the round trip as text -- write() expands them on the way
    out like every other byte this build emits."""
    for m in _LD_BLOCK.finditer(raw):
        if '"FAQPage"' not in m.group(1):
            continue
        try:
            data = json.loads(m.group(1))
        except ValueError as e:
            warn(f"{where}: its FAQPage block is not valid JSON ({e}) -- the page "
                 f"ships with no FAQ schema")
            return ""
        return ('<script type="application/ld+json">'
                + json.dumps(data, separators=(",", ":")) + '</script>')
    warn(f"{where}: no FAQPage block in the source -- the page ships with no FAQ schema")
    return ""

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
        raw = open(fp, encoding="utf-8").read()
        content = process_content(raw, slug)
        title = meta.get("title") or slug.replace("-", " ").title() + " | Cochin Wood Industries"
        desc  = meta.get("desc") or ""
        body = f'<main class="cw-page"><div class="cw-wrap">{content}</div></main>'
        pname = dict((s, n_) for s, n_, _ in PRODUCTS).get(slug)
        if pname:
            crumbs = [("Home", "/"), ("Products", "/products"), (pname, None)]
        else:
            crumbs = [("Home", "/"), (title.split("|")[0].strip(), None)]
        # /faq's own FAQPage block has been in the source file since the page was
        # ported and has never reached a built page: process_content() strips every
        # <script> out of an imported body, and that strip stays -- it is what keeps
        # the live product snippets' Product blocks (the invalid ones, offers with
        # no price, that product_schema() was written to replace) off the product
        # pages. So the one block worth keeping is lifted into the head instead,
        # matched by type and only on the page whose thirteen answers it states.
        extra = product_schema(slug) if pname else ""
        if slug == "faq":
            extra += faq_ld(raw, "/" + slug)
        write(f"{slug}/index.html", src=os.path.join("content","pages",fname), content=base(title, desc, "/"+slug, body,
              body_class="cw-contentpage", crumbs=crumbs, extra_head=extra))
        n += 1
    return n

# ---------------- /about buyer FAQ ----------------
#
# Eleven answered buyer questions and their FAQPage rich-result eligibility. Live
# carries them twice -- a visible accordion AND a static FAQPage block -- and the
# two texts are NOT the same on 7 of the 11. Both are commercial and technical
# commitments (payment terms, lead-times, BIS licence wording, ISPM-15), so both
# are carried across verbatim rather than one being reworded into the other:
# `a` is what a buyer reads, `schema` is what Googlebot reads, exactly as live
# serves them. Where the item has no `schema` key the two agree and the schema
# text is derived from `a`; `schema: null` marks the one question live displays
# but never listed in its FAQPage block.
#
# THE ONE ANSWER THAT IS NOT TYPED OUT HERE is "Which export markets do you
# currently ship to?". Live answers it twice and the two disagree -- the visible
# list named Bangladesh, Malaysia, Singapore, Vietnam, Maldives, Mauritius,
# Tanzania, Australia, Germany and the UK and no Americas at all, while the
# JSON-LD named the GCC, Turkey, three African markets, the Netherlands, four
# North American markets and Chile. On 1 Sep 2026 the JSON-LD list was picked
# and written into content/about-faq.json (commit 4e9f3253); Edwin overruled that
# on 2 Sep 2026 -- the visible list was the MORE complete of the two, and Israel
# and Vietnam were on neither, so the truth is the union of both plus those two:
# 28 countries across six continents.
#
# So the answer is no longer typed into content/about-faq.json at all. Both its
# visible and its schema copy carry {{CWI_EXPORT_MARKETS}}, which write() expands
# from content/export-markets.json -- one list, one place, and the page cannot
# contradict itself because both halves are the same substitution.
# tools/check_site.py derives the continent count from this answer's own words
# and enforces it against every page's copy; moving the number without the list,
# or the list without the number, is what that check exists to stop.
#
# Presentation is the build's own .cwg__faq/.cwg__faq-item, already in the CSS
# bundle and already used by the nine /export lanes -- for the reason
# export_section.py gives: live's .cw__about-faq-* classes came from the Zoho
# theme and do not exist here, and its accordion ran on an inline <script> that
# process_content strips. Nothing new is invented for one page.
ABOUT_FAQ_SRC = os.path.join("content", "about-faq.json")

def _faq_text(frag):
    """Visible text of an HTML fragment, for JSON-LD. Same rule export_section uses."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", frag))).strip()

def about_faq():
    """(visible section html, FAQPage ld+json) for /about, from one data file."""
    fp = os.path.join(ROOT, ABOUT_FAQ_SRC)
    if not os.path.exists(fp):
        warn(f"/about has no FAQ: {ABOUT_FAQ_SRC} is missing -- eleven answered buyer "
             f"questions and their FAQPage rich-result eligibility would go silently")
        return "", ""
    d = json.load(open(fp, encoding="utf-8"))
    items = d.get("items") or []
    if not items:
        warn(f"{ABOUT_FAQ_SRC} lists no questions")
        return "", ""

    blocks, entities = [], []
    for it in items:
        q, paras = it["q"], it["a"]
        blocks.append('<div class="cwg__faq-item"><h3>' + q + "</h3>"
                      + "".join(f"<p>{p}</p>" for p in paras) + "</div>")
        if "schema" in it and it["schema"] is None:
            continue                       # displayed on the page, never in the block
        # RAW text for the block. `q` and a hand-written `schema` are both HTML
        # source -- they go into the visible markup above as-is -- so they are
        # unescaped here; _faq_text already unescapes what it derives.
        text = html.unescape(it["schema"]) if it.get("schema") else _faq_text(" ".join(paras))
        entities.append({"@type": "Question", "name": html.unescape(q),
                         "acceptedAnswer": {"@type": "Answer", "text": text}})

    # Google's FAQPage rule is that the answer must appear on the page. The two
    # texts are allowed to differ in wording; a fact stated only in the schema is
    # a page contradicting itself, which is what check_site.py's faq-answer check
    # fails on. Catch it here too, at the source, rather than only in the checker.
    visible = _faq_text(" ".join(b for b in blocks))
    for e in entities:
        for tok in re.findall(r"\b(?:IS|ISO|ISPM|IICL)[ -]?\d[\w-]*\b",
                              e["acceptedAnswer"]["text"]):
            if tok not in visible:
                warn(f'/about FAQ: the schema answer to "{e["name"][:48]}" states {tok}, '
                     f"which the visible answer does not -- Googlebot would read a fact "
                     f"a buyer cannot see")

    html_out = ('<section class="cwg__faq"><div class="cwg__container">'
                f'<p class="cwg__eyebrow">{d["eyebrow"]}</p><h2>{d["h2"]}</h2>'
                f'<p class="cw__lede">{d["lede"]}</p>' + "".join(blocks) + "</div></section>")
    ld = ('<script type="application/ld+json">'
          + json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                        "mainEntity": entities},
                       separators=(",", ":"), ensure_ascii=False) + "</script>")
    return html_out, ld

def build_about():
    sdir = os.path.join(ROOT, "content", "pages")
    parts = []
    for f in ("about-history.html", "about-operation.html"):
        fp = os.path.join(sdir, f)
        if os.path.exists(fp): parts.append(process_content(open(fp, encoding="utf-8").read()))
        else: warn(f"/about is missing its {f} section -- content/pages/{f} not found")
    if not parts: return 0
    meta = PAGE_META.get("about", {})
    faq_html, faq_ld = about_faq()
    # The page opens on the "Our history" section label, so it carried no <h1> at
    # all — the only page on the site without one. The heading is hidden rather
    # than drawn so the layout is untouched.
    h1 = '<h1 class="cw-sr-only">About Cochin Wood Industries</h1>'
    body = (f'<main class="cw-page"><div class="cw-wrap">{h1}{"".join(parts)}</div>'
            f'{faq_html}</main>')
    write("about/index.html", src=os.path.join("content","pages","about-operation.html"), content=base(meta.get("title","About Cochin Wood Industries"),
          meta.get("desc",""), "/about", body, body_class="cw-contentpage",
          crumbs=[("Home", "/"), ("About", None)], extra_head=faq_ld))
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
                # RAW, not the escaped `short` used for the visible H1: json.dumps
                # escapes for JSON itself, so an '&amp;' carried in from posts.json
                # would ship inside the headline a crawler reads.
                "headline": html.unescape(title.split("|")[0].strip()),
                "description": html.unescape(desc or ""),
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

# Live serves /sitemap.xml as an INDEX referencing /sitemap-cms.xml and
# /sitemap-post.xml, both 200 (measured on cf-live, 31 Aug 2026). Google's
# cached copy of that index keeps requesting the children after cutover, and
# with _redirects at 99 of Cloudflare's 100 rules a redirect per child is not
# on the table -- so the build emits the same three files instead of one flat
# urlset. Split exactly as live splits: blog posts under /blogs/post/ go in
# -post, every other page in -cms; each URL appears in exactly one child.
# The children carry <loc> + a truthful git-dated <lastmod>. Live's Zoho-era
# <priority>/<changefreq> are not reproduced: they were per-page settings of an
# engine that no longer builds this site, unrecoverable for pages Zoho never
# had, and Google documents both fields as ignored.
def build_sitemap():
    paths = []
    for r, _, fs in os.walk(DIST):
        for f in fs:
            if not f.endswith(".html"): continue
            rel = os.path.relpath(os.path.join(r, f), DIST).replace(os.sep, "/")
            if rel == "404.html": continue    # the error page: C-22 sends /404 home
            paths.append("/" if rel == "index.html" else "/" + rel[:-len(".html")])
    paths = sorted(set(paths))
    def lastmod(path):
        rel = path.strip("/")
        return git_date(_page_source.get((rel + ".html") if rel else "index.html", "build.py"))
    XMLNS = ('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
             'xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 '
             'http://www.sitemaps.org/schemas/sitemap/0.9/{}" '
             'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"')
    def child(name, ps):
        items = "\n".join(f"  <url><loc>{LIVE + p}</loc><lastmod>{lastmod(p)}</lastmod></url>"
                          for p in ps)
        write(name, '<?xml version="1.0" encoding="UTF-8"?>\n'
              f'<urlset {XMLNS.format("sitemap.xsd")}>\n' + items + '\n</urlset>\n')
        return max((lastmod(p) for p in ps), default=datetime.date.today().isoformat())
    posts = [p for p in paths if p.startswith("/blogs/post/")]
    cms   = [p for p in paths if not p.startswith("/blogs/post/")]
    lm_cms, lm_post = child("sitemap-cms.xml", cms), child("sitemap-post.xml", posts)
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
          f'<sitemapindex {XMLNS.format("siteindex.xsd")}>\n'
          f'  <sitemap><loc>{LIVE}/sitemap-cms.xml</loc><lastmod>{lm_cms}</lastmod></sitemap>\n'
          f'  <sitemap><loc>{LIVE}/sitemap-post.xml</loc><lastmod>{lm_post}</lastmod></sitemap>\n'
          '</sitemapindex>\n')
    return f"{len(paths)}({len(cms)}cms+{len(posts)}post)"

def copy_referenced_files():
    copied = 0
    for ref, src in sorted(_files_used.items()):
        dst = os.path.join(DIST, urllib.parse.unquote(ref.lstrip("/")))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        copy_lf(src, dst); copied += 1
    return copied

# ---------------- what cf-live serves that no new page links ------------------
# THE REBUILD IS A REPLACEMENT FOR A SITE THAT IS ALREADY INDEXED, so "no page in
# the new build links this" is not the same question as "nothing on the internet
# asks for this". Measured against origin/cf-live: dropping the .html filter from
# both sides of the preflight's coverage check turns a green "293/293 covered"
# into 328 live URLs that would 404, and every one of the 328 is a non-HTML file
# the old check could not see. The 301 of them handled here are:
#
#   306 under /files/  -- the product, factory and process photography. Google
#        Images has these paths indexed, the app and third-party listings hotlink
#        them, and cf-live serves them with Access-Control-Allow-Origin: *. Nine
#        are also emitted by copy_referenced_files() below; the other 297 have no
#        referrer inside this build at all, which is exactly why they were lost.
#   4 root files, each of which fails in its own way if it goes missing:
#        see CARRIED_ROOT_FILES for the reason on each one.
#
# Carried from the git object store rather than from a working directory, so the
# bytes are cf-live's bytes and the build stays reproducible on a fresh clone.
#
# THE REF THAT SUPPLIES 311 OF THIS BUILD'S 607 FILES IS PINNED TO A COMMIT, NOT
# TO A BRANCH NAME. "origin/cf-live" is only ever as fresh as the last `git
# fetch`, and the checkouts on this machine are not fresh: the local cf-live is
# d38bacd4, 25 commits behind origin/cf-live's c59adae9. Building against the
# stale one was measured, not imagined -- it exits 0, raises no warning, and
# prints a NUMERICALLY IDENTICAL banner (253 pages, 311 carried, 607 files, 79
# redirects in the window), so nothing an operator reads tells them apart. The
# two dist/ trees differ in exactly one file, .github/workflows/site-checks.yml,
# and the stale copy of it is the PRE-HARDENING workflow that fetches
# check_site.py from origin/master at run time instead of running the pinned
# CHECKER_SHA=4678a8f5139bd1499f1d5f3a4d75071321ce2ffd. So an unfetched operator
# publishes an older, unpinned deploy gate while every preflight check reports
# green -- the exact class of silent wrong answer the preflight exists to catch.
# A build that draws a third of its bytes from a ref has to name that ref's
# commit, in the banner and in the published tree, or it cannot be reproduced.
#
# BUMPING THIS PIN IS A REVIEW, NOT AN EDIT. tools/cutover_preflight.py fails
# when this sha is not what origin/cf-live resolves to, and the answer to that
# failure is to re-review the 311 carried files against the new tip -- pasting
# the new sha in here until the gate goes green carries whatever landed on
# cf-live meanwhile into production unread.
LIVE_REF_NAME = "origin/cf-live"                         # where the pin came from
LIVE_SHA = "c59adae9ee7d4d31a1a62e9dc770579214584e56"    # origin/cf-live, read 4 Sep 2026
LIVE_REF = LIVE_SHA                # what git is actually handed, so no fetch can move it
LIVE_PIN = LIVE_REF_NAME + "@" + LIVE_SHA[:12]           # what the banner and dist/ record

CARRIED_ROOT_FILES = {
    "015ad99674249c7dc418af21415b06bc.txt":
        "THE INDEXNOW KEY (commit 004a8020). IndexNow verifies ownership by "
        "fetching this exact path and checking the body equals the filename, so "
        "it is the one file here a 301 cannot stand in for -- a redirect fails "
        "verification and every submission to Bing, Yandex and Seznam stops "
        "silently, with the site still looking fine.",
    "llms.txt":
        "11,918 bytes of hand-written copy that exists nowhere else in this "
        "repo. dist/llms.html is a different artifact and does not cover it: AI "
        "crawlers fetch /llms.txt by convention, and robots.txt here goes out of "
        "its way to court them with 19 named Allow blocks.",
    "favicon.png":
        "the root favicon browsers and feed readers request by convention even "
        "when the <link rel=icon> tags point elsewhere. Copied to its old path "
        "rather than redirected because a copy costs no redirect slot.",
    "cwi-og-share-1200x630.png":
        "THE SITE-WIDE og:image on 283 of cf-live's 293 pages. Every share card "
        "already sitting in a WhatsApp thread, a LinkedIn post or a Slack "
        "unfurl points at this path; losing it turns those into blank cards. "
        "The rebuild's own pages use /assets/og/<same file>, so this is the old "
        "path kept alive alongside the new one.",
}

# Blocker 5: the required check ships WITH the artifact, not beside it.
# cf-live's required status check "The site says one thing" is defined by this
# file, and the file exists on no other ref. The cutover replaces the tracked
# tree with dist/ wholesale, so a dist/ without .github DELETES the workflow on
# the publishing push: the check cannot run on that push, and because every
# later publish repeats the same replace, it never runs again -- the gate
# removes itself and nothing reports that it has. Copying it in here makes the
# gate part of the build output, so no runbook step and no tired operator at
# 11pm on cutover night can leave it out. It is hidden from visitors by the
# /.github/* 301 in PORTED_REDIRECTS, which is measured to work: probed on the
# live site 4 Sep 2026, www.cochinwood.in/.github/workflows/site-checks.yml
# answers 301 -> / with the file committed on cf-live. The noindex/no-store
# block in _headers is the second layer behind it, not the primary one.
CARRIED_WORKFLOW = ".github/workflows/site-checks.yml"

def _live_tree(prefix):
    """{path: bytes} for every blob under `prefix` on LIVE_REF.

    RAW OBJECT BYTES, NOT A CHECKOUT. `git archive` and `git checkout` both run
    the eol filters, so on a Windows machine with core.autocrlf=true they hand
    back llms.txt 124 bytes longer than the blob and site-checks.yml 59 bytes
    longer -- CRLF where cf-live serves LF. That is a wrong answer twice: the
    file stops matching what production serves, and the build stops being
    deterministic across platforms, which is the one property the preflight's
    byte-for-byte comparison is built on. `cat-file --batch` bypasses the
    filters. -z on ls-tree keeps the paths intact: 306 of these live under
    "files/Process Illustrations/" and friends, with spaces in every one."""
    import subprocess
    ls = subprocess.run(["git", "ls-tree", "-r", "-z", LIVE_REF, "--", prefix],
                        cwd=ROOT, capture_output=True, timeout=300)
    if ls.returncode != 0 or not ls.stdout:
        return None
    entries = []
    for rec in ls.stdout.split(b"\0"):
        if not rec: continue
        meta, path = rec.split(b"\t", 1)
        _mode, typ, sha = meta.split(b" ")
        if typ == b"blob":
            entries.append((sha.decode("ascii"), path.decode("utf-8")))
    if not entries:
        return None
    cat = subprocess.run(["git", "cat-file", "--batch"], cwd=ROOT, timeout=300,
                         input=("".join(s + "\n" for s, _ in entries)).encode("ascii"),
                         capture_output=True)
    if cat.returncode != 0:
        return None
    out, buf, i = {}, cat.stdout, 0
    for _sha, path in entries:
        nl = buf.index(b"\n", i)
        size = int(buf[i:nl].split(b" ")[2])
        out[path] = buf[nl + 1: nl + 1 + size]
        i = nl + 1 + size + 1          # trailing newline git adds after each blob
    return out

def _check_live_pin():
    """Say out loud when the pinned commit is absent, or when cf-live has moved.

    A MISSING PIN AND A MOVED PIN FAIL IN OPPOSITE DIRECTIONS, so they are worth
    separating. If the object is not in this clone the carry silently drops all
    311 files and the preflight's coverage check turns 620/620 into 309/620 --
    loud, and the operator only needs `git fetch origin`. If the object IS here
    but origin/cf-live has moved past it, everything still builds and the build
    is still reproducible; what has changed is that the 311 carried files are no
    longer what production serves, and only a human comparing the two trees can
    say whether that matters. The preflight turns that second case into a hard
    failure; this warning is here so the build itself does not look innocent."""
    import subprocess
    have = subprocess.run(["git", "rev-parse", "--verify", "--quiet",
                           LIVE_SHA + "^{commit}"],
                          cwd=ROOT, capture_output=True, text=True)
    if have.returncode != 0 or have.stdout.strip() != LIVE_SHA:
        warn(f"the pinned live commit {LIVE_SHA[:12]} is not in this clone, so "
             f"all 311 carried files -- the 306 /files/ photos, the 4 root files "
             f"and the required-check workflow -- are about to be skipped. Run "
             f"`git fetch origin` and rebuild")
        return
    tip = subprocess.run(["git", "rev-parse", "--verify", "--quiet", LIVE_REF_NAME],
                         cwd=ROOT, capture_output=True, text=True)
    now = tip.stdout.strip()
    if tip.returncode == 0 and now and now != LIVE_SHA:
        warn(f"{LIVE_REF_NAME} is now {now[:12]}, but this build is pinned to "
             f"{LIVE_SHA[:12]} and carried 311 files from it. That is not drift "
             f"to paper over: re-review what landed on cf-live in between before "
             f"moving LIVE_SHA, because those 311 files publish unread otherwise")


def carry_live_assets():
    """Put cf-live's non-HTML files into dist/ so cutover breaks no old URL."""
    _check_live_pin()
    n = 0
    for prefix, label in (("files", "media"),
                          (CARRIED_WORKFLOW, "the required-check workflow")):
        blobs = _live_tree(prefix)
        if blobs is None:
            warn(f"cannot read {label} from {LIVE_PIN} -- `git fetch origin` and "
                 f"rebuild. Publishing this dist/ as it stands 404s every "
                 f"/{prefix} URL cf-live serves today")
            continue
        for rel, data in sorted(blobs.items()):
            fp = os.path.join(DIST, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, "wb") as f: f.write(lf(data))
            n += 1
    for rel, _why in sorted(CARRIED_ROOT_FILES.items()):
        blobs = _live_tree(rel)
        if not blobs:
            warn(f"{rel} is not on {LIVE_PIN}: cf-live serves it today and this "
                 f"build would 404 it -- see CARRIED_ROOT_FILES for what that "
                 f"costs")
            continue
        with open(os.path.join(DIST, rel), "wb") as f: f.write(lf(blobs[rel]))
        n += 1
    return n

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
# page's own URL is sent home instead. FIRST IN THE FILE ON PURPOSE -- and, since
# it sits above the first wildcard rule, it is outside the 100-rule window
# entirely, so no number of additions below can push it off the end.
/404 / 301

# The 21 doubled-segment URLs from GSC, consolidated to one wildcard. cf-live's
# file said Pages "silently drops the :splat form" here; re-measured 31 Aug 2026
# on the throwaway project cwi-redirect-lab (fixture deployment
# adcd5f41.cwi-redirect-lab.pages.dev): two cache-busted passes a minute apart,
# on both the project URL and the pinned deployment URL, and every :splat form
# was honoured verbatim -- including this exact doubled-segment trailing-* form,
# with the splat spanning slashes. The August negative was the stale-edge-cache
# confound a later commit already suspected. GSC_DOUBLED_SLUGS in build.py still
# pins all 21 known sources: the build verifies each one's target is a page it
# emits, so the per-slug guarantee survives the consolidation. The wildcard also
# catches doubled URLs the explicit list never covered (they now 301 to the
# clean form; an unknown slug then lands on the 404 instead of 404ing directly).
# MUST STAY FIRST among the /blogs WILDCARD rules: _redirects is first-match-wins.
# (The 28 exact species rules sit above it. They are exact paths, so none of them
# can match a doubled /blogs/post/post/... URL and the invariant is untouched.)
/blogs/post/post/* /blogs/post/:splat 301

# The wood section. /woods-we-use is the live URL and this build now emits it, so
# both live rules still hold. It has to sit above the generic /blogs rules below.
#
# /blogs/post/wood-* is now a CATCH-ALL, not the whole answer. The 28 exact
# per-slug 301s are injected ABOVE the first wildcard rule by build_redirects()
# (see the SPECIES block there), so first-match-wins sends every indexed species
# URL to its own page and this rule only picks up wood- slugs the 28 do not name.
# The note that used to sit here said 28 explicit rules "do not fit under the
# 100-rule cut". Measured on cwi-redirect-lab 1 Sep 2026, that was wrong: the cut
# is 100 rules counted FROM THE FIRST WILDCARD RULE ONWARD, and rules above that
# point are not counted at all -- 150 static rules ahead of a wildcard all fired.
# Kept rather than dropped: it costs one rule and it is the only thing standing
# between an unlisted /blogs/post/wood-<x> and a 404.
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
# wildcard costs one rule. The August ":splat tested live and every path still
# 404'd" claim did not survive the 31 Aug cwi-redirect-lab re-test (stale edge
# cache confound; /dist/* /:splat IS honoured). The static target stays anyway:
# these are dead asset paths with no page behind them, so home is the right
# destination, not a 301 into a 404.
/dist/* / 301

# /index.html is a duplicate of /. build.py exempts *.html sources from its
# "this source is a real page" check, because sending this one home is the point.
/index.html / 301

# Carried back from cf-live (commit 6bc28e5a, "Stop serving the two files that
# describe how this site is built"). dist/ NOW CONTAINS .github/workflows/
# site-checks.yml -- carry_live_assets() puts it there so the required check
# survives a cutover that replaces the tracked tree with dist/ -- and that file
# answered 200 on live once already. It names the required check, the sha it is
# pinned to, and by omission what the gate does NOT verify, which is the more
# useful half to anybody probing the site.
#
# LAST IN THIS SOURCE BLOCK, NOT LAST IN THE EMITTED FILE. cf-live's copy is the
# final rule in cf-live's file; here it lands at rule 98 of the 108 in
# dist/_redirects (counted in the built output, 4 Sep 2026), because build_redirects()
# appends ten guide-slug rules generated after this literal. Nothing about the
# behaviour depends on the position -- Pages is first-match-wins and no rule
# below it matches /.github/ -- but the old wording claimed a position the built
# file contradicts, and a comment that can be falsified by reading the artifact
# beside it is worse than no comment.
#
# Listed in SHADOW_ALLOWED below, which is the only reason the shadow check does
# not drop it: hiding a file this build serves is the entire purpose here.
/.github/* / 301
"""

# The 21 doubled-segment /blogs/post/post/<slug> URLs GSC reports, formerly 21
# explicit rules. The /blogs/post/post/* wildcard above covers them (measured on
# cwi-redirect-lab, 31 Aug 2026); this list keeps the old per-slug guarantee:
# the build still checks that every known source's target is a page it emits,
# and warns per slug the day one goes missing, instead of shipping a 301 into
# the 404 silently.
GSC_DOUBLED_SLUGS = [
    "plywood-supply-to-bengaluru", "plywood-supply-to-chennai",
    "plywood-supply-to-coimbatore", "plywood-supply-to-davangere",
    "plywood-supply-to-guntur", "plywood-supply-to-hosur",
    "plywood-supply-to-hubli-dharwad", "plywood-supply-to-hyderabad",
    "plywood-supply-to-jeddah", "plywood-supply-to-jubail",
    "plywood-supply-to-kakinada", "plywood-supply-to-karur",
    "plywood-supply-to-khammam", "plywood-supply-to-khobar",
    "plywood-supply-to-nellore", "plywood-supply-to-riyadh",
    "plywood-supply-to-salem", "plywood-supply-to-sivakasi",
    "plywood-supply-to-sohar", "plywood-supply-to-tirupati",
    "plywood-supply-to-vizag",
]

# A :splat destination cannot be checked against served pages the way a static
# one is, so every rule using one must pin the known sources that prove its
# targets exist: src -> the values :splat is known to take (from GSC). A :splat
# rule with no entry here is dropped loudly rather than trusted blindly.
SPLAT_RULE_PROOF = {
    "/blogs/post/post/*": GSC_DOUBLED_SLUGS,
}

# The shadow check below drops any rule that matches a path this build serves,
# because such a rule takes real content off the site. These are the sources
# where taking the file off the site is the WHOLE POINT, so the check would be
# refusing to do the thing it was asked for. Each entry needs a reason for the
# same purpose DROPPED_FROM_LIVE's do: a silenced check must say why it is silent.
SHADOW_ALLOWED = {
    "/.github/*":
        "dist/ ships .github/workflows/site-checks.yml so that cf-live's "
        "required check 'The site says one thing' survives a publish that "
        "replaces the whole tracked tree -- but the file is infrastructure, not "
        "a page, and it answered 200 to the public once already (cf-live commit "
        "6bc28e5a). Shadowing it is the intended effect, and it works: probed on "
        "the live site 4 Sep 2026, both /.github/workflows/site-checks.yml and "
        "/CLAUDE.md answer 301 -> / while committed on cf-live, so the rule beats "
        "the committed file and cf-live's own _headers comment claiming the "
        "opposite is out of date. The _headers noindex + no-store block stays as "
        "the second layer, not as the one that is doing the work.",
}

# Rules NOT carried across from cf-live, and why. Recorded so the next person can
# see they were considered rather than missed. Settled entries print as ONE
# summary warning; an entry whose reason starts with "NEEDS OWNER" prints its
# own line until the owner rules on it.
DROPPED_FROM_LIVE = {
    "/CLAUDE.md /": "cf-live is served verbatim so its CLAUDE.md was downloadable; "
                    "the cutover serves dist/, which contains no such file",
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

# ---- how many rules Cloudflare Pages actually honours -------------------------
# MEASURED 1 Sep 2026 on the throwaway project cwi-redirect-lab, four fixtures,
# each swept rule-by-rule twice a minute apart, cache-busted, on both the pinned
# deployment URL and the project URL (the August measurement in this repo was
# wrong from stale edge cache, so nothing here is taken on trust):
#
#   B  130 static, no wildcard at all      -> all 130 fired
#      https://54526de2.cwi-redirect-lab.pages.dev
#   C  2 wildcard, 130 static, 3 wildcard  -> first 100 rules fired, rest dead
#      https://b5183417.cwi-redirect-lab.pages.dev
#   A  1 static, 2 wildcard, 200 static, 3 wildcard -> the 1 free static fired,
#      then 100 more from the first wildcard; 105 rules dead
#      https://f1357f1a.cwi-redirect-lab.pages.dev
#   D  150 static | 1 wildcard | 150 static | 1 wildcard  (prediction made first)
#      -> all 150 leading statics fired, then the wildcard + 99 statics = 100,
#         then f099..f149 and the trailing wildcard dead. Exactly as predicted.
#      https://f23aa0f4.cwi-redirect-lab.pages.dev
#
# So the cap is NOT "the first 100 rules in the file", and it is NOT "100 rules
# of any kind". It is: rules BEFORE the first wildcard rule are uncounted (>=150
# verified; Cloudflare documents 2,000 static), and from the first wildcard rule
# onward exactly 100 further rules are honoured -- static and wildcard alike.
# Ordering is therefore a budget decision as well as a precedence one: a static
# rule written below a wildcard spends one of the 100, the same rule written
# above it spends nothing.
STATIC_REDIRECT_LIMIT = 2000   # rules ahead of the first wildcard; >=150 measured
DYNAMIC_WINDOW_LIMIT  = 100    # rules honoured from the first wildcard onward

def _served_paths():
    """Every URL this build actually serves: each file, plus the clean directory
    URL of every index.html. Used so no redirect can shadow real content."""
    out = set()
    for r, _d, fs in os.walk(DIST):
        rel = os.path.relpath(r, DIST).replace(os.sep, "/")
        pre = "" if rel == "." else "/" + rel
        for f in fs:
            out.add(f"{pre}/{f}")
            if f == "index.html":
                out.add(pre or "/")
            elif f.endswith(".html") and f != "404.html":
                # Pages strips .html: about.html serves /about, so that clean URL
                # is real content no rule may shadow. NOT 404.html -- its clean
                # URL is the C-22 soft 404 that the /404 rule deliberately sends
                # home, and listing it here would drop that rule as a shadow.
                out.add(f"{pre}/{f[:-len('.html')]}")
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

    # The 28 indexed species URLs get their EXACT equivalent, not the hub. Every
    # one of /blogs/post/wood-<slug> is a page Google has ranked; 301ing all 28 to
    # /woods-we-use is a redirect to a generic hub, which Google treats as a soft
    # 404 and passes no ranking signal through -- 28 pages' equity thrown away for
    # a redirect that is technically a 301 and practically a dead end.
    #
    # Injected here rather than written into PORTED_REDIRECTS by hand, and injected
    # immediately BEFORE THE FIRST WILDCARD RULE, because that position is what
    # makes them free: see STATIC_REDIRECT_LIMIT / DYNAMIC_WINDOW_LIMIT above for
    # the measurement. Doing it in code means the invariant cannot rot the next
    # time someone reorders the file -- the anchor is "first wildcard", found live.
    # Precedence is the same argument from the other side: first-match-wins, so an
    # exact rule above /blogs/post/wood-* wins, and the wildcard stays below as the
    # catch-all for any wood- slug not in the 28.
    # Safe against the "/blogs/post/post/* MUST STAY FIRST among the /blogs rules"
    # invariant directly above it: these 28 sources are exact paths, and none of
    # them can match a doubled /blogs/post/post/... URL.
    species = [("r", src, LEGACY_REDIRECTS[src], "301")
               for src in (f"/blogs/post/{slug}" for _f, slug, _e, _d in SPECIES if slug)]
    first_wild = next((i for i, it in enumerate(items)
                       if it[0] == "r" and "*" in it[1]), len(items))
    # back up over that rule's own comment header so the block goes above the
    # whole thing rather than between a comment and the rule it explains
    while first_wild and items[first_wild - 1][0] == "#":
        first_wild -= 1
    items[first_wild:first_wild] = (
        [("#", ""),
         ("#", f"# --- the {len(species)} indexed species URLs, each to its own page ---"),
         ("#", "# Above the first wildcard rule on purpose: that is both what gives"),
         ("#", "# them precedence over /blogs/post/wood-* and what keeps them out of"),
         ("#", "# the 100-rule window that starts at the first wildcard.")]
        + species + [("#", "")])

    have  = {it[1] for it in items if it[0] == "r"}
    added = False

    # LEGACY_REDIRECTS also rewrites in-content links, so where it and the live
    # file disagree on a source the in-content target has to win -- otherwise a
    # link on the page and the 301 for the same slug lead to different places.
    overridden = []
    for src in sorted(LEGACY_REDIRECTS):
        dst = LEGACY_REDIRECTS[src]
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
        if ":splat" in dst:
            # Request-dependent target: check it against the pinned sources that
            # justify the rule (SPLAT_RULE_PROOF) instead of a static lookup.
            pinned = SPLAT_RULE_PROOF.get(src)
            if pinned is None:
                dropped.append((src, dst, ":splat destination with no pinned "
                                          "sources in SPLAT_RULE_PROOF")); continue
            misses = [s for s in pinned if not resolve(dst.replace(":splat", s))]
            for s in misses:
                warn(f"splat rule {src}: known source {src.replace('*', s)} will "
                     f"301 to {dst.replace(':splat', s)}, which this build does "
                     f"not emit -- that now lands on the 404")
            if misses and len(misses) == len(pinned):
                dropped.append((src, dst, "no pinned source resolves to a page "
                                          "this build emits")); continue
        elif not resolve(dst):
            dropped.append((src, dst, "target is not a page this build emits")); continue
        # a rule matching something we serve would take that page off the site
        if not src.endswith(".html") and src not in SHADOW_ALLOWED:
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
    # Two budgets, counted separately, because that is how Pages actually behaves
    # (STATIC_REDIRECT_LIMIT / DYNAMIC_WINDOW_LIMIT above carry the measurement).
    # The old single "n of 100" number described a budget that does not exist: it
    # counted rules above the first wildcard, which are free, against a cap that
    # only starts there.
    rules = [l for l in out if l and not l.startswith("#")]
    wild  = next((i for i, l in enumerate(rules) if "*" in l.split()[0]), len(rules))
    free, window = wild, len(rules) - wild
    if window > DYNAMIC_WINDOW_LIMIT:
        warn(f"_redirects: {window} rules sit at or below the first wildcard rule "
             f"({rules[wild].split()[0] if wild < len(rules) else '-'}); Cloudflare "
             f"Pages honours only {DYNAMIC_WINDOW_LIMIT} from there, so the last "
             f"{window - DYNAMIC_WINDOW_LIMIT} will never fire. Moving any static "
             f"rule above the first wildcard costs nothing and frees a slot")
    elif window > DYNAMIC_WINDOW_LIMIT - 5:
        # cf-live sat at 99 of 100 and 603 rules had already fallen off the end
        # once. Say so while there is still room to do something about it.
        warn(f"_redirects: {window} of the {DYNAMIC_WINDOW_LIMIT} rules Pages "
             f"honours from the first wildcard onward — "
             f"{DYNAMIC_WINDOW_LIMIT - window} left before rules start being "
             f"ignored (static rules can be moved above the first wildcard instead)")
    if free > STATIC_REDIRECT_LIMIT:
        warn(f"_redirects: {free} static rules ahead of the first wildcard; "
             f"Cloudflare documents {STATIC_REDIRECT_LIMIT}, so the last "
             f"{free - STATIC_REDIRECT_LIMIT} will never fire")
    header = (f"# Generated by build.py -- do not hand-edit; change PORTED_REDIRECTS\n"
              f"# or LEGACY_REDIRECTS instead. {len(rules)} rules: {free} static ahead\n"
              f"# of the first wildcard (of {STATIC_REDIRECT_LIMIT} Cloudflare Pages\n"
              f"# honours there) and {window} from that wildcard onward (of "
              f"{DYNAMIC_WINDOW_LIMIT}).\n"
              f"# Order is load-bearing twice over: first match wins, AND the 100-rule\n"
              f"# window starts at the first wildcard rule.\n")
    write("_redirects", header + "\n".join(out).strip("\n") + "\n")
    return n, free, window

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
            # TEXT MODE ON PURPOSE, DO NOT "OPTIMISE" THIS TO A BINARY READ.
            # Python's universal newlines fold the six sources' CRLF to \n on the
            # way in and write() pins \n on the way out, which is why bundle.css
            # was already the same bytes and the same hash on every platform
            # while site.js and fonts.css were not. A raw read here would put
            # this file in the same trap they were in.
            parts.append(f"/* --- {name} --- */\n" + _css_fix_urls(open(fp, encoding="utf-8").read(), name))
        _bundle_css = "\n".join(parts)
    return _bundle_css

# ONLY A CONTENT-ADDRESSED NAME MAY CARRY THE IMMUTABLE HEADER, so these three --
# the only files here whose bytes change from deploy to deploy -- carry a content
# hash in their name and nothing else under /assets/ does. Without the hash a
# returning visitor keeps the old CSS/JS until the cache expires, and the _headers
# block written in assets_and_meta() below names exactly these three plus
# /assets/fonts/* for the year-long pin; the logo, the icons and the og card are
# NOT content-addressed, so they get a day instead (see that block for the whole
# argument, and for why a blanket /assets/* rule cannot be used to say it).
#
# cw-events.js is hashed for that reason and one sharper. cf-live serves the
# conversion beacon from /js/cw-events.js at max-age=3600, must-revalidate; this
# build serves it from /assets/ where the pin is a year. Publish it under a fixed
# name and a broken beacon is frozen in every returning buyer's browser until
# September 2027, with no URL left to push a fix through.
ASSETS = {"bundle.css": "bundle.css", "site.js": "site.js", "cw-events.js": "cw-events.js"}

def _digest(data):
    if isinstance(data, str): data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:8]

def fingerprint_assets():
    ASSETS["bundle.css"] = f"bundle.{_digest(css_bundle_content())}.css"
    jp = os.path.join(ROOT, "assets", "site.js")
    if os.path.exists(jp):
        # read_lf, not a raw read: the name must be the digest of the bytes that
        # get PUBLISHED, and what gets published is the LF form. Hashing the
        # working-tree bytes instead made the name a property of the checkout --
        # site.f14bf457.js here, site.96278e59.js on any autocrlf=false clone,
        # for one unchanged commit.
        ASSETS["site.js"] = f"site.{_digest(read_lf(jp))}.js"
    # THE BEACON IS THE ONLY SOURCE OF WEBSITE CONVERSION NUMBERS. Every one of
    # cf-live's 293 pages loads it and POSTs tel_click, whatsapp_click,
    # quote_click and form_submit_success to /cw-event; the zone route stays
    # bound after cutover, so a build that omits the file raises no error
    # anywhere -- the dashboard simply reports ZERO conversions for a site that
    # is still producing enquiries, which is a wrong answer rather than a
    # missing one, and the first cut of this builder shipped exactly that on 0
    # of 253 pages. Commit 09476b27 paid for this file once; do not lose it
    # again. Restore with:
    #   git show origin/cf-live:js/cw-events.js > assets/cw-events.js
    ep = os.path.join(ROOT, "assets", "cw-events.js")
    if os.path.exists(ep):
        ASSETS["cw-events.js"] = f"cw-events.{_digest(read_lf(ep))}.js"
    else:
        ASSETS["cw-events.js"] = None      # no tag rather than 253 script 404s
        warn("assets/cw-events.js is missing: no page will load the /cw-event "
             "beacon, so every tel, WhatsApp, quote-intent and form-success "
             "click on all pages goes uncounted and the conversion dashboard "
             "reads zero. Run: git show origin/cf-live:js/cw-events.js > "
             "assets/cw-events.js")

def beacon_tag():
    """The /cw-event beacon script tag -- on every page, or (only if the source
    file has gone missing) on none. Deliberately a separate file from site.js:
    site.js opens by promising "No dependencies, no tracking", and burying a
    page-level conversion counter inside it would make that header a lie for
    every reader who checks."""
    name = ASSETS.get("cw-events.js")
    return f'\n<script src="{u("/assets/" + name)}" defer></script>' if name else ""

def build_css_bundle():
    write("assets/" + ASSETS["bundle.css"], css_bundle_content())

# Live robots.txt, verbatim minus its final Sitemap line (appended from LIVE at
# the write site in assets_and_meta, where the why of all this is recorded).
ROBOTS_TXT = """# Cochin Wood Industries — full-access policy for AI answer engines and search crawlers.

User-agent: *
Allow: /

# AI answer engines (explicit allow)
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Applebot-Extended
Allow: /

User-agent: Meta-ExternalAgent
Allow: /

User-agent: Meta-ExternalFetcher
Allow: /

User-agent: cohere-ai
Allow: /

User-agent: YouBot
Allow: /

User-agent: PhindBot
Allow: /

User-agent: CCBot
Allow: /

User-agent: Bytespider
Allow: /

User-agent: Amazonbot
Allow: /

User-agent: Diffbot
Allow: /

"""

def assets_and_meta():
    src = os.path.join(ROOT, "assets")
    dst = os.path.join(DIST, "assets")
    if os.path.exists(dst): shutil.rmtree(dst)
    # The six bundle sources are CSS_BUNDLE INPUTS, not URLs: every page links
    # /assets/bundle.<hash>.css and 0 of the 253 link these, so copytree was
    # publishing six dead stylesheets that any reader would take for the live
    # ones. fonts.css is deliberately NOT in this list even though it is also a
    # bundle input: cf-live serves /assets/fonts.css for real (it has its own
    # cache rule in the live _headers), so dropping it would turn a URL that
    # answers 200 today into a 404 at cutover.
    dead_bundle_sources = [n for n in CSS_BUNDLE if n != "fonts.css"]
    # copy_function, not the default copy2: assets/fonts.css is served verbatim
    # at a URL cf-live already answers, and a byte-exact copy of it out of THIS
    # checkout is a copy of 153 CRLF pairs that git would then undo in the index.
    # The font faces, the logo, the icons and the og card go through untouched --
    # copy_lf's NUL test sees them as binary.
    shutil.copytree(src, dst, copy_function=copy_lf,
                    ignore=shutil.ignore_patterns("photos", *dead_bundle_sources))
    # Publish the two fingerprinted scripts under their hashed names, so the
    # year-long immutable header below is only ever attached to a name that
    # changes when the bytes do.
    for key, plain_name in (("site.js", "site.js"), ("cw-events.js", "cw-events.js")):
        hashed = ASSETS.get(key)
        plain = os.path.join(dst, plain_name)
        if hashed and hashed != plain_name and os.path.exists(plain):
            os.replace(plain, os.path.join(dst, hashed))
        elif not hashed and os.path.exists(plain):
            os.remove(plain)      # unhashed leftover would get pinned for a year
    build_css_bundle()
    open(os.path.join(DIST, ".nojekyll"), "w").close()
    # Cloudflare Pages headers (ignored by GitHub Pages, honoured by CF Pages).
    #
    # The Content-Security-Policy below is carried VERBATIM from what production serves
    # today (`git show origin/cf-live:_headers`, re-checked against the wire on 1 Sep
    # 2026: www.cochinwood.in returns it on /, /contact, /assets/* and even on 404s).
    # It is the ONE security header here that no Cloudflare zone rule re-adds. Proof:
    # the apex 301 at https://cochinwood.in/ is a zone Redirect Rule that never reaches
    # Pages, and it still carries Strict-Transport-Security, X-Content-Type-Options,
    # Referrer-Policy, Permissions-Policy and the report-only CSP -- but NOT this
    # enforced one. So this file is its only source, and a build that omits it drops
    # the protection silently at cutover: frame-ancestors is what stops another origin
    # framing this site inside its own page, and base-uri stops an injected <base> tag
    # re-pointing every relative URL on the page.
    #
    # script-src, frame-src, connect-src and default-src are deliberately ABSENT, exactly
    # as on live. /contact runs Cloudflare Turnstile: it loads
    # https://challenges.cloudflare.com/turnstile/v0/api.js, frames the widget from that
    # same origin and calls back to it. Any one of those four directives, added without
    # also allow-listing challenges.cloudflare.com, would kill every quote submission on
    # the site while the page still looked perfectly healthy -- worse than no CSP at all.
    # base-uri, object-src and frame-ancestors govern none of those three things, which
    # is why this policy is safe to enforce unchanged. The pages also still carry inline
    # JS, so any script-src short of 'unsafe-inline' would break them anyway. Tighten
    # only with a policy that has been tested against a real Turnstile submission.
    #
    # ---- THE POLICY THAT WOULD REPLACE IT IS STAGED IN REPORT-ONLY, NOT ENFORCED ----
    #
    # This repository publishes on merge, and a wrong script-src takes the JavaScript
    # down on all 253 pages while every one of them still looks healthy. So the real
    # policy goes into Content-Security-Policy-Report-Only first: the browser evaluates
    # it, says what it WOULD have blocked, and blocks nothing.
    #
    # The origin list is counted, not guessed -- it is every external thing the built
    # tree actually loads. challenges.cloudflare.com serves the Turnstile script on
    # /contact, opens the widget's iframe and is called back by it, which is three
    # directives (script-src, frame-src, connect-src). static.cloudflareinsights.com
    # serves the page-view beacon Cloudflare injects at the edge and posts to
    # cloudflareinsights.com -- it is in no source file, which is exactly why it is easy
    # to leave out (assets/cw-events.js names Insights as the thing it supplements).
    # Everything else the site loads -- the CSS bundle, both scripts, every font file,
    # every image, the /cw-event and /ts-fail beacons -- is same-origin, which is what
    # makes default-src 'self' the right floor. The data: in img-src is the one non-file
    # image: the SVG wave bundle.css draws as a background.
    #
    # WHERE IT WILL FIRE, so the reports are read as expected rather than as news:
    #   * /contact. Its two inline <script> blocks (QUOTE_JS) and the inline onerror= on
    #     the Turnstile tag are the whole of the site's inline JavaScript, and script-src
    #     without 'unsafe-inline' refuses all three. JSON-LD is a data block, never
    #     executed, and is not reported. Promotion needs a nonce or hashes for those
    #     three, or the code moves into a file -- that is the work this staging is for.
    #   * Nowhere for styles: style-src carries 'unsafe-inline' rather than staging a
    #     failure already known. 19 pages ship a <style> block (21 of them) and 863
    #     elements a style attribute, nearly all of it inside imported bodies and some
    #     of it emitted here. Removing that is a content project, not a header change,
    #     and reporting 884 style violations would bury the three script findings.
    #   * www.cochinwood.in is named beside 'self' in form-action and connect-src on
    #     purpose. The form action and the /ts-fail beacon are ABSOLUTE by design (see
    #     the comment above the form): served from a preview origin, 'self' alone would
    #     block the submission and the beacon, and the preview is where this gets tested.
    #
    # NOTHING COLLECTS THESE YET. No report-uri/report-to, because there is no endpoint
    # to name and pointing one at a URL that does not collect is worse than admitting it:
    # violations appear in the browser console and nowhere else, so observing them means
    # opening the pages, /contact first. PROMOTE THE ENFORCED HEADER ONLY ONCE THIS ONE
    # HAS RUN CLEAN -- moving the same directive list up one header name is the whole
    # change, and until then nothing about what the site serves today is altered.
    # Production also carries a permissive Content-Security-Policy-Report-Only from a
    # Cloudflare zone rule (audit, 4 Sep 2026). This does not replace it: two
    # report-only policies are evaluated independently, and that one can only be removed
    # from the dashboard.
    #
    # ---- CACHE RULES: NAME THE CONTENT-ADDRESSED FILES, NEVER A BLANKET /assets/* ----
    #
    # "immutable" tells a browser not to revalidate even on a hard reload, so it is
    # only ever true of a URL that changes when its bytes change. This block used to
    # say `/assets/*  max-age=31536000, immutable`, which pinned six files whose names
    # never change -- logo.png, og/cwi-og-share-1200x630.png and the four icons -- on
    # all 253 pages, for a year. That is the exact claim audit commit c3961d74 ("Stop
    # claiming assets are immutable when their filenames never change") was written to
    # remove, so shipping it again would have silently reversed a fix that is already
    # paid for. The same rule on /files/* was worse than a reversal: cf-live serves
    # /files/* at max-age=86400 both before and after that audit, so a year there was a
    # NEW escalation, and it would have frozen 18 referenced media files -- the 17 in
    # the pages plus /files/Home/home-1-hero.jpg, which bundle.css loads as the
    # homepage hero background. Replace the hero photo after cutover and returning
    # visitors keep the old one until September 2027.
    #
    # WHY EACH HASHED FILE IS NAMED INDIVIDUALLY INSTEAD OF ONE /assets/* RULE:
    # Cloudflare Pages MERGES every matching rule into a single header rather than
    # letting the most specific rule win. A blanket /assets/* beside the narrower rules
    # below would emit two conflicting max-age values on the same response and leave
    # the browser to pick. That merge behaviour is why cf-live's own _headers has no
    # /assets/* rule at all and names /assets/fonts.css, /assets/og/* and
    # /assets/fonts/* one at a time -- see the note above its fonts block. Never add a
    # blanket rule that overlaps a narrower one here.
    #
    # fingerprint_assets() runs at the top of main(), well before this write, so the
    # three hashed names below are already settled and can be interpolated.
    immutable = "  Cache-Control: public, max-age=31536000, immutable\n"
    day       = "  Cache-Control: public, max-age=86400\n"
    hashed_rules = "".join(
        f"/assets/{ASSETS[k]}\n" + immutable
        for k in ("bundle.css", "site.js", "cw-events.js") if ASSETS.get(k))
    # THE PUBLISHED TREE MUST SAY WHICH COMMIT IT WAS BUILT FROM. 311 of dist/'s
    # 607 files are copied out of cf-live's object store, and a dist/ that does
    # not name that commit cannot be audited once the terminal that printed the
    # banner is closed -- and the banner is numerically identical whether the
    # carry came from origin/cf-live's c59adae9 or the 25-commits-stale local
    # cf-live d38bacd4, so the number alone never distinguished them. _headers
    # is the right carrier: Cloudflare Pages consumes it as configuration and
    # never serves it as a URL, so this line adds nothing to the public surface
    # and nothing for the preflight's coverage check to account for, and `#` is
    # a comment here exactly as it is throughout cf-live's own _headers.
    write("_headers",
        f"# built from {LIVE_PIN} -- the pin lives in build.py as LIVE_SHA\n" +
        hashed_rules +
        "/assets/fonts/*\n" + immutable +
        # Not content-addressed: same filename forever. An hour, then revalidate --
        # carried from cf-live, which gives this exact file exactly this rule.
        "/assets/fonts.css\n"
        "  Cache-Control: public, max-age=3600, must-revalidate\n"
        # Six binaries with fixed names, referenced by all 253 pages. A day means a
        # replaced logo or share card reaches everyone the same day instead of next year.
        "/assets/og/*\n" + day +
        "/assets/icons/*\n" + day +
        "/assets/logo.png\n" + day +
        # THE ROOT FAVICON IS BACK, SO ITS CACHE RULE HAS TO COME BACK WITH IT.
        # carry_live_assets() writes cf-live's favicon.png to the dist root again
        # (CARRIED_ROOT_FILES says why), and cf-live's _headers gives that exact
        # path "Cache-Control: public, max-age=86400". It was the only live cache
        # rule this file did not carry across, which left /favicon.png falling
        # through to the /* block -- and /* sets no Cache-Control at all, so the
        # file would ship with Pages' revalidate-every-request default instead of
        # the day it has today. Same value as cf-live, deliberately: a favicon
        # keeps its filename forever, so it can never be pinned like the hashed
        # assets above.
        "/favicon.png\n" + day +
        # Restored VERBATIM from cf-live, both lines. The CORS header is load-bearing:
        # these are the images other sites and the app hotlink, and dropping
        # Access-Control-Allow-Origin breaks every canvas/fetch consumer of them.
        "/files/*\n"
        "  Access-Control-Allow-Origin: *\n" + day +
        # Carried from cf-live for the same reason it exists there: the workflow file
        # has to sit in the published tree or the required check cannot run.
        # THE REDIRECT ACTUALLY WINS, MEASURED ON THE LIVE SITE. cf-live's own
        # _headers says a committed file beats every _redirects rule and cites a
        # 2026-08-15 attempt on /CLAUDE.md; that comment is now the stale one.
        # Probed 4 Sep 2026 against production with cache-busting queries:
        # https://www.cochinwood.in/.github/workflows/site-checks.yml and
        # https://www.cochinwood.in/CLAUDE.md BOTH answer 301 -> / while both
        # files are committed on cf-live. So this block is belt-and-braces, not
        # the only defence -- kept because noindex + no-store is what remains if
        # the rule ever stops being honoured, and because it costs no redirect
        # slot to keep.
        "/.github/*\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "  Cache-Control: no-store\n"
        "/*\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  Content-Security-Policy: base-uri 'self'; object-src 'none'; frame-ancestors 'self'\n"
        # Staged, not enforced -- it reports and blocks nothing. Same three directives as
        # the enforced line above, so promoting it later is a rename, not a rewrite.
        "  Content-Security-Policy-Report-Only: "
        "default-src 'self'; "
        "script-src 'self' https://challenges.cloudflare.com https://static.cloudflareinsights.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self' https://www.cochinwood.in https://challenges.cloudflare.com "
        "https://cloudflareinsights.com; "
        "frame-src https://challenges.cloudflare.com; "
        "form-action 'self' https://www.cochinwood.in; "
        "base-uri 'self'; object-src 'none'; frame-ancestors 'self'\n"
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
</div></section>''', self_url=False))
    # Carried from live VERBATIM (git show origin/cf-live:robots.txt, read 31 Aug
    # 2026), not regenerated: the 19 explicit Allow blocks for named AI crawlers
    # are a deliberate courtesy list -- this site courts AI readers (it has an
    # llms page) -- and the first cut of this builder silently dropped them for a
    # functionally-identical two-liner. Only the Sitemap line is templated on
    # LIVE, so it can never disagree with where the sitemap actually is; today
    # that renders byte-for-byte what live serves, trailing no-newline included.
    write("robots.txt", ROBOTS_TXT + f"Sitemap: {LIVE}/sitemap.xml")

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
    # Before copy_referenced_files() on purpose: where cf-live and this repo both
    # have a photo at the same /files/ path, the one the new pages actually
    # reference must be the one on disk, so it is written last and wins.
    c = carry_live_assets()
    f = copy_referenced_files()  # so this must run after it
    for ref in sorted(_files_missing):
        warn(f"photo missing, reference removed: {ref}")
    sm = build_sitemap()
    # last: it checks every rule against the pages this build actually emitted,
    # /files/ assets included, so everything has to be on disk first
    rd, rd_free, rd_window = build_redirects()
    cnt = sum(len(fs) for _,_,fs in os.walk(DIST))
    print(f"BUILD OK  base='{BASE or '(root)'}'  {p} content pages + {n} wood pages + {x} export pages + {b} blog posts + {f} images + {c} carried from {LIVE_PIN}  sitemap:{sm}  redirects:{rd} ({rd_free} static/{STATIC_REDIRECT_LIMIT} + {rd_window} from first wildcard/{DYNAMIC_WINDOW_LIMIT})  files: {cnt}")
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
