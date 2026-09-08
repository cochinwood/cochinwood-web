"""Premium Hardwood publication stays provenance-bound and quotation-only."""
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "assets/photos/files/Premium-Hardwood/premium-hardwood-family-original-2026-09-08.jpg"
HERO = ROOT / "assets/photos/files/Premium-Hardwood/premium-hardwood-hero-v2-2026-09-08.png"
HERO_WEBP = ROOT / "assets/photos/files/Premium-Hardwood/premium-hardwood-hero-v2-2026-09-08.webp"
PAGE = ROOT / "content/pages/premium-hardwood-plywood.html"


class PremiumHardwoodPhotoTests(unittest.TestCase):
    def test_reviewed_asset_bytes_and_manifest(self):
        manifest = json.loads((ROOT / "content/visual-media.json").read_text(encoding="utf-8"))
        media = manifest["draft_products"]["premium-hardwood-plywood"]
        self.assertEqual(hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
                         "9115bc38f8524cdf217136b834634c98cef1c7b4ee5c2a529c95902d8a6cb1df")
        self.assertEqual(hashlib.sha256(HERO.read_bytes()).hexdigest(),
                         "65fb08829dc376f9064281654ed4e9115d594b069472a65b2556368c3c1d778a")
        self.assertEqual(hashlib.sha256(HERO_WEBP.read_bytes()).hexdigest(),
                         "7e5821f82dda291d4f008359c3fbaff7e097166c2111ebde53d3fca4edad69ea")
        self.assertEqual(media["sha256"], hashlib.sha256(HERO_WEBP.read_bytes()).hexdigest())
        self.assertEqual(media["generated_artifact_sha256"], hashlib.sha256(HERO.read_bytes()).hexdigest())
        self.assertEqual(media["source_sha256"], hashlib.sha256(ORIGINAL.read_bytes()).hexdigest())
        self.assertEqual((media["width"], media["height"]), (1448, 1086))
        self.assertEqual((media["source_width"], media["source_height"]), (938, 1280))
        self.assertNotIn("caption", media)
        self.assertIn("not thickness-specific proof", media["scope"])

    def test_page_is_the_only_product_page_using_these_assets(self):
        references = []
        for candidate in (ROOT / "content/pages").glob("*.html"):
            text = candidate.read_text(encoding="utf-8")
            if "premium-hardwood-hero-v2-" in text:
                references.append(candidate.name)
        self.assertEqual(references, ["premium-hardwood-plywood.html"])

    def test_page_is_quote_only_and_does_not_invent_open_specs(self):
        page = PAGE.read_text(encoding="utf-8").lower()
        self.assertIn("request a quote", page)
        self.assertIn("online purchasing is not open", page)
        self.assertIn("full hardwood core", page)
        self.assertIn("12 mm and 18 mm", page)
        self.assertIn('alt="premium hardwood plywood"', page)
        self.assertIn('/contact#quote', page)
        self.assertNotIn("owner-approved", page)
        self.assertNotIn("approved source", page)
        self.assertNotIn("ai-edited", page)
        self.assertNotIn('href="/files/premium-hardwood/', page)
        for unsupported in ("gurjan", "muf", "bwr", "is 303", "is 710", "marine", "₹"):
            self.assertNotIn(unsupported, page)
        build = (ROOT / "build.py").read_text(encoding="utf-8")
        products_block = build.split("PRODUCTS = [", 1)[1].split("]", 1)[0]
        self.assertNotIn("premium-hardwood-plywood", products_block)

    def test_catalogue_records_verified_live_image_without_activation(self):
        catalogue = json.loads((ROOT / "commerce-preview/config/catalogue.proposed.json").read_text(encoding="utf-8"))
        hardwood = [item for item in catalogue["products"] if item["sku"].startswith("prem_hw_")]
        self.assertEqual(len(hardwood), 2)
        self.assertTrue(all(item["image_approved"] is True for item in hardwood))
        live_image = "https://www.cochinwood.in/files/Premium-Hardwood/premium-hardwood-hero-v2-2026-09-08.webp"
        self.assertTrue(all(item["actual_product_photo_url"] == live_image for item in hardwood))
        evidence = catalogue["draft_image_evidence"]["premium_hardwood_family"]
        self.assertEqual(evidence["publication_state"], "replacement_published_quote_only")
        self.assertEqual(evidence["replacement_family_image"]["public_url"], live_image)
        self.assertFalse(evidence["catalogue_activation"])
        self.assertFalse(evidence["merchant_activation"])
        self.assertFalse(catalogue["payment"]["enabled"])
        self.assertFalse(catalogue["merchant"]["enabled"])
        self.assertFalse(catalogue["policies"]["approved"])
        decision = catalogue["policies"]["damage_reporting_approval"]
        self.assertEqual(decision["owner_response"], "Within 24 hours of delivery, with photos.")
        self.assertIsNone(catalogue["policies"]["refunds"])


if __name__ == "__main__":
    unittest.main()
