#!/usr/bin/env python3
"""The /export section: one hub and eight country lanes, from data + a template.

The nine pages are the commercial core of the site and every one of their URLs
is indexed, so the URLs are fixed:

    /export            /export/uae         /export/saudi-arabia   /export/qatar
    /export/oman       /export/kuwait      /export/bahrain
    /export/sri-lanka  /export/israel

On the live site these are nine near-identical Zoho exports. Roughly half of
each page is boilerplate repeated nine times: the hero scaffolding, the byline,
the "no local stock" factory badge, the import-essentials table skeleton, the
four templated import FAQs, the warehouse FAQ, the "other export destinations"
block, breadcrumbs and the FAQPage schema. That half lives here, once. What is
genuinely per-lane lives in content/export/:

    export.json        every per-lane fact (ports, VAT, conformity, metadata)
    <slug>.body.html   that lane's own prose, exactly as it shipped
    hub.body.html      the hub's own prose
    export.raw.json    the verbatim live capture the other two were cut from

Adding a tenth country is two edits and no copy-paste:

  1. one object appended to `countries` in export.json — slug, the two forms of
     the name, title/desc/schema_name/crumb_leaf, kicker/h1/lede/tldr, the lane's
     own FAQ, cta_h2/cta_p, ports_ship, and (only if that market gets one) the
     `import` block: vat, vat_faq, conformity, ports_clear, landed_cost_note;
  2. one content/export/<slug>.body.html holding its prose.

Then add the slug to shared.related.order. The templated FAQs, the import table,
the hero, the schema, the sitemap entry and the back-links from the other nine
pages all follow from that. No existing page is touched.

The copy is unchanged: tools/compose_export_json.py asserted every shared string
byte-identical across all nine live pages before it was allowed into `shared`,
and refuses to fold a value that one lane states differently. Presentation moved
onto the build's own design system (.cwg__* / .cwp__*, both already in the CSS
bundle) because the live class names came from the Zoho theme and do not exist
here.

    python build.py              full site build, this section included

build.py calls build() below, from build_export() in its main(). Running this
file directly still works and is equivalent -- it just calls build.py's main().
"""
import os, re, json, html

import build as B

ROOT = os.path.dirname(os.path.abspath(__file__))
CDIR = os.path.join(ROOT, "content", "export")
SRC_JSON = os.path.join("content", "export", "export.json")


def _load():
    with open(os.path.join(CDIR, "export.json"), encoding="utf-8") as f:
        data = json.load(f)

    # Lanes added after the first eight live one-per-file under content/export/countries/, and
    # are merged here. The split is not decoration: four agents wrote twenty of these at once,
    # and a shared array in one file is a merge conflict per country. It also means adding the
    # twenty-ninth lane is dropping in a file, which is the whole point of a data-driven section.
    #
    # A per-file lane may omit "import": shared["import"] hard-codes the 5% GCC Common External
    # Tariff, which is true for the Gulf lanes and false everywhere else, so the non-GCC lanes
    # carry their own import table in their body instead. page() already treats it as optional.
    cdir = os.path.join(CDIR, "countries")
    if os.path.isdir(cdir):
        have = {c["slug"] for c in data["countries"]}
        for fn in sorted(os.listdir(cdir)):
            if not fn.endswith(".json"):
                continue
            with open(os.path.join(cdir, fn), encoding="utf-8") as f:
                c = json.load(f)
            c.setdefault("slug", fn[:-5])
            if c["slug"] in have:
                raise SystemExit(
                    f"export: {fn} duplicates the slug {c['slug']!r} already in export.json. "
                    "Two sources for one lane is how they drift apart -- delete one.")
            # keys beginning _ are notes to the next reader, not page data
            data["countries"].append({k: v for k, v in c.items() if not k.startswith("_")})
            have.add(c["slug"])
    return data


def _prose(name):
    with open(os.path.join(CDIR, name), encoding="utf-8") as f:
        return f.read().strip()


def _text(frag):
    """Visible text of an HTML fragment, for JSON-LD."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", frag))).strip()


# ---------------- shared blocks ----------------

def hero(shared, d):
    """Kicker, H1, lede, factory badge, the two hero buttons, the byline.

    Identical on all nine pages except for the four strings it interpolates.
    """
    acts = "".join(
        f'<a class="cwp__btn{"" if primary else " cwp__btn--secondary"}" href="{href}">{label}</a>'
        for href, label, primary in shared["hero_actions"])
    badge = (f'<p class="cwg__note">{shared["badge"].format(**d)}</p>'
             if d.get("name_the") else "")
    return f'''<header class="cwg__hero"><div class="cwg__container">
  <p class="cwp__eyebrow">{d["kicker"]}</p>
  <h1 class="cwg__h1">{d["h1"]}</h1>
  <p class="cwp__lede">{d["lede"]}</p>
  {badge}
  <div class="cwp__hero-actions">{acts}</div>
  <p class="cwg__meta">{shared["eeat"]}</p>
</div></header>'''


def tldr(d):
    return (f'<div class="cwg__container"><div class="cwg__tldr">'
            f'<p>{d["tldr"]}</p></div></div>')


def import_essentials(shared, d):
    """The "Import essentials" table. Six GCC lanes carry it; Sri Lanka and
    Israel never had one, so they do not get one invented for them."""
    imp = d.get("import")
    if not imp:
        return ""
    s = shared["import"]
    rows = [("HS code", s["hs_code"]),
            ("Customs duty", s["customs_duty"]),
            ("VAT at import", imp["vat"])]
    if imp.get("landed_cost_note"):
        rows.append(("Landed-cost note", s["landed_cost_note"]))
    rows += [("Conformity / standards", imp["conformity"]),
             ("Clears at", imp["ports_clear"]),
             ("Documents we provide", imp.get("documents", s["documents"])),
             ("ISPM-15", s["ispm15"])]
    body = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows)
    return (f'<section id="import"><h2>{s["h2"].format(**d)}</h2>'
            f'<p>{s["lead"].format(**d)}</p>'
            f'<table class="cwg__table"><thead><tr><th>Item</th><th>Detail</th></tr>'
            f'</thead><tbody>{body}</tbody></table></section>')


def faq_items(shared, d):
    """The lane's own questions, then the templated import ones in live order."""
    items = [tuple(qa) for qa in d["faq"]]
    imp = d.get("import") or {}
    v = dict(d,
             vat_faq=imp.get("vat_faq", ""),
             conformity_faq=imp.get("conformity_faq", imp.get("conformity", "")),
             documents_faq=imp.get("documents_faq", shared["documents_faq"]),
             ports_clear=imp.get("ports_clear", ""),
             ports_ship=d.get("ports_ship", ""))
    for key in d.get("faq_boiler", []):
        q, a = shared["faq_templates"][key]
        items.append((q.format(**v), a.format(**v)))
    return items


def faq_block(items):
    if not items:
        return "", ""
    inner = "".join(f'<div class="cwg__faq-item"><h3>{q}</h3><p>{a}</p></div>'
                    for q, a in items)
    ld = ('<script type="application/ld+json">' + json.dumps(
        {"@context": "https://schema.org", "@type": "FAQPage",
         "mainEntity": [{"@type": "Question", "name": _text(q),
                         "acceptedAnswer": {"@type": "Answer", "text": _text(a)}}
                        for q, a in items]},
        separators=(",", ":"), ensure_ascii=False) + "</script>")
    return (f'<section class="cwg__faq"><div class="cwg__container">'
            f'<h2>FAQ</h2>{inner}</div></section>'), ld


def related(shared, d):
    """Every other lane, in one fixed order, then the two standing links.

    On live this list is written out by hand on each page; here it is derived,
    so a tenth country appears on the other nine without touching them."""
    if "related" in d:                       # the hub keeps its own list
        label, links = d["related"]["label"], d["related"]["links"]
    else:
        label = shared["related"]["label"]
        links = ([["/export/" + s, "Plywood export to " + n]
                  for s, n in shared["related"]["names"] if s != d["slug"]]
                 + shared["related"]["tail"])
    body = "".join(f'<a href="{href}">{text}</a>' for href, text in links)
    return (f'<section class="cwg__related"><div class="cwg__wide">'
            f'<h2>{label}</h2>{body}</div></section>')


def cta(shared, d):
    href, label = shared["cta_btn"]
    return (f'<section class="cwg__cta"><div class="cwg__wide cwg__cta-inner">'
            f'<div><h2>{d["cta_h2"]}</h2><p>{d["cta_p"]}</p></div>'
            f'<a class="cwg__btn" href="{href}">{label}</a></div></section>')


def webpage_ld(shared, d, path):
    a = shared["author"]
    return ('<script type="application/ld+json">' + json.dumps(
        {"@context": "https://schema.org", "@type": "WebPage",
         "name": d["schema_name"],
         # /export/oman's live WebPage description is not its meta description;
         # both live strings are shipped as they are rather than reconciled.
         "description": d.get("schema_desc", d["desc"]), "url": B.LIVE + path,
         "isPartOf": {"@type": "WebSite", "name": "Cochin Wood Industries",
                      "url": B.LIVE + "/"},
         "about": {"@id": B.LIVE + "/#organization"},
         "dateModified": shared["date_modified"],
         "author": {"@type": "Person", "name": a["name"], "jobTitle": a["jobTitle"],
                    "worksFor": {"@id": B.LIVE + "/#organization"},
                    "url": B.LIVE + a["url"], "sameAs": a["sameAs"]},
         "publisher": {"@id": B.LIVE + "/#organization"}},
        separators=(",", ":"), ensure_ascii=False) + "</script>")


# ---------------- pages ----------------

def page(shared, d, path, prose, crumbs, src):
    faq, faq_ld = faq_block(faq_items(shared, d))
    body = (hero(shared, d) + "\n" + tldr(d) + "\n"
            + '<article class="cwg__body"><div class="cwg__container">'
            + prose + import_essentials(shared, d)
            + "</div></article>\n" + faq + "\n"
            # live puts the CTA before the lane-links strip; keep that order
            + cta(shared, d) + "\n" + related(shared, d))
    # Preserve published export research that landed directly on cf-live after
    # this source lineage's cutover. Exact matching makes stale patches fail loudly.
    with open(os.path.join(CDIR, 'published-patches.json'), encoding='utf8') as f:
        patches = json.load(f)['patches'].get(path.lstrip('/'), [])
    for patch in patches:
        if patch['after'] in body:
            continue  # already migrated into the underlying source
        if body.count(patch['before']) != 1:
            raise ValueError('Published export preservation patch drift: ' + path)
        body = body.replace(patch['before'], patch['after'], 1)
    html_ = B.base(d["title"], d["desc"], path, B.rewrite_links(body),
                   body_class="cw-encbody", extra_head=webpage_ld(shared, d, path) + faq_ld,
                   crumbs=crumbs, show_crumbs=False)
    B.write(path.lstrip("/") + "/index.html", html_, src=src)


def build():
    """Render /export and the eight lanes. Returns the page count.

    Called by build.py's build_export(), which runs it with the other section
    builders -- before assets_and_meta(), so any /files/ photo a lane grows
    later is copied, and before build_sitemap() and build_redirects(), so the
    nine URLs reach sitemap.xml and the five cf-live rules that point into
    /export stop being dropped as "target is not a page this build emits".
    """
    data = _load()
    shared = data["shared"]
    # the related-block order, as slug + the name the link text uses
    names = {c["slug"]: c["name_plain"] for c in data["countries"]}
    shared["related"]["names"] = [[s, names[s]] for s in shared["related"]["order"]]

    hub = data["hub"]
    page(shared, hub, "/export", _prose("hub.body.html"),
         [("Home", "/"), (hub["crumb_leaf"], "/export")],
         os.path.join("content", "export", "hub.body.html"))
    n = 1
    for c in data["countries"]:
        page(shared, c, "/export/" + c["slug"], _prose(c["slug"] + ".body.html"),
             [("Home", "/"), ("Export", "/export"), (c["crumb_leaf"], "/export/" + c["slug"])],
             os.path.join("content", "export", c["slug"] + ".body.html"))
        n += 1
    return n


def main():
    # build.py builds this section itself now, in the right order, so there is
    # nothing left to do here but hand over. Kept so the documented command in
    # tools/verify_export_vs_live.py keeps working.
    B.main()


if __name__ == "__main__":
    main()
