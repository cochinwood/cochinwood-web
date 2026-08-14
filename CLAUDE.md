# Branch map — read this before changing anything

## You are on `master`. This branch is NOT deployed.

`master` is the clean, dependency-free Python SSG rebuild (`build.py` → `dist/`).
It is intended to replace the live site — see `CUTOVER-PLAN.md` — but **that
cutover has not happened.** Nothing you fix here reaches a visitor until Phase 6
of that plan is carried out.

**The live site at https://www.cochinwood.in is served from the `cf-live` branch**,
which Cloudflare Pages publishes verbatim with no build step.

Verified 2026-08-15 by diffing the live homepage against `cf-live:index.html` —
byte-identical apart from Cloudflare's own email-obfuscation injection.

If you are here because a visitor reported a problem with the live site, you are on
the wrong branch:

    git checkout cf-live

## Branches

| Branch | What it is | Deployed |
|---|---|---|
| `cf-live` | The live site. ~293 hand-maintained `.html` files, no build step. | **yes — production** |
| `master` | This branch. Python SSG rebuild, the planned successor. | no |

## A note on the Zoho references

Both branches carry vocabulary inherited from CWI's former Zoho Sites site — the
`cf-live` HTML still contains `zsite-core.css` and similar, and `build.py` here
resolves photography by its original `/files/...` Zoho paths. **CWI is fully off
Zoho Sites.** Those are historical artefacts of the migration, not a live
dependency on Zoho.

## Build

    python build.py                             # -> dist/ for the domain root
    SITE_BASE=/cochinwood-web python build.py   # -> dist/ for GitHub project Pages
    STRICT=1 python build.py                    # fail the build on any warning

See `README.md` for the full generator documentation.
