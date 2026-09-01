# cochinwood.in — clean rebuild + Cloudflare Pages cutover plan

Migrating cochinwood.in off the Zoho Sites visual builder onto a **git-based
static site** that can be fully built, audited and managed from a diff.
Recurring cost **$0**.

**This is the strategy document — why the site is built this way and how it gets
published.** The night-of procedure, with numbered steps and a verification after
every step, is `CUTOVER-RUNBOOK.md`. If you are doing the cutover, go there.
If you are deciding something about how the cutover works, you are in the right place.

> **Status, 1 September 2026.** Phases 1–5 are done. Phase 6 is scheduled and the
> reviewed build is **`eaa832dafc84f87511c7c886e2c593016d9136d8`**. Later commits
> on the branch (this rewrite among them) are documentation and tooling only, and
> preflight proves that by rebuilding `eaa832da` and comparing all 289 files. The
> publishing *mechanism* was re-decided on 1 Sep after review — see
> [Phase 6](#phase-6--cloudflare-pages-cutover) and
> [Decision record](#decision-record--how-the-built-site-reaches-production). The
> deadline is not arbitrary: the CRM webform endpoint the old build posts to is
> **cancelled on 3 September**.

## Principles
- **Source → build → deploy.** Content + templates live in git; `build.py`
  renders `dist/`. No Zoho editor, no browser automation, every change is a diff.
- **No Node required.** Pure-Python SSG (`build.py`, stdlib only — verified: the
  single import line is `os, re, json, shutil, html, urllib.parse, datetime,
  struct, hashlib, sys`). Matches this machine, which has Python and not Node.
- **One source, two targets.** `SITE_BASE=""` builds for the domain root;
  `SITE_BASE=/cochinwood-web` builds the GitHub project-Pages preview. Same
  source, correct links either way.
- **SEO parity first.** URLs stay identical to the live site, so there is almost
  nothing to redirect; schema, sitemap, robots and `llms.txt` carry over. *Parity
  is a measured number, not an aspiration* — see below.
- **The build is deterministic, and that is load-bearing.** Two consecutive builds
  of the same commit must be byte-identical, or "verified once, published later"
  is not a claim anyone can make. Checked on every preflight.

## Branches / deploy

| Branch | What it is | Deployed |
|---|---|---|
| `master` | Source (`build.py`, `assets/`, `content/`). `dist/` is gitignored. **49 files behind the cutover work — see the warning below.** | no |
| `cutover-prep-2026-08-31` | The reviewed cutover work: build reviewed at `eaa832da`, plus later documentation/tooling commits that preflight proves change no output byte. **This is what gets published.** | preview only |
| `cf-live` | **Production.** Cloudflare Pages serves this branch **verbatim** at www.cochinwood.in — ~293 `.html` files, no build step. After Phase 6 it holds the built tree instead of hand-maintained files; it stays the production branch either way. | **yes** |
| `gh-pages` | Built preview (`SITE_BASE=/cochinwood-web`), GitHub Pages. | preview only |

> ### ⚠ `master` is not the cutover branch, and publishing it is a live incident
>
> This plan and the runbook both used to say the flip changes the production branch
> to `master`. Measured 1 Sep 2026:
>
> ```
> $ git merge-base origin/master origin/cutover-prep-2026-08-31
> 7dd9b5070d3a1266cc186cb240c3b620e1813ef3     # == master itself
> $ git diff --shortstat origin/master origin/cutover-prep-2026-08-31
>  49 files changed, 4826 insertions(+), 195 deletions(-)
> ```
>
> `master` is an **ancestor**, not a sibling. Publishing it would 404 **109 of the
> 293 live URLs**, restore the quote form posting to `crm.zoho.in`
> (`origin/master:build.py:534`) two days before that endpoint is cancelled, and
> drop the Content-Security-Policy (`git grep -c Content-Security-Policy
> origin/master` → zero hits in the whole tree).
>
> **Everything downstream now names a commit sha, never a branch**, and
> `tools/cutover_preflight.py` re-measures all three properties before anyone opens
> Cloudflare. Run against `master` it reports `184/293 covered`, one `crm.zoho.in`
> hit and no CSP, and exits 1.

## Phases

**Phase 1 — foundation & first pages ✅**
Python SSG, shared clean layout (sticky header nav, dark footer **with the Wood
Encyclopedia link**), brand tokens from `site.css` (greens, wood, Bree Serif/Poppins).
Rebuilt clean: Home, Products index, Contact. Wood Encyclopedia (hub + 15 species)
integrated with shared site chrome. Live preview on GitHub Pages.

**Phase 2 — remaining pages ✅**
13 product detail pages, Industries, Resources, About, FAQ, 4 policy pages,
rebuilt clean from the mirror; Zoho cruft dropped.

**Phase 3 — blog ✅** 156 posts as data + one post template; blog index, tags,
pagination, the city posts and guides.

**Phase 4 — forms & fonts ✅**
The quote form posts to **CWI's own Worker** at `https://www.cochinwood.in/web-lead`
(`webLead` in `cochin-wood-document-studio/webapp/api-worker.js`), gated by
Cloudflare Turnstile — `build.py:774`. Fonts self-hosted; Google/Zoho font CDNs
dropped.

> **The CRM webform endpoint must never come back.** `crm.zoho.in/crm/WebToLeadForm`
> is cancelled **3 September 2026**. A form posting there shows the buyer a success
> page while the enquiry reaches nobody — a silent failure on the revenue path, which
> is worse than an error page. Preflight checks **both** directions: `/web-lead`
> present *and* `crm.zoho.in` absent, because either alone can be true while the site
> is broken.

**Phase 5 — SEO parity ✅**
Org/LocalBusiness JSON-LD, per-page meta/canonical/OG, `sitemap.xml`, `robots.txt`,
`llms.txt`. Schema validation in `tools/check_site.py`.

Parity as measured on `eaa832da`, and re-measured unchanged on the current branch
tip, against the 293 URLs `cf-live` serves today:

```
233 built pages + 79 redirect rules  →  293 / 293 live URLs served or redirected
```

The 91-URL gap that was open on 26 Aug (202 pages against 293 URLs) is closed:
blog pagination and tag pages are built, and the five live category pages plus the
`/wood-encyclopedia/*` question are settled by redirect. `/woods-we-use` keeps its
URL. The `_redirects` file uses **79 of the 100 rules Pages honours**, against
`cf-live`'s current 99 — the cutover *buys back* 20 slots of headroom.

### Phase 6 — Cloudflare Pages cutover

**Publish the reviewed build `eaa832da` by pushing the locally built `dist/` as the contents of
`cf-live`. Change no Cloudflare setting.** Full procedure with per-step
verification: `CUTOVER-RUNBOOK.md`.

```
1. preflight  python tools/cutover_preflight.py eaa832da   → exit 0, 293/293
2. checker    (from inside dist/) python ../tools/check_site.py → exit 0
3. record     today's status codes + CSP header from the live domain
4. stage      direct-upload dist/ to the throwaway project cwi-redirect-lab
5. publish    push the built tree to cf-live         ← first step visitors see
6. purge      POST /zones/<zone>/purge_cache, then re-fetch WITHOUT ?cb=
7. resubmit   sitemap.xml in Search Console; request indexing on two moved URLs
rollback      Pages → Deployments → 52b41125-… → Rollback to this deployment
```

Two corrections to what this section used to say, both from 26 Aug and both
carried forward wrongly:

1. **There is no DNS step, and there is no Zoho origin.** Production has been the
   Cloudflare Pages project `cochinwood-web` serving `cf-live` verbatim for months.
   The cutover never touches DNS. Hunting for a DNS record during an incident costs
   time there is none of.
2. **`www.cochinwood.in` is the only custom domain on the Pages project.** Measured:
   `GET /accounts/<ACC>/pages/projects/cochinwood-web/domains` returns `www` and
   nothing else. The apex `cochinwood.in` is a **proxied A record to `192.0.2.1`**
   (an RFC 5737 documentation address — a placeholder carrying an edge redirect),
   and its 301 to `www` is **zone-level, independent of the Pages project**. So the
   apex is untouched by the cutover *and* by the rollback. Do not go looking for it
   in the Pages custom-domain list.

### Decision record — how the built site reaches production

Decided 1 Sep 2026, after review found that the previous answer had never been
tested. Recorded here so it is not silently re-litigated at 11pm.

**The question.** Cloudflare Pages can either build from source, or serve a branch
verbatim. Which one publishes `eaa832da`?

**The measurement that decided it.** A real deployment of this branch to the
production project:

```
https://adddbea8.cochinwood-web.pages.dev/           404
https://adddbea8.cochinwood-web.pages.dev/build.py   200
```

The project's `build_config` is `{"build_command": "", "destination_dir": "",
"root_dir": ""}` — all empty, **as it must be**, because `cf-live` is served
verbatim. A no-build project pointed at a **source** branch publishes the **source
tree**: the homepage 404s because `dist/` is gitignored and there is no root
`index.html`, and `build.py` is readable because it is a file in the document root.
**Cloudflare reported that deployment as a success.** A misconfigured deploy here
does not fail safely; it succeeds wrongly.

**And the build has never run there.** `GET .../deployments?per_page=25` → 25
deployments, every one triggered `github:push`, every one with `build_command: ""`.
The preview the owner inspected is `cochinwood-web-preview`, a **different project**
with `source: null` and an `ad_hoc` trigger — a direct upload that exercises no
Cloudflare build at all. Setting a build command at cutover would make the cutover
the first ever run of `python build.py` in Cloudflare's image.

| | **Path A — Cloudflare builds** | **Path B — push the built tree ✅ CHOSEN** |
|---|---|---|
| Settings changed at cutover | 3 (branch, build command, output dir) | **0** |
| Failure mode of one wrong field | homepage 404 + source served, reported as success | not reachable — no field to get wrong |
| Times this mechanism has published this site | **0** | every deployment for months |
| `build.py` proven in CF's build image | **no** | not needed |
| Python version | unpinned; verified `dist/` was built with **3.13.14**, CF's image differs | the exact bytes verified locally |
| `MIRROR_DIR` (`build.py:134`) points at sibling repo `../cochinwood-site` | **absent in the build image** — silently missing photos, not an error | irrelevant; build runs where the mirror is |
| Source files in the document root | `build.py`, `CUTOVER-*.md`, `tools/`, `content/` all served | **none** — `dist/` has no `.py` or `.md` at all |
| Redirect budget | n/a | 79/100, vs `cf-live`'s 99/100 today |
| Auto-rebuild on `git push` | **yes** — the real advantage | no; build locally, push the result |
| Rollback | change 3 settings back under pressure | one click to a retained deployment |

**Why Path B, in one sentence:** the cutover should change exactly one thing — the
bytes being served — and Path A changes the bytes *and* the publishing mechanism on
the same night, using a mechanism that has never once run.

**The honest cost of Path B.** No auto-rebuild: every content change needs a local
`python build.py` and a push of the built tree. And the cutover push is one commit
replacing ~293 hand-maintained files with 233 built pages — a diff nobody can review
line by line. That review is done instead by the 293/293 URL-coverage assertion in
preflight, which is the property that actually matters to a visitor.

**Path A is not rejected forever.** It is the better steady state and should be
adopted deliberately, on a quiet day, in this order: pin `PYTHON_VERSION`; remove or
default-guard the `MIRROR_DIR` fallback so the build cannot silently drop photos;
prove a green build on a throwaway Pages project; only then change the production
project's three fields, with the rollback deployment id written down first.

**Not attempted, on purpose:** no change was made to the production project, its
settings, its domains, or DNS while this decision was researched. Every Cloudflare
call was a `GET`, except a deploy-and-rollback pair on the throwaway project
`cwi-redirect-lab` that proved the rollback endpoint works.

## Two operational facts that have each cost a wrong answer once

**Publishing purges nothing.** A push to `cf-live` republishes the origin and leaves
the edge cache alone. Measured 28 Aug, two hours after a merge: `/` returned
`cf-cache-status: HIT, Age: 7148` — a pre-merge copy — while `/?cb=<rand>` returned
the correct document. Four independent readings agreed on the wrong answer because
all four were measuring the cache. **A cache-buster proves the origin is right and
proves nothing about what a visitor receives.** Purge the specific URLs, then
re-fetch *without* a buster. Step 6 of the runbook.

**A deployment's own URL is the only immutable reading.** The project alias
(`cochinwood-web.pages.dev`, and therefore `www`) does not switch to a new
deployment instantly — observed on the lab project after both a deploy and a
rollback. `https://<deployment-id>.<project>.pages.dev/` always serves exactly that
deployment. Verify there first; a cache-buster does not help, because the lag is in
which deployment the alias points at.

## Cost
$0 recurring (Cloudflare Pages free tier). One-time cost is build effort only.
Zoho One (CRM/Books) is unaffected — this is a capability upgrade, not a saving.
The one thing that *is* going away is the CRM **webform** endpoint on 3 September,
which Phase 4 already replaced with CWI's own Worker.
