"""Baut den Trainings-/Testdatensatz für die Werkzeugerkennung.

Quellen:
- Victorinox-Katalog (data/victorinox_produkte.json): Produktbild aufgeklappt (S1) mit den
  Werkzeuggruppen aus den Produktdaten. Zugeklappte Ansichten (S2 …) werden nicht verwendet,
  weil darauf keine Werkzeuge sichtbar sind.
- Konkurrenz (data/training/konkurrenz.csv, aus training/konkurrenz.py), nur fürs Training.

Aufteilung: Victorinox-Produkte werden nach Werkzeugset gruppiert, und jedes Set landet als
Ganzes im Training oder im Test. So sind z. B. alle 18 Classic-SD-Farbvarianten auf derselben
Seite und das Modell wird nur mit Messern getestet, deren Werkzeugkombination es nie gesehen hat.

Ausgabe (data/training/):
- datensatz.jsonl   eine Zeile pro Bild: id, quelle, marke, name, bild_url, werkzeug_gruppen, split
- referenzen.json   Beispielbilder für den Few-Shot-Prompt (aus dem Trainingsteil)

Aufruf:  python -m training.datensatz [--test-anteil 0.3]
"""

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

from app.katalog import load_products
from app.werkzeuge import GRUPPEN

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "training"
BILD_PARAMS = "?io=transform:fill,width:768&format=jpg"  # einheitliche Grösse, JPEG
MAX_REFERENZEN = 6


def lies_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def bild(url):
    if "imageengine.victorinox.com" in url and "?" not in url:
        return url + BILD_PARAMS
    return url


def split_fuer(gruppen_set, test_anteil):
    schluessel = ",".join(sorted(gruppen_set)).encode()
    wert = int(hashlib.sha1(schluessel).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "test" if wert < test_anteil else "train"


def victorinox(test_anteil):
    samples = []
    for row in load_products():
        g = set(row["werkzeug_gruppen"])
        if len(g) < 2 or not row["bild_url"]:
            continue  # Zubehör und Einzelwerkzeuge (Nagelschere …) sind keine Taschenmesser
        samples.append({
            "id": f"vx-{row['artikelnummer']}",
            "quelle": "victorinox.com",
            "marke": "Victorinox",
            "artikelnummer": row["artikelnummer"],
            "name": row["name"],
            "bild_url": bild(row["bild_url"]),
            "werkzeug_gruppen": sorted(g),
            "split": split_fuer(g, test_anteil),
        })
    return samples


def konkurrenz():
    path = OUT / "konkurrenz.csv"
    if not path.exists():
        print(f"  Hinweis: {path.name} fehlt, nur Victorinox-Daten (python -m training.konkurrenz)",
              file=sys.stderr)
        return []
    samples = []
    for row in lies_csv(path):
        g = {x.strip() for x in row["werkzeug_gruppen"].split(",") if x.strip() in GRUPPEN}
        if len(g) < 2:
            continue
        for i, url in enumerate(u for u in row["bild_urls"].split() if u):
            samples.append({
                "id": f"{row['marke'].lower()}-{row['artikelnummer']}-{i}",
                "quelle": row["quelle"],
                "marke": row["marke"],
                "artikelnummer": row["artikelnummer"],
                "name": row["name"],
                "bild_url": url,
                "werkzeug_gruppen": sorted(g),
                "split": "train",
            })
    return samples


def referenzen_waehlen(train):
    """Typische Messer (4-10 Gruppen) gierig nach neu abgedeckten Gruppen wählen.

    Riesige Modelle würden zwar alle Gruppen abdecken, sind auf dem Foto aber unübersichtlich
    und untypisch. Pro Marke höchstens die Hälfte, damit auch Fremdmarken als Beispiel dienen.
    """
    kandidaten = [s for s in train if 4 <= len(s["werkzeug_gruppen"]) <= 10
                  and "card" not in s["name"].casefold()]  # Swiss Card ist kein Taschenmesser
    gewaehlt, abgedeckt, namen = [], set(), set()
    while kandidaten and len(gewaehlt) < MAX_REFERENZEN:
        pro_marke = {m: sum(1 for g in gewaehlt if g["marke"] == m) for m in {s["marke"] for s in kandidaten}}
        erlaubt = [s for s in kandidaten if pro_marke[s["marke"]] < MAX_REFERENZEN // 2 and s["name"] not in namen]
        if not erlaubt:
            break
        bestes = max(erlaubt, key=lambda s: (len(set(s["werkzeug_gruppen"]) - abgedeckt), -len(s["werkzeug_gruppen"])))
        if not set(bestes["werkzeug_gruppen"]) - abgedeckt:
            break
        gewaehlt.append(bestes)
        namen.add(bestes["name"])
        abgedeckt |= set(bestes["werkzeug_gruppen"])
        kandidaten.remove(bestes)
    return gewaehlt, abgedeckt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-anteil", type=float, default=0.3)
    args = parser.parse_args()

    samples = victorinox(args.test_anteil) + konkurrenz()
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "datensatz.jsonl").open("w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    train = [s for s in samples if s["split"] == "train"]
    test = [s for s in samples if s["split"] == "test"]
    refs, abgedeckt = referenzen_waehlen(train)
    (OUT / "referenzen.json").write_text(json.dumps(
        [{k: r[k] for k in ("name", "marke", "bild_url", "werkzeug_gruppen")} for r in refs],
        ensure_ascii=False, indent=2), encoding="utf-8")

    marken = sorted({s["marke"] for s in train})
    print(f"Training: {len(train)} Bilder ({', '.join(marken)})", file=sys.stderr)
    print(f"Test:     {len(test)} Bilder (Victorinox, Werkzeugsets nicht im Training)", file=sys.stderr)
    print(f"Referenzen: {len(refs)} Bilder decken {len(abgedeckt)} von {len(GRUPPEN)} Gruppen ab", file=sys.stderr)
    nie_trainiert = set(GRUPPEN) - {g for s in train for g in s["werkzeug_gruppen"]}
    if nie_trainiert:
        print(f"Gruppen ohne Trainingsbeispiel: {', '.join(sorted(nie_trainiert))}", file=sys.stderr)


if __name__ == "__main__":
    main()
