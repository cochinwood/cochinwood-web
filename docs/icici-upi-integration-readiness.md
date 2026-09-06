# ICICI direct UPI checkout readiness

Research date: 6 September 2026. Public-document research was followed by an explicitly authorised bank request, sent at 22:06:34 IST. No bank registration, contract acceptance, payment or collect request has been performed.

Cochin Wood's existing ICICI merchant QR is a useful starting point, but its existence does **not** establish entitlement to bank APIs. ICICI offers the required product family. The next dependency is ICICI confirming and enabling direct merchant UPI Collections API access for the existing business, with current technical specifications and written commercial terms.

Company-provided VPA: `cochinwoodindustriesprivatelimited.ibz@icici`. This identifier has not been validated against the bank. Its suffix is not evidence of online API activation, merchant identity, settlement configuration or available permissions.

## What official sources confirm

| Requirement | Confirmed capability | What remains to obtain |
|---|---|---|
| Per-order payment request | ICICI lists QR/Intent APIs in its UPI Collections suite. | Current request schema, unique order/reference rules, amount/expiry constraints and supported web/mobile intent flow. |
| Server payment confirmation | ICICI lists Callback and Transaction Status APIs. | Signed/encrypted callback specification, verification keys/certificates, replay protection, retries, acknowledgement contract and definitive success/status semantics. Public marketing documentation does not establish these details. |
| Refunds | ICICI lists a Refund API. | Eligibility, full/partial refund limits, original-transaction linkage, idempotency, status enquiry and turnaround terms. |
| Reconciliation | ICICI describes automated collection reconciliation. | Daily transaction/settlement MIS format, API or download access, RRN/reference matching, fees, reversals and dispute treatment. |

These capabilities are explicitly listed in [ICICI's Collections API page](https://www.icici.bank.in/business-banking/cms/corporate-api-suite/collections-api). Endpoint paths or cryptographic algorithms from third-party copies were deliberately not adopted as current specifications.

ICICI describes static QR as a fixed code where the customer enters the amount, and dynamic QR as transaction-specific with a prefilled amount, including website use. Its UPI QR service requires an ICICI current account. The published price description is zero transaction charges for UPI-to-UPI collections, with MDR for RuPay credit-card or credit-line funded collections; device rentals are separate. This does **not** establish that API onboarding, annual platform services, support, status calls or refunds are free. [ICICI UPI Collections](https://www.icici.bank.in/business-banking/cms/merchant-solutions/upi-collections)

ICICI's Corporate API Suite describes developer registration, selection/testing of APIs, documents for UAT and production, and bank-assisted security checks and go-live. It says existing corporate customers can integrate with less additional paperwork, but does not promise automatic activation for every existing QR merchant. The current public portal is [ICICI API Portal](https://api-portal.icici.bank.in/); its detailed specifications were not exposed in the public text interface during this check. We did not register. [Corporate API Suite and onboarding](https://www.icici.bank.in/business-banking/cms/corporate-api-suite)

The bank separately offers online payment-gateway integration and dashboard/MIS/settlement tracking. That is a possible bank-provided alternative if direct UPI API eligibility or commercial terms are unsuitable; it is not assumed to be the same contract as the existing QR. [ICICI Online Collections](https://www.icicibank.com/business-banking/cms/merchant-solutions/online-collections.html)

## Additional bank access needed

Ask the existing relationship manager or merchant/CMS support to route the request to **direct merchant UPI Collections / QR-Intent API onboarding**, explicitly distinguishing it from consumer UPI, payout APIs and a general payment-gateway quotation. The existing merchant ID/current account can be shared through the bank's secure channel; it is not needed in this research document.

Obtain these before implementation is considered bank-ready:

1. Written confirmation that this merchant/VPA may support e-commerce collections for `www.cochinwood.in`, and whether the existing VPA is retained or a separately provisioned merchant/sub-merchant/VPA is required. Confirm KYC/MCC, website requirements and transaction/velocity limits.
2. Named API products and authorized portal access; current integration specification and UAT credentials; required NDA/application forms and bank onboarding contact.
3. Production credentials and activation process after UAT; HTTPS callback registration and authentication mechanism; key/certificate rotation; network/IP allowlisting and any fixed-egress or mTLS requirement. These are questions, not assumed ICICI requirements. They affect whether the existing Cloudflare runtime is suitable.
4. Current payment status, refund and reconciliation permissions; callback retry schedule, late-success handling, settlement timing and escalation contacts.
5. A written commercial schedule: setup/annual/minimum fees, per-transaction/API/status charges, normal account-funded UPI versus RuPay/credit-line/PPI funding, refund/settlement charges, GST, volume tiers and termination terms. Ask whether credit-funded methods can be disabled if unwanted.

ICICI lists relationship managers, merchant dashboard service requests, `cmssupport@icicibank.com` and 1800 1080 as support routes. The authorised request was sent to this CMS support address; bank API activation and written total fees remain pending. [ICICI Merchant Solutions support](https://www.icicibank.com/business-banking/cash-management-services/eazypay)

## What can be prepared without credentials

The following is our proposed engineering design, not an asserted ICICI API contract:

- Keep amount and order reference authoritative on the server. Create a durable payment attempt before requesting an order QR/intent. Present supported UPI apps, including Google Pay where supported; do not equate opening an app or returning to the browser with payment success.
- Use the bank's authenticated callback and/or authenticated status result to confirm the expected merchant, amount, currency and order reference. Payment screenshots, customer-entered RRNs and browser success parameters cannot authorize fulfilment automatically.
- Handle pending, expired, failed, late-success and reversal states; deduplicate repeated callbacks and repeated browser requests; prevent two payments from settling the same order twice.
- Prepare a bank-adapter interface, mock callback/status fixtures, reconciliation records and tests for mismatched amounts, duplicate/out-of-order callbacks, network timeouts and refunds. Keep real signing/decryption and endpoint details unimplemented until the official specification is received.
- Prepare accessible desktop QR/mobile intent UI and an honest pending-confirmation screen. No production checkout should claim automatic confirmation from the existing static QR alone.

No live implementation or funds movement is authorized by this research task. Bank PINs, OTPs and personal banking passwords are not integration credentials and are not needed by the developer.

## Authorised request sent to ICICI

**Subject:** Enable direct UPI QR/Intent Collections API for existing Cochin Wood merchant

Hello,

We already have an ICICI merchant UPI QR for Cochin Wood Industries Private Limited, VPA `cochinwoodindustriesprivatelimited.ibz@icici`. We want to accept order-specific UPI payments on `www.cochinwood.in`, with customers using their preferred UPI app, and confirm payments directly through ICICI rather than a third-party gateway.

Please confirm whether our existing merchant setup can be enabled for QR/Intent, authenticated callbacks, transaction-status enquiry, refunds and reconciliation APIs. If a new merchant/VPA mapping is required, please explain the process while retaining our existing QR service.

Please provide the onboarding checklist, current official API specifications, UAT access process, production/security requirements, settlement terms and a written fee schedule covering setup, recurring/API charges and each UPI funding type. Please also confirm applicable transaction limits and whether credit-funded UPI can be disabled.

Our technical team can provide the website details and proposed callback architecture through your secure onboarding process. Please connect us with the responsible UPI Collections API team.

Thank you,
Cochin Wood Industries Private Limited

**Status: SENT, verified in Gmail.** From `cochinwoodindia@gmail.com` to `cmssupport@icicibank.com`, 6 September 2026 at 22:06:34 IST. Subject: `Enable direct UPI QR/Intent Collections API for existing Cochin Wood merchant`. Sent message ID: `1a077942dd8ecf11`; thread ID: `1a077915e11318b5`; Gmail label: `SENT`. This receipt confirms sending, not a bank reply, API activation or agreement to charges. Do not resend this request.
