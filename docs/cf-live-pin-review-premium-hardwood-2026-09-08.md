# `cf-live` pin review for Premium Hardwood preparation — 8 September 2026

This record supports the `build.py` production pin move from
`255aeed1efc3861bc4264658711c2e1c58eb49e8` to
`a9178b958c5de667f8ddaadff9ab5bbc212f199e`. The destination is the verified
PR40 production merge; the source branch does not merge or deploy it again.

## Reviewed production window

The published tree differs in exactly 22 paths: five generated HTML files,
three sitemap files, `_headers`, `woods-we-use.html`, `woods-we-use/neem.html`,
and twelve Species image files. These are the already reviewed PR40 release:
the four destination/markup fixes, changed-only sitemap dates, Neem withholding
and disclosure, image-sitemap exclusion, and provenance-bearing Kadam, Melia
dubia and Sal image bytes.

PR39's sale-rate suppression remains present because PR40 was built from the
source lineage that already contained it. This pin move does not restore a
rate disclosure or an older generated page.

## Carried-file evidence

The `files/` tree contains 846 paths at both revisions. Twelve blobs changed:
the 320, 640, 960 and master WebPs for Kadam, Melia dubia and Sal. Each live
blob's SHA-256 was compared with the corresponding file under
`assets/photos/files/Species/`; all twelve pairs are equal. These are the
reviewed provenance updates, and the source build writes the same bytes after
the carried tree is copied.

The other five carried inputs are unchanged and retain these Git blobs:

- `.github/workflows/site-checks.yml`: `6e0a4f51940820d64a239eefda0ff216698d156e`
- `015ad99674249c7dc418af21415b06bc.txt`: `c4e4ff118eeba37b597c2ccbf8bafaa60999b874`
- `llms.txt`: `c1f2ece3d292fce002a59ea66e91f383c05ea34a`
- `favicon.png`: `42ed03eaf114a97d945d7b2cd99f7bf183563f86`
- `cwi-og-share-1200x630.png`: `5eeba7f60f47a4f07f20121f7fe2145a467e0a7b`

The carried inventory therefore remains 851 files. The pin now names the exact
verified production parent for the Premium Hardwood publication delta.

## Reproduction

```powershell
git fetch --prune origin
git diff --name-status 255aeed1efc3861bc4264658711c2e1c58eb49e8 a9178b958c5de667f8ddaadff9ab5bbc212f199e
git diff --name-status 255aeed1efc3861bc4264658711c2e1c58eb49e8 a9178b958c5de667f8ddaadff9ab5bbc212f199e -- files
python build.py
python tools/cutover_preflight.py HEAD
```
