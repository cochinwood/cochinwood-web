# Cloudflare Pages cutover — runbook

**What is being published:** the build reviewed as commit
**`8fc64aad5af0c66bae4c2b08d68ecde776f51dc9`** (`8fc64aad`) on `cutover-ready-2026-09-04`.
You will check out a *later* commit on that branch — this re-pin is one — and step 1 proves
it builds a `dist/` **byte-identical to `8fc64aad`'s across all 607 files** before you are
allowed to continue. The sha is the thing verified; the branch tip is merely where you find it.
**How it reaches production:** built locally into `dist/`, pushed as the **contents** of the
`cf-live` branch. **No Cloudflare setting is changed. There is no build command.**
**Rollback:** one click, restoring production deployment `52b41125-0e5e-4ecc-9fda-ba88974f85bd`.

Read step 0 before you open Cloudflare. If you are here during an incident, skip to
[Rollback](#rollback--verified-executable).

---

## Why the pin moved on 4 September 2026, and what a reviewer must check

The pin was `eaa832da` from 1 September until this commit. Moving it is **not** a
housekeeping bump, and the paragraph under step 1 says why: the sha names the tree that was
*reviewed*, so it may only move when a review has actually happened. One has. This section
records what it found and by what evidence, so the next reader can re-run it rather than take
it on trust.

**Five blockers were raised independently, then confirmed adversarially** — each one was
re-derived from the artifact rather than from the report that named it, and each was
reproduced as a mutation that a green preflight failed to catch. Four are fixed in `8fc64aad`;
the fifth is this document.

| # | What was wrong | What it would have cost | Now gated by |
|---|---|---|---|
| 1 | The coverage check compared only `.html`, on both sides | `293/293 covered` while **328 live URLs would 404** — 306 indexed and hotlinked photos under `/files/`, plus the root files | check 13, `620/620 covered, 27 reviewed-ignore`; every ignore carries a written reason |
| 2 | The runbook pinned a sha 13 commits behind, predating all of the above | The operator verifies a tree nobody reviewed, and the checks below it read as passing | this section, and step 1's re-pin at `8fc64aad` |
| 3 | The conversion beacon shipped on **0 of 253** pages | The dashboard reports **zero website conversions** — a *wrong* answer, not a missing one, and indistinguishable from the truth until someone compares it against WhatsApp | check 7, `253/253 pages, bytes match c59adae9ee7d`; `.gitattributes` pins `assets/cw-events.js` `-text` so `core.autocrlf=true` cannot rename its hashed URL |
| 4 | `_headers` claimed `max-age=31536000, immutable` on `/assets/*` and `/files/*` | **24 URLs whose names never change** pinned in visitors' browsers for a year; replace the hero photo after cutover and returning visitors keep the old one until September 2027 | only the three content-addressed names carry the year; the rest get a day, which is what `cf-live` serves today |
| 5 | `dist/` omitted `.github/workflows/site-checks.yml` | **The publishing push deletes the required check that gates it.** The check cannot run on the push that removed it, and every later publish repeats the removal in silence | check 8, byte-compared against the pinned live blob — *not* delegated to coverage, which is blind here because the `/.github/*` rule matches the URL whether or not the file exists |

**Three rounds of mutation testing were run against the gate itself**, because a check that
has never failed has not been tested. Rounds 1 and 2 killed plain deletion and same-length
corruption. The round-3 survivor is the one worth knowing about: it left all four carried root
files present **and byte-perfect** and hid the IndexNow key behind a wildcard — `/*.txt / 301`
in `PORTED_REDIRECTS` plus a `/*.txt` waiver in `build.py`'s `SHADOW_ALLOWED` — and the
preflight stayed at 12 passed / 1 failed, identical to control, with no build warning and
coverage still reading 620/620. `check_carried_root_files()` now matches `_redirects` sources
as **patterns** against those four paths and honours **no waiver list**, because for those four
being *served* is the requirement itself: IndexNow verifies ownership by fetching the exact key
path and comparing the body with the filename, so a 301 fails verification and every submission
to Bing, Yandex and Seznam stops while the site goes on looking fine.

**What a reviewer must check before authorising step 5.** Five things, in this order; the first
four are commands, and none of them touches production.

1. `python tools/cutover_preflight.py 8fc64aad` prints **`13 passed, 0 failed`** and
   `Preflight clean.`, and exits 0. Read the banner line under check 4: it is the build's own
   account of what it emitted, and it is the number every other claim here is checked against.
2. `git log --oneline 8fc64aad..HEAD` lists **only documentation commits**. If it lists a
   commit that touches `build.py`, the beacon, or anything else `dist/` is made of, then the
   sha above is stale again and this section has to be redone, not the sha alone.
3. The gate is being **carried**, not rewritten. This repo does not track the workflow at all;
   `build.py` reads it out of the pinned live commit, so compare the built copy with that blob
   directly and expect no output and exit 0:

   ```
   git cat-file -p c59adae9ee7d:.github/workflows/site-checks.yml \
     | cmp - dist/.github/workflows/site-checks.yml
   ```

   Do **not** substitute `git diff … -- .github/workflows/site-checks.yml`. It reports
   `1 file changed, 59 deletions(-)` here, which looks like the gate being removed and is
   nothing of the kind — the file is simply untracked on this branch and only ever exists in
   `dist/`.
4. From inside `dist/`, `python ../tools/check_site.py` exits 0 (step 2 below).
5. The rollback target is written down **before** anything moves:
   **`52b41125-0e5e-4ecc-9fda-ba88974f85bd`**, production, `cf-live` @ `c59adae9`, deployed
   2026-08-28T12:38:00Z. It exists, it is retained, and it is still what visitors are served
   right now — established when this runbook was written on 1 September and unchanged since,
   from the Pages deployments list. Nothing in this re-pin re-read Cloudflare; if the list has
   moved on, take the newest retained `cf-live` production deployment instead and record its
   id here before proceeding.

---

## Why this document was rewritten on 1 September 2026

Two faults were found by review and both are fixed below. They are recorded rather than
quietly corrected, because the second one is not intuitive and will be re-invented by the
next person who reads a Cloudflare settings page.

### Fault 1 — the flip step named the wrong branch

Step 5 used to say *"change the production branch to `master`"*. The reviewed,
preview-deployed work is not on `master`.

```
$ git merge-base origin/master origin/cutover-prep-2026-08-31
7dd9b5070d3a1266cc186cb240c3b620e1813ef3          # == master. master IS the merge base.

$ git diff --shortstat origin/master origin/cutover-prep-2026-08-31
 49 files changed, 4826 insertions(+), 195 deletions(-)
```

`master` is not a different line of work, it is **49 files behind**. Publishing it would have:

| consequence | measured how |
|---|---|
| **404s 109 of the 293 live URLs** — all blog pagination, the 5 category pages, 27 tag pages, the 9 `/export/*` market pages, `/woods-we-use`, both policy pages | `python tools/cutover_preflight.py 7dd9b507` on a `master` checkout → `184/293 covered` |
| **restores the quote form that posts to the CRM webform** — cancelled **3 September**, two days away. A buyer sees a success page; the enquiry reaches nobody. | `origin/master:build.py:534` → `action="https://crm.zoho.in/crm/WebToLeadForm"` vs `origin/cutover-prep-2026-08-31:build.py:774` → `action="https://www.cochinwood.in/web-lead"` |
| **drops the Content-Security-Policy** | `git grep -c Content-Security-Policy origin/master` → **0 hits anywhere in the tree**. Live today: `curl -sI https://www.cochinwood.in/` → `content-security-policy: base-uri 'self'; object-src 'none'; frame-ancestors 'self'`, which `origin/cutover-prep-2026-08-31:build.py:1850` reproduces verbatim. |

**A branch name cannot be verified. A sha that must reproduce a measured result can.** That is
why step 1 below is a script that names a sha and re-measures all three, and why it exits 1
rather than printing advice.

### Fault 2 — a misconfigured deploy does not fail, it succeeds wrongly

This was measured on a **real deployment of this branch to the production project**:

```
GET https://adddbea8.cochinwood-web.pages.dev/                        404
GET https://adddbea8.cochinwood-web.pages.dev/build.py                200
GET https://adddbea8.cochinwood-web.pages.dev/CUTOVER-RUNBOOK.md      200
GET https://adddbea8.cochinwood-web.pages.dev/CUTOVER-PLAN.md         200
GET https://adddbea8.cochinwood-web.pages.dev/tools/check_site.py     200
GET https://adddbea8.cochinwood-web.pages.dev/content/blog/posts.json 200
```

The homepage 404s and the source code is readable, and **Cloudflare reported that deployment
as a success.** The cause is structural, not a bug:

```
GET /accounts/<ACC>/pages/projects/cochinwood-web
  build_config: {"build_command": "", "destination_dir": "", "root_dir": "", ...}
```

The project has **no build command** — as it must not, because `cf-live` is served verbatim. A
project with no build command that is pointed at a **source** branch publishes the **source
tree**. `dist/` is `.gitignore`d, so the repo root has no `index.html`; it does have `build.py`.

The old step 5 listed the branch, the build command and the output directory in one sentence
with no check between them. Getting the branch right and any one of the other two wrong takes
the commercial front door down while the dashboard shows green. Below, **each field is its own
numbered step with its own verification** — and the recommended path changes **none of them**.

> This is not a hypothetical class of mistake in this repo. `cf-live` commit **`6bc28e5a`**,
> *"Stop serving the two files that describe how this site is built"*, exists because
> `/CLAUDE.md` and `/.github/workflows/site-checks.yml` were answering 200 on the live site. It
> spends 2 of the 100 redirect rules Pages honours to hide them.

### A third thing, established because it was being repeated without a source

**`python build.py` has never run in Cloudflare's build image.** Verified read-only:

```
GET /accounts/<ACC>/pages/projects/cochinwood-web/deployments?per_page=25
  → 25 deployments, ALL trigger github:push, ALL build_command ""   (0 of 25 non-empty)

GET /accounts/<ACC>/pages/projects/cochinwood-web-preview
  → source: null          ← no Git connection at all: direct upload
  → latest_deployment trigger: ad_hoc
```

The preview the owner inspected is **`cochinwood-web-preview`, a different project**, uploaded
directly. Nothing about it exercises a Cloudflare build. **If we set a build command at
cutover, the first time `build.py` ever runs in Cloudflare's image is the cutover itself.**

---

## The decision: two ways to publish `8fc64aad`

Both paths end with the same bytes in front of visitors. They differ in what has to go right.

### Path A — teach Cloudflare to build (rejected for this cutover)

Set production branch to a branch containing `8fc64aad`, build command `python build.py`,
output directory `dist`.

*For:* one source of truth; a `git push` rebuilds the site; no built artefacts in git.

*Against, and this is why it is rejected for **3 September**:*

1. **Three settings must be right simultaneously, and the failure mode is silent.** Fault 2
   above is exactly this path misconfigured by one field.
2. **The build has never run there.** First run would be the cutover.
3. **The Python version is unpinned and unknown.** The `dist/` verified below was produced by
   **Python 3.13.14**. Cloudflare's build image ships a different default; nothing in the repo
   pins `PYTHON_VERSION`.
4. **`build.py:134` reaches outside the repo.**
   `MIRROR_DIR = os.environ.get("MIRROR_DIR", os.path.join(os.path.dirname(ROOT), "cochinwood-site"))`
   — a **sibling checkout of a different repository**, used as a photo root at `build.py:135`.
   That directory will not exist in the build image. The reviewed tree happens not to need it
   (the verified build below ran with no such sibling present and emitted no photo warnings),
   but nothing enforces that, and the failure is a silently missing image rather than an error.

Path A is a reasonable destination. It is not something to attempt for the first time on the
night the commercial front door moves. Adopt it later, deliberately, after a build has actually
been proven green in Cloudflare's image on a throwaway project.

### Path B — push the built tree, change nothing in Cloudflare (**RECOMMENDED**)

Build `dist/` locally from the verified checkout, push its contents as `cf-live`. Production branch stays
`cf-live`. Build command stays empty. Output directory stays `/`.

*For:*

1. **Zero settings changed, so fault 2 is structurally impossible.** There is no build-command
   field to leave empty and no source branch to point at.
2. **It is the mechanism that has served 293 pages for months.** All 25 recent deployments are
   this mechanism; the 10 retained production deployments are all `cf-live` with an empty build
   command.
3. **The source-exposure class of bug disappears by construction.** `dist/` contains no `.py`
   and no `.md` at all (checked in preflight step 4). `cf-live` today needs two redirect rules
   to hide `CLAUDE.md` and `.github/`; the built tree needs none.
4. **Redirect headroom improves.** `cf-live` sits at 99 of the 100 rules Pages honours. The
   built `_redirects` carries **108 rules, and only 79 of them are counted** — measured on
   `cwi-redirect-lab`, rules written *above* the first wildcard are not charged against the
   100 (Cloudflare documents 2,000 static), and from the first wildcard onward exactly 100
   further rules are honoured. The build banner states the split: `redirects:108 (29
   static/2000 + 79 from first wildcard/100)`. That leaves **21 slots**, and ordering is a
   budget decision as well as a precedence one: a static rule moved above the first wildcard
   costs nothing.
5. **Rollback is a click, and it is verified below.**

*Against, stated honestly:*

- **No auto-rebuild.** Every future content change needs a local `python build.py` and a push
  of the built tree. This is the status quo and the team already works this way.
- **One enormous commit.** ~293 hand-maintained files are replaced by a 607-file built tree —
  253 pages, 108 redirect rules, and 311 files carried verbatim out of
  `origin/cf-live@c59adae9ee7d` — in a single push. That diff cannot be reviewed file by file.
  It is reviewed instead by the `620/620 covered` URL-coverage check in step 1, which is the
  property that actually matters.
- **`cf-live` is branch-protected** — the `The site says one thing` check must pass before a
  commit lands. That is a feature; budget for it rather than bypassing it.

**Take Path B on 3 September.** The rest of this runbook is Path B. Path A's settings are
recorded in `CUTOVER-PLAN.md` for whenever it is adopted on purpose.

---

## Step 0 — before you open Cloudflare

- [ ] You have a terminal with Python and a clean checkout. You have **not** opened the
      Cloudflare dashboard yet.
- [ ] Write down the rollback target now, before anything changes:
      **`52b41125-0e5e-4ecc-9fda-ba88974f85bd`** — production, `cf-live` @ `c59adae9`,
      deployed 2026-08-28T12:38:00Z. It is retained and it is the last thing visitors saw.
- [ ] Understand that **nothing you do in steps 1–4 touches production.** The first step that
      changes what a visitor receives is step 5, and it says so.

---

## Step 1 — verify the tree, before touching anything

One action. Run this and read the last line.

```
git fetch origin
git checkout cutover-ready-2026-09-04
MIRROR_DIR="C:/Users/Edwin David/cochinwood-site" python tools/cutover_preflight.py 8fc64aad
```

`MIRROR_DIR` is the sibling checkout of the photo repo that `build.py:134` resolves from the
parent of this checkout. Set it explicitly if your checkout does not sit beside
`cochinwood-site`; the build does not fail without it, it silently emits fewer images, which is
the kind of difference this step exists to make impossible.

**Verification:** the script must print `Preflight clean.` and **exit 0**. Pasted output,
4 Sep 2026 — `13 passed, 0 failed`:

```
  PASS  worktree is clean
  PASS  live pin is origin/cf-live's tip               pin c59adae9ee7d, tip c59adae9ee7d
  PASS  build exits 0, twice                           exit 0 / 0
  PASS  two builds byte-identical                      607 files
       banner: BUILD OK  base='(root)'  34 content pages + 29 wood pages + 29 export pages + 156 blog posts + 18 images + 311 carried from origin/cf-live@c59adae9ee7d  sitemap:252(96cms+156post)  redirects:108 (29 static/2000 + 79 from first wildcard/100)  files: 607
  PASS  HEAD publishes the reviewed bytes              HEAD=<yours> is a descendant of 8fc64aad; dist/ byte-identical (607 files)
  PASS  no source or config files in dist/
  PASS  conversion beacon ships on every page          dist/assets/cw-events.853632c8.js on 253/253 pages, bytes match c59adae9ee7d:js/cw-events.js
  PASS  required-check workflow ships in dist/         dist/.github/workflows/site-checks.yml matches c59adae9ee7d:.github/workflows/site-checks.yml (2933 bytes), pins CHECKER_SHA=4678a8f5
  PASS  carried root files ship verbatim               4 files, bytes match c59adae9ee7d
  PASS  quote form posts to /web-lead                  1 page(s)
  PASS  no page posts to crm.zoho.in                   0 hit(s)
  PASS  dist/_headers enforces a CSP                   base-uri 'self'; object-src 'none'; frame-ancestors 'self'
  PASS  every live URL served or redirected            620/620 covered, 27 reviewed-ignore
13 passed, 0 failed
```

**If any line says FAIL, stop. Do not open Cloudflare.** The script exits 1 and names what
failed. It is deliberately the same script that, run against `master`, reported `184/293
covered`, `1 hit(s)` on `crm.zoho.in` and an empty CSP on 1 Sep 2026 — i.e. it is known to
catch the exact mistake this runbook was rewritten to prevent. (That reading is the 1 September
one and has not been re-taken: the coverage check no longer compares only `.html`, so its
denominator on any tree is now 620 rather than 293. The point it makes — that this script fails
loudly on the wrong tree — is unchanged; the two numbers are simply not on the same scale.)

> **A sha, not a branch — and why the argument is not `HEAD`.** A document cannot name the
> commit that contains it: pinning "publish exactly this sha" breaks the moment anyone edits
> this runbook. So the argument is the **reviewed** sha, and the check is the property that
> actually matters — *the tree you are about to publish builds the same bytes as the tree that
> was reviewed*. The script accepts `HEAD == 8fc64aad`, or `HEAD` a descendant of it, which it
> then **proves** by checking out `8fc64aad` into a throwaway worktree, building it, and
> comparing every file. A documentation commit passes. A commit that changes one character of
> output fails and names the files. If review lands new *content*, that content must be
> reviewed and the sha in this step updated to the new reviewed commit.

---

## Step 2 — run the site checker against the built tree

One action. It runs **from inside `dist/`**.

```
cd dist
python ../tools/check_site.py
cd ..
```

**Verification:** last line reads
`OK - the site says one thing, and every link goes somewhere.` and it **exits 0**.
Expected shape, pasted from the run on `8fc64aad`'s `dist/` (4 Sep 2026):

```
pages          : 253
ld+json blocks : 781
export-market  : 1 pages carry the FAQ
cache rules    : 11 set Cache-Control
internal links : 10660
faq answers    : 320 checked against the page that asks the question
  reworded     : 50 say it in different words (counted, not failed)
  orphaned     : 4 questions with no visible heading (counted, not failed)
self-reference : 252 pages checked for canonical, og:url and title

OK - the site says one thing, and every link goes somewhere.
```

`pages : 253` and `self-reference : 252` differ by one on purpose, and it is not drift:
`tools/check_site.py:520` skips `404.html` because `_redirects` sends `/404` home, so it has no
address of its own to be canonical to.

If it exits non-zero, stop. Nothing has changed yet; you have lost nothing.

---

## Step 3 — record what production serves right now

One action. This is the "before" you will compare against, and the evidence that rollback
worked if you need it.

```
curl -sI "https://www.cochinwood.in/" | tr -d '\r' | grep -i "content-security-policy\|^HTTP"
curl -s -o /dev/null -w "%{http_code} /\n"              "https://www.cochinwood.in/"
curl -s -o /dev/null -w "%{http_code} /woods-we-use\n"  "https://www.cochinwood.in/woods-we-use"
curl -s -o /dev/null -w "%{http_code} /blogs/page/10\n" "https://www.cochinwood.in/blogs/page/10"
curl -s -o /dev/null -w "%{http_code} /build.py\n"      "https://www.cochinwood.in/build.py"
```

**Verification — record these, they are today's readings (measured 1 Sep 2026):**

```
200 /                200 /woods-we-use     200 /blogs/page/10     404 /build.py
content-security-policy: base-uri 'self'; object-src 'none'; frame-ancestors 'self'
```

`/woods-we-use` and `/blogs/page/10` are in the 109 that a `master` publish would 404, so they
are the two cheapest canaries you have. `/build.py` must be 404 **before and after**.

---

## Step 4 — stage the built tree on the throwaway lab project

One action. **Not** production, **not** `cochinwood-web-preview` (the owner is reviewing that
one). The lab project is `cwi-redirect-lab`.

Copy the direct-upload script, point `DIST` at your `dist/`, run it. The script refuses
`cochinwood-web` and `cochinwood-web-preview` by name.

**Verification:** against the deployment URL it prints, not the project alias:

```
curl -s -o /dev/null -w "%{http_code}\n" https://<id>.cwi-redirect-lab.pages.dev/            → 200
curl -s -o /dev/null -w "%{http_code}\n" https://<id>.cwi-redirect-lab.pages.dev/build.py    → 404
curl -sI https://<id>.cwi-redirect-lab.pages.dev/ | grep -i content-security-policy          → present
```

A **200 on `/` and a 404 on `/build.py`** is the pair that distinguishes a correct publish from
fault 2. Check both, in that order, every time.

> **Use the per-deployment URL, never the project alias.** Measured on `cwi-redirect-lab`:
> after a new deployment, and again after a rollback, the project alias kept serving the
> *previous* version for a while. `https://<id>.<project>.pages.dev/` is immutable and always
> serves exactly that deployment. A cache-busting query does **not** help here — the lag is in
> which deployment the alias points at, not in the HTTP cache.

---

## Step 5 — publish. THIS CHANGES WHAT VISITORS SEE.

One action: push the built tree as the contents of `cf-live`. Pages deploys the moment
`cf-live` moves; the push **is** the deploy.

```
# 1. Move dist/ OUT of the checkout first. cf-live has no .gitignore of its own,
#    so a dist/ sitting inside the checkout is swept up by `git add -A` below and
#    published at /dist/*. That has happened for real - the `/dist/* / 301` rule
#    in _redirects is the scar left by it.
mv dist ../cwi-cutover-dist

# 2. Land on the branch Pages deploys, and write down where to roll back to.
git checkout cf-live && git pull --ff-only
git rev-parse HEAD                    # record this - it is your git-side rollback point

# 3. Replace the tracked tree with dist/, keeping .git. Three commands, this order.
git rm -r --quiet -f .                # every tracked file, index and worktree; .git untouched
git clean -qfdx                       # untracked leftovers: cf-live has no .gitignore, so a
                                      # stray __pycache__/ WILL be committed otherwise (measured)
cp -a ../cwi-cutover-dist/. .         # the trailing "/." is what carries the dot-paths

# 4. Look before you commit. All three must hold.
git ls-files | wc -l                                            # 607 - the build banner's "files:" count
test -f .github/workflows/site-checks.yml && echo "gate carried"
test -f .nojekyll && echo "nojekyll carried"

git add -A && git commit -m "Publish the reviewed build (8fc64aad) as the served tree"
git push origin cf-live
```

> **`cp -r dist/* .` is the wrong command, and it fails silently.** A shell glob never matches a
> leading dot, so it copies **605 of dist/'s 607 files** (measured 4 Sep 2026 against this build)
> and drops exactly the two the cutover depends on:
>
> - `.github/workflows/site-checks.yml` — without it this very push **deletes** cf-live's required
>   check `The site says one thing`. The check cannot run on the push that removed it, every later
>   publish repeats the removal, and nothing anywhere reports that the gate has gone.
> - `.nojekyll` — committed on cf-live and served today (`/.nojekyll` answers **200**, probed
>   4 Sep 2026). It is what keeps the underscore-prefixed paths — `_headers` and `_redirects`,
>   i.e. the CSP and all 108 redirect rules — from being dropped on the GitHub Pages deploy path
>   this repo also builds for. Dropping a file the reviewed dist/ contains is a difference the
>   preflight has already signed off on and cannot re-check after the copy.
>
> `cp -a dist/. .` copies all 607, dot-entries included; `git ls-files | wc -l` reading 607 after
> step 4 is the proof, and it is the number to check rather than the copy's own silence.
>
> **This sequence was run, not reasoned about (4 Sep 2026).** A throwaway `git clone --no-local`
> of `cf-live`, `git rm -r -f .`, `git clean -qfdx`, `cp -a ../cwi-cutover-dist/. .`,
> `git add -A`:
>
> ```
> $ git ls-files | wc -l
> 607
> $ test -f .github/workflows/site-checks.yml && echo "gate carried"
> gate carried
> $ test -f .nojekyll && echo "nojekyll carried"
> nojekyll carried
>
> $ cp -r ../cwi-cutover-dist/* .   # the wrong command, same dist/, empty directory
> $ find . -type f | wc -l
> 605
> ```
>
> Nothing was pushed and the clone was deleted. `git add -A` also prints a wall of
> `LF will be replaced by CRLF` warnings on a `core.autocrlf=true` machine; they are not a
> problem here — the index keeps LF, which is what Pages serves, and
> `git cat-file -p :_redirects | wc -c` matches `wc -c < _redirects` at 12,122 bytes. Do not
> "fix" them by adding a `.gitattributes` to `cf-live`: `dist/` does not contain one, so it
> would be deleted by the next publish anyway.

`cf-live` requires the `The site says one thing` check to pass. Let it run. **Do not bypass it**
— the admin bypass exists so a broken checker cannot stop a *rollback*, not so it can wave a
deploy through.

**Verification, in this order — do not skip to the domain:**

1. Find the new **production** deployment id in Workers & Pages → `cochinwood-web` →
   Deployments. Record it.
2. Check the immutable per-deployment URL first:
   ```
   curl -s -o /dev/null -w "%{http_code}\n" https://<newid>.cochinwood-web.pages.dev/         → 200
   curl -s -o /dev/null -w "%{http_code}\n" https://<newid>.cochinwood-web.pages.dev/build.py → 404
   ```
   **If `/` is 404 or `/build.py` is 200, go straight to Rollback.** Do not investigate first.
3. Only then the real domain:
   ```
   curl -s -o /dev/null -w "%{http_code} /\n"             "https://www.cochinwood.in/?cb=$RANDOM"
   curl -s -o /dev/null -w "%{http_code} /woods-we-use\n" "https://www.cochinwood.in/woods-we-use?cb=$RANDOM"
   curl -s -o /dev/null -w "%{http_code} /blogs/page/10\n" "https://www.cochinwood.in/blogs/page/10?cb=$RANDOM"
   curl -sI "https://www.cochinwood.in/?cb=$RANDOM" | grep -i content-security-policy
   ```
   Expect `200 200 200` and the CSP present. The `?cb=` here is correct and deliberate: at this
   moment you are asking *what does the origin serve*. Step 6 asks the different question.

---

## Step 6 — purge the edge cache. Not optional.

**A push republishes the origin and purges nothing.** This repo has been caught by that twice.
Recorded on `cf-live` in `CLAUDE.md` and in commit `868d1a8d`: two hours after a merge,

```
https://www.cochinwood.in/            cf-cache-status: HIT   Age: 7148   (pre-merge copy)
https://www.cochinwood.in/?cb=<rand>  cf-cache-status: MISS              (correct)
```

That instance served a homepage missing `js/cw-events.js`, so the dashboard reported the
homepage producing zero quote clicks — **a wrong answer rather than a missing one**, corroborated
by four readings that were all measuring the cache.

One action — purge the specific URLs, not the zone:

```
POST https://api.cloudflare.com/client/v4/zones/345c58017e72448c9342c66fa525bbfa/purge_cache
{"files": ["https://www.cochinwood.in/",
           "https://www.cochinwood.in/contact",
           "https://www.cochinwood.in/sitemap.xml",
           "https://www.cochinwood.in/robots.txt",
           "https://www.cochinwood.in/woods-we-use"]}
```

Zone `cochinwood.in` = `345c58017e72448c9342c66fa525bbfa`. Purge specific URLs: a full purge
sends every page to the origin at once for no benefit.

**Verification — re-fetch WITHOUT a cache-buster.** This is the opposite of step 5 and the
distinction is the whole point:

```
curl -sI "https://www.cochinwood.in/" | grep -i "cf-cache-status\|age:"
```

Expect `cf-cache-status: MISS` (or a `HIT` with a very small `Age`). **A cache-buster proves the
origin is right and proves nothing about what a visitor receives.** A visitor does not send
`?cb=`.

> One reading trap, already paid for once: `/index.html` answers `BYPASS` with an empty body —
> that is a 308 to `/`, not a document. Probe the URL a visitor actually requests.

---

## Step 7 — resubmit the sitemaps in Search Console

The sitemap changed shape: **252 entries (96 CMS + 156 posts)**, and 108 redirect rules now
carry old URLs to new ones. Google will re-crawl on its own schedule; resubmission makes it
days instead of weeks, and the 109-URL question is exactly the one you want answered early.

`/sitemap.xml` is a **sitemap index**, not a list of pages — it holds two `<loc>` entries
pointing at `/sitemap-cms.xml` (96) and `/sitemap-post.xml` (156). Submit the index; Search
Console follows it and reports the children separately.

One action, in Google Search Console for `cochinwood.in`:

1. **Sitemaps** → remove the old `sitemap.xml` entry if present → **Add** `sitemap.xml` →
   Submit.
2. **URL Inspection** → `https://www.cochinwood.in/woods-we-use` → **Request indexing**.
   Repeat for `https://www.cochinwood.in/blogs/page/2`.

**Verification:** Sitemaps page shows status **Success** for the index and for both children,
and a discovered-URL count of **252** across them (96 + 156) — not 0, and not 293. If it reads
0 or "Couldn't fetch", re-check that `https://www.cochinwood.in/sitemap.xml`,
`/sitemap-cms.xml` and `/sitemap-post.xml` all return 200 — that is a cutover problem, not a
Google problem.

Then, over the following week, watch **Pages → Not indexed → Not found (404)**. A rise toward
~109 means something in the redirect set did not ship. It will not spike on day one.

---

## Rollback — verified executable

Use this the moment step 5's verification fails. Do not investigate first; roll back, then
investigate against the per-deployment URL, which stays alive.

### Primary — roll back the Pages deployment (seconds, no settings, no rebuild)

Workers & Pages → `cochinwood-web` → **Deployments** → production deployment
**`52b41125-0e5e-4ecc-9fda-ba88974f85bd`** (`cf-live` @ `c59adae9`, 2026-08-28T12:38:00Z) →
**⋯ → Rollback to this deployment**.

Equivalently, and this is the call the dashboard makes:

```
POST /accounts/<ACC>/pages/projects/cochinwood-web/deployments/52b41125-0e5e-4ecc-9fda-ba88974f85bd/rollback
```

**This was tested, not assumed.** On the throwaway project `cwi-redirect-lab`: deployed
version A, deployed version B, confirmed the alias served B's content, issued the rollback POST
to A's deployment id → `HTTP 200 success=True`, and the project alias returned
`VERSION-A-GOOD` while B's own per-deployment URL still served `VERSION-B-BAD`. The endpoint
does what it says.

Nine older `cf-live` production deployments are retained behind that one if it is somehow bad.

**Verification of the rollback:**

```
curl -s -o /dev/null -w "%{http_code} /\n"         "https://www.cochinwood.in/?cb=$RANDOM"
curl -s -o /dev/null -w "%{http_code} /build.py\n" "https://www.cochinwood.in/build.py"
curl -sI "https://www.cochinwood.in/?cb=$RANDOM" | grep -i content-security-policy
```

Must match step 3's recorded readings: `200 /`, `404 /build.py`, CSP present. **Then purge**
(step 6) — the rollback republishes the origin and, exactly like the deploy, purges nothing.

**Expect a lag on the alias.** Measured on the lab project: after a rollback the alias briefly
kept serving the newer version. If the first reading is wrong, check
`https://52b41125.cochinwood-web.pages.dev/` — if *that* is correct, the rollback worked and
the alias is catching up. Do not stack a second corrective action on top of a lag.

### Secondary — git-side, if the Pages rollback is unavailable

```
git push --force-with-lease origin <sha recorded in step 5>:cf-live
```

Then purge (step 6). Slower — it re-triggers the branch check — but it restores the same bytes.

### Things that are NOT the rollback

- **Do not remove the custom domain.** That takes the site offline. It does not fall back to
  anything; there is no Zoho origin and no other host.
- **Do not touch DNS.** No step in this runbook changes DNS, including the rollback.
- **Do not change the production branch or the build command.** On Path B they were never
  changed, so changing them during an incident can only make things worse.

---

## Correction: the apex is *not* a custom domain on the Pages project

Earlier versions of this file stated that `cochinwood.in` **and** `www.cochinwood.in` are both
custom domains on `cochinwood-web`. Measured:

```
GET /accounts/<ACC>/pages/projects/cochinwood-web/domains
  → www.cochinwood.in   status=active        ← the only one

DNS, zone cochinwood.in:
  CNAME  www.cochinwood.in  → cochinwood-web.pages.dev   proxied=true
  A      cochinwood.in      → 192.0.2.1                  proxied=true
```

`192.0.2.1` is an RFC 5737 documentation address — a placeholder that exists so a proxied
record can carry an edge redirect. `https://cochinwood.in/` does 301 to
`https://www.cochinwood.in/`, but that redirect is **zone-level and independent of the Pages
project**.

**What this means operationally:** the apex is unaffected by everything in this runbook,
including the rollback — which is good news, but do not go looking for `cochinwood.in` in the
Pages custom-domains list during an incident. It is not there, and it is not missing.

*(I could not read the rule that performs the apex redirect:
`GET /zones/<zone>/rulesets?phase=http_request_dynamic_redirect` returned **403** with the token
available here. The redirect is confirmed working by request; the mechanism behind it is
inferred from the placeholder A record, not read. If you need to change apex behaviour, find
the rule first.)*

---

## What is verified, and what is not

**Verified by measurement for the 4 Sep 2026 re-pin at `8fc64aad`:**

- Build determinism: two consecutive builds, **607 files**, byte-identical; `13 passed,
  0 failed`; coverage `620/620 covered, 27 reviewed-ignore`; beacon on `253/253` pages; the
  four carried root files byte-equal to `c59adae9ee7d`.
- `python build.py` exit 0; `tools/check_site.py` from inside `dist/` exit 0 at `pages : 253`,
  `internal links : 10660`.
- **The step 5 copy sequence, run end to end in a throwaway clone of `cf-live`.**
  `git rm -r -f .` → `git clean -qfdx` → `cp -a ../cwi-cutover-dist/. .` → `git add -A` gives
  `git ls-files | wc -l` = **607**, with `.github/workflows/site-checks.yml` and `.nojekyll`
  both present. The same dist/ through `cp -r dist/* .` gives **605** and neither of those two.
  Nothing was pushed; the clone was deleted.
- **The gate itself, by mutation.** Deleting a carried root file, corrupting one at the same
  length, and shadowing one behind a wildcard 301 with a `SHADOW_ALLOWED` waiver each now fail
  the preflight by name. The third of those passed at 12/1 before this commit.

**Verified by measurement for the 1 Sep 2026 rewrite, and not re-taken:**

- Branch divergence, the 109 404s, the form endpoint, the missing CSP — all four re-measured,
  all four now gated by `tools/cutover_preflight.py`. The `184/293` figure is on the old
  `.html`-only denominator; see the note under step 1.
- 0 of 25 recent deployments carry a build command; `cochinwood-web-preview` has `source: null`
  and an `ad_hoc` trigger.
- Source-tree exposure on deployment `adddbea8`, six URLs, status codes above.
- The rollback endpoint, end to end, on a throwaway project.

**Not verified, and deliberately not attempted:**

- **No change was made to the production project, its settings, its domains, or DNS.** Every
  Cloudflare call made while writing this was a `GET`, except the deploy/rollback pair on the
  throwaway `cwi-redirect-lab`.
- Path A has not been proven. Nobody has run `build.py` in Cloudflare's build image. If Path A
  is ever adopted, prove it on a throwaway project first — and pin `PYTHON_VERSION`.
- The apex redirect rule itself (403, above).

## Who does what

- **Can be done without the owner:** everything through step 4 — build, both verifications,
  the lab staging, and the cache purge in step 6.
- **Owner authorises:** the step 5 push to `cf-live`, and the Search Console actions in step 7.
- **Nobody changes:** the Pages production branch, the build command, the output directory,
  the custom domains, or DNS. Path B changes none of them, and that is the point.
