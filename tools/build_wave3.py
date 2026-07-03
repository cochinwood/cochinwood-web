import os, re, json, sys, html, glob
sys.stdout.reconfigure(encoding='utf-8')
CF = r"C:/Users/EDWIND~1/AppData/Local/Temp/claude/_cfmirror"
B3 = r"C:/Users/Edwin David/Claude Code/.claude/worktrees/inspiring-chaum-ea03ed/website-preview/wood-encyclopedia/_bodies3"
SITE = "https://www.cochinwood.in"
def rd(p): return open(p, encoding='utf-8').read()
def wr(p, t): open(p, 'w', encoding='utf-8').write(t)
def esc(s): return html.escape(s, quote=True)
def jesc(s): return json.dumps(s, ensure_ascii=False)[1:-1]
def un(s): return html.unescape(s)

METAS = [
 {"file":"casuarina","title":"Casuarina Wood (Casuarina equisetifolia): Properties, Density & Uses","slug":"wood-casuarina-equisetifolia","summary":"Casuarina (Casuarina equisetifolia): heavy, dense coastal hardwood at ~900-1000 kg/m3 - density, hardness, seasoning, durability and its packing-timber uses."},
 {"file":"subabul","title":"Subabul Wood (Leucaena leucocephala): Properties, Density & Uses","slug":"wood-subabul-leucaena-leucocephala","summary":"Subabul (Leucaena leucocephala): medium-density plantation wood (~500-650 kg/m3) that seasons well and treats easily — for packing cases, pallets and ply core."},
 {"file":"anjili","title":"Anjili (Wild Jack) Wood (Artocarpus hirsutus): Properties, Density & Uses","slug":"wood-anjili-artocarpus-hirsutus","summary":"Anjili (Wild Jack, Artocarpus hirsutus): a Western Ghats hardwood with teak-class strength (~600 kg/m3), very high durability, ideal for packing cases."},
 {"file":"matti","title":"Matti (Indian Laurel) Wood (Terminalia elliptica): Properties, Density & Uses","slug":"wood-matti-terminalia-elliptica","summary":"Matti (Indian laurel, Terminalia elliptica): a heavy, hard 800-870 kg/m3 hardwood for heavy-duty packing cases, pallets, sawn timber. Uses, density, sourcing."},
 {"file":"irul","title":"Irul (Pyinkado) Wood (Xylia xylocarpa): Properties, Density & Uses","slug":"wood-irul-xylia-xylocarpa","summary":"Irul (Pyinkado / Burma Ironwood, Xylia xylocarpa) is one of India's heaviest, most durable hardwoods - its properties, density, working traits and packing uses."},
 {"file":"venteak","title":"Venteak Wood (Lagerstroemia microcarpa): Properties, Density & Uses","slug":"wood-venteak-lagerstroemia-microcarpa","summary":"Venteak (benteak, Lagerstroemia microcarpa) is a Western Ghats teak substitute at ~640 kg/m3. Properties, density, seasoning, durability and packing uses."},
 {"file":"kadam","title":"Kadam Wood (Neolamarckia cadamba): Properties, Density & Uses","slug":"wood-kadam-neolamarckia-cadamba","summary":"Kadam (Neolamarckia cadamba): a light, fast-growing Indian plantation hardwood for plywood core veneer and packing cases. Density, strength, durability & uses."},
 {"file":"pala","title":"Pala (White Cheesewood) Wood (Alstonia scholaris): Properties, Density & Uses","slug":"wood-pala-alstonia-scholaris","summary":"Pala (white cheesewood, Alstonia scholaris) is a light, soft, low-density wood for packing cases, match splints and plywood core. Density, durability & uses."},
]
json.dump(METAS, open(B3 + "/posts3.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# ---------- build the 8 pages from the donor (same recipe as v3) ----------
don = rd(CF + "/blogs/post/how-plywood-is-made.html")
don2 = re.sub(r'<script type="application/ld\+json" id="schemagenerator">.*?</script>', '', don, flags=re.S)
DON_URL, DON_PATH = SITE + "/blogs/post/how-plywood-is-made", "/blogs/post/how-plywood-is-made"
DON_T1, DON_T2, DON_H1 = "How Plywood Is Made | Cochin Wood Industries", "How Plywood Is Made - Cochin Wood Industries", "How Plywood Is Made"
c_start = don2.find('<div class="theme-blog-part theme-blog-post-content">')
c_end   = don2.find('<div class="theme-blog-part theme-blog-post-footer-area">')
CTA = re.compile(r'(<a[^>]*href=")/contact("[^>]*>(?:(?!</a>).){0,160}?Request a [qQ]uote)', re.S)
built = 0
for m in METAS:
    slug, title, summ = m['slug'], un(m['title']), un(m['summary'])
    body = rd(B3 + f"/{m['file']}.body.html")
    url = f"{SITE}/blogs/post/{slug}"
    t = don2[:c_start] + ('<div class="theme-blog-part theme-blog-post-content">'
        '<div class="zpcontent-container blogpost-container ">' + body + '</div></div>') + don2[c_end:]
    t = t.replace(DON_URL, url).replace(DON_PATH, f"/blogs/post/{slug}")
    t = t.replace(DON_URL.replace('/', '\\/'), url.replace('/', '\\/'))
    t = t.replace(DON_PATH.replace('/', '\\/'), f"/blogs/post/{slug}".replace('/', '\\/'))
    t = t.replace('<title>' + DON_T1 + '</title>', '<title>' + esc(title) + '</title>')
    t = t.replace(DON_T2, esc(title))
    t = re.sub(r'(name="description" content=")[^"]*', lambda mm: mm.group(1) + esc(summ), t, count=1)
    t = re.sub(r'((?:name|property)="(?:og|twitter):description" content=")[^"]*', lambda mm: mm.group(1) + esc(summ), t)
    t = t.replace('data-post-heading="true">' + DON_H1 + '</h1>', 'data-post-heading="true">' + esc(title) + '</h1>')
    t = t.replace(' 11.06.26 04:11 AM ', ' 03.07.26 09:00 AM ')
    t = t.replace('>' + DON_H1 + '<', '>' + esc(title) + '<')
    t = re.sub(r'("user_summary":")(?:[^"\\]|\\.)*(")', lambda mm: mm.group(1) + jesc(summ) + mm.group(2), t)
    t = re.sub(r'("post_published_time":")[^"]*(")', r'\g<1>2026-07-03T09:00:00Z\g<2>', t)
    t = t.replace('<a href="/blogs/buyer-guides"> Buyer Guides</a>', '<a href="/woods-we-use"> Woods We Use</a>')
    t = CTA.sub(r'\g<1>/contact#quote\g<2>', t)
    bp = json.dumps({"@context":"https://schema.org","@type":"BlogPosting","headline":title,
        "description":summ,"url":url,"mainEntityOfPage":url,"datePublished":"2026-07-03",
        "dateModified":"2026-07-03","inLanguage":"en",
        "author":{"@type":"Organization","name":"Cochin Wood Industries","url":SITE+"/"},
        "publisher":{"@id":SITE+"/#localbusiness"},
        "isPartOf":{"@type":"CollectionPage","name":"Woods We Use","url":SITE+"/woods-we-use"}}, ensure_ascii=False)
    t = t.replace('</head>', '<script type="application/ld+json">' + bp + '</script></head>', 1)
    wr(CF + f"/blogs/post/{slug}.html", t)
    built += 1
print("wave-3 pages built:", built)

# ---------- hub: expand the Kerala timbers group to 14 cards ----------
def card(name, sci, slug):
    return (f'<a class="cwe__card" href="/blogs/post/{slug}"><p class="cwe__card-name">{name}</p>'
            f'<p class="cwe__card-sci">{sci}</p><span class="cwe__card-tag">Data sheet</span></a>')
TIMBERS = [
 ('Jackwood','Artocarpus heterophyllus','wood-jackwood-artocarpus-heterophyllus'),
 ('Anjili (Wild Jack)','Artocarpus hirsutus','wood-anjili-artocarpus-hirsutus'),
 ('Mango','Mangifera indica','wood-mango-mangifera-indica'),
 ('Silver oak','Grevillea robusta','wood-silver-oak-grevillea-robusta'),
 ('Matti (Indian Laurel)','Terminalia elliptica','wood-matti-terminalia-elliptica'),
 ('Irul (Pyinkado)','Xylia xylocarpa','wood-irul-xylia-xylocarpa'),
 ('Venteak','Lagerstroemia microcarpa','wood-venteak-lagerstroemia-microcarpa'),
 ('Casuarina','Casuarina equisetifolia','wood-casuarina-equisetifolia'),
 ('Subabul','Leucaena leucocephala','wood-subabul-leucaena-leucocephala'),
 ('Kadam','Neolamarckia cadamba','wood-kadam-neolamarckia-cadamba'),
 ('Pala (White Cheesewood)','Alstonia scholaris','wood-pala-alstonia-scholaris'),
 ('Semul (Silk Cotton)','Bombax ceiba','wood-semul-bombax-ceiba'),
 ('Sal','Shorea robusta','wood-sal-shorea-robusta'),
 ('Pine','Pinus spp.','wood-pine-pinus'),
]
h = rd(CF + "/woods-we-use.html")
gs = h.find('Kerala &amp; plantation timbers we saw for packing')
grid_s = h.find('<div class="cwe__grid">', gs)
grid_e = h.find('</div></div>', grid_s)  # grid close + group close
assert gs > 0 and grid_s > gs and grid_e > grid_s
h = h[:grid_s] + '<div class="cwe__grid">' + "".join(card(*t) for t in TIMBERS) + h[grid_e:]
wr(CF + "/woods-we-use.html", h)
print("hub Kerala group:", h.count('class="cwe__card"'), "cards total")

# ---------- sawn-timber strip: add key Kerala woods ----------
st = rd(CF + "/sawn-timber.html")
old = '<li><a href="/blogs/post/wood-jackwood-artocarpus-heterophyllus">Jackwood</a></li>'
addl = ('<li><a href="/blogs/post/wood-anjili-artocarpus-hirsutus">Anjili</a></li>'
        '<li><a href="/blogs/post/wood-matti-terminalia-elliptica">Matti</a></li>'
        '<li><a href="/blogs/post/wood-irul-xylia-xylocarpa">Irul</a></li>'
        '<li><a href="/blogs/post/wood-casuarina-equisetifolia">Casuarina</a></li>')
if 'wood-anjili' not in st:
    st = st.replace(old, old + addl, 1)
    wr(CF + "/sawn-timber.html", st); print("sawn-timber strip extended")

# ---------- sitemap + llms ----------
post = rd(CF + "/sitemap-post.xml")
add = [m for m in METAS if f"/blogs/post/{m['slug']}</loc>" not in post]
post = post.replace("</urlset>", "".join(f"<url><loc>{SITE}/blogs/post/{m['slug']}</loc><lastmod>2026-07-03</lastmod></url>" for m in add) + "</urlset>")
wr(CF + "/sitemap-post.xml", post); print(f"sitemap-post: +{len(add)}")
l = rd(CF + "/llms.txt")
marker = "- Last updated:"
sec = "".join(f"- {un(m['title'])}: {SITE}/blogs/post/{m['slug']}\n" for m in METAS if m['slug'] not in l)
l = l.replace(marker, sec + marker)
wr(CF + "/llms.txt", l); print("llms.txt: +8")

# ---------- sanity ----------
bad = 0
valid_root = {os.path.basename(p)[:-5] for p in glob.glob(CF + "/*.html")}
alias = {'about-us','privacy','terms','contact-us','blogs','woods-we-use'}
for m in METAS:
    t = rd(CF + f"/blogs/post/{m['slug']}.html")
    ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S)
    checks = {
        'donor residue': 'how-plywood-is-made' not in t and 'How Plywood Is Made' not in t and 'schemagenerator' not in t,
        'one BlogPosting': sum(1 for x in ld if '"BlogPosting"' in x) == 1,
        'faq': any('"FAQPage"' in x for x in ld),
        'spec card': 'cwe__spec' in t, 'refs': 'cwe__refs' in t,
        'cta anchored': '/contact#quote' in t,
        'no h1 in body': t.count('<h1') == 1,
        'category': '<a href="/woods-we-use"> Woods We Use</a>' in t,
    }
    for href in set(re.findall(r'href="/([a-z0-9\-]+)"', t)):
        if href not in valid_root and href not in alias: checks[f'broken:/{href}'] = False
    # citation integrity
    cites = set(re.findall(r'href="#(ref\d+)"', t)); ids = set(re.findall(r'id="(ref\d+)"', t))
    checks['citation ids'] = cites <= ids
    fails = [k for k, v in checks.items() if not v]
    if fails: print(" FAIL", m['file'], fails); bad += 1
h = rd(CF + "/woods-we-use.html")
if h.count('class="cwe__card"') != 28: print(" HUB FAIL: cards =", h.count('class="cwe__card"')); bad += 1
import xml.etree.ElementTree as ET
try: ET.fromstring(rd(CF + "/sitemap-post.xml"))
except Exception as e: print(" XML FAIL", e); bad += 1
print("SANITY wave-3:", "ALL PASS" if bad == 0 else f"{bad} FAILURES")
