#!/usr/bin/env python3
"""Port the nine live /export pages into content/export/ (data + prose).

Run once against a checkout of the cf-live branch:

    python tools/extract_export_live.py <path-to-cf-live-checkout>

It reads export.html and export/<slug>.html, splits each page into the parts
that are genuinely per-country and the parts that are boilerplate repeated
nine times, and writes:

    content/export/export.json        structured data, one entry per lane
    content/export/<slug>.body.html   that lane's own prose, verbatim

The boilerplate (hero scaffolding, byline, factory badge, import-essentials
table skeleton, the four templated import FAQs, the warehouse FAQ, the
"other export destinations" block, breadcrumbs and FAQPage schema) is NOT
written out per country — export_section.py regenerates it. Nothing here
rewrites the words: every string lands in the JSON exactly as it shipped.

This script is provenance, not part of the build. build.py never calls it.
"""
import os, re, sys, json, html

SLUGS = ["uae", "saudi-arabia", "qatar", "oman", "kuwait", "bahrain",
         "sri-lanka", "israel"]

def main_body(raw):
    """The Zoho code-snippet payload: everything the page actually says."""
    i = raw.find('id="thememaincontent"')
    j = raw.find('<!-- CWI static footer')
    seg = raw[i:j if j > 0 else len(raw)]
    k = seg.find('<div class="zpsnippet-container">')
    body = seg[k + len('<div class="zpsnippet-container">'):]
    body = re.sub(r'\s*<style>.*?</style>', '', body, count=1, flags=re.S)
    return body[:body.rfind('</section>') + len('</section>')]

def head_meta(raw):
    head = raw[:raw.find('</head>')]
    def g(pat):
        m = re.search(pat, head, re.S)
        return html.unescape(m.group(1)).strip() if m else ""
    return dict(title=g(r'<title>(.*?)</title>'),
                desc=g(r'<meta name="description" content="(.*?)"'),
                canonical=g(r'<link rel="canonical" href="(.*?)"'))

def json_ld(raw, typ):
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S):
        try: d = json.loads(m.group(1).strip())
        except Exception: continue
        if d.get("@type") == typ: return d
    return {}

def tidy(frag):
    frag = re.sub(r'\n{3,}', '\n\n', frag.strip())
    return re.sub(r'[ \t]+\n', '\n', frag) + "\n"

def sections(body):
    """[(id, inner_html)] for every <section class="cwg__section">."""
    out = []
    for m in re.finditer(r'<section class="cwg__section"([^>]*)>(.*?)</section>', body, re.S):
        sid = re.search(r'id="([^"]+)"', m.group(1))
        out.append((sid.group(1) if sid else "", m.group(2)))
    return out

def qa_pairs(frag):
    """FAQ <h3>/<p> pairs, in order."""
    return [(html.unescape(q.strip()), a.strip()) for q, a in
            re.findall(r'<h3>(.*?)</h3>\s*<p>(.*?)</p>', frag, re.S)]

def table_rows(frag):
    """[(header-cell, value-cell)] from a two-column tbody."""
    tb = re.search(r'<tbody>(.*?)</tbody>', frag, re.S)
    if not tb: return []
    return [(re.sub(r'\s+', ' ', a).strip(), re.sub(r'\s+', ' ', b).strip())
            for a, b in re.findall(r'<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>',
                                   tb.group(1), re.S)]

def hero(body):
    h = re.search(r'<header class="cwg__hero">(.*?)</header>', body, re.S).group(1)
    def g(pat, s=h):
        m = re.search(pat, s, re.S)
        return re.sub(r'\s+', ' ', m.group(1)).strip() if m else ""
    return dict(kicker=g(r'<p class="cwg__kicker">(.*?)</p>'),
                h1=g(r'<h1>(.*?)</h1>'),
                lede=g(r'<p class="cwg__lede">(.*?)</p>'),
                badge=g(r'<p class="cw__fbadge"[^>]*>(.*?)</p>'))

def tldr(body):
    m = re.search(r'<div class="cwg__tldr">(.*?)</div>', body, re.S)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else ""

def related(raw):
    m = re.search(r'<section class="cw-rel"[^>]*>.*?<p class="cw-rel__label">(.*?)</p>'
                  r'\s*<ul class="cw-rel__links">(.*?)</ul>', raw, re.S)
    if not m: return {}
    links = re.findall(r'<li><a href="([^"]+)">(.*?)</a></li>', m.group(2))
    return {"label": m.group(1).strip(),
            "links": [[h_, html.unescape(t)] for h_, t in links]}

def run(livedir, outdir):
    data = {"hub": {}, "countries": []}

    raw = open(os.path.join(livedir, "export.html"), encoding="utf-8").read()
    body = main_body(raw)
    secs = sections(body)
    prose = "\n\n".join(tidy(s) for sid, s in secs if sid != "faq")
    open(os.path.join(outdir, "hub.body.html"), "w", encoding="utf-8").write(tidy(prose))
    cta = re.search(r'<section class="cwg__cta">\s*<h2>(.*?)</h2>\s*<p>(.*?)</p>', body, re.S)
    data["hub"] = dict(head_meta(raw), hero=hero(body), tldr=tldr(body),
                       faq=qa_pairs(dict(secs).get("faq", "")),
                       cta_h2=cta.group(1).strip(), cta_p=cta.group(2).strip(),
                       related=related(raw),
                       schema_name=json_ld(raw, "WebPage").get("name", ""),
                       schema_desc=json_ld(raw, "WebPage").get("description", ""),
                       date_modified=json_ld(raw, "WebPage").get("dateModified", ""))

    for slug in SLUGS:
        raw = open(os.path.join(livedir, "export", slug + ".html"), encoding="utf-8").read()
        body = main_body(raw)
        secs = sections(body)
        d = dict(head_meta(raw), slug=slug, hero=hero(body), tldr=tldr(body))
        imp = dict(secs).get("import", "")
        own = [(sid, s) for sid, s in secs if sid not in ("import", "faq")]
        open(os.path.join(outdir, slug + ".body.html"), "w", encoding="utf-8").write(
            tidy("\n\n".join(tidy(s) for _, s in own)))
        if imp:
            lead = re.search(r'<p>(.*?)</p>', imp, re.S)
            d["import_essentials"] = {
                "h2": re.search(r'<h2>(.*?)</h2>', imp, re.S).group(1).strip(),
                "lead": re.sub(r'\s+', ' ', lead.group(1)).strip(),
                "rows": [list(r) for r in table_rows(imp)]}
        d["faq"] = qa_pairs(dict(secs).get("faq", ""))
        cta = re.search(r'<section class="cwg__cta">\s*<h2>(.*?)</h2>\s*<p>(.*?)</p>', body, re.S)
        d["cta_h2"], d["cta_p"] = cta.group(1).strip(), cta.group(2).strip()
        d["related"] = related(raw)
        wp = json_ld(raw, "WebPage")
        d["schema_name"] = wp.get("name", "")
        d["schema_desc"] = wp.get("description", "")
        d["date_modified"] = wp.get("dateModified", "")
        bc = json_ld(raw, "BreadcrumbList").get("itemListElement", [])
        d["crumb_leaf"] = bc[-1]["name"] if bc else ""
        data["countries"].append(d)

    with open(os.path.join(outdir, "export.raw.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    print("wrote", outdir)

if __name__ == "__main__":
    live = sys.argv[1]
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "content", "export")
    os.makedirs(out, exist_ok=True)
    run(live, out)
