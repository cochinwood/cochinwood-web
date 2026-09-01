# Cloudflare Pages cutover — runbook

**What is being published:** the build reviewed as commit
**`eaa832dafc84f87511c7c886e2c593016d9136d8`** (`eaa832da`) on `cutover-prep-2026-08-31`.
You will check out a *later* commit on that branch — this rewrite is one — and step 1 proves
it builds a `dist/` **byte-identical to `eaa832da`'s across all 289 files** before you are
allowed to continue. The sha is the thing verified; the branch tip is merely where you find it.
**How it reaches production:** built locally into `dist/`, pushed as the **contents** of the
`cf-live` branch. **No Cloudflare setting is changed. There is no build command.**
**Rollback:** one click, restoring production deployment `52b41125-0e5e-4ecc-9fda-ba88974f85bd`.

Read step 0 before you open Cloudflare. If you are here during an incident, skip to
[Rollback](#rollback--verified-executable).

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

## The decision: two ways to publish `eaa832da`

Both paths end with the same bytes in front of visitors. They differ in what has to go right.

### Path A — teach Cloudflare to build (rejected for this cutover)

Set production branch to a branch containing `eaa832da`, build command `python build.py`,
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
   built `_redirects` is **79**, leaving 21 slots.
5. **Rollback is a click, and it is verified below.**

*Against, stated honestly:*

- **No auto-rebuild.** Every future content change needs a local `python build.py` and a push
  of the built tree. This is the status quo and the team already works this way.
- **One enormous commit.** ~293 hand-maintained files are replaced by 233 built pages plus 79
  redirect rules in a single push. That diff cannot be reviewed file by file. It is reviewed
  instead by the 293/293 URL-coverage check in step 1, which is the property that actually
  matters.
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
git checkout cutover-prep-2026-08-31
python tools/cutover_preflight.py eaa832da
```

**Verification:** the script must print `Preflight clean.` and **exit 0**. Measured output on
1 Sep 2026 — `9 passed, 0 failed`:

```
  PASS  worktree is clean
  PASS  build exits 0, twice                           exit 0 / 0
  PASS  two builds byte-identical                      289 files
       banner: BUILD OK  base='(root)'  34 content pages + 29 wood pages + 9 export pages +
               156 blog posts + 18 images  sitemap:232(76cms+156post)  redirects:79/100  files: 289
  PASS  HEAD publishes the reviewed bytes              HEAD=<yours> is a descendant of eaa832da; dist/ byte-identical (289 files)
  PASS  no source files in dist/
  PASS  quote form posts to /web-lead                  1 page(s)
  PASS  no page posts to crm.zoho.in                   0 hit(s)
  PASS  dist/_headers enforces a CSP                   base-uri 'self'; object-src 'none'; frame-ancestors 'self'
  PASS  every live URL served or redirected            293/293 covered
```

**If any line says FAIL, stop. Do not open Cloudflare.** The script exits 1 and names what
failed. It is deliberately the same script that, run against `master`, reports
`184/293 covered`, `1 hit(s)` on `crm.zoho.in` and an empty CSP — i.e. it is known to catch the
exact mistake this runbook was rewritten to prevent.

> **A sha, not a branch — and why the argument is not `HEAD`.** A document cannot name the
> commit that contains it: pinning "publish exactly this sha" breaks the moment anyone edits
> this runbook. So the argument is the **reviewed** sha, and the check is the property that
> actually matters — *the tree you are about to publish builds the same bytes as the tree that
> was reviewed*. The script accepts `HEAD == eaa832da`, or `HEAD` a descendant of it, which it
> then **proves** by checking out `eaa832da` into a throwaway worktree, building it, and
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
Expected shape: `pages : 233`, `internal links : 9279`, `self-reference : 232 pages checked`.

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
git checkout cf-live && git pull --ff-only
git rev-parse HEAD                    # record this - it is your git-side rollback point
# replace the tracked tree with dist/, keeping .git, then:
git add -A && git commit -m "Publish the reviewed build (eaa832da) as the served tree"
git push origin cf-live
```

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

The sitemap changed shape: **232 entries (76 CMS + 156 posts)**, and 79 redirect rules now
carry old URLs to new ones. Google will re-crawl on its own schedule; resubmission makes it
days instead of weeks, and the 109-URL question is exactly the one you want answered early.

One action, in Google Search Console for `cochinwood.in`:

1. **Sitemaps** → remove the old `sitemap.xml` entry if present → **Add** `sitemap.xml` →
   Submit.
2. **URL Inspection** → `https://www.cochinwood.in/woods-we-use` → **Request indexing**.
   Repeat for `https://www.cochinwood.in/blogs/page/2`.

**Verification:** Sitemaps page shows status **Success** and a discovered-URL count in the
low 200s (not 0, not 293). If it reads 0 or "Couldn't fetch", re-check
`https://www.cochinwood.in/sitemap.xml` returns 200 — that is a cutover problem, not a Google
problem.

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

**Verified by measurement for this document (1 Sep 2026):**

- Branch divergence, the 109 404s, the form endpoint, the missing CSP — all four re-measured,
  all four now gated by `tools/cutover_preflight.py`.
- Build determinism: two consecutive builds, 289 files, byte-identical; and this rewrite's
  `dist/` is byte-identical to the reviewed `eaa832da`'s across all 289 files.
- `python build.py` exit 0; `tools/check_site.py` from inside `dist/` exit 0.
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
