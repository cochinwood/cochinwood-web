# Branch map — read this before changing anything

## The cutover HAS happened. `cf-live` is generated output now.

This file said the opposite until 5 September 2026, and it was wrong for a day —
it told two agents that `cf-live` was ~293 hand-maintained `.html` files and that
"nothing you fix here reaches a visitor". Both statements are now false, and
hand-editing HTML on the strength of them is wasted work that ships nothing.

**What is true, verified 5 Sep 2026 by counting rather than by reading a doc:**

| | |
|---|---|
| **Production** | branch `cf-live`, published verbatim by Cloudflare Pages at https://www.cochinwood.in |
| **What `cf-live` contains** | the **output** of `python build.py` — 607 files, 253 `.html`. Not hand-written. |
| **Source** | this lineage: `content/` + `build.py` on `cutover-ready-2026-09-04` |
| **The cutover** | `ebc11445`, 4 Sep 2026 07:03 IST, *"Publish the reviewed build (ce24ab15) as the served tree"* |

`ce24ab15` — the commit whose build was published — is an ancestor of
`cutover-ready-2026-09-04`, and `python build.py` on this branch still reports
`files: 607` with 253 `.html`. That match is the evidence, not this sentence.

Re-verify it yourself in three commands:

    git log -1 --format='%h %ad %s' ebc11445          # the cutover
    git ls-tree -r --name-only origin/cf-live | wc -l # 607
    python build.py                                   # "files: 607"

### So: edit the source, never the output

    content/**, build.py   ->  python build.py  ->  dist/  ->  published as cf-live

Editing a `.html` file expecting it to ship is the one mistake this page exists to
prevent. The next build overwrites it.

### `cf-live` has run ahead of the source, and that is a real thing to check

Four PRs (#17–#20) landed export-market data **directly on `cf-live`** after the
cutover. `build.py` is pinned to `LIVE_SHA = c59adae9` and carries 311 files from
it, so a build made today republishes that older snapshot over whatever those PRs
added. That is exactly what the first of the build's three standing warnings says.
**Read it. Do not move `LIVE_SHA` without re-reviewing what landed in between.**

## Branches

| Branch | What it is | Deployed |
|---|---|---|
| `cf-live` | **Production.** Build output, served verbatim. Do not hand-edit; do not push casually — a push here IS a deploy. | **yes** |
| `cutover-ready-2026-09-04` | The source: `content/` + `build.py`. Work here. | no — via a build |
| `master` | The original SSG rebuild, now an ancestor of the branch above. Superseded. | no |

## A note on the Zoho references

Vocabulary inherited from CWI's former Zoho Sites site survives in the markup and
in `build.py`, which still resolves photography by its original `/files/...` Zoho
paths. **CWI is fully off Zoho Sites.** Those are historical artefacts of the
migration, not a live dependency. Reading "zsite" and concluding the site still
runs on Zoho is a mistake that has already been made once.

## Build

    python build.py                             # -> dist/ for the domain root
    SITE_BASE=/cochinwood-web python build.py   # -> dist/ for GitHub project Pages
    STRICT=1 python build.py                    # fail the build on any warning

A clean build exits 0, prints `BUILD OK`, and emits exactly **three** warnings —
the `cf-live` drift pin, 7 rewritten 301 targets, and 13 rules deliberately not
carried. Those three are expected. A fourth is yours.

`STRICT=1` exits 1 on the three above, so it fails on an untouched checkout too;
that is not a regression you introduced.

See `README.md` for the full generator documentation.

## `/woods-we-use` keeps its URL — decided 31 Aug 2026 by Edwin. Do not re-open.

**The wood section stays at `/woods-we-use`. `/wood-encyclopedia` does NOT become the
canonical path.** It may be renamed *Wood Encyclopedia* in navigation, headings and page
titles — the visible words are free to change, the address is not.

Reason: the live URL is already indexed. Moving it costs a ranking dip and a fresh set of
301s for no product gain, while the naming benefit is available for nothing by changing the
words on the page. Renaming is reversible; losing rankings is not. **Generalise it: when in
doubt, do not move a URL.**

The code change landed on this lineage on 31 Aug 2026 (`WOOD_PATH` / `WOOD_LABEL` in
`build.py`), so the generator and this decision now agree. The conflict it closes was
raised as blocker 2 / recommendation 3 in
`cochinwood-audit-2026-08-25/CUTOVER-ASSESSMENT.md`, in the shared workspace repo
(`Claude Code`): `cf-live` served one page, `woods-we-use.html`, while `build.py` built a
whole section at the redirected path and emitted no `/woods-we-use` page at all. The
generator was the side that changed.

## One more stale copy, on another branch

`master` and `dedupe-2026-08-27` still carry their own `CLAUDE.md` opening *"You are on
`cf-live`. This is production … There is no build step … You edit the `.html` files
directly."* That was true before 4 Sep and is not true now. It is not fixed here because
those are a different lineage and this branch cannot speak for them — but anyone landing
there will be misled the same way, so it is worth fixing at the same time.
