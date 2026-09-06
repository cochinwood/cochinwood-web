# Cochin Wood image selection, 6 September 2026

`content/visual-media.json` is the reviewed placement map: five page introductions,
16 product families, four application cards and four order-process steps. These
29 placements use 25 distinct images. The source contact sheet is
`docs/visual-media-contact-sheet.html`; open it from a server rooted at this source
checkout to see the exact files referred to by the map.

The map describes the visible subject, records a conservative media category and
includes the SHA-256 of the actual inspected source bytes. Descriptions do not
establish wood species, bond grade, certification, current stock, a customer
project, a shipment or ownership of a facility. Process and application scenes
are illustrations and should remain visibly identified as such in their section.

## Restored material introductions

The earlier mirror and later published site reuse some filenames for different
images. An initial selection confused those versions; the delivered selection
was corrected by inspecting the actual source files and assigning the earlier
material compositions separate URLs:

| New URL | Actual subject | Original local mirror source |
| --- | --- | --- |
| `/files/Brand/home-materials.webp` | Leaning plywood samples beside a sunlit window | `files/Hero Optimized/Home.jpg` (WebP bytes) |
| `/files/Brand/contact-materials.jpg` | Small plywood panels stacked on a timber table | `files/Hero Optimized/Contact.jpg` |
| `/files/Brand/solid-wood-materials.jpg` | Smooth solid-wood boards stacked beside a window | `files/Product/rubberwood.jpg` |

These three files are copied unchanged into `assets/photos/files/Brand/`.
Existing `/files/` URLs retain their published bytes, including the warehouse
aisle at `Hero Optimized/Home.webp`, loading scene at `Hero Optimized/Contact.jpg`
and rough-sawn material at `Product/rubberwood.jpg`.

The catalogue flat lay, product presentations, industry applications and process
illustrations use existing published files. Every existing-URL source input in
this change was byte-compared with `origin/cf-live`; none was changed. The
additional eucalyptus input is the published image of rough-sawn slabs on a
warehouse floor, not the different version in the earlier mirror.

## Contextual product choices

There is no verified container-floor product photograph in the preserved image
library. Its loading illustration supplies context and has an explicit caption:
“Container loading illustration; flooring grade and treatment are confirmed in
the specification.” It must not be described as a photograph of the specified
floor panel.

The previous `Product/finger-joint.jpg` depicts a stylised triangular joint,
which does not reliably demonstrate the finished finger-joint board offered.
The replacement is a material illustration, labelled “Representative solid-wood
board samples; joint layout is confirmed with your specification.”

## Checks before publication

Run `python tools/check_visual_coverage.py` after `python build.py`. It checks:

- Every page family loads the same fingerprinted brand stylesheet, with the
  approved fonts, colours and reduced-motion treatment present.
- Local image files and responsive candidates exist; content images have alt
  text and dimensions to reserve their layout space.
- Every promised image ships with the exact bytes visually inspected here.
- The home, catalogue, contact, encyclopedia and export introductions include
  images; each of the 16 product families has an image in its own page and an
  illustrated link from the catalogue.
- The homepage retains imagery throughout its product, application and process
  story, rather than passing because the logo or one photograph still exists.
- Narrow checks catch previously removed, unsupported marketing claims.

The unmodified source baseline fails this check for the missing home sections,
text-only catalogue, missing catalogue/contact/encyclopedia/export introductions
and absent container-floor product imagery. This is the intended negative
control for the regression that prompted the upgrade.

Also run the existing site, published-preservation and quote journey checks.
Static image coverage does not establish aesthetic quality: inspect each page
template on desktop and mobile before publishing.
