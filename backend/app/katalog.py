"""Produktdaten: zwei Dateien, getrennt nach Herkunft.

data/victorinox_produkte.json  Victorinox-Sortiment, vom Scraper erzeugt (nie von Hand bearbeiten)
data/cross_references.json     von Hand gepflegt: Konkurrenzprodukte + Zuordnungen zwischen Produkten

Beide verwenden dasselbe Produktformat (`Produkt`). IDs sind global eindeutig:
`<marke>:<artikelnummer>`, z. B. `victorinox:1.3603`, `swiza:KNI.0036.1010`.
Werkzeuge stehen überall als deutsche Katalognamen ("Klinge, gross", "Korkenzieher").
Abgeleitetes wird nicht gespeichert, sondern beim Laden berechnet: `werkzeug_gruppen`
(über app/werkzeuge.py, für Matching und Bilderkennung). tools/tool_vocab.py bildet die
Namen zusätzlich auf englische IDs für die Klassifikation ab.

Die Ladefunktionen liefern Dictionaries mit den Feldern von `Produkt` plus
`werkzeug_gruppen`, damit matching.py, clef.py und training/ mit `row["…"]` arbeiten können.

Prüfen: `uv run python tools/check_catalog.py`
"""

from datetime import date
from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.werkzeuge import gruppen

DATA = Path(__file__).resolve().parent.parent / "data"
VICTORINOX_JSON = DATA / "victorinox_produkte.json"
CROSS_REFERENCES_JSON = DATA / "cross_references.json"

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


def als_row(p: Produkt) -> dict:
    """Produkt als Dictionary plus abgeleitete Werkzeuggruppen (siehe Moduldoku)."""
    return {**p.model_dump(mode="json", exclude={"quelle"}), "werkzeug_gruppen": sorted(gruppen(p.werkzeuge))}


@lru_cache
def load_products() -> tuple[dict, ...]:
    """Das komplette Victorinox-Sortiment (inkl. Zubehör)."""
    return tuple(als_row(p) for p in victorinox_datei().produkte)


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
