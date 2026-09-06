# Media for the Cochin Wood brand experience

Reviewed 6 September 2026 against actual source files in this checkout and the
published media tree at `39a4d2c46c3ca6abe2239d93e0e2f7373f86b6da`. Every shortlisted
source file is byte-identical to that published tree. No new media is required;
use the existing URLs and responsive variants. No existing media was changed.

## Selected hero

The strongest existing hero for an immersive treatment is the warehouse aisle.
Tall plywood stacks converge towards a small forklift beneath a long industrial
roof. Warm material colour, alternating light and shade, and strong perspective
give it depth. It can carry large, short typography with a dark overlay and a
small scroll-driven scale change.

```json
{
  "experience_hero": {
    "src": "/files/Hero%20Optimized/Home.webp",
    "alt": "A warehouse aisle between tall stacks of plywood, with a forklift in the distance",
    "kind": "brand illustration",
    "provenance": "Existing published Cochin Wood site asset; original capture or generation provenance is unverified. Use as illustrative brand imagery, not evidence of a particular owned facility or stock position.",
    "sha256": "1b7d40e886e96f805d20298b5b150f750fac51dd5838a49fce3e1f3184a15835"
  }
}
```

Source file:
`C:/Users/Edwin David/cwi-brand-experience/assets/photos/files/Hero Optimized/Home.webp`

Dimensions: **1200 × 860**. File size: **229,148 bytes**. Suggested desktop crop:
16:9, `object-position: 50% 45%`; keep the central aisle/forklift visible. Mobile
can use a taller crop at `50% 48%`. The 640-pixel published responsive variant was
also visually opened and shows the same warehouse scene. Avoid a large scale
increase: this is a 1200-pixel source, so an exaggerated zoom will soften it.

The similarly named earlier mirror asset
`C:/Users/Edwin David/cochinwood-site/files/Hero Optimized/Home.jpg` is a **different
image**: plywood samples leaning by a window. It must not be substituted based on
its filename. That earlier composition remains at `/files/Brand/home-materials.webp`.

## Supporting images

Use these as large sequential material/process views, with changing scale and
composition. Repeating them as small cards would lose the strength of their
texture and framing. The scene descriptions below describe what is visible;
they do not establish plant ownership, a completed shipment, product grade or
certification.

| Placement | Existing URL and actual scene | Dimensions / bytes | Suggested crop |
| --- | --- | --- | --- |
| Material becoming a panel | `/files/Process%20Illustrations/cwi-process-sanding.jpg` — a broad plywood sheet with sweeping grain emerging from a sanding machine | 1600 × 1067 / 246,574 | Desktop 16:9 at 50% 60%; mobile 4:5 at 58% 60%. Preserve the grain and machine mouth. |
| Close inspection | `/files/Process%20Illustrations/cwi-process-moisture.jpg` — a hand holds a pin meter against the cut edge of a plywood panel | 1600 × 1067 / 240,408 | Desktop 16:9 at 48% 50%; mobile 4:5 at 44% 50%. Keep both contact pins visible. |
| Destination and dispatch | `/files/Process%20Illustrations/cwi-process-loading.jpg` — a forklift lifts strapped plywood into an open container, framed by dark doors | 1600 × 1067 / 197,902 | Desktop 16:9 at 52% 48%; mobile 4:5 at 60% 50%. Keep the raised load and fork carriage together. |
| Layers and material identity | `/files/Enhanced%20Factory%20Photos/factory_24.jpg` — a fan of small plywood samples with distinct veneer edges on a timber surface | 1280 × 960 / 112,249 | Desktop 3:2 at 50% 58%; mobile 4:5 at 55% 55%. A tight, generous-scale material view works better than a sample-card thumbnail. |

Actual source paths:

- `C:/Users/Edwin David/cwi-brand-experience/assets/photos/files/Process Illustrations/cwi-process-sanding.jpg`
- `C:/Users/Edwin David/cwi-brand-experience/assets/photos/files/Process Illustrations/cwi-process-moisture.jpg`
- `C:/Users/Edwin David/cwi-brand-experience/assets/photos/files/Process Illustrations/cwi-process-loading.jpg`
- `C:/Users/Edwin David/cwi-brand-experience/assets/photos/files/Enhanced Factory Photos/factory_24.jpg`

The process scenes are already classified as illustrations. The panel fan is a
material illustration. All four files were visually inspected at these source
paths, not inferred from their names. The earlier mirror has no same-name
process files; its `factory_24.jpg` is byte-identical to the selected source.

| File | SHA-256 |
| --- | --- |
| `cwi-process-sanding.jpg` | `8a2e32e9440c52b882de9f9f460c0bd39f3e2b5aa54e65fef21d123cf812fcab` |
| `cwi-process-moisture.jpg` | `2d26cfd93d3bd68d9a81f260576e30555759bc26fedc9956098bdbcd530248cb` |
| `cwi-process-loading.jpg` | `ad44f5ad1160bdae55162d7362080832973d853d894c5d70347646db14661dba` |
| `factory_24.jpg` | `9a911c05a1bbee85d1eb5baabe1fb19a0f4b4f6fced286071677c86fef199c75` |

## Alternatives reviewed and not selected

The preserved `factory_14`, `factory_15`, `factory_16` and `factory_18` images show
industrial equipment and storage. They were inspected from exact published
bytes. Their busy framing, clipped highlights, equipment labels and, in one
case, a visible blur patch make them weaker for the primary hero. Their original
capture provenance and facility ownership are unverified.

Earlier mirror `factory_01` through `factory_04`, `factory_09`, `factory_12` and
`factory_13` show clean warehouse or machinery illustrations. They add little
to the chosen warehouse perspective and would introduce additional source
variants to reconcile. The selected five images provide a coherent material,
process and dispatch sequence using media already in the build.
