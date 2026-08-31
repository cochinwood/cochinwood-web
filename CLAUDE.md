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

## `/woods-we-use` keeps its URL — decided 31 Aug 2026 by Edwin. Do not re-open.

**The wood section stays at `/woods-we-use`. `/wood-encyclopedia` does NOT become the
canonical path.** It may be renamed *Wood Encyclopedia* in navigation, headings and page
titles — the visible words are free to change, the address is not.

Reason: the live URL is already indexed. Moving it costs a ranking dip and a fresh set of
301s for no product gain, while the naming benefit is available for nothing by changing the
words on the page. Renaming is reversible; losing rankings is not. **Generalise it: when in
doubt, do not move a URL.**

This closes a conflict the 25 Aug audit raised and deliberately left open — blocker 2 and
recommendation 3 in `cochinwood-audit-2026-08-25/CUTOVER-ASSESSMENT.md`, in the shared
workspace repo (`Claude Code`). The two sides were:

- `cf-live` serves one page, `woods-we-use.html`, and `_redirects` lines 28–29 send the
  other name to it:

      /wood-encyclopedia /woods-we-use 301
      /wood-encyclopedia/* /woods-we-use 301

- `master`'s `build.py` builds the opposite — a whole section at the redirected path.
  `build.py:598` writes `wood-encyclopedia/index.html`; `build.py:604` writes
  `wood-encyclopedia/<slug>/index.html` for the 20 species listed at `build.py:590`;
  `build.py:224` puts `("Wood Encyclopedia", "/wood-encyclopedia/", False)` in the nav.
  It emits no `/woods-we-use` page at all.

So `master` is the side that is wrong, and **the generator changes, not the live URL.**

**On this branch that code change HAS been made** (WOOD_PATH/WOOD_LABEL in build.py, 31 Aug 2026) — the paragraph below is kept for branches that predate it. It is a real change with consequences and needs its
own review, so until it lands `build.py` still contradicts this section — that is known, not
an oversight. Whoever picks it up: the target is `/woods-we-use` as the canonical path with
the *Wood Encyclopedia* label kept, and two more things fall out of it —

- `build.py:857-859` regenerates `_redirects` wholesale from `LEGACY_REDIRECTS`: 19 rules
  against the 96 live on `cf-live`, and the map at `build.py:28-48` does not contain the two
  `/wood-encyclopedia` rules above. Cutting over as written replaces the live redirect file
  with the short one and drops them.
- `LEGACY_REDIRECTS` at `build.py:45-47` points three old `/blogs/post/wood-*` slugs at
  `/wood-encyclopedia/...`; those targets have to move too.

