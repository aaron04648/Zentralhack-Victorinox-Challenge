"""Measure how well the Clef decision model classifies the 12 ground-truth SAK photos.

Three experiments, all against the real OpenRouter decisions endpoint:

1. `pairwise`  - ask "is photo B the same product as photo A?" for all 66 photo pairs.
2. `noul`     - ask attribute probes ("is the handle red?", "is a cross emblem visible?")
                 and report the per-class feature means.
3. `direct`   - ask "which brand is this?" with brand criteria, one photo at a time.

Usage:
    uv run python tools/eval_clef.py --experiment all
    uv run python tools/eval_clef.py --experiment noul --model cloudflare/clef

Requires OPENROUTER_API_KEY in the environment (or in .env at the repo root).
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from tools.clef_client import ClefClient  # noqa: E402

DATA_DIR = REPO / "data" / "sak_ground_truth"

CLASS_KEYS = ("ROXON", "HELTON", "SWIZA", "SPARTAN", "SYNERGY")


def load_env() -> None:
    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_dataset() -> tuple[list[str], list[str]]:
    labels = json.loads((DATA_DIR / "labels.json").read_text())
    names, classes = [], []
    for row in labels:
        name = f"p{row['page']}_{row['xobj']}_obj{row['obj']}"
        names.append(name)
        upper = row["label"].upper()
        classes.append(next((k for k in CLASS_KEYS if k in upper), "?"))
    return names, classes


def pairwise_experiment(client: ClefClient, names: list[str], classes: list[str]) -> None:
    print("=" * 70)
    print("EXPERIMENT 1: pairwise 'is this the same product?'")
    print("=" * 70)
    questions = {
        "match": {
            "type": "choice",
            "instructions": "Is photo B the same product model as photo A?",
            "criteria": {
                "same": "same product model",
                "different": "different product model",
            },
        }
    }
    results = {}
    start = time.time()
    count = 0
    for i, j in itertools.combinations(range(len(names)), 2):
        state = [
            {"type": "text", "text": "Photo A is the customer photo. Photo B is a catalogue candidate."},
            {"type": "image_url", "image_url": {"url": _data_url(DATA_DIR / f"{names[i]}.png")}},
            {"type": "text", "text": "Catalogue candidate photo:"},
            {"type": "image_url", "image_url": {"url": _data_url(DATA_DIR / f"{names[j]}.png")}},
        ]
        result = client.decide(state, questions)
        answer = result.answers["match"]
        results[f"{i},{j}"] = [answer.choice == "same", answer.probabilities]
        count += 1
        if count % 10 == 0:
            print(f"  {count} pairs done ({time.time() - start:.0f}s)")

    same_ok = same_total = diff_ok = diff_total = 0
    for key, (said_same, _) in results.items():
        i, j = (int(x) for x in key.split(","))
        if classes[i] == classes[j]:
            same_total += 1
            same_ok += said_same
        else:
            diff_total += 1
            diff_ok += not said_same
    print(f"\n  same-class pairs : {same_ok}/{same_total} correct "
          f"({same_ok / max(same_total, 1):.0%})")
    print(f"  diff-class pairs : {diff_ok}/{diff_total} correct "
          f"({diff_ok / max(diff_total, 1):.0%})")
    print(f"  overall          : {(same_ok + diff_ok) / len(results):.0%}")
    (REPO / "data" / "clef_pairwise_results.json").write_text(json.dumps(results, indent=1))


def _data_url(path: Path) -> str:
    import base64
    import mimetypes

    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


NOUL_QUESTIONS = {
    "red": {
        "type": "noul",
        "instructions": "Is the handle of this pocket knife RED?",
        "criteria": {"true": "red handle", "false": "not a red handle"},
    },
    "cross": {
        "type": "noul",
        "instructions": "Is a Swiss cross emblem (white cross inside a square or shield) visible on the handle?",
        "criteria": {"true": "a cross emblem is visible", "false": "no cross emblem"},
    },
    "text": {
        "type": "noul",
        "instructions": "Is the brand name printed in letters on the handle or scale?",
        "criteria": {"true": "brand text is visible", "false": "no brand text visible"},
    },
    "open": {
        "type": "noul",
        "instructions": "Are the tools of this pocket knife shown OPEN, fanned out, with multiple implements visible?",
        "criteria": {"true": "tools are shown open", "false": "tools are closed"},
    },
}


def noul_experiment(client: ClefClient, names: list[str], classes: list[str]) -> None:
    print("=" * 70)
    print("EXPERIMENT 2: attribute probes")
    print("=" * 70)
    results = {}
    for name in names:
        state = [
            {"type": "text", "text": "Product photo:"},
            {"type": "image_url", "image_url": {"url": _data_url(DATA_DIR / f"{name}.png")}},
        ]
        result = client.decide(state, NOUL_QUESTIONS)
        results[name] = {
            qid: answer.noul for qid, answer in result.answers.items()
        }
    (REPO / "data" / "clef_noul_results.json").write_text(json.dumps(results, indent=1))

    print(f"\n  {'photo':<21}{'truth':<9}" + "".join(f"{q:>8}" for q in NOUL_QUESTIONS))
    for name, klass in zip(names, classes):
        row = results[name]
        print(f"  {name:<21}{klass:<9}" + "".join(f"{row.get(q, 0):>8.3f}" for q in NOUL_QUESTIONS))

    print("\n  per-class means:")
    print(f"  {'class':<9}" + "".join(f"{q:>8}" for q in NOUL_QUESTIONS))
    for klass in CLASS_KEYS:
        members = [results[n] for n, k in zip(names, classes) if k == klass]
        if not members:
            continue
        print(f"  {klass:<9}" + "".join(
            f"{sum(m.get(q, 0) for m in members) / len(members):>8.3f}" for q in NOUL_QUESTIONS
        ))


BRAND_CRITERIA = {
    "roxon": "ROXON brand - black handle, slender parallel frames, corkscrew",
    "helton": "The Helton - black textured handle, narrow blade",
    "swiza": "Swiza - black handle with Swiss cross shield logo",
    "spartan": "Victorinox Spartan - red handle with Swiss cross emblem",
    "synergy": "Victorinox Synergy X Alox - dark grey plain textured scales, no logo",
}


def direct_experiment(client: ClefClient, names: list[str], classes: list[str]) -> None:
    print("=" * 70)
    print("EXPERIMENT 3: direct brand identification")
    print("=" * 70)
    questions = {
        "brand": {
            "type": "choice",
            "instructions": "Which brand and model is this pocket knife?",
            "criteria": BRAND_CRITERIA,
        }
    }
    hits = 0
    for name, klass in zip(names, classes):
        state = [
            {"type": "text", "text": "Catalogue photo:"},
            {"type": "image_url", "image_url": {"url": _data_url(DATA_DIR / f"{name}.png")}},
        ]
        result = client.decide(state, questions)
        answer = result.answers["brand"]
        # Option ids in the criteria are lowercase; class keys are uppercase.
        hit = (answer.choice or "").upper() == klass
        hits += hit
        probs = {k: round(v, 3) for k, v in sorted(answer.probabilities.items(), key=lambda kv: -kv[1])}
        print(f"  {name:<21}truth={klass:<9}pred={answer.choice:<9}conf={answer.confidence:.3f} "
              f"{'HIT' if hit else 'MISS'}  {probs}")
    print(f"\n  direct top-1: {hits}/{len(names)} = {hits / len(names):.0%}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--experiment", choices=["all", "pairwise", "noul", "direct"], default="all"
    )
    parser.add_argument("--model", default="cloudflare/clef-flash")
    args = parser.parse_args()

    load_env()
    names, classes = load_dataset()
    client = ClefClient(model=args.model)

    if args.experiment in ("all", "pairwise"):
        pairwise_experiment(client, names, classes)
    if args.experiment in ("all", "noul"):
        noul_experiment(client, names, classes)
    if args.experiment in ("all", "direct"):
        direct_experiment(client, names, classes)


if __name__ == "__main__":
    main()
