"""Prototype: candidate pre-filtering + Clef decision over the survivors.

Tests the documented architecture (docs/classification_recommendation.md §8):
the catalogue's tool lists are the discriminator that images failed at. So we
first narrow the catalogue with a cheap deterministic filter (tool-set overlap,
colour, availability), and only then let Clef pick between the survivors with
per-option criteria.

Wichtig: das Werkzeug-Vokabular des Backends (backend/app/werkzeuge.py) wird
verwendet, nicht das englische aus tools/tool_vocab.py - sonst schneiden sich
erkannte und katalogisierte Gruppen nie.

Usage:
    python tools/eval_kandidaten.py --limit 12 --kandidaten 8
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))

from tools.clef_client import ClefClient  # noqa: E402

DATA_DIR = REPO / "data" / "sak_ground_truth"
PRODUKTE_CSV = REPO / "backend" / "data" / "victorinox_sak_produkte.csv"

# Sichtbare Merkmale je Werkzeuggruppe (englisch) - kurz und konkret.
GROUP_EN = {
    "klinge_gross": "a large smooth-edged blade",
    "klinge_klein": "a shorter second blade",
    "klinge_wellenschliff": "a serrated blade",
    "klinge_spezial": "a hook or curved blade",
    "schere": "scissors",
    "holzsaege": "a coarse wood saw",
    "metallsaege": "a fine metal saw",
    "metallfeile": "a metal file",
    "nagelfeile": "a nail file",
    "korkenzieher": "a spiral corkscrew",
    "dosenoeffner": "a can opener",
    "kapselheber": "a bottle opener",
    "schraubendreher_flach": "a flat screwdriver",
    "schraubendreher_kreuz": "a Phillips screwdriver",
    "mini_schraubendreher": "a tiny mini screwdriver",
    "ahle": "a pointed awl",
    "zange": "pliers",
    "pinzette": "tweezers",
    "zahnstocher": "a plastic toothpick",
    "kugelschreiber": "a ballpoint pen",
    "stecknadel": "a straight pin",
    "lupe": "a magnifying glass",
    "led": "a built-in LED light",
    "massstab": "a ruler scale",
    "mehrzweckhaken": "a multi-purpose hook",
    "fischentschupper": "a fish scaler",
    "holzmeissel": "a wood chisel",
    "kistenoeffner": "a crate opener lever",
    "bits": "a bit holder",
    "nagelpflege": "a nail clipper",
    "trageclip": "a pocket clip",
    "drahtwerkzeug": "a wire stripper notch",
}


def katalog():
    with PRODUKTE_CSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    return [r for r in rows if r["werkzeug_gruppen"].strip()]


def gruppen(row):
    return {g.strip() for g in row["werkzeug_gruppen"].split(",") if g.strip()}


def kriterium(row: dict) -> str:
    """Kriterium fuer eine Kandidaten-Option: sichtbare Merkmale, kein Markenname."""
    teile = [GROUP_EN.get(g, g) for g in sorted(gruppen(row))]
    farben = ", ".join(c.strip() for c in (row.get("farben") or "").split(",") if c.strip())
    return (
        f"{row['name']} ({row['artikelnummer']}). "
        f"Tools: {', '.join(teile) if teile else 'none recorded'}. "
        f"Handle colours available: {farben or 'not recorded'}."
    )


def vorfilter(pool, erkannte_gruppen, farben):
    """Kandidaten einschraenken, bevor das Modell gefragt wird."""
    if not erkannte_gruppen:
        return list(pool)
    bewertet = []
    for row in pool:
        g = gruppen(row)
        gemeinsam = len(erkannte_gruppen & g)
        abdeckung = gemeinsam / len(erkannte_gruppen)
        praezision = gemeinsam / len(g)
        score = 0.65 * abdeckung + 0.30 * praezision
        if farben:
            kandidaten_farben = {c.strip().casefold() for c in (row.get("farben") or "").split(",")}
            if farben & kandidaten_farben:
                score += 0.05
        bewertet.append((score, row))
    bewertet.sort(key=lambda kv: (-kv[0], kv[1]["artikelnummer"]))
    return [row for _, row in bewertet]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--kandidaten", type=int, default=8)
    parser.add_argument("--modell", default="cloudflare/clef-flash")
    parser.add_argument("--vorfilter", default="werkzeug", choices=["werkzeug", "keiner"])
    args = parser.parse_args()

    client = ClefClient(model=args.modell)
    labels = json.loads((DATA_DIR / "labels.json").read_text())
    zeilen = []
    for row in labels:
        name = f"p{row['page']}_{row['xobj']}_obj{row['obj']}"
        match = re.search(r"SKU[:\s]*([0-9][0-9.]*[A-Za-z0-9]*)", row["label"], re.IGNORECASE)
        zeilen.append({"name": name, "erwartet": match.group(1) if match else None})

    zeilen = zeilen[: args.limit]
    pool = katalog()
    print(f"Katalog: {len(pool)} SKUs mit Werkzeugliste")

    top1 = top3 = bewertbar = 0
    for z in zeilen:
        erkannte_gruppen, farben = _erkennung(z["name"])

        if args.vorfilter == "werkzeug":
            kandidaten = vorfilter(pool, erkannte_gruppen, farben)
        else:
            kandidaten = list(pool)
        kandidaten = list(kandidaten)
        random.Random(z["name"]).shuffle(kandidaten)
        kandidaten = kandidaten[: args.kandidaten]

        frage = {
            "produkt": {
                "type": "choice",
                "instructions": (
                    "Which catalogue product is the knife in the customer photo? "
                    "Compare the handle colour, the shape and the number and type of "
                    "tools."
                ),
                "criteria": {r["artikelnummer"]: kriterium(r) for r in kandidaten},
            }
        }
        state = [
            {"type": "text", "text": "CUSTOMER PHOTO of a pocket knife:"},
            {"type": "image_url", "image_url": {"url": _data_url(DATA_DIR / f"{z['name']}.png")}},
        ]
        result = client.decide(state, frage)
        antwort = result.answers["produkt"]
        rang = [n for n, _ in sorted(antwort.probabilities.items(), key=lambda kv: -kv[1])][:3]
        platz = rang.index(z["erwartet"]) + 1 if z["erwartet"] in rang else None
        if z["erwartet"]:
            bewertbar += 1
            top1 += platz == 1
            top3 += platz is not None
        print(f"{z['name']:<20} erwartet={str(z['erwartet']):<12} platz={platz or '-'} "
              f"margin={antwort.confidence:.3f} top3={rang}")
    if bewertbar:
        print(f"\ntop-1 {top1}/{bewertbar}  top-3 {top3}/{bewertbar} "
              f"({top3 / bewertbar:.0%})")
    return 0


def _erkennung(name):
    """Erkannte Werkzeuggruppen aus dem Trainings-Cache (kein Live-Bildtest).

    Die Schwellen kommen aus backend/data/training/clef_schwellen.json - genau die,
    die auch das Backend benutzt.
    """
    cache = REPO / "backend" / "data" / "training" / "clef_cache.jsonl"
    pfad_schwellen = REPO / "backend" / "data" / "training" / "clef_schwellen.json"
    schwellen = json.loads(pfad_schwellen.read_text()) if pfad_schwellen.exists() else {}
    if cache.exists():
        for line in cache.read_text().splitlines():
            e = json.loads(line)
            if e["id"] in (f"foto-{name}", name):
                gruppen = {g for g, p in e["roh"]["werkzeuge"].items()
                           if p >= schwellen.get(g, 0.5)}
                return gruppen, set()
    return set(), set()


def _data_url(path: Path) -> str:
    import base64
    import mimetypes
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


if __name__ == "__main__":
    raise SystemExit(main())
