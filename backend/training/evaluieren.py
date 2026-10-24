"""Testet die Werkzeugerkennung gegen die Victorinox-CSV (Testteil aus datensatz.jsonl).

Gemessen wird:
- Werkzeugerkennung: Precision / Recall / F1 je Gruppe und gesamt, Anteil exakt richtiger Sets
- Matching: Ist das fotografierte Produkt unter den Top 1 / Top 3 des Katalogs?
  "gleichwertig" zählt auch Produkte mit identischem Werkzeugset (z. B. Farbvarianten).

Modi:
  vision   echte Bilderkennung (app/vision.py, Azure/OpenAI; Basis+Referenzen oder Fine-Tune)
  oracle   nimmt die wahren Werkzeuge als "erkannt" -> Obergrenze des Matchings, ohne API-Kosten

Aufruf:  python -m training.evaluieren [--modus vision|oracle] [--jev] [--limit 10]
Ergebnis: data/training/auswertung_<modus>.json
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from app import jev, matching, vision
from app.werkzeuge import GRUPPEN

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "training"


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--modus", choices=["vision", "oracle"], default="vision")
    parser.add_argument("--jev", action="store_true", help="Werkzeuge zusätzlich mit Jev zuordnen")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    samples = [json.loads(z) for z in (OUT / "datensatz.jsonl").read_text(encoding="utf-8").splitlines()]
    test = [s for s in samples if s["split"] == "test"]
    if args.limit:
        test = test[:args.limit]
    with (DATA / "victorinox_sak_produkte.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    gruppen_von = {r["artikelnummer"]: matching.produkt_gruppen(r) for r in rows}

    zaehler = {g: Counter() for g in GRUPPEN}
    details, exakt_sets, top1, top3, top3_gleich, fehler = [], 0, 0, 0, 0, 0
    for i, s in enumerate(test, 1):
        wahr = set(s["werkzeug_gruppen"])
        erkannt = {"marke": None, "modell": None, "artikelnummer_sichtbar": None, "werkzeuge": []}
        if args.modus == "oracle":
            erkannt_set = set(wahr)
        else:
            try:
                erkannt = vision.erkenne(s["bild_url"])
            except vision.VisionNichtKonfiguriert as e:
                sys.exit(str(e))
            except Exception as e:  # einzelne Bilder dürfen scheitern (Inhaltsfilter, Timeout)
                fehler += 1
                print(f"\n  Fehler bei {s['id']}: {e}", file=sys.stderr)
                continue
            werkzeuge = erkannt["werkzeuge"]
            if args.jev and (zugeordnet := jev.werkzeuge_zuordnen(werkzeuge)) is not None:
                werkzeuge = zugeordnet
            erkannt_set = {w["gruppe"] for w in werkzeuge}

        for g in GRUPPEN:
            if g in wahr and g in erkannt_set:
                zaehler[g]["tp"] += 1
            elif g in erkannt_set:
                zaehler[g]["fp"] += 1
            elif g in wahr:
                zaehler[g]["fn"] += 1
        exakt_sets += erkannt_set == wahr

        # Für den Test die Marke ausblenden: gemessen wird das Matching über Werkzeuge
        kandidaten = matching.rangliste(erkannt_set, rows, {}, top=3)
        nummern = [k["row"]["artikelnummer"] for k in kandidaten]
        top1 += bool(nummern) and nummern[0] == s["artikelnummer"]
        top3 += s["artikelnummer"] in nummern
        top3_gleich += any(gruppen_von[n] == wahr for n in nummern)
        details.append({
            "id": s["id"], "name": s["name"], "wahr": sorted(wahr), "erkannt": sorted(erkannt_set),
            "fehlend": sorted(wahr - erkannt_set), "falsch": sorted(erkannt_set - wahr),
            "top3": [f"{k['row']['name']} ({k['row']['artikelnummer']}, {k['score']})" for k in kandidaten],
        })
        print(f"\r  {i}/{len(test)}", end="", file=sys.stderr)
    print(file=sys.stderr)

    n = len(details)
    if not n:
        sys.exit("Keine Testbilder ausgewertet.")
    gesamt = Counter()
    for c in zaehler.values():
        gesamt.update(c)
    p, r, f1 = prf(gesamt["tp"], gesamt["fp"], gesamt["fn"])
    pro_gruppe = {
        g: dict(zip(("precision", "recall", "f1"), (round(x, 3) for x in prf(c["tp"], c["fp"], c["fn"]))),
                support=c["tp"] + c["fn"])
        for g, c in zaehler.items() if c["tp"] + c["fn"] + c["fp"]
    }
    ergebnis = {
        "modus": args.modus + ("+jev" if args.jev else ""),
        "testbilder": n, "fehler": fehler,
        "werkzeuge": {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3),
                      "exakt_richtige_sets": round(exakt_sets / n, 3)},
        "matching": {"top1_exakt": round(top1 / n, 3), "top3_exakt": round(top3 / n, 3),
                     "top3_gleichwertig": round(top3_gleich / n, 3)},
        "pro_gruppe": pro_gruppe,
        "details": details,
    }
    pfad = OUT / f"auswertung_{ergebnis['modus']}.json"
    pfad.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Modus {ergebnis['modus']}: {n} Testbilder" + (f", {fehler} Fehler" if fehler else ""))
    print(f"Werkzeuge  Precision {p:.2f}  Recall {r:.2f}  F1 {f1:.2f}  exakte Sets {exakt_sets / n:.0%}")
    print(f"Matching   Top-1 {top1 / n:.0%}  Top-3 {top3 / n:.0%}  Top-3 gleichwertig {top3_gleich / n:.0%}")
    schwach = sorted((v["f1"], g) for g, v in pro_gruppe.items() if v["support"] >= 3)[:5]
    if args.modus == "vision" and schwach:
        print("Schwächste Gruppen: " + ", ".join(f"{GRUPPEN[g][0]} ({f:.2f})" for f, g in schwach))
    print(f"Details -> {pfad}")


if __name__ == "__main__":
    main()
