# cochinwood-web — clean rebuild of cochinwood.in

Git-based static site for Cochin Wood Industries, built with a dependency-free
Python generator (`build.py`). Replaces the Zoho Sites builder so the whole site
is version-controlled, auditable, and deployable by push. See `CUTOVER-PLAN.md`.

## Build
    python build.py                      # -> dist/ for the domain root
    SITE_BASE=/cochinwood-web python build.py   # -> dist/ for GitHub project Pages

## Layout
- `build.py` — the generator (templates + content + page builders)
- `assets/` — brand CSS (`site.css` tokens, `guide.css`, `wood-enc.css`, `shell.css`) + logo
- `content/encyclopedia/` — the 15 wood-species pages (wrapped in site chrome at build)
- `dist/` — build output (gitignored on `master`; published on `gh-pages`)

## Status
Phase 1: Home, Products, Contact, and the Wood Encyclopedia (hub + 15) rebuilt clean.
Production target: Cloudflare Pages at cochinwood.in.
