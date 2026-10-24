"""Produktdaten, getrennt nach Herkunft.

data/victorinox_produkte.json       Victorinox-Sortiment der Webseite, vom Scraper erzeugt (nie von Hand bearbeiten)
data/kataloge/victorinox_2026.json  Victorinox-Katalog 2026 aus dem PDF, erzeugt (scraper/kataloge)
data/cross_references.json          von Hand gepflegt: Konkurrenzprodukte + Zuordnungen zwischen Produkten

Webseite und Katalog werden beim Laden zusammengeführt (load_products):
- Webseiten-Produkte mit Katalogeintrag (gleiche Artikel- oder Variantennummer): Werkzeuggruppen aus
  beiden Werkzeuglisten vereint (die Webseite kürzt Kombi-Werkzeuge, z. B. "Kapselheber" statt
  "Bottle opener | Screwdriver 5 mm | Wire stripper"), fehlende Funktionsanzahl/Länge aus dem Katalog.
- Katalog-Artikel ohne Webseiten-Produkt kommen als eigene Produkte dazu (Werkzeuge englisch,
  Foto aus dem Katalog als `bild_datei`), z. B. Classic SD 0.6223, Mini Champ Alox, Trailfinder.
`quellen` sagt pro Produkt, woher es kommt ("webseite", "katalog_2026").

Beide verwenden dasselbe Produktformat (`Produkt`). IDs sind global eindeutig:
`<marke>:<artikelnummer>`, z. B. `victorinox:1.3603`, `swiza:KNI.0036.1010`.
Werkzeuge stehen als Namen der jeweiligen Quelle ("Klinge, gross" auf der Webseite, "Blade, large"
im Katalog); app/werkzeuge.py versteht beide Sprachen.
Abgeleitetes wird nicht gespeichert, sondern beim Laden berechnet: `werkzeug_gruppen`
(über app/werkzeuge.py, für Matching und Bilderkennung). tools/tool_vocab.py bildet die
Namen zusätzlich auf englische IDs für die Klassifikation ab.

Die Ladefunktionen liefern Dictionaries mit den Feldern von `Produkt` plus `werkzeug_gruppen`
und `quellen`, damit matching.py, clef.py und training/ mit `row["…"]` arbeiten können.

Prüfen: `uv run python tools/check_catalog.py`
"""

import json
from datetime import date
from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.werkzeuge import gruppen

DATA = Path(__file__).resolve().parent.parent / "data"
VICTORINOX_JSON = DATA / "victorinox_produkte.json"
CROSS_REFERENCES_JSON = DATA / "cross_references.json"
KATALOG_2026_JSON = DATA / "kataloge" / "victorinox_2026.json"

ID_MUSTER = r"^[a-z0-9-]+:\S+$"


class Streng(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Quelle(Streng):
    typ: str                            # z. B. "herstellerseite", "foto", "katalog"
    url: str | None = None
    geprueft_am: date | None = None
    verifiziert: bool = False
    notiz: str | None = None


class Produkt(Streng):
    id: str = Field(pattern=ID_MUSTER)
    marke: str = Field(min_length=1)
    artikelnummer: str | None = None    # Artikelnummer des Herstellers
    name: str = Field(min_length=1)
    modell: str | None = None
    kategorien: list[str] = []          # Victorinox-Kategorien, z. B. "Everyday"
    unterkategorien: list[str] = []
    shop_kategorie: str | None = None
    preis_chf: int | float | None = None
    lagerstatus: str | None = None      # "inStock" | "outOfStock" | null
    varianten: list[str] = []           # Artikelnummern der Varianten
    farben: list[str] = []
    werkzeuge: list[str] = []           # deutsche Katalognamen
    # Technische Daten: nur verifizierte Werte, sonst null. Nie schätzen.
    anzahl_funktionen: int | float | None = Field(None, ge=0)
    laenge_mm: int | float | None = Field(None, ge=0)
    breite_mm: int | float | None = Field(None, ge=0)
    hoehe_mm: int | float | None = Field(None, ge=0)
    gewicht_g: int | float | None = Field(None, ge=0)
    material: str | None = None         # Schalenmaterial, z. B. "ABS/Cellidor"
    feststellbar: bool | None = None    # Klinge arretierbar
    einhandklinge: bool | None = None
    url: str | None = None
    bild_url: str | None = None
    bild_datei: str | None = None       # lokales Bild relativ zu data/ (Katalogfoto, wenn kein bild_url)
    galerie_bilder: list[str] = []
    quelle: Quelle | None = None        # Pflicht für alles, was nicht vom Scraper kommt

    @model_validator(mode="after")
    def id_passt_zur_marke(self):
        praefix = self.id.split(":", 1)[0]
        if praefix != self.marke.lower().replace(" ", "-"):
            raise ValueError(f"ID {self.id!r} muss mit '{self.marke.lower()}:' beginnen")
        return self


class VictorinoxDatei(Streng):
    quelle: str
    gescrapt_am: date
    anzahl: int
    produkte: list[Produkt]


class Beziehung(str, Enum):
    direktes_aequivalent = "direktes_aequivalent"      # praktisch dasselbe Produkt
    funktionale_alternative = "funktionale_alternative"  # erfüllt denselben Zweck
    nachfolger = "nachfolger"                          # ersetzt ein ausgelaufenes Produkt
    aehnlich = "aehnlich"                              # nur verwandt, schwächste Stufe


class Pruefstatus(str, Enum):
    verifiziert = "verifiziert"            # von Victorinox / Fachperson bestätigt
    vorgeschlagen = "vorgeschlagen"        # vom Team begründet vorgeschlagen
    modell_generiert = "modell_generiert"  # vom Agenten erzeugt, ungeprüft


class CrossReference(Streng):
    id: str
    von: str = Field(pattern=ID_MUSTER, description="Ausgangsprodukt, z. B. swiza:KNI.0036.1010")
    zu: str = Field(pattern=r"^victorinox:\S+$", description="Victorinox-Taschenmesser")
    beziehung: Beziehung
    status: Pruefstatus
    quelle: str = Field(min_length=1, description="Woher die Zuordnung stammt")
    geprueft_von: str | None = None     # Pflicht bei status=verifiziert (Rolle, nicht Name)
    notiz: str | None = None

    @model_validator(mode="after")
    def regeln(self):
        if self.von == self.zu:
            raise ValueError(f"{self.id}: verweist auf sich selbst")
        if self.status == Pruefstatus.verifiziert and not self.geprueft_von:
            raise ValueError(f"{self.id}: 'verifiziert' braucht 'geprueft_von'")
        return self


class CrossReferenceDatei(Streng):
    schema_version: str
    konkurrenzprodukte: list[Produkt]
    cross_references: list[CrossReference]

    @model_validator(mode="after")
    def konkurrenz_mit_quelle(self):
        for p in self.konkurrenzprodukte:
            if p.marke.lower() == "victorinox":
                raise ValueError(f"{p.id}: Victorinox-Produkte kommen vom Scraper, nicht aus cross_references.json")
            if p.quelle is None:
                raise ValueError(f"{p.id}: Konkurrenzprodukte brauchen eine 'quelle'")
        return self


@lru_cache
def victorinox_datei() -> VictorinoxDatei:
    return VictorinoxDatei.model_validate_json(VICTORINOX_JSON.read_text(encoding="utf-8"))


@lru_cache
def cross_reference_datei() -> CrossReferenceDatei:
    return CrossReferenceDatei.model_validate_json(CROSS_REFERENCES_JSON.read_text(encoding="utf-8"))


def als_row(p: Produkt, quellen=("webseite",)) -> dict:
    """Produkt als Dictionary plus abgeleitete Werkzeuggruppen (siehe Moduldoku)."""
    return {**p.model_dump(mode="json", exclude={"quelle"}), "werkzeug_gruppen": sorted(gruppen(p.werkzeuge)),
            "quellen": list(quellen)}


@lru_cache
def katalog_2026() -> tuple[dict, ...]:
    """Victorinox-Katalog 2026 (erzeugt von scraper/kataloge/victorinox_2026.py); leer, falls nicht vorhanden."""
    if not KATALOG_2026_JSON.exists():
        return ()
    return tuple(json.loads(KATALOG_2026_JSON.read_text(encoding="utf-8"))["produkte"])


def katalog_name(name):
    """Katalognamen sind in Grossbuchstaben: "MINI CHAMP ALOX" -> "Mini Champ Alox", "CLASSIC SD" bleibt "SD"."""
    return " ".join(w if len(w) <= 2 or any(c.isdigit() for c in w) else w.capitalize() for w in name.split())


def aus_katalog(k: dict) -> Produkt:
    unter = k.get("unterkategorie")
    return Produkt(
        id=k["id"], marke="Victorinox", artikelnummer=k["artikelnummer"], name=katalog_name(k["name"]),
        kategorien=[k["kategorie"]] if k.get("kategorie") else [],
        unterkategorien=[f"{k['kategorie']}: {unter}"] if unter else [], shop_kategorie=unter,
        varianten=[v["artikelnummer"] for v in k["varianten"]], werkzeuge=k["werkzeuge"],
        anzahl_funktionen=k.get("anzahl_funktionen"), laenge_mm=k.get("laenge_mm"), bild_datei=k.get("bild_datei"),
        quelle=Quelle(typ="katalog_pdf", verifiziert=True, notiz=f"Victorinox Catalogue 2026, S. {k['seite']}"),
    )


@lru_cache
def load_products() -> tuple[dict, ...]:
    """Das komplette Victorinox-Sortiment (inkl. Zubehör): Webseite, ergänzt um den Katalog 2026."""
    katalog = katalog_2026()
    nach_nummer = {}
    for k in katalog:  # exakte Artikelnummer vor Variantennummern
        for n in [k["artikelnummer"], *(v["artikelnummer"] for v in k["varianten"])]:
            nach_nummer.setdefault(n, k)
    for k in katalog:
        nach_nummer[k["artikelnummer"]] = k

    rows = []
    for p in victorinox_datei().produkte:
        k = next((nach_nummer[n] for n in [p.artikelnummer, *p.varianten] if n in nach_nummer), None)
        if not k:
            rows.append(als_row(p))
            continue
        row = als_row(p, ("webseite", "katalog_2026"))
        row["werkzeug_gruppen"] = sorted(set(row["werkzeug_gruppen"]) | gruppen(k["werkzeuge"]))
        for feld in ("anzahl_funktionen", "laenge_mm"):
            if row[feld] is None:
                row[feld] = k.get(feld)
        rows.append(row)
    web_nummern = {n for p in victorinox_datei().produkte for n in [p.artikelnummer, *p.varianten]}
    for k in katalog:
        if not any(n in web_nummern for n in [k["artikelnummer"], *(v["artikelnummer"] for v in k["varianten"])]):
            rows.append(als_row(aus_katalog(k), ("katalog_2026",)))
    return tuple(rows)


# Scope des Prototyps: nur Taschenmesser (siehe README). Das Sortiment enthält auch
# Zubehör, Nagelpflege, Swiss Cards und Swiss Tools (Zangen).
MESSER_KATEGORIEN = ("Everyday", "Outdoor & Sports", "Trades & Crafts")
KEINE_MESSER_SHOP = ("Personal Care", "Accessoires")
KEINE_MESSER_NAMEN = ("Swiss Card", "Smart Card", "Grillgabel", "Golf Tool", "Venture")


def is_pocket_knife(row: dict) -> bool:
    return (
        any(k in row["kategorien"] for k in MESSER_KATEGORIEN)
        and "Swiss Tools" not in row["kategorien"]
        and row["shop_kategorie"] not in KEINE_MESSER_SHOP
        and not any(name in row["name"] for name in KEINE_MESSER_NAMEN)
    )


@lru_cache
def load_pocket_knives() -> tuple[dict, ...]:
    return tuple(row for row in load_products() if is_pocket_knife(row))


@lru_cache
def load_konkurrenz() -> dict[str, dict]:
    return {p.id: als_row(p) for p in cross_reference_datei().konkurrenzprodukte}


def load_cross_references() -> list[CrossReference]:
    return cross_reference_datei().cross_references


def pruefe(ist_werkzeug=None) -> list[str]:
    """Fehler, die die Modelle allein nicht sehen: doppelte IDs, tote Verweise, unbekannte Werkzeuge.
    `ist_werkzeug(name) -> bool` prüft Werkzeugnamen (z. B. über tools/tool_vocab.canonical_tool)."""
    fehler = []
    victorinox = load_products()
    konkurrenz = cross_reference_datei().konkurrenzprodukte
    refs = load_cross_references()

    ids = [p["id"] for p in victorinox] + [p.id for p in konkurrenz]
    fehler += [f"Doppelte Produkt-ID: {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    ref_ids = [r.id for r in refs]
    fehler += [f"Doppelte Cross-Reference-ID: {i}" for i in sorted({i for i in ref_ids if ref_ids.count(i) > 1})]

    alle = set(ids)
    messer = {p["id"] for p in load_pocket_knives()}
    for r in refs:
        if r.von not in alle:
            fehler.append(f"{r.id}: unbekanntes Ausgangsprodukt {r.von}")
        if r.zu not in messer:
            fehler.append(f"{r.id}: Ziel {r.zu} ist kein Victorinox-Taschenmesser aus victorinox_produkte.json")

    if ist_werkzeug is not None:
        for p in konkurrenz:
            for w in p.werkzeuge:
                if not ist_werkzeug(w):
                    fehler.append(f"{p.id}: unbekanntes Werkzeug {w!r} (Katalognamen verwenden, siehe tools/tool_vocab.py)")
    return fehler
