"""Leatherman Katalog 2019 (catalogues/Leatherman-Katalog.pdf, Deutsch).

Werbebroschüre mit Doppelseiten (eine PDF-Seite = zwei Katalogseiten, je ein Produkt pro Hälfte).
Erkannt über Schrift und Position:

- Name: 30 pt fett ("MUT", "SURGE"), Anzahl Tools: weisse Zahl über "TOOLS"
- Gewicht und Masse in Mini-Schrift: "317.5 G", "7.6 CM", "12.7 CM" (geschlossen). Die Reihenfolge
  der beiden Masse ist im Layout nicht einheitlich: kleinerer Wert = Breite, grösserer = Länge.
- Werkzeuge: Aufzählungspunkte unter "WERKZEUGE" (zweispaltig, Umbrüche eingerückt ohne Punkt),
  Bits als Freitext unter "BITS"
- Einsatzbereiche (PRO, OUTDOOR, DIY, TRAVEL / EVERYDAY) als kleine Beschriftung der Symbole

Keine Artikelnummern im Katalog; die ID ist deshalb der Modellname (leatherman:<name>).
Hinweis: Katalog von 2019, Sortiment und Daten können veraltet sein.

Aufruf:  python -m scraper.kataloge.leatherman
Ausgabe: data/kataloge/leatherman_2019.json
"""

import re
import sys

import pymupdf

from scraper.kataloge.pdf import KATALOGE_PDF, schreibe, spans, zahl

PDF = KATALOGE_PDF / "Leatherman-Katalog.pdf"
BEREICHE = {"PRO", "OUTDOOR", "DIY", "TRAVEL / EVERYDAY", "TRAVEL", "EVERYDAY"}
# Abschnittsüberschriften (gleiche Schrift wie Produktnamen) -> Kategorie der folgenden Produkte
KATEGORIEN = {"LEATHERMAN FREE": "Free", "GROSSE TOOLS": "Grosse Tools", "MITTLERE TOOLS": "Mittlere Tools",
              "KOMPAKTE TOOLS": "Kompakte Tools", "SCHLÜSSELANHÄNGER": "Schlüsselanhänger", "MESSER": "Messer",
              "SCHEREN": "Scheren", "ACCESSOIRES": "Accessoires", "HOLSTER UND ZUBEHÖR": "Holster und Zubehör"}


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def liste(block, start_text, ende_texte):
    """Aufzählung unter einer Überschrift; Spalten von links nach rechts, Umbrüche angehängt."""
    koepfe = [s for s in block if s["t"] == start_text and "Bd" in s["font"]]
    if not koepfe:
        return []
    kopf = koepfe[0]
    enden = [s for s in block if s["t"] in ende_texte and "Bd" in s["font"]]
    eintraege = []
    zeilen = sorted((s for s in block if abs(s["size"] - 7) < 0.3 and s["y"] > kopf["y"] and s["x"] >= kopf["x"] - 3),
                    key=lambda s: (round(s["x"] / 50), s["y"]))
    for s in zeilen:
        # Spalte endet an der nächsten Überschrift (z. B. "BITS") in derselben Spalte
        if any(abs(e["x"] - s["x"]) < 40 and kopf["y"] < e["y"] <= s["y"] for e in enden):
            continue
        t = s["t"].lstrip("•").strip()
        if s["t"].startswith("•"):
            eintraege.append(t)
        elif eintraege and t:
            eintraege[-1] = (eintraege[-1][:-1] if eintraege[-1].endswith("-") else eintraege[-1] + " ") + t
    return [" ".join(e.split()) for e in eintraege]


def bits(block):
    kopf = next((s for s in block if s["t"] == "BITS" and "Bd" in s["font"]), None)
    if not kopf:
        return None
    zeilen = [s["t"] for s in sorted(block, key=lambda s: s["y"])
              if abs(s["size"] - 7) < 0.3 and abs(s["x"] - kopf["x"]) < 3 and kopf["y"] < s["y"] < kopf["y"] + 120
              and not s["t"].startswith("•")]
    return " ".join(" ".join(zeilen).split()) or None


def produkt(name_span, block, kategorie, seite):
    name = " ".join(name_span["t"].replace("®", "").split())
    tools = next((int(s["t"]) for s in block if s["color"] == 0xFFFFFF and s["size"] > 15 and s["t"].isdigit()), None)
    mini = [s["t"] for s in sorted(block, key=lambda s: s["y"]) if s["size"] < 5.5 and re.match(r"^[\d.,]+\s*(G|CM|MM)$", s["t"])]
    gewicht = next((zahl(t.split()[0]) for t in mini if t.endswith("G")), None)
    masse_mm = [zahl(t.split()[0]) * 10 for t in mini if t.endswith("CM") and zahl(t.split()[0])]
    bereiche = sorted({s["t"] for s in block if s["t"] in BEREICHE and s["size"] < 7})
    beschreibung = " ".join(s["t"] for s in sorted(block, key=lambda s: s["y"])
                            if abs(s["size"] - 7) < 0.3 and s["y"] < name_span["y"] + 160 and not s["t"].startswith("•")
                            and abs(s["x"] - name_span["x"]) < 8)
    return {
        "id": f"leatherman:{slug(name)}",
        "marke": "Leatherman",
        "artikelnummer": None,
        "modell": name,
        "name": f"Leatherman {name}",
        "kategorie": kategorie,
        "einsatzbereiche": bereiche,
        "seite": seite,
        "anzahl_funktionen": tools,
        "gewicht_g": gewicht,
        "breite_mm": zahl(round(min(masse_mm), 1)) if len(masse_mm) > 1 else None,
        "laenge_mm": zahl(round(max(masse_mm), 1)) if masse_mm else None,
        "werkzeuge": liste(block, "WERKZEUGE", {"BITS", "FARBE", "FARBEN"}),
        "bits": bits(block),
        "beschreibung": " ".join(beschreibung.split()) or None,
        "quelle": {"typ": "katalog_pdf", "datei": f"catalogues/{PDF.name}", "seite": seite, "verifiziert": False},
    }


def grosstexte(alle):
    """Grosse, fette Texte (Namen und Abschnitte); mehrzeilige zusammenfassen ("MUT" + "EOD", "ACCES-" + "SOIRES")."""
    # Nebeneinander ("FREE" "P2", leicht hochgestellt) oder untereinander ("TREAD" / "METRIC")
    gross = sorted((s for s in alle if s["size"] >= 25 and "Bd" in s["font"] and re.search(r"[A-Za-z]", s["t"])),
                   key=lambda s: (s["x"] > 432, round(s["y"] / 20), s["x"]))
    gruppen = []
    for s in gross:
        g = gruppen[-1] if gruppen else None
        gleiche_haelfte = g and (s["x"] > 432) == (g["x"] > 432)
        daneben = gleiche_haelfte and abs(s["y"] - g["y_ende"]) < 15 and 0 < s["x"] - g["x_ende"] < 40
        darunter = gleiche_haelfte and 15 <= s["y"] - g["y_ende"] < 45 and abs(s["x"] - g["x"]) < 60
        if daneben or darunter:
            g["t"] = (g["t"][:-1] if g["t"].endswith("-") else g["t"] + " ") + s["t"]
            g["y_ende"], g["x_ende"] = s["y"], s["x1"]
        else:
            gruppen.append({**s, "y_ende": s["y"], "x_ende": s["x1"]})
    return gruppen


def parse(pdf=PDF):
    produkte, kategorie = [], None
    for seite, page in enumerate(pymupdf.open(pdf), start=1):
        alle = spans(page)
        mitte = page.rect.width / 2
        for g in grosstexte(alle):
            text = " ".join(g["t"].replace("®", "").split()).upper()
            treffer = next((wert for k, wert in KATEGORIEN.items() if text == k or text.endswith(" " + k)), None)
            if treffer:
                kategorie = treffer
                continue
            block = [s for s in alle if (s["x"] >= mitte) == (g["x"] >= mitte)]
            # Nur echte Produktseiten: Tool-Anzahl oder Werkzeugliste in derselben Hälfte
            hat_tools = any(s["color"] == 0xFFFFFF and s["size"] > 15 and s["t"].isdigit() for s in block)
            if hat_tools or any(s["t"] == "WERKZEUGE" for s in block):
                p = produkt(g, block, kategorie, seite)
                if p["anzahl_funktionen"] or p["werkzeuge"]:   # Zubehörseiten haben beides nicht
                    produkte.append(p)
    return produkte


def main():
    produkte = parse()
    pfad = schreibe(produkte, "leatherman_2019.json", quelle=f"catalogues/{PDF.name}", titel="Leatherman Katalog 2019",
                    marke="Leatherman", sprache="de", hinweis="Katalog von 2019; keine Artikelnummern im Katalog")
    print(f"{len(produkte)} Produkte -> {pfad}", file=sys.stderr)


if __name__ == "__main__":
    main()
