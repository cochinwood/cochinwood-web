# Branch map — read this before changing anything

## `master` is superseded, and the cutover it says has not happened, has.

This file said `master` was "the planned successor", that "the cutover has not
happened", and that `cf-live` was "~293 hand-maintained `.html` files, no build
step". All three were true when written and none is true now. `master` is the
repository's default branch, so this is the first thing a fresh clone reads, which
is why it is worth correcting rather than leaving.

**What is true, verified 5 Sep 2026 by counting rather than by reading a doc:**

| | |
|---|---|
| **Production** | branch `cf-live`, published verbatim by Cloudflare Pages at https://www.cochinwood.in |
| **What `cf-live` contains** | the **output** of `python build.py` — 607 files, 253 `.html`. Not hand-written. |
| **Source** | `content/` + `build.py` on **`cutover-ready-2026-09-04`**, not on this branch |
| **The cutover** | `ebc11445`, 4 Sep 2026 07:03 IST, *"Publish the reviewed build (ce24ab15) as the served tree"* |
| **`master`** | an ancestor of the source branch. Real, but behind. Do not start work here. |

Re-verify it yourself in three commands:

    git log -1 --format='%h %ad %s' ebc11445          # the cutover
    git ls-tree -r --name-only origin/cf-live | wc -l # 607
    git checkout cutover-ready-2026-09-04 && python build.py   # "files: 607"

## Where to work

    git checkout cutover-ready-2026-09-04

Then edit `content/**` or `build.py` and run `python build.py`. **Never hand-edit a
`.html` file expecting it to ship** — `cf-live` is generated, and the next build
overwrites it. That is the single mistake this page exists to prevent, and it has
already cost one agent a day's work.

A push to `cf-live` IS a deploy. Branch and open a pull request instead.

## Branches

| Branch | What it is | Deployed |
|---|---|---|
| `cf-live` | **Production.** Build output, served verbatim. Do not hand-edit. | **yes** |
| `cutover-ready-2026-09-04` | The source: `content/` + `build.py`. Work here. | no — via a build |
| `master` | This branch. The original SSG rebuild, now behind the source branch. | no |
| `dedupe-2026-08-27` | A merged feature branch from 31 Aug. Its own `CLAUDE.md` is stale in a third, different way — it says "You are on `cf-live` … There is no build step … You edit the `.html` files directly." | no |

## `cf-live` has run ahead of the source, and that is a real thing to check

Four pull requests (#17–#20) landed export-market data **directly on `cf-live`**
after the cutover, and that work is **not** on `cutover-ready-2026-09-04`. A build
made from the source today would publish an older snapshot over it. `build.py` is
pinned to `LIVE_SHA = c59adae9` and carries 311 files from it, which is what the
first of the build's three standing warnings is about. **Read that warning. Do not
move `LIVE_SHA` without re-reviewing what landed in between.**

## A note on the Zoho references

Vocabulary inherited from CWI's former Zoho Sites site survives in the markup and in
`build.py`, which still resolves photography by its original `/files/...` Zoho paths.
**CWI is fully off Zoho Sites.** Those are historical artefacts of the migration, not
a live dependency. Reading "zsite" and concluding the site still runs on Zoho is a
mistake that has already been made once.

## Build

    python build.py                             # -> dist/ for the domain root
    SITE_BASE=/cochinwood-web python build.py   # -> dist/ for GitHub project Pages
    STRICT=1 python build.py                    # fail the build on any warning

A clean build exits 0, prints `BUILD OK`, and emits exactly **three** warnings — the
`cf-live` drift pin, 7 rewritten 301 targets, and 13 rules deliberately not carried.
Those three are expected; a fourth is yours. `STRICT=1` exits 1 on those three, so it
fails on an untouched checkout too — that is not a regression you introduced.

See `README.md` for the full generator documentation.
