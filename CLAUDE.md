# Cochin Wood public website: source and release rules

## Edit the source, then build

Production is `cf-live` in `cochinwood/cochinwood-web`, served by the Cloudflare Pages project `cochinwood-web` at https://www.cochinwood.in. A merge or push to `cf-live` deploys immediately. Its files are generated publication output.

The current source home is `master` in `cochinwood/cochinwood-web`: `build.py`, `export_section.py`, `content/`, `assets/` and `tools/`. Do not fix production HTML by hand: the next build would overwrite it. Older migration and preparation branches are historical or unmerged work; reconcile reviewed changes into the current source without replacing newer assets or content. A local checkout may be on an obsolete branch, so inspect its branch and commit before editing.

Run `python build.py` to create `dist/`. Page and asset counts change with the source. Use the actual build inventory rather than an old fixed count. A completed source commit is not a completed release: confirm it is included in the reviewed publication tree and verify the resulting production bytes.

## Preserve the agreed visual identity

Read [VISUAL-BRAND-GUIDE.md](VISUAL-BRAND-GUIDE.md). The current direction uses Poppins display/body typography, selective Bree Serif accents, forest green, restrained teal, warm white and larger material imagery. Edwin rejected the initial restoration and requested this stronger brand experience. The historical reference is `c59adae9`. Older skills naming Cormorant/Heebo are superseded by the documented June font unification and this source guide.

`assets/experience.css`, `assets/experience-inner.css` and `assets/experience-motion.css` follow the earlier `visual-system.css` layer. `content/visual-media.json` records inspected media, descriptions and hashes. A file existing in the library does not mean the pages show it. Run the coverage check and inspect actual desktop/mobile rendering before calling a visual change done. Do not replace the image-led site with text-card grids or restore obsolete claims. Illustrations must not be described as evidence of a particular factory, customer project or completed shipment.

## Preserve reviewed production content

`LIVE_SHA` in `build.py` pins the reviewed production tree whose images and root files are carried forward. Review changes before moving it. The 84 export corrections in `content/export/published-patches.json` are source inputs and must remain present in generated pages. The preservation check verifies those visible fragments and 320 existing media/root files. Reuse a different old image under a new URL rather than overwriting a preserved same-name file.

## Required checks and publication

Run `python build.py`, `python tools/check_visual_coverage.py`, and `python tools/check_published_preservation.py` from the source root. Run `python ../tools/check_site.py` from `dist/`.

The build intentionally reports two documented redirect warnings. A production pin warning requires review; an additional missing-media warning is a regression. `STRICT=1` treats even the intentional warnings as failures.

Use `python tools/preview.py` for local extensionless routes. Existing form tests are `tools/test_quote_journey.cjs` (local preview port 8873; all external requests intercepted) and `tools/test_form_measurement.cjs`. Do not submit synthetic leads to the live sales desk during visual QA.

Commit source, rebuild, and publish exact `dist/` bytes through a separate publication worktree and PR into `cf-live`. Use `core.autocrlf=false` for publication checkout and staging. Verify the staged tree matches every built file, require the GitHub site check and Cloudflare preview, and merge the exact reviewed head. Verify the production deployment, purge explicit changed public HTML URLs, then check live pages without a cache-busting query string.

## Fixed decisions

- The Wood Encyclopedia canonical stays `/woods-we-use`. Visible wording may change; the indexed URL does not. Edwin decided this on 31 August 2026.
- Historic `/files/...` paths are migration artefacts. The site is no longer hosted by Zoho Sites.
- The group's heritage dates to 1986. The private limited company dates to 2021.
- The business address identifies the seller. The producing works and visit pin are confirmed for the order or appointment.
- The staff app is a separate repository and deployment. Website changes do not authorize changes to staff data or additional messages to customers.
