import csv
import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    url: Value | None = None
    bild_url: Value | None = None

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


def to_product(row):
    """CSV-Zeile als bereinigtes Produkt für das Frontend (Listen statt Strings, Zahlen statt Text)."""
    try:
        preis = float(row["preis_chf"])
    except ValueError:
        preis = None
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
