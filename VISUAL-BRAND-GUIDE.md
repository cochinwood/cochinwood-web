# Cochin Wood visual system — 6 September 2026

The approved restoration uses the image-led pre-cutover site at c59adae9 as its reference, while preserving current truthful copy, accessible behavior and enquiry integration. The historical CSS explicitly locked Bree Serif headings and Poppins body text; older Cormorant/Heebo skill examples do not override that evidence.

## Shared rules

- Forest #1B4332 for headings and major closing bands; teal #007A5E for primary actions; warm white #FAF9F7, white and restrained pale green for surfaces; ink #141414 for text.
- White spacious header, circular logo and visible Cochin Wood wordmark. Light footer. Keep the existing navigation and mobile-menu behavior.
- Editorial headings, generous whitespace and image-led product/application cards. Avoid large repeated prose blocks and crowded outlines.
- Use verified existing images and honest adjacent captions. Process illustrations remain illustrations. No generated manufacturing proof, invented testimonials or unsupported country/production claims.
- Keep keyboard focus, legible captions, 44px-or-larger primary controls, reduced-motion support, and the original field validation/submission behavior.

## Markup contracts

The last CSS layer is assets/visual-system.css. Append it after existing component and legacy styles in the bundle.

- Light hero: .cw-hero.cw-hero--light > .cw-wrap > .cw-hero__layout, with .cw-hero__content and figure.cw-hero__media. A hero media image fills a 4:3 frame; place explicit captions inside figcaption. CTA and proof links use existing classes.
- Sections: .cw-section > .cw-wrap, .cw-section__head for heading/introduction. Optional --soft / --white surfaces.
- Catalogue: .cw-product-grid > a.cw-product-card with .cw-product-card__image > img and .cw-product-card__body containing heading, description and link label.
- Applications/process: .cw-application-grid/.cw-process-grid containing matching -card elements, image, heading and paragraph.
- Story: .cw-story with two direct children (image/figure and text), stacking on mobile.
- Preserved products: .cwp__hero-grid contains .cwp__hero-text and figure.cwp__hero-img; .cwp__hero-caption explains illustrative/representative images. .cwp__gallery holds figure.cwp__gallery-item containing img and figcaption.

All grids use minimum-zero columns to avoid content-driven horizontal overflow. A 96px desktop header becomes 76px below860px, and the existing mobile navigation starts below that header. Gallery/card columns reduce to one on narrow phones. CSS does not inject content, change data, or alter form/event logic.
