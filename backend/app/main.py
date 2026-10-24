import asyncio
import os
import uuid

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app import clef, jev, matching, vision
from app.katalog import load_cross_references, load_konkurrenz, load_pocket_knives, load_products
from app.werkzeuge import GRUPPEN

app = FastAPI(title="Victorinox Challenge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

Value = str | int | float | bool


class ProductFilter(BaseModel):
    """Filter auf die Produktfelder. Die JSON-Keys entsprechen den Spalten der früheren CSV."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    artikelnummer: Value | None = None
    name: Value | None = None
    kategorien: Value | None = None
    anzahl_kategorien: Value | None = None
    everyday: Value | None = Field(None, alias="Everyday")
    outdoor_sports: Value | None = Field(None, alias="Outdoor & Sports")
    trades_crafts: Value | None = Field(None, alias="Trades & Crafts")
    accessoires: Value | None = Field(None, alias="Accessoires")
    swiss_tools: Value | None = Field(None, alias="Swiss Tools")
    personalisieren: Value | None = Field(None, alias="Personalisieren")
    unterkategorien: Value | None = None
    shop_kategorie: Value | None = None
    preis_chf: Value | None = None
    lagerstatus: Value | None = None
    anzahl_varianten: Value | None = None
    varianten_artikelnummern: Value | None = None
    farben: Value | None = None
    anzahl_werkzeuge: Value | None = None
    werkzeuge: Value | None = None
    werkzeug_gruppen: Value | None = None
    anzahl_funktionen: Value | None = None
    laenge_mm: Value | None = None
    breite_mm: Value | None = None
    hoehe_mm: Value | None = None
    gewicht_g: Value | None = None
    material: Value | None = None
    feststellbar: Value | None = None
    einhandklinge: Value | None = None
    url: Value | None = None
    bild_url: Value | None = None
    galerie_bilder: Value | None = None

    @model_validator(mode="after")
    def not_empty(self):
        filters = self.filters()
        if not filters:
            raise ValueError("Mindestens ein Feld muss angegeben werden")
        empty = [col for col, value in filters.items() if isinstance(value, str) and not value.strip()]
        if empty:
            raise ValueError(f"Felder dürfen nicht leer sein: {', '.join(empty)}")
        return self

    def filters(self):
        """Gesetzte Felder als {Spaltenname: Wert}."""
        return self.model_dump(by_alias=True, exclude_none=True)


KATEGORIE_SPALTEN = ("Everyday", "Outdoor & Sports", "Trades & Crafts", "Accessoires", "Swiss Tools", "Personalisieren")


def column_value(row, col):
    """Wert eines Produkts in der Darstellung der früheren CSV-Spalte (für ProductFilter)."""
    if col in KATEGORIE_SPALTEN:
        return str(int(col in row["kategorien"]))
    derived = {
        "kategorien": "; ".join(row["kategorien"]),
        "anzahl_kategorien": len(row["kategorien"]),
        "unterkategorien": "; ".join(row["unterkategorien"]),
        "anzahl_varianten": len(row["varianten"]),
        "varianten_artikelnummern": ", ".join(row["varianten"]),
        "farben": ", ".join(row["farben"]),
        "anzahl_werkzeuge": len(row["werkzeuge"]),
        "werkzeuge": " / ".join(row["werkzeuge"]),
        "werkzeug_gruppen": ", ".join(row["werkzeug_gruppen"]),
        "galerie_bilder": " ".join(row["galerie_bilder"]),
        "feststellbar": {True: "Ja", False: "Nein"}.get(row["feststellbar"]),
        "einhandklinge": {True: "Ja", False: "Nein"}.get(row["einhandklinge"]),
    }
    value = derived[col] if col in derived else row.get(col)
    return "" if value is None else str(value)


def matches(cell, value):
    if isinstance(value, bool):
        value = int(value)
    if isinstance(value, (int, float)):
        try:
            return float(cell) == float(value)
        except ValueError:
            return False
    return cell.strip().casefold() == value.strip().casefold()


def to_product(row):
    """Produkt im Format der API (siehe docs/api.md)."""
    return {
        "id": row["id"],
        "marke": row["marke"],
        "artikelnummer": row["artikelnummer"],
        "name": row["name"],
        "kategorien": row["kategorien"],
        "unterkategorien": row["unterkategorien"],
        "shop_kategorie": row["shop_kategorie"],
        "preis_chf": row["preis_chf"],
        "lagerstatus": row["lagerstatus"],
        "varianten_artikelnummern": row["varianten"],
        "farben": row["farben"],
        "anzahl_werkzeuge": len(row["werkzeuge"]) or None,
        # " | " verbindet Teile eines Kombi-Werkzeugs
        "werkzeuge": row["werkzeuge"],
        "werkzeug_gruppen": row["werkzeug_gruppen"],
        "anzahl_funktionen": row["anzahl_funktionen"],
        "laenge_mm": row["laenge_mm"],
        "material": row["material"],
        "url": row["url"],
        "bild_url": row["bild_url"],
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/products/image")
def product_image(body: ProductFilter):
    """Liefert die bild_url aller Produkte, auf die alle angegebenen Felder zutreffen.

    Texte werden ohne Beachtung der Gross-/Kleinschreibung exakt verglichen,
    Zahlen und true/false numerisch (z. B. {"Everyday": true, "preis_chf": 39}).
    """
    filters = body.filters()
    found = [
        {"artikelnummer": p["artikelnummer"], "name": p["name"], "bild_url": p["bild_url"] or ""}
        for p in load_products()
        if all(matches(column_value(p, col), value) for col, value in filters.items())
    ]
    if not found:
        raise HTTPException(status_code=404, detail="Kein Produkt passt zu den angegebenen Feldern")
    return {"anzahl": len(found), "bild_url": found[0]["bild_url"], "treffer": found}


@app.get("/api/products")
def list_products(q: str = "", kategorie: str = "", limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    """Suche über die Taschenmesser. `q` sucht in Name, Artikelnummer (inkl. Varianten) und Farben,
    `kategorie` filtert auf eine der Messer-Kategorien (z. B. "Everyday")."""
    needle = q.strip().casefold()
    kategorie = kategorie.strip().casefold()
    found = []
    for row in load_pocket_knives():
        if kategorie and kategorie not in (k.casefold() for k in row["kategorien"]):
            continue
        haystack = " ".join((row["name"], row["artikelnummer"], *row["varianten"], *row["farben"]))
        if needle and needle not in haystack.casefold():
            continue
        found.append(to_product(row))
    return {"anzahl": len(found), "produkte": found[offset:offset + limit]}


@app.get("/api/products/{artikelnummer}")
def get_product(artikelnummer: str):
    """Ein Taschenmesser per Artikelnummer; Varianten-Artikelnummern werden auf ihr Produkt aufgelöst."""
    for row in load_pocket_knives():
        if row["artikelnummer"] == artikelnummer:
            return to_product(row)
    for row in load_pocket_knives():
        if artikelnummer in row["varianten"]:
            return to_product(row)
    raise HTTPException(status_code=404, detail=f"Kein Produkt mit Artikelnummer {artikelnummer}")


# --- Foto-Matching -----------------------------------------------------------

QUELLE_KATALOG = "Victorinox Produktdaten"
RUECKFRAGE_SCHWELLE = 0.5      # Jev: Wahrscheinlichkeit "nicht unterscheidbar"
RUECKFRAGE_ABSTAND = 0.05      # Fallback ohne Jev: Score-Abstand Platz 1 zu 2
MAX_BILD_BYTES = 8 * 1024 * 1024
VISUELL_SICHER = 0.3          # Clef-Bildsuche: Platz 1 gilt als das fotografierte Produkt ab dieser Wahrscheinlichkeit
KATEGORIE_MALUS = 0.5          # Score-Faktor für Kandidaten ausserhalb der gewählten Kategorie
VISUELL_ABSTAND = 2.5          # ... und wenn er mindestens so viel mal wahrscheinlicher ist als Platz 2
_matches = {}                  # match_id -> {"gruppen", "visuell"} (für das zweite Foto nach Rückfrage)


@app.on_event("startup")
async def kacheln_laden():
    """Katalogbilder für die Clef-Bildsuche im Hintergrund vorbereiten (einmalig, danach auf Platte)."""
    if clef.aktiv():
        asyncio.get_running_loop().run_in_executor(
            None, clef.kacheln_vorbereiten, [r for r in load_pocket_knives() if matching.produkt_gruppen(r)])


def produkt_merkmale(row):
    merkmale = []
    if row.get("werkzeuge"):
        merkmale.append({"key": "werkzeuge", "label": "Werkzeuge", "quelle": QUELLE_KATALOG,
                         "wert": sorted(GRUPPEN[g][0] for g in matching.produkt_gruppen(row))})
    if row.get("anzahl_funktionen"):
        merkmale.append({"key": "funktionen", "label": "Funktionen", "quelle": QUELLE_KATALOG,
                         "wert": row["anzahl_funktionen"]})
    if row.get("laenge_mm"):
        merkmale.append({"key": "laenge", "label": "Länge", "quelle": QUELLE_KATALOG,
                         "wert": f"{row['laenge_mm']} mm"})
    if row.get("material"):
        merkmale.append({"key": "schale", "label": "Schale", "quelle": QUELLE_KATALOG,
                         "wert": row["material"]})
    return merkmale


@app.post("/api/match")
async def match(bild: UploadFile = File(...), vorherige_match_id: str | None = Form(None),
                kategorie: str | None = Form(None)):
    """Foto -> erkannte Werkzeuge (Vision-Modell) -> Zuordnung/Rückfrage (Jev) -> Top-3 aus dem Katalog."""
    inhalt = await bild.read()
    if not inhalt or len(inhalt) > MAX_BILD_BYTES:
        raise HTTPException(status_code=400, detail="Bild fehlt oder ist grösser als 8 MB")

    schritte = []
    rows = load_pocket_knives()
    messer = [r for r in rows if matching.produkt_gruppen(r)]

    def kategorie_faktor(row):
        # Weicher Filter aus dem Dropdown: andere Kategorien zählen halb, fallen aber nicht weg
        return 1.0 if not kategorie or kategorie in row["kategorien"] else KATEGORIE_MALUS
    bild_url = vision.bild_als_url(inhalt, bild.content_type or "image/jpeg")
    # Bei Clef läuft die visuelle Katalogsuche parallel zur Werkzeug- und Markenerkennung
    mit_bildsuche = vision.anbieter() == "clef" and clef.aktiv()
    try:
        if mit_bildsuche:
            bild_url = await asyncio.to_thread(clef.bild_vorbereiten, bild_url)
        aufgaben = [asyncio.to_thread(vision.erkenne, bild_url)]
        if mit_bildsuche:
            aufgaben.append(asyncio.to_thread(clef.visuell_suchen, bild_url, messer))
        ergebnisse = await asyncio.gather(*aufgaben, return_exceptions=True)
    except Exception as fehler:  # Bild nicht lesbar
        raise HTTPException(status_code=400, detail=f"Bild nicht lesbar: {fehler}")
    erkannt = ergebnisse[0]
    if isinstance(erkannt, vision.VisionNichtKonfiguriert):
        raise HTTPException(status_code=503, detail=str(erkannt))
    if isinstance(erkannt, Exception):  # Anbieterfehler (Netz, Quote, Inhaltsfilter)
        raise HTTPException(status_code=502, detail=f"Bilderkennung fehlgeschlagen: {erkannt}")
    info = erkannt.pop("modell_info")
    erkannt.pop("_bild", None)
    schritte.append({"id": "vision", "label": "Bild analysiert", "status": "ok",
                     "detail": f"{len(erkannt['werkzeuge'])} Werkzeuge erkannt ({info['modell']}, {info['art']})"})

    werkzeuge = erkannt["werkzeuge"]
    try:
        zugeordnet = jev.werkzeuge_zuordnen(werkzeuge)
    except Exception as fehler:
        zugeordnet = None
        schritte.append({"id": "ocr", "label": "Werkzeuge zugeordnet", "status": "warnung",
                         "detail": f"Jev nicht erreichbar, Zuordnung der Bilderkennung verwendet ({fehler})"})
    if zugeordnet is not None:
        werkzeuge = zugeordnet
        schritte.append({"id": "ocr", "label": "Werkzeuge zugeordnet", "status": "ok",
                         "detail": f"Jev: {len(werkzeuge)} Werkzeuge mit Konfidenz bestätigt"})
    erkannte_gruppen = {w["gruppe"] for w in werkzeuge}
    visuell = {}
    if mit_bildsuche:
        if isinstance(ergebnisse[1], Exception):
            schritte.append({"id": "suche", "label": "Katalogbilder verglichen", "status": "warnung",
                             "detail": f"Bildsuche fehlgeschlagen, nur Werkzeug-Matching ({ergebnisse[1]})"})
        else:
            visuell = dict(ergebnisse[1])
    vorher = _matches.get(vorherige_match_id)
    if vorher:
        erkannte_gruppen |= vorher["gruppen"]
        if vorher["visuell"] and visuell:  # zwei Fotos: Mittelwert der Bildsuche
            visuell = {n: (visuell.get(n, 0) + vorher["visuell"].get(n, 0)) / 2 for n in visuell.keys() | vorher["visuell"].keys()}
        visuell = visuell or vorher["visuell"]

    marke = erkannt["marke"]
    ist_victorinox = bool(marke and "victorinox" in marke.casefold())
    schritte.append({"id": "marke", "label": "Marke bestimmt", "status": "ok" if marke else "warnung",
                     "detail": marke or "Marke nicht erkennbar"})

    if visuell:
        # Reihenfolge und Score aus der Bildsuche (auf Testfotos klar besser als die Werkzeuge),
        # die Werkzeuge liefern die Begründung
        nach_nummer = {r["artikelnummer"]: r for r in messer}
        kandidaten = []
        gewichtet = {n: p * kategorie_faktor(nach_nummer[n]) for n, p in visuell.items() if n in nach_nummer}
        for nummer, p in sorted(gewichtet.items(), key=lambda kv: -kv[1])[:3]:
            k = matching.bewerte(erkannte_gruppen, nach_nummer[nummer], erkannt) or {
                "row": nach_nummer[nummer], "gruppen": matching.produkt_gruppen(nach_nummer[nummer]),
                "gemeinsam": set(), "fehlend": set(), "zusaetzlich": set(), "gruende": []}
            k["score"] = round(p, 4)
            k["gruende"].insert(0, f"Bildähnlichkeit {p:.0%}")
            kandidaten.append(k)
        schritte.append({"id": "suche", "label": "Katalogbilder verglichen", "status": "ok",
                         "detail": f"Clef hat das Foto mit {len(messer)} Katalogbildern verglichen"})
        zweiter = kandidaten[1]["score"] if len(kandidaten) > 1 else 0.0
        eigenes = next((k for k in kandidaten[:1] if ist_victorinox and k["score"] >= VISUELL_SICHER
                        and k["score"] >= VISUELL_ABSTAND * zweiter), None)
    else:
        kandidaten = matching.rangliste(erkannte_gruppen, rows, erkannt, top=len(rows))
        for k in kandidaten:
            k["score"] = round(k["score"] * kategorie_faktor(k["row"]), 4)
        kandidaten = sorted(kandidaten, key=lambda k: -k["score"])[:3]
        schritte.append({"id": "suche", "label": "Katalog durchsucht",
                         "status": "ok" if kandidaten else "warnung",
                         "detail": f"{len(messer)} Messer über die Werkzeuge verglichen"})
        eigenes = next((k for k in kandidaten if k["score"] >= 0.95 and ist_victorinox), None)
    if eigenes:
        pfad = "aktuell"
    else:
        # Victorinox erkannt, aber nicht im aktuellen Katalog -> vermutlich ausgelaufen
        pfad = "nachfolger" if ist_victorinox else "ersatz"

    rueckfrage = None
    try:
        unklar = jev.rueckfrage_noetig(erkannt, kandidaten)
    except Exception:
        unklar = None
    if unklar is None and len(kandidaten) > 1:
        unklar = 1.0 if kandidaten[0]["score"] - kandidaten[1]["score"] < RUECKFRAGE_ABSTAND else 0.0
    if not erkannte_gruppen and not visuell:
        rueckfrage = {"frage": "Auf dem Foto sind keine Werkzeuge zu erkennen.",
                      "hinweis": "Bitte das Messer aufgeklappt fotografieren."}
    elif unklar is not None and unklar >= RUECKFRAGE_SCHWELLE:
        rueckfrage = {"frage": "Mehrere Messer passen ähnlich gut.",
                      "hinweis": "Ein Foto mit allen Werkzeugen ausgeklappt oder der Artikelnummer hilft."}
    schritte.append({"id": "empfehlung", "label": "Empfehlung erstellt",
                     "status": "warnung" if rueckfrage else "ok",
                     "detail": f"Top-Score {kandidaten[0]['score']:.2f}" if kandidaten else "Keine passenden Messer"})

    match_id = f"m_{uuid.uuid4().hex[:10]}"
    _matches[match_id] = {"gruppen": erkannte_gruppen, "visuell": visuell}

    return {
        "match_id": match_id,
        "pfad": pfad,
        "erkannt": {
            "marke": marke,
            "ist_victorinox": ist_victorinox,
            "modell": erkannt["modell"],
            "artikelnummer": erkannt["artikelnummer_sichtbar"],
            "kategorie": "Taschenmesser (SAK)" if erkannt["ist_taschenmesser"] else None,
            "konfidenz": erkannt["konfidenz"],
            "produkt": to_product(eigenes["row"]) if eigenes else None,
            "merkmale": [{"key": "werkzeuge", "label": "Werkzeuge", "quelle": "Bilderkennung",
                          "wert": sorted(GRUPPEN[g][0] for g in erkannte_gruppen)}] if erkannte_gruppen else [],
        },
        "empfehlungen": [
            {
                "produkt": to_product(k["row"]),
                "score": k["score"],
                "begruendung": matching.begruendung(k),
                "gruende": k["gruende"],
                "merkmale": produkt_merkmale(k["row"]),
            }
            for k in kandidaten
        ],
        "rueckfrage": rueckfrage,
        "schritte": schritte,
    }


@app.get("/api/alternativen/{produkt_id}")
def alternatives(produkt_id: str):
    """Explizite Zuordnungen aus cross_references.json für ein Produkt,
    z. B. /api/alternativen/swiza:KNI.0036.1010 oder /api/alternativen/victorinox:4.3803.1.
    Verifizierte Zuordnungen zuerst; das Ziel ist immer ein Victorinox-Taschenmesser."""
    knives = {row["id"]: row for row in load_pocket_knives()}
    if produkt_id not in knives and produkt_id not in load_konkurrenz():
        raise HTTPException(status_code=404, detail=f"Unbekanntes Produkt {produkt_id}")
    rang = {"verifiziert": 0, "vorgeschlagen": 1, "modell_generiert": 2}
    treffer = sorted(
        (r for r in load_cross_references() if r.von == produkt_id and r.zu in knives),
        key=lambda r: rang[r.status.value],
    )
    return {
        "von": produkt_id,
        "alternativen": [
            {
                "beziehung": r.beziehung.value,
                "status": r.status.value,
                "quelle": r.quelle,
                "notiz": r.notiz,
                "produkt": to_product(knives[r.zu]),
            }
            for r in treffer
        ],
    }
