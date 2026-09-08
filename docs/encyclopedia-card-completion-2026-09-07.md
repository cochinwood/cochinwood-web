# Encyclopedia card images — 7 September 2026

The owner requested completion of item 6, the five remaining grain-card spaces, then explicitly chose realistic AI variants based on the available originals instead of contacting outside researchers. No image-request emails were sent.

On 8 September 2026, the rights-ambiguous Neem generated card was withdrawn from directory rendering and the image sitemap pending permission. The other 27 directory cards retain their reviewed visuals in the same 4:3 frame. Anjili uses a new real, author-identified Kerala sawmill photograph by Rashid Edayur, released under CC0. Its end-grain crop and full photograph were reviewed independently. The original small research photograph and bark reference remain in its species page.

Melia dubia, Kadam and Sal use source-guided AI artwork generated with the built-in image tool. They are labelled **AI-assisted visual** and stored as `card_visual`, separately from the `images` collection of original reference photographs. Neem's corresponding asset and all of its source hashes, prompt and provenance are retained as `withheld_card_visual`, but it is not eligible to render pending written permission from the relevant rightsholder. The source records, exact prompts and licence or reuse-policy links are kept in `content/species-media.json`. These are visual reconstructions, not newly authenticated grain specimens or company stock photographs.

| Card | Reference used | Reuse and treatment |
|---|---|---|
| Melia dubia | Akshaya et al., Madras Agricultural Journal, Figure 1 untreated control; DOI 10.29321/MAJ.10.601156 | CC BY 4.0 source; AI-assisted reconstruction of broad pale wood appearance. |
| Neem | Deore et al., Plant Archives 20(2), 3399–3404 (2020), Figure 6; Nandurbar, Maharashtra specimen | **Withheld pending permission.** The publisher policy permits cited reuse, distribution and reproduction but does not establish a right to create and publish this source-guided generated derivative. Handwritten label/background were excluded in the retained artwork; fine grain is reconstructed. |
| Kadam | Haruni Krisnawati / CIFOR, 2011 Kadam monograph, Figure 5; DOI 10.17528/cifor/003396 | Current work-specific publisher page explicitly CC BY 4.0; verified in Chrome. AI-assisted close-up of broad wood appearance. |
| Sal | Baral et al., Forests 10:466 (2019), Figure 11; DOI 10.3390/f10060466 | CC BY 4.0. Source is a Nepal research specimen, not Indian/company stock. First generated version was rejected for excessive magnification; final artwork uses a wider visual field without claiming a measured anatomical scale. |
| Anjili | Rashid Edayur / Trip Unplanned, Artocarpus hirsutus logs at Kanjippura, Valanchery, Kerala | Explicit CC0 gallery. Real photograph, proportional encoding only; CSS end-grain crop, no generated detail. |

Every generated master is 1448 × 1086. Four WebP widths (320/640/960/1448) remain preserved for each generated asset; only the Melia dubia, Kadam and Sal sets provide responsive directory delivery. Anjili retains a 1600 × 2133 master with crop-aware responsive selection and a separate uncropped profile display. Its final WebP encoding was compared visually against the source at mobile DPR2.

The metadata records exact generation prompts, source URLs, licences or reuse policies, native-output hashes and original-reference hashes. The sixteen responsive WebP asset variants contain unsigned, self-declared IPTC/XMP `trainedAlgorithmicMedia` disclosure. That is deliberately not described as C2PA or Content Credentials. Native outputs, source proofs, rejected revisions and review receipts remain in `C:/Users/Edwin David/.codex/visualizations/2026/09/05/01a0708d-57f6-75a2-b691-19254be1f2a5/ai-grain-variants-2026-09-07/` and the adjoining `grain-completion-item6-2026-09-07/` folder. Project-consumed assets are versioned under `assets/photos/files/Species/`.

The original 52 source-image records and files remain intact. The new Anjili photograph raises the separate reference collection to 53.

## Publication and final validation

- Reviewed source: `fab42b8fc5102b9ef539da2db976b001a3feb6f5`.
- Publication [PR 38](https://github.com/cochinwood/cochinwood-web/pull/38), head `7ea9c39118565274a1cced4ac4f36616942be536`, merged at 08:01:20 UTC on 7 September 2026; production merge `ef44629fd2a63a18ce507dc3c9cf0cda871077a2`.
- Cloudflare Pages production deployment `ae447a2b-b25e-4701-b7f6-5af9912a15f6` completed successfully at 08:01:38 UTC. Previous production deployment `a9d4778c-89ad-4379-ae76-b3d0296334d3` is the rollback reference.
- All **1,126 baseline files** matched the reviewed prior production commit before copying; all **1,146 staged publication files** matched `dist` byte-for-byte. GitHub site checks and Cloudflare preview passed; 28 targeted preview URLs matched before merge.
- The build, site/link/schema checker, visual coverage, 84 preserved export fragments, 320 preserved asset/root checks and six image tests passed. An independent ordered-content review accepted 19 exact changes and six informational additions, with zero unreviewed or stale allowances. All 52 prior image records and bytes remain unchanged.
- Independent Chrome review passed at 320, 390, 768 and 1440 CSS pixels plus mobile DPR2: 28 distinct loaded card images, four AI-assisted labels, no empty spaces or horizontal overflow, consistent 4:3 frames, source/licence links, and working search/category navigation. The existing 145 navigation/layout cases passed earlier in the same review.
- Explicit public-URL cache invalidation succeeded at 08:03:10 UTC. At **08:03:51 UTC**, all **328 live checks** matched the built bytes, without cache-busting query strings: 254 canonical pages, 52 prior reference photos, 20 new image variants, the stylesheet and image sitemap. A normal Chrome visit also confirmed the released directory.
- Receipts: `publication-tree-proof.json`, `preview-live-proof.json`, `purge-live-proof.json`, `production-live-proof.json`, `independent-preservation-reviewed.json` and `encyclopedia-ai-integrated-independent-proof.json` in the AI variant artifact directory above.

Item 6's visual completion is live under the owner's revised AI-variant choice. No external original-photo requests were sent. This release does not establish that the four generated reconstructions are documentary grain photographs, and it does not change the separate commerce, payment or Google verification dependencies.
