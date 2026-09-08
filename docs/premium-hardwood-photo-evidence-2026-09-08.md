# Premium Hardwood family-image evidence — 8 September 2026

This is a private draft catalogue evidence record. Owner authorization to publish a representative family image is complete. The selected replacement is tracked in the website source and prepared on a quote-only page; production publication still depends on the separate reviewed release. This record does not activate a product, purchase flow or Merchant offer.

## Owner-approved original source

| Field | Verified value |
|---|---|
| Owner response | “Yes, please edit it and make the pic look better for sales.” |
| Question answered | “Does this plywood accurately represent the Premium Hardwood being launched, and may CWI publish this photograph?” |
| Approval recorded | `2026-09-08T16:53:15+05:30` |
| Archived filename | `cwi_wa_482_938x1280.jpg` |
| Company archive location | `marketing/photo-bank/raw/cwi_wa_482_938x1280.jpg` |
| SHA-256 | `9115bc38f8524cdf217136b834634c98cef1c7b4ee5c2a529c95902d8a6cb1df` |
| File identity | 63,026-byte, 938 × 1280 JPEG |
| Approved scope | Publication of one accurate shared representative Premium Hardwood family photograph for the proposed 12 mm and 18 mm SKUs, with a sales-oriented edit authorised |

The original file was rehashed from the known company photo archive for this receipt. The owner's answer authorizes CWI to publish the representative family photograph and to use the requested sales edit. The approval does not state that the photograph visibly distinguishes 12 mm from 18 mm.

## Rejected first sales edit

| Field | Verified value |
|---|---|
| Filename | `premium-hardwood-sales-edited-2026-09-08.png` |
| SHA-256 | `955a7a9fccee7b5fe47c9d55cca19d591d376aa8f1d7b09069db6461d8b72487` |
| File identity | 1,727,887-byte, 1074 × 1465 RGB PNG; no embedded PNG metadata |
| Method | OpenAI built-in image generation tool editing the approved original reference |
| Presentation | AI-edited sales presentation, not an untouched documentary photo |
| Current evidence location | Dated `hardwood-sales-photo` folder in the parent evidence workspace |
| Publication status | Rejected by the owner before publication; no prepared or live public URL |

The parent evidence folder's README retains the approval, original hash, first-edit prompt and method. The rejected first edit is not retained in the public asset tree and is not referenced by customer-facing output.

## Selected replacement presentation

| Field | Verified value |
|---|---|
| Filename | `premium-hardwood-hero-v2-2026-09-08.png` |
| SHA-256 | `65fb08829dc376f9064281654ed4e9115d594b069472a65b2556368c3c1d778a` |
| File identity | 2,191,872-byte, 1448 × 1086 RGB PNG |
| Method | OpenAI built-in image generation tool editing the approved original reference |
| Selection | Parent viewed the replacement and the user instructed the website worker to use it as the new Hardwood hero |
| Source location | `C:/Users/Edwin David/.codex/generated_images/01a07c1c-fa7f-7d52-a56c-f95a826950e0/exec-40942a85-b6ab-4b10-a87c-2cb7f3a77560.png` |
| Tracked reviewed artifact | `assets/photos/files/Premium-Hardwood/premium-hardwood-hero-v2-2026-09-08.png` |
| Optimized public master | `premium-hardwood-hero-v2-2026-09-08.webp`; 199,250 bytes; SHA-256 `7e5821f82dda291d4f008359c3fbaff7e097166c2111ebde53d3fca4edad69ea` |
| Responsive derivatives | 320, 640, 960, 1200 and 1448 pixels wide; all retain the full 4:3 composition without cropping |
| Prepared public URL | `https://www.cochinwood.in/files/Premium-Hardwood/premium-hardwood-hero-v2-2026-09-08.webp` (not live until the publication release is merged) |

The exact original remains tracked at `assets/photos/files/Premium-Hardwood/premium-hardwood-family-original-2026-09-08.jpg` for product-reference evidence. The customer page contains no owner-approval, generation, internal review or provenance wording. It does not link either image to a raw-file dead end.

## Claim and use boundaries

- The image applies to both `prem_hw_gurjan_12` and `prem_hw_gurjan_18` as one family representation. It does not show which thickness is pictured and must not be described as an exact 12 mm or exact 18 mm photograph.
- Image details do not establish core construction, layer count, face or back species, glue grade, finished dimensions, tolerances, certification, stock, premises or a customer shipment.
- The owner separately confirmed that both proposed thicknesses have a full hardwood core. That fact comes from the owner decision record, not from either image.
- Exact face/back construction, glue grade, finished dimensions, tolerances and supported certification remain unconfirmed.
- The reviewed original and selected replacement bytes are copied into proper tracked website asset locations and rehashed. The site build no longer depends on a Codex generated-cache path.
- Owner authorization and publication state remain separate. `image_approved` is true for both proposed Hardwood records. The intended production paths are recorded as prepared URLs, while `actual_product_photo_url` remains null until the reviewed publication release is merged and verified. Catalogue activation and Merchant activation remain false; publishing the page and files does not automatically change those gates.

## Quote-intent compatibility

The current live app baseline was inspected read-only at commit `5c17fce7b59efe049a8a2bcf7356d8410a7d7461`. Its enquiry route accepts `product` as a trimmed string up to 100 characters and does not apply a product enum. A local, network-free validation against that exact route accepted `Premium Hardwood Plywood`, retained source page `/premium-hardwood-plywood`, and produced readable staff-facing text. No enquiry was submitted and no app files were changed. The website therefore sends the readable product name through the existing schema without mapping Hardwood to another product.

## Decision-document coordination

Goodall's decision document remains owned by its app worktree and was reviewed read-only. Its coordinated update should record that publication approval is complete, preserve the unpublished URL state, record the original, rejected-edit and replacement hashes, retain the thickness and claim limits above, and keep identifiers and purchase/Merchant activation pending. Customer-facing pages must not publish this workflow record.
