# Compact export destination guides

The 28 existing `/export/{country}` pages use compact, branded introductions. Their repeated decorative loading photograph has been removed. The `/export` hub keeps its shared image hero.

Each guide retains its original heading, introduction, factory-stock clarification, quote and WhatsApp actions, byline, research, import table, FAQs and links. No new port, transit, compliance or business claim has been added. Desktop introductions place the heading beside the supporting text; phone layouts stack them without an empty media column. Both use the existing forest/teal palette, Poppins typography, selective Bree Serif accent and shared gutters.

Country sharing metadata retains the existing Cochin Wood brand image. The ownership manifest explicitly approves the 28 source-backed country routes as text guides. `unique_imagery.is_text_guide` accepts these exact source country records, plus the previously approved 109 Blog location guides. It rejects unregistered export paths, the Export hub, technical articles, unapproved decisions and missing reasons. The full gate still requires 185 owners; the Blog scope still requires 157 articles, including 48 article images and 109 location guides.

Validation:

- `python tools/test_export_text_guides.py` renders all 29 export pages in memory, verifies compact country heroes and branded sharing, preserves the hub photo, and compares the complete content signatures.
- `python tools/export_guide_preservation.py` compares built output against `tools/fixtures/export-guide-preservation-pr34.json`. The baseline includes ordered text blocks, links, anchor IDs, table text, sharing metadata, structured data and exact export source-file hashes. Only decorative hero media is excluded.
- `python tools/test_unique_images.py`, `python tools/test_unique_image_scope.py` and `python tools/test_location_guide_preview.py` cover explicit policy approval, valid source routes, full release scope and unchanged Blog rules.
- `python tools/check_unique_images.py` runs the complete 185-owner release gate; no reduced-scope flag is needed for this change.

Source tests pass. The coordinated rendered review and publication receipts are maintained with the release artifacts; this document does not claim a live deployment.
