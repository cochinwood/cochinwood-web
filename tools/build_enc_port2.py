import os, re, json, sys, html, glob
sys.stdout.reconfigure(encoding='utf-8')

CF  = r"C:/Users/EDWIND~1/AppData/Local/Temp/claude/_cfmirror"
WT  = r"C:/Users/Edwin David/Claude Code/.claude/worktrees/inspiring-chaum-ea03ed/website-preview/wood-encyclopedia"
ENC = r"C:/Users/Edwin David/cochinwood-web/content/encyclopedia"
SITE = "https://www.cochinwood.in"

def rd(p): return open(p, encoding='utf-8').read()
def wr(p, t): open(p, 'w', encoding='utf-8').write(t)
def esc(s): return html.escape(s, quote=True)
def jesc(s): return json.dumps(s, ensure_ascii=False)[1:-1]

# ---------- species metadata + bodies (same as v1) ----------
posts = json.load(open(WT + "/_bodies/posts.json", encoding='utf-8'))
meta = {p['file']: {'title': p['title'], 'slug': p['slug'], 'summary': p['summary']} for p in posts}
LD = re.compile(r'<script type="application/ld\+json">.*?</script>', re.S)
def page_to_body(t):
    s = t.find('</header>'); e = t.rfind('</body>')
    body = t[s + len('</header>'):e]
    return LD.sub(lambda m: m.group(0) if '"FAQPage"' in m.group(0) else '', body).strip()
wave2 = {'meranti':'wood-meranti-shorea','gmelina':'wood-gmelina-arborea',
         'melia-dubia':'wood-melia-dubia-malabar-neem','acacia-mangium':'wood-acacia-mangium',
         'semul':'wood-semul-bombax-ceiba'}
bodies = {f: rd(WT + f"/_bodies/{f}.body.html") for f in meta}
for f, slug in wave2.items():
    t = rd(ENC + f"/{f}.html")
    ttl = html.unescape(re.search(r'<title>([^<]+)</title>', t).group(1))
    ttl = re.sub(r'\s*\|\s*Cochin Wood.*$', '', ttl).strip()
    desc = html.unescape(re.search(r'name="description" content="([^"]+)"', t).group(1))
    meta[f] = {'title': ttl, 'slug': slug, 'summary': desc}
    bodies[f] = page_to_body(t)

# FIX 3: old clean-build URL scheme -> blog slugs, in every body
name2slug = {f: m['slug'] for f, m in meta.items()}
# also map plain species names used in hrefs (e.g. /wood-encyclopedia/pine)
XLINK = re.compile(r'href="/wood-encyclopedia/([a-z\-]+)"')
def fix_xlinks(b):
    def sub(m):
        n = m.group(1)
        if n in name2slug: return f'href="/blogs/post/{name2slug[n]}"'
        print("  !! unmapped cross-link:", n); return m.group(0)
    return XLINK.sub(sub, b)
bodies = {f: fix_xlinks(b) for f, b in bodies.items()}

# ---------- donor prep ----------
don = rd(CF + "/blogs/post/how-plywood-is-made.html")
# FIX 1: strip the Zoho schemagenerator BlogPosting (we inject our own)
don2 = re.sub(r'<script type="application/ld\+json" id="schemagenerator">.*?</script>', '', don, flags=re.S)
assert 'schemagenerator' not in don2
# FIX 5: dedupe doubled fonts.css link
don2 = don2.replace('<link rel="stylesheet" href="/assets/fonts.css">', '@@FONTS@@', 1)
don2 = don2.replace('<link rel="stylesheet" href="/assets/fonts.css">', '')
don2 = don2.replace('@@FONTS@@', '<link rel="stylesheet" href="/assets/fonts.css">')

DON_URL  = SITE + "/blogs/post/how-plywood-is-made"
DON_PATH = "/blogs/post/how-plywood-is-made"
DON_T1   = "How Plywood Is Made | Cochin Wood Industries"
DON_T2   = "How Plywood Is Made - Cochin Wood Industries"
DON_H1   = "How Plywood Is Made"
c_start = don2.find('<div class="theme-blog-part theme-blog-post-content">')
c_end   = don2.find('<div class="theme-blog-part theme-blog-post-footer-area">')
assert c_start > 0 and c_end > c_start

built = 0
for f, m in meta.items():
    slug, title, summ = m['slug'], m['title'], m['summary']
    url = f"{SITE}/blogs/post/{slug}"
    t = don2[:c_start] + ('<div class="theme-blog-part theme-blog-post-content">'
        '<div class="zpcontent-container blogpost-container ">' + bodies[f] + '</div></div>') + don2[c_end:]

    # plain + JSON-escaped donor URL/path (FIX 2)
    t = t.replace(DON_URL, url).replace(DON_PATH, f"/blogs/post/{slug}")
    t = t.replace(DON_URL.replace('/', '\\/'), url.replace('/', '\\/'))
    t = t.replace(DON_PATH.replace('/', '\\/'), f"/blogs/post/{slug}".replace('/', '\\/'))

    t = t.replace('<title>' + DON_T1 + '</title>', '<title>' + esc(title) + '</title>')
    t = t.replace(DON_T2, esc(title))
    t = re.sub(r'(name="description" content=")[^"]*', lambda mm: mm.group(1) + esc(summ), t, count=1)
    t = re.sub(r'((?:name|property)="(?:og|twitter):description" content=")[^"]*',
               lambda mm: mm.group(1) + esc(summ), t)
    t = t.replace('data-post-heading="true">' + DON_H1 + '</h1>',
                  'data-post-heading="true">' + esc(title) + '</h1>')
    t = t.replace(' 11.06.26 04:11 AM ', ' 02.07.26 09:00 AM ')
    t = t.replace('>' + DON_H1 + '<', '>' + esc(title) + '<')

    # FIX 2: zs_post_details residue
    t = re.sub(r'("user_summary":")(?:[^"\\]|\\.)*(")',
               lambda mm: mm.group(1) + jesc(summ).replace('\\', '\\\\') if False else mm.group(1) + jesc(summ) + mm.group(2), t)
    t = re.sub(r'("post_published_time":")[^"]*(")', r'\g<1>2026-07-02T09:00:00Z\g<2>', t)

    t = t.replace('<a href="/blogs/buyer-guides"> Buyer Guides</a>',
                  '<a href="/wood-encyclopedia"> Wood Encyclopedia</a>')

    bp = json.dumps({"@context":"https://schema.org","@type":"BlogPosting","headline":title,
        "description":summ,"url":url,"mainEntityOfPage":url,"datePublished":"2026-07-02",
        "dateModified":"2026-07-02","inLanguage":"en",
        "author":{"@type":"Organization","name":"Cochin Wood Industries","url":SITE+"/"},
        "publisher":{"@id":SITE+"/#localbusiness"},
        "isPartOf":{"@type":"CollectionPage","name":"Wood Encyclopedia","url":SITE+"/wood-encyclopedia"}},
        ensure_ascii=False)
    t = t.replace('</head>', '<script type="application/ld+json">' + bp + '</script></head>', 1)
    wr(CF + f"/blogs/post/{slug}.html", t)
    built += 1
print("blog pages rebuilt:", built)

# ---------- hub (corrected boundary, dedupe fonts) ----------
r = rd(CF + "/resources.html")
hub = rd(ENC + "/_hub.html")
hs = hub.find('<header class="cwg__hero">')
he = hub.find('</section>', hub.find('<section class="cwg__cta">')) + len('</section>')
hub_content = hub[hs:he]
hub_content = re.sub(r'href="[a-z\-]+\.html" data-slug="([^"]+)"', r'href="\1"', hub_content)
hub_content = hub_content.replace(' <em>(Preview: cards link to local files; on publish they point to /blogs/post/&lt;slug&gt;.)</em>', '')
hub_schemas = "\n".join(re.findall(r'<script type="application/ld\+json">.*?</script>', hub, re.S))
sec_starts = [x.start() for x in re.finditer(r'<section', r)]
cstart = max(s for s in sec_starts if s < r.find('class="cw__page-hero'))
strip_attr = [x.start() for x in re.finditer(r'<section[^>]+cwg__blog-strip', r)]
cend = r.find('</section>', strip_attr[-1]) + len('</section>')
t = r[:cstart] + hub_content + r[cend:]
repl = False
for s in re.findall(r'<script type="application/ld\+json">.*?</script>', t, re.S):
    if '"CollectionPage"' in s or '"ItemList"' in s:
        t = t.replace(s, hub_schemas if not repl else ''); repl = True
HUB_TITLE = "Wood Encyclopedia: Plywood & Timber Species Guide | Cochin Wood"
HUB_DESC = ("A working reference to the wood species behind plywood, packing and timber — density, hardness, "
            "workability, durability and uses. Independently researched and cross-checked by Cochin Wood Industries.")
t = t.replace(SITE + "/resources", SITE + "/wood-encyclopedia")
t = re.sub(r'<title>[^<]*</title>', '<title>' + esc(HUB_TITLE) + '</title>', t, count=1)
t = re.sub(r'(name="description" content=")[^"]*', lambda mm: mm.group(1) + esc(HUB_DESC), t, count=1)
t = re.sub(r'((?:name|property)="(?:og|twitter):title" content=")[^"]*', lambda mm: mm.group(1) + esc(HUB_TITLE), t)
t = re.sub(r'((?:name|property)="(?:og|twitter):description" content=")[^"]*', lambda mm: mm.group(1) + esc(HUB_DESC), t)
t = t.replace('<link rel="stylesheet" href="/assets/fonts.css">', '@@F@@', 1).replace('<link rel="stylesheet" href="/assets/fonts.css">', '').replace('@@F@@', '<link rel="stylesheet" href="/assets/fonts.css">')
wr(CF + "/wood-encyclopedia.html", t)
print("hub rebuilt")

# ---------- FIX 5 sitewide: dedupe fonts.css on all remaining pages ----------
deduped = 0
for fp in glob.glob(CF + "/**/*.html", recursive=True):
    t = rd(fp)
    if t.count('<link rel="stylesheet" href="/assets/fonts.css">') > 1:
        t = t.replace('<link rel="stylesheet" href="/assets/fonts.css">', '@@F@@', 1).replace('<link rel="stylesheet" href="/assets/fonts.css">', '').replace('@@F@@', '<link rel="stylesheet" href="/assets/fonts.css">')
        wr(fp, t); deduped += 1
print("fonts.css deduped on", deduped, "pages")

# ---------- FIX 4: sitemap children (index untouched) ----------
cms = rd(CF + "/sitemap-cms.xml")
if "/wood-encyclopedia</loc>" not in cms:
    cms = cms.replace("</urlset>", f"<url><loc>{SITE}/wood-encyclopedia</loc><lastmod>2026-07-02</lastmod><priority>0.7</priority></url></urlset>")
    wr(CF + "/sitemap-cms.xml", cms); print("sitemap-cms: +1 (hub)")
post = rd(CF + "/sitemap-post.xml")
add = [f"{SITE}/blogs/post/{m['slug']}" for m in meta.values() if f"<loc>{SITE}/blogs/post/{m['slug']}</loc>" not in post]
post = post.replace("</urlset>", "".join(f"<url><loc>{u}</loc><lastmod>2026-07-02</lastmod></url>" for u in add) + "</urlset>")
wr(CF + "/sitemap-post.xml", post); print(f"sitemap-post: +{len(add)}")
# revert any stray urls my v1 script may have put in the INDEX (defensive)
idx = rd(CF + "/sitemap.xml")
idx2 = re.sub(r'<url><loc>[^<]*</loc><lastmod>[^<]*</lastmod></url>', '', idx)
if idx2 != idx: wr(CF + "/sitemap.xml", idx2); print("sitemap index: cleaned stray <url> entries")

# ---------- FIX 6: llms.txt ----------
l = rd(CF + "/llms.txt")
if 'wood-encyclopedia' not in l:
    sec = "\n## Wood Encyclopedia (wood species reference)\nIndependently researched, cross-checked species datasheets (density, hardness, workability, durability, uses), with cited sources.\n- Hub: https://www.cochinwood.in/wood-encyclopedia\n"
    sec += "".join(f"- {m['title']}: {SITE}/blogs/post/{m['slug']}\n" for m in meta.values())
    marker = "- Last updated:"
    if marker in l:
        l = l.replace(marker, sec + "\n" + marker).replace("Last updated: 2026-06-24", "Last updated: 2026-07-03")
    else:
        l += sec
    wr(CF + "/llms.txt", l); print("llms.txt: encyclopedia section added")

# ---------- sanity ----------
bad = 0
for f, m in meta.items():
    t = rd(CF + f"/blogs/post/{m['slug']}.html")
    checks = {
        'zero donor slug': 'how-plywood-is-made' not in t,
        'zero donor title': 'How Plywood Is Made' not in t,
        'no schemagenerator': 'schemagenerator' not in t,
        'single fonts.css': t.count('href="/assets/fonts.css"') == 1,
        'no old xlinks': not XLINK.search(t),
        'blogposting once': t.count('"BlogPosting"') == 1,
        'faq schema': '"FAQPage"' in t,
        'title': esc(m['title']) in t,
        'summary in zs_post_details': jesc(m['summary'])[:40] in t,
        'date patched': '2026-07-02T09:00:00Z' in t and '2026-06-11' not in t,
        'footer link': '/wood-encyclopedia">Wood Encyclopedia<' in t,
        'spec card': 'cwe__spec' in t,
    }
    fails = [k for k, v in checks.items() if not v]
    if fails: print(" FAIL", f, fails); bad += 1
h = rd(CF + "/wood-encyclopedia.html")
for k, v in {'20 cards': h.count('cwe__card') >= 20, 'no leftovers': 'From our notebook' not in h,
             'CollectionPage': '"CollectionPage"' in h, 'single fonts': h.count('href="/assets/fonts.css"') == 1}.items():
    if not v: print(" HUB FAIL", k); bad += 1
import xml.etree.ElementTree as ET
for f in ["sitemap.xml", "sitemap-cms.xml", "sitemap-post.xml"]:
    try: ET.fromstring(rd(CF + "/" + f))
    except Exception as e: print(" XML FAIL", f, e); bad += 1
print("SANITY:", "ALL PASS" if bad == 0 else f"{bad} FAILURES")
