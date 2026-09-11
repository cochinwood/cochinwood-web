"""Embed and verify self-declared provenance for encyclopedia AI card artwork.

This writes ordinary XMP into WebP containers.  It intentionally creates no
C2PA manifest, signature, Content Credentials claim, creator credit, or
ownership claim.  The records say what they are: machine-readable disclosure
of an AI-assisted illustration, with its source citation retained separately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
from xml.etree import ElementTree
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / "assets" / "photos" / "files"
SPECIES_MANIFEST = ROOT / "content" / "species-media.json"
RESPONSIVE_MANIFEST = ROOT / "content" / "responsive-media.json"
AI_SOURCE_TYPE = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
XMP_FLAG = 0x04
AI_VISUAL_FIELDS = ("card_visual", "withheld_card_visual")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def asset_path(src: str, files: Path = FILES) -> Path:
    if not src.startswith("/files/"):
        raise ValueError("AI card source must be a published /files/ URL: " + src)
    return files / src.removeprefix("/files/")


def generated_cards(species=None):
    species = _load(SPECIES_MANIFEST) if species is None else species
    cards = []
    for slug, entry in species.items():
        fields = [field for field in AI_VISUAL_FIELDS if entry.get(field) is not None]
        if len(fields) > 1:
            raise ValueError(f"{slug}: a generated visual cannot be both rendered and withheld")
        item = entry.get(fields[0]) if fields else None
        if item is None:
            continue
        if item.get("generated") is not True or item.get("kind") != "AI-assisted wood visual":
            raise ValueError(f"{slug}: AI visual is not declared AI-assisted artwork")
        for key in ("src", "source_url", "credit", "reference_taxon", "generation_method"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f"{slug}: missing {key} for AI-card provenance")
        cards.append((slug, entry, item))
    if len(cards) != 4:
        raise ValueError(f"Expected four generated encyclopedia cards, found {len(cards)}")
    return cards


def card_xmp(slug: str, entry: dict, item: dict) -> bytes:
    """Return an unsigned XMP disclosure, without representing C2PA provenance."""
    description = (
        f"AI-assisted visual for {entry['scientific_name']}, generated with the OpenAI built-in image tool "
        f"from a cited {item['reference_taxon']} visual reference. Illustrative artwork only; it is not a "
        "documentary specimen, a verified grain observation, or a photograph of Cochin Wood stock."
    )
    return (
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:iptcExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
        'xmlns:xmp="http://ns.adobe.com/xap/1.0/" '
        f'iptcExt:DigitalSourceType="{AI_SOURCE_TYPE}" '
        'xmp:CreatorTool="OpenAI built-in image generation" '
        'xmp:Label="AI-assisted visual; self-declared XMP provenance">'
        '<dc:title><rdf:Alt><rdf:li xml:lang="x-default">AI-assisted visual</rdf:li></rdf:Alt></dc:title>'
        '<dc:description><rdf:Alt><rdf:li xml:lang="x-default">'
        + escape(description)
        + '</rdf:li></rdf:Alt></dc:description>'
        '<dc:source><rdf:Bag><rdf:li>'
        + escape(item["source_url"])
        + '</rdf:li></rdf:Bag></dc:source>'
        '<dc:rights><rdf:Alt><rdf:li xml:lang="x-default">'
        + escape(f"Reference citation: {item['credit']}. See the linked source for its current reuse terms.")
        + '</rdf:li></rdf:Alt></dc:rights>'
        '</rdf:Description></rdf:RDF></x:xmpmeta>'
    ).encode("utf-8")


def _chunks(blob: bytes):
    if len(blob) < 12 or blob[:4] != b"RIFF" or blob[8:12] != b"WEBP":
        raise ValueError("Not a WebP RIFF container")
    if struct.unpack_from("<I", blob, 4)[0] != len(blob) - 8:
        raise ValueError("Invalid WebP RIFF length")
    offset, chunks = 12, []
    while offset < len(blob):
        if offset + 8 > len(blob):
            raise ValueError("Truncated WebP chunk header")
        name = blob[offset:offset + 4]
        length = struct.unpack_from("<I", blob, offset + 4)[0]
        end = offset + 8 + length
        if end > len(blob):
            raise ValueError("Truncated WebP chunk payload")
        chunks.append((name, blob[offset + 8:end]))
        offset = end + (length % 2)
    if offset != len(blob):
        raise ValueError("Invalid WebP chunk padding")
    return chunks


def _dimensions(chunks) -> tuple[int, int]:
    for name, data in chunks:
        if name == b"VP8X":
            if len(data) != 10:
                raise ValueError("Invalid VP8X header")
            return int.from_bytes(data[4:7], "little") + 1, int.from_bytes(data[7:10], "little") + 1
    for name, data in chunks:
        if name == b"VP8 ":
            if len(data) < 10 or data[3:6] != b"\x9d\x01\x2a":
                raise ValueError("Unsupported VP8 frame")
            return struct.unpack_from("<H", data, 6)[0] & 0x3FFF, struct.unpack_from("<H", data, 8)[0] & 0x3FFF
        if name == b"VP8L":
            if len(data) < 5 or data[0] != 0x2F:
                raise ValueError("Unsupported VP8L frame")
            bits = int.from_bytes(data[1:5], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    raise ValueError("WebP has no VP8, VP8L, or VP8X image header")


def _chunk(name: bytes, data: bytes) -> bytes:
    if len(name) != 4:
        raise ValueError("WebP chunk names are four bytes")
    return name + struct.pack("<I", len(data)) + data + (b"\0" if len(data) % 2 else b"")


def xmp_payload(blob: bytes) -> bytes | None:
    payloads = [data for name, data in _chunks(blob) if name == b"XMP "]
    if len(payloads) > 1:
        raise ValueError("WebP has more than one XMP chunk")
    if not payloads:
        return None
    try:
        ElementTree.fromstring(payloads[0])
    except ElementTree.ParseError as error:
        raise ValueError("Invalid XMP XML") from error
    return payloads[0]


def has_c2pa_claim(blob: bytes) -> bool:
    # This checks the container markers used by C2PA/JUMBF claims.  XMP itself
    # remains deliberately unsigned and is tested separately.
    return any(name in {b"C2PA", b"JUMD", b"JUMB"} for name, _data in _chunks(blob))


def with_xmp(blob: bytes, xmp: bytes) -> bytes:
    chunks = _chunks(blob)
    if has_c2pa_claim(blob):
        raise ValueError("Refusing to alter a WebP with a C2PA/JUMBF claim")
    xmp_payload(blob)  # Validate an existing packet and reject duplicate XMP.
    try:
        ElementTree.fromstring(xmp)
    except ElementTree.ParseError as error:
        raise ValueError("Invalid replacement XMP XML") from error
    width, height = _dimensions(chunks)
    body = []
    vp8x_seen = False
    for name, data in chunks:
        if name == b"XMP ":
            continue
        if name == b"VP8X":
            vp8x_seen = True
            if len(data) != 10:
                raise ValueError("Invalid VP8X header")
            revised = bytes([data[0] | XMP_FLAG]) + data[1:]
            body.append(_chunk(name, revised))
        else:
            body.append(_chunk(name, data))
    if not vp8x_seen:
        vp8x = bytes([XMP_FLAG, 0, 0, 0]) + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
        body.insert(0, _chunk(b"VP8X", vp8x))
    body.append(_chunk(b"XMP ", xmp))
    payload = b"WEBP" + b"".join(body)
    rebuilt = b"RIFF" + struct.pack("<I", len(payload)) + payload
    return blob if rebuilt == blob else rebuilt


def card_candidates(responsive: dict, item: dict):
    group = responsive.get(item["src"])
    if not isinstance(group, list) or not group:
        raise ValueError("AI card has no responsive source group: " + item["src"])
    candidates = []
    for candidate in group:
        if not isinstance(candidate, dict) or not isinstance(candidate.get("src"), str):
            raise ValueError("Invalid responsive candidate for " + item["src"])
        candidates.append(candidate)
    if candidates[-1]["src"] != item["src"]:
        raise ValueError("AI card master must be the final responsive candidate: " + item["src"])
    return candidates


def pending_changes(species=None, responsive=None, files: Path = FILES):
    """Return every stale provenance or declared-hash error without writing."""
    species = _load(SPECIES_MANIFEST) if species is None else species
    responsive = _load(RESPONSIVE_MANIFEST) if responsive is None else responsive
    pending = []
    for slug, entry, item in generated_cards(species):
        expected = card_xmp(slug, entry, item)
        for candidate in card_candidates(responsive, item):
            path = asset_path(candidate["src"], files)
            actual = path.read_bytes()
            if xmp_payload(actual) != expected or has_c2pa_claim(actual):
                pending.append(f"{path.relative_to(files).as_posix()}: XMP provenance missing or stale")
            declared = candidate.get("sha256")
            measured = digest(path)
            if declared != measured:
                pending.append(f"{path.relative_to(files).as_posix()}: responsive SHA-256 is stale")
        master = asset_path(item["src"], files)
        if item.get("sha256") != digest(master):
            pending.append(f"{master.relative_to(files).as_posix()}: card master SHA-256 is stale")
    return pending


def update(species_manifest: Path = SPECIES_MANIFEST,
           responsive_manifest: Path = RESPONSIVE_MANIFEST,
           files: Path = FILES):
    """Write validated XMP and refresh every declared responsive/master hash."""
    species, responsive = _load(species_manifest), _load(responsive_manifest)
    changed = []
    revisions = []
    for slug, entry, item in generated_cards(species):
        expected = card_xmp(slug, entry, item)
        for candidate in card_candidates(responsive, item):
            path = asset_path(candidate["src"], files)
            original = path.read_bytes()
            revised = with_xmp(original, expected)
            revisions.append((path, original, revised, candidate))
    # Complete every container preflight before changing any delivered file.
    for path, original, revised, candidate in revisions:
        if revised != original:
            path.write_bytes(revised)
            changed.append(path)
        candidate["sha256"] = digest(path)
    for _slug, _entry, item in generated_cards(species):
        item["sha256"] = digest(asset_path(item["src"], files))
    _write_json(species_manifest, species)
    _write_json(responsive_manifest, responsive)
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="embed XMP and refresh declared hashes")
    args = parser.parse_args()
    if args.write:
        changed = update()
        print(json.dumps({"changed": [path.relative_to(ROOT).as_posix() for path in changed]}))
        return
    pending = pending_changes()
    if pending:
        raise SystemExit("AI-card provenance missing or stale: " + "; ".join(pending))
    print("AI-card provenance OK")


if __name__ == "__main__":
    main()
