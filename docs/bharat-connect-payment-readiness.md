# Bharat Connect (B2B) Payment Integration Readiness

Research & confirmation date: 13 September 2026.  
This document records the company owner's decision to adopt **Bharat Connect for Business via Zoho Books** as the official payment integration for Cochin Wood Industries Private Limited, superseding previous direct ICICI merchant API investigations.

---

## 1. Executive Summary & Decision

On 13 September 2026, the company owner confirmed that Cochin Wood Industries will use **Bharat Connect for Business** (powered by Zoho Payment Technologies Pvt Ltd and NPCI Bharat BillPay Ltd) through the company's active **Zoho Books** accounting system instead of implementing a direct ICICI merchant UPI API.

### Verified Active Configuration in Zoho Books:
- **Platform**: Zoho Books (`books.zoho.in`)
- **Integration**: Bharat Connect For Business (`settings/integrations/bharat-connect`)
- **Status**: **ACTIVE**
- **Operating Entity**: Cochin Wood Industries Private Limited
- **GSTIN**: `32AAJCC9689H1Z5`
- **B2B ID (Biller Identifier)**: `CWIPL`
- **Platform Provider**: Zoho Payment Technologies Pvt Ltd (RBI-authorized Payment Aggregator) in partnership with NPCI Bharat BillPay Ltd.

---

## 2. Why Bharat Connect via Zoho Books Supersedes ICICI Direct API

| Dimension | Legacy ICICI Direct API Investigation | Bharat Connect (via Zoho Books) |
| :--- | :--- | :--- |
| **Operational State** | Pending corporate banking approval, UAT credentials, NDAs, and API contracts. | **Live & Active** in Zoho Books with registered B2B ID `CWIPL`. |
| **Payment Reconciliation** | Required writing custom webhook listeners, signature verification, and manual ledger matching. | **Automated in Zoho Books**. Invoices are automatically updated to "Paid" upon settlement. |
| **Commercial Model Fit** | Plywood requires staff confirmation of freight and stock before final payment. ICICI API was consumer-cart oriented. | **Native B2B Invoicing Model**: Perfectly matches CWI's approved workflow where staff issues an invoice with exact freight. |
| **Payment Options for Customers** | Restricted to UPI intent / QR code apps. | **Universal Channels**: Customers can pay invoices via UPI (BHIM, Google Pay, PhonePe, Paytm, CRED), Net Banking, or NEFT/RTGS. |
| **Tax & GST Compliance** | Custom integration needed to link payments to GST tax invoices. | **Direct GSTIN Linkage**: Linked directly to GSTIN `32AAJCC9689H1Z5`, ensuring seamless e-invoicing and tax compliance. |

---

## 3. Order & Payment Flow Architecture

The approved commercial workflow follows a verified invoice-presentment and settlement architecture:

```
Customer Order / RFQ (Website / WhatsApp)
      │
      ▼
Operations & Sales Verification (Stock reserved & Freight calculated)
      │
      ▼
Zoho Books Tax Invoice Generated (Linked to B2B ID: CWIPL)
      │
      ▼
Invoice Published to Bharat Connect Network + Shared via WhatsApp / Email
      │
      ▼
Customer Pays via UPI / Net Banking / Bharat Connect Enabled Banking App
      │
      ▼
Automated Settlement & Reconciliation in Zoho Books (Status: PAID)
      │
      ▼
Order Dispatched with Accompanying GST Invoice
```

---

## 4. Key Configuration Parameters in Codebase

The commerce engine configuration (`commerce-preview/config/catalogue.proposed.json`) is updated to reflect this architecture:

```json
"payment": {
  "provider": "bharat-connect-zoho",
  "model": "bharat_connect_invoice",
  "b2b_id": "CWIPL",
  "gstin": "32AAJCC9689H1Z5",
  "platform": "Zoho Books (Zoho Payment Technologies / NPCI Bharat Connect)",
  "status_in_zoho": "ACTIVE",
  "enabled": false,
  "uat_passed": false,
  "commercial_terms_approved": false
}
```

*Note: Live transaction gates (`enabled`, `uat_passed`) remain explicitly governed by end-to-end testing of a sample invoice before public customer checkout is activated.*

---

## 5. Next Operational Steps for Company Staff

1. **Map Frequent B2B Contacts**:
   - In Zoho Books (`settings/integrations/bharat-connect`), click **"Link Now"** to map existing contractor, dealer, and business customer records to their fetched Bharat Connect B2B IDs.
2. **Review Default Payment Gateway Settings**:
   - Verify in `Settings` -> `Online Payments` that the invoice payment link includes Bharat Connect and UPI collection methods.
3. **End-to-End Test Invoice**:
   - Issue an internal test invoice (e.g. ₹10) from Zoho Books to verify that the payment link properly renders the Bharat Connect option and reconciles back to the invoice upon payment.
