"""Regression checks for unsigned, self-declared AI-card XMP metadata."""
import copy
from pathlib import Path
import shutil
import sys
import tempfile
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

    def test_verifier_rejects_stale_responsive_and_master_hashes(self):
        species = provenance._load(provenance.SPECIES_MANIFEST)
        responsive = provenance._load(provenance.RESPONSIVE_MANIFEST)
        stale_responsive = copy.deepcopy(responsive)
        stale_responsive["/files/Species/neem-ai-visual.webp"][0]["sha256"] = "0" * 64
        self.assertIn("responsive SHA-256 is stale", "\n".join(provenance.pending_changes(species, stale_responsive)))
        stale_master = copy.deepcopy(species)
        stale_master["neem"]["withheld_card_visual"]["sha256"] = "0" * 64
        self.assertIn("card master SHA-256 is stale", "\n".join(provenance.pending_changes(stale_master, responsive)))

    def test_write_preserves_image_payloads_and_refreshes_fixture_hashes(self):
        species = provenance._load(provenance.SPECIES_MANIFEST)
        responsive = provenance._load(provenance.RESPONSIVE_MANIFEST)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = root / "files"
            for _slug, _entry, item in provenance.generated_cards(species):
                for candidate in provenance.card_candidates(responsive, item):
                    source = provenance.asset_path(candidate["src"])
                    target = provenance.asset_path(candidate["src"], files)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
            species_path, responsive_path = root / "species.json", root / "responsive.json"
            stale_species, stale_responsive = copy.deepcopy(species), copy.deepcopy(responsive)
            neem = provenance.asset_path("/files/Species/neem-ai-visual.webp", files)
            original = neem.read_bytes()
            chunks = []
            for name, data in provenance._chunks(original):
                if name == b"XMP ":
                    continue
                if name == b"VP8X":
                    data = bytes([data[0] & ~provenance.XMP_FLAG]) + data[1:]
                chunks.append(provenance._chunk(name, data))
            stripped = b"RIFF" + (b"WEBP" + b"".join(chunks)).__len__().to_bytes(4, "little") + b"WEBP" + b"".join(chunks)
            neem.write_bytes(stripped)
            stale_responsive["/files/Species/neem-ai-visual.webp"][0]["sha256"] = "0" * 64
            stale_responsive["/files/Species/neem-ai-visual.webp"][-1]["sha256"] = "0" * 64
            stale_species["neem"]["withheld_card_visual"]["sha256"] = "0" * 64
            provenance._write_json(species_path, stale_species)
            provenance._write_json(responsive_path, stale_responsive)
            before_payloads = [(name, data) for name, data in provenance._chunks(stripped)
                               if name in {b"VP8 ", b"VP8L", b"ALPH"}]
            changed = provenance.update(species_path, responsive_path, files)
            written = neem.read_bytes()
            after_payloads = [(name, data) for name, data in provenance._chunks(written)
                              if name in {b"VP8 ", b"VP8L", b"ALPH"}]
            self.assertIn(neem, changed)
            self.assertEqual(before_payloads, after_payloads)
            self.assertEqual(provenance.pending_changes(
                provenance._load(species_path), provenance._load(responsive_path), files), [])

    def test_writer_rejects_malformed_duplicate_xmp_and_c2pa_containers(self):
        image = provenance.asset_path("/files/Species/neem-ai-visual.webp").read_bytes()
        duplicate = image + provenance._chunk(b"XMP ", provenance.xmp_payload(image))
        duplicate = b"RIFF" + (len(duplicate) - 8).to_bytes(4, "little") + duplicate[8:]
        with self.assertRaisesRegex(ValueError, "more than one XMP"):
            provenance.with_xmp(duplicate, b"<xmp/>")
        malformed = image[:16]
        with self.assertRaisesRegex(ValueError, "RIFF length|Truncated"):
            provenance.with_xmp(malformed, b"<xmp/>")
        claim = provenance._chunk(b"JUMB", b"claim")
        claimed = b"RIFF" + (4 + len(claim)).to_bytes(4, "little") + b"WEBP" + claim
        with self.assertRaisesRegex(ValueError, "C2PA/JUMBF"):
            provenance.with_xmp(claimed, b"<xmp/>")


if __name__ == "__main__":
    unittest.main()
