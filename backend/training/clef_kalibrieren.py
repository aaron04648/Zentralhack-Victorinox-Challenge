"""Lernt pro Werkzeuggruppe, ab welcher Clef-Wahrscheinlichkeit ein Werkzeug als erkannt gilt.

Clefs Wahrscheinlichkeiten sind nur schwach kalibriert (docs/classification_recommendation.md),
eine feste Schwelle von 0.5 passt also nicht für jedes Werkzeug. Auf den Trainingsbildern
(Victorinox + SWIZA, datensatz.jsonl split=train) wird je Gruppe die Schwelle mit dem besten
F1 gewählt; Gruppen mit zu wenig Beispielen bekommen die global beste Schwelle.

Die Clef-Antworten werden zwischengespeichert (data/training/clef_cache.jsonl), auch für die
Testbilder, damit training/evaluieren.py sie ohne neue API-Aufrufe auswerten kann.

Aufruf:  python -m training.clef_kalibrieren [--limit 50]
Ergebnis: data/training/clef_schwellen.json (wird von app/clef.py automatisch geladen)
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app import clef
from app.werkzeuge import GRUPPEN

OUT = Path(__file__).resolve().parent.parent / "data" / "training"
CACHE = OUT / "clef_cache.jsonl"
MIN_BEISPIELE = 5            # je positiv und negativ, sonst globale Schwelle
KANDIDATEN = [round(0.05 * i, 2) for i in range(1, 20)]
PARALLEL = 4


def cache_laden():
    if not CACHE.exists():
        return {}
    eintraege = (json.loads(z) for z in CACHE.read_text(encoding="utf-8").splitlines() if z.strip())
    return {(e["id"], e["modell"]): e["roh"] for e in eintraege}


def roh_fuer(samples):
    """Clef-Rohwahrscheinlichkeiten je Sample, aus dem Cache oder per API (und dann gecacht)."""
    cache = cache_laden()
    modell = clef.modell()
    fehlend = [s for s in samples if (s["id"], modell) not in cache]
    if fehlend:
        print(f"  {len(fehlend)} Bilder an Clef ({modell}), {len(samples) - len(fehlend)} aus dem Cache",
              file=sys.stderr)

    def abfragen(s):
        try:
            return s, clef.wahrscheinlichkeiten(clef.bild_vorbereiten(s["bild_url"]))
        except Exception as fehler:
            print(f"\n  Fehler bei {s['id']}: {fehler}", file=sys.stderr)
            return s, None

    with CACHE.open("a", encoding="utf-8") as f, ThreadPoolExecutor(PARALLEL) as pool:
        for i, (s, roh) in enumerate(pool.map(abfragen, fehlend), 1):
            if roh is not None:
                cache[(s["id"], modell)] = roh
                f.write(json.dumps({"id": s["id"], "modell": modell, "roh": roh}) + "\n")
                f.flush()
            print(f"\r  {i}/{len(fehlend)}", end="", file=sys.stderr)
    if fehlend:
        print(file=sys.stderr)
    return {s["id"]: cache[(s["id"], modell)] for s in samples if (s["id"], modell) in cache}


def f1(paare, t):
    tp = sum(1 for p, wahr in paare if p >= t and wahr)
    fp = sum(1 for p, wahr in paare if p >= t and not wahr)
    fn = sum(1 for p, wahr in paare if p < t and wahr)
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="nur die ersten N Trainingsbilder (Test)")
    args = parser.parse_args()
    if not clef.aktiv():
        sys.exit("OPENROUTER_API_KEY fehlt in .env")

    samples = [json.loads(z) for z in (OUT / "datensatz.jsonl").read_text(encoding="utf-8").splitlines()]
    train = [s for s in samples if s["split"] == "train"]
    test = [s for s in samples if s["split"] == "test"]
    if args.limit:
        train = train[:args.limit]
    roh = roh_fuer(train + test)

    paare = {g: [] for g in GRUPPEN}  # g -> [(p, wahr)]
    for s in train:
        if s["id"] in roh:
            for g in GRUPPEN:
                paare[g].append((roh[s["id"]]["werkzeuge"][g], g in s["werkzeug_gruppen"]))
    alle = [x for liste in paare.values() for x in liste]
    if not alle:
        sys.exit("Keine Trainingsbilder ausgewertet.")
    global_t = max(KANDIDATEN, key=lambda t: f1(alle, t))

    schwellen, zeilen = {}, []
    for g, liste in paare.items():
        pos = sum(1 for _, w in liste if w)
        if pos >= MIN_BEISPIELE and len(liste) - pos >= MIN_BEISPIELE:
            schwellen[g] = max(KANDIDATEN, key=lambda t: f1(liste, t))
        else:
            schwellen[g] = global_t
        zeilen.append((g, pos, f1(liste, 0.5), schwellen[g], f1(liste, schwellen[g])))
    (OUT / "clef_schwellen.json").write_text(json.dumps(schwellen, indent=2), encoding="utf-8")

    print(f"Training: {sum(1 for s in train if s['id'] in roh)} Bilder, globale Schwelle {global_t}")
    print(f"{'Gruppe':26} {'Beispiele':>9} {'F1@0.5':>7} {'Schwelle':>8} {'F1':>6}")
    for g, pos, f_alt, t, f_neu in sorted(zeilen, key=lambda z: -z[1]):
        if pos:
            print(f"{GRUPPEN[g][0]:26} {pos:9} {f_alt:7.2f} {t:8.2f} {f_neu:6.2f}")
    # Gesamt-F1 mit je Gruppe eigener Schwelle: Schwelle vorab abziehen, dann gilt überall 0
    kalibriert = [(p - schwellen[g], w) for g, liste in paare.items() for p, w in liste]
    print(f"Gesamt-F1 Training: {f1(alle, 0.5):.2f} mit Schwelle 0.5 -> {f1(kalibriert, 0):.2f} kalibriert")
    print(f"Schwellen -> {OUT / 'clef_schwellen.json'}  |  Testen: python -m training.evaluieren")


if __name__ == "__main__":
    main()
