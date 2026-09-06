# Cochin Wood brand experience — 6 September 2026

Edwin rejected the initial visual restoration and asked for a stronger site, using West Fraser as a visual benchmark. This iteration retains the actual CWI logo, forest green, warm material imagery and factual business voice, while replacing the repeated light split-hero/card treatment. The previous restoration is a historical baseline, not a user-approved final design.

## Visual direction

- Poppins is the primary display and reading face. Bree Serif remains in the wordmark and selected editorial accents. Remove legacy global `!important` font locks instead of fighting them on every new component.
- Forest #1B4332, teal #007A5E, warm white #FAF9F7 and natural wood colour. Large imagery, sharp quiet edges, fine rules, generous space, restrained controls.
- The homepage has a full-width warehouse illustration, asymmetric product families, industry imagery, a sticky illustrated process sequence, a material encyclopedia story and a prominent enquiry close. Inner pages vary their composition within the same typography, colour and spacing system.
- Image provenance and actual scenes are recorded in `content/visual-media.json` and `docs/experience-media.md`. Illustrations are not evidence of owned facilities, current stock, customer projects or completed shipments. Group heritage dates to 1986; the company dates to 2021. Do not restore unsupported country counts or certification claims.

## Source and motion

`experience_home.py` owns the homepage composition. `assets/experience.css` owns the shell, homepage and catalogue. `assets/experience-inner.css` refines the preserved inner templates. These follow `visual-system.css`. The final `brand-consistency.css` layer normalizes legacy section headings and action shapes while preserving the wordmark and selective hero accents. The deferred, content-addressed `experience-motion.js` supplies optional IntersectionObserver/rAF effects without scroll hijacking or dependencies.

Home, Products, Industries, Export and Blog use the shared section bar from `page_navigation.py`. Blog uses the same shell for topic filters and keeps query/topic choices in the URL. The109 city-guide directory entries use compact text with existing regional metadata. Their individual articles omit the mechanically inserted repeated material lead; authored text, technical content and links remain intact. Technical articles retain their relevant photographic or diagram imagery. Retired gallery files remain available under their published URLs through `content/preserved-media.json`.

`data-reveal` is always visible at rest. `data-parallax` is a gentle image translation inside a clipped visual frame. Matched `data-process-step` and `data-process-image` values activate the desktop process illustration. On narrow screens and with reduced motion, each step carries its own static image. Page text never depends on the animation.

## Screen adaptation and release

Use fluid typography, minimum-zero grids, content wrapping and responsive image crops. Header is 88px desktop / 76px mobile. Keep logo Home links, one quote action in the primary menu, keyboard focus, large primary controls and the existing enquiry submission behavior. Tables scroll within a labelled keyboard-accessible region; the page itself must not overflow.

Build and run all required source/preservation/site checks. `tools/test_responsive_layout.cjs` checks every indexed page at narrow phone and laptop widths, and representative templates across additional and breakpoint-adjacent sizes. Inspect actual desktop/mobile rendering and scroll behavior, including reduced motion. Test quote submission only against local mocks. Publish exact reviewed build bytes and verify the live release.

The final shared body rhythm layer is `assets/content-spacing.css`, loaded after component styles. It reduces stacked padding in catalogue groups, Industries and Blog, plus desktop Home section spacing above1000px. Hero geometry, header/navigation offsets, process-step heights and mobile Home spacing remain governed by their existing components.
