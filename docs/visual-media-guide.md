# Cochin Wood image system — 6 September 2026

## Current presentation and integration

The public presentation uses direct subject descriptions and useful specification
captions. Generic image-production labels such as “illustration” and
“representative image” are removed at render time. Source provenance remains in
the manifests. Image captions still explain buyer-relevant qualifications:
container-flooring grade/thickness/treatment, finger-joint layout, and sawn-timber
species/dimensions are confirmed through the specification. Do not remove normal
technical prose such as “representative averages”. Empty navigation anchors must
survive cleanup.

`editorial_media.enhance_editorial_media(body, path, image, link)` runs before hero
normalization. It adds content figures without replacing the original article
prose, removes duplicate hero images from existing product galleries, and adds
useful product-detail/application figures. `article_lead(slug)` supplies a
reviewed lead for all 157 live articles and directory thumbnails.
`article_share_media(slug)` returns a related raster image for social cards and
schema when the on-page lead is an SVG diagram.

Data contracts:

- `content/visual-media.json`: established page/product/application/process
  assignments, 16 products and seven commercial timber choices. Finger-joint
  board now has a clearly visible splice instead of generic unjointed samples.
- `content/editorial-media.json`: all 157 article leads, 16 product gallery
  supplements, three generated product/application scenes, eight authored
  technical diagrams, and four useful visuals for additional guide pages.
- `content/species-media.json`: all 28 encyclopedia entries, with 28 botanical
  references and 17 additional scientific wood-collection specimens.
- `content/responsive-media.json`: 87 verified original-to-candidate groups,
  totalling 339 candidates. Every candidate is an explicit, resolvable source
  input and must be registered/copied by the build.
- `content/responsive-derivatives.json`: original hashes, dimensions, byte sizes
  and encoding notes for derivatives made from existing site assets.

New web assets are under `assets/photos/files/Editorial`, `Species` and
`Responsive`. Seventy-five missing legacy candidate inputs were copied from the
immutable PR29 baseline to their original `assets/photos/files/...` paths, only
after checking their recorded SHA-256 hashes. These are copies of existing
published bytes, not replacements with different scenes.

## Responsive images and preserved assets

Existing public asset bytes are preserved. New compressed derivatives have
distinct URLs. The existing homepage warehouse composition is unchanged; the
reviewed 1200-pixel WebP derivative is 117,236 bytes versus 229,148 bytes for the
original, a 48.8% reduction. Its 400, 640, 960 and 1200 pixel candidates are made
from the same inspected original. The landscape sizing contract remains for desktop and wider tablets.
`content/home-art-direction.json` additionally supplies two exact pixel crops:
590×860 for viewports up to 480px (60,276 bytes), and 762×860 for viewports up
to 620px (79,650 bytes). Both preserve the original 57% object-position through
the nested cover crop within less than one source pixel. The narrower master
uses 73.7% fewer bytes than the original 229,148-byte landscape image. The
original scene and 700px narrow-phone image stage remain unchanged.

Every currently assigned page-hero source from the earlier placement audit has a
responsive group. Existing embedded EXIF/XMP/ICC metadata is retained when it
exists. No crop, fabricated detail or upscaling was introduced in these
compression derivatives. Merely naming a legacy file “Factory” does not prove
that it documents owned premises, a shipment, stock, or a customer project.

The old `specialty-timbers-320/480/640/960.jpg` files depict a different scene from
the currently selected original. They remain excluded. The current upright
sample fan now has its own matching derivatives in `Responsive`.

The build must register each srcset candidate individually. It is insufficient
to add URLs to HTML and rely on the legacy carry-forward set: new candidate files
otherwise remain inside the excluded `assets/photos` directory. Missing files,
wrong widths and hash mismatches should fail the build or release audit.

## Species images: identity and licensing

Every species reference retains its actual pictured taxon, file-page URL,
source description, credit, license link, original/source hash, derivative hash
and adaptation note. Source identity and license were checked using Wikimedia
file metadata, and each actual downloaded image was viewed in the contact
sheets. All source licenses used here permit commercial reuse: public domain,
CC0, CC BY or CC BY-SA. Attribution and license links appear alongside the
reference images. Credit/source metadata is also embedded in WebP XMP.

Seventeen wood photographs originate from CIRAD's digitized xylarium. CIRAD's
[collection documentation](https://numba.cirad.fr/numba/fr/content/les-sous-collections-xylotheque)
explains the scientific specimen collection and its metadata. The selected file
records name the source taxon or timber group; the Wikimedia records mark these
scans as public domain. Exact source-file records are retained in the manifest.

The scientific wood specimens cover acacia-mangium, gmelina, gurjan/keruing,
mahogany, mango, meranti, okoume, pine, rubberwood, semul, sheesham, silver-oak,
teak, casuarina, subabul, irul and pala. These are existing specimen photographs;
no grain texture was generated. No end-grain view is claimed where the source
shows only a wood surface.

For trade groups, the caption states the photographed example accurately:

- The birch botanical image is *Betula pendula*, not every birch species.
- The eucalyptus source label is *Eucalyptus globulus* subsp. *maidenii*.
- Keruing wood is labelled *Dipterocarpus* spp.; the botanical photograph is
  *Dipterocarpus alatus*.
- Meranti wood is labelled as the red-meranti *Shorea* group; the botanical
  photograph is *Shorea leprosula*.
- The pine wood specimen is *Pinus caribaea*; the botanical image is *Pinus radiata*.
- The mahogany references show *Swietenia macrophylla*, not *Toona ciliata*.

The remaining eleven entries have licensed, taxon-identified botanical
references rather than an invented grain image. Botanical identification in a
published source is evidence for the pictured subject; it is not an independent
wood-anatomy examination, a certification of stock, or a promise that natural
material will match a photograph exactly.

## Article and product imagery

The 48 substantive articles have title-reviewed subject assignments. The 109
supply-location articles use relevant material photographs selected from the
products actually discussed in their source text. They do not pretend to show a
warehouse, customer or shipment in the named city. Intentional reuse in this
family is preferable to fictional location photography.

The eight diagrams explain veneer layers, three board-core constructions, panel
dimensions, packing-case structure, container weight/space limits, an enquiry
specification, floor-panel support, and cable-drum flange dimensions. They are
code-native SVG assets with explicit dimensions and readable alternative text.
Eight mobile SVG variants use 600px-wide portrait layouts with 25–34px native
text and preserve every original diagram text token. Picture sources carry
their own width/height so the alternate aspect ratio reserves the correct
space. These are responsive layouts of the same diagrams, not eight new topics.
They contain no invented test results, capacity figures, certifications or
regulatory approval stamps. Full-size diagram links support closer inspection.

Product galleries pair material/detail information with suitable applications.
The existing hero remains the product identifier; an exact hero duplicate is
removed from a gallery before supplements are added. The container-flooring
sample remains a panel photograph, and the commercial sawn-timber hero remains
rough-sawn boards. Scientific species visuals are kept separate from generic
commercial timber catalogue images.

Additional guide visuals accompany `/export-process`,
`/rubberwood-plywood-container-weight`, `/plywood-price-guide` and
`/blogs/gcc-export`. Policy pages, the machine-readable LLM page, FAQ and the
price-tracker utility do not need decorative photography.

## Generated assets and original prompts

Three assets were created with the built-in `image_gen` tool and visually
inspected on 6 September 2026. The originals remain in the Codex generated-image
folder recorded in the manifest, and all web-consumed final variants are saved
inside this repository. Each generated WebP variant includes the IPTC XMP
DigitalSourceType value
`http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia`.
Generation metadata is internal; the public captions describe the material or
application naturally. These images do not identify a named customer, factory,
shipment, exact species or tested product grade.

### Cabinetry — built-in prompt

Use case: product-mockup. Create one premium editorial application image for
Cochin Wood Industries website showing a precise, modern fitted plywood cabinet
in a calm residential interior. Wide landscape composition 3:2, clean
architectural product photography, focus on an open cabinet door revealing pale
plywood edge laminations and tidy joinery; warm natural oak-like wood neutral
material tone, forest-green painted niche or wall as restrained accent, daylight,
realistic high-detail material, generous visible cabinetry occupying the frame.
This is a material/application concept, not a named customer project. No people,
logos, brand names, labels, certifications, watermarks, text, fabricated factory,
or busy props. Do not add fantastical geometry. Create a finished professional
photograph-style image, not a collage or webpage.

### Packing case — built-in prompt

Use case: product-mockup. Create one premium plywood industrial-packaging
application image for Cochin Wood Industries website. Wide 3:2 landscape,
isolated product presentation on a warm cream neutral studio floor with soft
daylight, a sturdy partially open wooden shipping crate constructed correctly
from a plywood panel shell with solid timber perimeter battens and timber pallet
skids; inside is a simple unbranded grey precision motor secured by proper timber
blocking on its base, clearly show structural support and a separate lifted
plywood lid leaning nearby. Close three-quarter viewpoint, packing construction
occupies most of frame; authentic plywood layered edges, warm natural wood,
minimal forest-green backdrop accent. Focus on materials and packing
arrangement, not a named shipment or customer's goods. No people, factory or
port, no text, no stamps, no certification or logos, no watermarks. Clean
restrained professional product-photography look, sharp realistic geometry, no
collage or website interface.

The chosen output visibly shows the shell, battens, skids and motor. The caption
does not claim that hidden internal blocking or cargo restraint has been
verified; that part of the prompt is not independently established by the view.

### Finger-joint detail — built-in prompt

Use case: product-mockup. Create one premium plywood-material educational
product image, wide 3:2 composition, of three finished finger-jointed solid wood
boards in pale warm natural timber, resting horizontally on a warm cream studio
surface. Most important subject: one close, clearly visible conventional finger
joint zigzag end-grain splice running across the board width, with realistic
fine interlocking tapered fingers properly joined flush, normal straight grain
switching subtly at the splice, no gap, no impossible jagged board outline. One
main board in foreground fills most of frame, two plain supporting boards behind
it, modest shallow depth of field, soft daylight and subtle forest-green
backdrop. Precise credible joinery study with matte unfinished texture, not a
specific wood species or proof of any tested grade. No labels, text, logos,
badges, watermark, no people, no factory or brand documentation. Natural
professional catalogue photography, not diagram or collage.

## Verification and evidence

The source-only transformation dry run covered all 253 indexed pages, with all
157 article figures and 28 species sections present and no image-production
labels left in the checked captions. All 339 responsive candidate source files
resolve and match their recorded hashes. The source inputs and metadata are
ready for the integrated browser/image-decoding and preservation gates; those
release checks are separate from an image contact-sheet review.

Contact sheets and raw source/license records are saved in the shared task
artifact folder as `editorial-assets-contact.html/png`,
`species-contact-botanical-1.html/png`, `species-contact-botanical-2.html/png`,
`species-contact-wood.html/png`, and `species-selected-raw.json`. The final
rendered-site checks must verify that every candidate is copied and resolves,
that crop/contain rules are correct, that credits remain readable, and that
article text, product details and navigation anchors remain intact.


Final integrated candidate audit (878 output files): all 254 currently indexed
canonical pages were scanned; 247 contain main-content images and the seven
image-free routes are intentional utility/policy pages. All 339 declared raster
candidates exist in the output, decode, match their recorded hashes and have the
correct widths. All eight mobile SVG sources resolve and preserve the original
diagram information. All twelve generated WebP variants retain the expected
IPTC DigitalSourceType metadata. No image-production labels or missing image /
picture-source references were found. The UI audit confirms the mobile diagram
at 390px uses the 600×850 source at 342×484.5 CSS pixels without overflow, and
mobile Home selects the correct portrait family. These checks do not themselves
constitute a production deployment or a field certification of a material.


Catalogue performance follow-up: the unchanged 1200×860 material flatlay at
`/files/Hero%20Optimized/Products.jpg` now uses a distinct WebP response family
at 320, 480, 640, 720, 768, 960 and 1200 pixels. The 720px version is 19,290
bytes, compared with 80,184 bytes for the previously selected 960px JPEG
(75.9% smaller). The 1200px WebP master is 70,674 bytes. The original JPEG
and its legacy variants remain unchanged. All 341 candidate source files
pass decode, recorded SHA and measured-width checks. The full-size master and
720px output were visually inspected; the source scene, crop and geometry are
unchanged. Browser selection and Lighthouse must be rechecked after the next
integrated build; earlier output totals above describe the preceding build.
