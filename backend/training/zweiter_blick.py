"""Performance-Test für den zweiten Blick (clef.werkzeuge_pruefen): Werkzeugerkennung vorher/nachher.

Pro Bild (Katalog aus datensatz.jsonl, Wahrheit = werkzeug_gruppen):
  1. Erkennung wie in der App (Clef-Rohwerte aus dem Cache, clef.auswerten)
  2. Röntgenblick (clef.lokalisieren) für alle erkannten Werkzeuge
  3. Zweiter Blick (clef.werkzeuge_pruefen) für alle verorteten Werkzeuge
Schritt 2 und 3 werden mit Zeitmessung gecacht (data/training/zweiter_blick_cache.jsonl), damit
sich verschiedene Grenzen ohne neue Clef-Anfragen vergleichen lassen. --neu fragt erneut.

Der zweite Blick hilft nicht bei jedem Werkzeug gleich: Kombiwerkzeuge (Schraubendreher am
Kapselheber) und Werkzeuge in der Schale (Pinzette, Zahnstocher) verneint er oft zu Unrecht.
--kalibrieren bestimmt darum auf dem Trainingsteil je Gruppe, ob und ab welcher Grenze der zweite
Blick ein Werkzeug streichen darf (-> data/training/zweiter_blick_grenzen.json, von app/clef.py
geladen). Ohne --kalibrieren wird auf dem Testteil gemessen, auch mit diesen Grenzen je Gruppe.

Aufruf:  python -m training.zweiter_blick [--kalibrieren] [--limit N] [--neu] [--grenze 0.2]
                                         [--regel streng|kombiniert]
Ergebnis: data/training/auswertung_zweiter_blick.json
"""

import argparse
import hashlib
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from app import clef
from training.clef_kalibrieren import roh_fuer
from training.evaluieren import OUT, prf

CACHE = OUT / "zweiter_blick_cache.jsonl"
GRENZEN = [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5]
PARALLEL = 4
MIN_GEWINN_F1 = 0.02       # so viel muss eine Gruppe im Training gewinnen, sonst prüft der zweite Blick sie nicht
MIN_FAELLE = 3             # und so viele Treffer + Fehlalarme braucht es, damit das Urteil zählt


def samples_laden(split):
    samples = [json.loads(z) for z in (OUT / "datensatz.jsonl").read_text(encoding="utf-8").splitlines()]
    return [s for s in samples if s["split"] == split]


def konfig():
    """Ändert sich Ausschnitt, Raster oder Fragetext, gilt der Cache nicht mehr."""
    import inspect
    quelle = inspect.getsource(clef.werkzeuge_pruefen) + inspect.getsource(clef._ausschnitt) + \
        inspect.getsource(clef._pruef_raster)
    werte = f"{clef.PRUEF_RASTER}/{clef.PRUEF_AUSSCHNITT}/{clef.PRUEF_QUELLE_PX}/{clef.modell()}"
    return hashlib.sha1((quelle + werte).encode()).hexdigest()[:10]


def cache_laden(k):
    if not CACHE.exists():
        return {}
    eintraege = (json.loads(z) for z in CACHE.read_text(encoding="utf-8").splitlines() if z.strip())
    return {e["id"]: e for e in eintraege if e["konfig"] == k}


def messen(s, erkannt, k):
    gruppen = [w["gruppe"] for w in erkannt["werkzeuge"]]
    bild = clef.bild_vorbereiten(s["bild_url"])
    t1 = time.perf_counter()
    orte = clef.lokalisieren(bild, gruppen) if gruppen else {}
    t2 = time.perf_counter()
    pruefung = clef.werkzeuge_pruefen(s["bild_url"], orte) if orte else {}
    t3 = time.perf_counter()
    return {"id": s["id"], "konfig": k, "orte": orte, "pruefung": pruefung,
            "zeit_roentgen": round(t2 - t1, 2), "zeit_pruefung": round(t3 - t2, 2)}


def behalten(gruppe, p, v, grenze, regel):
    """Erstes Urteil p, zweiter Blick v (None = nicht geprüft) -> Werkzeug behalten?

    grenze: None (ohne zweiten Blick), eine Zahl für alle Gruppen oder {gruppe: grenze}.
    """
    if isinstance(grenze, dict):
        grenze = grenze.get(gruppe)
    if grenze is None or v is None:
        return True
    if regel == "streng":
        return v >= grenze
    return (p * v) ** 0.5 >= grenze  # kombiniert: geometrisches Mittel beider Blicke


def bewerten(samples, erkannt, cache, grenze, regel="streng"):
    """-> (gesamt tp/fp/fn, je Gruppe tp/fp/fn). grenze=None: ohne zweiten Blick."""
    gesamt = [0, 0, 0]
    je_gruppe = {}
    for s in samples:
        wahr = set(s["werkzeug_gruppen"])
        pruefung = cache[s["id"]]["pruefung"]
        gefunden = {w["gruppe"] for w in erkannt[s["id"]]["werkzeuge"]
                    if behalten(w["gruppe"], w["wahrscheinlichkeit"], pruefung.get(w["gruppe"]), grenze, regel)}
        for g in wahr | gefunden:
            z = je_gruppe.setdefault(g, [0, 0, 0])
            i = 0 if g in wahr and g in gefunden else 1 if g in gefunden else 2
            z[i] += 1
            gesamt[i] += 1
    return gesamt, je_gruppe


def kalibrieren(samples, erkannt, cache):
    """Je Gruppe die strenge Grenze mit dem besten F1 im Training; nur wenn sie klar hilft."""
    _, vorher = bewerten(samples, erkannt, cache, None)
    ergebnis = {}
    for g, (tp, fp, fn) in sorted(vorher.items()):
        f1_vorher = prf(tp, fp, fn)[2]
        beste, f1_beste = None, f1_vorher
        for grenze in GRENZEN:
            _, nachher = bewerten(samples, erkannt, cache, {g: grenze})
            f1 = prf(*nachher.get(g, [0, 0, tp + fn]))[2]
            if f1 > f1_beste + 1e-9:
                beste, f1_beste = grenze, f1
        genug = tp + fp >= MIN_FAELLE
        if beste is not None and genug and f1_beste - f1_vorher >= MIN_GEWINN_F1:
            ergebnis[g] = beste
        print(f"  {g:<24} F1 {f1_vorher:.2f} -> {f1_beste:.2f}  Grenze {beste}  "
              f"{'übernommen' if g in ergebnis else '-'}", file=sys.stderr)
    return ergebnis


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--neu", action="store_true", help="Röntgen + zweiten Blick neu abfragen")
    parser.add_argument("--grenze", type=float, default=0.2, help="Grenze für die Tabelle je Gruppe")
    parser.add_argument("--regel", choices=["streng", "kombiniert"], default="streng")
    parser.add_argument("--kalibrieren", action="store_true", help="Grenzen je Gruppe auf dem Trainingsteil lernen")
    args = parser.parse_args()

    samples = samples_laden("train" if args.kalibrieren else "test")[:args.limit]
    roh = roh_fuer(samples)
    samples = [s for s in samples if s["id"] in roh]
    erkannt = {s["id"]: clef.auswerten(roh[s["id"]]) for s in samples}

    k = konfig()
    cache = {} if args.neu else cache_laden(k)
    fehlend = [s for s in samples if s["id"] not in cache]
    if fehlend:
        print(f"  {len(fehlend)} Bilder: Röntgen + zweiter Blick ({len(samples) - len(fehlend)} aus dem Cache)",
              file=sys.stderr)

        def abfragen(s):
            try:
                return messen(s, erkannt[s["id"]], k)
            except Exception as fehler:
                print(f"\n  Fehler bei {s['id']}: {fehler}", file=sys.stderr)
                return None

        with CACHE.open("a", encoding="utf-8") as f, ThreadPoolExecutor(PARALLEL) as pool:
            for i, e in enumerate(pool.map(abfragen, fehlend), 1):
                if e:
                    cache[e["id"]] = e
                    f.write(json.dumps(e) + "\n")
                    f.flush()
                print(f"\r  {i}/{len(fehlend)}", end="", file=sys.stderr)
        print(file=sys.stderr)
    samples = [s for s in samples if s["id"] in cache]

    if args.kalibrieren:
        grenzen = kalibrieren(samples, erkannt, cache)
        clef.PRUEF_GRENZEN.write_text(json.dumps({"konfig": k, "bilder": len(samples), "grenzen": grenzen},
                                                 ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{len(grenzen)} Gruppen mit zweitem Blick: {grenzen}\n-> {clef.PRUEF_GRENZEN}")
        return
    je_gruppe = clef.pruef_grenzen()

    zeilen = []
    for regel in ("streng", "kombiniert"):
        for grenze in [None, *GRENZEN] if regel == "streng" else GRENZEN:
            (tp, fp, fn), _ = bewerten(samples, erkannt, cache, grenze, regel)
            p, r, f1 = prf(tp, fp, fn)
            zeilen.append({"regel": regel, "grenze": grenze, "tp": tp, "fp": fp, "fn": fn,
                           "precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3)})
    if je_gruppe:
        (tp, fp, fn), _ = bewerten(samples, erkannt, cache, je_gruppe)
        p, r, f1 = prf(tp, fp, fn)
        zeilen.append({"regel": "je Gruppe", "grenze": "gelernt", "tp": tp, "fp": fp, "fn": fn,
                       "precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3)})
        args.grenze, args.regel = je_gruppe, "streng"

    _, vorher = bewerten(samples, erkannt, cache, None)
    _, nachher = bewerten(samples, erkannt, cache, args.grenze, args.regel)
    pro_gruppe = {}
    for g in sorted(vorher):
        a, b = prf(*vorher[g]), prf(*nachher.get(g, [0, 0, vorher[g][0] + vorher[g][2]]))
        pro_gruppe[g] = {"support": vorher[g][0] + vorher[g][2],
                         "fp_vorher": vorher[g][1], "fp_nachher": nachher.get(g, [0, 0, 0])[1],
                         "precision_vorher": round(a[0], 2), "precision_nachher": round(b[0], 2),
                         "recall_vorher": round(a[1], 2), "recall_nachher": round(b[1], 2)}

    roentgen = [cache[s["id"]]["zeit_roentgen"] for s in samples if cache[s["id"]]["orte"]]
    pruefung = [cache[s["id"]]["zeit_pruefung"] for s in samples if cache[s["id"]]["pruefung"]]
    zeiten = {"bilder": len(samples),
              "roentgen_median_s": round(statistics.median(roentgen), 2) if roentgen else None,
              "pruefung_median_s": round(statistics.median(pruefung), 2) if pruefung else None,
              "pruefung_p90_s": round(sorted(pruefung)[int(0.9 * (len(pruefung) - 1))], 2) if pruefung else None,
              "gepruefte_werkzeuge": sum(len(cache[s["id"]]["pruefung"]) for s in samples),
              "erkannte_werkzeuge": sum(len(erkannt[s["id"]]["werkzeuge"]) for s in samples)}

    print(f"\n{len(samples)} Testbilder (Katalog), Konfiguration {k}\n")
    print("Regel        Grenze     TP   FP   FN  Precision  Recall    F1")
    for z in zeilen:
        name = "ohne" if z["grenze"] is None else z["grenze"] if isinstance(z["grenze"], str) else f"{z['grenze']:.2f}"
        print(f"{z['regel']:<12} {name:>6} {z['tp']:>6} {z['fp']:>4} {z['fn']:>4}  "
              f"{z['precision']:>9.3f} {z['recall']:>7.3f} {z['f1']:>5.3f}")
    print(f"\nJe Gruppe, {'gelernte Grenzen' if je_gruppe else f'Regel {args.regel}, Grenze {args.grenze}'} (nur Gruppen, deren Fehlalarme oder Treffer sich ändern):")
    for g, w in pro_gruppe.items():
        if (w["fp_vorher"], w["recall_vorher"]) != (w["fp_nachher"], w["recall_nachher"]):
            print(f"  {g:<24} FP {w['fp_vorher']:>2} -> {w['fp_nachher']:>2}   "
                  f"Recall {w['recall_vorher']:.2f} -> {w['recall_nachher']:.2f}   (Support {w['support']})")
    print(f"\nZeit: Röntgen {zeiten['roentgen_median_s']} s, zweiter Blick {zeiten['pruefung_median_s']} s "
          f"(Median, p90 {zeiten['pruefung_p90_s']} s), {zeiten['gepruefte_werkzeuge']} von "
          f"{zeiten['erkannte_werkzeuge']} erkannten Werkzeugen geprüft")

    ziel = OUT / "auswertung_zweiter_blick.json"
    ziel.write_text(json.dumps({"konfig": k, "gesamt": zeilen, "grenze_je_gruppe": args.grenze, "regel": args.regel,
                                "pro_gruppe": pro_gruppe, "zeiten": zeiten}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    print(f"-> {ziel}")


if __name__ == "__main__":
    main()
