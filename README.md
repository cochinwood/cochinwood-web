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

Two corrections happen on the way out:

- **True extension.** Part of the Zoho asset set is WebP carrying a `.jpg` name.
  Served by extension a browser gets `image/jpeg` for WebP bytes and refuses to
  decode it, so the build sniffs the magic bytes and publishes each file under
  the extension it deserves, rewriting the reference to match.
- **True dimensions.** `width`/`height` are read from the file rather than
  trusted from the markup, so the browser reserves the right box and the page
  does not shift as photos load.

One photo is still unresolved: `files/Product/bwr-hardwood.jpg`, which exists on
no branch. That product hero simply renders without art. To restore it, drop the
file at `assets/photos/files/Product/bwr-hardwood.jpg` and rebuild — layouts
collapse gracefully while a photo is absent and re-expand once it exists.

`PRODUCT_HERO` maps catalogue slugs to hero photography for pages whose hero slot
previously held a Zoho stock placeholder. A slug with no entry keeps no hero
image rather than borrowing an unrelated one.

### Titles
`seo_title()` fits every `<title>` into ~62 characters so search snippets stop
truncating mid-word: it shortens or drops the brand suffix, simplifies the
species-page pattern, and drops a trailing parenthetical or subtitle. The visible
H1 and the `og:title` keep the full headline. `TITLE_OVERRIDES` holds the handful
of headlines that needed a hand-written short form; the build warns if any title
still does not fit.

### Redirects
`dist/_redirects` is generated from two things. `PORTED_REDIRECTS` carries the
hand-maintained rule set from the live `cf-live` branch verbatim, comments and
order included; `LEGACY_REDIRECTS` holds the old Zoho slugs, and each of its
entries *also* rewrites in-content links at build time — so where the two
disagree on a slug, `LEGACY_REDIRECTS` wins and the build says so, because a 301
and the links on the page must not lead to different places.

Every rule is then re-checked against the pages the build actually emitted. A
rule whose target is not built is dropped and reported, and comes back on its own
the day that page is added; a rule that would shadow a real page is dropped too.
**Cloudflare Pages honours only the first 100 rules** — the build counts them,
prints the count in its banner and warns as the file approaches the limit, so put
anything order-sensitive near the top. `DROPPED_FROM_LIVE` records the live rules
deliberately not carried across, and why.

## Status
All pages rebuilt clean: Home, Products (13 lines), Industries, About, Contact,
FAQ, Resources, policies, Wood Encyclopedia (hub + 20) and 156 blog posts.
Production target: Cloudflare Pages at cochinwood.in.
