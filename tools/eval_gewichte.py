"""Compare scoring weights for the product recommendation, offline.

The recommendation for a competitor knife should satisfy the *functional* need
first (coverage: what the photographed knife can do must also be possible with
the recommended one) and only then be as close as possible (precision: no
pointless extra tools).

This script replays the cached detections and the cached catalogue images
against several weightings and reports how often the expected article number
lands in the top-3.

Usage:
    python tools/eval_gewichte.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

TRAINING = REPO / "backend" / "data" / "training"
DATA_DIR = REPO / "data" / "real_photos"
KONKURRENZ = ("ROXON", "SWIZA", "HELTON", "LEATHERMAN", "GERBER", "BENCHMADE")
SCHALENTEILE = {"pinzette", "zahnstocher", "kugelschreiber", "stecknadel"}

GEWICHTE = {
    "ist": (0.65, 0.30),
    "abdeckung_2x": (0.80, 0.15),
    "abdeckung_3x": (0.90, 0.05),
    "nur_abdeckung": (1.0, 0.0),
    "ausgewogen": (0.5, 0.5),
}


def katalog():
    with (REPO / "backend" / "data" / "victorinox_sak_produkte.csv").open(
            encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def gruppen(row):
    return {g.strip() for g in row["werkzeug_gruppen"].split(",") if g.strip()}


def eq_nr(a: str, b: str) -> bool:
    return a == b or a.startswith(b + ".") or b.startswith(a + ".")


def main() -> int:
    pool = [r for r in katalog() if r["werkzeug_gruppen"].strip()]
    schwellen = json.loads((TRAINING / "clef_schwellen.json").read_text())
    cache = {}
    for line in (TRAINING / "clef_cache.jsonl").read_text().splitlines():
        e = json.loads(line)
        cache[e["id"]] = e

    faelle = []
    labels = json.loads((REPO / "data" / "sak_ground_truth" / "labels.json").read_text())
    for row in labels:
        name = f"p{row['page']}_{row['xobj']}_obj{row['obj']}"
        e = cache.get(f"foto-{name}")
        if not e:
            continue
        match = re.search(r"SKU[:\s]*([0-9][0-9.]*[A-Za-z0-9]*)", row["label"], re.IGNORECASE)
        erkannt = {g for g, p in e["roh"]["werkzeuge"].items() if p >= schwellen.get(g, 0.5)}
        faelle.append({"name": name, "erkannt": erkannt, "erwartet": match.group(1) if match else None})

    for name, gewicht in GEWICHTE.items():
        top1 = top3 = gesamt = 0
        for fall in faelle:
            if not fall["erwartet"]:
                continue
            gesamt += 1
            bewertet = []
            for row in pool:
                g = gruppen(row)
                gemeinsam = len(fall["erkannt"] & g)
                abdeckung = gemeinsam / len(fall["erkannt"])
                sichtbar = g - (SCHALENTEILE - fall["erkannt"])
                praezision = gemeinsam / len(sichtbar) if sichtbar else 0.0
                score = gewicht[0] * abdeckung + gewicht[1] * praezision
                if row["lagerstatus"] == "inStock":
                    score += 0.05
                bewertet.append((score, row["artikelnummer"]))
            bewertet.sort(key=lambda t: -t[0])
            rang = [nr for _, nr in bewertet]
            platz = next((i for i, nr in enumerate(rang, 1) if eq_nr(nr, fall["erwartet"])), None)
            top1 += platz == 1
            top3 += platz is not None and platz <= 3
        print(f"{name:<16} abdeckung={gewicht[0]:.2f} praezision={gewicht[1]:.2f}  "
              f"top-1 {top1}/{gesamt}  top-3 {top3}/{gesamt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
