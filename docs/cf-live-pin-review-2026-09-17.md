# `cf-live` pin review — 17 September 2026

Moves the `build.py` production pin from `234822ae60d427e3b14a2a56f72bfd268b313eae` (reviewed in
`docs/cf-live-pin-review-2026-09-16b.md`) to `16360c061771a2da38adcab14880c7ad1c17b256`, the current
tip of `cf-live`.

The simplest kind of move: one publication in the window, built from source that is already on
`master`, and not one carried input changed.

## Reviewed production window

```text
16360c06 Merge pull request #78 from cochinwood/publish/price-exposure-sweep-20260916
b63670e5 Publish price-exposure-sweep-20260916 (source a141a0a9)
```

The publication names the source revision it was built from, and that revision is on `master` as
PR #77 (`674db5c7`). Cloudflare Pages reports production deployment `7a360a20` for it; the twelve
changed pages were purged on www and apex, re-fetched as an ordinary visitor and checked in both
directions — the removed figure absent, the replacement sentence present, 12/12 — and 12 URLs were
accepted by IndexNow.

## Tree and carried-file comparison

1,171 paths at both revisions: 14 modified, none added, none deleted. The 14 are the twelve hedged
blog posts, `_headers` and `sitemap-post.xml`.

Carried inputs, all unchanged:

  - `files`: `a7bd7cb3629b`
  - `assets`: `0c6c02deee9d`
  - `.github/workflows/site-checks.yml`: `6e0a4f519408`
  - `llms.txt`: `c1f2ece3d292`
  - `favicon.png`: `42ed03eaf114`
  - `cwi-og-share-1200x630.png`: `5eeba7f60f47`

Nothing this build copies from the pinned tree moved, so advancing the pin changes no published
byte. What it buys is that `cutover_preflight`'s live-pin check and the sitemap `lastmod` comparison
read the tree that is actually live.

## Two things this move also settles

**The sitemap `lastmod` seed.** `content/sitemap-lastmod-seed.json` was pinned at `103efa27` and its
own documentation says it exists only until the pin catches up: *"Once LIVE_SHA points at a
publication built with the seed, the published sitemap carries the same dates and the file can be
deleted."* That condition is now met, and `tools/seed_sitemap_lastmod.py` reports what remains.

**`HAND_EDITED_LIVE_ASSETS` stays empty.** Re-checked at this pin by re-hashing every
content-addressed file under `assets/`: 20 hashed assets, 20 named for their own bytes, 0 mismatched.
The guard that used it is still there, warning on an empty map.

## Standing item, not settled here

`.github/workflows/site-checks.yml` pins `CHECKER_SHA=4678a8f5…` (master @ 2026-08-28), and
`tools/check_site.py` has moved since. The pin is deliberate — the workflow says so at length, and
the reason is auditability: a gate that cannot say which version passed is not one you can audit
after an incident. But the cost it names ("improvements do not reach this branch until CHECKER_SHA
moves") is now three weeks deep. Bumping it means editing a file that lives only on `cf-live`, so it
belongs in a publication rather than here.
