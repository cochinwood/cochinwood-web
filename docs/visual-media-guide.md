# Cochin Wood image selection, 6 September 2026

`content/visual-media.json` records page introductions, 16 product lines, four
application cards, four order-process steps and seven timber choices. Its 38
references use 33 distinct images, including the earlier `home_hero` retained
for compatibility and the current `experience_hero`. The separate
`content/responsive-media.json` maps 19 originals to 98 verified candidates,
including the original full-size files.

Each entry describes the inspected subject, records a conservative category
and includes a SHA-256 hash. Imagery does not independently establish species,
bond grade, certification, stock, customer work, a shipment or facility
ownership. Keep relevant representative-image and process captions visible.

## Page identity and appropriate reuse

| Placement | Source | Reason |
| --- | --- | --- |
| Current homepage | `/files/Hero%20Optimized/Home.webp` | Existing deep warehouse-aisle illustration. |
| Catalogue | `/files/Hero%20Optimized/Products.jpg` | Material flatlay represents the range. |
| Blog directory | `/files/Brand/home-materials.webp` | Warm window-side plywood samples distinguish guides from the catalogue. |
| Encyclopedia | `/files/Product/specialty-timbers.jpg` | Upright sample fan supports comparison of wood character. |
| Sawn-timber hero and card | `/files/Product/acacia.jpg` | Rough-sawn planks communicate timber rather than borrowing the encyclopedia image. |
| Container-flooring hero and card | `/files/Logo/og/og-container-flooring.jpg` | Thick brown-faced panel with its layered edge visible; no overlaid logo or text. |
| Export family | `/files/Process%20Illustrations/cwi-process-loading.jpg` | Loading is relevant to export; reuse within the destination family is intentional. |

The earlier statement that only a loading illustration was available for
container flooring was incomplete. An appropriate existing representative panel
image was found in the legacy `Logo/og` directory. Its caption is
“Representative panel; grade, thickness and treatment are confirmed in the
specification.” The image does not prove the ordered panel's grade or dimensions.

A product image can usefully repeat between its catalogue card and detail page.
Unrelated page introductions should have their own appropriate scene. Desktop
and mobile copies of homepage process figures are alternative layouts, not two
simultaneously displayed uses.

## Timber choices and responsive coverage

`timber_species` is ordered: `eucalyptus`, `rubberwood`, `acacia`, `mahogany`,
`jackwood`, `silverwood`, `specialty-timbers`. Entries include both `name` and
`label`, plus the normal source, alt text, kind, provenance and hash fields.
The first six scenes show rough-sawn boards with varied colour, grain and cuts;
the final scene is the current upright sample fan beside a window. Labels follow
the earlier catalogue; the images alone cannot establish botanical identity.

The six named-species originals match historical catalogue revision `c59adae9`
byte for byte. All seven current originals also match published revision
`39a4d2c46c3ca6abe2239d93e0e2f7373f86b6da`. Each named species has matching
320, 480, 640 and 960 pixel variants plus its measured original width: 30 newly
registered candidates in addition to the previous 68. Original/320 pairs were
visually compared; intermediate sizes were checked for matching proportions and
scene content. Every candidate's bytes match the pinned published revision.

**Never attach legacy `specialty-timbers-320/480/640/960.jpg` candidates to the
current `specialty-timbers.jpg`.** The current original shows upright samples
beside a window; the older candidates show four blocks on a warehouse bench.
That family is intentionally absent from the responsive map. No matching smaller
files exist for the selected blog or container-flooring image in the reviewed
set; those images currently use their originals.

## Preserved bytes and source inputs

Earlier mirror and later published files can share a filename while containing
different scenes. Three restored warm compositions therefore use distinct URLs:

| Preserved distinct URL | Earlier mirror source |
| --- | --- |
| `/files/Brand/home-materials.webp` | `files/Hero Optimized/Home.jpg`, containing WebP bytes |
| `/files/Brand/contact-materials.jpg` | `files/Hero Optimized/Contact.jpg` |
| `/files/Brand/solid-wood-materials.jpg` | `files/Product/rubberwood.jpg` |

These are unchanged source copies. Existing published URLs retain their bytes.
The latest update adds explicit source inputs for acacia, mahogany, jackwood,
silverwood and the container-flooring panel. This prevents a different earlier
mirror image from silently replacing the selected scene. No image was
re-encoded or generated.

The finger-joint board continues to use representative solid-wood material,
with joint layout confirmed in the specification. The older
`Product/finger-joint.jpg` depicts a stylised triangular joint and should not be
presented as proof of the finished layout offered.

## Verification before publication

After integrating the map and building, run the existing visual-coverage, site,
published-preservation and quote-journey checks. Verify local originals and
responsive candidates resolve with the recorded bytes and measured dimensions.
The preservation check must retain existing URL bytes.

Inspect the homepage, blog directory, catalogue, sawn-timber page,
container-flooring page and encyclopedia at desktop and mobile widths. Confirm
the intended scene at each responsive size: a valid URL alone cannot detect a
same-name/different-scene mistake. The historical source contact sheet at
`docs/visual-media-contact-sheet.html` predates the latest placements; use the
current JSON and rendered pages as the placement authority.
