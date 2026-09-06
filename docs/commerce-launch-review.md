# Online shop commercial review

Prepared 7 September 2026. This is an internal review document, not published customer terms.

## Confirmed direction

Selected standard plywood sheets, Kerala delivery initially, with custom/bulk/export orders remaining quotations. Commercial/packing plywood is excluded from the proposed online catalogue. Investigate the existing ICICI merchant UPI relationship first. Google Pay can be a customer UPI option only through the bank-supported flow. No fees, bank activation or live checkout are represented as approved.

The four proposed options are Premium Hardwood Gurjan BWR (MUF), 8 × 4 ft, in 12 mm and 18 mm, and Premium Marine Gurjan BWP (PF), 8 × 4 ft, in 12 mm and 18 mm. Exact finished dimensions, tolerances and grade/certification claims need confirmation for each sold variant.

## Company inputs needed

| Input | Review decision / value required | Current configuration |
|---|---|---|
| Exact four launch variants | Confirm identities, finished dimensions and tolerances, face/core/bond and evidence for any claims | Proposed; identity approval false |
| Selling price | Tax-inclusive INR per sheet for each variant | Blank; historical quote rates have not been copied |
| Tax | Approved tax treatment and rate; freight treatment and invoice requirements | Blank |
| Stock | Sheets reserved for online orders; restocking responsibility | Blank |
| Quantity limits | Minimum and maximum per variant; mixed basket limits | Blank |
| Exact product imagery | Photographs of the actual sold variant, with commercial rights | Pending; preview uses existing family images only |
| Product identifiers | Genuine GTIN/MPN, or explicit confirmation none are assigned | Pending; no invented identifiers |
| Delivery eligibility | Exact Kerala PIN codes | No live postcode approved |
| Freight and delivery window | Charge per postcode/quantity band, inclusive tax treatment, earliest/latest arrival and order cut-off | Blank |
| Unloading | Who supplies labour/equipment and any access restrictions | Draft awaiting company terms |
| Damage handling | What customers record at delivery, how to report, resolution process | Draft awaiting company terms |
| Cancellation/refunds | Permitted cancellation stage, refund eligibility, times and costs | Draft awaiting company terms |

Edit `commerce-preview/config/catalogue.proposed.json` after review, including approver, date and configuration version. Use `python tools/prepare_commerce.py` to regenerate the readable review and readiness report. Null means unknown. Zero freight must be an explicit free-delivery decision, not a missing value.

## Customer policy copy structure to complete

**Delivery.** “Enter your delivery PIN code and quantity to see availability, the delivery charge and estimated arrival before payment.” Follow with the actual serviceable area, timings, unloading terms and exception contact. Only approved postcode rules may return a payable total.

**Product details.** Show the exact sheet, thickness, finished dimensions and tolerance, approved price including applicable tax, availability and minimum quantity. Keep claims limited to evidence for that variant. If the minimum is more than one sheet, display the minimum purchasable total as well as the per-sheet price.

**Cancellation.** State the approved order stage at which cancellation can be requested, how to request it, and any applicable cost. Do not insert an arbitrary period or “non-refundable” condition without company review.

**Damage and returns.** State how to document and report damaged delivery, who arranges collection, the remedy, and when a refund is issued. Do not treat a money refund as proof that usable stock has returned to the warehouse.

**Payment.** Confirm an order as paid only after the bank verifies the correct order reference, payee, amount, currency and final state. A UPI app redirect, screenshot or typed reference cannot release stock for fulfilment.

These structures are not legal advice or approved policy language. Final online terms must match the company's actual fulfilment process and applicable requirements.

## Merchant preparation

`tools/prepare_commerce.py` produces an internal HTML review and JSON readiness report. With `--release`, it can generate local XML/TSV feed and matching Product/Offer JSON only when all company, image, policy, payment and checkout review gates pass. It never submits to Google. Synthetic fixtures always fail the release gate, even if other flags are changed to approved. A failed run removes stale feed artifacts in its specified output folder.

The feed and structured offers share the same catalogue records. Prices use integer paise and INR. Minimum purchasable quantities are reflected in both the title and total price. Availability uses allocated stock relative to that minimum. The feed's `kerala-approved-postcodes` shipping label requires corresponding reviewed Merchant Center shipping settings; a label by itself does not enforce delivery restrictions.

The exporter evaluates a reviewed configuration; it is not evidence that a bank or Google approved the account. Production `checkout_verified`, `landing_pages_verified`, `shipping_verified` and `returns_verified` must be backed by actual launch checks. Product URLs still need to be published as real buyable pages and compared against the feed at launch.

Primary references reviewed 7 September 2026: [Google product data specification](https://support.google.com/merchants/answer/7052112), [Google checkout requirements](https://support.google.com/merchants/answer/9158778), [Google Pay India web integration](https://developers.google.com/pay/india/api/web/intro). Product titles, images, prices and availability must correspond to the actual sale offer. Existing quotation products are not automatically Shopping offers.

## Bank and account dependencies

ICICI acknowledged the authorised request under **E099605724** on 6 September 2026 at 22:12 IST. That message is an acknowledgement only; no API activation, official schemas, test credentials or written fees were supplied. Keep real payment implementation disabled until those are received and tested.

Google Business case **1-6734000040756** remains separate from checkout. The authorised follow-up was sent; verification still needs Google's route to become available and the required authorised on-site business verification.
