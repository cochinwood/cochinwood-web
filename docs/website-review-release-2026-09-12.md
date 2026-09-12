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
