"""Evaluate the brand question exactly as the backend does it.

Uses backend/app/clef.py (same image preparation, same parallel question
packets, same thresholds), so the numbers match what the live API returns.

Usage:
    python tools/eval_marke_pipeline.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))

from app import clef  # noqa: E402

DATA_DIR = REPO / "data" / "sak_ground_truth"
KONKURRENZ = ("ROXON", "SWIZA", "HELTON", "LEATHERMAN", "GERBER", "BENCHMADE")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nur-marke", action="store_true",
                        help="Nur die Markenfrage stellen (ohne Werkzeugpakete).")
    args = parser.parse_args()

    labels = json.loads((DATA_DIR / "labels.json").read_text())
    fotos = []
    for row in labels:
        name = f"p{row['page']}_{row['xobj']}_obj{row['obj']}"
        label = row["label"].upper()
        erwartet = next((m for m in KONKURRENZ if m in label), None)
        if erwartet is None and "SAK" in label:
            erwartet = "VICTORINOX"
        fotos.append((name, erwartet, DATA_DIR / f"{name}.png"))

    demo = REPO / "frontend" / "public" / "demo" / "swiza-d03.jpg"
    if demo.exists():
        fotos.append(("swiza-d03", "SWIZA", demo))

    top1 = top3 = 0
    for name, erwartet, pfad in fotos:
        # So, wie das Backend das Bild aufbereitet.
        bild = clef.bild_vorbereiten(f"data:image/jpeg;base64," + _b64(pfad))
        roh = clef.wahrscheinlichkeiten(bild)
        marken = roh["marke"]
        rang = sorted(marken, key=lambda k: -marken[k])
        platz = next((i for i, k in enumerate(rang, 1)
                      if erwartet and k == erwartet.casefold()), None)
        top1 += platz == 1
        top3 += platz is not None and platz <= 3
        top3_probs = {k: round(v, 3) for k, v in sorted(marken.items(), key=lambda kv: -kv[1])[:3]}
        print(f"{name:<20} erwartet={str(erwartet):<12} platz={platz or '-'}  {top3_probs}")
    print(f"\nBackend-Pfad: top-1 {top1}/{len(fotos)}  top-3 {top3}/{len(fotos)} "
          f"({top3 / len(fotos):.0%})")
    return 0


def _b64(pfad: Path) -> str:
    import base64
    return base64.b64encode(pfad.read_bytes()).decode()


if __name__ == "__main__":
    raise SystemExit(main())
