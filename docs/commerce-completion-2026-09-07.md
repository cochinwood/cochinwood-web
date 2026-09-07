# Commerce staging progress — 7 September 2026

**Price approval update, 7 September 2026:** the owner approved Premium Hardwood 12 mm at ₹2,794.24 and 18 mm at ₹3,209.60 per nominal 8 × 4 ft sheet, including 18% GST and excluding freight. These exact amounts are recorded in the local proposed configuration. This closes the two sheet-price and product-GST decisions in the earlier receipt below; stock, other commercial approvals and purchasing remain pending. Internal app rates are unchanged.

The isolated commerce implementation is deployed and verified on the authenticated staff staging application through **build 597**, including the corrected catalogue approval labels. The customer shop remains a local preview; production commerce and real payments remain disabled. This is a staging receipt, not a public shop launch.

The first proposed launch is **Premium Hardwood in 12 mm and 18 mm, nominal 8 × 4 ft sheets**. Both Marine variants are inactive until their exact core construction is confirmed. They are excluded from the actual shop selection and future Merchant export. The separate four-variant synthetic fixture remains available for multi-item and concurrency tests; it does not approve any commercial offer.

## Review now

- [Shop preview](http://127.0.0.1:8891/commerce-preview/)
- [Authenticated staff staging app](https://staging-app.cochinwood.in/)
- [Local staff test preview](http://127.0.0.1:8891/commerce-preview/staff.html)
- [Catalogue and launch review](http://127.0.0.1:8891/commerce-preview/readiness/)

The customer preview runs on this PC only. Use **Test checkout** for fictional prices/stock and the example contact details. **Actual setup** contains the two unapproved Hardwood options and refuses checkout. The remote staff staging app uses existing staff authentication and an isolated commerce database. Existing product-family images demonstrate layout; exact sold-product image approval remains part of launch review.

## Delivered

| Area | Completed preparation |
|---|---|
| Shop preview | Two active proposed Hardwood thicknesses, Marine purchase hold, deep links, multiple-product/thickness basket, quantity changes/removal, item-only draft persistence, delivery eligibility/charge/window, contact/address and optional GSTIN, review and recorded synthetic order |
| Orders | Dedicated remote Cloudflare D1 staging ledger and a shared local test core; server-calculated prices; atomic stock reservations; immutable catalogue, policy, delivery and price snapshots; transaction guards for concurrent catalogue changes; order access tokens and safe retries |
| Payment rehearsal | Simulated success, failure, cancellation, expiry and full refund; late/conflicting results rejected; recovery after a committed response is lost; no bank calls or payment links |
| Stock | Concurrent last-sheet protection, all-or-nothing mixed-order reservation and verified scheduled staging hold expiry; refunds require stock review rather than automatic restocking |
| Authenticated staff review | Online orders integrated with the actual staff shell in staging; editable role permissions, assigned-order and alias scopes, oversight permissions, audited assignment and owner-only synthetic payment rehearsal |
| Notification adapter | Existing company mail transport integrated with a separate durable commerce delivery ledger; recipient/claim guards, bounded retry of known failures and no automatic retry of unconfirmed sends; staging and synthetic events cannot send email |
| Commercial configuration | Separate incomplete company proposal and fictional test fixture; review table, explicit approval requirements, postcode/quantity bands and policy drafting structure |
| Merchant preparation | Local XML/TSV exporter plus matching Product/Offer data from one catalogue; default review-only output; synthetic/missing/unapproved/undeliverable offers blocked; stale export invalidated on malformed configuration |
| SEO | Current sitemap/robots and sampled canonical checks, authenticated Google/Bing/Analytics report review with actual report dates; no new issue found in that bounded live technical sample |
| Image sourcing | Additional identified/rights review for four wood-grain gaps; no unsuitable or unlicensed replacement added |

The authenticated integration is available in **staging**, with synthetic records separate from both staff databases. Production commerce remains off. Its outbox records are notification previews; **no commerce emails were sent**. The production notification adapter still needs its controlled delivery review and deliberate production configuration before it can be enabled.

## Verification

- **217 core assertions** and **102 actual-Worker integration assertions** passed in the current app source receipt. Coverage includes eight separate SQLite connections contending for the final sheet, multi-item rollback, catalogue-change races, immutable snapshots, signed staff identities, role/alias isolation, production simulation refusal and notification batches beyond 100 events. The app suite also passes without a sibling website checkout by using bundled fixtures.
- **13 remote D1 rehearsal checks** passed. Subsequent SELECT-only verification confirms all **11 expected database triggers** and the staging environment marker. The staging cron receipt confirms an unpaid synthetic order expired and its held stock was released without a manual expiry call or external notification.
- **20 Merchant preparation tests** passed, including exclusion of held Marine offers. An independent reviewer reproduced and verified fixes for stale feeds after invalid input, undeliverable minimum quantities and whitespace-only identifiers.
- The updated local preview passed **12 Chrome browser journey groups**, including the Marine hold, mixed baskets, stale-response races, input validation, GSTIN roundtrip, uncertain payment recovery, role scopes, refund stock review, keyboard use and responsive layouts. The actual staff shell passed **11 Chrome scenario groups**, including the backend's real readiness response shape. Build 597 was separately verified in the authenticated remote staging Chrome session: order records, readiness labels and the Marine-held configuration loaded correctly after the new cached shell was adopted.
- Both build-597 deployment phases passed **221 Node suites and 1,153 Python tests**, with all **66 historical export-order price comparisons** unchanged. Source `235675edd6456e93395aaef1130c76600e973996` is recorded in the private staff-app release receipt. Staging deployment does not enable public checkout.
- Screenshots were inspected. Product-image fixed-height stretching was corrected and aspect ratios are now measured by the browser checks.
- The local browser baseline recorded **zero external requests and zero browser exceptions**. Commerce tests and staging rehearsal made **zero bank calls and zero real email sends**. Remote staging verification does use the staging application and dedicated Cloudflare D1; it must not be described as entirely local.
- The production deployment configuration keeps commerce disabled and has no commerce database binding. Production checkout, payment and notification enablement remain separate launch steps.
- The customer commerce preview and prepared Merchant exports have not been published to the production website. Existing public product, enquiry and reference pages retain their current purpose.

The canonical backend core is in the staff app's `webapp/routes/commerce-core.js`; the local harness shares that implementation through `prepared-commerce/service.mjs`. Its API contract, staging infrastructure, current integration verification and cron receipt are maintained in the private staff-app repository under `docs/commerce/`. Website preview source remains in this repository's `commerce-preview/`. Company rate evidence and the approval packet are kept in private staff-app documentation, not copied into this public website repository.

Browser proof and screenshots are saved in:

`C:/Users/Edwin David/.codex/visualizations/2026/09/05/01a0708d-57f6-75a2-b691-19254be1f2a5/commerce-preview/`

`browser-proof.json` records the verification timestamp and tested source hashes. The backend receipt records source hashes and its verification time. `commerce-preview/readiness/readiness.json` records the company configuration hash and outstanding field approvals. Its field-level blockers are missing launch inputs, not newly discovered defects in the live website.

## Still needed for launch

1. Company confirmation of the **two Hardwood variants**: exact construction/dimensions, tax-inclusive prices, selling entity and tax treatment, allocated online stock, order limits and actual product photographs/identifiers. Marine remains held and needs no approval to finish the initial Hardwood launch.
2. Actual Kerala serviceable PIN codes, freight and arrival windows, unloading, damage, cancellation and refund terms. The commercial review is in `docs/commerce-launch-review.md`.
3. ICICI activation, official payment/callback/status/refund specifications, credentials, UAT and approved written commercial terms. The existing bank acknowledgement does not establish API access or zero total fees.
4. The real payment endpoint/bank adapter and production launch integration, including the production ledger, reviewed role grants, expiry configuration, controlled commerce-email delivery review and final end-to-end payment/reconciliation/refund checks. Staging D1, authenticated staff integration, the notification adapter and scheduled staging expiry are already implemented and verified. Partial fulfilment and partial bank refunds are not implemented by the synthetic full-refund rehearsal.
5. Publish only approved purchasable products, verify page/checkout/feed parity, then submit to Merchant Center and await review. The prepared exporter has not submitted anything.

Separate from the Hardwood checkout launch: Google Business still needs an available verification route and authorised on-site participation; natural wood-grain references for **Melia dubia, Neem, Sal and Kadam** need verified samples or commercial rights; and meaningful search/enquiry comparisons need complete reporting periods. Existing botanical references remain available. These do not reopen the already completed public imagery, navigation or sitemap work. Current dated search findings are in `docs/commerce-preparation-seo-image-check-2026-09-07.md`.

Current rate evidence has been prepared privately for owner review. No stored reference rate is promoted to a live retail offer without explicit commercial approval.
