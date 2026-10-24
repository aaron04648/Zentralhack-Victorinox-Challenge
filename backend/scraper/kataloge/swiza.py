"""SWIZA Taschenmesser (catalogues/Swiza_Messer.pdf, Katalog eines Wiederverkäufers).

Das PDF enthält nur eingescannte Seiten, deshalb OCR mit Tesseract (Kommandozeile, eng).
Jede Seite hat drei Spalten: Modell + "N functions" | Werkzeuge (Englisch, Französisch,
Deutsch als je ein Absatz) | Artikel-Grundnummer ("KSH.0010.") mit Farbcodes ("1000 Red").
Gerade und ungerade Seiten sind gegeneinander verschoben; die Spalten werden pro Seite an
den "N functions"-Zeilen ausgerichtet.

OCR-Korrekturen:
- Modellnamen: O/0 nach SWIZA-Schema "1–2 Buchstaben + 2 Ziffern + Zusatz" ("SHO1R" -> "SH01 R").
  Bleibt ein Name unlesbar ("1703", nur "(WAVY EDGE)"), wird er vom selben Modell in einem anderen
  Abschnitt übernommen: Die Artikelnummer ist Serie + 3 Ziffern Modell + 1 Ziffer Abschnitt
  (SH01 R = KSH.0010 / .0016 / .0013, SH01 TR = KST.0010 / .0016 / .0013).
- Farbnamen: pro Farbcode der häufigste gelesene Name (der Code bedeutet überall dieselbe Farbe)
- Sondereditionen S. 27–29: Kürzel in dünner, hellgrauer Schrift sind per OCR nicht zuverlässig
  lesbar (3 wird zu S); Modell und Artikelnummer stehen deshalb in SONDEREDITIONEN,
  manuell am PDF geprüft.

Die Funktionsanzahl von SWIZA zählt Kombi-Werkzeuge einzeln ("Bottle opener with screwdriver
& wire bender" = 3) und taugt daher nicht als Prüfsumme für die Werkzeugliste.

Aufruf:  python -m scraper.kataloge.swiza        (braucht tesseract im PATH, ~2 min)
Ausgabe: data/kataloge/swiza.json
"""

import collections
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pymupdf

from scraper.kataloge.pdf import KATALOGE_PDF, schreibe

PDF = KATALOGE_PDF / "Swiza_Messer.pdf"
DPI = 400
FUNKTIONEN = re.compile(r"^(\d+)\s*functions?$")
GRUNDNUMMER = re.compile(r"^(K[A-Z0-9]{2})[A-Z]?[.,]+\s?(\d{4})[.,]*$")
ZIFFERNAEHNLICH = "0123456789OILSG"
GUELTIGES_MODELL = re.compile(r"^[A-Z]{1,2}\d{2}( |$)")
OCR_WOERTER = {r"\baw[!|1l]": "awl", r"\bfiat\b": "flat", r"\bfiat-": "flat-"}  # häufige Lesefehler in den Werkzeugtexten
PRAEFIXE_2 = {"SH", "TT", "BL", "WO", "HO", "GO", "CO", "GR", "GS", "WM"}  # sonst ein Buchstabe

# Seite 2–15: Standardsortiment; 16–22 und 23–26: dieselben Modelle mit anderen Artikelnummern
# (23–26 laut Abbildungen mit schwarzer Klinge und schwarzen Werkzeugen); 27–29: Sondereditionen.
ABSCHNITTE = [(2, 15, 1, None), (16, 22, 2, None), (23, 26, 3, "schwarze Klinge und Werkzeuge (laut Abbildungen)"),
              (27, 29, 4, "Sonderedition")]
SONDEREDITIONEN = {  # Seite -> [(Modell, Artikelnummer)] in Reihenfolge auf der Seite
    27: [("D01 HEIMAT", "KNB.0010.HEI1"), ("D01 HEIMAT", "KNB.0010.HEI2"), ("D01 HEIMAT", "KNB.0010.HEI3"),
         ("D03 HEIMAT", "KNB.0030.HEI1"), ("D03 HEIMAT", "KNB.0030.HEI2")],
    28: [("D03 HEIMAT", "KNB.0030.HEI3"), ("D03 MARGUERITE", "KNB.0030.MAR2"), ("D03 ST BERNARD", "KNB.0030.STB1"),
         ("D03 EDELWEISS BLUE", "KNB.0030.EDW1"), ("D03 EDELWEISS ROSA", "KNB.0030.EDW2")],
    29: [("D03 HORSE", "KNB.0030.FA01"), ("D03 BOUVIER", "KNB.0030.FA05"),
         ("D03 CHINESE NEW YEAR 3", "KNB.0030.CN03"), ("D03 CHINESE NEW YEAR 4", "KNB.0030.CN04")],
}


def woerter(page):
    """OCR einer Seite: Wörter mit relativer Position. Zwischengespeichert, weil langsam."""
    schluessel = hashlib.md5(f"{PDF.stat().st_size}-{PDF.stat().st_mtime}-{page.number}-{DPI}".encode()).hexdigest()
    cache = Path(tempfile.gettempdir()) / "swiza_ocr" / f"{schluessel}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
    tsv = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "11", "-l", "eng", "tsv"],
                         input=pix.tobytes("png"), capture_output=True, check=True).stdout.decode()
    out = [{"t": r["text"], "x": int(r["left"]) / pix.width, "y": int(r["top"]) / pix.height, "h": int(r["height"]) / pix.height}
           for r in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE)
           if r["level"] == "5" and r["text"].strip() and float(r["conf"]) > 0]
    cache.parent.mkdir(exist_ok=True)
    cache.write_text(json.dumps(out))
    return out


def nachlesen(page, x0, y0, x1, y1):
    """Einen kleinen Bereich gezielt bei 600 dpi als einzelne Zeile lesen."""
    r = page.rect
    pix = page.get_pixmap(dpi=600, colorspace=pymupdf.csGRAY,
                          clip=pymupdf.Rect(x0 * r.width, y0 * r.height, x1 * r.width, y1 * r.height))
    return subprocess.run(["tesseract", "stdin", "stdout", "--psm", "7", "-l", "eng"],
                          input=pix.tobytes("png"), capture_output=True).stdout.decode().strip()


def zeilen(ws, x0, x1):
    """Wörter einer Spalte zu Zeilen gruppieren (ähnliche Höhe), links nach rechts."""
    out = []
    for w in sorted((w for w in ws if x0 <= w["x"] < x1), key=lambda w: w["y"] + w["h"] / 2):
        m = w["y"] + w["h"] / 2
        if out and abs(out[-1]["m"] - m) < 0.0045:
            out[-1]["w"].append(w)
        else:
            out.append({"m": m, "w": [w]})
    for z in out:
        z["w"].sort(key=lambda w: w["x"])
        z["t"] = " ".join(w["t"] for w in z["w"])
        z["y"] = min(w["y"] for w in z["w"])
    return out


def modell(text):
    """"SHO1R" -> "SH01 R", "JO2R" -> "J02 R", "wooo" -> "WO00"; sonst der gelesene Text."""
    tokens = text.split()
    if not tokens:
        return None
    t = tokens[0].replace("i", "").upper()             # "i" ist OCR-Rauschen ("SHi10R")
    if len(t) > 2 and t[0].isalpha() and t[1] == "0" and t[:1] + "O" in PRAEFIXE_2:
        t = t[0] + "O" + t[2:]                          # "C003" -> "CO03"
    for n in (2, 1):
        prefix = t[:n]
        if not prefix.isalpha() or (n == 2 and prefix not in PRAEFIXE_2):
            continue
        lauf = ""
        for c in t[n:]:
            if c not in ZIFFERNAEHNLICH:
                break
            lauf += c
        gelesen = len(lauf)
        if gelesen == 3:  # ein Zeichen zu viel gelesen: "SHO02", "SH0O1" (ein O), "COO0O" (vorne)
            lauf = lauf.replace("O", "", 1) if "O" in lauf[1:] or lauf[0] == "O" else lauf[1:]
        if len(lauf) == 2:
            ziffern = lauf.translate(str.maketrans("OILSG", "01156"))
            return " ".join(f"{prefix}{ziffern} {t[n + gelesen:]} {' '.join(tokens[1:])}".split())
    return text.strip()


def werkzeuge(text):
    """Englischer Absatz -> Liste; Trenner sind Gedankenstriche (von der OCR auch als - = ~ gelesen)."""
    text = re.sub(r"\s*[—–]+\s*|\s+[-=~]+\s+|\s+-(?=[A-Z“\"])|(?<=[a-z,])-\s+", " — ", text)
    for falsch, richtig in OCR_WOERTER.items():
        text = re.sub(falsch, richtig, text)
    teile = [t.strip(" -—–=~") for t in text.split(" — ")]
    return [t for t in teile if len(t) > 1]


def abschnitt(seite):
    return next(((nr, hinweis) for von, bis, nr, hinweis in ABSCHNITTE if von <= seite <= bis), (None, None))


def seite_lesen(page, nr):
    ws = woerter(page)
    zahlen_x = [v["x"] for w in ws if w["t"].startswith("function")
                for v in ws if abs(v["y"] - w["y"]) < 0.003 and 0 < w["x"] - v["x"] < 0.025 and v["t"].isdigit()]
    if not zahlen_x:
        return []
    hx = min(zahlen_x)
    versatz = hx - 0.131
    kopf = zeilen(ws, hx - 0.006, 0.335 + versatz)
    mitte = zeilen(ws, 0.335 + versatz, 0.684 + versatz)
    artikel = zeilen(ws, 0.684 + versatz, 0.99)

    # Einträge: jede "N functions"-Zeile; der Modellname steht in der Zeile darüber
    eintraege = []
    for i, z in enumerate(kopf):
        fm = FUNKTIONEN.match(z["t"])
        if fm and i > 0 and z["y"] - kopf[i - 1]["y"] < 0.02:
            eintraege.append({"modell": modell(kopf[i - 1]["t"]), "funktionen": int(fm.group(1)), "y": kopf[i - 1]["y"]})

    produkte = []
    for i, e in enumerate(eintraege):
        y0, y1 = e["y"] - 0.004, (eintraege[i + 1]["y"] - 0.004 if i + 1 < len(eintraege) else 1)
        # Drei Absätze (Englisch, Französisch, Deutsch), getrennt durch grösseren Zeilenabstand
        absaetze = []
        for z in (z for z in mitte if y0 <= z["y"] < y1):
            if absaetze and z["m"] - absaetze[-1][-1]["m"] < 0.0105:
                absaetze[-1].append(z)
            else:
                absaetze.append([z])
        absaetze = [" ".join(z["t"] for z in a) for a in absaetze]

        basis, farben = None, []
        art = [z for z in artikel if y0 <= z["y"] < y1]
        for z in art:
            toks = z["t"].split()
            if toks and (m := GRUNDNUMMER.match(toks[0])):
                basis = f"{m.group(1).replace('0', 'O')}.{m.group(2)}"
                toks = toks[1:]
            if toks and re.match(r"^\d{4}$", toks[0]):
                farben.append({"code": toks[0], "farbe": " ".join(toks[1:]) or None})
        if not basis and art:  # Grundnummer von der OCR übersehen: links der ersten Farbzeile nachlesen
            x = min(w["x"] for w in art[0]["w"])
            roh = nachlesen(page, x - 0.065, art[0]["y"] - 0.004, x - 0.002, art[0]["y"] + 0.01)
            if m := GRUNDNUMMER.match(roh.split()[0] if roh.split() else ""):
                basis = f"{m.group(1).replace('0', 'O')}.{m.group(2)}"
                print(f"  nachgelesen S.{nr} {e['modell']}: {roh!r} -> {basis}", file=sys.stderr)

        nr_abschnitt, hinweis = abschnitt(nr)
        produkte.append({
            "modell": e["modell"], "seite": nr, "abschnitt": nr_abschnitt,
            **({"abschnitt_hinweis": hinweis} if hinweis else {}),
            "anzahl_funktionen": e["funktionen"],
            "werkzeuge": werkzeuge(absaetze[0]) if absaetze else [],
            "beschreibung_de": absaetze[2] if len(absaetze) >= 3 else None,
            "basis": basis, "farben": farben,
        })

    if nr in SONDEREDITIONEN:
        geprueft = SONDEREDITIONEN[nr]
        if len(geprueft) != len(produkte):
            print(f"  WARNUNG S.{nr}: {len(produkte)} Einträge gelesen, {len(geprueft)} erwartet", file=sys.stderr)
        for p, (name, nummer) in zip(produkte, geprueft):
            p["modell"], p["basis"], p["farben"] = name, nummer, []
    return produkte


def farbnamen_bereinigen(produkte):
    """Pro Farbcode der häufigste gelesene Name ("Blus", "Biue" -> "Blue")."""
    namen = collections.defaultdict(collections.Counter)
    for p in produkte:
        for f in p["farben"]:
            if f["farbe"]:
                namen[f["code"]][f["farbe"]] += 1
    beste = {code: zaehler.most_common(1)[0][0] for code, zaehler in namen.items()}
    for p in produkte:
        for f in p["farben"]:
            f["farbe"] = beste.get(f["code"], f["farbe"])


def modelle_ergaenzen(produkte):
    """Unlesbare Modellnamen vom selben Modell eines anderen Abschnitts übernehmen (gleiche Serie + Modellziffern)."""
    schluessel = lambda p: (p["basis"][:3], p["basis"][4:7]) if p["basis"] and len(p["basis"]) >= 8 else None
    bekannt = {}
    for p in produkte:
        p["modell"] = " ".join(p["modell"].split())
        if GUELTIGES_MODELL.match(p["modell"]) and schluessel(p):
            bekannt.setdefault(schluessel(p), p["modell"])
    for p in produkte:
        if not GUELTIGES_MODELL.match(p["modell"]) and schluessel(p) in bekannt:
            print(f"  Modell S.{p['seite']} {p['basis']}: {p['modell']!r} -> {bekannt[schluessel(p)]!r}", file=sys.stderr)
            p["modell"] = bekannt[schluessel(p)]
    for p in produkte:
        if not GUELTIGES_MODELL.match(p["modell"]):
            print(f"  WARNUNG S.{p['seite']} {p['basis']}: Modellname unklar {p['modell']!r}", file=sys.stderr)


def als_produkt(p):
    basis = p["basis"]
    sonderedition = p["abschnitt"] == 4
    return {
        "id": f"swiza:{basis}" if basis else None,
        "marke": "SWIZA",
        "artikelnummer": basis,
        "modell": p["modell"],
        "name": f"SWIZA {p['modell']}",
        "seite": p["seite"],
        "abschnitt": p["abschnitt"],
        **({"abschnitt_hinweis": p["abschnitt_hinweis"]} if "abschnitt_hinweis" in p else {}),
        "anzahl_funktionen": p["anzahl_funktionen"],
        "werkzeuge": p["werkzeuge"],
        "beschreibung_de": p["beschreibung_de"],
        "varianten": [] if sonderedition else [
            {"artikelnummer": f"{basis}.{f['code']}" if basis else None, "farbcode": f["code"], "farbe": f["farbe"]}
            for f in p["farben"]],
        "quelle": {"typ": "katalog_pdf_ocr", "datei": f"catalogues/{PDF.name}", "seite": p["seite"],
                   "verifiziert": False},
    }


def parse(pdf=PDF):
    doc = pymupdf.open(pdf)
    roh = []
    for nr, page in enumerate(doc, start=1):
        roh += seite_lesen(page, nr)
    farbnamen_bereinigen(roh)
    modelle_ergaenzen(roh)
    return [als_produkt(p) for p in roh]


def main():
    produkte = parse()
    pfad = schreibe(produkte, "swiza.json", quelle=f"catalogues/{PDF.name}",
                    titel="SWIZA Swiss Pocket Knives (Meier's Neuheiten AG)", marke="SWIZA", sprache="en",
                    hinweis="OCR aus eingescannten Seiten; Texte können Lesefehler enthalten")
    ohne = [p["modell"] for p in produkte if not p["id"]]
    print(f"{len(produkte)} Messer -> {pfad}" + (f" (ohne Artikelnummer: {ohne})" if ohne else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
