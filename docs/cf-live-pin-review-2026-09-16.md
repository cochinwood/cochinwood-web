# `cf-live` pin review — 16 September 2026

This record licenses the `build.py` production pin move from
`1d699b6ef4c315489117c3d5af6d5bdb8c91f100` (production merge of PR #67, reviewed in
`docs/cf-live-pin-review-2026-09-15c.md`) to
`f906f6196f1648954ad7f8ff6ade5e3b09473d68`, the current tip of `cf-live`.

It is not a routine pin move. Three of the four publications in this window were made
**without a source commit**, by editing built output directly, and one of them left three
content-addressed asset URLs serving bytes their names do not describe. The pin cannot move
until that is repaired, which is what the branch carrying this record does.

## Reviewed production window

```text
f906f619 Merge pull request #72 from cochinwood/publish/site-audit-fixes-20260916
71f4df00 Merge pull request #71 from cochinwood/publish/contact-ui-redesign-20260916
9e4115aa Merge pull request #70 from cochinwood/publish/live-sales-contacts-20260916
16294f69 Merge pull request #69 from cochinwood/publish/load-figure-consistency-20260916
```

`f906f619` has parents `71f4df00` and `012d9e0c`. Cloudflare Pages project `cochinwood-web`
reports production deployment `c56c6fb9` (16 Sep 2026 06:23:48 UTC, branch `cf-live`, status
success) for it.

Only PR #69 came from a reviewed source branch that was merged back into `master`
(PR #68, `master` `58639e95`). PRs #70, #71 and #72 did not.

## What a build of `master` could not reproduce

A clean `python build.py` at `master` `58639e95` differed from this tip in **259 of 1,168
files**: 255 HTML pages, `assets/bundle.eba2ca64.css`, `assets/site.c6a8ed6d.js`,
`assets/quote-form.98c2da2a.js` and `assets/quick-inquiry.cced64e0.js`. All 259 belong to
publication `012d9e0c` (PR #72). The four asset files changed content **without changing
name**, which is the signature of an edit made to built output rather than to source: a name
this build emits is derived from the bytes, so the generator cannot produce that state.

Searching every ref in the repository for the markup it introduced (`cw-mobile-dock`) returns
`012d9e0c` and nothing else. There is no source branch to merge; the peer session that might
have held one confirmed it never worked in this repository.

### The three URLs that lie about themselves

`assets/` is carried into every build from the pinned tree, so those names become this build's
output too. Their bytes do not hash to the names they are published under:

| published name | name says | bytes are |
|---|---|---|
| `assets/bundle.eba2ca64.css` | `eba2ca64` | `13a35d2f` |
| `assets/site.c6a8ed6d.js` | `c6a8ed6d` | `6fee576e` |
| `assets/quote-form.98c2da2a.js` | `98c2da2a` | `8bf296ac` |
| `assets/quick-inquiry.cced64e0.js` (not carried) | `cced64e0` | `547fdf03` |

These URLs are served with a year-long immutable pin. A returning visitor who cached one is
pinned until September 2027 to bytes the name never described, and there is no URL left to
push a correction through. Moving `LIVE_SHA` onto this tip without repairing them fails
`tools/cutover_preflight.py`'s "named for its own bytes" checks — 18 passed, 3 failed, which
is what closed PR #74.

## What this branch does about it

1. **Reconstructs publication #72 in source**, from the published bytes, so the generator owns
   it: the mobile action dock on every page, the homepage trust ribbon and hero calls to
   action, the catalogue filter pills and their script, the container-calculator card on
   `/export`, the product-specific quote links on the species pages, the quick-search index
   and modal, and the quote-form and quick-inquiry script changes. `assets/conversion-ui.css`
   is new; the three JavaScript files are taken verbatim from the published bytes.
2. **Repairs the three carried URLs.** `HAND_EDITED_LIVE_ASSETS` in `build.py` carries each
   one from `71f4df00`, the tip immediately before the hand edit, where the bytes still match
   the name. Publishing this `dist/` restores the invariant on `cf-live` itself, after which
   the map can be deleted.
3. **Moves the pin** to `f906f619`.

## Verification

A build of this branch reproduces `cf-live`'s 256 HTML pages exactly, once the four
legitimately renamed asset URLs are normalised, with two intended exceptions:

- `contact.html` — the generator's accessibility pass adds `aria-hidden="true"` and
  `focusable="false"` to five decorative icons in the sales directory. The hand-edited copy
  never passed through it.
- `404.html` — gains the dock. The hand edit was applied to 255 pages and skipped the error
  page; the dock is emitted from the shared page shell here, and a lost visitor is the one
  most likely to want the sales desk.

`python -m unittest discover -s tools` — 126 tests, OK. `tools/check_site.py` — OK.
The export-guide preservation baseline was recaptured (its documented refresh path) because
`/export` legitimately gains the calculator card; the 28 country guides are unchanged.

## Tree and carried-file comparison

`git ls-tree -r --name-only` reports 1168 paths at the old pin and 1168 at the new one;
changes by kind: 262 modified, none added or deleted.

The inputs every build copies from the pinned tree:

  - `files`: unchanged at `a7bd7cb3629b`
  - `assets`: **CHANGED** `7374ec9dac64` -> `0aea90f06a09`
  - `.github/workflows/site-checks.yml`: unchanged at `6e0a4f519408`
  - `015ad99674249c7dc418af21415b06bc.txt`: unchanged at `c4e4ff118eeb`
  - `llms.txt`: unchanged at `c1f2ece3d292`
  - `favicon.png`: unchanged at `42ed03eaf114`
  - `cwi-og-share-1200x630.png`: unchanged at `5eeba7f60f47`

`assets` moved because of the hand edit described above, and is the reason
`HAND_EDITED_LIVE_ASSETS` exists. No other carried input moved.

## Standing risk this window leaves behind

Publishing straight to `cf-live` from a branch that never returns to `master` costs a day of
forensics per occurrence and, this time, came within one publication of freezing three broken
immutable URLs for a year. The publication flow — source PR to `master` first, then a
`publish/*` PR built from it — exists to prevent exactly this.
