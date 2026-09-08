# Commerce configuration

`catalogue.proposed.json` is the company review record. Null means unknown, not zero or free. No selling price, stock allocation, certification, finished dimension, freight rate or service promise has been inferred from historical quoting data.

`catalogue.synthetic.json` contains deliberately fictional numbers and postcodes for isolated software tests. It is not an offer, approved rate card, tax opinion or stock statement. It must never be used for a public feed, live order or bank payment. Both files are outside the production site build.

All money is integer paise. On 7 September 2026, the owner approved the two Premium Hardwood sheet prices including 18% GST: 12 mm at ₹2,794.24 and 18 mm at ₹3,209.60, nominal 8 × 4 ft. `pricing_approval` records this limited approval; the overall catalogue approval remains pending. The isolated checkout harness uses exact postcode and quantity bands, not a claim that all Kerala postcodes are serviceable. The owner selected staff-confirmed freight with customer acceptance of the full issued invoice before payment; that live workflow is still to be implemented using the existing PI/Orders records. It does not require inventing a fixed tariff for this harness. Seller identity and final invoice/freight tax configuration remain separate launch checks.

The selected payment model is `upi_bank_verified_invoice`: ICICI UPI with staff verifying actual bank credit. Its live gates remain false. An automatic bank API is a separately reviewed future option. The approved Hardwood prices are ₹2,368 / ₹2,720 before GST and freight; their tax-inclusive values are recorded in `unit_price_paise`. Stock remains unknown. Commercial remains absent; Marine remains inactive with no approved purchase price.

Before approval, review every product identity, actual product photo and identifier; exact finished dimensions/tolerances; sheet price, tax, stock and min/max quantity; delivery eligibility, price and dates; unloading, damage, cancellation and refund policies. Record approver/date and version. Payment and Merchant activation are separate release gates.

A release policy URL is eligible only with a matching `policies.reviewed_pages` record. Each record names the versioned source page, exact public URL, reviewer and timezone-aware review date, required service topics, and the SHA-256 of the reviewed source content after line endings are normalized to LF. The route must match that source and the hash must still match the file. A valid URL by itself does not establish policy review, and policy review does not satisfy the separate checkout, confirmation, delivery-estimate, payment or Merchant verification gates.

Preview images are existing product-family presentations. `actual_product_photo_url` stays null until a photograph of the exact sold product is approved. Preview imagery cannot satisfy the Shopping image approval gate.

## Approved stock allocation approach

The owner selected **Operations confirmation and reservation for each invoice** on 7 September 2026. `inventory_policy.mode` is `staff_per_invoice`. Before a customer can pay, Operations must confirm availability and reserve the exact sheets for that invoice. No fixed online stock pool was approved; numeric `stock` fields remain null. Minimum and maximum order quantities still await the owner's answers.

The current cart and Merchant exporter only support a fixed stock pool. They explicitly refuse this per-invoice policy even if other fields later receive numbers and approvals. The live invoice reservation workflow belongs to the separate purchase implementation; selecting the policy does not create reservations or change role permissions. A combined order minimum, if approved, must not be entered as a separate minimum for each thickness.
