"""Evaluate the *ranking* of candidate products, offline, on the cached detections.

This isolates the question "which products do we put in the top 3?" from the
question "does the vision model detect the brand/tools correctly?".

Two candidate sources:
- **Werkzeug-Matching**: coverage/precision of the detected tool groups against
  the catalogue's tool list (deterministic, cheap).
- **Bildsuche**: the Clef visual tournament over the catalogue images.

`--modus` selects how the two are combined:

- `nur_werkzeug`  - tools only
- `nur_bild`      - image search only
- `summe`         - normalised sum of both
- `werkzeug_2x`   - tools weighted twice as much as the image search

Usage:
    python tools/eval_ranking.py --modus summe
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from app.werkzeuge import GRUPPEN  # noqa: E402

DATA_DIR = REPO / "data" / "sak_ground_truth"
TRAINING = REPO / "backend" / "data" / "training"

KONKURRENZ = ("ROXON", "SWIZA", "HELTON", "LEATHERMAN", "GERBER", "BENCHMADE")
SCHALENTEILE = {"pinzette", "zahnstocher", "kugelschreiber", "stecknadel"}


def lade():
    labels = json.loads((DATA_DIR / "labels.json").read_text())
    schwellen = json.loads((TRAINING / "clef_schwellen.json").read_text())
    cache = {}
    for line in (TRAINING / "clef_cache.jsonl").read_text().splitlines():
        e = json.loads(line)
        cache[e["id"]] = e
    return labels, schwellen, cache


def eq_nr(a: str, b: str) -> bool:
    return a == b or a.startswith(b + ".") or b.startswith(a + ".")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--modus", default="summe",
                        choices=["nur_werkzeug", "nur_bild", "summe", "werkzeug_2x"])
    args = parser.parse_args()

    labels, schwellen, cache = lade()

    auswertung = json.loads((TRAINING / "auswertung_fotos_vision_clef.json").read_text())
    bild_ranks = {}
    for detail in auswertung.get("details", []):
        bild_ranks[detail["id"]] = detail

    marke_ok = marke_gesamt = sku_ok = sku_gesamt = 0
    for row in labels:
        name = f"p{row['page']}_{row['xobj']}_obj{row['obj']}"
        key = f"foto-{name}"
        e = cache.get(key)
        if not e:
            continue
        erkannt = {g for g, p in e["roh"]["werkzeuge"].items() if p >= schwellen.get(g, 0.5)}

        marke_roh = e["roh"]["marke"]
        erkannte_marke = max(marke_roh, key=marke_roh.get)
        label = row["label"].upper()
        erwartet_marke = next((m for m in KONKURRENZ if m in label), None)
        if erwartet_marke:
            marke_gesamt += 1
            marke_ok += erkannte_marke == erwartet_marke.lower()
        elif "SAK" in label:
            marke_gesamt += 1
            marke_ok += erkannte_marke == "victorinox"

        detail = bild_ranks.get(key, {})
        bild_liste = detail.get("top3_bild", [])
        bild_score = {}
        for eintrag in bild_liste:
            match = re.match(r"^.*?\(([^,]+), ([0-9.]+)\)$", eintrag)
            if match:
                bild_score[match.group(1).strip()] = float(match.group(2))

        werkzeug_liste = detail.get("top3", [])
        werkzeug_score = {}
        for eintrag in werkzeug_liste:
            match = re.match(r"^.*?\(([^,]+), ([0-9.]+)\)$", eintrag)
            if match:
                werkzeug_score[match.group(1).strip()] = float(match.group(2))

        erwartet = None
        m = re.search(r"SKU[:\s]*([0-9][0-9.]*[A-Za-z0-9]*)", row["label"], re.IGNORECASE)
        if m:
            erwartet = m.group(1)

        if args.modus == "nur_werkzeug":
            rang = sorted(werkzeug_score, key=lambda k: -werkzeug_score[k])
        elif args.modus == "nur_bild":
            rang = sorted(bild_score, key=lambda k: -bild_score[k])
        else:
            alle = set(werkzeug_score) | set(bild_score)
            max_w = max(werkzeug_score.values(), default=1.0) or 1.0
            max_b = max(bild_score.values(), default=1.0) or 1.0
            gewicht = 2.0 if args.modus == "werkzeug_2x" else 1.0
            rang = sorted(
                alle,
                key=lambda k: -(gewicht * werkzeug_score.get(k, 0) / max_w
                                + bild_score.get(k, 0) / max_b),
            )

        platz = next((i for i, nr in enumerate(rang, 1) if eq_nr(nr, erwartet)), None) if erwartet else None
        if erwartet:
            sku_gesamt += 1
            sku_ok += platz is not None and platz <= 3

        print(f"{name:<20} erwartet={str(erwartet):<12} platz={platz or '-'}  "
              f"werkzeug={list(werkzeug_score)[:3]}  bild={list(bild_score)[:3]}")

    print(f"\nModus {args.modus}: Marke {marke_ok}/{marke_gesamt}, "
          f"SKU top-3 {sku_ok}/{sku_gesamt}")


if __name__ == "__main__":
    main()
