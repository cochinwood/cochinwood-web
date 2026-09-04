#!/usr/bin/env python3
"""The /export section: one hub and twenty-eight country lanes, data + a template.

The pages are the commercial core of the site and every one of their URLs is
indexed, so the URLs are fixed. The first eight, which live in export.json:

    /export            /export/uae         /export/saudi-arabia   /export/qatar
    /export/oman       /export/kuwait      /export/bahrain
    /export/sri-lanka  /export/israel

and twenty more added later, one JSON file each under content/export/countries/,
listed in content/export-markets.json alongside them.

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

Adding the twenty-ninth country is two edits and no copy-paste:

  1. one content/export/countries/<slug>.json — slug, the two forms of the name,
     title/desc/schema_name/crumb_leaf, kicker/h1/lede/tldr, the lane's own FAQ,
     cta_h2/cta_p, ports_ship, and (only if that market gets one) the `import`
     block: vat, vat_faq, conformity, ports_clear, landed_cost_note;
  2. one content/export/<slug>.body.html holding its prose.

AND THE MARKET MUST BE IN content/export-markets.json, which is where the lane
list, the country count and the continent count all come from. There is no order
list to append to here any more: _lane_groups() reads that file, so a market
named there with a body file to match is linked from the hub and from every other
lane automatically, and one that is missing from it is reported by name at build
time. It used to be a hand-kept `shared.related.order` of eight, which is exactly
how twenty lanes shipped linked from nothing but the sitemap.

The templated FAQs, the import table, the hero, the schema, the sitemap entry and
the back-links from every other lane all follow. No existing page is touched.

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
    """Every other lane, grouped by continent, then the two standing links.

    THIS BLOCK USED TO BE A FLAT LIST OF EIGHT, AND THAT IS EXACTLY HOW TWENTY OF
    THE TWENTY-EIGHT LANES ENDED UP REACHABLE FROM NOTHING BUT THE SITEMAP. The
    eight were the original Gulf-plus lanes named in export.json; the twenty that
    landed later, one JSON file each, were never added to the order list, so this
    block -- the only cross-lane navigation the section has -- linked none of them,
    and neither did the hub. `git grep href=\"/export/australia\"` over the served
    tree returned nothing but australia.html's own canonical.

    The grouping is derived from content/export-markets.json, the file that already
    rules the country list, the country count and the continent count, so a market
    added there with a body file to match appears on the other twenty-seven without
    anyone touching this function. Deriving it is the point: that JSON's own
    _history records two market lists drifting apart, and a hand-kept order list
    here would have been the third copy.
    """
    if "related" in d:                       # the hub keeps its own list
        label = d["related"]["label"]
        body = "".join(f'<a href="{href}">{text}</a>'
                       for href, text in d["related"]["links"])
    else:
        label = shared["related"]["label"]
        parts = []
        for continent, entries in shared["related"]["groups"]:
            pills = "".join(f'<a href="/export/{s}">Plywood export to {n}</a>'
                            for s, n, _list_name in entries if s != d["slug"])
            if pills:                        # the lane's own continent, alone, would be empty
                parts.append(f"<h3>{continent}</h3>{pills}")
        parts.append("".join(f'<a href="{href}">{text}</a>'
                             for href, text in shared["related"]["tail"]))
        body = "".join(parts)
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
    html_ = B.base(d["title"], d["desc"], path, B.rewrite_links(body),
                   body_class="cw-encbody", extra_head=webpage_ld(shared, d, path) + faq_ld,
                   crumbs=crumbs, show_crumbs=False)
    B.write(path.lstrip("/") + "/index.html", html_, src=src)


HUB_MARKETS_TOKEN = "{{CWI_EXPORT_LANE_GROUPS}}"


def _lane_groups(data):
    """[[continent, [[slug, pill_name, list_name], ...]], ...] -- every lane, canonical order.

    The continents and their order come from content/export-markets.json. TWO NAMES
    PER LANE, ON PURPOSE: the pill reads "Plywood export to <pill_name>" and wants
    the lane's own name_plain, which carries the article the sentence needs ("the
    Maldives", "the United States"); the hub's list wants the canonical bare name
    from export-markets.json, because "Singapore, the Maldives" in a comma list is
    the article leaking out of a sentence it is no longer in. A market's slug is its
    name lowercased with spaces hyphenated, exact for all twenty-eight today,
    checked both ways below.

    Both mismatches are reported rather than swallowed, and they are different
    failures: a market with no lane page is a gap in the section, while a lane page
    the canonical list does not name is a page for a market we do not claim to
    serve. The stray lane is still grouped and linked -- this function exists
    because unlinked lanes are the bug, so it must not create one while reporting.
    """
    names = {c["slug"]: c["name_plain"] for c in data["countries"]}
    groups, placed = [], set()
    for g in getattr(B, "EXPORT_GROUPS", []):
        entries = []
        for c in g["countries"]:
            slug = c["name"].lower().replace(" ", "-")
            if slug in names:
                entries.append([slug, names[slug], c["name"]])
                placed.add(slug)
            else:
                B.warn("export: content/export-markets.json names %s, but there is no "
                       "lane at content/export/%s.body.html -- nothing links to that "
                       "market" % (c["name"], slug))
        if entries:
            groups.append([g["continent"], entries])
    stray = sorted(s for s in names if s not in placed)
    if stray:
        B.warn("export: %d lane page(s) are not in content/export-markets.json (%s) -- "
               "the canonical market list and the lanes disagree; they are linked under "
               "'Other markets' so they stay reachable, but one of the two is wrong"
               % (len(stray), ", ".join(stray)))
        groups.append(["Other markets", [[s, names[s], names[s]] for s in stray]])
    return groups


def _hub_market_table(groups):
    """The hub's own market list: every lane, linked, grouped by continent.

    Replaces a hand-written eight-row table that had drifted twenty markets behind
    the section it introduces. Uses cwg__table, already styled, so this adds no CSS
    -- which matters more than it looks: assets are content-hashed, and changing one
    renames it, at which point the hash the live tree still carries is a URL this
    build no longer serves and cutover_preflight's coverage check fails.
    """
    rows = "".join(
        "<tr><td>%s</td><td>%s</td></tr>"
        % (continent, ", ".join('<a href="/export/%s">%s</a>' % (s, list_name)
                                for s, _pill, list_name in entries))
        for continent, entries in groups)
    return ('<table class="cwg__table"><thead><tr><th>Region</th><th>Markets</th>'
            '</tr></thead><tbody>%s</tbody></table>' % rows)


def build():
    """Render /export and its twenty-eight lanes. Returns the page count.

    Called by build.py's build_export(), which runs it with the other section
    builders -- before assets_and_meta(), so any /files/ photo a lane grows
    later is copied, and before build_sitemap() and build_redirects(), so the
    URLs reach sitemap.xml and the five cf-live rules that point into
    /export stop being dropped as "target is not a page this build emits".
    """
    data = _load()
    shared = data["shared"]
    # the related block, grouped by continent -- see related() for why it is derived
    shared["related"]["groups"] = _lane_groups(data)

    hub = data["hub"]
    hub_body = _prose("hub.body.html")
    if HUB_MARKETS_TOKEN not in hub_body:
        raise SystemExit("export: hub.body.html no longer carries %s, so the hub would "
                         "ship without its market list" % HUB_MARKETS_TOKEN)
    hub_body = hub_body.replace(HUB_MARKETS_TOKEN,
                                _hub_market_table(shared["related"]["groups"]))
    page(shared, hub, "/export", hub_body,
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
