#!/usr/bin/env python3
"""Extract JPEG/JPEG 2000 image streams from the catalogue PDFs.

This deliberately keeps the original PDF image bytes. It does not try to infer
which catalogue product an image belongs to; the manifest preserves each PDF
object number and its dimensions for that follow-up mapping.
"""

import argparse
import json
import re
from pathlib import Path


DEFAULT_PDFS = [
    "Leatherman-Katalog.pdf",
    "pds_sku_426118_productbrochure_manual data sheet.pdf",
    "Swiza_Messer.pdf",
    "Victorinox_Catalogue_2026.pdf",
]
OBJECT = re.compile(rb"(?m)(\d+)\s+(\d+)\s+obj\b")
IMAGE = re.compile(rb"/Subtype\s*/Image\b")
STREAM = re.compile(rb"\bstream\r?\n")
LENGTH = re.compile(rb"/Length\s+(\d+)(?!\s+\d+\s+R)")
WIDTH = re.compile(rb"/Width\s+(\d+)")
HEIGHT = re.compile(rb"/Height\s+(\d+)")
FILTER = re.compile(rb"/Filter\s*(?:/([A-Za-z0-9]+)|\[([^\]]+)\])")


def pdf_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", Path(name).stem.lower()).strip("_")


def image_records(pdf: Path):
    data = pdf.read_bytes()
    starts = list(OBJECT.finditer(data))
    for index, match in enumerate(starts):
        end = data.find(b"endobj", match.end())
        if end < 0:
            continue
        body = data[match.end():end]
        if not IMAGE.search(body):
            continue
        stream_match = STREAM.search(body)
        if not stream_match:
            continue
        dictionary = body[:stream_match.start()]
        filter_match = FILTER.search(dictionary)
        if not filter_match:
            continue
        filter_name = (filter_match.group(1) or filter_match.group(2) or b"").decode("ascii", "replace")
        if "DCTDecode" in filter_name:
            extension, encoding = ".jpg", "DCTDecode"
        elif "JPXDecode" in filter_name:
            extension, encoding = ".jp2", "JPXDecode"
        else:
            continue
        length_match = LENGTH.search(dictionary)
        if not length_match:
            continue
        stream_start = stream_match.end()
        stream_length = int(length_match.group(1))
        payload = body[stream_start:stream_start + stream_length]
        if len(payload) != stream_length:
            continue
        yield {
            "object": int(match.group(1)),
            "generation": int(match.group(2)),
            "width": int(WIDTH.search(dictionary).group(1)) if WIDTH.search(dictionary) else None,
            "height": int(HEIGHT.search(dictionary).group(1)) if HEIGHT.search(dictionary) else None,
            "filter": encoding,
            "extension": extension,
            "bytes": payload,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdfs", nargs="*", type=Path, help="PDF paths (defaults to known files in ~/Downloads)")
    parser.add_argument("--output", type=Path, default=Path("data/catalogue_images"))
    args = parser.parse_args()
    pdfs = args.pdfs or [Path.home() / "Downloads" / name for name in DEFAULT_PDFS]
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = []
    for pdf in pdfs:
        if not pdf.exists():
            print(f"skip missing: {pdf}")
            continue
        prefix = pdf_slug(pdf.name)
        folder = args.output / prefix
        folder.mkdir(parents=True, exist_ok=True)
        count = 0
        for record in image_records(pdf):
            rel = Path(prefix) / f"obj_{record['object']:05d}{record['extension']}"
            target = args.output / rel
            target.write_bytes(record.pop("bytes"))
            manifest.append({"pdf": pdf.name, "file": rel.as_posix(), **record})
            count += 1
        print(f"{pdf.name}: extracted {count} JPEG/JPEG 2000 images")
    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"manifest: {manifest_path} ({len(manifest)} images)")


if __name__ == "__main__":
    main()
