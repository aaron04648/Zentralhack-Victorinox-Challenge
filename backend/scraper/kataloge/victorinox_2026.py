"""Victorinox Swiss Army Knife & Tools 2026 (catalogues/Victorinox_Catalogue_2026.pdf, Englisch).

Jede Produktbox im Katalog hat dasselbe Layout, das hier über Schrift, Farbe und
relative Position erkannt wird (die Ränder von geraden und ungeraden Seiten unterscheiden sich):

- Artikelnummer: rot, fett 12 pt; daneben der Name (schwarz, fett 12 pt)
- links darunter "16 Functions" und "91 mm"
- Werkzeuge: "01." … mit Text; "– Screwdriver 3 mm" gehört zum Werkzeug davor (Kombi-Werkzeug,
  gespeichert als "Bottle opener | Screwdriver 6 mm" wie in den Webseiten-Daten). Zeilen ohne
  Nummer direkt darunter sind Umbrüche, mit Abstand darunter Hinweise ("With neck cord").
- Varianten: Artikelnummer fett 9 pt, davor graue Verpackungseinheit, evtl. graue Beschreibung darüber
- "We recommend case 6 7 8": Nummern der Etuis im Zubehör-Teil (dort grau 13 pt als etui_nummer)

Prüfung beim Import: Bei jedem Messer muss die Zahl der nummerierten Zeilen der Angabe
"N Functions" entsprechen.

Aufruf:  python -m scraper.kataloge.victorinox_2026
Ausgabe: data/kataloge/victorinox_2026.json
"""

import re
import sys

import pymupdf

from scraper.kataloge.pdf import KATALOGE_PDF, schreibe, spans, zahl

PDF = KATALOGE_PDF / "Victorinox_Catalogue_2026.pdf"
ROT, GRAU, WEISS = 0xB00930, 0x646363, 0xFFFFFF
ARTNR = re.compile(r"^[0-9A-Z]\.\d{4}(\.[0-9A-Z]+)*(\.\d+)?$")
NUMMER = re.compile(r"^(\d{2})\.$")


def ist(s, size, color=0, bold=None):
    if abs(s["size"] - size) > 0.2 or s["color"] != color:
        return False
    return bold is None or (("Bd" in s["font"]) == bold)


def werkzeuge_aus(zeilen):
    """Nummerierte Zeilen -> Werkzeugliste; "– X" hängt an der Zeile davor (Kombi-Werkzeug)."""
    liste = []
    for t in zeilen:
        if t.startswith("–") and liste:
            liste[-1] = re.sub(r"\s+with$", "", liste[-1]) + " | " + t.lstrip("– ").strip()
        else:
            liste.append(t)
    return [re.sub(r"\s+with$", "", w) for w in liste]


def produkt(kopf, block, kategorie, unterkategorie, seite):
    name = next((s["t"] for s in block if ist(s, 12, 0, True) and abs(s["y"] - kopf["y"]) < 3 and s["x"] > kopf["x"]), None)
    links = [s["t"] for s in block if abs(s["x"] - kopf["x"]) < 4 and s is not kopf and ist(s, 9)]
    funktionen = next((int(m.group(1)) for t in links if (m := re.match(r"(\d+)\s*Functions?", t))), None)
    laenge = next((zahl(m.group(1)) for t in links if (m := re.match(r"([\d.]+)\s*mm$", t))), None)

    # Werkzeuge: Nummer + Text auf derselben Zeile, Spalten von links nach rechts
    zeilen = []
    for n in sorted((s for s in block if NUMMER.match(s["t"]) and ist(s, 9)), key=lambda s: (s["x"] > 250, s["y"])):
        rechts = sorted((s for s in block if ist(s, 9) and abs(s["y"] - n["y"]) < 1.5 and 0 < s["x"] - n["x"] < 40), key=lambda s: s["x"])
        zeilen.append({"nr": int(NUMMER.match(n["t"]).group(1)), "text": " ".join(s["t"] for s in rechts),
                       "x": n["x"], "y": n["y"], "text_x": rechts[0]["x"] if rechts else n["x"] + 15})
    belegt = {id(s) for z in zeilen for s in block if abs(s["y"] - z["y"]) < 1.5 and z["x"] - 1 <= s["x"] < z["text_x"] + 120}
    for z in zeilen:  # Umbrüche: gleiche Einrückung, eine Zeile tiefer, ohne Nummer
        for s in sorted(block, key=lambda s: s["y"]):
            if (id(s) not in belegt and ist(s, 9) and abs(s["x"] - z["text_x"]) < 2 and 8 < s["y"] - z["y"] < 13
                    and not NUMMER.match(s["t"])
                    and not any(abs(o["y"] - s["y"]) < 1.5 and abs(o["x"] - z["x"]) < 5 for o in zeilen)):
                z["text"] += " " + s["t"]
                belegt.add(id(s))
    zeilen.sort(key=lambda z: z["nr"])
    if funktionen and len(zeilen) != funktionen:
        print(f"  WARNUNG S.{seite} {kopf['t']}: {funktionen} Functions, aber {len(zeilen)} Werkzeugzeilen", file=sys.stderr)

    varianten = []
    for v in sorted((s for s in block if ist(s, 9, 0, True) and ARTNR.match(s["t"]) and s["y"] > kopf["y"] + 5), key=lambda s: (s["y"], s["x"])):
        menge = next((int(s["t"]) for s in block if ist(s, 10, GRAU) and s["t"].isdigit() and abs(s["y"] - v["y"]) < 2 and 0 < v["x"] - s["x"] < 30), None)
        beschreibung = next((s["t"] for s in block if ist(s, 9, GRAU) and 0 < v["y"] - s["y"] < 15 and abs(s["x"] - v["x"]) < 3), None)
        varianten.append({"artikelnummer": v["t"], "verpackungseinheit": menge,
                          "verpackung": "blister" if re.search(r"B\d?$", v["t"]) else "standard",
                          **({"beschreibung": beschreibung} if beschreibung else {})})

    # Hinweise: unnummerierte Zeilen in der Werkzeugspalte mit Abstand unter der Liste, Aufzählungen im Zubehör
    hinweise = [s["t"].lstrip("•").strip() for s in block if ist(s, 9) and s["t"].startswith("•")]
    if zeilen:
        x, ende = min(z["x"] for z in zeilen), max(z["y"] for z in zeilen)
        hinweise += [s["t"] for s in sorted(block, key=lambda s: s["y"])
                     if id(s) not in belegt and ist(s, 9) and abs(s["x"] - x) <= 3 and s["y"] > ende + 13
                     and not s["t"].startswith("We recommend") and not ARTNR.match(s["t"])]

    etui_zeile = next((s for s in block if s["t"].startswith("We recommend case")), None)
    etuis = [int(s["t"]) for s in block if etui_zeile and ist(s, 6.4, WEISS) and s["t"].isdigit() and abs(s["y"] - etui_zeile["y"]) < 3]
    etui_nummer = next((int(s["t"]) for s in block if ist(s, 13, GRAU) and s["t"].isdigit() and abs(s["x"] - kopf["x"]) < 10), None)

    return {
        "id": f"victorinox:{kopf['t']}",
        "marke": "Victorinox",
        "artikelnummer": kopf["t"],
        "name": name,
        "kategorie": kategorie,
        "unterkategorie": unterkategorie,
        "seite": seite,
        "anzahl_funktionen": funktionen,
        "laenge_mm": laenge,
        "werkzeuge": werkzeuge_aus([z["text"] for z in zeilen]),
        "hinweise": hinweise,
        "varianten": varianten,
        "etui_empfehlung": etuis,
        **({"etui_nummer": etui_nummer} if etui_nummer is not None else {}),
    }


def parse(pdf=PDF):
    produkte, kategorie, unterkategorie = [], None, None
    for seite, page in enumerate(pymupdf.open(pdf), start=1):
        alle = spans(page)
        for s in alle:
            # Seitenkopf "EVERYDAY  Essentials" (gerade Seiten) bzw. Reiter am Rand (ungerade Seiten)
            if s["y"] < 60 and ist(s, 15, ROT):
                kategorie = s["t"].title()
                unterkategorie = next((o["t"] for o in alle if o["y"] < 60 and ist(o, 12) and abs(o["y"] - s["y"]) < 6), None)
            elif s["x"] > 540 and ist(s, 11, WEISS) and s["t"].title() != kategorie:
                kategorie, unterkategorie = s["t"].title(), None
        koepfe = sorted((s for s in alle if ist(s, 12, ROT, True) and ARTNR.match(s["t"])), key=lambda s: s["y"])
        # Zubehörseiten sind zweispaltig: Blöcke dann pro Spalte (Grenze bei x = 280)
        zweispaltig = any(k["x"] > 280 for k in koepfe)
        spalte = (lambda x: x > 280) if zweispaltig else (lambda x: False)
        for kopf in koepfe:
            folgende = [k["y"] for k in koepfe if k["y"] > kopf["y"] + 3 and spalte(k["x"]) == spalte(kopf["x"])]
            y1 = min(folgende) - 2 if folgende else 800
            block = [s for s in alle if kopf["y"] - 2 <= s["y"] < y1 and spalte(s["x"]) == spalte(kopf["x"])]
            produkte.append(produkt(kopf, block, kategorie, unterkategorie, seite))
    return produkte


def main():
    produkte = parse()
    pfad = schreibe(produkte, "victorinox_2026.json",
                    quelle=f"catalogues/{PDF.name}", titel="Victorinox Swiss Army Knife & Tools 2026",
                    marke="Victorinox", sprache="en")
    messer = sum(1 for p in produkte if p["anzahl_funktionen"])
    print(f"{len(produkte)} Artikel ({messer} mit Funktionsangabe) -> {pfad}", file=sys.stderr)


if __name__ == "__main__":
    main()
