# Public content reconciliation — 12 September 2026

Reconciled the reviewed flooring and certification work from `352b0e40` and
`7a1e963e` onto current `master` (`e50b7394`), preserving the September 11 imagery,
metadata, schema and LinkedIn improvements. This is source work, not a release.

The earlier 46-page flooring edit did not cover every table or paragraph. An
independent context scan found 27 pages requiring further clarification, including
explicit thinner-board replacement advice in Pipavav, Nashik, Ludhiana, Manama
and Rourkela. Structural replacement is the owner-confirmed 28 mm product;
thinner packing boards are described as supplementary lining or dunnage.

The certification edit also missed Hyderabad metadata and Hyderabad/Vizag FAQs.
Those now distinguish ISPM-15 plant-health treatment from pharmaceutical,
food-contact and cold-chain qualification. Buyer-side FDA audit context and
explicit non-certification statements are retained. The existing trade-claims
policy is unchanged; its search description now states its 3-day/14-day windows.

The pending loading-table patch was not copied: it fixed 40ft payload counts but
left impossible 20ft counts and claimed that thickness alone changes the limiting
factor. The revised guide uses consistent 650 kg/m³ arithmetic, labels its table as
capacity-only upper bounds and requires a separate whole-sheet layout. At fixed
density the weight/volume relation is independent of thickness. The export FAQ,
hub preservation patch and three related export pages use the same explanation.

References checked on 12 September 2026:

- [Hapag-Lloyd container specifications](https://www.hapag-lloyd.com/en/services-information/cargo-fleet/container.html): actual units vary; dimensions, doors, tare and ratings must be checked.
- [USDA APHIS wood packaging material](https://www.aphis.usda.gov/plant-imports/wood-packaging-material): ISPM-15 concerns pest risk in regulated wood packaging; processed plywood is exempt.
- [IPPC ISPM-15 text](https://www.ippc.int/static/media/files/publication/en/2019/02/ISPM_15_2018_En_WoodPackaging_Post-CPM13_Rev_Annex1and2_Fixed_2019-02-01.pdf): processed-wood exemption and solid-wood packaging scope.

`content/blog/mirror_regions.json` remains a historical import archive, not an
input to the current `build.py` blog builder (`content/blog/posts.json`). Do not
restore archived bodies over the corrected canonical posts. The rendered-content
regressions deliberately examine metadata, tables and JSON-LD as well as prose,
so republishing those old claims cannot pass by only correcting visible paragraphs.

Regression command after building: `python -m unittest tools.test_content_claims
tools.test_website_backlog_regressions`. Normal visual, publication-preservation
and site checks remain required for the integrated release.

Validation on the reconciled source (12 September): build 1,156 files; 10 content,
prior-backlog and sitemap-history tests passed; visual coverage passed; all 84
preservation fragments and 320 original assets passed; site check passed on 256
pages, 802 JSON-LD blocks and 15,981 internal links. The live-pin warning remains
for the integration owner to reconcile; the two intentional redirect warnings remain.
The source diff changes 67 city guides and one loading guide against the starting
master, including overlaps among the prior 46-page pass and the additional fixes.
