# `cf-live` pin review — 16 September 2026

This record licenses the `build.py` production pin move from
`1d699b6ef4c315489117c3d5af6d5bdb8c91f100` (production merge of PR #67, reviewed in
`docs/cf-live-pin-review-2026-09-15c.md`) to
`f906f6196f1648954ad7f8ff6ade5e3b09473d68`, the production merge of PR #69 (load-figure consistency sweep).

## Reviewed production window

```text
f906f619 Merge pull request #72 from cochinwood/publish/site-audit-fixes-20260916
71f4df00 Merge pull request #71 from cochinwood/publish/contact-ui-redesign-20260916
9e4115aa Merge pull request #70 from cochinwood/publish/live-sales-contacts-20260916
16294f69 Merge pull request #69 from cochinwood/publish/load-figure-consistency-20260916
```

`f906f619` has parents 71f4df00 012d9e0c. Cloudflare Pages project `cochinwood-web` reports production deployment
`3bd6b7ff-3b06-4f62-97c1-e3c6a5c1e121` (16 Sep 2026 03:20 UTC, branch `cf-live`, status success) for it. After that
deployment the 32 changed HTML and sitemap files were purged on www and apex, 14 hedged pages were verified live as
an ordinary visitor, and `tools/submit_indexnow.py --submit` byte-compared 30 changed URLs against the build before
IndexNow accepted them.

## Tree and carried-file comparison

`git ls-tree -r --name-only` reports 1168 paths at the old pin and 1168 at the new one; changes by kind: {'M': 262}.
They are the generated output of the reviewed PR #68 source change (truck and container load figures hedged across
31 city guides, two statistics reconciled, `tools/load_figures.py`, seven new content-claim tests).

The inputs every build copies from the pinned tree:

- `files`: unchanged at `a7bd7cb3629b`
- `assets`: **CHANGED** 7374ec9dac64 -> 0aea90f06a09
- `.github/workflows/site-checks.yml`: unchanged at `6e0a4f519408`
- `015ad99674249c7dc418af21415b06bc.txt`: unchanged at `c4e4ff118eeb`
- `llms.txt`: unchanged at `c1f2ece3d292`
- `favicon.png`: unchanged at `42ed03eaf114`
- `cwi-og-share-1200x630.png`: unchanged at `5eeba7f60f47`

No carried input moved, so advancing the pin changes no copied file; it lets the release preflight's live-pin check
and the sitemap lastmod comparison read the tree that is actually live.
