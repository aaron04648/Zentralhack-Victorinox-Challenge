"""Run both labelled photo sets through the complete local /api/match pipeline."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parent.parent
PDF_DIR = REPO / "data" / "sak_ground_truth"
PXL_DIR = REPO / "data" / "real_photos"
OUTPUT = REPO / "data" / "api_match_both_sets.json"
sys.path.insert(0, str(REPO))
PXL_CORRECTIONS = {
    "07_PXL_20261024_070713477.jpg": "Gerber",  # visible Gerber shield mark
    "10_PXL_20261024_070745178.jpg": "Gerber",  # Gerber logo and lettering
    "12_PXL_20261024_070755770.jpg": None,       # non-SAK branded folder; brand unclear
}


def pdf_rows() -> list[dict]:
    from tools.eval_match_api import load_labels

    rows = []
    for row in load_labels():
        truth_brand = row["marke"].title() if row["marke"] else None
        rows.append({"set": "pdf_packshots", "file": row["datei"], "truth_brand": truth_brand,
                     "legacy_truth_brand": truth_brand,
                     "truth_sku": row["erwartet"], "label_source": "Sven annotation with page 13/22 correction"})
    return rows


def pxl_rows() -> list[dict]:
    labels = json.loads((PXL_DIR / "labels.json").read_text())
    rows = []
    for filename, info in labels.items():
        legacy_class = info["class"]
        if filename in PXL_CORRECTIONS:
            brand = PXL_CORRECTIONS[filename]
            source = "manual visual correction to legacy label"
        elif legacy_class == "leatherman":
            brand, source = "Leatherman", "visible engraved brand"
        elif legacy_class == "gerber":
            brand, source = "Gerber", "visible engraved brand"
        else:
            brand, source = "Victorinox", "Swiss cross or Victorinox marking / legacy label"
        rows.append({"set": "pxl_phone_photos", "file": filename,
                     "truth_brand": brand, "truth_sku": None, "legacy_class": legacy_class,
                     "legacy_truth_brand": "Leatherman" if legacy_class == "leatherman" else
                     "Gerber" if legacy_class == "gerber" else "Victorinox",
                     "label_source": source})
    return rows


def hit_brand(prediction: str | None, truth: str | None) -> bool:
    if truth is None:
        return prediction is None
    return bool(prediction and truth.casefold() in prediction.casefold())


def catalogue_skus() -> dict[str, str]:
    path = REPO / "backend" / "data" / "victorinox_sak_produkte.csv"
    values: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            article = row["artikelnummer"].strip()
            values[article] = article
            values.update({v.strip(): article for v in (row.get("varianten_artikelnummern") or "").split(",") if v.strip()})
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--save", type=Path, default=OUTPUT)
    args = parser.parse_args()
    url = args.url.rstrip("/") + "/api/match"
    rows = pdf_rows() + pxl_rows()
    results = []

    sku_aliases = catalogue_skus()
    with httpx.Client(timeout=args.timeout) as client:
        for index, row in enumerate(rows, 1):
            path = (PDF_DIR if row["set"] == "pdf_packshots" else PXL_DIR) / row["file"]
            started = time.time()
            with path.open("rb") as image:
                response = client.post(url, files={"bild": (path.name, image)})
            elapsed = round(time.time() - started, 2)
            if response.status_code != 200:
                row.update({"http_status": response.status_code, "error": response.text[:2000],
                            "seconds": elapsed})
                results.append(row)
                print(f"{index:02d}/{len(rows)} ERROR {row['set']:<16} {path.name}: HTTP {response.status_code}", flush=True)
                continue

            data = response.json()
            recognized = data.get("erkannt") or {}
            recommendations = data.get("empfehlungen") or []
            recs = [{"artikelnummer": rec.get("produkt", {}).get("artikelnummer"),
                     "name": rec.get("produkt", {}).get("name"), "score": rec.get("score"),
                     "reasons": rec.get("gruende", [])} for rec in recommendations]
            prediction = recognized.get("marke")
            brand_hit = hit_brand(prediction, row["truth_brand"])
            sku_rank = next((rank for rank, rec in enumerate(recs, 1)
                             if row["truth_sku"] and rec["artikelnummer"] and
                             (rec["artikelnummer"] == row["truth_sku"] or
                              rec["artikelnummer"].startswith(row["truth_sku"] + ".") or
                              row["truth_sku"].startswith(rec["artikelnummer"] + "."))), None)
            sku_canonical = sku_aliases.get(row["truth_sku"])
            sku_family_rank = next((rank for rank, rec in enumerate(recs, 1)
                                    if sku_canonical and rec["artikelnummer"] == sku_canonical), None)
            row.update({"http_status": response.status_code, "prediction_brand": prediction,
                        "brand_confidence": recognized.get("konfidenz"), "brand_hit": brand_hit,
                        "legacy_brand_hit": hit_brand(prediction, row.get("legacy_truth_brand")),
                        "prediction_model": recognized.get("modell"),
                        "recognized_tools": recognized.get("werkzeuge", []),
                        "recognized_category": recognized.get("kategorie"),
                        "path": data.get("pfad"), "sku_rank": sku_rank,
                        "expected_sku_in_top3": bool(sku_rank and sku_rank <= 3),
                        "truth_sku_canonical": sku_canonical, "sku_family_rank": sku_family_rank,
                        "expected_sku_family_in_top3": bool(sku_family_rank and sku_family_rank <= 3),
                        "recommendations": recs, "clarification": data.get("rueckfrage"),
                        "seconds": elapsed, "steps": data.get("schritte", [])})
            results.append(row)
            top = ", ".join(f"{r['artikelnummer']} {r['name']} ({r['score']})" for r in recs[:3])
            print(f"{index:02d}/{len(rows)} {row['set']:<16} {path.name:<30} "
                  f"brand={prediction!s:<12} truth={row['truth_brand']!s:<12} "
                  f"conf={recognized.get('konfidenz', 0):.2f} sku_rank={sku_rank or '-'} "
                  f"{elapsed:.1f}s | {top}", flush=True)

    summaries = {}
    for dataset in ("pdf_packshots", "pxl_phone_photos"):
        subset = [r for r in results if r["set"] == dataset and r.get("http_status") == 200]
        known = [r for r in subset if r["truth_brand"] is not None]
        confident = [r for r in known if (r.get("brand_confidence") or 0) >= 0.6]
        sku_rows = [r for r in subset if r["truth_sku"] is not None]
        sku_matchable = [r for r in sku_rows if r["truth_sku"] in sku_aliases]
        summaries[dataset] = {
            "completed": len(subset), "brand_correct_corrected_labels": sum(r["brand_hit"] for r in known),
            "brand_denominator_corrected_labels": len(known),
            "brand_correct_legacy_labels": sum(r["legacy_brand_hit"] for r in subset),
            "brand_denominator_legacy_labels": len(subset),
            "brand_confidence_at_least_0_6_correct": sum(r["brand_hit"] for r in confident),
            "brand_confidence_at_least_0_6_coverage": len(confident),
            "clarification_requests": sum(r.get("clarification") is not None for r in subset),
            "low_confidence_without_clarification": sum(
                (r.get("brand_confidence") or 0) < 0.6 and r.get("clarification") is None for r in subset
            ),
            "sku_rows": len(sku_rows),
            "sku_matchable_in_catalogue": len(sku_matchable),
            "sku_in_top3_all_labelled": sum(bool(r.get("expected_sku_in_top3")) for r in sku_rows),
            "sku_in_top3_matchable": sum(bool(r.get("expected_sku_in_top3")) for r in sku_matchable),
            "sku_family_in_top3": sum(bool(r.get("expected_sku_family_in_top3")) for r in sku_rows),
            "mean_seconds": round(sum(r["seconds"] for r in subset) / max(len(subset), 1), 2),
        }
    report = {"started_at_utc": datetime.now(timezone.utc).isoformat(),
              "endpoint": url, "sets": summaries, "rows": results}
    args.save.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("\nSUMMARY", json.dumps(summaries, ensure_ascii=False))
    print(f"Raw endpoint responses: {args.save}")
    return 0 if len(results) == len(rows) and all(r.get("http_status") == 200 for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
