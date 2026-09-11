# Kerala online catalogue — preparation record

Updated 6 September 2026. Status: preparation only; no products submitted to Google and no checkout accepting money.

## Decisions confirmed by Edwin

- Sell selected standard plywood sheets online.
- Accept delivery orders within Kerala initially.
- Keep custom, bulk and export requirements on the existing quotation journey.
- There is no existing payment gateway account. Prepare a recommendation and setup requirements.
- Commercial/packing plywood is excluded from the proposed online catalogue. Edwin requested removal on 6 September 2026.
- Edwin prefers to investigate direct Google Pay/UPI because of gateway commission. Direct merchant UPI through the existing ICICI merchant relationship is the chosen first route to investigate; API activation and commercial terms are not yet approved by the bank.
- Edwin confirmed an existing ICICI merchant QR and supplied `cochinwoodindustriesprivatelimited.ibz@icici`. This is a company-provided identifier; the bank has not yet confirmed online API activation.
- Marketing imagery must reflect Perumbavoor or the Indian plywood industry. Images must not imply that generated or third-party premises are company facilities.

## Revised payment recommendation

Investigate **direct merchant UPI through Cochin Wood's company bank first**, with Google Pay as a customer payment option. This follows Edwin's preference to avoid percentage gateway commission. Google's India website integration requires a verified merchant UPI ID, a unique reference for each transaction, and bank APIs for checking payment status. Its documented web flow covers Android Chrome; desktop, iPhone and other browsers require a supported alternative, such as an approved order-specific QR/omnichannel flow, which must be tested separately. [Google Pay India prerequisites](https://developers.google.com/pay/india/api/web/intro), [Google's merchant registration steps](https://support.google.com/console/answer/10945206?hl=en).

Google states that bank-account UPI payments have no transaction fee, while RuPay credit cards, credit lines and wallets on UPI can attract MDR. Obtain the bank's written API/setup/service charges and enabled payment-source terms before describing the complete integration as free. [Google Pay business fee guidance](https://support.google.com/pay-offline-merchants/answer/13591970?hl=en).

A static QR alone does not give our server automatic payment confirmation. Screenshots and a browser's payment response are not sufficient evidence to fulfil an order. The acquiring bank/provider must support checking the exact order reference, amount, payee and final payment state. If direct-bank integration is unavailable or commercially unattractive, compare written gateway offers for a UPI-focused checkout; Razorpay and Cashfree remain alternatives, not approved selections. [Google's integration requirements](https://developers.google.com/pay/india/api/web/intro).

No provider account has been created, contract accepted, bank information submitted or paid subscription purchased in this preparation.

ICICI-specific research and the prepared request are in [icici-upi-integration-readiness.md](icici-upi-integration-readiness.md). The request was explicitly authorised and sent from `cochinwoodindia@gmail.com` to `cmssupport@icicibank.com` on 6 September 2026 at 22:06:34 IST. Gmail confirms `SENT`: message `1a077942dd8ecf11`, thread `1a077915e11318b5`, subject `Enable direct UPI QR/Intent Collections API for existing Cochin Wood merchant`. Do not resend. Bank API activation and written total fees remain pending; no bank registration, contract acceptance or payment has occurred.

## What we need from the company bank / UPI provider

ICICI and the existing company-provided merchant VPA are already identified above. The sent request asks ICICI for online merchant acceptance, the assigned merchant category code, a status-check API, authenticated callbacks, order-reference support, refund/reconciliation procedures, sandbox access and written commercial terms. Await the bank response and activation requirements; the sent request is not evidence that API access is enabled.

Register the company and verified merchant UPI ID in the Google Pay & Wallet Console if needed for the chosen integration. Google requires business-profile approval and UPI-ID verification. The bank/provider remains responsible for the payment-status APIs. Owner involvement may be needed for account verification and access. [Google's India merchant onboarding](https://support.google.com/console/answer/10945206?hl=en).

The registered legal address and the staffed customer office can be different. Each field must contain its correct address; do not overwrite the legal address merely to match the website's customer-visit address.

After approval, provide authorised developer access and test-mode credentials. Store API credentials only in server secrets. Identity documents, passwords and live secrets must not be committed to the website repository. The public site receives only the public merchant/payment parameters required by the selected integration.

## Proposed first selection — requires commercial confirmation

The staff catalogue contains the following relevant product identities. These are four proposed variants for review, not approved sale offers or stock claims:

| Staff product key | Product identity | Proposed size | Proposed thicknesses |
|---|---|---|---|
| prem_hw_gurjan | Cochin Premium Hardwood, Gurjan BWR (MUF) | 8 × 4 ft | 12 mm, 18 mm |
| prem_marine_gurjan | Cochin Premium Marine, Gurjan BWP (PF) | 8 × 4 ft | 12 mm, 18 mm |

Source: `cochin-wood-document-studio/webapp/catalog.js`, inspected 6 September 2026. The static catalogue explicitly contains historical reference prices; they have **not** been copied into online offers. The live staff rate card is a quoting input, not automatic approval of a retail price, available stock or a certification claim.

Confirm for each variant: exact finished dimensions and tolerances, face/core/bond, manufacturer and genuine product identifier where one exists, evidence for any grade/certification claim, selling price per sheet including applicable tax, stock reserved for online sale, minimum/maximum order, replenishment lead time and a photograph of the actual product. Do not infer a certified finished board from a generic product-family description. Never create invented GTINs.

## Kerala delivery and service policy

Prepare a serviceable postcode table with an actual delivery price and promised window for each supported postcode/quantity band. Confirm unloading responsibility, damaged-delivery reporting, cancellation and refund handling, and any minimum basket value. Unsupported postcodes should lead to the quote form before payment. A Kerala state label alone is insufficient to calculate delivery.

Merchant Center currently has historical India shipping settings, including a ₹300,000 threshold and a 6–25 day window. These have not been approved for the new retail model and must not be copied into checkout. Existing shipping/return policy pages must be reconciled with the approved online terms before launching.

## Customer journey and app record

1. Choose a clearly specified sheet and quantity; see the tax-inclusive sheet price.
2. Enter a Kerala delivery postcode; see eligibility, delivery charge and expected window before payment.
3. Review the full basket total and the policies. Guest checkout is available; company name and GSTIN are optional.
4. The server rechecks the approved catalogue, price, stock and delivery rule, reserves stock and creates an order. Client-supplied amounts are never authoritative.
5. The supported UPI flow takes payment. The server checks the bank/provider's authoritative status and matches the order reference, amount and recipient. An unverified browser success message cannot release goods. Authenticated callbacks and a reconciliation job recover interrupted browser journeys; the exact implementation depends on the chosen bank's API.
6. One paid-order record reaches the staff app, with exact item/price/tax/delivery snapshots, payment reference and fulfilment status. Duplicate callbacks cannot create duplicate orders. Owner alerts go to cochinwoodindia@gmail.com and edwin.david@cochinwood.in, plus the assigned salesperson once assigned.
7. Failed/abandoned payments release the reservation according to a bounded policy. Refunds and payment exceptions remain traceable. This requires implementation and testing; the existing enquiry pipeline is not a paid-order system.

## Merchant feed and launch acceptance

Create feed entries only for real approved purchasable variants. The feed, landing page, structured data, basket and checkout must agree on identity, price and availability. Delivery restrictions must reflect the actual Kerala service area. Quotation-only products remain outside the purchase feed. Google's checkout requirements include the ability for individuals to buy and accurate pricing, availability and delivery information. [Google checkout requirements](https://support.google.com/merchants/answer/9158778?hl=en).

Before live launch, verify test-mode success/failure/cancellation; tampered totals; unavailable stock; concurrent last-stock purchases; duplicate, delayed and out-of-order callbacks; incorrect signatures; non-Kerala addresses; delivery charges; customer and staff order receipts; refund state; and recovery after an interrupted payment. Validate the Merchant feed and real landing pages. Use a separately authorised live payment only after test mode passes.

## Explicitly still needed

1. Approval of exact launch variants, prices, stock and order limits.
2. Serviceable Kerala postcodes, freight charges and online service terms.
3. Merchant UPI/bank identification, suitable payment-status APIs, account verification, developer access and test credentials; then the final provider decision.
4. Checkout, stock reservation and paid-order integration implementation followed by test-mode verification.
5. Merchant product submission and Google's review after the real purchase journey is ready.

The commercial model decision is complete. Shopping activation is not complete and cannot be represented as active merely because the website is verified and claimed.
