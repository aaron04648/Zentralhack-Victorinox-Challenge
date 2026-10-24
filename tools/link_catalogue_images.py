#!/usr/bin/env python3
"""Link extracted PDF image objects to catalogue pages and create SWIZA row crops.

Page-level links are exact PDF references. SWIZA is a scanned catalogue, so its
product crops use the catalogue parser's product order and equal row bands; those
crop associations are marked for review in the generated index.
"""

import json
import re
import zlib
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "data" / "catalogue_images"
CATALOG_ROOT = ROOT / "backend" / "data" / "kataloge"
PDF_ROOT = Path.home() / "Downloads"
PDFS = {
    "Leatherman-Katalog.pdf": "leatherman_2019.json",
    "pds_sku_426118_productbrochure_manual data sheet.pdf": "gerber.json",
    "Swiza_Messer.pdf": "swiza.json",
    "Victorinox_Catalogue_2026.pdf": "victorinox_2026.json",
}
OBJECT = re.compile(rb"(?m)(\d+)\s+(\d+)\s+obj\b")
REF = re.compile(rb"(\d+)\s+\d+\s+R\b")


def dict_value(data, key):
    """Return a direct value after /key, including a balanced PDF dictionary."""
    match = re.search(rb"/" + re.escape(key) + rb"\b", data)
    if not match:
        return None
    pos = match.end()
    while pos < len(data) and data[pos] in b" \t\r\n":
        pos += 1
    if data[pos:pos + 2] == b"<<":
        depth, end = 0, pos
        while end < len(data) - 1:
            if data[end:end + 2] == b"<<":
                depth += 1
                end += 2
            elif data[end:end + 2] == b">>":
                depth -= 1
                end += 2
                if depth == 0:
                    return data[pos:end]
            else:
                end += 1
    ref = re.match(rb"(\d+)\s+\d+\s+R", data[pos:])
    if ref:
        return int(ref.group(1))
    array = re.match(rb"\[([^\]]*)\]", data[pos:])
    return array.group(0) if array else None


def decode_stream(body):
    match = re.search(rb"\bstream\r?\n", body)
    if not match:
        return None
    dictionary = body[:match.start()]
    length = re.search(rb"/Length\s+(\d+)(?!\s+\d+\s+R)", dictionary)
    if not length:
        return None
    raw = body[match.end():match.end() + int(length.group(1))]
    if b"FlateDecode" in dictionary:
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            try:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            except zlib.error:
                return None
    return raw


def read_objects(pdf):
    raw = pdf.read_bytes()
    found = list(OBJECT.finditer(raw))
    objects = {}
    for match in found:
        end = raw.find(b"endobj", match.end())
        if end >= 0:
            objects[int(match.group(1))] = raw[match.end():end]
    # Expand compressed objects so page trees and page dictionaries are visible.
    for object_id, body in list(objects.items()):
        if b"/Type/ObjStm" not in body and b"/Type /ObjStm" not in body:
            continue
        decoded = decode_stream(body)
        first = re.search(rb"/First\s+(\d+)", body)
        count = re.search(rb"/N\s+(\d+)", body)
        if decoded is None or not first or not count:
            continue
        header = [int(n) for n in re.findall(rb"\d+", decoded[:int(first.group(1))])]
        n = int(count.group(1))
        pairs = list(zip(header[0:2 * n:2], header[1:2 * n:2]))
        for i, (inner_id, offset) in enumerate(pairs):
            stop = pairs[i + 1][1] if i + 1 < len(pairs) else len(decoded) - int(first.group(1))
            objects[inner_id] = decoded[int(first.group(1)) + offset:int(first.group(1)) + stop]
    return objects, raw


def references(value):
    return [int(x) for x in REF.findall(value or b"")]


def page_order(objects, raw):
    catalog = next((i for i, body in objects.items() if re.search(rb"/Type\s*/Catalog\b", body)), None)
    root = None
    if catalog is not None:
        root = dict_value(objects[catalog], b"Pages")
    if not isinstance(root, int):
        trailer = raw.rfind(b"trailer")
        roots = re.findall(rb"/Root\s+(\d+)\s+\d+\s+R", raw[trailer:]) if trailer >= 0 else []
        if roots:
            root = dict_value(objects.get(int(roots[-1]), b""), b"Pages")
    if not isinstance(root, int):
        return sorted(i for i, body in objects.items() if re.search(rb"/Type\s*/Page\b", body))
    pages, seen = [], set()

    def walk(object_id):
        if object_id in seen:
            return
        seen.add(object_id)
        body = objects.get(object_id, b"")
        if re.search(rb"/Type\s*/Page\b", body):
            pages.append(object_id)
            return
        kids = dict_value(body, b"Kids")
        if isinstance(kids, bytes):
            for child in references(kids):
                walk(child)

    walk(root)
    return pages or sorted(i for i, body in objects.items() if re.search(rb"/Type\s*/Page\b", body))


def page_images(objects, page_ids):
    pages = []
    for page_no, page_id in enumerate(page_ids, 1):
        body = objects.get(page_id, b"")
        resource = dict_value(body, b"Resources")
        if isinstance(resource, int):
            resource = objects.get(resource, b"")
        xobjects = dict_value(resource or b"", b"XObject")
        if isinstance(xobjects, int):
            xobjects = objects.get(xobjects, b"")
        ids = []
        for ref in references(xobjects):
            child = objects.get(ref, b"")
            if re.search(rb"/Subtype\s*/Image\b", child):
                ids.append(ref)
            elif re.search(rb"/Subtype\s*/Form\b", child):
                nested = dict_value(child, b"Resources")
                if isinstance(nested, int):
                    nested = objects.get(nested, b"")
                nested_x = dict_value(nested or b"", b"XObject")
                if isinstance(nested_x, int):
                    nested_x = objects.get(nested_x, b"")
                ids.extend(r for r in references(nested_x) if re.search(rb"/Subtype\s*/Image\b", objects.get(r, b"")))
        pages.append({"page": page_no, "page_object": page_id, "image_objects": sorted(set(ids))})
    return pages


def crop_swiza(image_path, output_path, row, row_count, width, height):
    """Crop the product photo column from one evenly spaced catalogue row."""
    import subprocess

    # Page 2's five rows and the remaining standard pages share this left photo column.
    band_start = round(height * (0.035 + row * 0.93 / row_count))
    band_end = round(height * (0.035 + (row + 1) * 0.93 / row_count))
    x0, x1 = round(width * 0.185), round(width * 0.35)
    margin = round((band_end - band_start) * 0.04)
    y0, y1 = band_start + margin, band_end - margin
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["magick", str(image_path), "-crop", f"{x1-x0}x{y1-y0}+{x0}+{y0}", "+repage", str(output_path)], check=True)


def main():
    manifest = json.loads((ASSET_ROOT / "manifest.json").read_text(encoding="utf-8"))
    assets_by_pdf_obj = {(row["pdf"], row["object"]): row for row in manifest}
    index = {"page_links": [], "products": []}
    swiza_pages = Path("/tmp/victorinox_swiza_pages")
    for pdf_name, catalog_name in PDFS.items():
        pdf = PDF_ROOT / pdf_name
        if not pdf.exists():
            continue
        objects, raw = read_objects(pdf)
        pages = page_images(objects, page_order(objects, raw))
        products = json.loads((CATALOG_ROOT / catalog_name).read_text(encoding="utf-8"))["produkte"]
        by_page = defaultdict(list)
        for product in products:
            by_page[product.get("seite")].append(product)
        for page in pages:
            page_no = page["page"]
            linked_assets = [assets_by_pdf_obj[(pdf_name, x)] for x in page["image_objects"] if (pdf_name, x) in assets_by_pdf_obj]
            page_products = by_page.get(page_no, [])
            index["page_links"].append({
                "pdf": pdf_name, "page": page_no, "products": [p.get("id") for p in page_products],
                "image_files": [a["file"] for a in linked_assets],
            })
            if pdf_name == "Swiza_Messer.pdf" and linked_assets and page_products:
                page_asset = linked_assets[0]
                source = ASSET_ROOT / page_asset["file"]
                page_png = swiza_pages / f"page_{page_no:02d}.png"
                if not page_png.exists():
                    swiza_pages.mkdir(parents=True, exist_ok=True)
                    import subprocess
                    subprocess.run(["magick", str(source), str(page_png)], check=True)
                for row, product in enumerate(page_products):
                    out = Path("swiza_product_crops") / f"p{page_no:02d}_{product['id'].split(':',1)[1].lower().replace(' ', '_').replace('/', '_')}.png"
                    crop_swiza(page_png, ASSET_ROOT / out, row, len(page_products), page_asset["width"], page_asset["height"])
                    index["products"].append({
                        "id": product["id"], "name": product.get("name"), "pdf": pdf_name,
                        "page": page_no, "image": out.as_posix(),
                        "association": "page product order + evenly spaced row crop",
                        "needs_review": True,
                    })
            elif pdf_name in {"Leatherman-Katalog.pdf", "pds_sku_426118_productbrochure_manual data sheet.pdf"} and page_products and linked_assets:
                # Image objects belong to the PDF page, and on two-product spreads
                # their order follows the catalogue layout. Keep these as candidates
                # and label the order-based split for human review.
                photo_assets = [a for a in linked_assets if (a["width"] or 0) >= 150 and (a["height"] or 0) >= 100]
                if not photo_assets:
                    photo_assets = linked_assets
                for row, product in enumerate(page_products):
                    if len(page_products) == 1:
                        chosen = photo_assets
                        method = "single catalogue product on PDF page"
                        review = len(chosen) != 1
                    elif len(photo_assets) >= len(page_products):
                        start = round(row * len(photo_assets) / len(page_products))
                        stop = round((row + 1) * len(photo_assets) / len(page_products))
                        chosen = photo_assets[start:stop]
                        method = "PDF page order split across products"
                        review = True
                    else:
                        chosen = photo_assets
                        method = "shared page candidates; ambiguous"
                        review = True
                    index["products"].append({
                        "id": product.get("id"), "name": product.get("name"), "pdf": pdf_name,
                        "page": page_no, "image_candidates": [a["file"] for a in chosen],
                        "association": method, "needs_review": review,
                    })
    target = ASSET_ROOT / "product_links.json"
    target.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    swiza_count = sum(p["pdf"] == "Swiza_Messer.pdf" for p in index["products"])
    print(f"Wrote {target}: {len(index['page_links'])} page links, {len(index['products'])} product records ({swiza_count} SWIZA crops)")
    for pdf_name in PDFS:
        linked_pages = [p for p in index["page_links"] if p["pdf"] == pdf_name and p["image_files"]]
        print(f"{pdf_name}: {len(linked_pages)} pages with image XObjects")


if __name__ == "__main__":
    main()
