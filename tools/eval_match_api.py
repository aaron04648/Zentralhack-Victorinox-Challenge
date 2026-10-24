"""Evaluate the deployed /api/match endpoint on the 12 ground-truth photos.

Two metrics, because they answer different questions:

- **Marke**: is the single brand returned by the full endpoint correct? Unlike the
  direct Clef harness, `/api/match` currently returns only one brand, not a brand top-k.
- **SKU**: is the expected article number in the top-3 recommendations? Weaker
  signal: the sticky-note labels on PDF pages 13 and 22 are assigned by column,
  not by photo; `FOTO_KORREKTUR` fixes those mappings. Labelled SKU `0.8226.22` is
  represented as a variant of canonical catalogue article `0.8226.20`; exact variant
  selection is distinct from matching the correct product family.

Usage:
    python tools/eval_match_api.py --url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data" / "sak_ground_truth"

# Konkurrenzmarken, die es im Katalog nicht gibt -> nur Marke bewertbar.
KONKURRENZ = ("ROXON", "SWIZA", "HELTON", "LEATHERMAN", "GERBER", "BENCHMADE")
# The sticky notes on PDF pages 13 and 22 are positioned by column, not by photo.
# Keep these corrections aligned with training/evaluieren.py.
FOTO_KORREKTUR = {
    "p13_Im1_obj16": ("LEATHERMAN", None),
    "p13_Im2_obj18": ("VICTORINOX", "3.0224.3CN"),
    "p13_Im3_obj19": ("GERBER", None),
    "p13_Im4_obj21": ("VICTORINOX", "3.0323.L"),
    "p22_Im1_obj24": ("GERBER", None),
    "p22_Im2_obj26": ("VICTORINOX", "0.9411.D20"),
    "p22_Im3_obj27": ("BENCHMADE", None),
}


def load_labels() -> list[dict]:
    """Ground-truth rows with the expected brand and Victorinox article number."""
    rows = json.loads((DATA_DIR / "labels.json").read_text())
    for row in rows:
        name = f"p{row['page']}_{row['xobj']}_obj{row['obj']}"
        row["datei"] = f"{name}.png"
        if name in FOTO_KORREKTUR:
            row["marke"], row["erwartet"] = FOTO_KORREKTUR[name]
            row["modell"] = None
            continue
        match = re.search(r"SKU[:\s]*([0-9][0-9.]*[A-Za-z0-9]*)", row["label"], re.IGNORECASE)
        row["erwartet"] = match.group(1) if match else None
        label = row["label"].upper()
        row["marke"] = next((m for m in KONKURRENZ if m in label), None)
        if row["marke"] is None:
            # Victorinox-Produkte: Marke ist "Victorinox", Modell aus dem Label.
            row["marke"] = "VICTORINOX" if "SAK" in label else None
            row["modell"] = row["label"].split("/")[-1].split("(")[0].strip()
        else:
            row["modell"] = None
    return rows


def marke_richtig(erkannt: str, erwartet: str) -> bool:
    if not erkannt:
        return False
    if erwartet == "VICTORINOX":
        return "victorinox" in erkannt.casefold()
    return erwartet.casefold() in erkannt.casefold()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=float, default=240.0)
    args = parser.parse_args()

    url = args.url.rstrip("/") + "/api/match"
    rows = load_labels()
    marke_ok = marke_gesamt = sku_ok = sku_gesamt = 0

    with httpx.Client(timeout=args.timeout) as client:
        for row in rows:
            t0 = time.time()
            with (DATA_DIR / row["datei"]).open("rb") as handle:
                response = client.post(url, files={"bild": (row["datei"], handle, "image/png")})
            dauer = time.time() - t0
            if response.status_code != 200:
                print(f"{row['datei']:<22} HTTP {response.status_code}: {response.text[:120]}")
                continue
            data = response.json()
            erkannt = data["erkannt"]
            treffer = [e["produkt"]["artikelnummer"] for e in data["empfehlungen"]]
            namen = [e["produkt"]["name"] for e in data["empfehlungen"]]

            treffer_marke = marke_richtig(erkannt["marke"] or "", row["marke"])
            if row["marke"]:
                marke_gesamt += 1
                marke_ok += treffer_marke

            platz = None
            if row["erwartet"]:
                sku_gesamt += 1
                for i, nr in enumerate(treffer, 1):
                    if nr == row["erwartet"] or nr.startswith(row["erwartet"] + ".") \
                            or row["erwartet"].startswith(nr + "."):
                        platz = i
                        break
                sku_ok += platz is not None and platz <= 3

            marke_text = "OK " if treffer_marke else "XX "
            print(f"{marke_text}{row['datei']:<22} marke={str(erkannt['marke']):<12} "
                  f"erwartet={str(row['marke']):<12} konf={erkannt['konfidenz']:.2f} "
                  f"sku_platz={platz or '-'} {dauer:5.1f}s")
            for i, (nr, name) in enumerate(zip(treffer, namen), 1):
                print(f"      {i}. {nr:<14} {name}")

    print(f"\nMarke  richtig: {marke_ok}/{marke_gesamt} = {marke_ok / max(marke_gesamt, 1):.0%}")
    if sku_gesamt:
        print(f"SKU top-3:      {sku_ok}/{sku_gesamt} = {sku_ok / sku_gesamt:.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
