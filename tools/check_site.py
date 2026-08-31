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
import html as html_mod
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

# Fields the Worker does NOT read. They reach the lead book only because the page's own JS folds
# them into `description` before submitting, so losing that loop loses the thickness, the quantity
# and the quote basis off every enquiry -- with no error at either end.
PACKED_FIELDS = ["spec_grade", "quantity", "incoterm"]

# The retired CRM webform. Its subscription lapses on 3 Sep 2026; a form posting there would show
# the buyer a success page while the enquiry reached nobody, which is the worst shape this failure
# can take. Named here so a reappearance is caught by this file rather than by a silent quarter.
DEAD_CRM = ["crm.zoho.in", "WebToLeadForm", "LEADCF", "xnQsjsdp", "xmIwtLD"]

def check_quote_form():
    # BOTH LAYOUTS, and that is the entire point of this line. cf-live is a flat mirror with
    # contact.html at the root, while `python build.py` emits pretty URLs and puts the page at
    # contact/index.html. This check only ever looked for the flat name, so against a built tree it
    # reported a bare "contact.html missing" -- which reads like a harmless layout quirk -- and NOT
    # ONE of the assertions below ever ran. That is how the build carried a quote form still posting
    # to the retired CRM webform: the single check written to catch exactly that could not see the
    # file it was written to check.
    cands = [ROOT / "contact.html", ROOT / "contact" / "index.html"]
    p = next((c for c in cands if c.exists()), None)
    if p is None:
        bad("quote-form", "contact.html",
            "missing -- looked for " + " and ".join(rel(c) for c in cands))
        return 0
    where = rel(p)
    src = p.read_text(encoding="utf-8", errors="replace")
    if 'action="https://www.cochinwood.in/web-lead"' not in src:
        bad("quote-form", where, "the form no longer posts to /web-lead on the Worker")
    for f in FORM_FIELDS:
        if f'name="{f}"' not in src:
            bad("quote-form", where,
                f'field name="{f}" is gone; the Worker reads it and would store it empty')
    for f in PACKED_FIELDS:
        if f'name="{f}"' not in src:
            bad("quote-form", where,
                f'field name="{f}" is gone; the Worker never reads it directly, so it reaches the '
                f'lead book only via the data-pack loop below')
        elif f'data-pack=' not in src:
            bad("quote-form", where,
                f'name="{f}" is present but nothing carries data-pack; it would be posted and '
                f'dropped, losing the thickness/quantity/quote basis off every enquiry')
    for dead in DEAD_CRM:
        if dead in src:
            bad("quote-form", where,
                f'"{dead}" is back. The CRM webform was retired and its subscription is cancelled; '
                f'a form posting there thanks the buyer and delivers the enquiry nowhere')
    if 'name="cwq2_website"' not in src:
        bad("quote-form", where, "the honeypot field is gone, so the first spam gate is open")
    if "data-sitekey=" not in src:
        bad("quote-form", where, "the Turnstile widget has no sitekey")
    if 'data-error-callback="cwq2TsFail"' not in src:
        bad("quote-form", where,
            "the Turnstile error-callback is gone. It is the ONLY thing that reports the widget "
            "refusing real buyers -- the hourly probe is signed past that gate and an automated "
            "browser is never issued a token, so losing this is a silent blind spot")
    if "/ts-fail" not in src:
        bad("quote-form", where, "the beacon no longer points at /ts-fail")
    if 'name="cf-turnstile-response"' not in src and "cf-turnstile-response" not in src:
        bad("quote-form", where,
            "nothing checks for a Turnstile token before submitting. Without that gate a buyer "
            "whose challenge failed is shown the ordinary thank-you while the Worker refuses the "
            "enquiry -- the success card keys off nothing but ?sent=1")
    return 1


# ---------------------------------------------------------------------------------------------
# 6. The page and its markup say the same thing.
#
# check_json_ld above proves a block PARSES. It has never proved a block is TRUE, and on 28 Aug
# 2026 that gap cost something real: /faq's visible answer said container flooring was "built to
# ISO container floor specifications and the IICL TB-001 bulletin" while its own FAQPage schema
# said Okoume-faced boards on a rubberwood core -- two different products, and the visible copy
# was claiming a certification container-flooring-plywood.html says in terms that we do not hold.
# It was live and indexed, and this checker reported OK on it every run, including the one that
# gated the merge which published it.
#
# Google's FAQPage guidance is that the answer must appear on the page. Enforcing that is what
# would have caught it: the schema text was nowhere in the visible copy.
#
# WHAT IS ENFORCED IS THE FACTS, NOT THE WORDS, and that line was drawn by measurement rather
# than taste. Requiring the schema text to appear verbatim fails 76 of the 481 displayed answers
# on today's site, and every one sampled is a harmless rewrite -- "blocks or bearers in the pallet
# must be treated" against "blocks or bearers must be treated". A gate that cries wolf 76 times is
# one people learn to bypass, and bypassing is worse than not checking.
#
# So a schema answer must keep the HARD FACTS of the visible one: standard and specification
# tokens (IS 710, ISPM-15, IICL TB-001), species and resin names, and numbers with units. Those
# are exactly what a paraphrase preserves and a contradiction changes.
#
# CALIBRATED IN BOTH DIRECTIONS, because a rule that fires on nothing is as useless as one that
# fires on everything:
#     today's site, 481 displayed answers ...... 0 failures
#     faq.html before c4b93d74, IICL live ...... 1 failure, missing "rubberwood" and "1mm"
# That one is the contradiction this check exists for -- the visible copy claimed film-faced
# boards built to ISO, the schema said Okoume on a rubberwood core, and no earlier check in this
# file could see it.
#
# TWO THINGS ARE COUNTED RATHER THAN FAILED, both pre-existing and neither a contradiction: a
# question with no matching visible heading (keyword-expanded rewrites), and an answer that says
# the right things in different words. Printed so they cannot grow unnoticed.
# ---------------------------------------------------------------------------------------------
TAGS = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
COMMENT = re.compile(r"<!--.*?-->", re.S)
ANYTAG = re.compile(r"<[^>]+>")


def norm_text(t):
    t = html_mod.unescape(t)
    for a, b in (("\u00a0", " "), ("\u2013", "-"), ("\u2014", "-"), ("\u2019", "'"),
                 ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u2212", "-")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def visible_text(src):
    t = COMMENT.sub(" ", TAGS.sub(" ", src))
    return norm_text(ANYTAG.sub(" ", t))


def faq_questions(src):
    """(name, answer) for every FAQPage Question, however the blocks are nested."""
    out = []
    for m in LD.finditer(src):
        try:
            doc = json.loads(m.group(1))
        except Exception:
            continue
        for node in (doc if isinstance(doc, list) else [doc]):
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph") if isinstance(node.get("@graph"), list) else [node]
            for g in graph:
                if not isinstance(g, dict) or g.get("@type") != "FAQPage":
                    continue
                ents = g.get("mainEntity") or []
                for q in (ents if isinstance(ents, list) else [ents]):
                    if not isinstance(q, dict):
                        continue
                    a = q.get("acceptedAnswer") or {}
                    out.append((str(q.get("name") or ""),
                                str(a.get("text") or "") if isinstance(a, dict) else ""))
    return out


SPEC = re.compile(r"\b(?:IS|ISO|ISPM|IICL|TB|EN|BS|ASTM|BWP|BWR|MR|HDF|MDF|PF|MUF|UF)"
                  r"[ -]?\d[\w-]*\b")
NAMED = re.compile(r"\b(?:ISPM|IICL|ISO|BWP|BWR|Okoume|Gurjan|rubberwood|keruing|apitong|birch|"
                   r"eucalyptus|poplar|hardwood|softwood|melamine|phenolic|formaldehyde)\b", re.I)
QTY = re.compile(r"\b\d+(?:\.\d+)?\s?(?:mm|cm|kg|kg/m3|%|ply|plies)\b", re.I)

def hard_facts(t):
    """Standards, species, resins and measurements -- what a paraphrase keeps."""
    out = set()
    for rx in (SPEC, NAMED, QTY):
        for m in rx.findall(norm_text(t)):
            out.add(re.sub(r"[ -]", "", str(m)).lower())
    return out


def check_faq_matches_page():
    n_q = 0
    loose_names = 0
    reworded = 0
    for p in HTML:
        src = p.read_text(encoding="utf-8", errors="replace")
        qs = faq_questions(src)
        if not qs:
            continue
        vis = visible_text(src)
        vis_facts = hard_facts(vis)
        for name, answer in qs:
            q = norm_text(name)
            a = norm_text(ANYTAG.sub(" ", answer))
            if not a:
                bad("faq-answer", rel(p), 'the answer to "%s" is empty' % name[:60])
                continue
            if not q or q not in vis:
                # The page does not DISPLAY this question, so there is no visible answer for the
                # schema to contradict. Counted, not failed -- see the note above.
                loose_names += 1
                continue
            n_q += 1
            if a not in vis:
                reworded += 1
            missing = sorted(hard_facts(a) - vis_facts)
            if missing:
                bad("faq-answer", rel(p),
                    'the page ASKS "%s" and its schema answer states facts the page does not.\n'
                    "      only in the schema : %s\n"
                    "      schema answer      : %s\n"
                    "      Googlebot reads that; a buyer reads the page. Check which is true "
                    "against the product page before changing either."
                    % (name[:60], ", ".join(missing), a[:140]))
    return n_q, loose_names, reworded


# ---------------------------------------------------------------------------------------------
# 7. Each page agrees with itself about its own address.
#
# canonical, og:url and the file's own path are three statements of one fact, maintained by hand
# across 293 files. A canonical pointing at the wrong page hands that page's ranking to another
# one; an og:url disagreeing with it makes every share resolve somewhere the canonical denies.
# Neither is visible in a browser and neither breaks anything a person would notice.
#
# THE EXPECTED URL IS DERIVED THE WAY PAGES SERVES IT, not the way the file is named: Pages strips
# .html and serves index.html at the directory root. Checking against the filename would fail
# every page on the site.
# ---------------------------------------------------------------------------------------------
SITE = "https://www.cochinwood.in"
CANON = re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]*>', re.I)
OGURL = re.compile(r'<meta[^>]+property=["\']og:url["\'][^>]*>', re.I)
# NOT `HREF`: the link checker already owns that name at the top of the file, and its pattern
# matches href OR src. Redefining it here silently dropped 3,877 links from that check --
# same tree, 43451 before and 39574 after, with nothing failing to say so.
CANON_HREF = re.compile(r'href\s*=\s*"([^"]+)"', re.I)
CONTENT = re.compile(r'content\s*=\s*"([^"]+)"', re.I)
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
# The hero art on every blog post carries an <svg><title> for screen readers. It is an
# accessibility label, not the document title, and counting it reported 24 pages as having
# two titles when every one of them has exactly one.
SVG = re.compile(r"<svg\b.*?</svg>", re.S | re.I)


def served_url(p):
    r = rel(p)
    if r == "index.html":
        return SITE + "/"
    if r.endswith("/index.html"):
        return SITE + "/" + r[:-len("/index.html")] + "/"
    return SITE + "/" + r[:-len(".html")]


def attr(pattern, tag):
    m = pattern.search(tag)
    return m.group(1) if m else ""


def absolute(u):
    """A canonical may be relative -- /blogs/page/10 is valid and Google resolves it.

    Demanding an absolute URL would have failed 28 pages that are perfectly correct, which is how
    a checker teaches people to ignore it."""
    u = (u or "").strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return SITE + u
    return u


def check_self_reference():
    n = 0
    for p in HTML:
        if rel(p) == "404.html":      # _redirects sends /404 home; it has no address of its own
            continue
        src = p.read_text(encoding="utf-8", errors="replace")
        want = served_url(p).rstrip("/") or SITE
        n += 1

        cs = CANON.findall(src)
        if len(cs) != 1:
            bad("canonical", rel(p), "expected exactly one rel=canonical, found %d" % len(cs))
        else:
            got = absolute(attr(CANON_HREF, cs[0])).rstrip("/") or SITE
            if got != want:
                bad("canonical", rel(p), "points at %s\n      expected %s" % (got, want))

        og = OGURL.findall(src)
        if len(og) > 1:
            bad("og:url", rel(p), "%d og:url tags; they cannot all be right" % len(og))
        elif og:
            got = absolute(attr(CONTENT, og[0])).rstrip("/") or SITE
            if got != want:
                bad("og:url", rel(p), "says %s\n      but the page is served at %s" % (got, want))

        ts = TITLE.findall(SVG.sub(" ", src))
        if len(ts) != 1:
            bad("title", rel(p), "expected exactly one <title>, found %d" % len(ts))
        elif not norm_text(ts[0]):
            bad("title", rel(p), "the <title> is empty")
    return n


def main():
    n_ld = check_json_ld()
    n_faq = check_continents()
    n_hdr = check_headers()
    n_lnk = check_links()
    check_quote_form()
    n_q, loose, reworded = check_faq_matches_page()
    n_self = check_self_reference()

    print(f"pages          : {len(HTML)}")
    print(f"ld+json blocks : {n_ld}")
    print(f"export-market  : {n_faq} pages carry the FAQ")
    print(f"cache rules    : {n_hdr} set Cache-Control")
    print(f"internal links : {n_lnk}")
    print(f"faq answers    : {n_q} checked against the page that asks the question")
    print(f"  reworded     : {reworded} say it in different words (counted, not failed)")
    print(f"  orphaned     : {loose} questions with no visible heading (counted, not failed)")
    print(f"self-reference : {n_self} pages checked for canonical, og:url and title")

    if not fails:
        print("\nOK - the site says one thing, and every link goes somewhere.")
        return 0
    print(f"\n{len(fails)} PROBLEM(S):\n")
    for check, where, detail in fails:
        print(f"  [{check}] {where}\n      {detail}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
