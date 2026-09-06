# Commerce configuration

`catalogue.proposed.json` is the company review record. Null means unknown, not zero or free. No selling price, stock allocation, certification, finished dimension, freight rate or service promise has been inferred from historical quoting data.

`catalogue.synthetic.json` contains deliberately fictional numbers and postcodes for isolated software tests. It is not an offer, approved rate card, tax opinion or stock statement. It must never be used for a public feed, live order or bank payment. Both files are outside the production site build.

All money is integer paise. Tax-inclusive prices are used in the proposed retail model; the rate and tax treatment still require company confirmation. Delivery rules are exact postcode and quantity bands, not a claim that all Kerala postcodes are serviceable. Freight is inclusive of applicable tax when approved. Final invoicing must use the company's reviewed tax configuration.

Before approval, review every product identity, actual product photo and identifier; exact finished dimensions/tolerances; sheet price, tax, stock and min/max quantity; delivery eligibility, price and dates; unloading, damage, cancellation and refund policies. Record approver/date and version. Payment and Merchant activation are separate release gates.

Preview images are existing product-family presentations. `actual_product_photo_url` stays null until a photograph of the exact sold product is approved. Preview imagery cannot satisfy the Shopping image approval gate.
