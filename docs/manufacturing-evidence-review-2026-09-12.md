# Manufacturing and dispatch evidence review — 12 September 2026

## Completed source change

The company-verification page now gives buyers a practical order-evidence checklist: written specification and producing unit; applicable technical documents; works and inspection arrangements; and packing, weight and dated photo requirements agreed before dispatch. The About operation and factory visit sections link to it. This adds a useful way for buyers to obtain evidence for their own order without presenting an unidentified archive image as proof of a named facility or shipment. Existing hero imagery and representative-product presentation remain intact.

This is a source receipt. Publication and production verification belong to the integrating release; this document alone does not establish that the change is live.

## Evidence inspected

- Current source at `e50b7394`: `VISUAL-BRAND-GUIDE.md`, `docs/experience-media.md`, `content/visual-media.json`, `docs/premium-hardwood-photo-evidence-2026-09-08.md`, company-verification, About operation, factory and the six existing case-study entries.
- The CWI company marketing archive at `C:/Users/Edwin David/Claude Code/marketing/photo-bank`: **219 raw JPEGs and 12 curated bank JPEGs** were inventoried with file size, dimensions and SHA-256. None of those files contains a capture date in the checked EXIF date fields; filesystem modification dates were not treated as capture dates.
- Ten key archive candidates were visually reviewed: raw `407`, `424`, `434` and the hash-matched owner-approved `482`; bank `dispatch-truck-01`, `export-loading-01`, `quality-check-01`, `loading-forklift-01`, `truck-loading-01` and `plywood-stack-01`.
- Four legacy published files, `Enhanced Factory Photos/factory_14.jpg`, `factory_15.jpg`, `factory_16.jpg` and `factory_18.jpg`, were visually reviewed from the production checkout. They show industrial scenes but the reviewed provenance records do not establish the facility operator, capture date or exact CWI relationship.
- Existing marketing `case-study-intake.md` and `content-claims-to-verify.md` were read. The intake requests additional shipment facts and lists five older cases. It does not contain completed new shipment rows or supporting delivery records. The current website has six cases. Owner confirmations in the claims file support general repeat-specification and technical-data-sheet language, not independently verified quantities or outcomes for new case studies.

## Candidate decisions

| Candidate | Observed evidence | Decision |
|---|---|---|
| Premium Hardwood raw `cwi_wa_482_938x1280.jpg` | 938 × 1280; 63,026 bytes; SHA-256 `9115bc38f8524cdf217136b834634c98cef1c7b4ee5c2a529c95902d8a6cb1df`. Existing source receipt records the owner's permission for representative Premium Hardwood family use. | Retain the approved existing product presentation. This permission does not establish factory identity, exact thickness, present stock or a completed customer shipment. |
| Raw `cwi_wa_434_1600x719.jpg` | Truck stacked with plywood. SHA-256 `2f1de3ccdd952a218dcaf0488e1a43b8bdc9218cc5aef47d5ab8bf82233fbe7c`. | Strong candidate once the works, approximate date, product and publication scope are confirmed. No destination, load quantity or ownership inferred. |
| Raw `cwi_wa_424_720x1280.jpg` | People loading red-faced panels into a container. SHA-256 `1e195410533f02ca7cf74f7b242d42216c731dd872bfccd4bdacba58acee6470`. | Candidate only. Product, works, capture date and shipment link remain unverified. |
| Raw `cwi_wa_407_1600x900.jpg` | Truck load at night, with blur and people in view. SHA-256 `3a41f5f1e02065fa8222d71274a7488d06262775365e6b03306007b317460b9a`. | Lower-priority candidate; no documentary caption facts established. |
| Curated `bank/` imagery | `_work/_COMPARE.jpg` explicitly compares an original, blurred version and Gemini AI presentation. Some inspected bank images differ materially from their raw counterpart. | Do not describe curated images as untouched documentary photographs. Their presence in a company archive alone does not establish which edits or claims were approved. |
| Existing warehouse/process illustrations | Current brand and media registers explicitly define them as illustrations, with original facility provenance unverified. | Preserve their illustrative role; do not reuse as customer or owned-factory evidence. |
| New shipment case studies | No completed, approved shipment intake or matching source documents found in this bounded review. | No new factual case study was invented. Existing claims are subject to the separate content review. |

The full 231-file local inventory is delivered as `cochinwood-photo-evidence-inventory-2026-09-12.csv` in the task outputs. It distinguishes inventory-only files from visually reviewed files. No private raw photos, contact details, contracts or financial records were copied into the public asset tree.

## Exact inputs still needed for documentary publication

For one useful factory/dispatch photo set, identify two or three of the raw candidates above (or other originals) and record the facility and its relationship to CWI, approximate capture date, scene/product description and confirmation that the selected people/scene can be shown publicly. If the caption makes a shipment claim, associate it privately with an order or dispatch record. Generic caption facts can be confirmed without disclosing a customer's identity.

For each factual case study, retain a private source reference plus the approved public fields: sector, destination, actual product, specification, dispatched quantity or scope, dispatch period and the result that can be substantiated. A quotation or proforma alone does not prove dispatch or receipt. Customer names, rates, contract values, container numbers and identifying labels stay out of public copy unless separately authorised.

The website implementation is complete for the evidence currently supported. New documentary gallery/case-study publication remains dependent on those missing facts; it must not be marked complete merely because this inventory exists.

## Validation

`python build.py`, visual coverage, published preservation and the generated-site check all passed. The build has the two documented redirect warnings plus the existing stale production-pin warning (`a9178b958c5d` versus `5e8fdcf484f7`); the integrating release must review and reconcile that pin. A local browser check covered company-verification, About and factory pages at 390 and 1440 pixels with all external requests blocked: no horizontal overflow and the new checklist links resolve. The new checklist was visually inspected at both widths. No enquiry was submitted and no external messages were sent.
