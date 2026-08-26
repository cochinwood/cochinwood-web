# cochinwood.in — clean rebuild + Cloudflare Pages cutover plan

Migrating cochinwood.in off the Zoho Sites visual builder onto a **git-based
static site** that Claude can fully build, audit and manage. Recurring cost **$0**.

## Principles
- **Source → build → deploy.** Content + templates live in git; `build.py`
  renders `dist/`. No Zoho editor, no browser automation, every change is a diff.
- **No Node required.** Pure-Python SSG (`build.py`) — matches this machine
  (Python only). Cloudflare Pages / GitHub Pages run it with zero extra tooling.
- **One source, two targets.** `SITE_BASE=""` builds for the domain root
  (Cloudflare Pages @ cochinwood.in); `SITE_BASE=/cochinwood-web` builds the
  GitHub project-Pages preview. Same source, correct links either way.
- **SEO parity first.** URLs stay identical to the live site, so there's almost
  nothing to redirect; schema, sitemap, robots and `llms.txt` carry over.

## Branches / deploy
- `master` — source (`build.py`, `assets/`, `content/`). `dist/` is gitignored.
  **Not deployed.**
- `gh-pages` — built preview (`SITE_BASE=/cochinwood-web`). GitHub Pages serves it.
- `cf-live` — **production today.** Cloudflare Pages serves this branch verbatim at
  cochinwood.in: ~293 hand-maintained `.html` files, no build step. It is the static
  mirror of the old Zoho site plus every fix since. Until Phase 6 below is done, this
  is the only branch a visitor ever sees.
- **Production after cutover (target state, NOT yet live)** — Cloudflare Pages will
  build `python build.py` (SITE_BASE unset) and serve `dist/` at cochinwood.in.
  Private repo is fine there. Phase 6 is what flips production from `cf-live` to
  this build; nothing on `master` reaches users before that.

## Phases
**Phase 1 — foundation & first pages ✅ (this build)**
- Python SSG, shared clean layout (sticky header nav, dark footer **with the Wood
  Encyclopedia link**), brand tokens from `site.css` (greens, wood, Bree Serif/Poppins).
- Rebuilt clean: **Home, Products index, Contact.**
- **Wood Encyclopedia** (hub + 15 species) integrated with shared site chrome.
- Live preview on GitHub Pages.

**Phase 2 — remaining pages** (13 product detail pages, Industries, Resources,
About, FAQ, 4 policy pages). Rebuild clean from the mirror content; drop Zoho cruft.

**Phase 3 — blog (156 posts)** Convert each post to a Markdown/data file + one
post template; build blog index, tags, and the 100 city posts + guides. Content
already exists (much of it authored here) — this is mechanical.

**Phase 4 — forms & fonts** Wire the contact/quote form to the existing Zoho CRM
webform endpoint via a **Cloudflare Worker** (keeps leads flowing to CRM, $0).
Self-host Bree Serif + Poppins (drop the Google/Zoho font CDNs) for speed + privacy.

**Phase 5 — SEO parity** Org/LocalBusiness JSON-LD, per-page meta/canonical/OG,
`sitemap.xml`, `robots.txt`, `llms.txt`; redirect map for any slug that changed
(currently ~none — paths are 1:1). Lighthouse + schema validation in the build.

**Phase 6 — Cloudflare Pages cutover**

> Corrected 2026-08-26. The steps below used to describe flipping DNS away from "the Zoho
> origin". **There is no Zoho origin.** Production has been the Cloudflare Pages project
> `cochinwood-web` serving the `cf-live` branch verbatim, with `cochinwood.in` and `www`
> already attached to it as custom domains. The cutover therefore never touches DNS — it
> changes what that one project builds. Following the old wording under pressure would have
> sent someone hunting for a DNS record that does not exist, during an incident.

1. On the existing `cochinwood-web` Pages project, verify the current production settings so
   you can restore them exactly: production branch `cf-live`, **no** build command, output
   directory `/`. Write them down before changing anything.
2. Point a **preview** deployment at `master` with build command `python build.py` and output
   directory `dist`. Verify the resulting `*.pages.dev` URL end-to-end — every page, assets,
   the quote form, schema — against the live site. Nothing about production has changed yet.
3. Reconcile the URL set before flipping. As of 2026-08-26 the build emits 202 pages against
   293 live URLs; the gap is blog category, pagination and tag pages. Also settle
   `/wood-encyclopedia/*`, which this build produces but `cf-live` 301s to `/woods-we-use` —
   both cannot be right.
4. **Flip:** change the project's production branch to `master`, set build command
   `python build.py`, output directory `dist`. The custom domains stay where they are; DNS is
   not touched. Deployment is atomic — Pages serves the previous build until the new one
   succeeds.
5. Purge the Cloudflare cache; re-test; submit the sitemap in Search Console. Expect the edge
   to keep serving cached HTML at some PoPs for a while — a cache-busting query proves what the
   origin is actually returning.
6. **Rollback:** set the production branch back to `cf-live`, clear the build command, restore
   output directory `/`, and redeploy. `cf-live` is never modified by any of this, so it is
   always exactly the site that was live before the flip. No DNS change is involved in the
   rollback either.

## Cost
$0 recurring (Cloudflare Pages free tier). One-time cost is build effort only.
Zoho One (CRM/Books) is unaffected — this is a capability upgrade, not a saving.
