# Decisions needed before the Kerala online shop can launch — 8 September 2026

Three things on this page need **Edwin's decision**, not an engineer's. Nothing here has been applied.
The separate rate-suppression change in this same working tree HAS been applied and is described at the
bottom.

---

## 1. The published policy pages contradict the shop that was priced yesterday

All three are live and indexed on cochinwood.in right now. Each states, as binding terms of sale, the
opposite of the launch approved on 7 September.

| Live clause | What it says | What the approved launch does |
|---|---|---|
| Terms cl. 1 | "This website does not operate a shopping cart, take online payment or display purchase prices. Nothing on it is an offer to sell. All prices are given by written quotation." | A shopping cart taking UPI payment, displaying ₹2,794.24 and ₹3,209.60 |
| Terms cl. 4 | "Prices are exclusive of GST and any other tax, duty or levy" | Online prices are **tax-inclusive** at 1800 bps |
| Shipping policy | "Cochin Wood Industries does not sell to consumers." / "We do not ship parcels or single sheets." | Sells **single 8×4 sheets** to Kerala addresses |
| Returns policy | "This is not a consumer returns policy. There is no cooling-off period and no right of return for change of mind." | Google Merchant is a consumer channel; the Consumer Protection (E-Commerce) Rules 2020 apply |

**Recommended shape: do not rewrite the existing terms. Add a scoped online channel to each.**

The current B2B wording is not sloppy — it is doing real work protecting truckload business (no returns
on bulk industrial goods, price fixed only at proforma, quotation-based pricing). Rewriting it to fit a
two-SKU Kerala pilot would weaken the protections on the business that actually pays the bills. Scoping is
safer and is also what Google requires: it wants a returns policy that covers *the offers in the feed*,
not the whole company.

### Draft insert — Terms, new clause after cl. 1

> **1A. Online orders.** Cochin Wood Industries operates a separate online channel for a limited range of
> products delivered within Kerala. Where a product is listed with a price on that channel, that listing is
> an offer to sell on the terms shown at checkout, and clauses 1 and 4 do not apply to it. Online prices
> are stated inclusive of GST at the rate in force; delivery is quoted and confirmed separately before
> payment. All other supply — including all export, all bulk and all made-to-order work — remains by
> written quotation under clause 1.

### Draft insert — Shipping policy, new section

> **Online orders within Kerala.** The online channel supplies listed products in single-sheet quantities
> to serviceable Kerala PIN codes. Availability is confirmed by our Operations team and the sheets are
> reserved for your invoice before payment is taken. Delivery charges are confirmed on the invoice before
> you pay; we do not despatch until the invoice is accepted and payment is credited. The statements above
> that we do not sell to consumers and do not ship single sheets describe our quotation-based bulk supply,
> and do not apply to this channel.

### Draft insert — Returns policy, new section

> **Online orders within Kerala.** For products bought through the online channel you may cancel any order
> that has not yet been despatched for a full refund. If the goods arrive damaged, short, or not matching
> the product described, tell us within **[N] days** of delivery with photographs and we will replace them
> or refund you in full, including delivery. Refunds are made to the original payment method within
> **[N] business days** of us accepting the return. The bulk-supply terms above — no cooling-off period and
> no right of return for change of mind — continue to apply to all quotation-based orders.

**Two numbers I have deliberately left as `[N]`.** They are commitments, not drafting, and they should be
yours: the damage/shortage reporting window, and the refund turnaround. A common pair is 7 days and 7
business days. Also still open: whether you offer change-of-mind cancellation *after* despatch, which for
a single plywood sheet on a Kerala lorry may cost more in return freight than the sheet is worth — saying
"no change-of-mind return once despatched" is legitimate and clearer than staying silent.

### One more thing this exposes

`tools/prepare_commerce.py` blocks release until `policies.delivery_url`, `policies.returns_url` and
`policies.cancellation_url` are set — but the only validation is on the URL's **shape** (https, correct
host, non-empty path). It never fetches the page. So pointing `returns_url` at today's no-returns policy
turns the gate green. The gate creates the appearance of a policy review without performing one. Worth
either strengthening it or, at minimum, not treating a green gate here as evidence.

---

## 2. The Neem card is a derivative of a source that does not grant adaptation rights

Four AI-assisted wood visuals are live on `/woods-we-use`. **Three are fine** — Melia dubia, Sal and Kadam
are built on CC BY 4.0 sources, and CC BY 4.0 expressly permits adaptations. The on-page disclosure is
good: a visible "AI-assisted visual" label, a credit line, alt text that leads with "AI-assisted", and a
build guard that refuses to render generated artwork without provenance.

**Neem is the exception, and the site's own label says so.** Its credit reads:

> Deore et al. (2020) · Figure 6 · **Reuse with attribution**

The cited licence page grants reuse, distribution and reproduction, and advises seeking the copyright
owner's permission. It does not grant the right to **adapt**. The published file is an adaptation — the
entry's own metadata records the figure as the image-to-image "Input image" and stores its
`original_reference_sha256`. Reuse is not adaptation, and the gap is visible on the card itself.

**Options, in the order I'd consider them:**

- **(a) Pull the Neem AI card** and leave that species with no wood image, as it was before yesterday.
  Costs nothing, closes the exposure today, and is consistent with the standing decision not to publish a
  weak or unlicensed image. **This is what I'd do while (b) runs.**
- **(b) Write to the corresponding author** for permission to adapt Figure 6. The lead was already
  captured under the grain-sourcing task artifacts. If granted, restore the card with the permission
  recorded in the metadata.
- **(c) Photograph your own Neem.** You are a timber merchant — an identified Neem sample photographed in
  Perumbavoor beats every licensed research figure, carries no third-party rights at all, and could
  replace the remaining AI cards over time.

I have not removed it. Say which and I'll implement it.

### Separately: the AI files carry no embedded provenance

All four are listed in `/sitemap-images.xml` as bare `<image:loc>`, which actively invites Google Images
to index them, and the WebP files carry no EXIF, XMP, C2PA or IPTC `digitalSourceType`. Every disclosure
lives in the HTML. Once one is surfaced in image search, hotlinked or right-click-saved, what remains is
an unmarked photorealistic image of "Melia dubia wood" on a timber merchant's domain with nothing marking
it as generated. Two cheap fixes, not mutually exclusive: embed IPTC/C2PA provenance in the four files,
and/or drop them from the image sitemap. Recommend both.

---

## 3. What I DID apply in this working tree (rate suppression)

This one needed no new decision — it re-applies **your own decision of 28 July 2026** (commit `9d903cac`,
"Remove all published sale-rate disclosures (28 pages)"), which the 4 September whole-tree republish
(`ebc11445`) silently reverted on the pages below.

**Applied in two rounds — the first was incomplete and independent review caught it.** Round 1 rewrote
prose only. But `9d903cac` had removed rates from **prose AND table cells**, so six pages ended up saying
"quoted on request" in a paragraph directly above a table still printing the full rate card. Round 2 fixed
the tables and the cases the first pattern could not see. Recording this because the failure is
instructive: round 1 "verified" itself with the same narrow pattern used to build the edits, which can
only ever return zero.

**Round 1 — 24 prose edits across 18 posts** in `content/blog/posts.json`, in the same voice `9d903cac`
used:

- **The margin formula — 6 edits, the important ones.** "purchase rate plus ₹2.50/sq.ft" and its variants
  on jamnagar, aurangabad, agra, bhilwara (×2) and udaipur. Printed beside a sell rate, that formula
  discloses your purchase rate by subtraction.
- **The ex-factory rate card — 2 edits.** ₹24–₹42/sq.ft on hubli-dharwad and greater-noida, plus agra's
  per-thickness list (8 mm ₹28, 10 mm ₹31.50, 12 mm ₹33.50, 18 mm ₹42).
- **Jackwood ₹400/cft — 13 edits** across tiruppur, duqm, solapur, gurugram, greater-noida, noida, agra,
  udaipur, jalandhar, dhanbad, bhubaneswar, cuttack and asansol → "quoted on request".
- **The Okoume/Gurjan per-sq.ft delta — 3 edits.** Converted to a qualitative ordering
  (Highest / Mid / Baseline) so the buyer guidance survives without the figures. **This is the one I'd
  flag as a close call** — a relative delta between face veneers does not disclose your cost or margin,
  and you may prefer it restored. `9d903cac` removed it, so I followed your precedent.

**Round 2 — 10 more prose edits and 62 table cells across 11 tables.** The rate cells became
`On request`, which is exactly what `9d903cac` did (its message: "per-sq.ft sell-rate tables on 14 pages
→ On request"; its diff shows `<td>24</td>` → `<td>On request</td>`).

- **Rate-card tables, 11 of them:** tiruppur, karur, duqm, jamnagar, karnal, indore, jalandhar, cuttack,
  durgapur, asansol, and the BWR-vs-BWP explainer.
- **The rule `9d903cac` was actually following, which round 2 adopts: absolute money out, relative
  figures kept.** July replaced the BWR/BWP rate column with "On request" but deliberately **kept** the
  "Premium over MR" percentages (Baseline / 13–25% / 55–73%), because a percentage discloses neither the
  purchase rate nor the sell rate. Round 2 does the same. It also means the birch/okoume conversion in
  round 1 was right: that delta was in ₹/sq.ft, which is absolute.
- **Prose the first pattern could not see:** tuticorin's full ladder written out in a sentence; jackwood
  written as "Rs 400 **/** cft", "Rs 400 **per** cft" and "₹400 **per cubic foot**" (karur, karnal,
  jamshedpur, durgapur, tuticorin, bhilwara); and a tiruppur FAQ offering "indexed pricing against our
  purchase rates" — no number, but it publishes the mechanism.
- **Two round-1 sentences replaced with `9d903cac`'s own wording**, which reads better: jamnagar had a
  dangling modifier, and bhilwara ended up with "on request" twice in adjacent sentences.

Deliberately **left alone**, matching `9d903cac`'s own note: the third-party port-haulage benchmarks on
mundra-vs-pipavav (₹/MT), the triple-wall crate build-cost benchmarks, the BWR/BWP per-container upgrade
deltas, a fumigation-risk figure on the cable-drum guide, and macro export statistics. Those are market
data, not CWI rates. Five pages still refer to "our ex-factory price card" without publishing any figure,
which is fine — `9d903cac` only struck the word "**published**" where bhilwara claimed the card was public.

**Round 3 — three more, found by independent review, two of them serious.**

- **Solapur was publishing the complete eight-thickness ladder in prose, with no currency symbol on any
  number** — "6 mm at 24, 8 mm at 28, 10 mm at 31.5 … 18 mm at 42". Invisible to a money-symbol sweep
  *and* to a table sweep. It escaped the July fix because the table was flattened into a sentence on
  28 August (`4678a8f5`) during the posts.json migration, after July had converted it to "On request".
  It is **live on `origin/cf-live` right now**.
- **The rule from round 2 needed correcting.** "Absolute money out, relative figures kept" is only safe
  when the relative figure stands **alone**. The BWR/BWP page kept the premium percentages (13–25%,
  55–73%) *and* published per-container upgrade costs (₹2,000–4,000, ₹8,000–12,000). The percentage is
  the divisor: 2000/450 ÷ 0.13 = ₹34.2 … 12000/450 ÷ 0.73 = ₹36.5 — four independent derivations bracket
  the blanked ₹33.50 to within about 5%. The absolute figures are now gone and the argument is kept.
- **The same shape on the triple-wall crate post**, where the money is CWI's own build price: a
  "+38–45%" table row plus "₹2,800–₹3,500 to the build cost", "the ₹3,000 premium", "the customer's
  ₹3,000 saving". All three absolutes removed; the percentage stays.

Plus tidy-ups the now-empty tables exposed: two pages date-stamping "Rates as of 9 June 2026" above a
table with no rates, a Durgapur FAQ referring to "the ex-factory rates published above", the Karnal
Okoume row left inconsistent with its own column, the Asansol jackwood/rubberwood distinction my round-1
rewrite had flattened, and the birch post's **meta description** — the text Google displays — still
advertising "the per-sqft cost delta".

**Verified with four detectors, each keyed on a different signal and none of them the pattern the edits
were written from:** ladder-adjacency (a thickness within 40 characters of a ladder value, no currency
symbol required — this is what caught Solapur), margin vocabulary, the absolute-plus-relative shape that
allows reconstruction, and attributes/structured data (meta, og, alt, title, JSON-LD). Result: **zero CWI
sale rates, purchase rates or margin disclosures remain** in the source or in `dist/`. Every surviving
rupee figure was individually classified and is third-party or macro data — port haulage, CFS storage,
tolls, cargo values, export statistics — the categories `9d903cac` named as deliberately kept. All 157
posts build; 1,146 files.

**Three rounds were needed and each round's own check said it was finished.** Rounds 1 and 2 both
verified with a pattern derived from the fix list, which can only return zero. That is worth remembering
next time something needs sweeping.

Also applied, as factual corrections rather than decisions:

- **Melia dubia credit** "Thamoung et al." → **"Akshaya et al."** Mewada Thamoung is the third-listed
  author. Verified against Crossref `10.29321/MAJ.10.601156`, which gives the order Akshaya R, Akhato
  Sumi, Mewada Thamoung, Biswajit Debnath. CC BY 4.0 is conditioned on proper citation, so this is the one
  card whose licence compliance rested on getting the name right.
- **Sal alt text** "AI-assisted **end-grain** visual" → "AI-assisted wood visual". The delivered image
  shows continuous longitudinal fibre, not a transverse cut — the generation prompt had listed that as the
  failure mode to avoid. The entry's provenance already disclaims any grain-identification claim; the alt
  text was contradicting it.

---

## 4. A blocker on publishing ANY of this

This working tree's `LIVE_SHA` is pinned to `4dd77b462955`, but `origin/cf-live` is now `ef44629f`.
`tools/cutover_preflight.py` check 2 will **hard-fail** on that, so nothing can ship until the pin is
re-reviewed and moved. I have not moved it — that is a deliberate release step with its own review, and
it should not ride along inside a content fix.

**Correction to what I first told you: nothing would actually be reverted.** I initially said publishing
as-is would push older copies of PR37 and PR38. That was wrong, and an independent check disproved it by
hashing every file rather than trusting the build's warning. `dist/` and `origin/cf-live@ef44629f` have
identical file sets — 1,146 each, none missing, none extra — differing in exactly the 20 files this work
intends to change. All 24 image blobs added since the pin (including the four AI species visuals) are
present and byte-identical, because they are emitted from the local `assets/photos/files/` tree rather
than carried from the pin; PR37's four redirect rules are present in `dist/_redirects`. So the pin is a
gate to clear, not a danger to fear.

**One real defect found while checking this:** the build's warning and `cutover_preflight.py` both say
**311** carried files. That number is a hardcoded literal and is now wrong — the build actually carries
**827** (822 blobs under `files/` at the pin, plus one workflow and four root files; the banner prints the
true figure). An operator told to "re-review the 311 carried files" would be reviewing under 40% of the
real set. Worth fixing before the next cutover, since that instruction is the guardrail.

---

## Status

Nothing is committed, nothing is pushed, nothing is deployed. The rate-suppression and image-metadata
edits sit uncommitted in `C:/Users/Edwin David/cwi-brand-experience` (`content/blog/posts.json`,
`content/species-media.json`, `docs/encyclopedia-card-completion-2026-09-07.md`) and can be dropped with
`git checkout -- content/ docs/`. The policy inserts and the Neem decision are drafts on this page only.

**Two loose ends recorded rather than fixed, both deliberate:**

- `content/blog/mirror_regions.json` (910 KB) is a parallel archive copy of blog bodies that still holds
  the un-suppressed text, including the original ₹2.80–₹4.50/sq.ft veneer delta. It is **not published** —
  `build.py:1822` sets `BLOG_SRC` to `posts.json` alone — so this is latent, not live. I left it as an
  archive rather than rewriting history in it, but it is the obvious way the rates come back if anyone
  ever re-seeds `posts.json` from it. Worth a comment at the top of that file saying so.
- A pre-existing malformed close tag `</h3<p>` on `plywood-supply-to-tiruppur`, plus nested `<thead>` on
  muscat and ras-al-khaimah. Present on `origin/cf-live` already, unrelated to this work, and the only
  three structural HTML defects across all 157 posts — cheap to fix in a separate pass.
