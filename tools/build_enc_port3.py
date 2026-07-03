import os, re, json, sys, html
sys.stdout.reconfigure(encoding='utf-8')
CF  = r"C:/Users/EDWIND~1/AppData/Local/Temp/claude/_cfmirror"
WT  = r"C:/Users/Edwin David/Claude Code/.claude/worktrees/inspiring-chaum-ea03ed/website-preview/wood-encyclopedia"
ENC = r"C:/Users/Edwin David/cochinwood-web/content/encyclopedia"
SITE = "https://www.cochinwood.in"
def rd(p): return open(p, encoding='utf-8').read()
def wr(p, t): open(p, 'w', encoding='utf-8').write(t)
def esc(s): return html.escape(s, quote=True)
def jesc(s): return json.dumps(s, ensure_ascii=False)[1:-1]

posts = json.load(open(WT + "/_bodies/posts.json", encoding='utf-8'))
meta = {p['file']: {'title': p['title'], 'slug': p['slug'], 'summary': p['summary']} for p in posts}
LD = re.compile(r'<script type="application/ld\+json">.*?</script>', re.S)
def page_to_body(t):
    s = t.find('</header>'); e = t.rfind('</body>')
    return LD.sub(lambda m: m.group(0) if '"FAQPage"' in m.group(0) else '', t[s+9:e]).strip()
wave2 = {'meranti':'wood-meranti-shorea','gmelina':'wood-gmelina-arborea',
         'melia-dubia':'wood-melia-dubia-malabar-neem','acacia-mangium':'wood-acacia-mangium',
         'semul':'wood-semul-bombax-ceiba'}
bodies = {f: rd(WT + f"/_bodies/{f}.body.html") for f in meta}
for f, slug in wave2.items():
    t = rd(ENC + f"/{f}.html")
    ttl = re.sub(r'\s*\|\s*Cochin Wood.*$', '', html.unescape(re.search(r'<title>([^<]+)</title>', t).group(1))).strip()
    desc = html.unescape(re.search(r'name="description" content="([^"]+)"', t).group(1))
    meta[f] = {'title': ttl, 'slug': slug, 'summary': desc}
    bodies[f] = page_to_body(t)

name2slug = {f: m['slug'] for f, m in meta.items()}
REMAP = {'/okoume-plywood': '/products',
         '/guide-okoume-vs-gurjan': '/blogs/post/birch-vs-okoume-vs-gurjan-pick-the-right-face-veneer-for-export-packing'}
def fix_body(b):
    b = re.sub(r'href="/wood-encyclopedia/([a-z\-]+)"',
               lambda m: f'href="/blogs/post/{name2slug[m.group(1)]}"' if m.group(1) in name2slug else m.group(0), b)
    b = b.replace('href="/wood-encyclopedia"', 'href="/woods-we-use"')
    b = b.replace('>Wood Encyclopedia<', '>Woods We Use<').replace('> Wood Encyclopedia<', '> Woods We Use<')
    for k, v in REMAP.items(): b = b.replace(f'href="{k}"', f'href="{v}"')
    return b
bodies = {f: fix_body(b) for f, b in bodies.items()}

don = rd(CF + "/blogs/post/how-plywood-is-made.html")
don2 = re.sub(r'<script type="application/ld\+json" id="schemagenerator">.*?</script>', '', don, flags=re.S)
assert 'schemagenerator' not in don2
DON_URL, DON_PATH = SITE + "/blogs/post/how-plywood-is-made", "/blogs/post/how-plywood-is-made"
DON_T1, DON_T2, DON_H1 = "How Plywood Is Made | Cochin Wood Industries", "How Plywood Is Made - Cochin Wood Industries", "How Plywood Is Made"
c_start = don2.find('<div class="theme-blog-part theme-blog-post-content">')
c_end   = don2.find('<div class="theme-blog-part theme-blog-post-footer-area">')
assert c_start > 0 and c_end > c_start
CTA = re.compile(r'(<a[^>]*href=")/contact("[^>]*>(?:(?!</a>).){0,160}?Request a [qQ]uote)', re.S)

built = 0
for f, m in meta.items():
    slug, title, summ = m['slug'], m['title'], m['summary']
    url = f"{SITE}/blogs/post/{slug}"
    t = don2[:c_start] + ('<div class="theme-blog-part theme-blog-post-content">'
        '<div class="zpcontent-container blogpost-container ">' + bodies[f] + '</div></div>') + don2[c_end:]
    t = t.replace(DON_URL, url).replace(DON_PATH, f"/blogs/post/{slug}")
    t = t.replace(DON_URL.replace('/', '\\/'), url.replace('/', '\\/'))
    t = t.replace(DON_PATH.replace('/', '\\/'), f"/blogs/post/{slug}".replace('/', '\\/'))
    t = t.replace('<title>' + DON_T1 + '</title>', '<title>' + esc(title) + '</title>')
    t = t.replace(DON_T2, esc(title))
    t = re.sub(r'(name="description" content=")[^"]*', lambda mm: mm.group(1) + esc(summ), t, count=1)
    t = re.sub(r'((?:name|property)="(?:og|twitter):description" content=")[^"]*', lambda mm: mm.group(1) + esc(summ), t)
    t = t.replace('data-post-heading="true">' + DON_H1 + '</h1>', 'data-post-heading="true">' + esc(title) + '</h1>')
    t = t.replace(' 11.06.26 04:11 AM ', ' 02.07.26 09:00 AM ')
    t = t.replace('>' + DON_H1 + '<', '>' + esc(title) + '<')
    t = re.sub(r'("user_summary":")(?:[^"\\]|\\.)*(")', lambda mm: mm.group(1) + jesc(summ) + mm.group(2), t)
    t = re.sub(r'("post_published_time":")[^"]*(")', r'\g<1>2026-07-02T09:00:00Z\g<2>', t)
    t = t.replace('<a href="/blogs/buyer-guides"> Buyer Guides</a>', '<a href="/woods-we-use"> Woods We Use</a>')
    t = CTA.sub(r'\g<1>/contact#quote\g<2>', t)
    bp = json.dumps({"@context":"https://schema.org","@type":"BlogPosting","headline":title,
        "description":summ,"url":url,"mainEntityOfPage":url,"datePublished":"2026-07-02",
        "dateModified":"2026-07-02","inLanguage":"en",
        "author":{"@type":"Organization","name":"Cochin Wood Industries","url":SITE+"/"},
        "publisher":{"@id":SITE+"/#localbusiness"},
        "isPartOf":{"@type":"CollectionPage","name":"Woods We Use","url":SITE+"/woods-we-use"}}, ensure_ascii=False)
    t = t.replace('</head>', '<script type="application/ld+json">' + bp + '</script></head>', 1)
    wr(CF + f"/blogs/post/{slug}.html", t)
    built += 1
print("species pages regenerated:", built)

# sanity
bad = 0
valid_root = {os.path.basename(p)[:-5] for p in __import__('glob').glob(CF + "/*.html")}
for f, m in meta.items():
    t = rd(CF + f"/blogs/post/{m['slug']}.html")
    ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S)
    checks = {
        'donor residue': 'how-plywood-is-made' not in t and 'How Plywood Is Made' not in t and 'schemagenerator' not in t,
        'one BlogPosting': sum(1 for x in ld if '"BlogPosting"' in x) == 1,
        'faq': any('"FAQPage"' in x for x in ld),
        'new hub name': '/woods-we-use' in t and '/wood-encyclopedia' not in t,
        'category': '<a href="/woods-we-use"> Woods We Use</a>' in t,
        'cta anchored': '/contact#quote' in t,
        'isPartOf': '"name": "Woods We Use"' in t or '"name":"Woods We Use"' in t,
        'no theme-menu damage': 'href="/about-us"' in t and 'href="/privacy"' in t,  # donor chrome intact (redirects handle)
        'single fonts': t.count('href="/assets/fonts.css"') == 1,
        'date': '2026-07-02T09:00:00Z' in t,
    }
    # internal single-segment links must exist as files or be redirect aliases
    alias = {'about-us','privacy','terms','contact-us','blogs','woods-we-use'}
    for href in set(re.findall(r'href="/([a-z0-9\-]+)"', t)):
        if href not in valid_root and href not in alias:
            checks[f'broken:/{href}'] = False
    fails = [k for k, v in checks.items() if not v]
    if fails: print(" FAIL", f, fails); bad += 1
print("SANITY v3:", "ALL 20 PASS" if bad == 0 else f"{bad} FAILURES")
