# Commerce preparation: search and species-image check

Read-only audit on **7 September 2026 IST**, begun at 00:47:56 IST (6 September 19:17:56 UTC). This is a bounded follow-up to the current production release, not a deployment receipt or a full indexing audit. Public files were fetched without running website JavaScript; authenticated Google Search Console, Bing Webmaster Tools and Google Analytics dashboards were read in separate browser tabs. No enquiry, purchase, analytics event, indexing request, email or settings change was created. No image was added.

The current destination-guide release is already complete. Its authoritative records are `docs/destination-guides-completion-2026-09-07.md` and the release artifact `destination-guides-live-release.json`; this follow-up does not reopen that release.

## Current live technical checks

| Check | Actual result | Meaning and limit |
|---|---|---|
| [Sitemap index](https://www.cochinwood.in/sitemap.xml) | HTTP 200; valid XML; lists CMS, post and image sitemaps | The index is reachable. This does not prove that all listed pages are indexed. |
| [CMS sitemap](https://www.cochinwood.in/sitemap-cms.xml) | HTTP 200; 97 unique URLs | All listed page URLs use the canonical `www.cochinwood.in` host. |
| [Post sitemap](https://www.cochinwood.in/sitemap-post.xml) | HTTP 200; 157 unique URLs | Together with CMS, the two content sitemaps list 254 page URLs. |
| [Image sitemap](https://www.cochinwood.in/sitemap-images.xml) | HTTP 200; 110 unique page URLs and 321 image placements | Image-sitemap page URLs intentionally overlap content-sitemap URLs. Image placements are not a count of unique photographs. |
| [Robots file](https://www.cochinwood.in/robots.txt) | HTTP 200; general crawling allowed; sitemap advertised | No blanket disallow was present. Individual search-engine decisions remain outside this check. |
| Apex homepage | `https://cochinwood.in/` resolved to the `www` homepage, HTTP 200 | The fetch followed redirects; the intermediate redirect status was not separately measured. |
| Representative HTML | Homepage, `/products`, `/export/uae`, `/woods-we-use/neem`: HTTP 200, correct self-canonical, no meta-robots exclusion | Four representative canonical pages were freshly checked here. This is not a new full-site 254-page crawl. |

## Authenticated search and analytics evidence

The signed-in Google account was `cochinwoodindia@gmail.com`, with access to the `cochinwood.in` domain property.

| Dashboard | Report period / freshness shown | Observed result |
|---|---|---|
| [Google Search performance](https://search.google.com/search-console/performance/search-analytics?resource_id=sc-domain%3Acochinwood.in) | Web search, 5 June–4 September 2026; three-month selection | 817 clicks, 82.9k impressions, 1% CTR, average position 7.5. The period ends before the latest releases, so these numbers cannot measure their effects. |
| [Google Sitemaps](https://search.google.com/search-console/sitemaps?resource_id=sc-domain%3Acochinwood.in) | Both submitted and last read 6 September | Main and image sitemap each show **Success**. Dashboard discovered counts were 500 and 247 respectively. Those asynchronous counts differ from current XML contents and are not evidence of a current fetch failure. No repeated submission was made. |
| [Google Page indexing](https://search.google.com/search-console/index?resource_id=sc-domain%3Acochinwood.in) | Last updated **28 August 2026** | 259 indexed; 171 excluded across seven reasons. This is an old report, not a count of new release defects. |
| [Google Product snippets](https://search.google.com/search-console/r/product?resource_id=sc-domain%3Acochinwood.in) | Last updated **5 September 2026** | 19 invalid items requiring an offer, review or aggregate rating. The former missing-price issue is marked **Passed**, with zero affected items. These are reported structured-data items, not a freshly verified count of current product pages. |
| Google overview experience | Overview read during this audit; underlying report date not opened | Mobile Core Web Vitals: 55 good URLs, zero needs-improvement or poor; desktop has no data. HTTPS: 54 HTTPS, zero non-HTTPS; breadcrumbs: 47 valid, zero invalid. These counts do not establish coverage of all 254 URLs. |
| [Bing Webmaster Tools](https://www.bing.com/webmasters/searchperf?siteUrl=https://www.cochinwood.in/) | 6 June–5 September 2026 | 81 clicks, 3.6k impressions. Bing recommends more relevant high-quality inbound links. No outreach was performed. Fresh Bing sitemap/indexing details were not opened in this bounded pass. |
| [Google Analytics](https://analytics.google.com/analytics/web/#/a316059356p491827563/reports/intelligenthome) | 31 August–6 September, last seven days | Property `cwi-b2b-showcase`: one active user, 82 events, zero key events and two Direct sessions. This is too little data to assess conversion performance or distinguish genuine buyers from internal visits. |
| [Analytics data streams](https://analytics.google.com/analytics/web/#/a316059356p491827563/admin/streams/table?restoreUserState=true) | Status at audit time | Web stream **Cochin Wood — cochinwood.in**, URL `https://www.cochinwood.in`, ID `11307314845`, reports traffic received in the past 48 hours. Another stream named CWI-B2B-Showcase reports no data in that period; it was not deleted or changed. |

The dated indexing exclusions were: 65 not found, 44 redirects, 29 alternatives with proper canonical, three noindex, 26 crawled but not indexed, two Google-selected different canonicals, and two discovered but not indexed. Individual affected URLs were **not** drilled into during this pass. Redirects and canonical alternatives can be intentional historical routes; they should not be mass-rewritten to make the aggregate count smaller.

Observed non-brand query examples were `plywood manufacturers in kerala` (6 clicks / 280 impressions), `block board door` (4 / 462), `neem wood` (2 / 338), and `matti wood` (3 / 109). These are query impressions, **not search-volume estimates**. They support prioritizing useful product/specification and species content, but do not justify invented rankings, regional demand or guaranteed traffic. A country breakdown was not read.

Analytics currently records page views and engagement plus `quote_form_view` (6), `quote_click` (3) and `contact_whatsapp` (1). None of these is proof of a completed sale. A completed-order event in the upcoming commerce work should depend on the real accepted order/payment state and carry no customer contact details.

## Four remaining natural wood references

The earlier `docs/species-grain-completion.md` was reviewed first. Its 52 unique references across 28 species, with real wood references for 24 species, remain unchanged. This pass searched additional exact-taxon research and collection results. **No new photograph passed both the subject and commercial-rights checks.** This is not a claim that no suitable photograph exists elsewhere.

| Species | Additional source examined | Result |
|---|---|---|
| **Melia dubia** | [Saravanan et al., comparative wood-properties study, 2014](https://www.isca.me/rjrs/archive/special_issue2013/47.ISCA-ISC-2013-1AFS-36.pdf) | The primary paper identifies Melia samples from Karnataka and refers to specimen figures. No explicit commercial reuse licence was established in the opened paper or targeted publisher search. The figure screenshot fetch also failed, so the exact usable photograph was not visually verified. It remains a permission-and-image-review candidate, not an accepted asset. |
| **Azadirachta indica** — neem | [Quartey, Eshun and Attitsogbui, 2021, official paper](https://www.scirp.org/pdf/msa_2021111211394496.pdf), DOI 10.4236/msa.2021.1211031 | The paper explicitly grants CC BY 4.0 and identifies Ghanaian neem samples. Its figure is a comparative-strength chart, accompanied by tables; it does not supply the requested natural wood photograph. The licence alone does not solve the image gap. |
| **Shorea robusta** — sal | [Tripathi and Adhikari, 2021, heart-rot study](https://doi.org/10.1155/2021/6673832), with [accessible paper copy](https://pdfs.semanticscholar.org/365e/07421b3a6eca1eb768cb0aee8d8b0f545495.pdf) | The paper states CC Attribution, but its figures are maps, diagrams and charts rather than a grain photograph. A separate [Sal xylothèque entry](https://www.lairdubois.fr/xylotheque/185-sal.html) has identified wood imagery under CC BY-NC-SA 4.0, which was not accepted for the commercial site. |
| **Neolamarckia cadamba** — kadam / kelempayan | [FRIM Timber Technology Bulletin 16](https://info.frim.gov.my/infocenter/booksonline/ttb/TTBNO16.PDF) | The bulletin identifies the correct taxon and lists a Kelempayan image with other timbers. Commercial reuse rights were not established, and the image-page screenshot request failed. It is a possible institutional-permission lead, not a usable approved asset. |
| **Neolamarckia cadamba** | [Current Agriculture Trends, 2024 paper](https://currentagriculturetrends.vitalbiotech.org/aadmin/articles/CAT-2024-3-9-16-19.pdf) | Explicit CC BY 4.0, but the relevant image shows a plantation rather than wood grain. A further [PLOS xylogenesis study](https://pmc.ncbi.nlm.nih.gov/articles/PMC4954708/) is about developing stems; the follow-up figure request was access-limited and no suitable grain photograph was verified. |

Known earlier exclusions still apply: Neem is not Melia merely because the latter is called Malabar neem; Sal cannot be replaced by another Shorea species; modified, dyed or compressed laboratory material should not be represented as natural wood. Smithsonian metadata openness does not grant rights to an image carrying separate usage conditions. No noncommercial image was reused, no synthetic grain was generated, and no permission request or purchase was made.

## Next priorities

| Priority | Action supported by this evidence | Completion condition |
|---|---|---|
| 1 | Give genuinely purchasable commerce variants truthful offer metadata when their price, availability and checkout are operational. Preserve quote-only treatment for the rest. | Visible purchase terms, server data and structured offers agree; do not invent reviews or prices to clear the Product snippet report. |
| 2 | After search reports refresh, inspect the exact affected canonical/404 URLs and compare them with the maintained redirect history. | Fix actual lost canonical pages or unintended exclusions; retain legitimate redirects and canonical alternatives. |
| 3 | Validate commerce measurement using the controlled release tests and real accepted transaction state. | No fake sales, customer PII or duplicate purchase events; distinguish checkout interest from a completed transaction. Existing tiny GA totals are not a conversion baseline. |
| 4 | Use observed Kerala/product/species queries to prioritize clearer useful buyer answers and links. | Preserve accurate existing content; assess later with comparable date ranges and adequate data, not a ranking promise. |
| 5 | Obtain species-verified company sample photographs or explicit commercial image permission for the four grain gaps. | Confirm taxon, rights, source photograph and display quality before adding. Existing botanical references remain available meanwhile. |

Access to all three search/analytics dashboards is available; this task does not need another connector. Remaining external dependencies are search-engine recrawling/report freshness and suitable verified image rights or company samples. No current live canonical/sitemap/robots blocker was found in the checks above.
