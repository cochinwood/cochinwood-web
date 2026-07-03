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
- `gh-pages` — built preview (`SITE_BASE=/cochinwood-web`). GitHub Pages serves it.
- **Production** — Cloudflare Pages builds `python build.py` (SITE_BASE unset) and
  serves `dist/` at cochinwood.in. Private repo is fine there.

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
1. Connect the repo to **Cloudflare Pages**, build command `python build.py`,
   output dir `dist`, root `/`.
2. Verify the `*.pages.dev` build end-to-end (all pages, assets, forms, schema).
3. Add `cochinwood.in` + `www` as custom domains on the Pages project (you're
   already on Cloudflare — DNS is in place).
4. Flip DNS/routing from the Zoho origin to Pages. Keep Zoho live until verified.
5. Purge Cloudflare cache; re-test; submit sitemap in Search Console.
6. **Rollback:** revert the DNS/route change — Zoho origin is untouched until step 4.

## Cost
$0 recurring (Cloudflare Pages free tier). One-time cost is build effort only.
Zoho One (CRM/Books) is unaffected — this is a capability upgrade, not a saving.
