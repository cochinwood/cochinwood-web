# `cf-live` pin review — 15 September 2026

This record licenses the `build.py` production pin move from
`5e8fdcf484f7659cc178385978a01e4decc34497` to
`7d588f16b0036b5f4b825ac96b4d8df78d99dff4`, the production merge of PR #62.
It also records that release (PR #62 publication, PR #63 source).

## Reviewed production window

```text
7d588f16 Merge PR #62 publish/product-schema-visible-facts-20260915
64c894dd Merge PR #60 publish/website-audit-20260914
c06ed144 Merge PR #59 publish/approved-thickness-presets-20260914
2a8e99cb Merge PR #58 publish/approved-thickness-ranges-20260914
d04f700e Merge PR #57 publish/website-improvements-20260914
9c1e05ca Publish full-aspect audit remediations (#54)
8514f52e Merge PR #52 publish/website-review-20260912
```

Until 15 September the release preflight failed its live-pin check against
`64c894dd`. This review closes that gap.

## Tree and carried-file comparison

`git ls-tree -r --name-only` reports 1,156 paths at the old pin and 1,168 at the
new one: 12 added, 261 modified, none removed.

- Added: `assets/bundle.eba2ca64.css`, `assets/container-calculator.ea9e2f64.js`,
  `assets/favicon.ico`, `assets/print.cdc7a549.css`,
  `assets/quick-inquiry.cced64e0.js`, `assets/quote-form.98c2da2a.js`,
  `assets/site.c6a8ed6d.js`, four `assets/tds/*.pdf` data sheets and the root
  `favicon.ico`.
- Modified: 157 blog posts, 28 export pages, 28 wood-species pages, the 16
  product pages, 27 other content pages, the three sitemaps, `_headers` and
  `_redirects`. They are the generated output of the reviewed releases above.

The inputs every build copies from the pinned tree are unchanged:

- `files/`: tree `a7bd7cb3629b` at both revisions.
- `.github/workflows/site-checks.yml`: blob `6e0a4f519408` at both.
- `015ad99674249c7dc418af21415b06bc.txt` (IndexNow key): blob `c4e4ff118eeb` at both.
- `llms.txt`: blob `c1f2ece3d292` at both.
- `favicon.png`: blob `42ed03eaf114` at both.
- `cwi-og-share-1200x630.png`: blob `5eeba7f60f47` at both.

Hashed assets matched by `LIVE_HASHED_ASSET_RE` go from 11 to 15. The four newly
carried are `bundle.eba2ca64.css`, `container-calculator.ea9e2f64.js`,
`quote-form.98c2da2a.js` and `site.c6a8ed6d.js`. None is dropped, so the carried
count moves from 867 to 871.

Two assets were published and deleted inside the window:
`assets/bundle.16eb5fba.css` (PR #52) and `assets/bundle.fde25d10.css` (PR #54).
Both were removed by `025e515b` (PR #57), so neither pin carries them. They are
not restored. No file in the new pin's tree and no source file references either
name, so restoring them would republish stylesheets nothing links to.

## Preservation check against the source build

With `LIVE_SHA` at `7d588f16`, a build of `master` (`05b2cd4b`) produced 1,168
files. `tools/verify_publication.py dist <cf-live checkout> --ref 7d588f16`
reports 0 missing, 0 extra and 1 different file: `_headers`. Its only change is
the generated provenance line, from `origin/cf-live@5e8fdcf484f7` to
`origin/cf-live@7d588f16b003`. Before the move the same source reproduced all
1,168 files of `7d588f16` byte for byte, including the sitemaps.

`python tools/cutover_preflight.py HEAD` on the pin commit reports 21 passed and 0 failed, including the live-tip pin, two byte-identical builds, every live URL served or redirected, the carried bytes, the publication workflow, the beacon, the forms, the CSP and the immutable asset hashes.

## Release receipt: PR #62 and PR #63, 15 September 2026

- **Source:** PR #63 merged as `05b2cd4b` with a merge commit (parents
  `e4cd0ffa`, `76b41b8b`). It brings `master` level with the already-live source
  of PRs #57–#60 (`bf692200`, `46b5ed58`, `9232b55d`, `f0b283df`), plus
  `495dedf1` and `76b41b8b`.
- **Publication:** PR #62 merged as `7d588f16` (parents `64c894dd`, `e333d869`).
  Its tree is identical to the reviewed head `e333d869`. `tools/verify_publication.py`
  matched 1,168 of 1,168 files, with none missing, extra or different.
- **Change:** 82 facts in the Product JSON-LD of the 16 product pages, each copied
  verbatim from one visible block of its page. No `offers`, price, availability,
  SKU, MPN or GTIN. `tools/test_product_schema_facts.py` guards this.
- **Checks on `7d588f16`:** GitHub "The site says one thing" succeeded (Actions
  run 34948640203). Cloudflare Pages succeeded.
- **Deployment:** Cloudflare Pages production deployment
  `223ccec0-736c-49e1-bd9f-44ec5b8c187b`, created 2026-09-15 08:44:41 UTC for commit
  `7d588f16` on `cf-live`, stage `deploy`: success.
- **Live verification:** ordinary requests to `https://www.cochinwood.in` returned all
  18 changed files byte-identical to `7d588f16`: the 16 product pages,
  `sitemap-cms.xml` and `sitemap.xml`. The apex served one stale edge copy of
  `/container-flooring-plywood` (`cf-cache-status: HIT`, age 3,708 s), although
  the origin already had the new bytes. The 18 paths were purged on both www and
  the apex (36 URLs, two API batches, both successful). Afterwards all 18 paths
  on both hosts matched `7d588f16`.
- **Known and unchanged:** `tools/test_export_text_guides.py` still fails 30
  subtests, as it did before this release. Its 7 September fixture predates the
  approved export-page releases.

## Reproduction commands

```powershell
git fetch --prune origin
git diff --name-status 5e8fdcf484f7..7d588f16b003
git diff --name-status 5e8fdcf484f7..7d588f16b003 -- files .github/workflows/site-checks.yml 015ad99674249c7dc418af21415b06bc.txt llms.txt favicon.png cwi-og-share-1200x630.png
git log --diff-filter=D --name-status 5e8fdcf484f7..7d588f16b003 -- assets
python build.py
python tools/verify_publication.py dist <cf-live checkout> --ref 7d588f16b003
python tools/cutover_preflight.py HEAD
```
