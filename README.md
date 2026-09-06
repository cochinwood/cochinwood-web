# Cochin Wood public website

The Python static-site generator for https://www.cochinwood.in, separate from the staff app at app.cochinwood.in.

The current source builds 254 canonical pages, including all 157 articles and 28 species entries, plus the supply-market directory. It retains all 16 product lines and seven timber catalogue choices. The generated sitemaps define the current route inventory.

## Build and preview

    python build.py
    python tools/preview.py --help

The build uses Python's standard library and versioned media. It builds beside `dist` and replaces `dist` only after generation succeeds. Missing or mismatched responsive candidates fail generation while preserving the previous output. `SITE_BASE` optionally sets a preview subpath.

Generated text uses LF bytes across platforms. CSS and JavaScript filenames are content-addressed. `build.py` pins the production revision supplying preserved image URLs, root discovery files and the publication workflow. Review those files before updating the pin.

## Source map

- `build.py`: templates, routes, metadata, asset registration and output.
- `content/`: page bodies, articles, species notes and market data.
- `content/export-markets.json`: the single source for export-country claims.
- `content/regional-navigation.json`, `regional_seo.py`: navigation among existing country and city guides, the supply-market directory and image sitemap.
- `assets/`: shared brand styles, responsive layout, navigation and progressive motion with reduced-motion support.
- `content/visual-media.json`, `content/editorial-media.json`, `content/species-media.json`: visual selection, descriptions, source identification and credits.
- `content/responsive-media.json`, `content/home-art-direction.json`: reviewed image sizes and same-scene homepage mobile crops.
- `assets/photos/files/`: media sources; existing public image URLs are retained. New candidate widths and hashes are checked during generation.
- `hero_layout.py`: shared inner-page hero adaptation without rewriting articles. `assets/viewport-heroes.css` budgets the visual stage against available screen height.
- `page_navigation.py`, `assets/page-navigation.*`: compact sticky section links, mobile disclosure, active section and measured header offsets. Native links work without scripting.
- `quote_form.py`, `assets/quote-form.*`: repeatable product specifications, same-tab draft recovery and backward-compatible native enquiry delivery. See [multi-product enquiries](docs/multi-product-enquiries.md).
- `site_preservation.py`: ordered content, specification, schema, form, download, link, redirect and asset comparisons with exact reviewed allowances.

The visual identity uses forest green, warm neutrals, natural wood, Poppins and Bree Serif. See [the media guide](docs/visual-media-guide.md) for licensing and image review decisions. Customer-facing captions explain products; production provenance stays in these records.

## Release checks

Run the site checker from the generated document root:

    Push-Location dist
    python ../tools/check_site.py
    Pop-Location
    python tools/check_visual_coverage.py
    python tools/check_published_preservation.py
    python -m unittest discover -s tools -p 'test_site_preservation.py'
    python -m unittest discover -s tools -p 'test_regional_seo.py'

Browser suites in `tools/test_*.cjs` cover heroes, responsive layouts, blog and encyclopedia navigation, quote journeys and consent-based measurement. Use the bundled Node/Playwright runtime and inspect each script's options. Production enquiries are intercepted in isolated regression tests. Review actual desktop/phone screenshots and measure performance with all images loaded.

Freeze production output before editing and compare the final candidate using `site_preservation.py`. Review intended text and image changes explicitly. Page counts alone do not prove content preservation.

## Publication and search

Cloudflare Pages project `cochinwood-web` serves the generated tree on `cf-live`, with no remote build step. Use a fresh publication worktree, preserve LF bytes, review the pull request and checks, then publish the tested tree. Verify the matching deployment, public routes and asset hashes, retaining the previous deployment for rollback. Never publish a source branch as the document root.

`CUTOVER-PLAN.md` and its runbook document the historical migration. Their dated counts and source revisions are not current release instructions.

The quote form uses the company `/web-lead` endpoint and Turnstile. Accepted enquiries are counted server-side. Optional Google Analytics uses the existing company container only after consent; see [website measurement](docs/website-measurement.md).

Sitemaps cover canonical pages, articles and images. After verifying public release bytes, `tools/submit_indexnow.py` submits changed canonical URLs using the existing public ownership key. It defaults to a dry run and saves receipts to avoid duplicate submissions. Search-engine receipt does not promise indexing or ranking.
