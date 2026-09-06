# Commerce preparation completed — 7 September 2026

This receipt covers the work that can be prepared and tested without approved selling prices or ICICI API access. It is a **local staging delivery**, not a public shop launch. The production website and staff app have not been deployed or changed in this run.

## Review now

- [Shop preview](http://127.0.0.1:8891/commerce-preview/)
- [Staff order preview](http://127.0.0.1:8891/commerce-preview/staff.html)
- [Catalogue and launch review](http://127.0.0.1:8891/commerce-preview/readiness/)

The preview runs on this PC only. Use **Test checkout** for fictional prices/stock and the example contact details. **Actual setup** deliberately has blank commercial values and refuses checkout. Existing product-family images demonstrate layout; exact sold-product image approval remains part of launch review.

## Delivered

| Area | Completed preparation |
|---|---|
| Shop | Two premium families/four variants, deep links, multiple-product/thickness basket, quantity changes/removal, item-only draft persistence, delivery eligibility/charge/window, contact/address and optional GSTIN, review and recorded order |
| Orders | Durable SQLite using D1-shaped service statements; server-calculated prices; atomic stock reservations; immutable catalogue, policy, delivery and price snapshots; order access tokens; safe retries and duplicate protection |
| Payment rehearsal | Simulated success, failure, cancellation, expiry and full refund; late/conflicting results rejected; recovery after a committed response is lost; no bank calls or payment links |
| Stock | Concurrent last-sheet protection, all-or-nothing mixed-order reservation, unpaid hold expiry; refunds require stock review rather than automatic restocking |
| Staff review | Owner, assigned Sales, unrelated Sales and Purchase test views; server-enforced visibility and simulation permissions; local notification outbox for the two owners, assigned salesperson and synthetic buyer |
| Commercial configuration | Separate incomplete company proposal and fictional test fixture; review table, explicit approval requirements, postcode/quantity bands and policy drafting structure |
| Merchant preparation | Local XML/TSV exporter plus matching Product/Offer data from one catalogue; default review-only output; synthetic/missing/unapproved/undeliverable offers blocked; stale export invalidated on malformed configuration |
| SEO | Current sitemap/robots and sampled canonical checks, authenticated Google/Bing/Analytics report review with actual report dates; no new issue found in that bounded live technical sample |
| Image sourcing | Additional identified/rights review for four wood-grain gaps; no unsuitable or unlicensed replacement added |

The staff review is a separate local preview. It is **not installed in `app.cochinwood.in`**. Its outbox contains notification previews; **no emails were sent**. Real staff authentication, assignment, delivery transport and production order integration are recorded as launch work, not represented as complete.

## Verification

- **190 backend assertions** passed, including eight separate SQLite connections contending for the final sheet, multi-item rollback, duplicate/conflicting events, exact postcode validation, role isolation, durable reopen and full server restart.
- **19 Merchant preparation tests** passed. An independent reviewer reproduced and verified fixes for stale feeds after invalid input, undeliverable minimum quantities and whitespace-only identifiers.
- **12 Chrome browser journey groups** passed, including mixed baskets, stale-response races, input validation, GSTIN roundtrip, uncertain payment recovery, role scopes, refund stock review, keyboard use and responsive layouts at **320, 390, 768, 1229 and 1440 pixels**.
- Screenshots were inspected. Product-image fixed-height stretching was corrected and aspect ratios are now measured by the browser checks.
- Browser external requests: **0**. Browser exceptions: **0**. Bank calls: **0**. Emails sent: **0**.
- Production staff-app collector: **68 allowlisted files; zero commerce files**. Production `webapp/` has no diff from its starting commit.
- Production website builder, content, images, navigation and quotation source have no diff from starting source `d539232ca7957852749d3194e7923c1a042fd43a`; current `dist/` contains no commerce or Merchant feed files. Existing production pages were not rebuilt or published by this task.

Backend source is in `C:/Users/Edwin David/cochin-wood-document-studio/prepared-commerce/`; its runbook, API contract and verification receipt are in that repository's `docs/commerce/`. The backend preparation was saved in commit `cf96eef` on branch `prepare/kerala-commerce-2026-09-07`. Website preview source is in this repository's `commerce-preview/`, on the same branch name. Both are isolated source branches; they are not production releases.

Browser proof and screenshots are saved in:

`C:/Users/Edwin David/.codex/visualizations/2026/09/05/01a0708d-57f6-75a2-b691-19254be1f2a5/commerce-preview/`

`browser-proof.json` records the verification timestamp and tested source hashes. The backend receipt records source hashes and its verification time. `commerce-preview/readiness/readiness.json` records the company configuration hash and outstanding field approvals. Its field-level blockers are missing launch inputs, not newly discovered defects in the live website.

## Still needed for launch

1. Company confirmation of the four exact variants, tax-inclusive prices, tax treatment, online stock, order limits and actual product photos/identifiers.
2. Actual Kerala serviceable PIN codes, freight and arrival windows, unloading, damage, cancellation and refund terms. The commercial review is in `docs/commerce-launch-review.md`.
3. ICICI activation, official technical specifications, credentials, UAT and written commercial terms. The bank's **E099605724** acknowledgement does not establish API access or zero total fees.
4. The actual bank adapter, staging D1 and authenticated staff-app integration, production notification transport/expiry scheduling and final launch checks. The tested local service provides the order foundation; it does not yet implement these production connections, partial fulfilment or partial bank refunds.
5. Publish only approved purchasable products, verify page/checkout/feed parity, then submit to Merchant Center and await review. The prepared exporter has not submitted anything.
6. Google Business case **1-6734000040756** remains awaiting the verification route/support response and authorised on-site verification.
7. Verified commercial-use wood-grain photographs for **Melia dubia, Neem, Sal and Kadam**. Botanical references remain available. The completed search does not prove no suitable source exists elsewhere.
8. Complete post-release reporting periods for meaningful search/enquiry comparisons. The daily monitoring automation is already active; current dated findings are in `docs/commerce-preparation-seo-image-check-2026-09-07.md`.

An MCQ was asked about preparing proposed online prices from the current staff selling rate card versus separate online prices or holding launch. Until the answer and subsequent price approval, no historical quoting rate is promoted to a live retail offer.
