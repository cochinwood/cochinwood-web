# Online shop commercial review

Prepared 7 September 2026. This is an internal review document, not published customer terms.

## Confirmed direction

Selected standard plywood sheets, Kerala delivery initially, with custom/bulk/export orders remaining quotations. Commercial/packing plywood is excluded from the proposed online catalogue. Investigate the existing ICICI merchant UPI relationship first. Google Pay can be a customer UPI option only through the bank-supported flow. No fees, bank activation or live checkout are represented as approved.

The initial proposed purchase options are **Premium Hardwood, nominal 8 × 4 ft, in 12 mm and 18 mm**. The proposed Gurjan BWR (MUF) construction, exact finished dimensions, tolerances and any grade/certification claims still need confirmation for these sold variants.

**Both Marine variants are held inactive until their exact core construction is confirmed.** They are excluded from the actual shop selection and future Merchant export. No Marine price, stock or photograph approval is required for the initial Hardwood launch. The separate synthetic four-variant fixture remains solely for test coverage.

## Implementation status

### Owner decisions added on 7 September

The owner selected **invoice payment with verified credit before fulfilment**. Staff will confirm freight, then the customer will accept the full invoice before paying. This is the first-launch payment direction. A screenshot, UPI-app return or customer-entered transaction reference cannot mark an order paid.

### Owner decision added on 13 September: Bharat Connect via Zoho Books

The owner decided to use **Bharat Connect for Business via Zoho Books** instead of a direct ICICI UPI integration. Bharat Connect is already **ACTIVE** in Cochin Wood's Zoho Books account (GSTIN: `32AAJCC9689H1Z5`, B2B ID: `CWIPL`, powered by Zoho Payment Technologies Pvt Ltd and NPCI Bharat BillPay Ltd). When staff issues an invoice with confirmed freight, it is presented on the Bharat Connect network; customers can pay via UPI (BHIM, Google Pay, PhonePe, Paytm, CRED), Net Banking, or NEFT/RTGS; and Zoho Books reconciles the payment automatically without manual bank-statement review. See [Bharat Connect readiness](bharat-connect-payment-readiness.md). Direct ICICI merchant API onboarding is superseded.

The owner requested a review table using the app's current rates **plus ₹20 per square foot**, then explicitly approved the exact two Hardwood prices including **18% GST**: 12 mm ₹2,794.24 and 18 mm ₹3,209.60 per nominal 8 × 4 ft sheet. Freight is separate. This approval is limited to those two sheet prices and their GST treatment; stock, specifications and the overall purchase launch remain pending.

On 8 September, the owner was asked whether archived source `cwi_wa_482_938x1280.jpg` (`9115bc38f8524cdf217136b834634c98cef1c7b4ee5c2a529c95902d8a6cb1df`) accurately represents the Premium Hardwood being launched and whether CWI may publish it. The owner answered yes and requested a sales-oriented edit. The returned PNG (`955a7a9fccee7b5fe47c9d55cca19d591d376aa8f1d7b09069db6461d8b72487`) is recorded as an AI-edited family presentation in [the evidence receipt](premium-hardwood-photo-evidence-2026-09-08.md). It is not an untouched documentary photo, does not distinguish 12 mm from 18 mm, and cannot support claims based on generated layers or edges. Image owner-approval is therefore recorded as true for both Hardwood records. Exact project assets and prepared production paths now exist, while `actual_product_photo_url` stays null until the reviewed release is merged and verified; the remaining catalogue, purchase and Merchant gates stay closed.

The owner also set the damage/shortage reporting requirement with the exact answer **“Within 24 hours of delivery, with photos.”** The proposed configuration now records the customer term “Report damage or shortages within 24 hours of delivery and include photographs.” This closes only the reporting deadline and evidence input. Remedy, inspection or collection, after-dispatch returns and the time to initiate an accepted refund remain pending.

The offline Merchant exporter accepts this explicitly reviewed invoice workflow as an alternative to the bank API, while requiring evidence of bank-credit verification, invoice acceptance, late-payment handling, refunds, final charges, purchase confirmation and delivery estimates. The proposed configuration records the chosen model but leaves all launch-verification flags false. No live payment or Merchant offer is enabled.

[Google's checkout requirements](https://support.google.com/merchants/answer/10249082?hl=en) permit invoicing, but a quotation-only website is not eligible. The freight-review stage must lead to a complete online purchase at a final, accepted total. Billing addresses must be independent of the Kerala delivery restriction. The existing Merchant shipping policy covering all India with a ₹300,000 minimum and a 6–25-business-day estimate must be reconciled before offers are submitted; it is not the approved Kerala policy.

### Earlier implementation record

**Build 597 is deployed and verified in the authenticated staff staging app, including the corrected catalogue approval labels.** The isolated remote D1 ledger, staff identity and role integration, audited assignment, immutable order/price snapshots, stock reservations, scheduled staging expiry and durable notification adapter are implemented. Staging suppresses real email and cannot accept real payments.

The customer shop remains a local preview. The actual ICICI payment endpoint and UAT, production commerce configuration, controlled production email review and final public launch verification remain pending. A synthetic paid/refunded status is not a bank transaction or approval of commercial terms.

## Company inputs needed

| Input | Review decision / value required | Current configuration |
|---|---|---|
| Two Hardwood launch variants | Confirm identities, finished dimensions and tolerances, face/core/bond and evidence for any claims | Two active proposals; identity approval false; Marine held |
| Selling price | Tax-inclusive INR per sheet for 12 mm and 18 mm Hardwood | Approved 7 September 2026: ₹2,794.24 / ₹3,209.60; recorded in proposed configuration |
| Tax and seller | Product GST approved at 18%; confirm legal selling/invoice entity, freight treatment and invoice requirements | Sheet-price GST approved; remaining invoice details pending |
| Stock | Operations confirms availability and reserves exact sheets for each invoice before payment | Per-invoice approach approved; numeric stock remains unknown, reservation workflow implementation pending |
| Quantity limits | Minimum and maximum per variant; mixed basket limits | Blank |
| Product imagery | Owner approved publication of the original as an accurate shared Premium Hardwood family image and authorised the sales edit; exact original and derivative hashes are recorded | Approval is complete and `image_approved` is true for both Hardwood records. Exact files are tracked in the website and prepared for the quote-only page; the production URLs stay unpublished until release. It is not thickness-specific proof. |
| Product identifiers | Genuine GTIN/MPN, or explicit confirmation none are assigned | Pending; no invented identifiers |
| Delivery eligibility | Exact Kerala PIN codes | No live postcode approved |
| Freight and delivery window | Charge per postcode/quantity band, inclusive tax treatment, earliest/latest arrival and order cut-off | Blank |
| Unloading | Who supplies labour/equipment and any access restrictions | Draft awaiting company terms |
| Damage handling | Reporting deadline/evidence; then inspection, collection and remedy process | Reporting deadline/evidence approved: within 24 hours of delivery, with photos. Remaining handling and remedy process pending. |
| Cancellation/refunds | Permitted cancellation stage, refund eligibility, times and costs | Draft awaiting company terms |

The company approval packet and detailed rate/source evidence are maintained in the private staff-app documentation. Keep those commercial details out of this public repository until an approved customer offer is ready. After review, update `commerce-preview/config/catalogue.proposed.json` with the approved offer values, approver, date and configuration version. Use `python tools/prepare_commerce.py` to regenerate the readable review and readiness report. Null means unknown. Zero freight must be an explicit free-delivery decision, not a missing value.

## Customer policy copy structure to complete

**Delivery.** “Enter your delivery PIN code and quantity to see availability, the delivery charge and estimated arrival before payment.” Follow with the actual serviceable area, timings, unloading terms and exception contact. Only approved postcode rules may return a payable total.

**Product details.** Show the exact sheet, thickness, finished dimensions and tolerance, approved price including applicable tax, availability and minimum quantity. Keep claims limited to evidence for that variant. If the minimum is more than one sheet, display the minimum purchasable total as well as the per-sheet price.

**Cancellation.** State the approved order stage at which cancellation can be requested, how to request it, and any applicable cost. Do not insert an arbitrary period or “non-refundable” condition without company review.

**Damage and returns.** State the approved reporting rule: damage or shortages must be reported within 24 hours of delivery with photos. The inspection, collection and remedy process and refund-initiation timing still need approval. Do not treat a money refund as proof that usable stock has returned to the warehouse.

**Payment.** Confirm an order as paid only after the bank verifies the correct order reference, payee, amount, currency and final state. A UPI app redirect, screenshot or typed reference cannot release stock for fulfilment.

These structures are not legal advice or approved policy language. Final online terms must match the company's actual fulfilment process and applicable requirements.

## Merchant preparation

`tools/prepare_commerce.py` produces an internal HTML review and JSON readiness report. With `--release`, it can generate local XML/TSV feed and matching Product/Offer JSON only when all company, image, policy, payment and checkout review gates pass. It never submits to Google. Synthetic fixtures always fail the release gate, even if other flags are changed to approved. A failed run removes stale feed artifacts in its specified output folder.

The feed and structured offers share the same active catalogue records. The initial export scope is the **two Hardwood variants only**; held Marine records remain excluded. Prices use integer paise and INR. Minimum purchasable quantities are reflected in both the title and total price. Availability uses allocated stock relative to that minimum. The feed's `kerala-approved-postcodes` shipping label requires corresponding reviewed Merchant Center shipping settings; a label by itself does not enforce delivery restrictions.

The exporter evaluates a reviewed configuration; it is not evidence that a bank or Google approved the account. Production `checkout_verified`, `landing_pages_verified`, `shipping_verified` and `returns_verified` must be backed by actual launch checks. Product URLs still need to be published as real buyable pages and compared against the feed at launch.

Primary references reviewed 7 September 2026: [Google product data specification](https://support.google.com/merchants/answer/7052112), [Google checkout requirements](https://support.google.com/merchants/answer/9158778), [Google Pay India web integration](https://developers.google.com/pay/india/api/web/intro). Product titles, images, prices and availability must correspond to the actual sale offer. Existing quotation products are not automatically Shopping offers.

## Bank and account dependencies

ICICI has acknowledged the authorised request. The correspondence and reference are recorded privately. An acknowledgement alone does not supply API activation, official schemas, test credentials or written charges. The real payment adapter must be implemented against the bank's actual contract, pass UAT and satisfy the approved terms before production payments are enabled.

Google Business verification remains separate from checkout. The authorised follow-up is already sent under the existing support case; verification still needs Google's route to become available and the required authorised on-site participation. Existing sitemap submissions and the Merchant business-address correction are complete; do not repeat them as launch blockers. Merchant offer submission waits for the approved, functioning purchase pages and checkout, and Google controls its later review outcome.
