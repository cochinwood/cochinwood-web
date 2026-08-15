"""Check the hand-maintained cf-live site before it reaches a visitor.

WHY THIS EXISTS. cf-live has no build step, no generator and no package manager: what is committed
is byte-for-byte what Cloudflare Pages serves. That is the branch's great virtue and its whole risk
-- there is nothing between a typo and production. Until this file, nothing was.

Every check below is here because the thing it checks has already gone wrong, or would go wrong
invisibly. None of them look at style; a page that is ugly is a judgement call, and a page that
claims two different numbers is not.

    python tools/check_site.py            (from the cf-live working tree)

Stdlib only, deliberately: adding a dependency to a repo whose entire point is that it has none
would be a strange way to protect it.

IT LIVES ON `master` AND IS NOT DEPLOYED, exactly like tools/purge-css.py, for the reason CLAUDE.md
gives: Pages publishes every committed file on cf-live. Verified 15 Aug 2026 -- `.nojekyll` is
committed there and answers 200, so a checker committed to cf-live would be downloadable from
www.cochinwood.in. The workflow fetches this file from master and runs it against the cf-live tree.
"""
import json
import pathlib
import re
import sys
from urllib.parse import unquote

ROOT = pathlib.Path(".").resolve()
HTML = sorted(p for p in ROOT.rglob("*.html") if ".git" not in p.parts)

fails = []
def bad(check, where, detail):
    fails.append((check, where, detail))

def rel(p):
    try: return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError: return str(p)

LD = re.compile(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)


# ---------------------------------------------------------------------------------------------
# 1. Every ld+json block parses.
#
# 292 of the 293 pages carry a JSON-LD FAQ, 1431 blocks in all. They are hand-maintained inside
# hand-maintained HTML, they are invisible in a browser, and a single stray comma silently removes
# a page from every rich result Google would otherwise give it. The 10 Aug 2026 audit checked all
# 1431 by hand; this is that check, kept.
# ---------------------------------------------------------------------------------------------
def check_json_ld():
    n = 0
    for p in HTML:
        src = p.read_text(encoding="utf-8", errors="replace")
        for i, m in enumerate(LD.finditer(src), 1):
            n += 1
            try:
                json.loads(m.group(1))
            except Exception as e:
                bad("json-ld", f"{rel(p)} block {i}", str(e)[:120])
    if n == 0:
        bad("json-ld", "(site)", "no ld+json blocks found at all — the extractor is not looking "
                                "where it should, which would make this check pass on anything")
    return n


# ---------------------------------------------------------------------------------------------
# 2. The continent count in the copy matches the country list in the data.
#
# CLAUDE.md: "Never move the number without the list." 292 pages answer "Which export markets do
# you currently ship to?" with the countries spelled out, while the visible copy states a count.
# Changing one and not the other leaves the site claiming one number in the prose Google reads and
# another in the data Google indexes -- worse than either alone, and the exact self-refuting shape
# the 10 Aug 2026 audit existed to remove.
#
# The count is DERIVED from the answer rather than hard-coded here, so this file never becomes a
# second place the number has to be updated. If Chile lapses, the answer loses "in South America",
# the derived count becomes four, and the copy is then required to say four.
# ---------------------------------------------------------------------------------------------
CONTINENTS = ["Asia", "Africa", "Europe", "North America", "South America", "Oceania", "Australia"]
WORD = {"four": 4, "five": 5, "4": 4, "5": 5, "three": 3, "six": 6, "3": 3, "6": 6}
CLAIM = re.compile(r"\b(four|five|three|six|3|4|5|6)[\s -]*continents?\b", re.I)

# READ FROM THE SOURCE, NOT FROM PARSED JSON-LD, and the reason matters. The export-market FAQ is
# NOT one of the 1431 static ld+json blocks: it is built as a JavaScript object literal in an
# ordinary <script> and injected into the DOM at runtime. Parsing only the static blocks finds it on
# zero pages and this check then passes on everything, which is how it first behaved. Matching the
# source text finds it wherever it lives, static or injected, and keeps working if that changes.
MARKET_Q = re.compile(
    r'"Which export markets do you currently ship to\?"\s*,\s*"acceptedAnswer"\s*:\s*\{'
    r'[^}]*?"text"\s*:\s*"([^"]+)"', re.S)

def market_answer(src):
    m = MARKET_Q.search(src)
    return m.group(1) if m else None

def check_continents():
    """One canonical count, derived from the country list, enforced against every page's copy.

    This used to compare copy against the FAQ ON THE SAME PAGE, which worked only because all 292
    pages carried the FAQ — and they carried it in a script that never ran. With the FAQ made static
    it lives on one page, so a per-page comparison would pass on the 291 that no longer have it.
    The site-wide form is the stronger check anyway: the country list is the authority, and EVERY
    page's claim has to match it. It also catches two pages disagreeing with each other, which the
    per-page version never could."""
    answers = {}
    for p in HTML:
        t = market_answer(p.read_text(encoding="utf-8", errors="replace"))
        if t: answers[rel(p)] = t
    if not answers:
        bad("continents", "(site)", "the export-market FAQ is not on any page — the country list "
                                    "is the authority for the count and it has gone")
        return 0

    counts = set()
    for where, text in answers.items():
        named = [c for c in CONTINENTS if re.search(r"\b" + c + r"\b", text)]
        # South America must not be inferred from a Caribbean island — see CLAUDE.md. Haiti, Puerto
        # Rico and the Dominican Republic are NORTH America; reading them as South is what produced
        # the earlier false five-continent claim.
        if "South America" in named and "Chile" not in text:
            bad("continents", where,
                "the answer claims South America without naming Chile")
        counts.add(len(named))
    if len(counts) > 1:
        bad("continents", "(site)",
            f"the export-market answer names different continent counts on different pages: {sorted(counts)}")
        return len(answers)

    canon = counts.pop()
    for p in HTML:
        src = p.read_text(encoding="utf-8", errors="replace")
        claims = {WORD[m.group(1).lower()] for m in CLAIM.finditer(src)}
        if claims and claims != {canon}:
            bad("continents", rel(p),
                f"the copy claims {sorted(claims)} continent(s); the country list names {canon}")
    return len(answers)


# ---------------------------------------------------------------------------------------------
# 3. No two _headers rules that set Cache-Control can match one path.
#
# Cloudflare Pages MERGES every matching rule instead of letting the most specific win, so two
# rules matching one path append two Cache-Control values into a single header and the browser is
# handed a contradiction. This is why /assets/fonts.css and /assets/og/* are named individually
# rather than as /assets/* -- an /assets/* rule would collide with /assets/fonts/*. CLAUDE.md
# records that _headers and _redirects have both caused regressions here before.
# ---------------------------------------------------------------------------------------------
def check_headers():
    f = ROOT / "_headers"
    if not f.exists():
        bad("_headers", "_headers", "missing")
        return 0
    rules, cur = [], None
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            cur = (line.strip(), [])
            rules.append(cur)
        elif cur:
            cur[1].append(line.strip())
    caching = [(pat, hs) for pat, hs in rules
               if any(h.lower().startswith("cache-control") for h in hs)]

    def overlap(a, b):
        ap, bp = a.rstrip("*"), b.rstrip("*")
        a_glob, b_glob = a.endswith("*"), b.endswith("*")
        if a_glob and b_glob: return ap.startswith(bp) or bp.startswith(ap)
        if a_glob: return b.startswith(ap)
        if b_glob: return a.startswith(bp)
        return a == b

    for i in range(len(caching)):
        for j in range(i + 1, len(caching)):
            if overlap(caching[i][0], caching[j][0]):
                bad("_headers", f"{caching[i][0]} vs {caching[j][0]}",
                    "both set Cache-Control and both can match one path; Pages merges them into "
                    "two conflicting values on one header")
    return len(caching)


# ---------------------------------------------------------------------------------------------
# 4. Every internal link points at a file that exists.
#
# A 404 on this site is expensive out of proportion to the mistake: Cloudflare caches them, and a
# mistyped href can outlive the commit that fixed it. Pages serves /contact from contact.html, so a
# link resolves if the path exists as-is, with .html, or as a directory index.
# ---------------------------------------------------------------------------------------------
HREF = re.compile(r'(?:href|src)\s*=\s*"([^"]+)"', re.I)
SKIP = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|#|data:)", re.I)
# An href built by JavaScript — "/blogs/post/'+slugOf(k)+'" — is a template, not a URL. There is no
# file for it by design and there never will be.
TEMPLATED = re.compile(r"'\s*\+|\+\s*'|\$\{|<%")

def redirect_sources():
    """The `from` column of _redirects. A path with a rule is not a broken link — it is a 301."""
    f = ROOT / "_redirects"
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line.split()[0])
    return out

REDIRECTS = None

def redirected(path):
    for src in REDIRECTS:
        if src.endswith("*"):
            if path.startswith(src[:-1]):
                return True
        elif src == path:
            return True
    return False

def resolves(path):
    base = ROOT / unquote(path).lstrip("/")
    cands = [base, base / "index.html"]
    if not base.suffix:
        cands.append(base.with_name(base.name + ".html"))
    for c in cands:
        try:
            if c.is_file():
                return True
        except OSError:
            pass
    return redirected(path)

def check_links():
    global REDIRECTS
    REDIRECTS = redirect_sources()
    checked = 0
    for p in HTML:
        src = p.read_text(encoding="utf-8", errors="replace")
        for m in HREF.finditer(src):
            u = m.group(1).strip()
            if not u.startswith("/") or SKIP.match(u) or TEMPLATED.search(u):
                continue
            # Cloudflare rewrites mailto: into /cdn-cgi/l/email-protection at the edge. It is not in
            # the repo and must never be "fixed" — CLAUDE.md is explicit about that.
            if u.startswith("/cdn-cgi/"):
                continue
            path = u.split("#")[0].split("?")[0]
            if not path:
                continue
            checked += 1
            if not resolves(path):
                bad("links", rel(p), f"{u} is neither a committed file nor a _redirects rule")
    if checked == 0:
        bad("links", "(site)", "no root-relative links found — the extractor is not working")
    return checked


# ---------------------------------------------------------------------------------------------
# 5. The quote form still says what the Worker expects to hear.
#
# contact.html posts straight to the app's Worker. Rename a field here and the enquiry still
# submits, still returns the ordinary thank-you, and arrives with that field empty -- there is no
# error anywhere. The Turnstile error-callback is on the same footing: it is the only thing that
# reports the widget refusing a real buyer, and losing it would be silent by construction.
# ---------------------------------------------------------------------------------------------
FORM_FIELDS = ["name", "company", "email", "phone", "products", "destination", "description"]

def check_quote_form():
    p = ROOT / "contact.html"
    if not p.exists():
        bad("quote-form", "contact.html", "missing")
        return 0
    src = p.read_text(encoding="utf-8", errors="replace")
    if 'action="https://www.cochinwood.in/web-lead"' not in src:
        bad("quote-form", "contact.html", "the form no longer posts to /web-lead on the Worker")
    for f in FORM_FIELDS:
        if f'name="{f}"' not in src:
            bad("quote-form", "contact.html",
                f'field name="{f}" is gone; the Worker reads it and would store it empty')
    if 'name="cwq2_website"' not in src:
        bad("quote-form", "contact.html", "the honeypot field is gone, so the first spam gate is open")
    if "data-sitekey=" not in src:
        bad("quote-form", "contact.html", "the Turnstile widget has no sitekey")
    if 'data-error-callback="cwq2TsFail"' not in src:
        bad("quote-form", "contact.html",
            "the Turnstile error-callback is gone. It is the ONLY thing that reports the widget "
            "refusing real buyers -- the hourly probe is signed past that gate and an automated "
            "browser is never issued a token, so losing this is a silent blind spot")
    if "/ts-fail" not in src:
        bad("quote-form", "contact.html", "the beacon no longer points at /ts-fail")
    return 1


def main():
    n_ld = check_json_ld()
    n_faq = check_continents()
    n_hdr = check_headers()
    n_lnk = check_links()
    check_quote_form()

    print(f"pages          : {len(HTML)}")
    print(f"ld+json blocks : {n_ld}")
    print(f"export-market  : {n_faq} pages carry the FAQ")
    print(f"cache rules    : {n_hdr} set Cache-Control")
    print(f"internal links : {n_lnk}")

    if not fails:
        print("\nOK - the site says one thing, and every link goes somewhere.")
        return 0
    print(f"\n{len(fails)} PROBLEM(S):\n")
    for check, where, detail in fails:
        print(f"  [{check}] {where}\n      {detail}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
