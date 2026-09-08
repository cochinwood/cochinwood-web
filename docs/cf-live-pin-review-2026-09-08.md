# `cf-live` pin review — 8 September 2026

This record licenses the `build.py` production pin move from
`ef44629fd2a63a18ce507dc3c9cf0cda871077a2` to
`255aeed1efc3861bc4264658711c2e1c58eb49e8`. The reviewed window is the live
publication of PR39:

```text
255aeed1 Merge PR39 publish/rate-suppression-2026-09-08
adeed2a5 Stop publishing own sale rates and margin rule
```

## Tree and carried-file comparison

`git ls-tree -r --name-only` reports 1,146 paths at each revision, with no added
or removed path. Thirty-four paths have different blobs.

The files copied into every build from the live tree have no differences in the
review window:

- `files/`: 846 blobs at each revision; tree object
  `4816045338c20c5662f7c68de5453d73e84b49cd` at both revisions.
- `.github/workflows/site-checks.yml`: blob
  `6e0a4f51940820d64a239eefda0ff216698d156e` at both revisions.
- `015ad99674249c7dc418af21415b06bc.txt`: blob
  `c4e4ff118eeba37b597c2ccbf8bafaa60999b874` at both revisions.
- `llms.txt`: blob `c1f2ece3d292fce002a59ea66e91f383c05ea34a`
  at both revisions.
- `favicon.png`: blob `42ed03eaf114a97d945d7b2cd99f7bf183563f86`
  at both revisions.
- `cwi-og-share-1200x630.png`: blob
  `5eeba7f60f47a4f07f20121f7fe2145a467e0a7b` at both revisions.

The carried count therefore remains 851 and the pin update cannot change an
image, discovery file, workflow or other preserved blob. Franklin's separate
image-rights/removal branch is not part of this review or integration.

## Reviewed published diff

The 34 modified paths classify as follows:

- 28 generated HTML pages: `blogs.html` and 27 posts. The semantic diff removes
  CWI sale-rate numbers, the `purchase rate + ₹2.50/sq.ft` margin rule, and price
  deltas. Replacements say “On request”, describe relative cost without figures,
  or direct the buyer to a job-specific quote. This is PR39's rate suppression.
- 2 generated species pages: `woods-we-use.html` and
  `woods-we-use/melia-dubia.html`. These carry the already-shipped Melia credit
  correction from “Thamoung et al.” to “Akshaya et al.”; the Sal card alt text is
  corrected from “end-grain visual” to “wood visual”. No image blob changes.
- 3 sitemap files. URL inventories are unchanged. `sitemap-post.xml` keeps all
  157 URLs and changes 157 `lastmod` values from 2026-09-05 to 2026-09-08;
  `sitemap-cms.xml` keeps 97 URLs and changes four dates; the three-entry sitemap
  index changes two dates. The per-post `lastmod` correction on this branch
  supersedes the monolithic post-date update without removing any URL.
- `_headers`: only its generated build-provenance comment changes, from the
  prior production pin to `ef44629fd2a6`.

The 27 changed post paths are:

```text
blogs/post/birch-vs-okoume-vs-gurjan-pick-the-right-face-veneer-for-export-packing.html
blogs/post/bwr-vs-bwp-for-export-packing-when-mr-grade-will-fail-at-sea.html
blogs/post/plywood-boxes-for-machinery-triple-wall-vs-reinforced-single-wall.html
blogs/post/plywood-for-packing-cases.html
blogs/post/plywood-supply-to-agra.html
blogs/post/plywood-supply-to-asansol.html
blogs/post/plywood-supply-to-aurangabad.html
blogs/post/plywood-supply-to-bhilwara.html
blogs/post/plywood-supply-to-bhubaneswar.html
blogs/post/plywood-supply-to-cuttack.html
blogs/post/plywood-supply-to-dhanbad.html
blogs/post/plywood-supply-to-duqm.html
blogs/post/plywood-supply-to-durgapur.html
blogs/post/plywood-supply-to-greater-noida.html
blogs/post/plywood-supply-to-gurugram.html
blogs/post/plywood-supply-to-hubli-dharwad.html
blogs/post/plywood-supply-to-indore.html
blogs/post/plywood-supply-to-jalandhar.html
blogs/post/plywood-supply-to-jamnagar.html
blogs/post/plywood-supply-to-jamshedpur.html
blogs/post/plywood-supply-to-karnal.html
blogs/post/plywood-supply-to-karur.html
blogs/post/plywood-supply-to-noida.html
blogs/post/plywood-supply-to-solapur.html
blogs/post/plywood-supply-to-tiruppur.html
blogs/post/plywood-supply-to-tuticorin.html
blogs/post/plywood-supply-to-udaipur.html
```

## Preservation check against the source build

Before changing the pin, a clean build from this branch and the full
`origin/cf-live@255aeed1` tree each contained exactly 1,146 paths, with no path
present on only one side. SHA-1 blob comparison found five differences:

```text
blogs/post/plywood-supply-to-aurangabad.html
blogs/post/plywood-supply-to-muscat.html
blogs/post/plywood-supply-to-ras-al-khaimah.html
blogs/post/plywood-supply-to-tiruppur.html
sitemap-post.xml
```

The four pages are the confirmed destination-guide fixes owned by this branch.
The sitemap difference is the per-post `lastmod` correction. Every other live
blob, including all PR39 rate suppression and both species-credit corrections,
was already reproduced byte for byte. After the pin change, `_headers` also
changes intentionally to name the new pinned revision.

## Reproduction commands

```powershell
git fetch --prune origin
git diff --name-status ef44629fd2a6..origin/cf-live
git diff --name-status ef44629fd2a6..origin/cf-live -- files .github/workflows/site-checks.yml 015ad99674249c7dc418af21415b06bc.txt llms.txt favicon.png cwi-og-share-1200x630.png
git ls-tree -r ef44629fd2a6
git ls-tree -r origin/cf-live
python build.py
python tools/cutover_preflight.py HEAD
```

The final preflight result is 17 passed and 0 failed, including the live-tip pin,
two byte-identical builds, all 1,145 live URL paths preserved, all carried bytes,
the publication workflow, beacon, forms, headers, LF normalization and immutable
asset hashes.
