# cochinwood-web — clean rebuild of cochinwood.in

Git-based static site for Cochin Wood Industries, built with a dependency-free
Python generator (`build.py`). Replaces the Zoho Sites builder so the whole site
is version-controlled, auditable, and deployable by push. See `CUTOVER-PLAN.md`.

## Build
    python build.py                             # -> dist/ for the domain root
    SITE_BASE=/cochinwood-web python build.py   # -> dist/ for GitHub project Pages
    STRICT=1 python build.py                    # fail the build on any warning (use in CI)

The build prints a warning block and exits non-zero under `STRICT=1`. It never
ships a broken image or a dead internal link — anything it cannot resolve is
removed from the markup and reported.

## Layout
- `build.py` — the generator (templates + content + page builders)
- `assets/` — brand CSS, `components.css` (shared UI), `site.js`, fonts, logo
- `assets/photos/` — **drop site photography here** (see below)
- `content/encyclopedia/` — the 20 wood-species pages (wrapped in site chrome at build)
- `content/pages/`, `content/blog/posts.json` — page and post content
- `dist/` — build output (gitignored on `master`; published on `gh-pages` / `cf-live`)

### Photography
Content references photos by their original Zoho paths (`/files/...`). The build
looks for each one in `assets/photos/<same path>` first, then in `$MIRROR_DIR`
(default `../cochinwood-site`). A reference that resolves is copied into `dist/`;
one that does not is **stripped from the markup** and listed at the end of the
build, so a broken image can never reach production.

18 photos are currently unresolved — the About gallery, the Industries and BWR
hero art, and several CSS background images. To restore them, copy the files in
under `assets/photos/` keeping the same path, e.g.

    assets/photos/files/Enhanced Factory Photos/factory_08.jpg
    assets/photos/files/Product/bwr-hardwood.jpg

and rebuild. Layouts collapse gracefully while a photo is absent and re-expand
once it exists — no markup change needed.

### Redirects
`LEGACY_REDIRECTS` in `build.py` is the single source of truth for old Zoho
slugs. Each entry both rewrites in-content links at build time and emits a 301
into `dist/_redirects` for Cloudflare Pages, so inbound links keep their value.
Add a slug there when a URL changes.

## Status
All pages rebuilt clean: Home, Products (13 lines), Industries, About, Contact,
FAQ, Resources, policies, Wood Encyclopedia (hub + 20) and 156 blog posts.
Production target: Cloudflare Pages at cochinwood.in.
