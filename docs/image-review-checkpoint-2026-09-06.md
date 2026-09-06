# Website image review checkpoint — 6 September 2026

Historical checkpoint at source commit `4f894320`: local preview only at that time. See [the subsequent Blog, encyclopedia and spacing release review](blog-encyclopedia-spacing-release-2026-09-06.md) for the next release scope and its verification. This checkpoint remains a record of the earlier incomplete full-site migration.

## Integrated and checked locally

- Four distinct original Indian industry photographs from the user-authorized company raw archive replace four technical-article leads and their matching directory/share images. The originals match archived Git blobs; no retouching, source cropping, mark removal or upscaling was used. See [provenance and placements](indian-industry-image-replacements.md).
- Seven commercially reusable, identified wood references were added for birch, eucalyptus, jackwood, venteak, matti, anjili and the Populus group. All 45 previous image records are preserved. Anjili's small source is capped at its native 370px width. See [reference sources and remaining gaps](species-grain-completion.md).
- The 109 location buying guides have a compact text directory with region labels. Their mechanically injected repeated packing photograph is omitted; article prose, section IDs, tables, destinations and navigation remain. OG/Twitter use the existing branded share card; their BlogPosting schema no longer claims the removed photograph. This is the recommended local preview while the optional design preference remains unanswered.
- Main page heroes and existing public product families are retained.

## Verification

The rebuilt site has 254 canonical pages, 255 HTML files and 157 blog articles. Its internal-link, canonical/schema, visual-coverage and published-asset preservation checks pass. The four new industry figures and seven new wood references pass 22 Chrome checks at 390px and 1229px, including image loading, full-frame containment, credits and the native-width limit. Their rendered screenshots were reviewed.

Focused checks confirm all 109 location article bodies and all 157 directory destinations are retained. Browser checks cover search/filter URL restoration, no horizontal overflow, and metadata for all 113 approved image/text owners. Six ownership unit tests and three location-preview source tests pass.

Image sitemap output contains 138 pages, 278 placements and 103 unique image URLs, with no missing or external image assets. Its lower page count is the intentional removal of the 109 repetitive decorative location leads; all article canonicals remain in the normal sitemap.

The build still reports the existing pinned-live-head and documented redirect warnings. `LIVE_SHA` was not changed. The published preservation check confirms 84 export fragments and 320 production assets/root files remain intact.

## Still incomplete

1. **72 editorial/export image assignments** remain unapproved: 44 technical articles and 28 export country pages. `tools/check_unique_images.py` intentionally returns failure for these assignments. The four new photographs do not establish that all current website images are suitable or unique.
2. **Other repeated or inappropriate product, application and homepage photographs** remain in the broader inventory. The ownership gate currently covers the explicit editorial/export migration; it is not a claim of whole-site photographic uniqueness.
3. **Four wood-grain references** still need suitable commercially reusable photographs or verified company samples: Melia dubia, neem, sal and kadam. Botanical pictures or generated grain do not satisfy these gaps.
4. Complete the remaining media decisions and run the full release review before publication. Preserve functional identity reuse, such as one article's directory thumbnail linking to that same article; do not reuse its photograph for an unrelated article.

## Related commercial dependencies

Commercial/packing plywood has been removed from the proposed online launch catalogue. Four standard BWR/BWP variants remain proposals; actual prices, stock, Kerala freight and service terms still need approval. No paid checkout or Merchant product feed has been activated.

The authorized ICICI request was sent on 6 September 2026 at 22:06:34 IST. Direct bank-account UPI has published zero transaction charges, but API activation and written setup/recurring/service terms remain pending. See [ICICI readiness](icici-upi-integration-readiness.md) and [catalogue plan](kerala-online-catalogue-plan.md). Do not resend the already-sent request.
