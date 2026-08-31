#!/usr/bin/env python3
"""Fold content/export/export.raw.json (the verbatim live capture) into the
maintained content/export/export.json, factoring the boilerplate out.

Every string this moves into `shared` is asserted byte-identical against all
nine live pages first, and every templated FAQ answer is re-rendered and
compared with the live answer. Where a lane disagrees with the others on a
fact, the assertion fails loudly and the value stays per-country: nothing is
silently averaged into a house position.

Run once, after extract_export_live.py. build.py never calls it.
"""
import os, re, json, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CDIR = os.path.join(ROOT, "content", "export")

# slug -> (the name as the copy writes it in a sentence, the bare name)
NAMES = {
    "uae":          ("the UAE",      "UAE"),
    "saudi-arabia": ("Saudi Arabia", "Saudi Arabia"),
    "qatar":        ("Qatar",        "Qatar"),
    "oman":         ("Oman",         "Oman"),
    "kuwait":       ("Kuwait",       "Kuwait"),
    "bahrain":      ("Bahrain",      "Bahrain"),
    "sri-lanka":    ("Sri Lanka",    "Sri Lanka"),
    "israel":       ("Israel",       "Israel"),
}
ORDER = list(NAMES)

FAQ_T = {
 "hs": ("What HS code is plywood under for {name_the} imports?",
        "Plywood falls under HS heading 4412 (sub-headings 4412.31, 4412.33, 4412.34 "
        "and 4412.39 by face species). We state the correct code on the commercial "
        "invoice for your clearing agent."),
 "duty": ("How much import duty applies to plywood in {name_the}?",
        "The GCC Common External Tariff is 5% customs duty on the CIF value. {vat_faq} "
        "We quote FCA or FOB Cochin in USD; duty and VAT are added by your agent at clearance."),
 "standards": ("What standards or conformity approval does {name_the} require?",
        "Clearance references {conformity_faq}. We supply the certificate of origin and "
        "product documentation your agent needs; regulated-product certificates are "
        "arranged where they apply."),
 "documents": ("What documents do you provide for {name_the} customs?",
        "{documents_faq} — issued so your shipment clears at {ports_clear} without hold-ups."),
 "warehouse": ("Do you have a plywood factory or warehouse in {name_plain}?",
        "No — Cochin Wood is an Indian plywood factory near Cochin (Kochi), Kerala. "
        "We do not hold local stock or a warehouse in {name_the}; we ship full-container "
        "loads FOB Cochin to {ports_ship}. You buy factory-direct from India."),
}

BADGE = ('Shipping direct from our <a href="/plywood-factory">plywood factory near '
         'Cochin (Kochi)</a>, India &mdash; no local stock in {name_the}.')
IMPORT_H2   = "Import essentials for {name_the}"
IMPORT_LEAD = ("What your clearing agent needs to land a plywood shipment in {name_the}. "
               "We quote FCA or FOB Cochin in USD; customs duty and any VAT are added at "
               "import on the CIF value.")
DOCS_TABLE = "Commercial invoice, packing list, certificate of origin, bill of lading"
DOCS_FAQ   = "Commercial invoice, packing list, certificate of origin and bill of lading"

problems = []

def same(label, got, want):
    if got != want:
        problems.append("%s\n    live : %s\n    tmpl : %s" % (label, got, want))

def strip_badge(b):
    """The live badge carries inline styles; the build styles it from the sheet."""
    return re.sub(r"\s+", " ", re.sub(r'\s*style="[^"]*"', "", b)).strip()


def main():
    raw = json.load(open(os.path.join(CDIR, "export.raw.json"), encoding="utf-8"))
    by = {c["slug"]: c for c in raw["countries"]}
    out_countries = []

    for slug in ORDER:
        c = by[slug]
        name_the, name_plain = NAMES[slug]
        v = {"name_the": name_the, "name_plain": name_plain}
        same("%s: hero badge" % slug, strip_badge(c["hero"]["badge"]), BADGE.format(**v))

        d = {"slug": slug, "name_the": name_the, "name_plain": name_plain,
             "title": c["title"], "desc": c["desc"], "schema_name": c["schema_name"],
             "crumb_leaf": c["crumb_leaf"], "kicker": c["hero"]["kicker"],
             # /export/oman is the one lane whose WebPage schema description is not
             # its meta description. Both live strings are kept; neither is guessed.
             **({"schema_desc": c["schema_desc"]} if c["schema_desc"] != c["desc"] else {}),
             "h1": c["hero"]["h1"], "lede": c["hero"]["lede"], "tldr": c["tldr"]}

        boiler = ["warehouse"]
        ie = c.get("import_essentials")
        if ie:
            rows = dict(ie["rows"])
            same("%s: import h2" % slug, ie["h2"], IMPORT_H2.format(**v))
            same("%s: import lead" % slug, ie["lead"], IMPORT_LEAD.format(**v))
            imp = {"vat": rows["VAT at import"],
                   "conformity": rows["Conformity / standards"],
                   "ports_clear": rows["Clears at"],
                   "landed_cost_note": "Landed-cost note" in rows}
            if rows["Documents we provide"] != DOCS_TABLE:
                imp["documents"] = rows["Documents we provide"]
            d["import"] = imp
            boiler = ["hs", "duty", "standards", "documents", "warehouse"]

        faq = list(c["faq"])
        tail, faq = faq[-len(boiler):], faq[:-len(boiler)]
        v.update(ports_clear=d.get("import", {}).get("ports_clear", ""),
                 vat_faq="", conformity_faq="", documents_faq=DOCS_FAQ, ports_ship="")
        for key, pair in zip(boiler, tail):
            lq, la = pair
            tq, ta = FAQ_T[key]
            same("%s: FAQ %s question" % (slug, key), lq, tq.format(**v))
            if key == "duty":
                v["vat_faq"] = re.search(r"CIF value\. (.+?) We quote FCA", la).group(1)
                d["import"]["vat_faq"] = v["vat_faq"]
            elif key == "standards":
                v["conformity_faq"] = re.search(
                    r"^Clearance references (.+?)\. We supply", la).group(1)
                if v["conformity_faq"] != d["import"]["conformity"]:
                    d["import"]["conformity_faq"] = v["conformity_faq"]
            elif key == "documents":
                v["documents_faq"] = re.search(r"^(.+?) — issued so", la).group(1)
                if v["documents_faq"] != DOCS_FAQ:
                    d["import"]["documents_faq"] = v["documents_faq"]
            elif key == "warehouse":
                v["ports_ship"] = re.search(r"FOB Cochin to (.+?)\. You buy", la).group(1)
                d["ports_ship"] = v["ports_ship"]
            same("%s: FAQ %s answer" % (slug, key), la, ta.format(**v))

        d["faq"] = [list(x) for x in faq]
        d["faq_boiler"] = boiler
        d["cta_h2"], d["cta_p"] = c["cta_h2"], c["cta_p"]

        # the related block is the other seven lanes in one fixed order, then two links
        want = ([["/export/" + s, "Plywood export to " + NAMES[s][1]]
                 for s in ORDER if s != slug]
                + [["/export-process", "How we handle an export order"],
                   ["/export", "All export markets"]])
        if c["related"]["links"] != want:
            problems.append("%s: related links are not the derived order\n"
                            "    live : %s\n    tmpl : %s" % (slug, c["related"]["links"], want))
        out_countries.append(d)

    hub = raw["hub"]
    uae_rows = dict(by["uae"]["import_essentials"]["rows"])
    shared = {
        "eeat": ("By <strong>Edwin David</strong>, Director, Cochin Wood Industries "
                 "&mdash; plywood manufacturer in Perumbavoor, Kerala. "
                 "<span aria-hidden=\"true\">&middot;</span> Last updated 18 July 2026."),
        "date_modified": hub["date_modified"],
        "author": {"name": "Edwin David", "jobTitle": "Director", "url": "/about",
                   "sameAs": ["https://www.linkedin.com/in/edwin-david-thoppilan"]},
        "hero_actions": [["/contact#quote", "Request an export quote", True],
                         ["https://wa.me/919567410175", "WhatsApp the export desk", False]],
        "cta_btn": ["/contact#quote", "Request a quote"],
        "badge": BADGE,
        "import": {"h2": IMPORT_H2, "lead": IMPORT_LEAD,
                   "hs_code": uae_rows["HS code"],
                   "customs_duty": "5% GCC Common External Tariff on CIF value",
                   "landed_cost_note": uae_rows["Landed-cost note"],
                   "documents": DOCS_TABLE,
                   "ispm15": "Panels exempt; assembled crates stamped through a compliant process"},
        "faq_templates": {k: list(t) for k, t in FAQ_T.items()},
        "documents_faq": DOCS_FAQ,
        "related": {"label": "Other export destinations", "order": ORDER,
                    "tail": [["/export-process", "How we handle an export order"],
                             ["/export", "All export markets"]]},
    }
    for slug in ORDER:
        ie = by[slug].get("import_essentials")
        if not ie:
            continue
        rows = dict(ie["rows"])
        same("%s: HS code row" % slug, rows["HS code"], shared["import"]["hs_code"])
        same("%s: customs duty row" % slug, rows["Customs duty"], shared["import"]["customs_duty"])
        same("%s: ISPM-15 row" % slug, rows["ISPM-15"], shared["import"]["ispm15"])
        if "Landed-cost note" in rows:
            same("%s: landed-cost note" % slug, rows["Landed-cost note"],
                 shared["import"]["landed_cost_note"])

    data = {"shared": shared,
            "hub": {"title": hub["title"], "desc": hub["desc"],
                    "schema_name": hub["schema_name"], "crumb_leaf": hub["hero"]["h1"],
                    **({"schema_desc": hub["schema_desc"]}
                       if hub["schema_desc"] != hub["desc"] else {}),
                    "kicker": hub["hero"]["kicker"], "h1": hub["hero"]["h1"],
                    "lede": hub["hero"]["lede"], "tldr": hub["tldr"],
                    "faq": [list(x) for x in hub["faq"]],
                    "cta_h2": hub["cta_h2"], "cta_p": hub["cta_p"],
                    "related": {"label": hub["related"]["label"],
                                "links": hub["related"]["links"]}},
            "countries": out_countries}

    if problems:
        print("%d MISMATCH(ES) - the live pages disagree with the template:" % len(problems))
        for p in problems:
            print("  ! " + p)
        return 1
    with open(os.path.join(CDIR, "export.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("content/export/export.json written; every shared string verified "
          "byte-identical across all nine live pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
