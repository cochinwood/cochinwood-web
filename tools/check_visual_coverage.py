#!/usr/bin/env python3
"""Check the public site's image/brand delivery contract, not its aesthetics.

Run after build.py: python tools/check_visual_coverage.py [--dist PATH]
This catches a repeat of the generated-site cutover's image loss: an asset can
exist in the deployment while every product card silently becomes text-only.
Desktop/mobile browser review is still required for visual acceptance.
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def local_path(value):
    """Normalise encoded file names without treating query strings as paths."""
    parsed = urlsplit(value)
    if parsed.netloc and parsed.netloc not in {"cochinwood.in", "www.cochinwood.in"}:
        return None
    return unquote(parsed.path).lstrip("/")


def media_entries(value):
    if isinstance(value, dict):
        if "src" in value:
            yield value
        else:
            for item in value.values():
                yield from media_entries(item)
    elif isinstance(value, list):
        for item in value:
            yield from media_entries(item)


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.images = []
        self.styles = []
        self.text = []
        self.anchors = []
        self.main_depth = 0
        self.muted = 0
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "main":
            self.main_depth += 1
        if tag in {"script", "style"}:
            self.muted += 1
        if tag == "a":
            self.anchors.append(attrs.get("href", ""))
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.styles.append(attrs.get("href", ""))
        if tag == "img":
            self.images.append({**attrs, "in_main": bool(self.main_depth),
                                "link": self.anchors[-1] if self.anchors else ""})

    def handle_endtag(self, tag):
        if tag == "main":
            self.main_depth = max(0, self.main_depth - 1)
        if tag in {"script", "style"}:
            self.muted = max(0, self.muted - 1)
        if tag == "a" and self.anchors:
            self.anchors.pop()

    def handle_data(self, value):
        if not self.muted:
            self.text.append(value)

    @property
    def content_images(self):
        return [i for i in self.images if i["in_main"]
                and "/logo" not in i.get("src", "").lower()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    dist = args.dist.resolve()
    if not (dist / "index.html").exists():
        parser.error(f"No built homepage at {dist}; run build.py first")
    manifest = json.loads((ROOT / "content/visual-media.json").read_text(encoding="utf-8"))
    errors = []
    pages = {}
    linked_image_count = 0
    stylesheet_sets = Counter()
    for path in sorted(dist.rglob("*.html")):
        if path.name == "404.html":
            continue
        key = path.relative_to(dist).as_posix().removesuffix(".html")
        if key == "index":
            key = ""
        page = Page(path.read_text(encoding="utf-8"))
        pages[key] = page
        # Every generated page must load the same local design-system bundle.
        bundles = [s for s in page.styles if re.search(r"/assets/(?:bundle|site)\.[a-f0-9]+\.css(?:\?|$)", s)]
        stylesheet_sets.update(bundles)
        if not bundles:
            errors.append(f"/{key}: missing shared fingerprinted stylesheet")
        for img in page.images:
            src = img.get("src", "")
            relative = local_path(src)
            if relative is not None and not (dist / relative).is_file():
                errors.append(f"/{key}: missing image {src}")
            if img["in_main"]:
                if not img.get("alt", "").strip():
                    errors.append(f"/{key}: content image lacks descriptive alt: {src}")
                if not all(img.get(a, "").isdigit() and int(img[a]) > 0 for a in ("width", "height")):
                    errors.append(f"/{key}: image has no reserved dimensions: {src}")
            if img.get("srcset"):
                for candidate in img["srcset"].split(","):
                    candidate_src = candidate.strip().rsplit(" ", 1)[0]
                    relative = local_path(candidate_src)
                    if relative is not None and not (dist / relative).is_file():
                        errors.append(f"/{key}: missing responsive image {candidate_src}")
    if len(stylesheet_sets) != 1:
        errors.append(f"Page families load {len(stylesheet_sets)} different shared CSS bundles")
    for sheet in stylesheet_sets:
        css_path = dist / local_path(sheet)
        if not css_path.exists():
            errors.append(f"Missing shared CSS asset: {sheet}")
            continue
        css = css_path.read_text(encoding="utf-8")
        if "Cochin Wood visual system" not in css:
            errors.append("Shared CSS does not include the restored visual system")
        # Verify the restored font/palette files were delivered, even when a
        # bundler change accidentally leaves the old output in place.
        for token in ("Bree Serif", "Poppins", "#1b4332", "#007a5e"):
            if token.lower() not in css.lower():
                errors.append(f"Shared CSS lacks brand token {token}")
        if "prefers-reduced-motion" not in css:
            errors.append("Shared CSS has no reduced-motion treatment")

    entries = list(media_entries(manifest))
    promised = {local_path(e["src"]) for e in entries}
    for ref in sorted(promised):
        if not (dist / ref).is_file():
            errors.append(f"Curated image is absent from publication: /{ref}")
    for entry in entries:
        asset = dist / local_path(entry["src"])
        if asset.is_file() and entry.get("sha256"):
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            if digest != entry["sha256"]:
                errors.append(f"Published bytes differ from the inspected image: {entry['src']}")
    home = pages.get("")
    catalogue = pages.get("products")
    if not home or len(home.content_images) < 10:
        errors.append("Homepage lost its image-led product/application/process sections (fewer than 10 content images)")
    for key in ("home_hero", "catalogue_hero", "contact_hero", "encyclopedia_hero", "export_hero"):
        route = {"home_hero": "", "catalogue_hero": "products", "contact_hero": "contact",
                 "encyclopedia_hero": "woods-we-use", "export_hero": "export"}[key]
        page = pages.get(route)
        if not page or not page.content_images:
            errors.append(f"/{route}: image-led introduction is missing")
    for slug in manifest["products"]:
        product = pages.get(slug)
        if not product or not product.content_images:
            errors.append(f"/{slug}: product presentation image is missing")
        card_images = [] if not catalogue else [i for i in catalogue.content_images
            if local_path(i["link"]) in {slug, slug + ".html", slug + "/"}]
        if not card_images:
            errors.append(f"/products: {slug} has no linked product-card image")
        linked_image_count += bool(card_images)

    # Narrow known false marketing claims; do not ban factual country counts
    # in export research or the group's accurately qualified 1986 heritage.
    forbidden = (
        r"(?:ship(?:ping)?|export(?:ing|s)?)\s+(?:to\s+)?50\+?\s+countries",
        r"800\s*m[³3]\s*(?:shipment|shipped)",
        r"private\s+limited\s+(?:company\s+)?(?:since|established\s+in)\s+1986",
    )
    for route in ("", "products", "about", "plywood-factory", "contact"):
        if route not in pages:
            continue
        visible = " ".join(" ".join(pages[route].text).split())
        for pattern in forbidden:
            if re.search(pattern, visible, re.I):
                errors.append(f"/{route}: known unsupported marketing claim returned ({pattern})")

    if errors:
        print("VISUAL COVERAGE FAILED")
        for error in errors:
            print(" - " + error)
        return 1
    print(f"VISUAL COVERAGE OK: {len(pages)} pages share one brand bundle; "
          f"{len(promised)} curated images delivered; {linked_image_count} illustrated catalogue links; "
          f"{len(home.content_images)} homepage content images.")
    print("Static checks do not establish aesthetic quality. Complete desktop/mobile browser review before release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
