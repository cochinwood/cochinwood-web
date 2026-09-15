# `cf-live` pin review — 15 September 2026 (third)

This record licenses the `build.py` production pin move from
`103efa27393106b7e58836a616c49d271e5fda56` (production merge of PR #64, reviewed in
`docs/cf-live-pin-review-2026-09-15b.md`) to
`1d699b6ef4c315489117c3d5af6d5bdb8c91f100`, the production merge of PR #67.

## Reviewed production window

```text
1d699b6e Merge pull request #67 from cochinwood/publish/content-accuracy-20260915
3baf5ab4 Refresh publication of content-accuracy-20260915 (source 0b9f91f4)
```

`1d699b6e` has parents `103efa27` and `3baf5ab4`. The publication commit `3baf5ab4` carries the built
`dist/` of reviewed source `0b9f91f4e30997567f4e2d0d9cbda8523b501362`, which landed on `master` as PR #66
(merge `464ed466`). Its tree is identical to `1d699b6e`'s tree.

Cloudflare Pages project `cochinwood-web` reports production deployment
`9140498e-aa16-43fb-9307-e14db2161107` (15 Sep 2026 18:23:57 UTC, branch `cf-live`, commit `1d699b6ef4c3`,
status success). After a targeted purge of the 84 changed HTML and sitemap files on `www` and apex, 14 key pages
were verified live as an ordinary visitor, and `tools/submit_indexnow.py --submit` byte-compared all 255 page
URLs against the build before IndexNow accepted them (HTTP 200).

## Tree and carried-file comparison

`git ls-tree -r --name-only` reports 1,168 paths at both revisions: none added, none removed, 85 modified —
47 blog posts, 23 export pages, 7 root pages, 4 `woods-we-use` pages, `sitemap.xml`, `sitemap-cms.xml`,
`sitemap-post.xml` and `_headers`. They are the generated output of the reviewed PR #66 source change
(container-loading accuracy, certification-claim and price-figure removals, sitemap lastmod, titles, pin to #64).

The inputs every build copies from the pinned tree are unchanged:

- `files/`: tree `a7bd7cb3629b` at both revisions.
- `assets/`: tree `7374ec9dac64` at both revisions.
- `.github/workflows/site-checks.yml`: blob `6e0a4f519408` at both.
- `015ad99674249c7dc418af21415b06bc.txt` (IndexNow key): blob `c4e4ff118eeb` at both.
- `llms.txt`: blob `c1f2ece3d292` at both.
- `favicon.png`: blob `42ed03eaf114` at both.
- `cwi-og-share-1200x630.png`: blob `5eeba7f60f47` at both.

No carried input moved, so advancing the pin changes no copied file; it lets the release preflight's live-pin
check and the sitemap lastmod comparison read the tree that is actually live.
