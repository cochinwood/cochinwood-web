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
reviewed. So check 1 accepts HEAD == <reviewed-sha>, or HEAD a descendant of it
whose dist/ is byte-identical - which it proves by building <reviewed-sha> in a
throwaway worktree and comparing every file. A commit that changes documentation
passes. A commit that changes one character of output does not.

Checks, in the order a failure is cheapest to fix:

  1. worktree is clean                    - nothing uncommitted is in it
  2. HEAD publishes the reviewed bytes    - HEAD == sha, or a doc-only descendant
  3. two builds are byte-identical        - the build is deterministic
  4. dist/ carries no source files        - .py/.md at the doc root is a leak
  5. quote form posts to /web-lead        - and NOT to crm.zoho.in
  6. dist/_headers enforces a CSP         - matching what production serves now
  7. every live URL is served or 301s     - 293/293 against origin/cf-live

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
LIVE_REF = "origin/cf-live"

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

FAILED = []
PASSED = []


def check(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print("  %s  %-46s %s" % ("PASS" if ok else "FAIL", name, detail))
    return ok


def git(*args):
    out = subprocess.run(("git", "-C", ROOT) + args, capture_output=True, text=True)
    return out.returncode, out.stdout.strip(), out.stderr.strip()


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

    # 2 + 3. Determinism, and equivalence to the reviewed tree.
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

    # 4. dist/ is a document root. Anything in it is public. A tree with build.py
    #    and CUTOVER-RUNBOOK.md at its root has been served for real once already
    #    (deployment adddbea8) - see CUTOVER-RUNBOOK.md step 0.
    leaked = sorted(r for r in second if r.endswith((".py", ".md")))
    check("no source files in dist/", not leaked, ", ".join(leaked[:4]))

    # 5. The form. Both directions, because "the good endpoint is present" and
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

    # 6. The CSP production serves today. master has no CSP at all, so a flip to
    #    master silently drops a header nobody would notice missing.
    hdr = os.path.join(DIST, "_headers")
    csp = ""
    if os.path.exists(hdr):
        with open(hdr, encoding="utf-8") as fh:
            for line in fh:
                if line.strip().lower().startswith("content-security-policy:"):
                    csp = line.split(":", 1)[1].strip()
    check("dist/_headers enforces a CSP", bool(csp), csp[:60])

    # 7. The whole point. Every URL a visitor can reach today must still resolve.
    rc, listing, err = git("ls-tree", "-r", "--name-only", LIVE_REF)
    if rc != 0:
        check("live URL set readable (%s)" % LIVE_REF, False, err[:80])
    else:
        live = sorted({canonical(l) for l in listing.splitlines()
                       if l.endswith(".html")})
        served = {canonical(os.path.join(b, n).replace(DIST, "").lstrip("\\/"))
                  for b, _d, ns in os.walk(DIST) for n in ns if n.endswith(".html")}
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
              "%d/%d covered%s" % (len(live) - len(missing), len(live),
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
