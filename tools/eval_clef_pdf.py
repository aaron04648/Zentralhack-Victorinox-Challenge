"""Evaluate Clef brand ranking on Sven's 12 corrected PDF packshots.

Prompt variants are tuned on the same 12 examples, so report the final score as
an in-sample diagnostic, not an independent estimate of generalisation.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "sak_ground_truth"
OUT = REPO / "data"
API = "https://openrouter.ai/api/alpha/decisions"
MODEL = "cloudflare/clef-flash"

# Correct photo-to-label mapping. The PDF sticky notes on pages 13 and 22 were
# attached by column rather than to the corresponding photo; match the products
# visually and preserve the corrections already used by backend/training/evaluieren.py.
TRUTH = {
    "p1_Im1_obj3": "roxon",
    "p1_Im2_obj5": "helton",
    "p1_Im3_obj7": "swiza",
    "p1_Im4_obj9": "victorinox",
    "p1_Im5_obj11": "victorinox",
    "p13_Im1_obj16": "leatherman",
    "p13_Im2_obj18": "victorinox",
    "p13_Im3_obj19": "gerber",
    "p13_Im4_obj21": "victorinox",
    "p22_Im1_obj24": "gerber",
    "p22_Im2_obj26": "victorinox",
    "p22_Im3_obj27": "benchmade",
}

CRITERIA = {
    "rich": {
        "roxon": "ROXON Swiss Army style multitool: black textured scales, narrow parallel metal frame and ROXON lettering on the handle.",
        "helton": "The Helton folding multitool: black heavily dotted or textured handle, exposed steel implements and THE HELTON lettering on the blade.",
        "swiza": "SWIZA Swiss Army knife: dark smooth handle with a prominent white cross inside a round or circular badge; SWIZA lettering on the blade.",
        "victorinox": "Victorinox pocket knife or multitool: Swiss cross inside the distinctive pointed shield, red or dark scales, or recognizable Victorinox tool construction.",
        "leatherman": "Leatherman plier multitool: folding pliers at the centre, many steel implements, and LEATHERMAN lettering on a handle.",
        "gerber": "Gerber branded knife or multitool: GERBER lettering or the Gerber shield logo; may be a plier multitool or a folding knife.",
        "benchmade": "Benchmade folding knife: one-hand locking blade with a pocket clip and the small butterfly Benchmade logo on the blade.",
    },
    "compact": {
        "roxon": "ROXON multitool; ROXON printed on black handle.",
        "helton": "The Helton knife; dotted black handle and THE HELTON printed on blade.",
        "swiza": "SWIZA knife; cross in a circular badge and SWIZA printed on blade.",
        "victorinox": "Victorinox knife or multitool; Swiss cross in pointed shield, red or black scales.",
        "leatherman": "Leatherman pliers multitool; LEATHERMAN printed on handle.",
        "gerber": "Gerber knife or multitool; GERBER name or shield G logo.",
        "benchmade": "Benchmade folding knife; butterfly logo on blade, pocket clip.",
    },
    "evidence": {
        "roxon": "The visible ROXON word on the black scale, slim metal side frame, and folding tools arranged around a black handle.",
        "helton": "The words THE HELTON printed on the blade and a black handle covered in evenly spaced round dimples.",
        "swiza": "The word SWIZA on a steel blade and a white plus sign enclosed by a circular ring on the black handle.",
        "victorinox": "A Victorinox shield-shaped cross emblem on a red or dark scale, or unmistakable Victorinox SwissTool construction.",
        "leatherman": "The word LEATHERMAN engraved on one of the long handles of a folding plier tool.",
        "gerber": "The word GERBER or a shield containing a G on the product; Gerber can be either a folding knife or a plier multitool.",
        "benchmade": "The butterfly-shaped Benchmade mark on a folding knife blade, with a pivot and pocket clip.",
    },
}


def load_env() -> str:
    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is missing from .env or environment")
    return key


def ask(key: str, model: str, name: str, criteria: dict[str, str], image_view: str,
        instructions: str, context: str) -> dict:
    source = DATA / f"{name}.png"
    if image_view == "trim":
        with tempfile.NamedTemporaryFile(suffix=".jpg") as output:
            subprocess.run([
                "magick", str(source), "-background", "white", "-alpha", "remove", "-alpha", "off",
                "-fuzz", "8%", "-trim", "+repage", "-resize", "1024x1024", "-quality", "88", output.name,
            ], check=True, capture_output=True)
            image = Path(output.name).read_bytes()
        mime = "image/jpeg"
    else:
        image = source.read_bytes()
        mime = "image/png"
    state = [
        {"type": "text", "text": context},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64," + base64.b64encode(image).decode()}},
    ]
    payload = {
        "model": model,
        "provider": {"only": ["cloudflare"]},
        "state": state,
        "questions": {"brand": {"type": "choice", "instructions": instructions,
                                   "criteria": criteria}},
    }
    request = Request(API, data=json.dumps(payload).encode(), method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost", "X-Title": "victorinox-pdf-classification-eval",
    })
    try:
        with urlopen(request, timeout=120) as response:
            return json.load(response).get("answers", {}).get("brand", {})
    except HTTPError as error:
        detail = error.read().decode(errors="replace")[:1200]
        raise RuntimeError(f"Clef HTTP {error.code}: {detail}") from None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=sorted(CRITERIA), default="rich")
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--candidate-set", choices=("seven", "production"), default="seven")
    parser.add_argument("--image-view", choices=("raw", "trim"), default="raw")
    parser.add_argument("--save", type=Path)
    args = parser.parse_args()
    key = load_env()
    if args.candidate_set == "production":
        import sys
        sys.path.insert(0, str(REPO / "backend"))
        from app.clef import MARKEN
        criteria = {option: definition[1] for option, definition in MARKEN.items()}
        instructions = "Which brand made this pocket knife, multitool or folding knife? Choose based on visible features and markings."
        context = "Product photo of a pocket knife or multitool:"
    else:
        criteria = CRITERIA[args.variant]
        instructions = "Which brand made the pictured product? Choose the closest match based on visible evidence."
        context = "Identify the brand of the product in this clean catalogue photo."
    results = []
    top1 = top3 = 0
    for name, truth in TRUTH.items():
        answer = ask(key, args.model, name, criteria, args.image_view, instructions, context)
        probs = answer.get("probabilities") or {}
        ranking = sorted(probs, key=probs.get, reverse=True)
        rank = ranking.index(truth) + 1 if truth in ranking else None
        top1 += rank == 1
        top3 += rank is not None and rank <= 3
        row = {"photo": name, "truth": truth, "rank": rank,
               "prediction": ranking[0] if ranking else None, "probabilities": probs,
               "image_sha256": hashlib.sha256((DATA / f"{name}.png").read_bytes()).hexdigest()}
        results.append(row)
        print(f"{name:<22} truth={truth:<12} rank={str(rank):<4} "
              f"top={[(k, round(probs[k], 3)) for k in ranking[:3]]}")

    report = {"dataset": "Sven-annotated PDF packshots, corrected page 13/22 mapping",
              "model": args.model,
              "variant": args.variant if args.candidate_set == "seven" else "production",
              "image_view": args.image_view,
              "candidate_set": args.candidate_set,
              "top1": top1, "top3": top3,
              "total": len(results), "rows": results}
    default_result_name = "production" if args.candidate_set == "production" else args.variant
    path = args.save or OUT / f"clef_pdf_{default_result_name}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"\n{args.variant}: top-1 {top1}/{len(results)}, top-3 {top3}/{len(results)}")
    print(f"Raw results: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
