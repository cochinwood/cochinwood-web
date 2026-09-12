# Website review release — 12 September 2026

## Baseline and authorization

Edwin authorized completion of the eight tasks from the 12 September website review: unsupported claims, container calculator, returns descriptions, source/publication reconciliation, enquiry verification, remaining technical corrections, measurement baseline, and substantiated manufacturing evidence.

Source `origin/master` was `e50b7394`; live `origin/cf-live` was `5e8fdcf484f7659cc178385978a01e4decc34497`. Cloudflare confirmed production deployment `74901632-4ebd-4309-ae53-d3f1335d0b6f` for that live commit. Before edits, a fresh build of the source reproduced all 1,156 production files byte for byte: zero added, zero missing, zero changed. This verified the later Premium Hardwood, optimized species images, metadata, and LinkedIn work was present before integrating older pending corrections.

That byte comparison is the basis for advancing the carried-asset pin to `5e8fdcf4`. The existing immutable bundles and preserved file URLs must remain available alongside new bundles. The pin is a reviewed input, not a moving reference.

## Completion vocabulary

- **Implemented:** source changes exist and their relevant checks pass.
- **Published:** the reviewed publication commit has a successful production deployment.
- **Verified live:** ordinary public URL requests return the approved content and relevant browser interactions work.
- **Needs evidence:** the required business facts or original media have not been substantiated. Source text or an image filename cannot substitute for evidence.

A source commit, a passing build or a saved note alone must never be recorded as a completed live fix. A publication branch alone is not a published release. Source and publication must be linked with a file-hash manifest and deployment identity.

## Release procedure

1. Commit reviewed source on a branch based on current `master`; inspect pending changes individually and retain newer source work.
2. Run the required build, coverage, preservation, site and affected browser tests. Use the built artifact for calculator testing, since the content sanitizer removes inline script.
3. Use `tools/cutover_preflight.py` to verify the current production pin, clean source, reproducibility and retained URLs.
4. Copy the exact built files to an isolated publication worktree based on current `cf-live` with `core.autocrlf=false`.
5. Run `tools/verify_publication.py` against the staged publication tree. Its report must have zero added, missing or mismatched files.
6. Open source and publication PRs, verify required checks and Cloudflare preview, then merge the reviewed heads. Recheck remote heads before merging to preserve concurrent work.
7. Confirm Cloudflare's successful production deployment identifies the publication merge commit. Purge explicit changed HTML and sitemap URLs on apex and www, then verify ordinary live requests and key browser interactions.
8. Save a dated receipt identifying source, publication, deployment, checks, hash inventory, live verification and unresolved evidence needs. Update the tracker using the vocabulary above.

The private measurement and live verification receipts are deliverables in the review task's outputs directory. They must not be copied to `dist/`.

## Completed release — 13 September 2026

Source PR #51 merged as `ebc7732ce9f222411005a0b760f43a763bc046a9`; its reviewed implementation was `83e933f5b0f2736446004b0550d21832dc535f99`. Publication PR #52 merged as `8514f52e0fac57ad66aeab38e2962e883e935879`, matching all 1,158 tested files exactly. Cloudflare production deployment `d71a50ab-bb60-4d59-9c43-3a65fb4b15ea` succeeded on 12 September at 10:35:56 UTC and was reconfirmed on 13 September. This section records completion and does not change generated content or advance the next release's carried-asset pin.

| Review item | Completion |
|---|---|
| Unsupported certification claims | Corrected in the affected city guides, descriptions and FAQs; published and verified live. |
| Container calculator | External fingerprinted controller restored; conservative flat-stack and payload model, packing allowances, validation and accessible results tested and verified live. |
| Returns descriptions | Metadata now agrees with the B2B policy; published and verified live. |
| Source and publication reconciliation | Source, publication, exact file hashes, deployment identity and ordinary-URL checks recorded. |
| Enquiry journey | Local native-post, multi-item, validation, retry and confirmation tests passed. One labelled live monitor enquiry passed the normal browser verification and was saved once with two separate product specifications. The monitor path intentionally skips staff notifications; its JSON response was blocked by Chrome after the save. Existing genuine-enquiry records showed provider acceptance on the assigned and both owner notification routes. Inbox arrival/read was not independently verified. |
| Remaining technical/loading corrections | Corrected the wider guide and export FAQ/market wording; payload/volume ceilings are distinguished from an actual loading arrangement. |
| Measurement baseline | Actual Search Console, Analytics and accepted-enquiry baseline saved privately with periods, exclusions and limitations. |
| Company evidence and imagery | Order-verification checklist published and linked from About/factory. Edwin confirmed that approved AI-modified marketing imagery should remain. Original-photo replacement and new documentary case studies are optional enhancements, not release blockers. |

Release checks passed: 20-check cutover preflight; two identical builds; existing public-path coverage; 84 preserved export fragments and 320 assets; visual coverage; generated-site consistency; content/publication tests; calculator arithmetic/browser checks; multi-product quote journey; form counters; and 31 consent/search-measurement assertions.

The first production check caught stale edge copies despite a successful deployment. Cloudflare's connector lacked cache-purge permission, so targeted purges were completed through the existing authenticated dashboard. On 13 September, 18 confirmed URL-purge batches covered 514 URLs: every changed HTML path and the sitemap on apex and www. The final HTTP scan verified all 255 public content pages, seven apex aliases and nine fingerprinted assets against the approved bytes, with zero failed requests or stale content pages. A nonexistent route returned the exact custom 404 document and HTTP 404; direct `/404.html` follows the existing redirect to home and was not counted as a content-page success.

The live calculator was also operated after the final purge: 20ft/18 mm returned 242 sheets, 13.0 m³ and 8.7 t including packing; switching to the default 40ft/12 mm returned 728 sheets, 26.0 m³ and 17.2 t. These remain labelled planning assumptions, not shipment commitments.
