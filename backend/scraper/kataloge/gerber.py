"""Gerber Gear Full Line Product Catalog (catalogues/pds_sku_426118_productbrochure_manual data sheet.pdf, Englisch).

Querformat, eine oder mehrere Produktspalten pro Seite. Erkannt über Schrift und Position:

- Name: fett 11 pt ("MYTH® FOLDER"), Beschreibung: kursiv 7 pt darunter
- Specs: "BLADE LENGTH:" links, Wert rechts auf derselben Zeile (mehrzeilige Werte möglich)
- SKU-Zeilen unten (6 pt): Verpackung, Artikelnummer ("31-001164", "22-01145DS", ältere Multi-Tools fünfstellig
  "47530"), Ausführung (Schliff/Form, Farbe, Griff …)
- Fusszeile: Kategorie und Unterkategorie ("KNIVES | FOLDING SHEATH")
- Kundenzitate (graue, fette Kursivschrift) werden ignoriert

Die Schrift verwendet "Ø" für die Null ("3Ø-ØØØ717"); wird beim Lesen ersetzt.
Masse in Zoll und Unzen; zusätzlich in mm und g umgerechnet (Originalwert bleibt in "specs").

Aufruf:  python -m scraper.kataloge.gerber
Ausgabe: data/kataloge/gerber.json
"""

import re
import sys

import pymupdf

from scraper.kataloge.pdf import KATALOGE_PDF, schreibe, spans as pdf_spans

PDF = KATALOGE_PDF / "pds_sku_426118_productbrochure_manual data sheet.pdf"
SKU = re.compile(r"^(\d{2}-\d{4,6}[A-Z]{0,3}|\d{5})$")   # "31-001164", "22-01145DS", ältere Multi-Tools "47530"
GRAU_ZITAT = 0x969798


def spans(page):
    return [{**s, "t": s["t"].replace("Ø", "0").replace("ø", "0")} for s in pdf_spans(page)]


def hat_sku(s):
    """Textbaustein enthält eine Artikelnummer (teils mit Tabulator: "BACKER CARD\t 30-001223")."""
    return any(SKU.match(t.strip()) for t in s["t"].split("\t"))


def zoll_mm(text):
    m = re.search(r"([\d.]+)\s*(\"|”|IN\b)", text or "")
    return round(float(m.group(1)) * 25.4, 1) if m else None


def unzen_g(text):
    m = re.search(r"([\d.]+)\s*OZ", text or "")
    return round(float(m.group(1)) * 28.3495, 1) if m else None


def spalten(namen, breite):
    """Bereich jeder Produktspalte: vom Namen bis zum nächsten Namen in derselben Zeile."""
    bereiche = []
    for n in namen:
        rechts = [o["x"] for o in namen if o is not n and abs(o["y"] - n["y"]) < 40 and o["x"] > n["x"]]
        unten = [o["y"] for o in namen if o is not n and o["y"] > n["y"] + 40 and abs(o["x"] - n["x"]) < 60]
        bereiche.append((n, n["x"] - 5, min(rechts) - 5 if rechts else breite, n["y"] - 3, min(unten) - 3 if unten else 10_000))
    return bereiche


def produkt(name, block, sku_zeilen, kategorie, unterkategorie, seite):
    # Specs zeilenweise: Label links ("WEIGHT:"), Wert rechts auf derselben Zeile; Zeilen ohne Label
    # direkt darunter in der Wertspalte setzen den Wert fort ("DOWNRANGE: S30V" / "BLACK: 420HC")
    zeilen = []
    for s in sorted((s for s in block if abs(s["size"] - 7) < 0.3 and "Obl" not in s["font"] and s["color"] != GRAU_ZITAT),
                    key=lambda s: s["y"]):
        if zeilen and abs(s["y"] - zeilen[-1][0]["y"]) < 2:
            zeilen[-1].append(s)
        else:
            zeilen.append([s])
    specs, label, letzte_y = {}, None, None
    for zeile in zeilen:
        kopf = next((s for s in zeile if s["t"].endswith(":") and s["t"][:-1].isupper() and abs(s["x"] - name["x"]) < 5), None)
        werte = [s["t"] for s in sorted(zeile, key=lambda s: s["x"]) if s is not kopf and s["x"] > name["x"] + 30]
        if kopf:
            label = kopf["t"][:-1].strip()
            specs[label] = " ".join(werte)
        elif label and werte and zeile[0]["y"] - letzte_y < 9 and all(s["x"] > name["x"] + 30 for s in zeile):
            specs[label] = (specs[label] + " " + " ".join(werte)).strip()
        else:
            label = None
        letzte_y = zeile[0]["y"]
    beschreibung = " ".join(s["t"] for s in sorted(block, key=lambda s: s["y"]) if "Obl" in s["font"] and abs(s["size"] - 7) < 0.3)
    varianten = []
    for zeile in sku_zeilen:
        teile = [t.strip() for s in zeile for t in s["t"].split("\t") if t.strip()]
        sku_i = next(i for i, t in enumerate(teile) if SKU.match(t))
        varianten.append({"artikelnummer": teile[sku_i], "verpackung": " ".join(teile[:sku_i]) or None,
                          "ausfuehrung": teile[sku_i + 1:]})
    titel = " ".join(name["t"].replace("®", "").replace("™", "").split())
    return {
        "id": f"gerber:{varianten[0]['artikelnummer']}" if varianten else f"gerber:{re.sub(r'[^a-z0-9]+', '-', titel.lower())}",
        "marke": "Gerber",
        "artikelnummer": varianten[0]["artikelnummer"] if varianten else None,
        "modell": titel,
        "name": f"Gerber {titel}",
        "kategorie": kategorie,
        "unterkategorie": unterkategorie,
        "seite": seite,
        "klingenlaenge_mm": zoll_mm(specs.get("BLADE LENGTH")),
        "laenge_offen_mm": zoll_mm(specs.get("OVERALL LENGTH") or specs.get("OPEN LENGTH")),
        "laenge_geschlossen_mm": zoll_mm(specs.get("CLOSED LENGTH")),
        "gewicht_g": unzen_g(specs.get("WEIGHT")),
        "specs": specs,
        "beschreibung": " ".join(beschreibung.split()) or None,
        "varianten": varianten,
        "quelle": {"typ": "katalog_pdf", "datei": f"catalogues/{PDF.name}", "seite": seite, "verifiziert": False},
    }


def parse(pdf=PDF):
    produkte = []
    for seite, page in enumerate(pymupdf.open(pdf), start=1):
        alle = spans(page)
        fuss = sorted((s for s in alle if s["y"] > page.rect.height - 40 and abs(s["size"] - 7) < 0.3), key=lambda s: s["x"])
        kategorie = next((s["t"].title() for s in fuss if "Bd" in s["font"]), None)
        unterkategorie = next((s["t"].lstrip("| ").title() for s in fuss if "Light" in s["font"]), None)
        # Namen: fett 11 pt; Teile auf derselben Zeile ("MYTH" "®" "FOLDER") zusammenfassen
        roh = sorted((s for s in alle if s["size"] >= 10.5 and "Bold" in s["font"]), key=lambda s: (round(s["y"]), s["x"]))
        namen = []
        for s in roh:
            if namen and abs(s["y"] - namen[-1]["y"]) < 3 and 0 <= s["x"] - namen[-1]["x1"] < 25:
                namen[-1]["t"] += " " + s["t"]
                namen[-1]["x1"] = s["x1"]
            else:
                namen.append(dict(s))
        # SKU-Zeilen: 6 pt, enthalten eine Artikelnummer; einer Spalte zugeordnet über die x-Position
        zeilen = {}
        for s in (s for s in alle if abs(s["size"] - 6) < 0.3 and s["color"] != GRAU_ZITAT):
            zeilen.setdefault(round(s["y"]), []).append(s)
        sku_zeilen = [sorted(z, key=lambda s: s["x"]) for z in zeilen.values() if any(hat_sku(s) for s in z)]
        for name, x0, x1, y0, y1 in spalten(namen, page.rect.width):
            block = [s for s in alle if x0 <= s["x"] < x1 and y0 <= s["y"] < y1]
            eigene = []
            for z in sku_zeilen:
                teil = [s for s in z if x0 <= s["x"] < x1]
                if teil and any(hat_sku(s) for s in teil) and teil[0]["y"] > name["y"]:
                    eigene.append(teil)
            if not eigene and not any(s["t"].endswith(":") for s in block):
                continue  # Überschrift ohne Produkt
            produkte.append(produkt(name, block, eigene, kategorie, unterkategorie, seite))
    return produkte


def main():
    produkte = parse()
    pfad = schreibe(produkte, "gerber.json", quelle=f"catalogues/{PDF.name}", titel="Gerber Gear Full Line Product Catalog",
                    marke="Gerber", sprache="en")
    print(f"{len(produkte)} Produkte, {sum(len(p['varianten']) for p in produkte)} Artikel -> {pfad}", file=sys.stderr)


if __name__ == "__main__":
    main()
