"""Testet die Erkennung gegen Daten, die das Modell nicht gesehen hat.

Testsets:
  katalog  Victorinox-Testteil aus datensatz.jsonl (Werkzeugsets nicht im Training), Wahrheit = CSV
  fotos    die 12 Kundenfotos aus dem Input-PDF (data/sak_ground_truth): Marke, und für
           die 5 Victorinox-Fotos auch das Produkt (Labels korrigiert, siehe FOTO_KORREKTUR)

Gemessen wird:
- Werkzeugerkennung (nur katalog): Precision / Recall / F1 je Gruppe und gesamt
- Matching: Ist das richtige Produkt Top 1 / Top 3? "gleichwertig" zählt auch Produkte mit
  identischem Werkzeugset oder Namen (Farbvarianten). Mit --bildwahl zusätzlich die visuelle
  Katalogsuche von Clef (app/clef.py visuell_suchen), wie sie /api/match verwendet.
  Achtung: Beim Katalog-Testset ist das Testbild das Katalogbild selbst; für die Bildsuche
  ist das zu leicht. Ehrlich ist dort nur das Werkzeug-Matching, für die Bildsuche das Set fotos.

Modi:
  vision   echte Bilderkennung (app/vision.py: Clef oder OpenAI, je nach .env)
  oracle   wahre Werkzeuge als "erkannt" -> Obergrenze des Matchings, ohne API-Kosten

Clef-Antworten aus training/clef_kalibrieren.py (data/training/clef_cache.jsonl) werden
wiederverwendet; neue Bilder werden abgefragt und ebenfalls gecacht.

Aufruf:  python -m training.evaluieren [--set katalog|fotos] [--modus vision|oracle]
                                       [--bildwahl] [--jev] [--limit 10]
Ergebnis: data/training/auswertung_<set>_<modus>.json
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from app import clef, jev, matching, vision
from app.werkzeuge import GRUPPEN
from training.clef_kalibrieren import roh_fuer

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "training"
FOTOS = DATA / "sak_ground_truth"
FOTO_MARKEN = {"Roxon": "Roxon", "The Helton": "The Helton", "Swiza": "SWIZA"}
# Die Notizzettel auf PDF-Seite 13 und 22 sind nach Spalte statt nach Bild zugeordnet
# (labels.json). Richtig ist laut Bild und den übrigen Notizen im PDF:
FOTO_KORREKTUR = {
    "p13_Im1_obj16": ("Leatherman", None),
    "p13_Im2_obj18": ("Victorinox", "3.0224.3CN"),   # Swiss Tool Spirit XBS
    "p13_Im3_obj19": ("Gerber", None),
    "p13_Im4_obj21": ("Victorinox", "3.0323.L"),     # Swiss Tool
    "p22_Im1_obj24": ("Gerber", None),
    "p22_Im2_obj26": ("Victorinox", "0.9411.D20"),   # Evoke Alox
    "p22_Im3_obj27": ("Benchmade", None),
}


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def katalog_samples():
    samples = [json.loads(z) for z in (OUT / "datensatz.jsonl").read_text(encoding="utf-8").splitlines()]
    return [s for s in samples if s["split"] == "test"]


def foto_samples(rows):
    """Kundenfotos; bei Victorinox-Fotos die Artikelnummer und Werkzeuge aus dem Katalog."""
    if not FOTOS.exists():
        sys.exit(f"{FOTOS} fehlt (docker compose up -d backend, Volume aus docker-compose.yml)")
    samples = []
    for eintrag in json.loads((FOTOS / "labels.json").read_text(encoding="utf-8")):
        name = f"p{eintrag['page']}_{eintrag['xobj']}_obj{eintrag['obj']}"
        label = eintrag["label"]
        nummer = label.split("SKU")[-1].strip(" :)") if "SKU" in label else None
        marke = "Victorinox" if nummer else FOTO_MARKEN.get(label, label)
        if name in FOTO_KORREKTUR:
            marke, nummer = FOTO_KORREKTUR[name]
            label = f"{marke} {nummer or ''}".strip()
        row = next((r for r in rows if nummer and (r["artikelnummer"] == nummer or nummer in
                    r["varianten_artikelnummern"].replace(" ", "").split(","))), None)
        samples.append({
            "id": f"foto-{name}",
            "name": label,
            "marke": marke,
            "artikelnummer": row["artikelnummer"] if row else None,
            "werkzeug_gruppen": sorted(matching.produkt_gruppen(row)) if row else None,
            "bild_url": "data:image/png;base64," + __import__("base64").b64encode(
                (FOTOS / f"{name}.png").read_bytes()).decode(),
        })
    return samples


def erkennen(samples, modus, mit_jev):
    """-> {id: erkannt} im Format von vision.erkenne (ohne modell_info)."""
    if modus == "oracle":
        return {s["id"]: {"werkzeuge": [{"gruppe": g} for g in s["werkzeug_gruppen"] or []],
                          "marke": s["marke"]} for s in samples}
    ergebnisse = {}
    if vision.anbieter() == "clef":
        if not clef.aktiv():
            sys.exit("OPENROUTER_API_KEY fehlt in .env")
        for sid, roh in roh_fuer(samples).items():
            ergebnisse[sid] = clef.auswerten(roh)
    else:
        for i, s in enumerate(samples, 1):
            try:
                ergebnisse[s["id"]] = vision.erkenne(s["bild_url"])
            except vision.VisionNichtKonfiguriert as e:
                sys.exit(str(e))
            except Exception as e:  # einzelne Bilder dürfen scheitern (Quote, Inhaltsfilter)
                print(f"\n  Fehler bei {s['id']}: {e}", file=sys.stderr)
            print(f"\r  {i}/{len(samples)}", end="", file=sys.stderr)
        print(file=sys.stderr)
    if mit_jev:
        for e in ergebnisse.values():
            if (zugeordnet := jev.werkzeuge_zuordnen(e["werkzeuge"])) is not None:
                e["werkzeuge"] = zugeordnet
    return ergebnisse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=["katalog", "fotos"], default="katalog")
    parser.add_argument("--modus", choices=["vision", "oracle"], default="vision")
    parser.add_argument("--bildwahl", action="store_true", help="zusätzlich visuelle Katalogsuche mit Clef")
    parser.add_argument("--jev", action="store_true", help="Werkzeuge zusätzlich mit Jev zuordnen")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    with (DATA / "victorinox_sak_produkte.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    gruppen_von = {r["artikelnummer"]: matching.produkt_gruppen(r) for r in rows}
    name_von = {r["artikelnummer"]: r["name"] for r in rows}
    messer = [r for r in rows if gruppen_von[r["artikelnummer"]]]
    nach_nummer = {r["artikelnummer"]: r for r in rows}
    samples = katalog_samples() if args.set == "katalog" else foto_samples(rows)
    if args.modus == "oracle":
        samples = [s for s in samples if s["werkzeug_gruppen"]]
    if args.limit:
        samples = samples[:args.limit]
    erkannt_von = erkennen(samples, args.modus, args.jev)

    zaehler = {g: Counter() for g in GRUPPEN}
    treffer = Counter()  # top1, top3, top3_gleich, (+ _bild), marke, mit_produkt
    details = []
    for s in samples:
        if s["id"] not in erkannt_von:
            continue
        erkannt = erkannt_von[s["id"]]
        erkannt_set = {w["gruppe"] for w in erkannt["werkzeuge"]}
        treffer["n"] += 1
        treffer["marke"] += (erkannt.get("marke") or "").casefold() == s["marke"].casefold()
        eintrag = {"id": s["id"], "name": s["name"], "marke_wahr": s["marke"], "marke_erkannt": erkannt.get("marke"),
                   "erkannt": sorted(erkannt_set)}

        wahr = set(s["werkzeug_gruppen"]) if s["werkzeug_gruppen"] else None
        if wahr is not None and args.set == "katalog":
            for g in GRUPPEN:
                if g in wahr and g in erkannt_set:
                    zaehler[g]["tp"] += 1
                elif g in erkannt_set:
                    zaehler[g]["fp"] += 1
                elif g in wahr:
                    zaehler[g]["fn"] += 1
            treffer["exakt_sets"] += erkannt_set == wahr
            eintrag.update(fehlend=sorted(wahr - erkannt_set), falsch=sorted(erkannt_set - wahr))

        # Matching nur über Werkzeuge (Marke ausgeblendet), damit es messbar bleibt
        kandidaten = matching.rangliste(erkannt_set, rows, {}, top=3)
        varianten = [("", kandidaten)]
        if args.bildwahl and args.modus == "vision":
            treffer_bild = clef.visuell_suchen(clef.bild_vorbereiten(s["bild_url"]), messer)[:3]
            varianten.append(("_bild", [{"row": nach_nummer[n], "score": round(p, 3)} for n, p in treffer_bild]))
        if s["artikelnummer"]:
            treffer["mit_produkt"] += 1
            for suffix, top in varianten:
                nummern = [k["row"]["artikelnummer"] for k in top]
                treffer["top1" + suffix] += bool(nummern) and nummern[0] == s["artikelnummer"]
                treffer["top3" + suffix] += s["artikelnummer"] in nummern
                treffer["top3_gleich" + suffix] += any(gruppen_von[n] == gruppen_von[s["artikelnummer"]]
                                                       or name_von[n] == name_von[s["artikelnummer"]]
                                                       for n in nummern)
        for suffix, top in varianten:
            eintrag["top3" + suffix] = [f"{k['row']['name']} ({k['row']['artikelnummer']}, {k['score']})" for k in top]
        details.append(eintrag)

    n = treffer["n"]
    if not n:
        sys.exit("Keine Testbilder ausgewertet.")
    gesamt = Counter()
    for c in zaehler.values():
        gesamt.update(c)
    p, r, f1 = prf(gesamt["tp"], gesamt["fp"], gesamt["fn"])
    m = treffer["mit_produkt"] or 1
    modus = args.modus + ("" if args.modus == "oracle" else f"_{vision.anbieter()}") + ("+jev" if args.jev else "")
    ergebnis = {
        "set": args.set, "modus": modus, "bilder": n, "marke_richtig": round(treffer["marke"] / n, 3),
        "werkzeuge": {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3),
                      "exakt_richtige_sets": round(treffer["exakt_sets"] / n, 3)} if args.set == "katalog" else None,
        "matching": {k: round(treffer[k] / m, 3) for k in
                     ("top1", "top3", "top3_gleich", "top1_bild", "top3_bild", "top3_gleich_bild") if k in treffer
                     or not k.endswith("_bild")},
        "pro_gruppe": {g: dict(zip(("precision", "recall", "f1"), (round(x, 3) for x in prf(c["tp"], c["fp"], c["fn"]))),
                               support=c["tp"] + c["fn"])
                       for g, c in zaehler.items() if c["tp"] + c["fn"] + c["fp"]},
        "details": details,
    }
    pfad = OUT / f"auswertung_{args.set}_{modus}.json"
    pfad.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Set {args.set}, Modus {modus}: {n} Bilder, Marke richtig {treffer['marke'] / n:.0%}")
    if args.set == "katalog":
        print(f"Werkzeuge  Precision {p:.2f}  Recall {r:.2f}  F1 {f1:.2f}  exakte Sets {treffer['exakt_sets'] / n:.0%}")
    if treffer["mit_produkt"]:
        print(f"Matching ({treffer['mit_produkt']} Bilder mit bekanntem Produkt)")
        print(f"  nur Werkzeuge   Top-1 {treffer['top1'] / m:.0%}  Top-3 {treffer['top3'] / m:.0%}  "
              f"Top-3 gleichwertig {treffer['top3_gleich'] / m:.0%}")
        if "top1_bild" in treffer or args.bildwahl:
            print(f"  Bildsuche       Top-1 {treffer['top1_bild'] / m:.0%}  Top-3 {treffer['top3_bild'] / m:.0%}  "
                  f"Top-3 gleichwertig {treffer['top3_gleich_bild'] / m:.0%}")
    if args.set == "katalog" and args.modus == "vision":
        schwach = sorted((v["f1"], g) for g, v in ergebnis["pro_gruppe"].items() if v["support"] >= 3)[:5]
        print("Schwächste Gruppen: " + ", ".join(f"{GRUPPEN[g][0]} ({f:.2f})" for f, g in schwach))
    print(f"Details -> {pfad}")


if __name__ == "__main__":
    main()
