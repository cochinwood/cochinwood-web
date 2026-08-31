#!/usr/bin/env python3
"""Prove the generated /export section still says what the live pages say.

    python export_section.py                       # build dist/
    python tools/verify_export_vs_live.py <cf-live-checkout>

For each of the nine URLs it compares dist/<path>/index.html against the live
page on three axes:

  * every visible line of copy inside <main>, whitespace- and entity-normalised
  * <title>, meta description, canonical
  * the WebPage, BreadcrumbList and FAQPage JSON-LD, key by key

It exits non-zero on any difference, so it can gate a change to export.json or
to a lane's prose. One difference is expected and is listed at the bottom of
this file; anything else means the port drifted.

KNOWN AND ACCEPTED
  /export/bahrain <title>: live ships "Indian Plywood Exporter to Bahrain —
  FOB Cochin" (47 chars) with no brand suffix. build.py's seo_title() appends
  " | Cochin Wood" to any title that still fits inside TITLE_MAX, which is the
  rule every other page on this site obeys, including Bahrain's seven sibling
  lanes. Sri Lanka's title escapes it only because it is two characters too
  long. Left as the shell decides; og:title and twitter:title keep the live
  string verbatim. To pin the live title instead, add it to TITLE_OVERRIDES in
  build.py — which is Edwin's call, not this script's.
"""
import re, os, sys, json, html, difflib

PAGES = [("export.html", "export")] + [
    ("export/%s.html" % s, "export/" + s) for s in
    ["uae", "saudi-arabia", "qatar", "oman", "kuwait", "bahrain", "sri-lanka", "israel"]]


def text(frag):
    frag = re.sub(r"<(script|style|svg)\b.*?</\1>", "", frag, flags=re.S)
    frag = re.sub(r"<[^>]+>", "\n", frag)
    return [l for l in (re.sub(r"\s+", " ", x).strip()
                        for x in html.unescape(frag).split("\n")) if l]


def live_text(live, name):
    """The Zoho page's own words: the code-snippet payload plus the lane-links
    strip, which the theme renders after it."""
    t = open(os.path.join(live, name), encoding="utf-8").read()
    seg = t[t.find('id="thememaincontent"'):t.find("<!-- CWI static footer")]
    k = seg.find('<div class="zpsnippet-container">') + len('<div class="zpsnippet-container">')
    body = seg[k:]
    body = body[:body.rfind("</section>") + len("</section>")]
    rel = re.search(r'<section class="cw-rel".*?</section>', t, re.S)
    return text(body) + text(rel.group(0) if rel else "")


def meta(t):
    h = t[:t.find("</head>")]
    def g(pat):
        m = re.search(pat, h, re.S)
        return html.unescape(m.group(1)).strip() if m else None
    return {"title": g(r"<title>(.*?)</title>"),
            "description": g(r'<meta name="description" content="(.*?)"'),
            "canonical": g(r'<link rel="canonical" href="(.*?)"')}


def schemas(t):
    out = {}
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
        try:
            d = json.loads(m.group(1).strip())
        except Exception:
            continue
        ty = d.get("@type")
        out[",".join(ty) if isinstance(ty, list) else ty] = d
    return out


def main(live, dist):
    fails = 0
    for lf, path in PAGES:
        built_path = os.path.join(dist, path, "index.html")
        if not os.path.exists(built_path):
            print("%-22s MISSING from dist/ - run export_section.py first" % path)
            fails += 1
            continue
        L = open(os.path.join(live, lf), encoding="utf-8").read()
        B = open(built_path, encoding="utf-8").read()
        issues = []

        a = live_text(live, lf)
        b = text(re.search(r'<main id="main">(.*?)</main>', B, re.S).group(1))
        issues += ["copy: " + l for l in difflib.unified_diff(a, b, lineterm="", n=0)
                   if l[:1] in "+-" and l[:3] not in ("+++", "---")]

        ml, mb = meta(L), meta(B)
        for k in ml:
            if ml[k] != mb[k]:
                issues.append("%s\n        live : %s\n        built: %s" % (k, ml[k], mb[k]))

        sl, sb = schemas(L), schemas(B)
        for ty in ("WebPage", "BreadcrumbList", "FAQPage"):
            x, y = sl.get(ty), sb.get(ty)
            if x is None and y is None:
                continue
            if x is None or y is None:
                issues.append("%s present live=%s built=%s" % (ty, x is not None, y is not None))
                continue
            for k in sorted(set(x) | set(y)):
                if x.get(k) != y.get(k):
                    issues.append("%s.%s\n        live : %s\n        built: %s"
                                  % (ty, k, str(x.get(k))[:220], str(y.get(k))[:220]))

        print("%-22s %3d lines of copy  %s" % (path, len(b), "OK" if not issues else "DIFFERS"))
        for i in issues:
            print("     " + i)
        fails += len(issues)

    print()
    print("all nine pages match live on copy, metadata and schema" if not fails
          else "%d difference(s) above - see KNOWN AND ACCEPTED in this file" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2
                  else os.path.join(root, "dist")))
