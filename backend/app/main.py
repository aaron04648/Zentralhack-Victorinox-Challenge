import asyncio
import csv
import os
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app import clef, jev, matching, vision
from app.werkzeuge import GRUPPEN

PRODUCTS_CSV = Path(__file__).resolve().parent.parent / "data" / "victorinox_sak_produkte.csv"

app = FastAPI(title="Victorinox Challenge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

Value = str | int | float | bool


class ProductFilter(BaseModel):
    """Filter auf die CSV-Spalten. Die JSON-Keys entsprechen exakt den CSV-Spaltennamen."""

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
        """Gesetzte Felder als {CSV-Spaltenname: Wert}."""
        return self.model_dump(by_alias=True, exclude_none=True)


def matches(cell, value):
    if isinstance(value, bool):
        value = int(value)
    if isinstance(value, (int, float)):
        try:
            return float(cell) == float(value)
        except ValueError:
            return False
    return cell.strip().casefold() == value.strip().casefold()


@lru_cache
def load_products():
    with PRODUCTS_CSV.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def split_list(cell, sep=","):
    return [part.strip() for part in cell.split(sep) if part.strip()]


def to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_product(row):
    """CSV-Zeile als bereinigtes Produkt für das Frontend (Listen statt Strings, Zahlen statt Text)."""
    preis = to_number(row["preis_chf"])
    return {
        "artikelnummer": row["artikelnummer"],
        "name": row["name"],
        "kategorien": split_list(row["kategorien"], ";"),
        "unterkategorien": split_list(row["unterkategorien"], ";"),
        "shop_kategorie": row["shop_kategorie"].replace("\xa0", " "),
        "preis_chf": preis,
        "lagerstatus": row["lagerstatus"] or None,
        "varianten_artikelnummern": split_list(row["varianten_artikelnummern"]),
        "farben": split_list(row["farben"]),
        "werkzeuge": split_list(row.get("werkzeuge", ""), " / "),
        "werkzeug_gruppen": split_list(row.get("werkzeug_gruppen", "")),
        "anzahl_funktionen": to_number(row.get("anzahl_funktionen")),
        "laenge_mm": to_number(row.get("laenge_mm")),
        "material": row.get("material") or None,
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
        {"artikelnummer": p["artikelnummer"], "name": p["name"], "bild_url": p["bild_url"]}
        for p in load_products()
        if all(matches(p[col], value) for col, value in filters.items())
    ]
    if not found:
        raise HTTPException(status_code=404, detail="Kein Produkt passt zu den angegebenen Feldern")
    return {"anzahl": len(found), "bild_url": found[0]["bild_url"], "treffer": found}


@app.get("/api/products")
def list_products(q: str = "", kategorie: str = "", limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    """Katalog-Suche. `q` sucht in Name, Artikelnummer (inkl. Varianten) und Farben,
    `kategorie` filtert auf eine der Hauptkategorien (z. B. "Everyday")."""
    needle = q.strip().casefold()
    kategorie = kategorie.strip().casefold()
    found = []
    for row in load_products():
        if kategorie and kategorie not in (k.casefold() for k in split_list(row["kategorien"], ";")):
            continue
        haystack = " ".join((row["name"], row["artikelnummer"], row["varianten_artikelnummern"], row["farben"]))
        if needle and needle not in haystack.casefold():
            continue
        found.append(to_product(row))
    return {"anzahl": len(found), "produkte": found[offset:offset + limit]}


@app.get("/api/products/{artikelnummer}")
def get_product(artikelnummer: str):
    """Ein Produkt per Artikelnummer; Varianten-Artikelnummern werden auf ihr Produkt aufgelöst."""
    for row in load_products():
        if row["artikelnummer"] == artikelnummer:
            return to_product(row)
    for row in load_products():
        if artikelnummer in split_list(row["varianten_artikelnummern"]):
            return to_product(row)
    raise HTTPException(status_code=404, detail=f"Kein Produkt mit Artikelnummer {artikelnummer}")


# --- Foto-Matching -----------------------------------------------------------

QUELLE_KATALOG = "Victorinox Produktdaten"
RUECKFRAGE_SCHWELLE = 0.5      # Jev: Wahrscheinlichkeit "nicht unterscheidbar"
RUECKFRAGE_ABSTAND = 0.05      # Fallback ohne Jev: Score-Abstand Platz 1 zu 2
MAX_BILD_BYTES = 8 * 1024 * 1024
VISUELL_SICHER = 0.3          # Clef-Bildsuche: Platz 1 gilt als das fotografierte Produkt ab dieser Wahrscheinlichkeit
VISUELL_ABSTAND = 2.5          # ... und wenn er mindestens so viel mal wahrscheinlicher ist als Platz 2
_matches = {}                  # match_id -> {"gruppen", "visuell"} (für das zweite Foto nach Rückfrage)


@app.on_event("startup")
async def kacheln_laden():
    """Katalogbilder für die Clef-Bildsuche im Hintergrund vorbereiten (einmalig, danach auf Platte)."""
    if clef.aktiv():
        asyncio.get_running_loop().run_in_executor(
            None, clef.kacheln_vorbereiten, [r for r in load_products() if matching.produkt_gruppen(r)])


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
async def match(bild: UploadFile = File(...), vorherige_match_id: str | None = Form(None)):
    """Foto -> erkannte Werkzeuge (Vision-Modell) -> Zuordnung/Rückfrage (Jev) -> Top-3 aus dem Katalog."""
    inhalt = await bild.read()
    if not inhalt or len(inhalt) > MAX_BILD_BYTES:
        raise HTTPException(status_code=400, detail="Bild fehlt oder ist grösser als 8 MB")

    schritte = []
    rows = load_products()
    messer = [r for r in rows if matching.produkt_gruppen(r)]
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
        for nummer, p in sorted(visuell.items(), key=lambda kv: -kv[1])[:3]:
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
        kandidaten = matching.rangliste(erkannte_gruppen, rows, erkannt, top=3)
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
