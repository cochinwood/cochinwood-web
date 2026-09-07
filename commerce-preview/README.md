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

**Actual setup** loads `config/catalogue.proposed.json`. Only the two Hardwood variants are active proposals; both Marine variants are held out of purchasing until their construction is confirmed. Hardwood selling prices and stock still await approval, so purchasing remains blocked. This view never substitutes the staff rate card or historical prices.

**Test checkout** loads `config/catalogue.synthetic.json`. Sheet prices, stock, tax and delivery terms are fictional fixtures. PIN codes 683542 and 682001 exercise eligible delivery. Other PIN codes are rejected before an order can be made. Customer emails must end in `@example.invalid`; “Fill example details” provides made-up information. Optional GSTIN is stored as provided after format validation; it does not establish registration status or issue a tax invoice.

Use different materials and thicknesses in one basket. The backend calculates amounts and snapshots the selection, price, policies, delivery window and address. Success, failure, cancellation, expiry and full refund buttons simulate local events. Full refund does not automatically restock paid sheets; staff must review goods and stock separately.

Staff review has owner, assigned salesperson, unassigned salesperson and Purchase role examples. Backend permissions determine which orders and notification previews are returned. The outbox contains records only; no email provider is connected. These are staging roles and records, not production account sessions.

## Data and failure handling

- Only SKU and quantity are kept in browser localStorage. Names, contact details, delivery addresses and order access tokens stay in memory.
- Synthetic order snapshots are stored in a local SQLite database under `%LOCALAPPDATA%/CochinWood/commerce-preview/` by default. Pass `--db` for a separate QA database. Do not enter real customer information.
- Late quote responses are discarded after the basket, PIN code or mode changes. Order creation locks edits. If its response is lost or uncertain, the submitted payload and idempotency key stay fixed in memory and edits remain locked until the same order attempt is recovered or definitively refused. Keep the page open during recovery; the local preview does not retain personal details or resume an order after a page reload.
- Payment simulation retains the event ID for retries and reconciles the stored order after an uncertain network result. An unverified browser success message never creates a paid state.
- Starting another test order refreshes the backend stock snapshot.

## Browser verification

Run with Playwright installed and local Chrome available:

```powershell
node 'C:/Users/Edwin David/cwi-brand-experience/commerce-preview/test-preview.cjs'
```

For the focused order-submission recovery regression, run `node commerce-preview/test-recovery.cjs` from this repository. It starts its own loopback server with an isolated in-memory SQLite ledger, commits an order while dropping the response, then verifies that retry returns the same order and reservation. It also verifies that a definite stock refusal permits corrections. Its result is `order-recovery-proof.json` in the configured artifact directory.

Set `COMMERCE_PREVIEW_URL` for another loopback port and `COMMERCE_PREVIEW_ARTIFACTS` for a separate output directory. Tests create synthetic orders only. They cover catalogue blocking, variant deep links, mixed baskets, item-only persistence, delivery validation and backend totals, stale quote races, form validation and GSTIN, edit locking during creation, recovery after a committed payment response is lost, role restrictions, refunds, cancellation, image aspect ratios and responsive layout at 320, 390, 768, 1229 and 1440 pixels. External network requests are blocked and reported.

The reviewed output for 7 September 2026 is in:

`C:/Users/Edwin David/.codex/visualizations/2026/09/05/01a0708d-57f6-75a2-b691-19254be1f2a5/commerce-preview/`

Key files: `browser-proof.json`, `shop-actual-desktop.png`, `shop-test-desktop.png`, `shop-test-390.png`, `staff-owner-desktop.png`, `staff-owner-390.png`, and `checkout-test-paid.png`.

Before any public launch, approved company prices, stock, product specifications and photographs, service areas, freight and policies must replace the incomplete proposed configuration. The actual staff interface is separately integrated and verified in authenticated staging; this local staff preview remains a separate harness. Bank integration and confirmation, approved production enablement, customer order recovery after a reload and real Merchant review remain launch work. Synthetic fixtures must never be published as retail offers.
