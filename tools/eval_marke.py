"""Try alternative brand criteria for the Clef brand question.

The live pipeline misreads the SWIZA D03 (the client's reference example) as
Victorinox, because both brands put a cross on the handle. This script tries
several wordings of the brand criteria against all 12 ground-truth photos and
reports top-1/top-3.

Usage:
    python tools/eval_marke.py --variante a
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from tools.clef_client import ClefClient  # noqa: E402

DATA_DIR = REPO / "data" / "sak_ground_truth"
KONKURRENZ = ("ROXON", "SWIZA", "HELTON", "LEATHERMAN", "GERBER", "BENCHMADE")

VARIANTEN = {
    "a": {
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
    "b": {
        "victorinox": "a folding knife with a red or coloured handle and a white cross stamped inside "
                      "a shield shape with pointed shoulders",
        "swiza": "a folding knife with a smooth black handle, a white cross stamped inside a plain "
                 "round circle, and the word SWIZA engraved on the blade",
        "wenger": "a folding knife with a red handle and a cross inside a rounded square",
        "leatherman": "a plier-based multitool with solid steel handles",
        "gerber": "a multitool with the word GERBER on it",
        "roxon": "a slim black folding knife with the word ROXON on the handle",
        "helton": "a plain black folding knife without any logo or lettering",
        "andere": "an unknown brand with no logo and no lettering",
    },
    "c": {
        "victorinox": "Victorinox Swiss Army Knife: cross emblem inside a shield outline, red handle, "
                      "or the word VICTORINOX engraved on the blade",
        "swiza": "SWIZA Swiss Army Knife: cross emblem inside a circle badge, matte black handle, "
                 "the word SWIZA engraved on the blade",
        "wenger": "Wenger: cross emblem inside a rounded square, red handle",
        "leatherman": "Leatherman: stainless steel plier multitool",
        "gerber": "Gerber: the word GERBER on the tool",
        "roxon": "ROXON: the word ROXON in white capitals",
        "helton": "The Helton: black handle with no logo and no lettering at all",
        "andere": "unknown brand, no logo, no lettering",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variante", default="a", choices=sorted(VARIANTEN))
    parser.add_argument("--modell", default="cloudflare/clef-flash")
    args = parser.parse_args()

    client = ClefClient(model=args.modell)
    labels = json.loads((DATA_DIR / "labels.json").read_text())
    fotos = [REPO / "frontend" / "public" / "demo" / "swiza-d03.jpg"]

    zeilen = []
    for row in labels:
        name = f"p{row['page']}_{row['xobj']}_obj{row['obj']}"
        label = row["label"].upper()
        erwartet = next((m for m in KONKURRENZ if m in label), None)
        if erwartet is None and "SAK" in label:
            erwartet = "VICTORINOX"
        zeilen.append((name, erwartet, DATA_DIR / f"{name}.png"))

    zeilen.append(("swiza-d03", "SWIZA", fotos[0]))

    frage = {
        "marke": {
            "type": "choice",
            "instructions": "Which brand is this pocket knife?",
            "criteria": VARIANTEN[args.variante],
        }
    }

    top1 = top3 = 0
    for name, erwartet, pfad in zeilen:
        state = [
            {"type": "text", "text": "Product photo:"},
            {"type": "image_url", "image_url": {"url": _data_url(pfad)}},
        ]
        result = client.decide(state, frage)
        antwort = result.answers["marke"]
        rang = [k for k, _ in sorted(antwort.probabilities.items(), key=lambda kv: -kv[1])]
        # Der Markenname im Katalog ist "Victorinox"; die Option heisst "victorinox".
        treffer = next((i for i, k in enumerate(rang, 1)
                        if erwartet and erwartet.casefold() == k), None)
        top1 += treffer == 1
        top3 += treffer is not None and treffer <= 3
        print(f"{name:<20} erwartet={str(erwartet):<12} platz={treffer or '-'}  "
              f"probs={ {k: round(v,3) for k,v in sorted(antwort.probabilities.items(), key=lambda kv:-kv[1])[:3]} }")
    print(f"\nVariante {args.variante}: top-1 {top1}/{len(zeilen)}  top-3 {top3}/{len(zeilen)}")
    return 0


def _data_url(path: Path) -> str:
    import base64
    import mimetypes
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


if __name__ == "__main__":
    raise SystemExit(main())
