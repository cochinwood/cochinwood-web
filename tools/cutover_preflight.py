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
  8. quote form posts to /web-lead        - and NOT to crm.zoho.in
  9. dist/_headers enforces a CSP         - matching what production serves now
 10. every live URL is served or 301s     - all 647 paths on the pinned live
                                            commit, HTML and not, minus a
                                            reviewed ignore-list with reasons

CHECKS 6 AND 7 EXIST BECAUSE THE COVERAGE CHECK CANNOT SEE EITHER FAILURE. Both
were reproduced against this script before they were written. Move
assets/cw-events.js aside and the build still exits 0 (build.py only warns), the
beacon lands on 0 of 253 pages -- the exact regression commit 09476b27 paid to
fix -- and check 10 still reported "620/620 covered", because the old path
/js/cw-events.js sits in the ignore list. Delete dist/.github/workflows/
site-checks.yml after the build and check 10 also reported 620/620, masked
twice over: by its ignore entry and by the /.github/* rule in _redirects, which
matches the path whether or not the file exists. Removing the ignore entry does
not close that second hole. The controls prove the harness itself works --
deleting the IndexNow key, llms.txt or any /files/ image each drops it to
619/620 and names the file. A check that cannot fail on the thing it is said to
cover is not a check, so these two assert the bytes directly.

Exit 0 = every check passed. Exit 1 = do not start the cutover.
"""
import fnmatch
import hashlib
import os
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

# ---- live paths check 10 is allowed to skip, and why for each one ------------
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
                    "" if served == want else
                    " -- name should be %s for these bytes" % want))


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
    the pinned one is 2,933 bytes and runs
    CHECKER_SHA=4678a8f5139bd1499f1d5f3a4d75071321ce2ffd, so publishing the
    stale copy silently downgrades the deploy gate to an unpinned checker.
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
    pinned = b"CHECKER_SHA=4678a8f5139bd1499f1d5f3a4d75071321ce2ffd" in got
    return check(name, got == live and pinned,
                 "dist/%s %s %s:%s (%d bytes)%s"
                 % (CARRIED_WORKFLOW,
                    "matches" if got == live else "DIFFERS from",
                    LIVE_SHA[:12], CARRIED_WORKFLOW, len(got),
                    "" if pinned else " -- and it does NOT pin CHECKER_SHA, so "
                    "it would fetch the checker from origin/master at run time"))


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
    LEAK_SUFFIXES = (".py", ".md", ".yml", ".yaml", ".json", ".env", ".toml",
                     ".ini", ".cfg", ".sh", ".ps1", ".bat", ".pem", ".key")
    LEAK_ALLOWED = {CARRIED_WORKFLOW}
    leaked = sorted(r for r in second
                    if r.endswith(LEAK_SUFFIXES) and r not in LEAK_ALLOWED)
    check("no source or config files in dist/", not leaked,
          ", ".join(leaked[:4]))

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

    # 8. The form. Both directions, because "the good endpoint is present" and
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

    # 9. The CSP production serves today. master has no CSP at all, so a flip to
    #    master silently drops a header nobody would notice missing.
    hdr = os.path.join(DIST, "_headers")
    csp = ""
    if os.path.exists(hdr):
        with open(hdr, encoding="utf-8") as fh:
            for line in fh:
                if line.strip().lower().startswith("content-security-policy:"):
                    csp = line.split(":", 1)[1].strip()
    check("dist/_headers enforces a CSP", bool(csp), csp[:60])

    # 10. The whole point. Every URL a visitor can reach today must still resolve.
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
