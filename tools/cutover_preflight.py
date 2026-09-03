"""Cutover preflight - run this BEFORE touching anything in Cloudflare.

    python tools/cutover_preflight.py <reviewed-sha>

Answers one question: does the tree checked out here publish what was reviewed,
and does it serve every URL the live site serves today? If any check fails the
cutover does not start. Nothing here talks to Cloudflare, nothing here needs a
token, and nothing here changes what a visitor receives - it is safe to run as
often as you like.

WHY THIS EXISTS. CUTOVER-RUNBOOK.md used to say "change the production branch to
master". master is 49 files behind the reviewed work: publishing it 404s 109 of
the 293 live URLs, restores the quote form that posts to the CRM endpoint being
cancelled on 3 September, and drops the Content-Security-Policy. Every one of
those is a check below. A runbook step that names a branch cannot be verified;
a sha that must reproduce a measured result can.

THE ARGUMENT IS THE REVIEWED SHA, WHICH IS USUALLY NOT HEAD. A document cannot
name the commit that contains it, so pinning "publish exactly this sha" fails the
moment anyone edits the runbook. What actually matters is weaker and stronger at
once: the tree you publish must BUILD THE SAME BYTES as the tree that was
reviewed. So check 3 accepts HEAD == <reviewed-sha>, or HEAD a descendant of it
whose dist/ is byte-identical - which it proves by building <reviewed-sha> in a
throwaway worktree and comparing every file. A commit that changes documentation
passes. A commit that changes one character of output does not.

Checks, in the order a failure is cheapest to fix:

  1. worktree is clean                    - nothing uncommitted is in it
  2. the live pin is origin/cf-live's tip - build.py's LIVE_SHA, still current
  3. HEAD publishes the reviewed bytes    - HEAD == sha, or a doc-only descendant
  4. two builds are byte-identical        - the build is deterministic
  5. dist/ carries no source files        - source and config at the doc root
  6. the conversion beacon ships          - on every page, live bytes, right hash
  7. the required-check workflow ships    - dist/.github/..., live bytes
  8. the carried root files ship verbatim - as FILES, with cf-live's bytes
  9. quote form posts to /web-lead        - and NOT to crm.zoho.in
 10. dist/_headers enforces a CSP         - matching what production serves now
 11. every live URL is served or 301s     - all 647 paths on the pinned live
                                            commit, HTML and not, minus a
                                            reviewed ignore-list with reasons

CHECKS 6, 7 AND 8 EXIST BECAUSE THE COVERAGE CHECK CANNOT SEE THEIR FAILURES.
All three were reproduced against this script before they were written. Move
assets/cw-events.js aside and the build still exits 0 (build.py only warns), the
beacon lands on 0 of 253 pages -- the exact regression commit 09476b27 paid to
fix -- and check 11 still reported "620/620 covered", because the old path
/js/cw-events.js sits in the ignore list. Delete dist/.github/workflows/
site-checks.yml after the build and check 11 also reported 620/620, masked
twice over: by its ignore entry and by the /.github/* rule in _redirects, which
matches the path whether or not the file exists. Removing the ignore entry does
not close that second hole. And the four CARRIED_ROOT_FILES had neither an
existence-as-a-file assertion nor a byte assertion, so two mutations went
through fully green with a BYTE-IDENTICAL banner: substituting a 301 for the
IndexNow key, which coverage accepts as if it served the file, and shipping
CRLF-corrupted carried bytes, which grew dist/llms.txt from 11,918 to 12,042.
The controls prove the harness itself works -- deleting the IndexNow key,
llms.txt or any /files/ image each drops coverage to 619/620 and names the file.
A check that cannot fail on the thing it is said to cover is not a check, so
these three assert the bytes directly.

Exit 0 = every check passed. Exit 1 = do not start the cutover.
"""
import fnmatch
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

# THE PIN IS READ OUT OF build.py, NEVER RETYPED HERE. build.py carries 311 of
# dist/'s 607 files out of one commit's object store; if this file kept its own
# copy of that sha the two could drift and the gate would then be checking a
# commit the build never touched, which is worse than not checking at all.
# Imported rather than regex-scraped so that a rename of LIVE_SHA breaks loudly
# at import instead of silently matching nothing. build.py's module level only
# defines constants and reads content/export-markets.json; main() is guarded.
sys.path.insert(0, ROOT)
import build as _build                                          # noqa: E402
LIVE_REF_NAME = _build.LIVE_REF_NAME
LIVE_SHA = _build.LIVE_SHA
LIVE_REF = LIVE_SHA          # every live-side read below is against the pin
LIVE_PIN = _build.LIVE_PIN   # "origin/cf-live@<12>", for anything a human reads
CARRIED_WORKFLOW = _build.CARRIED_WORKFLOW
CARRIED_ROOT_FILES = _build.CARRIED_ROOT_FILES

# build.py:134 defaults MIRROR_DIR to a SIBLING checkout of a different repo
# (../cochinwood-site) and uses it as a photo root at build.py:135. That makes
# the build's output a function of where the checkout sits on disk. Pin it, so
# this script compares commits rather than directory layouts.
MIRROR = os.environ.get("MIRROR_DIR",
                        os.path.join(os.path.dirname(ROOT), "cochinwood-site"))

# The live quote form posts here. The CRM webform it replaced is cancelled on
# 3 Sep 2026 - a page posting there shows the buyer a success screen while the
# enquiry reaches nobody, which is worse than an error.
GOOD_FORM = "/web-lead"
DEAD_FORM = "crm.zoho.in"

# The deploy gate must run a checker it names, not one it looks up when it runs.
# WHICH sha is not this pattern's business - byte-equality with the pinned live
# blob already fixes that, and demanding one literal sha here turned a legitimate
# CHECKER_SHA bump into a failure whose message said the opposite of the truth.
CHECKER_SHA_RE = re.compile(rb"CHECKER_SHA[=:]\s*['\"]?([0-9a-fA-F]{40})")

# An IndexNow key file is a root .txt whose stem IS the key. Matched by shape
# rather than by the one literal key in CARRIED_ROOT_FILES, so rotating the key -
# a routine thing to do, and the reason the file is named after its contents in
# the first place - keeps the body-equals-filename assertion instead of quietly
# losing it the moment the name changes.
INDEXNOW_KEY_RE = re.compile(r"^[0-9a-fA-F]{8,128}\.txt$")

# ---- root paths a 301 must never stand in for -------------------------------
#
# NAMED HERE AND NOT READ OUT OF build.py, WHICH IS THE ONE PLACE THIS FILE
# DELIBERATELY KEEPS ITS OWN COPY. LIVE_SHA is imported precisely so the two
# cannot drift; these four are the opposite case, because the failure being
# gated IS the deletion of the declaration. Measured: drop the IndexNow key
# from build.py's CARRIED_ROOT_FILES and add "/015ad...txt / 301" to
# PORTED_REDIRECTS, and a check that iterates CARRIED_ROOT_FILES passes -- it
# reports "3 files, bytes match" and never looks for the fourth. Duplication is
# the mechanism: removing one of these is a two-place edit, and the second place
# is a gate whose reviewer has to be told why.
NO_REDIRECT_ROOT_FILES = {
    "015ad99674249c7dc418af21415b06bc.txt":
        "the IndexNow key. IndexNow verifies ownership by fetching this exact "
        "path and checking the body equals the filename, so a 301 fails "
        "verification and every submission to Bing, Yandex and Seznam stops "
        "silently while the site still looks fine.",
    "llms.txt":
        "11,918 bytes of hand-written copy that exists nowhere else in the "
        "repo, fetched by AI crawlers at this path by convention. dist/"
        "llms.html is a different artifact and a 301 to it serves HTML to a "
        "client that asked for text.",
    "favicon.png":
        "the root icon browsers and feed readers request by convention even "
        "when the <link rel=icon> tags point elsewhere; build.py copies it "
        "rather than redirecting because a copy costs no redirect slot.",
    "cwi-og-share-1200x630.png":
        "the og:image on 283 of cf-live's 293 pages. Every share card already "
        "sitting in a WhatsApp thread, a LinkedIn post or a Slack unfurl points "
        "at this path, and unfurl caches do not chase redirects reliably.",
}

# ---- live paths check 11 is allowed to skip, and why for each one ------------
#
# A SILENCED CHECK MUST SAY WHY IT IS SILENT. build.py's DROPPED_FROM_LIVE set
# this precedent for redirect rules that were considered and not carried; this is
# the same idea for URLs. Everything NOT in here has to be served or redirected,
# so the only way to make this check green is to fix the build or to add a line
# here with a reason someone can argue with. 27 entries against 647 live paths.
#
# Two kinds only. NEVER-A-URL: files that are in the repo because Pages serves
# the repo, not because anyone should fetch them. RETIRED WITH THE OLD THEME:
# Zoho-era assets that only the old markup ever referenced, and no page in the
# rebuild does.
_IGNORED = {
    # --- never a URL ---
    "/CLAUDE.md":
        "the working guide for whoever edits cf-live; it is at the web root only "
        "because Claude Code loads it from the repo root and Pages serves the "
        "repo verbatim. dist/ has no such file, so nothing to serve.",
    "/.github/workflows/site-checks.yml":
        "the definition of cf-live's required check. build.py DOES ship it in "
        "dist/ -- otherwise the publishing push deletes the gate -- but it is "
        "infrastructure, not a page, so it is not coverage. THAT IT SHIPS IS "
        "ASSERTED BY check_workflow(), NOT DELEGATED: this entry excusing the "
        "path is only half the reason the coverage check is blind to a missing "
        "workflow -- the other half is the /.github/* rule in _redirects, which "
        "matches the URL whether or not the file exists, so deleting the entry "
        "would not have closed the hole. check_workflow() compares the built "
        "bytes against the pinned live blob instead. Measured on the live site "
        "4 Sep 2026: /.github/workflows/site-checks.yml and /CLAUDE.md both "
        "answer 301 -> / while committed on cf-live, so the redirect really "
        "does hide the file and cf-live's _headers comment saying it cannot is "
        "the stale one; the noindex, no-store block is the second layer.",

    # --- retired with the old Zoho theme; 0 of the 253 rebuilt pages link any ---
    "/template/55562362302e4b8a8860fffaee39d549/js/eventhandler.js":
        "Zoho theme bundle, referenced only by Zoho-generated markup that no "
        "longer exists.",
    "/template/55562362302e4b8a8860fffaee39d549/js/header.js": "same theme bundle.",
    "/template/55562362302e4b8a8860fffaee39d549/js/language-list.js": "same theme bundle.",
    "/template/55562362302e4b8a8860fffaee39d549/js/megamenu.js": "same theme bundle.",
    "/template/55562362302e4b8a8860fffaee39d549/stylesheets/blog-style.css":
        "same theme bundle.",
    "/template/55562362302e4b8a8860fffaee39d549/stylesheets/style.css": "same theme bundle.",
    "/template/55562362302e4b8a8860fffaee39d549/stylesheets/sub-style.css":
        "same theme bundle.",
    "/zs-customcss.css":
        "the Zoho per-site override sheet, loaded as /zs-customcss.css?v=... by "
        "the old template only. The rebuild's CSS is one hashed bundle.",
    "/zs-lang_en_US.js": "Zoho's UI string table for the old template.",
    "/css/zsite-core.css": "Zoho platform CSS, superseded by /assets/bundle.<hash>.css.",
    "/js/zsite-core.js": "Zoho platform JS, superseded by /assets/site.<hash>.js.",
    "/js/cw-events.js":
        "REPUBLISHED, NOT RETIRED: this is the /cw-event conversion beacon, and "
        "the build now serves the identical bytes at "
        "/assets/cw-events.<hash>.js on all 253 pages. It moves because /js/* is "
        "cached for an hour and /assets/ pins content-addressed names for a "
        "year. ONLY THE OLD PATH IS SKIPPED HERE, AND check_beacon() ASSERTS THE "
        "NEW ONE. This reason used to delegate to build.py, 'which warns if "
        "assets/cw-events.js is missing' -- that was false as written: build.py's "
        "warn() only raises under STRICT and this script does not set it, so the "
        "delegation pointed at a check with no teeth. Reproduced by moving the "
        "source file aside: build exits 0, the beacon reaches 0 of 253 pages, "
        "and this coverage check still printed 620/620. check_beacon() now "
        "compares the built /assets/cw-events.<hash>.js against the pinned live "
        "blob and counts the pages carrying it.",
    "/assets/js/cw-hero-art.60842a8585.js":
        "the 58 KB base64 hero-art blob the 109 old city posts shared. Those "
        "posts are rebuilt without it and nothing else ever loaded it.",
    "/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js":
        "injected by Cloudflare's own email obfuscation and committed by "
        "accident; Cloudflare serves it from the edge when it is wanted.",
    "/site-conf.json":
        'an empty Zoho stub -- the whole file is {"apps":{}}. Nothing reads it '
        "and there is nothing in it to lose.",
    # The 10 superseded webfonts. The rebuilt pages load Poppins and Bree Serif
    # only; Cormorant and Heebo went with the old theme, and each hashed name is
    # requested by nothing that still exists.
    "/assets/fonts/cormorant-co3bmX5slCNuHLi8bLeY9MK7whWMhyjYp3tKgS4.woff2":
        "Cormorant, dropped with the old theme.",
    "/assets/fonts/cormorant-co3bmX5slCNuHLi8bLeY9MK7whWMhyjYpHtKgS4.woff2":
        "Cormorant, dropped with the old theme.",
    "/assets/fonts/cormorant-co3bmX5slCNuHLi8bLeY9MK7whWMhyjYpntKgS4.woff2":
        "Cormorant, dropped with the old theme.",
    "/assets/fonts/cormorant-co3bmX5slCNuHLi8bLeY9MK7whWMhyjYqXtK.woff2":
        "Cormorant, dropped with the old theme.",
    "/assets/fonts/cormorant-co3bmX5slCNuHLi8bLeY9MK7whWMhyjYrXtKgS4.woff2":
        "Cormorant, dropped with the old theme.",
    "/assets/fonts/heebo-NGS6v5_NC0k9P9GKTbFzsQ.woff2":
        "Heebo, dropped with the old theme.",
    "/assets/fonts/heebo-NGS6v5_NC0k9P9GYTbFzsQ.woff2":
        "Heebo, dropped with the old theme.",
    "/assets/fonts/heebo-NGS6v5_NC0k9P9H0TbFzsQ.woff2":
        "Heebo, dropped with the old theme.",
    "/assets/fonts/heebo-NGS6v5_NC0k9P9H2TbE.woff2":
        "Heebo, dropped with the old theme.",
    "/assets/fonts/heebo-NGS6v5_NC0k9P9H4TbFzsQ.woff2":
        "Heebo, dropped with the old theme.",
}

FAILED = []
PASSED = []


def check(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print("  %s  %-46s %s" % ("PASS" if ok else "FAIL", name, detail))
    return ok


def git(*args):
    out = subprocess.run(("git", "-C", ROOT) + args, capture_output=True, text=True)
    return out.returncode, out.stdout.strip(), out.stderr.strip()


def live_blob(path):
    """Raw object bytes of `path` at the pinned live commit, or None.

    cat-file, NEVER a checkout, for the reason build.py's _live_tree records:
    this machine has core.autocrlf=true, so checking these files out rewrites LF
    to CRLF and hands back site-checks.yml 59 bytes longer (2,933 -> 2,992, one
    per line) and cw-events.js 114 bytes longer (6,080 -> 6,194). Comparing dist/
    against those would fail on files that are in fact byte-perfect, and a gate
    that cries wolf gets waved through.
    """
    out = subprocess.run(("git", "-C", ROOT, "cat-file", "blob",
                          "%s:%s" % (LIVE_SHA, path)), capture_output=True)
    return out.stdout if out.returncode == 0 else None


def served_bytes(rel):
    """Bytes of one file inside dist/, or None when it is not there."""
    fp = os.path.join(DIST, rel.replace("/", os.sep))
    if not os.path.isfile(fp):
        return None
    with open(fp, "rb") as fh:
        return fh.read()


def check_live_pin():
    """build.py's LIVE_SHA must still be what origin/cf-live points at.

    311 OF THE 607 PUBLISHED FILES COME OUT OF THAT ONE COMMIT, so this is the
    check that stops a carry nobody has read. It is deliberately a hard failure
    and deliberately does NOT tell the operator to bump the pin: the correct
    response to "cf-live has moved" is to review what moved and then decide,
    because the alternative -- paste the new sha, re-run, green -- publishes
    whatever landed on cf-live in the meantime with no one having looked at it.
    """
    name = "live pin is %s's tip" % LIVE_REF_NAME
    rc_have, have, _ = git("rev-parse", "--verify", "--quiet",
                           LIVE_SHA + "^{commit}")
    if rc_have != 0 or have != LIVE_SHA:
        return check(name, False,
                     "pinned commit %s is not in this clone: run `git fetch "
                     "origin` (all 311 carried files would be skipped)"
                     % LIVE_SHA[:12])
    rc_tip, tip, err = git("rev-parse", "--verify", "--quiet", LIVE_REF_NAME)
    if rc_tip != 0 or not tip:
        return check(name, False,
                     "cannot resolve %s: %s" % (LIVE_REF_NAME, err[:60]))
    return check(name, tip == LIVE_SHA,
                 "pin %s, tip %s%s" % (LIVE_SHA[:12], tip[:12],
                 "" if tip == LIVE_SHA else
                 " -- RE-REVIEW the 311 carried files against the new tip, do "
                 "NOT just bump LIVE_SHA"))


def check_beacon():
    """The /cw-event beacon must ship, on every page, as cf-live's own bytes.

    THIS IS THE ONLY THING THAT CATCHES A MISSING BEACON. Reproduced before it
    was written: move assets/cw-events.js aside and build.py's warn() only
    appends to a list -- it raises solely under STRICT, which this script does
    not set -- so the build exits 0, the beacon lands on 0 of 253 pages, every
    tel, WhatsApp, quote-intent and form-success click goes uncounted, the
    conversion dashboard reads zero for a site still taking enquiries, and the
    coverage check below still printed a green 620/620 because /js/cw-events.js
    is on its ignore list. Bytes and page count are asserted here instead.

    BYTE-PARITY WITH THE LIVE BEACON IS THE RULE, NOT AN ACCIDENT OF THIS BUILD,
    so an operator who has just added a tracked event and hit this failure has
    not found a build fault -- the failure text says so, because the previous
    wording sent them looking for one. The beacon is the one script cf-live and
    this tree must serve identically through the cutover: the live page and the
    rebuilt page have to report the same events to the same dashboard while both
    are reachable, and the /assets/cw-events.<hash>.js name is the sha256 of
    those bytes, so changing the source changes the URL on all 253 pages at once.
    The legitimate route is therefore to land the new beacon on cf-live first and
    then move LIVE_SHA to the commit that carries it -- which is a review of
    everything else that landed there too, as check_live_pin() says.

    THE "name should be X for these bytes" CLAUSE THAT USED TO SIT HERE IS GONE
    because it was mathematically dead in the only case it could fire. `want` is
    sha256 of the LIVE blob and build.py names the file from sha256 of the
    working-tree bytes, so served == want is the same statement as data == live;
    the clause could only ever print once the bytes already differed, and it then
    told the operator the "correct" name was the hash of bytes they do not have.
    Observed on a 6,127-byte edited beacon: "name should be cw-events.853632c8.js
    for these bytes", where 853632c8 is the hash of the 6,080-byte live file.
    """
    name = "conversion beacon ships on every page"
    live = live_blob("js/cw-events.js")
    if live is None:
        return check(name, False,
                     "cannot read %s:js/cw-events.js -- `git fetch origin`"
                     % LIVE_SHA[:12])
    adir = os.path.join(DIST, "assets")
    found = sorted(n for n in (os.listdir(adir) if os.path.isdir(adir) else [])
                   if n.startswith("cw-events.") and n.endswith(".js"))
    if len(found) != 1:
        return check(name, False,
                     "found %d dist/assets/cw-events.<hash>.js, expected 1 -- "
                     "restore it with: git show %s:js/cw-events.js > "
                     "assets/cw-events.js" % (len(found), LIVE_REF_NAME))
    served = found[0]
    data = served_bytes("assets/" + served)
    want = "cw-events.%s.js" % hashlib.sha256(live).hexdigest()[:8]
    pages = [os.path.join(b, n) for b, _d, ns in os.walk(DIST)
             for n in ns if n.endswith(".html")]
    carrying = 0
    for fp in pages:
        with open(fp, encoding="utf-8", errors="replace") as fh:
            if served in fh.read():
                carrying += 1
    return check(name,
                 data == live and served == want and bool(pages)
                 and carrying == len(pages),
                 "dist/assets/%s on %d/%d pages, bytes %s %s:js/cw-events.js%s"
                 % (served, carrying, len(pages),
                    "match" if data == live else "DIFFER from", LIVE_SHA[:12],
                    "" if data == live else
                    " (served sha256 %s, live sha256 %s) -- serving cf-live's "
                    "beacon byte "
                    "for byte is the deliberate rule, not a build artefact, so "
                    "do NOT edit assets/cw-events.js to clear this: land the new "
                    "beacon on %s first, then move build.py's LIVE_SHA to the "
                    "commit carrying it and re-review that commit"
                    % (hashlib.sha256(data or b"").hexdigest()[:8],
                       hashlib.sha256(live).hexdigest()[:8], LIVE_REF_NAME)))


def check_workflow():
    """dist/ must carry cf-live's required-check workflow, byte for byte.

    THE PUBLISHING PUSH REPLACES THE WHOLE TRACKED TREE, so a dist/ without this
    file deletes the required check "The site says one thing" on the very push
    that publishes -- the check cannot run on that push, every later publish
    repeats the deletion, and the gate never reports that it removed itself.
    The coverage check below cannot see this: reproduced by deleting the built
    file, which left it reporting 620/620 covered and 0 misses, masked twice
    over by its own ignore entry and by the /.github/* rule in _redirects, which
    matches the path whether or not the file exists. The byte comparison also
    catches the subtler half: the copy on the 25-commits-stale local cf-live is
    2,098 bytes and fetches check_site.py from origin/master at run time, while
    the pinned one is 2,933 bytes and runs CHECKER_SHA=4678a8f5 (40 hex), so
    publishing the stale copy silently downgrades the deploy gate to an unpinned
    checker.

    THE SECOND ASSERTION ASKS THAT SOME CHECKER_SHA IS PINNED, NOT THAT ONE
    PARTICULAR SHA IS. It used to test for the literal
    CHECKER_SHA=4678a8f5139bd1499f1d5f3a4d75071321ce2ffd, which made it a
    blocker on legitimate work: the workflow's own comment says the checker
    stays frozen "until CHECKER_SHA moves. That is deliberate", so the day
    cf-live bumps it, an operator who does exactly the right thing -- re-review
    the new tip, update LIVE_SHA -- still failed here, and read a message
    claiming the workflow "does NOT pin CHECKER_SHA, so it would fetch the
    checker from origin/master", which was untrue of the workflow in front of
    them. Byte-equality with the pinned live blob above is the real assertion
    and it already covers which sha is pinned; what is left worth refusing on
    its own is a workflow that pins no checker at all and resolves one at run
    time, so that is what the regex states.
    """
    name = "required-check workflow ships in dist/"
    live = live_blob(CARRIED_WORKFLOW)
    if live is None:
        return check(name, False,
                     "cannot read %s:%s -- `git fetch origin`"
                     % (LIVE_SHA[:12], CARRIED_WORKFLOW))
    got = served_bytes(CARRIED_WORKFLOW)
    if got is None:
        return check(name, False,
                     "dist/%s is MISSING: publishing this tree deletes cf-live's "
                     "required check" % CARRIED_WORKFLOW)
    m = CHECKER_SHA_RE.search(got)
    return check(name, got == live and bool(m),
                 "dist/%s %s %s:%s (%d bytes)%s"
                 % (CARRIED_WORKFLOW,
                    "matches" if got == live else "DIFFERS from",
                    LIVE_SHA[:12], CARRIED_WORKFLOW, len(got),
                    (", pins CHECKER_SHA=%s" % m.group(1)[:8].decode("ascii"))
                    if m else
                    " -- and it pins NO CHECKER_SHA at all, so the deploy gate "
                    "would resolve check_site.py from origin/master at run time "
                    "and stop being a fixed checker"))


def live_root_indexnow_keys():
    """IndexNow key files at the pinned live commit's root, found by shape.

    READ OFF cf-live, NOT OUT OF build.py, so that rotating the key keeps the
    assertion instead of silently losing it, and so that deleting the key from
    build.py's CARRIED_ROOT_FILES cannot delete the requirement along with it.
    """
    rc, listing, _ = git("ls-tree", "--name-only", LIVE_SHA)
    if rc != 0:
        return []
    return sorted(n.strip() for n in listing.splitlines()
                  if INDEXNOW_KEY_RE.match(n.strip()))


def check_carried_root_files():
    """The carried root files must be FILES in dist/, carrying cf-live's bytes.

    A REDIRECT IS NOT COVERAGE FOR THESE FOUR, AND THE COVERAGE CHECK CANNOT SAY
    SO. Measured: delete the IndexNow key from build.py's CARRIED_ROOT_FILES and
    add "/015ad99674249c7dc418af21415b06bc.txt / 301" to PORTED_REDIRECTS, and
    the whole preflight went green at 620/620 covered while the file was
    genuinely absent from dist/. IndexNow verifies ownership by fetching that
    exact path and checking THE BODY EQUALS THE FILENAME, so a 301 fails
    verification and every submission to Bing, Yandex and Seznam stops silently
    with the site still looking fine. Existence is asserted here as a file on
    disk, which no _redirects rule can satisfy.

    THE EXPECTATION DOES NOT COME OUT OF build.py ALONE, WHICH IS THE WHOLE POINT
    AND IS DELIBERATELY UNLIKE LIVE_SHA ABOVE. A first version of this check
    iterated CARRIED_ROOT_FILES and was re-run against the redirect-substitution
    mutant: it passed, printing "3 files, bytes match", because the same edit that
    dropped the key from the build also dropped it from the check's own to-do
    list. A gate that reads its requirements out of the thing it is gating cannot
    fail on a requirement being deleted. So the four paths a 301 must never stand
    in for are named below in this file, the live commit is scanned for IndexNow
    keys by shape as well, and CARRIED_ROOT_FILES is folded in on top so that a
    fifth carried file added later is byte-checked without anyone remembering to
    come here. Removing one of these is then a two-place edit with a reason in
    both -- which is what "reviewable" means.

    THE BYTES ARE ASSERTED BECAUSE PLAIN DELETION WAS THE ONLY MUTATION ANYTHING
    CAUGHT. These four were the one part of the carried tree with neither an
    existence-as-a-file assertion nor a byte assertion, and two corruptions of
    them went through fully green: appending a single trailing newline to the
    carried key made the served body b"015ad...06bc\\n", so body == filename is
    now false and IndexNow verification fails; and CRLF-ing the carried .txt
    files grew dist/llms.txt from 11,918 to 12,042 bytes -- exactly the +124 that
    build.py's _live_tree docstring warns `git archive` and `git checkout`
    introduce on this core.autocrlf=true machine. The live side is read with
    `git cat-file` for that same reason: a checkout of the pinned blob would
    itself be CRLF-rewritten, and the comparison would then pass on corrupt bytes.

    THE INDEXNOW BODY IS CHECKED AGAINST ITS OWN SPECIFICATION, NOT ONLY AGAINST
    cf-live. Body == filename, no trailing whitespace and no newline, is the
    property the search engines actually fetch and test; stating it directly
    costs one comparison and catches the corruption in the terms the operator
    will have to fix it in.

    PRESENT IS NOT THE SAME AS SERVED, SO THE EMITTED RULES ARE READ TOO. The
    last mutation to survive this gate left all four files in dist/ and
    byte-perfect, and hid one behind a wildcard 301: "/*.txt / 301" in
    PORTED_REDIRECTS plus "/*.txt" in build.py's SHADOW_ALLOWED, which waives
    build.py's own shadow-dropper. Preflight stayed at 12/1 -- identical to
    control, no build warning, coverage 620/620. The rule scan below therefore
    matches _redirects sources as PATTERNS against these paths and honours no
    waiver list, because for these four being served IS the requirement, not a
    preference an owner can trade away with a written reason.
    """
    name = "carried root files ship verbatim"
    required = dict(NO_REDIRECT_ROOT_FILES)
    for k in live_root_indexnow_keys():
        required.setdefault(k, "an IndexNow key at %s's root, matched by shape."
                                % LIVE_PIN)
    for k in CARRIED_ROOT_FILES:
        required.setdefault(k, "declared in build.py's CARRIED_ROOT_FILES.")

    # Every emitted rule, as (line number, source, destination). Pages evaluates
    # _redirects before it serves a static asset, so a rule that MATCHES one of
    # these paths at best does nothing and at worst shadows the file -- and it is
    # the exact shape of the substitution this check exists for, so it is named
    # rather than tolerated.
    #
    # MATCHES, NOT EQUALS, AND NOT SUBJECT TO SHADOW_ALLOWED. Two rounds of
    # mutation testing died on the equality test; the third survived it. build.py
    # has its own shadow-dropper, and the single edit -- add "/*.txt / 301" to
    # PORTED_REDIRECTS -- is caught there: the build refuses to emit the rule and
    # prints "redirect dropped: /*.txt -> / (would shadow /015ad99674249c7dc418af
    # 21415b06bc.txt, which this build serves)". But SHADOW_ALLOWED waives that
    # dropper by design (/.github/* is in it precisely so a served file CAN be
    # hidden), so the two-line mutation -- the rule plus "/*.txt" in
    # SHADOW_ALLOWED -- shipped a tree where the IndexNow key was present and
    # byte-perfect underneath a 301, with the preflight fully green at 12/1,
    # coverage 620/620 and no build warning. Nothing between the mutation and the
    # cutover looked at it.
    #
    # SHADOW_ALLOWED MUST THEREFORE NOT REACH THESE FOUR. For the rest of the
    # tree, shadowing is a judgement call an owner is allowed to make with a
    # written reason. For these four, being SERVED is the requirement itself:
    # IndexNow verifies ownership by fetching the exact key path and comparing
    # the body with the filename, and a 301 is not a body -- verification fails,
    # every submission to Bing, Yandex and Seznam stops, and the site goes on
    # looking perfectly fine. The same shape of silence covers the other three.
    # So this gate reads the built artifact and asserts the property directly,
    # with no waiver list of its own to be added to.
    #
    # Cloudflare's * spans slashes, so /*.txt matches /015ad...txt and a rule
    # source is compared as a pattern. This mirrors build.py's _rule_re; the copy
    # is deliberate, for the reason NO_REDIRECT_ROOT_FILES gives above -- the
    # failure being gated is an edit to build.py, so the gate cannot borrow
    # build.py's opinion of what shadows what.
    rules = []
    red = os.path.join(DIST, "_redirects")
    if os.path.exists(red):
        with open(red, encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                line = line.strip()
                if line and not line.startswith("#") and len(line.split()) >= 2:
                    p = line.split()
                    rules.append((n, p[0], p[1]))

    def shadowing(rel):
        """(line, src, dst) of the first emitted rule Pages would answer for
        /rel, or None. First match wins, which is Pages' own precedence."""
        path = "/" + rel
        for n, src, dst in rules:
            pat = "^" + ".*".join(re.escape(part)
                                  for part in src.split("*")) + "$"
            if re.match(pat, path):
                return (n, src, dst)
        return None

    problems = []
    for rel in sorted(required):
        if rel not in CARRIED_ROOT_FILES:
            problems.append("%s is NOT in build.py's CARRIED_ROOT_FILES, so the "
                            "build does not carry it: %s A 301 in its place is "
                            "not an answer -- delete it from this file's "
                            "NO_REDIRECT_ROOT_FILES too, with a reason, if it is "
                            "genuinely no longer needed"
                            % (rel, required[rel]))
        live = live_blob(rel)
        if live is None:
            problems.append("%s is not on %s at all -- `git fetch origin`, "
                            "because the build silently skips what it cannot "
                            "read" % (rel, LIVE_SHA[:12]))
            continue
        hit = shadowing(rel)
        if hit:
            n, src, dst = hit
            problems.append("dist/_redirects line %d, `%s %s`, MATCHES /%s and "
                            "Pages answers a redirect before it serves a static "
                            "file, so /%s is shadowed: the bytes are in the tree "
                            "and the URL still 301s. That path must answer 200 "
                            "with its own bytes, because it is %s Adding %s to "
                            "build.py's SHADOW_ALLOWED does NOT make this legal "
                            "-- SHADOW_ALLOWED waives build.py's own dropper and "
                            "cannot waive this check, which is the whole point of "
                            "it. Delete the rule, or narrow its source so it stops "
                            "matching /%s. Coverage will read 620/620 either way; "
                            "it counts an answer, not the right one"
                            % (n, src, dst, rel, rel, required[rel], src, rel))
        if not os.path.isfile(os.path.join(DIST, rel.replace("/", os.sep))):
            problems.append("dist/%s is MISSING as a file (%s serves %d bytes "
                            "there); a _redirects rule pointing /%s elsewhere is "
                            "not coverage -- this path has to answer 200 with its "
                            "own bytes" % (rel, LIVE_SHA[:12], len(live), rel))
            continue
        got = served_bytes(rel)
        if got != live:
            # A same-length corruption -- a byte flipped, a character swapped --
            # made this line print the same number twice ("dist/favicon.png is
            # 2180 bytes and c59adae9ee7d:favicon.png is 2180"), which reads as
            # a check contradicting itself and invites the reader to dismiss it.
            # Lengths are the useful evidence when they differ; when they agree,
            # the digests are, so say whichever one is actually distinguishing.
            # Same reasoning as the beacon check, which has printed both sha256s
            # since it was written.
            if len(got) == len(live):
                how = ("both %d bytes but sha256 %s vs %s"
                       % (len(got), hashlib.sha256(got).hexdigest()[:12],
                          hashlib.sha256(live).hexdigest()[:12]))
            else:
                how = "%d bytes vs %d" % (len(got), len(live))
            problems.append("dist/%s and %s:%s differ -- %s. The served copy is "
                            "NOT cf-live's, so the cutover changes a file it is "
                            "only supposed to carry"
                            % (rel, LIVE_SHA[:12], rel, how))
            continue
        if INDEXNOW_KEY_RE.match(rel):
            want = rel[: -len(".txt")]
            if got != want.encode("ascii"):
                problems.append("dist/%s must contain exactly %r and contains "
                                "%r -- IndexNow fetches this path and compares "
                                "the body with the filename, so a trailing "
                                "newline or a CRLF fails verification and every "
                                "submission to Bing, Yandex and Seznam stops"
                                % (rel, want, got[:64].decode("ascii", "replace")))
    ok = check(name, not problems,
               "%d files, bytes match %s" % (len(required), LIVE_SHA[:12])
               if not problems else problems[0])
    for p in problems[1:]:
        print("       %s" % p)
    return ok


def canonical(path):
    """The URL a visitor requests, from a file path in a served tree.

    cf-live serves about.html at /about; this build serves about/index.html at
    /about. Comparing the two needs both reduced to the same key, or every page
    reads as missing and the check is noise.
    """
    p = "/" + path.strip("/").replace("\\", "/")
    if p.endswith("/index.html"):
        p = p[: -len("index.html")]
    elif p.endswith(".html"):
        p = p[:-5]
    p = "/" + p.strip("/")
    return p if p != "/" else "/"


IGNORED_LIVE_PATHS = {canonical(p) for p in _IGNORED}


def tree_hashes():
    acc = {}
    for base, _dirs, names in os.walk(DIST):
        for n in names:
            full = os.path.join(base, n)
            rel = os.path.relpath(full, DIST).replace("\\", "/")
            with open(full, "rb") as fh:
                acc[rel] = hashlib.sha256(fh.read()).hexdigest()
    return acc


def build():
    out = subprocess.run((sys.executable, "build.py"), cwd=ROOT,
                         capture_output=True, text=True,
                         env=dict(os.environ, MIRROR_DIR=MIRROR))
    banner = [l for l in out.stdout.splitlines() if l.startswith("BUILD OK")]
    return out.returncode, (banner[0] if banner else out.stdout.strip()[-200:])


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    want = sys.argv[1]

    print("\ncutover preflight -- %s\n" % ROOT)

    # 1. Nothing uncommitted. Checked first because every later check reads the
    #    working tree, and an uncommitted edit makes all of them describe
    #    something that is not what would be published.
    rc, dirty, _ = git("status", "--porcelain")
    check("worktree is clean", rc == 0 and not dirty,
          "%d modified path(s)" % len(dirty.splitlines()) if dirty else "")

    # 2. The pin, before anything is built with it. Cheapest possible failure:
    #    it is one rev-parse, and it is the difference between carrying 311
    #    reviewed files and carrying 311 unread ones.
    check_live_pin()

    # 3 + 4. Determinism, and equivalence to the reviewed tree.
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    rc1, banner = build()
    first = tree_hashes()
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    rc2, _ = build()
    second = tree_hashes()
    check("build exits 0, twice", rc1 == 0 and rc2 == 0, "exit %s / %s" % (rc1, rc2))
    check("two builds byte-identical", first == second and bool(first),
          "%d files" % len(second))
    print("       banner: %s" % banner)

    rc, head, _ = git("rev-parse", "HEAD")
    if rc == 0 and head.startswith(want):
        check("HEAD publishes the reviewed bytes", True,
              "HEAD == %s" % want[:12])
    else:
        # HEAD moved past the reviewed sha - normally a documentation commit.
        # Trust nothing about that: build the reviewed sha and diff the output.
        rc_anc, _, _ = git("merge-base", "--is-ancestor", want, "HEAD")
        if rc_anc != 0:
            check("HEAD publishes the reviewed bytes", False,
                  "HEAD=%s is NOT a descendant of %s" % (head[:12], want[:12]))
        else:
            # OUTSIDE ROOT, deliberately. build.py:134 resolves MIRROR_DIR from
            # the PARENT of the checkout, so where the baseline sits on disk is
            # an input to the build. Both builds also get MIRROR_DIR pinned to
            # the same absolute path below, so the comparison measures the
            # commits and not their locations.
            tmp = tempfile.mkdtemp(prefix="cwi-preflight-baseline-")
            os.rmdir(tmp)   # git worktree add wants to create it itself
            rc_wt, _, err = git("worktree", "add", "--detach", tmp, want)
            if rc_wt != 0:
                check("HEAD publishes the reviewed bytes", False,
                      "cannot check out %s: %s" % (want[:12], err[:70]))
            else:
                env = dict(os.environ, MIRROR_DIR=MIRROR)
                out = subprocess.run((sys.executable, "build.py"), cwd=tmp,
                                     capture_output=True, text=True, env=env)
                base = {}
                bdist = os.path.join(tmp, "dist")
                for b, _d, ns in os.walk(bdist):
                    for n in ns:
                        f = os.path.join(b, n)
                        rel = os.path.relpath(f, bdist).replace("\\", "/")
                        with open(f, "rb") as fh:
                            base[rel] = hashlib.sha256(fh.read()).hexdigest()
                subprocess.run(("git", "-C", ROOT, "worktree", "remove",
                                "--force", tmp), capture_output=True)
                if out.returncode != 0 or not base:
                    # Never report "the trees differ" when the baseline simply
                    # did not build - that sends the reader hunting a content
                    # change that does not exist.
                    check("HEAD publishes the reviewed bytes", False,
                          "baseline build of %s FAILED (exit %s, %d files): %s"
                          % (want[:12], out.returncode, len(base),
                             (out.stderr or out.stdout).strip()[-120:]))
                else:
                    differ = sorted(k for k in set(base) | set(second)
                                    if base.get(k) != second.get(k))
                    check("HEAD publishes the reviewed bytes", not differ,
                          "HEAD=%s is a descendant of %s; dist/ %s (%d files)"
                          % (head[:12], want[:12],
                             "byte-identical" if not differ else
                             "DIFFERS in %d file(s): %s" % (len(differ),
                                                            ", ".join(differ[:3])),
                             len(second)))

    # 5. dist/ is a document root. Anything in it is public. A tree with build.py
    #    and CUTOVER-RUNBOOK.md at its root has been served for real once already
    #    (deployment adddbea8) - see CUTOVER-RUNBOOK.md step 0.
    #
    #    .py AND .md WERE NO LONGER THE WHOLE RISK. dist/ now deliberately ships
    #    an infrastructure file - .github/workflows/site-checks.yml, the one .yml
    #    in 607 - so "config never appears here" stopped being true, and a
    #    future stray .yml, .json, .env or .toml would have passed this check in
    #    silence while being fetchable from the document root. The extensions
    #    below are the ones that carry configuration or credentials; the single
    #    intentional path is allowed by name rather than by extension, so a
    #    SECOND .yml anywhere in the tree still fails. Nothing dist/ legitimately
    #    serves is on this list: the 607 files are html, jpg, webp, woff2, png,
    #    xml, txt, js, css, .nojekyll, _headers, _redirects and that one .yml.
    #
    #    .json IS ON THE LIST AND A PWA MANIFEST WOULD TRIP IT. Nothing in this
    #    build emits one today, so the check costs nothing now and would catch
    #    the next config file that lands in the document root by accident. The
    #    failure message names LEAK_ALLOWED for exactly that case: a .json that
    #    is genuinely meant to be public gets added there by path, deliberately,
    #    the same way the workflow is - it is not a reason to weaken the suffix
    #    list, because that would re-open the leak for every other .json too.
    LEAK_SUFFIXES = (".py", ".md", ".yml", ".yaml", ".json", ".env", ".toml",
                     ".ini", ".cfg", ".sh", ".ps1", ".bat", ".pem", ".key")
    LEAK_ALLOWED = {CARRIED_WORKFLOW}
    leaked = sorted(r for r in second
                    if r.endswith(LEAK_SUFFIXES) and r not in LEAK_ALLOWED)
    check("no source or config files in dist/", not leaked,
          "" if not leaked else
          "%s -- these are fetchable from the document root. If one is meant to "
          "be public, add its exact path to LEAK_ALLOWED in this file rather "
          "than dropping its suffix from LEAK_SUFFIXES"
          % ", ".join(leaked[:4]))

    # 6 + 7. The two blocker fixes the coverage check below is blind to. Both
    #    read dist/ directly and compare against the pinned live commit, because
    #    a delegated check ("build.py warns about it") is not a check: build.py's
    #    warn() only raises under STRICT, and STRICT is deliberately NOT set for
    #    the builds above - this tree emits 2 by-design warnings (7 redirect
    #    targets rewritten to match LEGACY_REDIRECTS, 13 live rules dropped with
    #    recorded reasons), so STRICT=1 would fail a clean, reviewed tree and
    #    the first operator to hit that would learn to ignore the gate.
    check_beacon()
    check_workflow()

    # 8. The four root files carried out of cf-live's object store. Same reason
    #    as 6 and 7 -- the coverage check below accepts a 301 as coverage, so a
    #    redirect substituted for the IndexNow key reads as 620/620 -- plus a
    #    byte comparison, because these four were the only carried files whose
    #    CONTENT nothing asserted, and corrupt bytes are the failure mode that
    #    leaves the file present and the site looking fine.
    check_carried_root_files()

    # 9. The form. Both directions, because "the good endpoint is present" and
    #    "the dead endpoint is absent" can both be false at once.
    good = dead = 0
    for rel in second:
        if not rel.endswith(".html"):
            continue
        with open(os.path.join(DIST, rel), encoding="utf-8", errors="replace") as fh:
            body = fh.read()
        good += body.count('action="https://www.cochinwood.in' + GOOD_FORM)
        dead += body.count(DEAD_FORM)
    check("quote form posts to %s" % GOOD_FORM, good > 0, "%d page(s)" % good)
    check("no page posts to %s" % DEAD_FORM, dead == 0, "%d hit(s)" % dead)

    # 10. The CSP production serves today. master has no CSP at all, so a flip to
    #    master silently drops a header nobody would notice missing.
    hdr = os.path.join(DIST, "_headers")
    csp = ""
    if os.path.exists(hdr):
        with open(hdr, encoding="utf-8") as fh:
            for line in fh:
                if line.strip().lower().startswith("content-security-policy:"):
                    csp = line.split(":", 1)[1].strip()
    check("dist/_headers enforces a CSP", bool(csp), csp[:60])

    # 11. The whole point. Every URL a visitor can reach today must still resolve.
    #
    # THIS CHECK USED TO BUILD BOTH OF ITS SETS FROM .html ONLY, on both sides,
    # and so reported a green "293/293 covered" for a tree in which 328 live URLs
    # would have 404'd -- all 328 non-HTML, which is precisely what the filters
    # made invisible. A check that can only fail on the class of file it already
    # covers is not a check. Both filters are gone; the live set is now all 647
    # paths on cf-live and the served set is all of dist/. canonical() stays,
    # because /about is still about.html on one side and about/index.html on the
    # other.
    rc, listing, err = git("ls-tree", "-r", "--name-only", LIVE_REF)
    if rc != 0:
        check("live URL set readable (%s)" % LIVE_PIN, False, err[:80])
    else:
        live = sorted({canonical(l) for l in listing.splitlines() if l.strip()}
                      - IGNORED_LIVE_PATHS)
        served = {canonical(os.path.join(b, n).replace(DIST, "").lstrip("\\/"))
                  for b, _d, ns in os.walk(DIST) for n in ns}
        rules = []
        red = os.path.join(DIST, "_redirects")
        if os.path.exists(red):
            with open(red, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith("#") and len(line.split()) >= 2:
                        rules.append(line.split()[0])
        missing = []
        for u in live:
            if u in served:
                continue
            pats = [r if ("*" in r or ":splat" in r) else canonical(r) for r in rules]
            if any(fnmatch.fnmatch(u, p.replace(":splat", "*")) or
                   p.replace(":splat", "*") == u for p in pats):
                continue
            missing.append(u)
        check("every live URL served or redirected",
              not missing,
              "%d/%d covered, %d reviewed-ignore%s"
              % (len(live) - len(missing), len(live), len(IGNORED_LIVE_PATHS),
                 ("; first missing " + missing[0]) if missing else ""))
        if missing:
            print("       %d live URL(s) would 404. First 10:" % len(missing))
            for u in missing[:10]:
                print("         %s" % u)

    print("\n%d passed, %d failed" % (len(PASSED), len(FAILED)))
    if FAILED:
        print("\nDO NOT START THE CUTOVER. Failed: %s\n" % ", ".join(FAILED))
        return 1
    print("\nPreflight clean. Proceed to CUTOVER-RUNBOOK.md step 2.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
