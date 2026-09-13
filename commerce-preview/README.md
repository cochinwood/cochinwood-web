# Kerala shop and staff preview

This directory is an isolated, local staging interface. It is not part of the public website build, not connected to the live staff app, and does not accept payment or send email. The existing quotation journey is unchanged.

## Open the preview

The backend is prepared in `C:/Users/Edwin David/cochin-wood-document-studio/prepared-commerce/`. Its local harness serves this website directory and shared brand assets:

```powershell
node 'C:/Users/Edwin David/cochin-wood-document-studio/tools/commerce/preview-server.mjs' --web-root 'C:/Users/Edwin David/cwi-brand-experience' --port 8891
```

Use Node 24 or the installed Codex Node runtime if `node` is not on PATH. A running instance already using port 8891 should be reused; do not launch a duplicate.

- Shop: `http://127.0.0.1:8891/commerce-preview/`
- Staff review: `http://127.0.0.1:8891/commerce-preview/staff.html`
- Launch readiness: `http://127.0.0.1:8891/commerce-preview/readiness/`
- Variant selection example: `http://127.0.0.1:8891/commerce-preview/?sku=prem_hw_gurjan_18`

The server listens only on loopback, denies cross-origin API requests, protects configuration files, and serves noindex headers. Do not expose this harness to the internet.

## Review the two modes

**Actual setup** loads `config/catalogue.proposed.json`. Only the two Hardwood variants are active proposals; both Marine variants are held out of purchasing until their construction is confirmed. The owner approved the two tax-inclusive Hardwood prices and selected Operations confirmation and stock reservation for each invoice on 7 September 2026. Order limits and the remaining launch inputs are pending. The per-invoice reservation workflow is separate implementation work, and this fixed-stock cart refuses that policy. This view never substitutes the staff rate card, historical prices or invented stock.

**Test checkout** loads `config/catalogue.synthetic.json`. Sheet prices, stock, tax and delivery terms are fictional fixtures. PIN codes 683542 and 682001 exercise eligible delivery. Other PIN codes are rejected before an order can be made. Customer emails must end in `@example.invalid`; “Fill example details” provides made-up information. Optional GSTIN is stored as provided after format validation; it does not establish registration status or issue a tax invoice.

Use different materials and thicknesses in one basket. The backend calculates amounts and snapshots the selection, price, policies, delivery window and address. Success, failure, cancellation, expiry and full refund buttons simulate local events. Full refund does not automatically restock paid sheets; staff must review goods and stock separately.

Staff review has owner, assigned salesperson, unassigned salesperson and Purchase role examples. Backend permissions determine which orders and notification previews are returned. The outbox contains records only; no email provider is connected. These are staging roles and records, not production account sessions.

## Data and failure handling

- By default, only SKU and quantity are kept in browser localStorage. Names, contact details, delivery addresses and order access tokens stay in memory. Optional device recovery is described below; it never writes those details as plaintext.
- Synthetic order snapshots are stored in a local SQLite database under `%LOCALAPPDATA%/CochinWood/commerce-preview/` by default. Pass `--db` for a separate QA database. Do not enter real customer information.
- Late quote responses are discarded after the basket, PIN code or mode changes. Order creation locks edits. If its response is lost or uncertain, the submitted payload and idempotency key stay fixed and edits remain locked until the same order attempt is recovered or definitively refused. Without optional saved recovery, keep the page open until this is resolved.
- Payment simulation retains the event ID for retries and reconciles the stored order after an uncertain network result. An unverified browser success message never creates a paid state.
- Starting another test order refreshes the backend stock snapshot.

## Optional recovery after closing the page

Before submission, an optional collapsed control offers an encrypted recovery copy on this device. It is off by default and creates no account. Choosing it requires a repeated passphrase of 12–256 characters; the passphrase cannot be recovered and is never stored. Normal checkout requires no passphrase.

`recovery.js` uses native Web Crypto AES-256-GCM with a random 96-bit nonce per write. A non-extractable key is derived with PBKDF2-SHA-256, a random 128-bit salt and 600,000 iterations. Origin, storage version and timestamps are authenticated with the ciphertext. Browser Web Locks coordinate writes between tabs; a changed copy is not silently overwritten. No new dependency or server endpoint is introduced.

The original request body, idempotency key and displayed quote are encrypted **before** submission. If saving fails, no order request is sent until the user retries or opts out. After an accepted response, the encrypted payload is minimized to the order ID and bearer access token. Neither plaintext facts, the passphrase nor the key enter localStorage or sessionStorage. This protects saved data at rest; it does not protect an unlocked page from malicious scripts or someone controlling the device.

The copy is available for 24 hours from its first save. Updates do not extend that time. An expired copy is removed when this page is next opened or checks recovery; browser storage restrictions can prevent physical removal, which is reported. The copy is bound to the same browser profile and origin, including the loopback port. Clearing site data, losing the passphrase or changing origin can make it unavailable. This is not a backup or a production customer identity system.

Opening the page never restores contact details or sends an order automatically. The user chooses **Unlock and review**. A known accepted order uses the existing bearer-protected `GET /orders/:id` to obtain current status, without trusting a cached payment state. An uncertain original attempt presents its frozen facts and requires confirmation before replaying the exact existing POST body and idempotency key. This obtains the original order if it already committed; it does not create a second reservation. Corrupt data or an incorrect passphrase send nothing.

Only one recovery copy is stored per origin. Another order cannot silently overwrite it. **Forget saved copy** requires a second confirmation and removes browser data only. Forgetting or expiry does not cancel an order or release a reservation; the interface tells the user to check the existing order before submitting the same requirement again. Production recovery across devices or after lost credentials still requires a separately reviewed server-side customer identity/recovery design.

## Browser verification

Run with Playwright installed and local Chrome available:

```powershell
node 'C:/Users/Edwin David/cwi-brand-experience/commerce-preview/test-preview.cjs'
```

For the focused order-submission recovery regression, run `node commerce-preview/test-recovery.cjs` from this repository. It starts its own loopback server with an isolated in-memory SQLite ledger, commits an order while dropping the response, then verifies that retry returns the same order and reservation. It also verifies that a definite stock refusal permits corrections. Its result is `order-recovery-proof.json` in the configured artifact directory.

Run `node commerce-preview/test-device-recovery.cjs` for optional device recovery. It uses its own isolated server and real SQLite, blocks external network, and checks default privacy, encrypted saved data, wrong passphrases, exact-request replay across closed browser contexts, accepted-order GET-only recovery, explicit forgetting, expiry, damaged storage, unavailable storage and authenticated timestamp tampering. Its receipt is `customer-device-recovery-proof.json`; `customer-recovery-mobile.png` records the rendered 390px recovery panel.

Set `COMMERCE_PREVIEW_URL` for another loopback port and `COMMERCE_PREVIEW_ARTIFACTS` for a separate output directory. Tests create synthetic orders only. They cover catalogue blocking, variant deep links, mixed baskets, item-only persistence, delivery validation and backend totals, stale quote races, form validation and GSTIN, edit locking during creation, recovery after a committed payment response is lost, role restrictions, refunds, cancellation, image aspect ratios and responsive layout at 320, 390, 768, 1229 and 1440 pixels. External network requests are blocked and reported.

The reviewed output for 7 September 2026 is in:

`C:/Users/Edwin David/.codex/visualizations/2026/09/05/01a0708d-57f6-75a2-b691-19254be1f2a5/commerce-preview/`

Key files: `browser-proof.json`, `shop-actual-desktop.png`, `shop-test-desktop.png`, `shop-test-390.png`, `staff-owner-desktop.png`, `staff-owner-390.png`, and `checkout-test-paid.png`.

The owner selected Bharat Connect for Business via Zoho Books (active B2B ID `CWIPL`, GSTIN `32AAJCC9689H1Z5`) with automated payment reconciliation upon payment via UPI / NetBanking / NEFT, after staff confirms freight and the customer accepts the complete issued invoice. The first live design extends the existing app's issued PI and Orders workflow; this cart and its separate ledger remain an isolated test harness. Direct ICICI merchant API onboarding is superseded.

The owner approved the two nominal 8 × 4 ft Hardwood sheet prices: 12 mm ₹2,368 + ₹426.24 GST = ₹2,794.24; 18 mm ₹2,720 + ₹489.60 GST = ₹3,209.60. The configuration records these exact prices including 18% GST. Freight remains separate. Before payable offers, confirm stock handling, product specifications and exact-product photographs, seller/invoice details, delivery eligibility/timing and operating terms. Commercial remains excluded and Marine remains held. Approval of these prices does not approve the full catalogue or enable purchasing.

The actual staff interface is separately integrated and verified in authenticated staging; this local staff preview remains a harness. Immutable acceptance of the full issued invoice, confirmed allocation, actual-credit review and exception/refund handling, production customer identity/recovery, notification delivery and an approved release remain implementation work. The local device-recovery implementation does not enable those services. Merchant listings need a complete purchase process with final mandatory charges; awaiting a freight quote alone is insufficient. Synthetic fixtures must never be published as retail offers.
