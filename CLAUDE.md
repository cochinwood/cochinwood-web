# Branch map — read this before changing anything

## You are on `cf-live`. This is production.

Cloudflare Pages serves this branch **verbatim** at https://www.cochinwood.in.
What is committed here is exactly what a visitor receives. There is no build step,
no generator, no package manager, no `dist/`. You edit the `.html` files directly.

Verified 2026-08-15: the live homepage is byte-identical to `index.html` on this
branch, apart from Cloudflare's own edge injection — it rewrites `mailto:` links
into `/cdn-cgi/l/email-protection` and adds `email-decode.min.js`. That difference
is Cloudflare's, not ours, and must never be "fixed".

Re-verify at any time:

    git show origin/cf-live:index.html > /tmp/repo.html
    curl -s https://www.cochinwood.in/ > /tmp/live.html
    diff /tmp/repo.html /tmp/live.html

## The Zoho strings are fossils, not a live Zoho site

This branch descends from a static mirror of CWI's former Zoho Sites site, so the
HTML still contains `zsite-core.css`, `zs-customcss.css`, a `zs_rendering_mode`
global, and `/template/55562362302e4b8a8860fffaee39d549/...`. `/css/zsite-core.css`
returns HTTP 200.

**CWI is fully off Zoho Sites.** Every one of those files is committed in this repo
and served by Cloudflare. Nothing calls out to Zoho. Reading "zsite" in the markup
and concluding the site still runs on Zoho is a mistake that has already been made
once — check `git ls-tree -r origin/cf-live` to see where a file comes from, rather
than inferring the host from the markup's vocabulary.

Some of that inheritance is dead weight worth removing for load speed. Some of it
the mirrored layout still depends on. Never delete Zoho-era CSS, JS or markup
without first proving in a browser that the affected pages render identically
before and after, at both 375px and 1280px.

## Branches

| Branch | What it is | Deployed |
|---|---|---|
| `cf-live` | The live site. ~293 hand-maintained `.html` files, no build step. | **yes — production** |
| `master` | A clean Python SSG rebuild (`build.py` → `dist/`) intended to replace this branch. See `CUTOVER-PLAN.md` there. | no |

Work landed on `master` reaches no users today.

## Config files

- `_headers`, `_redirects` — Cloudflare Pages config, hand-maintained.
- `_redirects` is first-match-wins, and Pages drops `:splat` in some rule forms.
  Both have caused regressions in this repo before.
- `robots.txt`, `sitemap.xml` — hand-maintained; keep them in step with the pages
  that actually exist.

## Caching caveat

`_headers` marks `/assets/*`, `/css/*`, `/js/*` and `/template/*` as
`max-age=31536000, immutable`. Only `assets/fonts/*.woff2` are genuinely
content-addressed. The rest — `assets/fonts.css`, `css/zsite-core.css`,
`js/zsite-core.js`, the `template/` stylesheets — have stable filenames and are
referenced with no version query string, so an edit to any of them will not reach
a returning visitor, and `immutable` means even a hard reload will not revalidate.
Narrow those rules before relying on them.

## Automated audit

A scheduled cloud routine audits this branch every 6 hours and opens a single
`audit/<date>` PR against `cf-live`. It must verify every finding against the
actual file before fixing, and opens no PR when nothing survives verification.
