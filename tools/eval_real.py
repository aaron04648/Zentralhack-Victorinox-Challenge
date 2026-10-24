"""Evaluate the deployed /api/match endpoint on the 12 real Pixel photos.

These are the photos the demo will actually use (real smartphone photos of
products on a desk, mostly closed knives), so they are far more representative
than the clean catalogue packshots in data/sak_ground_truth/.

Usage:
    python tools/eval_real.py --url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data" / "real_photos"

# Erwartete Marke je Klasse.
KLASSE_MARKE = {
    "leatherman": "Leatherman",
    "gerber": "Gerber",
    "sak_red": "Victorinox",
    "sak_black": "Victorinox",
    "ruler": "Victorinox",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=float, default=240.0)
    args = parser.parse_args()

    url = args.url.rstrip("/") + "/api/match"
    labels = json.loads((DATA_DIR / "labels.json").read_text())

    marke_ok = marke_gesamt = 0
    zeilen = []
    with httpx.Client(timeout=args.timeout) as client:
        for datei, info in labels.items():
            t0 = time.time()
            with (DATA_DIR / datei).open("rb") as handle:
                response = client.post(url, files={"bild": (datei, handle, "image/jpeg")})
            dauer = time.time() - t0
            if response.status_code != 200:
                print(f"{datei:<40} HTTP {response.status_code}: {response.text[:100]}")
                continue
            data = response.json()
            erkannt = data["erkannt"]
            erwartet = KLASSE_MARKE[info["class"]]
            treffer = erwartet.casefold() in (erkannt["marke"] or "").casefold()
            marke_gesamt += 1
            marke_ok += treffer
            zeilen.append((datei, info, erkannt, data, treffer, dauer))

    for datei, info, erkannt, data, treffer, dauer in zeilen:
        marke_text = "OK " if treffer else "XX "
        print(f"{marke_text}{datei:<40} {info['class']:<12} "
              f"marke={str(erkannt['marke']):<12} konf={erkannt['konfidenz']:.2f} "
              f"pfad={data['pfad']:<10} {dauer:5.1f}s")
        for i, e in enumerate(data["empfehlungen"], 1):
            print(f"      {i}. {e['produkt']['artikelnummer']:<14} {e['produkt']['name']} "
                  f"(score {e['score']})")

    print(f"\nMarke richtig: {marke_ok}/{marke_gesamt} = {marke_ok / max(marke_gesamt, 1):.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
