# Multiple products in one enquiry

The quote form accepts up to 20 independently specified items. Contact details,
delivery destination, quote basis and notes are shared. Each item keeps its own
product, grade, thickness, dimensions, quantity, unit and help request. Product
links preselect the first item. No prices or unit conversions are inferred.

The native POST retains the established field names and adds a version 2 JSON
`enquiry` payload with an `items` array. Deploy the backward-compatible staff-app
backend before publishing this form. The backend continues accepting version 1
and native legacy clients; no database migration is needed. Each full payload is
stored separately from the bounded lead preview, and staff review all items
before preparing a draft. AI uses the existing provider and limits.

Unsaved entries stay in sessionStorage in the same browser tab for up to four
hours. Identical retries reuse their enquiry key; edited submissions get a new
key. A successful durable save/replay returns a matching `received` identifier.
Only that accepted return clears the pending draft. A bare `sent=1` URL, failed
verification or failed storage does not clear it. Storage failure is tolerated.

The local browser journey intercepts native POSTs, checks distinct specifications,
add/remove, product presets, validation, retry restoration and mobile layout.
Its encoded fixture can be supplied to the staff-app
`tests/test_multi_product_enquiries.mjs` harness to verify exact persistence and
readback without creating a production enquiry or sending messages.
