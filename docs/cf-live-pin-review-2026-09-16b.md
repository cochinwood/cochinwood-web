# `cf-live` pin review — 16 September 2026 (second move)

Moves the `build.py` production pin from `f906f6196f1648954ad7f8ff6ade5e3b09473d68` (reviewed in
`docs/cf-live-pin-review-2026-09-16.md`) to `234822ae60d427e3b14a2a56f72bfd268b313eae`, the current
tip of `cf-live`.

This is the routine counterpart to the last one. The window contains a single publication — this
repository's own, built from reviewed source that is already on `master` — and it is the move that
lets `HAND_EDITED_LIVE_ASSETS` be deleted.

## Reviewed production window

```text
234822ae Merge pull request #76 from cochinwood/publish/audit-ui-source-reconstruct-20260916
44a51c41 Refresh publication of audit-ui-source-reconstruct-20260916 (source 2edea7cd)
e3eb31d4 Publish audit-ui-source-reconstruct-20260916 (source 0f599098)
```

Both content commits name the source revision they were built from, and both of those are on
`master` (PR #75, merged as `a5e3afa2`). Cloudflare Pages reports production deployment `41a9b61b`
for `234822ae`, and the changed pages were purged on www and apex, verified live as an ordinary
visitor, and submitted to IndexNow (255 URLs accepted, receipt 2026-09-16T13:04:17Z).

## Tree and carried-file comparison

1,168 paths at the old pin, 1,171 at the new one: 3 added, 261 modified, none deleted. The three
additions are the correctly-named replacements for assets that had been edited in place —
`assets/bundle.23544f2e.css`, `assets/site.6fee576e.js`, `assets/quick-inquiry.547fdf03.js`. The 261
modifications are the 256 pages that now reference them, `_headers`, and the four repaired legacy
asset files.

Carried inputs:

  - `files`: unchanged at `a7bd7cb3629b`
  - `assets`: **CHANGED** `0aea90f06a09` -> `0c6c02deee9d`
  - `.github/workflows/site-checks.yml`: unchanged at `6e0a4f519408`
  - `llms.txt`: unchanged at `c1f2ece3d292`
  - `favicon.png`: unchanged at `42ed03eaf114`
  - `cwi-og-share-1200x630.png`: unchanged at `5eeba7f60f47`

`assets` moved for the reason above, and that movement is the point of this pin move.

## The repair map is retired here

`HAND_EDITED_LIVE_ASSETS` existed because four hashed assets on `cf-live` served bytes their names
did not describe, and `assets/` is carried into every build from the pin. Publishing PR #76 restored
all four. Verified independently against the new tip, by re-hashing every content-addressed file in
`assets/` and comparing with the hash in its own name: **20 hashed assets, 20 match, 0 mismatch.**

So the map is emptied at this pin — there is nothing left for it to repair. The guard that used it,
`_named_for_its_own_bytes()`, is deliberately KEPT with an empty map: it now does nothing except warn
loudly the next time a carried asset's name stops describing it, which is the failure that cost a day
to find. An empty map with a live guard is the state this should stay in.

## Verification

`python build.py` — clean, and the two stale-pin warnings are gone.
`python -m unittest discover -s tools` — 127 tests, OK (126 before; this release adds one).
`tools/check_site.py` — OK.
`tools/cutover_preflight.py` — see the release branch; the live-pin check now reads
`pin 234822ae60d4, tip 234822ae60d4`.
