#!/usr/bin/env python3
"""
Cochin Wood Industries — clean static-site builder (no external deps).

Source in this repo -> renders to dist/. Set SITE_BASE to deploy under a
subpath (e.g. /cochinwood-web for GitHub project Pages); leave empty for the
domain root (Cloudflare Pages at cochinwood.in).

    python build.py          # builds to dist/ at root ("")
    SITE_BASE=/cochinwood-web python build.py
"""
import os, re, json, shutil, html

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
BASE = os.environ.get("SITE_BASE", "").rstrip("/")   # "" or "/cochinwood-web"
LIVE = "https://www.cochinwood.in"                    # canonical production host
def u(path): return (BASE + path) if path.startswith("/") else path

CONTACT = dict(email="sales@cochinwood.in", phone_disp="+91 95674 10175",
               phone_href="+919567410175", addr="Kuruppampady, Ernakulam, Kerala 683545")

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

NAV = [("Products", "/products", False), ("Industries", "/industries", True),
       ("Wood Encyclopedia", "/wood-encyclopedia/", False),
       ("Resources", "/resources", True), ("Contact", "/contact", False)]

def header():
    links = ""
    for label, path, external in NAV:
        href = LIVE + path if external else u(path)
        links += f'<a href="{href}">{label}</a>\n'
    return f'''<header class="cw-hd"><div class="cw-wrap cw-hd__in">
  <a class="cw-hd__brand" href="{u('/')}"><img src="{u('/assets/logo.png')}" alt="Cochin Wood Industries logo"><span style="display:block"><b>Cochin Wood Industries</b><span>Plywood Manufacturer &middot; Kochi</span></span></a>
  <button class="cw-burger" aria-label="Menu" onclick="document.getElementById('nav').classList.toggle('open')">&#9776;</button>
  <nav class="cw-nav" id="nav">
    {links}<a class="cw-cta" href="{u('/contact')}">Get a quote</a>
  </nav>
</div></header>'''

def footer():
    prod = "".join(f'<a href="{LIVE}/{s}">{n}</a>' for s,n,_ in PRODUCTS[:7])
    return f'''<footer class="cw-ft"><div class="cw-wrap">
  <div class="cw-ft__cols">
    <div class="cw-ft__brand"><b>Cochin Wood Industries</b><p>Plywood manufacturer in Kochi, Kerala — packing, Okoume and shuttering ply, shipped across India and exported. Part of a group manufacturing in Perumbavoor since 1986.</p></div>
    <div><h4>Products</h4>{prod}</div>
    <div><h4>Explore</h4><a href="{u('/products')}">All products</a><a href="{u('/wood-encyclopedia/')}">Wood Encyclopedia</a><a href="{LIVE}/resources">Resources</a><a href="{LIVE}/industries">Industries</a></div>
    <div><h4>Contact</h4><a href="tel:{CONTACT['phone_href']}">{CONTACT['phone_disp']}</a><a href="mailto:{CONTACT['email']}">{CONTACT['email']}</a><a href="https://maps.google.com/?q=Kuruppampady+Kerala" target="_blank" rel="noopener">{CONTACT['addr']}</a></div>
  </div>
  <div class="cw-ft__bar"><span>&copy; 2026 Cochin Wood Industries Pvt Ltd. Group established 1986.</span>
  <span><a href="{LIVE}/privacy-policy" style="display:inline">Privacy</a> &middot; <a href="{LIVE}/terms-and-conditions" style="display:inline">Terms</a></span></div>
</div></footer>'''

def base(title, desc, path, body, body_class="", extra_head=""):
    canonical = LIVE + path
    return f'''<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="{u('/assets/logo.png')}">
<link href="https://fonts.googleapis.com/css2?family=Bree+Serif&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{u('/assets/site.css')}">
<link rel="stylesheet" href="{u('/assets/guide.css')}">
<link rel="stylesheet" href="{u('/assets/wood-enc.css')}">
<link rel="stylesheet" href="{u('/assets/shell.css')}">
{extra_head}</head>
<body class="{body_class}">
{header()}
{body}
{footer()}
</body>
</html>'''

def write(path, content):
    fp = os.path.join(DIST, path)
    os.makedirs(os.path.dirname(fp) or DIST, exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f: f.write(content)

# ---------------- HOME ----------------
def home():
    cards = "".join(
        f'<a class="cw-card" href="{LIVE}/{s}"><h3>{n}</h3><p>{d}</p><span class="cw-card__tag">View &rarr;</span></a>'
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
        f'<a class="cw-card" href="{LIVE}/{s}"><h3>{n}</h3><p>{d}</p><span class="cw-card__tag">View &rarr;</span></a>'
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
        "/products", body))

# ---------------- CONTACT ----------------
def contact():
    body = f'''
<section class="cw-sec"><div class="cw-wrap" style="max-width:760px">
  <p class="cw-hero__ey" style="color:var(--cw-green-600)">Get in touch</p>
  <h1 class="cw-sec__h" style="font-size:clamp(1.9rem,4vw,2.8rem)">Request a quote</h1>
  <p class="cw-sec__lead">Tell us the product, grade, thickness, quantity and delivery location. We reply within one business day with a price and lead time.</p>
  <div class="cw-feat" style="margin-bottom:30px">
    <div><h3>WhatsApp / Phone</h3><p><a href="tel:{CONTACT['phone_href']}">{CONTACT['phone_disp']}</a></p></div>
    <div><h3>Email</h3><p><a href="mailto:{CONTACT['email']}">{CONTACT['email']}</a></p></div>
    <div><h3>Works &amp; office</h3><p>{CONTACT['addr']}</p></div>
  </div>
  <a class="cw-btn cw-btn--p" href="mailto:{CONTACT['email']}?subject=Plywood%20enquiry">Email an enquiry</a>
  <p style="margin-top:26px;color:var(--cw-ink-600);font-size:.9rem">A quote form wired to our CRM lands here in the migration — for now, WhatsApp or email is fastest.</p>
</div></section>'''
    write("contact/index.html", base(
        "Contact — Request a Plywood Quote | Cochin Wood Industries",
        "Contact Cochin Wood Industries, Kuruppampady, Ernakulam, Kerala. WhatsApp/phone +91 95674 10175 or sales@cochinwood.in for plywood quotes, pan-India and export.",
        "/contact", body))

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
    # remaining root-relative (products, contact, guides) -> live site for now
    body = re.sub(r'href="/(?!/)', f'href="{LIVE}/', body)
    return body

def encyclopedia():
    slugs = ["okoume","gurjan","rubberwood","eucalyptus","poplar","birch","jackwood",
             "mango","silver-oak","pine","teak","sheesham","sal","neem","mahogany"]
    encdir = os.path.join(ROOT, "content", "encyclopedia")
    # hub
    title, desc, body = enc_extract(os.path.join(encdir, "_hub.html"))
    body = enc_rewrite(body, slugs)
    write("wood-encyclopedia/index.html", base(title, desc, "/wood-encyclopedia", body, body_class="cw-encbody"))
    # species
    for s in slugs:
        title, desc, body = enc_extract(os.path.join(encdir, f"{s}.html"))
        body = enc_rewrite(body, slugs)
        write(f"wood-encyclopedia/{s}/index.html", base(title, desc, f"/wood-encyclopedia/{s}", body, body_class="cw-encbody"))
    return len(slugs)+1

# ---------------- assets + meta ----------------
def assets_and_meta():
    src = os.path.join(ROOT, "assets")
    dst = os.path.join(DIST, "assets")
    if os.path.exists(dst): shutil.rmtree(dst)
    shutil.copytree(src, dst)
    open(os.path.join(DIST, ".nojekyll"), "w").close()
    write("404.html", base("Page not found | Cochin Wood Industries", "Page not found.", "/404",
        f'<section class="cw-sec"><div class="cw-wrap" style="text-align:center;padding:60px 0"><h1 class="cw-sec__h">Page not found</h1><p class="cw-sec__lead" style="margin:0 auto 24px">That page has moved or doesn\'t exist.</p><a class="cw-btn cw-btn--p" href="{u("/")}">Back to home</a></div></section>'))
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {LIVE}/sitemap.xml\n")

def main():
    if os.path.exists(DIST): shutil.rmtree(DIST)
    os.makedirs(DIST)
    home(); products(); contact()
    n = encyclopedia()
    assets_and_meta()
    cnt = sum(len(fs) for _,_,fs in os.walk(DIST))
    print(f"BUILD OK  base='{BASE or '(root)'}'  pages: home+products+contact + {n} encyclopedia  files: {cnt}")

if __name__ == "__main__":
    main()
