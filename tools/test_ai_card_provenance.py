"""Regression checks for unsigned, self-declared AI-card XMP metadata."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import ai_card_provenance as provenance


class AICardProvenanceTests(unittest.TestCase):
    def test_all_generated_cards_have_the_expected_xmp_and_hashes(self):
        species = provenance._load(provenance.SPECIES_MANIFEST)
        responsive = provenance._load(provenance.RESPONSIVE_MANIFEST)
        for slug, entry, item in provenance.generated_cards(species):
            expected = provenance.card_xmp(slug, entry, item)
            for candidate in provenance.card_candidates(responsive, item):
                with self.subTest(species=slug, image=candidate["src"]):
                    image = provenance.asset_path(candidate["src"])
                    blob = image.read_bytes()
                    self.assertEqual(provenance.xmp_payload(blob), expected)
                    self.assertIn(provenance.AI_SOURCE_TYPE.encode("ascii"), expected)
                    self.assertIn(item["source_url"].encode("utf-8"), expected)
                    self.assertFalse(provenance.has_c2pa_claim(blob))
                    self.assertEqual(candidate["sha256"], provenance.digest(image))
            self.assertEqual(item["sha256"], provenance.digest(provenance.asset_path(item["src"])))

    def test_provenance_writer_is_idempotent(self):
        self.assertEqual(provenance.pending_changes(), [])


if __name__ == "__main__":
    unittest.main()
