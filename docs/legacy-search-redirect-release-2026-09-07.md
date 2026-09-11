# Legacy search redirect repair — 7 September 2026

The refreshed Google Search Console not-found report contained four legacy page URLs still returning HTTP 404. The Chennai, Vizag and Pune pallet/crate routes now redirect permanently to `/plywood-pallets`, consistent with the established Mumbai/Delhi/Ahmedabad route family. Retired `/blogs/south-india/page/*` pagination redirects to the current searchable `/blogs` directory.

All 70 reported examples were checked. The other 64 page URLs already redirect to HTTP 200. The two remaining asset-directory roots properly return 404 and were not redirected over their real image files. Search reports need a later recrawl to reflect the repairs.

## Verified publication

- Source: `5805e5c285b2d39fd39414aaf8ab547ba83f41f9`.
- Publication PR: https://github.com/cochinwood/cochinwood-web/pull/37, merged 7 September 2026 at 06:56:39 UTC.
- Reviewed publication head: `f5182ae4efecafe3fce9b2b2397abcac506b2900`; production merge: `f2de8f96e3bc7ed55e832abc2109bc34572ed6a0`.
- Cloudflare Pages production deployment: `a9d4778c-89ad-4379-ae76-b3d0296334d3`, successful at 06:57:00 UTC.
- **Only `_redirects` changed. All 1,125 other files, including every page, image and stylesheet, are byte-for-byte unchanged.** All 1,126 publication files matched the generated candidate before committing.
- Exactly four rules were added; the existing rule order and destinations remain preserved. Counts are 115 total / 29 before the first wildcard / 86 within the supported 100-rule wildcard window. No current page is shadowed.
- Full static check passed: 255 HTML files, 254 canonicals, 15,669 internal links and 799 structured-data blocks. Visual coverage and 84 historical export fragments / 320 original asset checks passed. Ordered-content comparison accepted one exact reviewed redirect delta with zero outstanding differences.
- GitHub's site check and Cloudflare preview passed. Preview and live checks each verified six redirect cases plus four unchanged key pages with exact destination bytes.
- Cached error responses were purged for ten explicit legacy URLs across the two public hostnames. The connector lacked cache-purge scope; the existing company deployment credential successfully performed the same narrow operation after re-verifying the zone/account. No staff hostname or whole-zone purge was used.

Evidence lives under `C:/Users/Edwin David/.codex/visualizations/2026/09/05/01a0708d-57f6-75a2-b691-19254be1f2a5/`, including `seo-redirect-live-proof-2026-09-07.json`, `seo-redirect-preview-proof-2026-09-07.json`, `seo-followup-byte-proof-2026-09-07.json`, `seo-followup-preservation-final-2026-09-07.json` and `seo-redirect-cache-purge-2026-09-07.json`.

Rollback reference is the preceding production deployment `3e4ac3bc-64ce-4dcf-ab9c-efde097fad3b`. No design, product data, form, image or staff application changed in this release.
