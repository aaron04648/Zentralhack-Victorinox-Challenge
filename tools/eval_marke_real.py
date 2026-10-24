"""Try tighter brand vocabularies on the real Pixel photos.

The 12 real photos (data/real_photos/) show five product classes. A tight
vocabulary works better than a broad one: every extra option competes for
probability mass (docs/classification_recommendation.md §7).

Usage:
    python tools/eval_marke_real.py --variante 5klassen
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

DATA_DIR = REPO / "data" / "real_photos"

VARIANTEN = {
    "5klassen": {
        "victorinox": "a Victorinox Swiss Army Knife or Alox multi-tool: a white cross emblem on the "
                      "handle, the name VICTORINOX engraved on the blade or scale, red, black or silver "
                      "colours",
        "leatherman": "a Leatherman multi-tool: solid stainless steel handles, the word LEATHERMAN "
                      "engraved on the handle",
        "gerber": "a Gerber multi-tool: the word GERBER engraved on the handle or blade",
        "andere": "unclear: no brand name or emblem is readable on this photo",
    },
    "5klassen_eng": {
        "victorinox": "VICTORINOX engraved on the blade, or a Swiss cross emblem on the handle",
        "leatherman": "LEATHERMAN engraved on the handle",
        "gerber": "GERBER engraved on the handle or blade",
        "andere": "unclear: nothing readable",
    },
    "breit": {
        "victorinox": "Victorinox Swiss Army Knife: a white cross inside a shield OUTLINE that has "
                      "pointed shoulders and a flat bottom, brand name VICTORINOX usually printed on "
                      "the scale or the blade",
        "swiza": "SWIZA Swiss Army Knife: a white cross inside a plain CIRCLE badge, or a cross in a "
                 "rounded square, on a smooth black or coloured handle, brand name SWIZA printed in "
                 "block capitals on the blade or handle",
        "wenger": "Wenger Swiss Army Knife: a white cross in a rounded square, usually on red scales, "
                  "the name WENGER printed on the blade",
        "leatherman": "Leatherman multitool: plier-based folding tool with solid stainless steel "
                      "handles, no logo emblem",
        "gerber": "Gerber multitool or folding knife: the name GERBER printed on the blade or handle",
        "roxon": "ROXON Swiss Army Knife: black handle with a slender parallel metal frame, the name "
                 "ROXON printed in white capitals on the handle or blade",
        "helton": "The Helton Swiss Army Knife: plain black textured handle with no logo and no "
                  "lettering, narrow plain blade",
        "andere": "another or unknown brand, no readable logo or lettering",
    },
}

# Erwartete Marke je Klasse.
KLASSE_MARKE = {
    "leatherman": "victorinox",
    "gerber": "gerber",
    "sak_red": "victorinox",
    "sak_black": "victorinox",
    "ruler": "victorinox",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variante", default="5klassen", choices=sorted(VARIANTEN))
    parser.add_argument("--modell", default="cloudflare/clef-flash")
    args = parser.parse_args()

    labels = json.loads((DATA_DIR / "labels.json").read_text())
    frage = {
        "marke": {
            "type": "choice",
            "instructions": "Which brand is this pocket knife or multi-tool?",
            "criteria": VARIANTEN[args.variante],
        }
    }

    top1 = top3 = sicher = sicher_richtig = 0
    for datei, info in labels.items():
        pfad = DATA_DIR / datei
        bild = clef.bild_vorbereiten("data:image/jpeg;base64," + _b64(pfad))
        state = [{"type": "text", "text": "Product photo:"},
                 {"type": "image_url", "image_url": {"url": bild}}]
        result = clef.entscheide(state, frage)
        antwort = result["marke"]
        probs = antwort.get("probabilities") or {}
        rang = sorted(probs, key=lambda k: -probs[k])
        erwartet = KLASSE_MARKE[info["class"]]
        platz = next((i for i, k in enumerate(rang, 1) if k == erwartet), None)
        top1 += platz == 1
        top3 += platz is not None and platz <= 3
        sicher_werte = sorted(probs.values(), reverse=True)
        konf = sicher_werte[0] if sicher_werte else 0.0
        if konf >= 0.3:
            sicher += 1
            sicher_richtig += platz == 1
        top3p = {k: round(v, 3) for k, v in sorted(probs.items(), key=lambda kv: -kv[1])[:3]}
        print(f"{datei:<40} {info['class']:<12} platz={platz or '-'} konf={konf:.3f} {top3p}")

    gesamt = len(labels)
    print(f"\nVariante {args.variante}: top-1 {top1}/{gesamt}  top-3 {top3}/{gesamt}  "
          f"| bei konf>=0.3: {sicher_richtig}/{sicher} korrekt")
    return 0


def _b64(pfad: Path) -> str:
    import base64
    return base64.b64encode(pfad.read_bytes()).decode()


if __name__ == "__main__":
    raise SystemExit(main())
