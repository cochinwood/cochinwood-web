import os, re, json, sys, glob, html
sys.stdout.reconfigure(encoding='utf-8')
CF = r"C:/Users/EDWIND~1/AppData/Local/Temp/claude/_cfmirror"
SITE = "https://www.cochinwood.in"
def rd(p): return open(p, encoding='utf-8').read()
def wr(p, t): open(p, 'w', encoding='utf-8').write(t)

SLUG = {
 'okoume':'wood-okoume-aucoumea-klaineana','gurjan':'wood-gurjan-keruing-dipterocarpus',
 'rubberwood':'wood-rubberwood-hevea-brasiliensis','eucalyptus':'wood-eucalyptus',
 'poplar':'wood-poplar-populus','birch':'wood-birch-betula','jackwood':'wood-jackwood-artocarpus-heterophyllus',
 'mango':'wood-mango-mangifera-indica','silver-oak':'wood-silver-oak-grevillea-robusta','pine':'wood-pine-pinus',
 'teak':'wood-teak-tectona-grandis','sheesham':'wood-sheesham-dalbergia-sissoo','sal':'wood-sal-shorea-robusta',
 'neem':'wood-neem-azadirachta-indica','mahogany':'wood-mahogany-swietenia-toona','meranti':'wood-meranti-shorea',
 'gmelina':'wood-gmelina-arborea','melia-dubia':'wood-melia-dubia-malabar-neem','acacia-mangium':'wood-acacia-mangium',
 'semul':'wood-semul-bombax-ceiba'}
def post(f): return "/blogs/post/" + SLUG[f]

# ---------- 1. sitewide renames ----------
n1=n2=0
for fp in glob.glob(CF + "/**/*.html", recursive=True):
    t = rd(fp); o = t
    t = t.replace('/wood-encyclopedia', '/woods-we-use')
    t = t.replace('>Wood Encyclopedia<', '>Woods We Use<')
    t = t.replace('> Wood Encyclopedia<', '> Woods We Use<')
    t = t.replace('"name":"Wood Encyclopedia"', '"name":"Woods We Use"')
    t = t.replace('"name": "Wood Encyclopedia"', '"name": "Woods We Use"')
    if t != o: wr(fp, t); n1 += 1
print("renamed refs on", n1, "pages")

# ---------- 2. new hub content ----------
def card(name, sci, f):
    return (f'<a class="cwe__card" href="{post(f)}"><p class="cwe__card-name">{name}</p>'
            f'<p class="cwe__card-sci">{sci}</p><span class="cwe__card-tag">Data sheet</span></a>')
VENEERS = [('Okoume','Aucoumea klaineana','okoume'),('Gurjan / Keruing','Dipterocarpus spp.','gurjan'),
 ('Rubberwood','Hevea brasiliensis','rubberwood'),('Eucalyptus','Eucalyptus spp.','eucalyptus'),
 ('Poplar','Populus spp.','poplar'),('Gmelina','Gmelina arborea','gmelina'),
 ('Malabar Neem','Melia dubia','melia-dubia'),('Acacia (Mangium)','Acacia mangium','acacia-mangium')]
TIMBERS = [('Jackwood','Artocarpus heterophyllus','jackwood'),('Mango','Mangifera indica','mango'),
 ('Silver oak','Grevillea robusta','silver-oak'),('Pine','Pinus spp.','pine'),
 ('Sal','Shorea robusta','sal'),('Semul (Silk Cotton)','Bombax ceiba','semul')]
ASKED = [('Teak','Tectona grandis','teak'),('Sheesham','Dalbergia sissoo','sheesham'),
 ('Mahogany','Swietenia / Toona ciliata','mahogany'),('Neem','Azadirachta indica','neem'),
 ('Birch','Betula spp.','birch'),('Meranti / Red Lauan','Shorea spp.','meranti')]

def group(title, intro, items):
    cards = "".join(card(*i) for i in items)
    return (f'<div class="cwe__group"><h2>{title}</h2><p>{intro}</p>'
            f'<div class="cwe__grid">{cards}</div></div>')

HUB_CONTENT = f'''<header class="cwg__hero">
  <div class="cwg__container">
    <nav class="cwg__crumb" aria-label="Breadcrumb"><a href="/">Home</a><span class="cwg__crumb-sep" aria-hidden="true">&rsaquo;</span><span aria-current="page">Woods We Use</span></nav>
    <p class="cwg__eyebrow">Woods We Use</p>
    <h1 class="cwg__h1">The woods behind our plywood &amp; timber</h1>
    <p class="cwg__meta">Every veneer we peel and every timber we saw &middot; independently researched, cross-checked and cited</p>
  </div>
</header>
<div class="cwg__container">
  <div class="cwg__tldr">
    <p><strong>What this is:</strong> the species that actually pass through our factory gates &mdash; the face and core veneers inside our plywood, and the Kerala hardwoods our sawn-timber desk cuts for packing. Each entry covers <strong>density, hardness, workability, durability and real-world use</strong>, cross-checked across independent sources with references on every page. Where we use a wood, we say exactly where.</p>
  </div>
</div>
<article class="cwg__body">
  <div class="cwg__wide">
{group("Face &amp; core veneers in our plywood",
 'The woods we peel and press into <a href="/commercial-plywood">commercial packing ply</a>, <a href="/marine-plywood">marine</a> and <a href="/bwr-hardwood-plywood">BWR boards</a>.', VENEERS)}
{group("Kerala &amp; plantation timbers we saw for packing",
 'The solid woods behind our <a href="/sawn-timber">sawn timber</a>, <a href="/plywood-boxes-crates">cases &amp; crates</a> and <a href="/plywood-pallets">pallets</a>.', TIMBERS)}
{group("Timbers buyers ask about",
 'Not part of our standard range &mdash; but buyers ask, so here are honest data sheets. Need an alternative we do stock? <a href="/contact#quote">Ask the desk</a>.', ASKED)}
    <div class="cwe__note" style="max-width:820px">Every entry is researched from multiple independent sources &mdash; botanical databases, forest-products laboratories, the IUCN Red List and the timber trade &mdash; and figures are cross-checked before we publish. Where sources disagree, we show the range. All writing is Cochin Wood Industries' own; sources are cited on each page.</div>
  </div>
</article>
<section class="cwg__cta">
  <div class="cwg__wide cwg__cta-inner">
    <div><h2>Looking for plywood or timber, not a data sheet?</h2><p>Tell us the grade, thickness, quantity and destination &mdash; we'll quote within one business day.</p></div>
    <a class="cwg__btn" href="/contact#quote">Request a quote</a>
  </div>
</section>'''

HUB_TITLE = "Woods We Use: Plywood Veneers & Packing Timbers | Cochin Wood"
HUB_DESC = ("The wood species behind Cochin Wood's plywood and sawn timber — Okoume, Gurjan, Rubberwood, Kerala "
            "hardwoods and more. Density, hardness and use data, cross-checked and cited.")
NEW_SCHEMAS = ('<script type="application/ld+json">' + json.dumps({
  "@context":"https://schema.org","@type":"CollectionPage","name":"Woods We Use",
  "description":HUB_DESC,"url":SITE+"/woods-we-use","publisher":{"@id":SITE+"/#organization"}}, ensure_ascii=False) + '</script>\n'
  '<script type="application/ld+json">' + json.dumps({
  "@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
   {"@type":"ListItem","position":1,"name":"Home","item":SITE+"/"},
   {"@type":"ListItem","position":2,"name":"Woods We Use","item":SITE+"/woods-we-use"}]}, ensure_ascii=False) + '</script>')

h = rd(CF + "/wood-encyclopedia.html")   # already sitewide-renamed hrefs inside
cs = h.find('<header class="cwg__hero">')
ce = h.find('</section>', h.find('<section class="cwg__cta">')) + len('</section>')
assert cs > 0 and ce > cs
h = h[:cs] + HUB_CONTENT + h[ce:]
# swap old CollectionPage/Breadcrumb schema block(s)
olds = [s for s in re.findall(r'<script type="application/ld\+json">.*?</script>', h, re.S)
        if '"CollectionPage"' in s or ('"BreadcrumbList"' in s and 'Woods We Use' not in s and 'Resources' in s) or '"ItemList"' in s]
done = False
for s in re.findall(r'<script type="application/ld\+json">.*?</script>', h, re.S):
    if '"CollectionPage"' in s or '"ItemList"' in s or ('"BreadcrumbList"' in s and '"Resources"' in s):
        h = h.replace(s, NEW_SCHEMAS if not done else ''); done = True
def esc(s): return html.escape(s, quote=True)
h = re.sub(r'<title>[^<]*</title>', '<title>' + esc(HUB_TITLE) + '</title>', h, count=1)
h = re.sub(r'(name="description" content=")[^"]*', lambda m: m.group(1) + esc(HUB_DESC), h, count=1)
h = re.sub(r'((?:name|property)="(?:og|twitter):title" content=")[^"]*', lambda m: m.group(1) + esc(HUB_TITLE), h)
h = re.sub(r'((?:name|property)="(?:og|twitter):description" content=")[^"]*', lambda m: m.group(1) + esc(HUB_DESC), h)
wr(CF + "/woods-we-use.html", h)
os.remove(CF + "/wood-encyclopedia.html")
print("hub: woods-we-use.html written, wood-encyclopedia.html removed")

# ---------- 3. redirect ----------
wr(CF + "/_redirects", "/wood-encyclopedia /woods-we-use 301\n/wood-encyclopedia/* /woods-we-use 301\n")
print("_redirects written")

# ---------- 4. resources card copy ----------
rp = CF + "/resources.html"
t = rd(rp)
t = t.replace('<h3>Woods We Use</h3><p>Datasheets for 20 wood species',
              '<h3>Woods We Use</h3><p>Data sheets for the species behind our plywood &amp; timber')
wr(rp, t)

# ---------- 5. species pages: fix links to non-existent pages ----------
valid = {os.path.basename(p)[:-5] for p in glob.glob(CF + "/*.html")}
REMAP = {'/okoume-plywood': '/products'}
gg = [p for p in glob.glob(CF + "/blogs/post/wood-*.html")]
fixed = {}
for fp in gg:
    t = rd(fp); o = t
    for href in set(re.findall(r'href="(/[a-z0-9\-]+)"', t)):
        name = href[1:]
        if name not in valid and href not in ('/woods-we-use',):
            new = REMAP.get(href)
            if not new and os.path.exists(CF + '/blogs/post/' + name + '.html'): continue
            if not new:
                blog = 'guide-' in name and name.replace('guide-','') or None
                cand = [b for b in glob.glob(CF+'/blogs/post/*.html') if name.replace('guide-','') in os.path.basename(b)]
                new = '/blogs/post/' + os.path.basename(cand[0])[:-5] if cand else '/resources'
            t = t.replace(f'href="{href}"', f'href="{new}"')
            fixed[href] = new
    if t != o: wr(fp, t)
print("remapped links:", fixed)

# ---------- 6. product strips ----------
STRIP_MAP = {
 'commercial-plywood': [('Rubberwood','rubberwood'),('Eucalyptus','eucalyptus'),('Poplar','poplar'),('Silver oak','silver-oak')],
 'marine-plywood': [('Gurjan','gurjan'),('Okoume','okoume'),('Eucalyptus','eucalyptus')],
 'bwr-hardwood-plywood': [('Gurjan','gurjan'),('Eucalyptus','eucalyptus'),('Rubberwood','rubberwood')],
 'film-faced-shuttering-plywood': [('Eucalyptus','eucalyptus'),('Poplar','poplar'),('Gurjan','gurjan')],
 'plywood-boxes-crates': [('Okoume','okoume'),('Rubberwood','rubberwood'),('Pine','pine'),('Jackwood','jackwood'),('Mango','mango')],
 'plywood-pallets': [('Jackwood','jackwood'),('Mango','mango'),('Silver oak','silver-oak'),('Rubberwood','rubberwood')],
 'plywood-cable-drums': [('Rubberwood','rubberwood'),('Eucalyptus','eucalyptus'),('Pine','pine')],
 'container-flooring-plywood': [('Gurjan / Keruing','gurjan'),('Eucalyptus','eucalyptus'),('Acacia','acacia-mangium')],
 'block-board-flush-doors': [('Poplar','poplar'),('Rubberwood','rubberwood'),('Gmelina','gmelina'),('Semul','semul')],
 'finger-joint-board': [('Rubberwood','rubberwood')],
 'chequered-anti-skid-plywood': [('Eucalyptus','eucalyptus'),('Gurjan','gurjan'),('Poplar','poplar')],
 'sawn-timber': [('Jackwood','jackwood'),('Mango','mango'),('Silver oak','silver-oak'),('Sal','sal'),('Pine','pine')],
}
added = 0
for page, woods in STRIP_MAP.items():
    fp = CF + f"/{page}.html"
    t = rd(fp)
    if 'cw-woods-strip' in t: continue
    links = "".join(f'<li><a href="{post(f)}">{n}</a></li>' for n, f in woods)
    strip = ('<div class="cw-woods-strip"><span class="cw-woods-strip__label">The woods behind this product</span>'
             f'<ul class="cw-woods-strip__links">{links}'
             '<li><a class="cw-woods-strip__all" href="/woods-we-use">All woods we use &rarr;</a></li></ul></div>')
    i = t.rfind('<footer class="cw-ft"')
    assert i > 0, page
    t = t[:i] + strip + t[i:]
    wr(fp, t); added += 1
print("product strips added:", added)

css = rd(CF + "/zs-customcss.css")
if 'cw-woods-strip' not in css:
    css += """
/* woods-behind-this-product strip (mirrors geo-strip look) */
.cw-woods-strip{background:#f4f7f6;border-top:1px solid #e2e9e6;padding:18px 24px;text-align:center}
.cw-woods-strip__label{display:block;font-family:'Poppins',sans-serif;font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#5f6e76;margin-bottom:8px}
.cw-woods-strip__links{margin:0;padding:0;list-style:none;line-height:2}
.cw-woods-strip__links li{display:inline-block;margin:0;padding:0}
.cw-woods-strip__links a{display:inline-block;color:#007A5E;text-decoration:none;font-size:14px;font-weight:500;padding:0 13px;border-right:1px solid #dfe4e6;white-space:nowrap}
.cw-woods-strip__links li:last-child a{border-right:none}
.cw-woods-strip__links a:hover{text-decoration:underline}
.cw-woods-strip__all{font-weight:600}
@media(max-width:600px){.cw-woods-strip__links a{padding:0 10px;font-size:13px}}
"""
    wr(CF + "/zs-customcss.css", css)
    print("strip CSS added")

# ---------- 7. llms.txt + sitemap ----------
l = rd(CF + "/llms.txt")
l = l.replace("## Wood Encyclopedia (wood species reference)", "## Woods We Use (wood species reference)")
l = l.replace(SITE + "/wood-encyclopedia", SITE + "/woods-we-use")
wr(CF + "/llms.txt", l)
sm = rd(CF + "/sitemap-cms.xml").replace(SITE + "/wood-encyclopedia", SITE + "/woods-we-use")
wr(CF + "/sitemap-cms.xml", sm)
print("llms.txt + sitemap-cms updated")

# ---------- 8. sanity ----------
bad = 0
h = rd(CF + "/woods-we-use.html")
for k, v in {'20 cards': h.count('cwe__card') == 20 * 1 or h.count('class="cwe__card"') == 20,
             '3 groups': h.count('cwe__group') == 3,
             'no old name': 'Wood Encyclopedia' not in h,
             'canonical': 'canonical" href="https://www.cochinwood.in/woods-we-use"' in h,
             'cta anchored': '/contact#quote' in h,
             'CollectionPage': '"CollectionPage"' in h and '"Woods We Use"' in h}.items():
    if not v: print(" HUB FAIL", k); bad += 1
left = [fp for fp in glob.glob(CF + "/**/*.html", recursive=True) if '/wood-encyclopedia' in rd(fp)]
if left: print(" RESIDUAL old URL in:", [os.path.relpath(x, CF) for x in left[:5]]); bad += 1
lbl = [fp for fp in glob.glob(CF + "/**/*.html", recursive=True) if 'Wood Encyclopedia' in rd(fp)]
if lbl: print(" RESIDUAL old label in:", [os.path.relpath(x, CF) for x in lbl[:5]]); bad += 1
for f in ["sitemap-cms.xml"]:
    import xml.etree.ElementTree as ET
    try: ET.fromstring(rd(CF + "/" + f))
    except Exception as e: print(" XML FAIL", f, e); bad += 1
ok = rd(CF + "/blogs/post/wood-okoume-aucoumea-klaineana.html")
for k, v in {'category renamed': '> Woods We Use</a>' in ok, 'isPartOf renamed': '"name": "Woods We Use"' in ok,
             'okoume-plywood fixed': '/okoume-plywood' not in ok}.items():
    if not v: print(" SPECIES FAIL", k); bad += 1
print("SANITY:", "ALL PASS" if bad == 0 else f"{bad} ISSUES")
