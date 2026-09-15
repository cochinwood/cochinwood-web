# `cf-live` pin review — 15 September 2026 (second)

This record licenses the `build.py` production pin move from
`7d588f16b0036b5f4b825ac96b4d8df78d99dff4` (production merge of PR #62, reviewed in
`docs/cf-live-pin-review-2026-09-15.md`) to
`103efa27393106b7e58836a616c49d271e5fda56`, the production merge of PR #64.

## Reviewed production window

```text
103efa27 Merge pull request #64 from cochinwood/publish/cable-drums-is-10418-20260915
fed0caf1 Publish IS 10418 on the cable drums page
```

`git log 7d588f16..103efa27` lists only these two commits. `103efa27` has parents
`7d588f16` and `fed0caf1`, so the window contains one publication: `fed0caf1`.

The Cloudflare Pages production deployment for `103efa27` was not re-checked from the worktree
that wrote this record, which has no Cloudflare access. Confirm it in the `cochinwood-web` project
before relying on this record for a release.

## Tree and carried-file comparison

`git ls-tree -r --name-only` reports 1,168 paths at both revisions. `git diff --name-status
7d588f16 103efa27` reports none added, none removed and 3 modified: `_headers`,
`plywood-cable-drums.html` and `sitemap-cms.xml`. They are the generated output of the reviewed
PR #65 source change (IS 10418 on the cable drums page and in its Product markup). No `assets/`
path changed.

The inputs every build copies from the pinned tree are unchanged (`git rev-parse <rev>:<path>`):

- `files/`: tree `a7bd7cb3629b` at both revisions.
- `.github/workflows/site-checks.yml`: blob `6e0a4f519408` at both.
- `015ad99674249c7dc418af21415b06bc.txt` (IndexNow key): blob `c4e4ff118eeb` at both.
- `llms.txt`: blob `c1f2ece3d292` at both.
- `favicon.png`: blob `42ed03eaf114` at both.
- `cwi-og-share-1200x630.png`: blob `5eeba7f60f47` at both.

No carried input moved, so advancing the pin changes no copied file. It lets the release
preflight's live-pin check pass and lets the sitemap `<lastmod>` comparison
(`sitemap_lastmod.py`) read the tree that is actually live, so the cable drums page is no longer
redated on every build.

## Commands

```text
git log --format='%h %s' 7d588f16b003..103efa273931
git log -1 --format='%h %P' 103efa273931
git ls-tree -r --name-only 7d588f16b003 | wc -l
git ls-tree -r --name-only 103efa273931 | wc -l
git diff --name-status 7d588f16b003 103efa273931
git rev-parse 7d588f16b003:files 103efa273931:files
```
