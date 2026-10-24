"""Evaluate the classification pipeline on real smartphone photos.

`data/real_photos/` holds 12 photos taken with a Pixel phone of products on a
desk - the actual demo domain, as opposed to the clean packshots in
`data/sak_ground_truth/`.

Ground truth was established by reading the brand markings directly off the
photos ("LEATHERMAN Rev", "GERBER", the Swiss cross shield, the cm scale), not
from a model prediction.

Usage:
    uv run python tools/eval_real.py                 # brand decision
    uv run python tools/eval_real.py --experiment all
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from tools.clef_client import ClefClient  # noqa: E402

DATA_DIR = REPO / "data" / "real_photos"

# Criteria describe visible features, not brand names alone.
BRAND_CRITERIA = {
    "sak_red": "a Victorinox Swiss Army Knife with RED scales and the Swiss cross emblem",
    "sak_black": "a Victorinox Swiss Army Knife with plain BLACK scales and no emblem",
    "ruler": "a flat metal ruler or measuring tool with a centimetre scale",
    "leatherman": "a stainless steel Leatherman multitool, silver metal with cut-out slots",
    "gerber": "a grey/silver Gerber multitool with an angular cut-out frame design",
}


def load_env() -> None:
    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_dataset() -> list[tuple[Path, str, str]]:
    labels = json.loads((DATA_DIR / "labels.json").read_text())
    return [
        (DATA_DIR / name, entry["class"], entry["desc"])
        for name, entry in sorted(labels.items())
    ]


def brand_experiment(client: ClefClient) -> None:
    print("=" * 74)
    print("BRAND DECISION on real smartphone photos")
    print("=" * 74)
    questions = {
        "product": {
            "type": "choice",
            "instructions": "Which product is shown in this photo?",
            "criteria": BRAND_CRITERIA,
        }
    }
    rows = []
    for path, truth, desc in load_dataset():
        result = client.decide(
            state=["Photo of a product on a desk:"], questions=questions, images=[path]
        )
        answer = result.answers["product"]
        ranked = sorted(answer.probabilities.items(), key=lambda kv: -kv[1])
        values = [v for _, v in ranked]
        margin = values[0] - values[1] if len(values) > 1 else 0.0
        hit1 = answer.choice == truth
        hit3 = truth in [k for k, _ in ranked[:3]]
        rows.append((path.name, truth, answer.choice, answer.confidence, margin, hit1, hit3))
        mark = "OK" if hit1 else ("top3" if hit3 else "MISS")
        print(
            f"  {path.name[:34]:<34} truth={truth:<11} pred={answer.choice:<11} "
            f"conf={answer.confidence:.3f} margin={margin:.3f}  {mark}"
        )

    top1 = sum(r[5] for r in rows)
    top3 = sum(r[6] for r in rows)
    print(f"\n  TOP-1: {top1}/{len(rows)} = {top1 / len(rows):.0%}")
    print(f"  TOP-3: {top3}/{len(rows)} = {top3 / len(rows):.0%}")

    correct = [r[3] for r in rows if r[5]]
    wrong = [r[3] for r in rows if not r[5]]
    if correct and wrong:
        print(
            f"\n  mean confidence when CORRECT: {sum(correct) / len(correct):.3f}"
            f"   when WRONG: {sum(wrong) / len(wrong):.3f}"
        )
        print("\n  abstention sweep (confident enough to show a single answer):")
        for threshold in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7):
            shown = [r for r in rows if r[3] >= threshold]
            if not shown:
                continue
            precision = sum(r[5] for r in shown) / len(shown)
            print(
                f"    conf>={threshold}: show {len(shown):>2}/{len(rows)}, "
                f"precision {precision:.0%}, coverage {len(shown) / len(rows):.0%}"
            )

    (REPO / "data" / "real_brand_results.json").write_text(
        json.dumps(
            [
                {
                    "photo": r[0],
                    "truth": r[1],
                    "pred": r[2],
                    "confidence": r[3],
                    "margin": r[4],
                    "hit1": r[5],
                    "hit3": r[6],
                }
                for r in rows
            ],
            indent=1,
        )
    )


def open_state_experiment(client: ClefClient) -> None:
    print("=" * 74)
    print("OPEN / CLOSED GATE on real smartphone photos")
    print("=" * 74)
    questions = {
        "open_state": {
            "type": "noul",
            "instructions": (
                "Are the implements of this pocket knife shown OPEN (fanned out, "
                "so several different tools are visible at once)?"
            ),
            "criteria": {
                "true": "the knife is shown open with several tools visible",
                "false": "the knife is closed or only one tool is visible",
            },
        }
    }
    for path, truth, desc in load_dataset():
        value = client.decide(
            state=["Photo of a product on a desk:"], questions=questions, images=[path]
        ).answers["open_state"].noul
        print(f"  {path.name[:34]:<34} open={value:.2f}   {desc[:46]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--experiment", choices=["all", "brand", "open_state"], default="all"
    )
    parser.add_argument("--model", default="cloudflare/clef-flash")
    args = parser.parse_args()

    load_env()
    client = ClefClient(model=args.model)
    if args.experiment in ("all", "brand"):
        brand_experiment(client)
    if args.experiment in ("all", "open_state"):
        open_state_experiment(client)


if __name__ == "__main__":
    main()
