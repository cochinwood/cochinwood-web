# Blog, encyclopedia, product images and spacing review

Status: published and verified in PR34, merge `4dd77b462955e332dd4802d0b1997324e7f21c74`. All 1,122 staged files matched the reviewed build; all 491 checked preview and production paths matched, including 254 canonical pages. The destination-guide follow-up is documented in `destination-guides-completion-2026-09-07.md`.

This phase addresses Edwin's repeated Blog photographs, missing encyclopedia thumbnails, five requested product/application replacements and excessive blank space. It preserves the existing brand, URLs, article content, products and enquiry behavior.

## Image ownership

The Blog phase requires exactly 157 existing articles: 48 distinct article-owned images and 109 location buying guides presented as compact regional entries. Location guides retain their complete text; the automatically inserted generic packing photograph is removed. Their social cards use the existing brand graphic and do not claim an article photograph in structured data. A directory thumbnail and the article it links to intentionally share the same image.

Four article images come from the user-authorized raw Indian industry archive. The other 44 are separately generated for their specific article subjects, with Indian industrial settings, observed material descriptions and original generation records. They are marketing or educational scenes, not documentation of company facilities, certification, stock or customer projects. Source originals and prompts are kept outside the published build. Compressed responsive WebPs preserve generated-media metadata.

Run `python tools/check_unique_images.py --scope blog` for the Blog scope. At PR34 release it correctly reported the 28 pending country guides. The approved destination-guide follow-up now makes the default full 185-owner check pass as well. This is an editorial ownership check, not a claim that no photograph can recur in a directly linked product or article preview.

## Products and encyclopedia

Three replacement product images cover film-faced shuttering plywood, container flooring plywood, and block board/flush doors. Construction and Joinery sectors use distinct application scenes. The container flooring specification caption is preserved. Exact prompts, source hashes, accepted edit history and responsive derivatives are recorded in the requested-image manifests.

All 28 encyclopedia cards gain identified references, linked to the full species page and credits. There are 52 reference images, including a historical botanical plate. Twenty-four species have wood references; Melia dubia, Neem, Sal and Kadam currently use tree or botanical references because verified, commercially reusable grain photographs are still unavailable. Generated grain is not used for species identification. Most card thumbnails fill their frame; Birch and Sal preserve their complete identification views. Full galleries preserve uncropped sources, Neem is rotated only for display, and Anjili is capped at its native resolution.

## Layout and preservation

The final `content-spacing.css` layer reduces compounded section padding on desktop Home, Industries, product groups and Blog tools. Hero, header and section-bar geometry stay under their existing shared components. Mobile Home and process-step heights are preserved. Shared desktop heroes center the heading and supporting copy together beside the image, eliminating the lopsided blank lower-left area on shorter introductions. Breadcrumbs, image dimensions and the mobile heading/image/support order are preserved.

The carry pin advances to reviewed production PR33, `b4962022cbeee7f9a08865b4e7ad8887cad6e8f8`. The intervening changes add published media and intentional redirect/header revisions already represented in source. Review confirms all 255 HTML paths, 254 canonicals, existing media, workflow and reserved root bytes remain. Only the superseded stylesheet fingerprint rolls over. The historic 84 export fragments and 320-asset preservation check remains in addition to the latest-production comparison.

## Remaining outside this phase

- The 28 country-export assignments and six redundant product-gallery placements are addressed in the destination-guide follow-up. Directly linked product previews, article thumbnails and alternate responsive markup intentionally reuse their corresponding owner image.
- Four verified species grain references remain unavailable, as named above.
- ICICI API terms/activation and approved online catalogue prices, stock and freight are separate commercial dependencies. No checkout or Merchant product feed is activated by this visual release.

Final evidence is retained in the task's visualization artifact directory, including responsive, brand, encyclopedia, Blog ownership, semantic preservation, staged-byte and live-release receipts.
