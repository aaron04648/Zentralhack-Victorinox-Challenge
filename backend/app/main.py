import asyncio
import copy
import csv
import hashlib
import json
import math
import os
import threading
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from typing import Dict
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app import clef, jev, konkurrenz, matching, tunnel, vision
from app.werkzeuge import GRUPPEN

# Das Embedding-Modul ist optional: es liefert nur die experimentelle
# /score_categories-Route. Wenn es nicht verfuegbar ist (fehlende Abhaengigkeiten,
# laufende Umbauten), startet der Kern der Demo trotzdem.
try:
    from app import embeddings
    from app.embeddings import (CATEGORIES, cosine_similarity,
                                generate_category_embeddings, setup_embedding_model)
    EMBEDDINGS_AKTIV = True
except Exception:  # pragma: no cover - abhaengig von der lokalen Umgebung
    embeddings = None
    CATEGORIES: list[str] = []
    EMBEDDINGS_AKTIV = False

    def generate_category_embeddings():
        return []

    def setup_embedding_model():
        raise RuntimeError("Embedding-Modul nicht verfuegbar")

    def cosine_similarity(a, b):
        return 0.0

PRODUCTS_CSV = Path(__file__).resolve().parent.parent / "data" / "victorinox_sak_produkte.csv"

app = FastAPI(title="Victorinox Challenge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

Value = str | int | float | bool

class CategoryScores(BaseModel):
    query: str
    scores: Dict[str, float]


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


# Scope des Prototyps: nur Taschenmesser (siehe README). Die CSV enthält das ganze
# SAK-Sortiment inkl. Zubehör, Nagelpflege, Swiss Cards und Swiss Tools (Zangen).
MESSER_KATEGORIEN = ("Everyday", "Outdoor & Sports", "Trades & Crafts")
KEINE_MESSER_SHOP = ("Personal Care", "Accessoires")
KEINE_MESSER_NAMEN = ("Swiss Card", "Smart Card", "Grillgabel", "Golf Tool", "Venture")


def is_pocket_knife(row):
    kategorien = split_list(row["kategorien"], ";")
    return (
        any(k in kategorien for k in MESSER_KATEGORIEN)
        and "Swiss Tools" not in kategorien
        and row["shop_kategorie"].replace("\xa0", " ") not in KEINE_MESSER_SHOP
        and not any(name in row["name"] for name in KEINE_MESSER_NAMEN)
    )


@lru_cache
def load_pocket_knives():
    return [row for row in load_products() if is_pocket_knife(row)]


@lru_cache
def load_empfehlbare():
    """Taschenmesser plus Swiss Tools: die Swiss Tools nur als Ersatz für fremde Zangen-Multitools."""
    return load_pocket_knives() + [r for r in load_products() if "Swiss Tools" in split_list(r["kategorien"], ";")]


def ja_nein(wert):
    return {"Ja": True, "Nein": False}.get((wert or "").strip())


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
        "anzahl_werkzeuge": int(row["anzahl_werkzeuge"]) if row["anzahl_werkzeuge"].isdigit() else None,
        # " / " trennt Werkzeuge; " | " verbindet Teile eines Kombi-Werkzeugs und bleibt drin
        "werkzeuge": split_list(row["werkzeuge"], " / "),
        "werkzeug_gruppen": split_list(row.get("werkzeug_gruppen", "")),
        "anzahl_funktionen": to_number(row.get("anzahl_funktionen")),
        "laenge_mm": to_number(row.get("laenge_mm")),
        "breite_mm": to_number(row.get("breite_mm")),
        "hoehe_mm": to_number(row.get("hoehe_mm")),
        "gewicht_g": to_number(row.get("gewicht_g")),
        "material": row.get("material") if row.get("material") not in ("", "Undefiniert", None) else None,
        "feststellbar": ja_nein(row.get("feststellbar")),
        "einhandklinge": ja_nein(row.get("einhandklinge")),
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
    """Suche über die Taschenmesser. `q` sucht in Name, Artikelnummer (inkl. Varianten) und Farben,
    `kategorie` filtert auf eine der Messer-Kategorien (z. B. "Everyday")."""
    needle = q.strip().casefold()
    kategorie = kategorie.strip().casefold()
    found = []
    for row in load_pocket_knives():
        if kategorie and kategorie not in (k.casefold() for k in split_list(row["kategorien"], ";")):
            continue
        haystack = " ".join((row["name"], row["artikelnummer"], row["varianten_artikelnummern"], row["farben"]))
        if needle and needle not in haystack.casefold():
            continue
        found.append(to_product(row))
    return {"anzahl": len(found), "produkte": found[offset:offset + limit]}


@app.get("/api/products/{artikelnummer}")
def get_product(artikelnummer: str):
    """Ein Taschenmesser (oder Swiss Tool, Ersatz für fremde Zangen-Multitools) per Artikelnummer;
    Varianten-Artikelnummern werden auf ihr Produkt aufgelöst."""
    for row in load_empfehlbare():
        if row["artikelnummer"] == artikelnummer:
            return to_product(row)
    for row in load_empfehlbare():
        if artikelnummer in split_list(row["varianten_artikelnummern"]):
            return to_product(row)
    raise HTTPException(status_code=404, detail=f"Kein Produkt mit Artikelnummer {artikelnummer}")


# --- Foto-Matching -----------------------------------------------------------

QUELLE_KATALOG = "Victorinox Produktdaten"
RUECKFRAGE_SCHWELLE = 0.5      # Jev: Wahrscheinlichkeit "nicht unterscheidbar"
RUECKFRAGE_ABSTAND = 0.05      # Fallback ohne Jev: Score-Abstand Platz 1 zu 2
MAX_BILD_BYTES = 8 * 1024 * 1024
MARKE_SICHER = 0.6            # ab dieser Markenwahrscheinlichkeit wird bei Fremdmarken nur im Markenkatalog gesucht
VISUELL_SICHER = 0.3          # Clef-Bildsuche: Platz 1 gilt als das fotografierte Produkt ab dieser Wahrscheinlichkeit
KATEGORIE_MALUS = 0.5          # Score-Faktor für Kandidaten ausserhalb der gewählten Kategorie
VISUELL_ABSTAND = 2.5
ZANGE_SICHER = 0.5             # fremdes Multitool mit Zange -> Swiss Tools kommen als Ersatz in Frage
MIN_NACH_ZWECK = 10            # so viele Produkte bleiben mindestens nach dem Zweck-Filter
GEWICHT_BILD_TIEBREAK = 0.05   # fremde Marke: Bildähnlichkeit entscheidet nur bei gleicher Ausstattung
VERWENDUNG_GEWICHT = 0.5       # Stärke des Verwendungszwecks: Faktor exp(0.5 * z) auf Clefs Wahrscheinlichkeit          # ... und wenn er mindestens so viel mal wahrscheinlicher ist als Platz 2
_matches = {}                  # match_id -> Erkennungskontext (zweites Foto, Werkzeug-Korrektur ohne neue Clef-Anfrage)
_vorab = OrderedDict()         # sha1(Foto) -> Task mit Erkennung + Orten aus dem Röntgenblick der Vorschau
MAX_VORAB = 50


@app.on_event("startup")
async def kacheln_laden():
    """Katalogbilder für die Clef-Bildsuche im Hintergrund vorbereiten (einmalig, danach auf Platte)."""
    loop = asyncio.get_running_loop()
    messer = [r for r in load_pocket_knives() if matching.produkt_gruppen(r)]
    if clef.aktiv():
        loop.run_in_executor(None, clef.kacheln_vorbereiten, messer)
        loop.run_in_executor(None, clef.kacheln_vorbereiten, konkurrenz.bild_rows(konkurrenz.produkte()))


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
                kategorie: str | None = Form(None), verwendung: str | None = Form(None)):
    """Foto -> erkannte Werkzeuge (Vision-Modell) -> Zuordnung/Rückfrage (Jev) -> Top-3 aus dem Katalog."""
    inhalt = await bild.read()
    async for ereignis in _match_ablauf(inhalt, bild.content_type, vorherige_match_id, kategorie, verwendung):
        if ereignis["typ"] == "fehler":
            raise HTTPException(status_code=ereignis["status"], detail=ereignis["detail"])
        if ereignis["typ"] == "ergebnis":
            return ereignis["ergebnis"]


@app.post("/api/match/stream")
async def match_stream(bild: UploadFile = File(...), vorherige_match_id: str | None = Form(None),
                       kategorie: str | None = Form(None), verwendung: str | None = Form(None)):
    """Wie /api/match, aber als Live-Ablauf: eine JSON-Zeile pro Ereignis (application/x-ndjson).

    {"typ": "schritt", "schritt": {...}}     Schritt startet ("laeuft") oder ist fertig ("ok"/"warnung")
    {"typ": "werkzeuge", "werkzeuge": [...]} erkannte Werkzeuge mit Position auf dem Foto (Röntgenblick)
    {"typ": "ergebnis", "ergebnis": {...}}   wie die Antwort von /api/match, danach Ende
    {"typ": "fehler", "status": 503, "detail": "..."}
    """
    inhalt = await bild.read()

    async def zeilen():
        async for ereignis in _match_ablauf(inhalt, bild.content_type, vorherige_match_id, kategorie, verwendung):
            yield json.dumps(ereignis, ensure_ascii=False) + "\n"

    return StreamingResponse(zeilen(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/kamera/messer")
async def kamera_messer(bild: UploadFile = File(...)):
    """Auto-Auslöser: Ist auf diesem (kleinen) Kamerabild ein Messer zu sehen? -> {"messer": p} (ca. 1 s)."""
    inhalt = await bild.read()
    if not inhalt or len(inhalt) > MAX_BILD_BYTES:
        raise HTTPException(status_code=400, detail="Bild fehlt oder ist grösser als 8 MB")
    if not clef.aktiv():
        raise HTTPException(status_code=503, detail="Messer-Prüfung braucht Clef")
    try:
        p = await asyncio.to_thread(clef.messer_sichtbar, vision.bild_als_url(inhalt, bild.content_type or "image/jpeg"))
    except Exception as fehler:
        raise HTTPException(status_code=502, detail=f"Messer-Prüfung fehlgeschlagen: {fehler}")
    return {"messer": round(p, 3)}


# --- Handy als Kamera: QR-Code am Computer, Foto vom Handy kommt zurück -------------------------
# Zwei Wege fürs Handy:
# - Tunnel (Standard am Computer unter localhost): cloudflared öffnet https://<zufall>.trycloudflare.com
#   nur für diese Kopplung; das Handy bekommt die schlanke Seite /h/{id}. Der Tunnel schliesst, sobald
#   das Foto da ist, der Dialog am Computer zu ist oder der Computer nicht mehr nachfragt.
# - Direkt: HANDY_BASIS_URL (WLAN-Adresse) bzw. die öffentliche Adresse der App -> React-Seite /handy/{id}.
HANDY_TTL_S = 30 * 60
HANDY_MAX = 200
TUNNEL_LEERLAUF_S = 60          # fragt der Computer so lange nicht nach, wird der Tunnel geschlossen
TUNNEL_SCHLIESSEN_NACH_FOTO_S = 3  # kurz warten, damit die Antwort ans Handy noch durch den Tunnel geht
HANDY_SEITE = Path(__file__).resolve().parent / "handy_seite.html"
_handy = OrderedDict()  # id -> {"zeit", "gesehen", "verbunden", "nummer", "foto", "typ", "tunnel"}


@app.middleware("http")
async def nur_handy_seite_durch_tunnel(request, call_next):
    """Über den Tunnel ist nur /h/... erreichbar, nicht die übrige App und API."""
    host = request.headers.get("host", "")
    if (host.endswith(".trycloudflare.com") or "cf-ray" in request.headers) and not request.url.path.startswith("/h/"):
        return Response("Nicht gefunden", status_code=404, media_type="text/plain")
    return await call_next(request)


def _handy_sitzung(sitzung_id):
    jetzt = time.time()
    while _handy and jetzt - next(iter(_handy.values()))["zeit"] > HANDY_TTL_S:
        _handy.popitem(last=False)
    sitzung = _handy.get(sitzung_id)
    if not sitzung:
        raise HTTPException(status_code=404, detail="Sitzung abgelaufen, bitte den QR-Code neu scannen")
    return sitzung


def _tunnel_aufraeumen():
    """Tunnel schliessen, wenn ihn keine Kopplung mehr braucht (Foto da, Dialog zu, Computer weg)."""
    jetzt = time.time()
    gebraucht = any(s["tunnel"] and jetzt - s["gesehen"] < TUNNEL_LEERLAUF_S for s in _handy.values())
    if not gebraucht and tunnel.offen():
        threading.Thread(target=tunnel.schliessen, daemon=True).start()


async def _tunnel_waechter():
    while True:
        await asyncio.sleep(20)
        _tunnel_aufraeumen()


@app.on_event("startup")
async def tunnel_waechter_starten():
    asyncio.create_task(_tunnel_waechter())


@app.on_event("shutdown")
def tunnel_beenden():
    tunnel.schliessen()  # auch beim Neuladen (uvicorn --reload), sonst bliebe cloudflared offen


class HandyStart(BaseModel):
    tunnel: bool = False  # True: öffentlichen Tunnel öffnen (Computer unter localhost, Handy nicht im selben Netz)


@app.post("/api/handy")
async def handy_starten(start: HandyStart | None = None):
    """Neue Kopplung -> {id, url, tunnel}. url = Adresse für den QR-Code (null: Frontend nimmt seine eigene)."""
    sitzung_id = uuid.uuid4().hex[:12]
    jetzt = time.time()
    sitzung = _handy[sitzung_id] = {"zeit": jetzt, "gesehen": jetzt, "verbunden": False, "nummer": 0,
                                    "foto": None, "typ": None, "tunnel": False}
    while len(_handy) > HANDY_MAX:
        _handy.popitem(last=False)
    if start and start.tunnel:
        if not tunnel.verfuegbar():
            raise HTTPException(status_code=503, detail="cloudflared ist nicht installiert (Backend-Image neu bauen)")
        sitzung["tunnel"] = True  # schon vor dem Öffnen, sonst schliesst der Wächter ihn währenddessen
        try:
            basis = await asyncio.to_thread(tunnel.oeffnen)
        except Exception as fehler:
            sitzung["tunnel"] = False
            raise HTTPException(status_code=502, detail=f"Tunnel konnte nicht geöffnet werden ({fehler})")
        return {"id": sitzung_id, "url": f"{basis}/h/{sitzung_id}", "tunnel": True}
    basis = os.getenv("HANDY_BASIS_URL", "").rstrip("/")
    return {"id": sitzung_id, "url": f"{basis}/handy/{sitzung_id}" if basis else None, "tunnel": False}


@app.get("/api/handy/{sitzung_id}")
def handy_status(sitzung_id: str):
    """Für den Computer (Polling): verbunden = Handy hat die Seite geöffnet, nummer = Anzahl gesendeter Fotos."""
    sitzung = _handy_sitzung(sitzung_id)
    sitzung["gesehen"] = time.time()
    return {"verbunden": sitzung["verbunden"], "nummer": sitzung["nummer"], "tunnel": sitzung["tunnel"] and tunnel.offen()}


@app.delete("/api/handy/{sitzung_id}", status_code=204)
def handy_beenden(sitzung_id: str):
    """Dialog am Computer geschlossen: Kopplung beenden, Tunnel zu, wenn ihn sonst niemand braucht."""
    sitzung = _handy.get(sitzung_id)
    if sitzung:
        sitzung["tunnel"] = False
    _tunnel_aufraeumen()


@app.post("/api/handy/{sitzung_id}/verbunden", status_code=204)
@app.post("/h/{sitzung_id}/verbunden", status_code=204, include_in_schema=False)
def handy_verbunden(sitzung_id: str):
    _handy_sitzung(sitzung_id)["verbunden"] = True


@app.post("/api/handy/{sitzung_id}/foto")
@app.post("/h/{sitzung_id}/foto", include_in_schema=False)
async def handy_foto_senden(sitzung_id: str, bild: UploadFile = File(...)):
    sitzung = _handy_sitzung(sitzung_id)
    inhalt = await bild.read()
    if not inhalt or len(inhalt) > MAX_BILD_BYTES:
        raise HTTPException(status_code=400, detail="Bild fehlt oder ist grösser als 8 MB")
    sitzung.update(foto=inhalt, typ=bild.content_type or "image/jpeg", verbunden=True, nummer=sitzung["nummer"] + 1)
    if sitzung["tunnel"]:  # Foto ist da: Tunnel gleich wieder schliessen
        sitzung["tunnel"] = False
        asyncio.get_running_loop().call_later(TUNNEL_SCHLIESSEN_NACH_FOTO_S, _tunnel_aufraeumen)
    return {"nummer": sitzung["nummer"]}


@app.get("/api/handy/{sitzung_id}/foto")
def handy_foto_holen(sitzung_id: str):
    sitzung = _handy_sitzung(sitzung_id)
    if not sitzung["foto"]:
        raise HTTPException(status_code=404, detail="Noch kein Foto")
    return Response(sitzung["foto"], media_type=sitzung["typ"], headers={"Cache-Control": "no-store"})


@app.get("/h/ping", include_in_schema=False)
def handy_ping():
    return Response("ok", media_type="text/plain")


@app.get("/h/{sitzung_id}", include_in_schema=False)
def handy_seite(sitzung_id: str):
    """Schlanke Handy-Seite für den Tunnel: Foto aufnehmen, verkleinern, an den Computer schicken."""
    if sitzung_id not in _handy:
        return Response("<h1 style='font-family:sans-serif'>QR-Code abgelaufen</h1><p style='font-family:sans-serif'>"
                        "Bitte am Computer erneut „Mit Handy scannen“ wählen.</p>", media_type="text/html", status_code=404)
    html = HANDY_SEITE.read_text(encoding="utf-8").replace("{{SITZUNG}}", sitzung_id)
    return Response(html, media_type="text/html", headers={"Cache-Control": "no-store"})


@app.post("/api/roentgen")
async def roentgen(bild: UploadFile = File(...)):
    """Röntgenblick sofort nach der Aufnahme: Marke + Werkzeuge mit Position, ohne Katalogsuche.

    Das Ergebnis wird unter dem Hash des Fotos gemerkt; /api/match mit demselben Foto übernimmt es,
    statt Clef ein zweites Mal zu fragen.
    """
    inhalt = await bild.read()
    if not inhalt or len(inhalt) > MAX_BILD_BYTES:
        raise HTTPException(status_code=400, detail="Bild fehlt oder ist grösser als 8 MB")
    if not (vision.anbieter() == "clef" and clef.aktiv()):
        raise HTTPException(status_code=503, detail="Röntgenblick braucht Clef")
    try:
        vorab = await asyncio.shield(_vorab_starten(inhalt, bild.content_type))
    except Exception as fehler:
        raise HTTPException(status_code=502, detail=f"Röntgenblick fehlgeschlagen: {fehler}")
    erkannt = vorab["erkannt"]
    return {"marke": erkannt.get("marke"), "konfidenz": erkannt.get("konfidenz"),
            "werkzeuge": _werkzeug_liste(_gewichte(erkannt["werkzeuge"]), vorab["orte"])}


def _gewichte(werkzeuge):
    """Gruppe -> Wahrscheinlichkeit (1.0 = sicher, z. B. ohne Angabe oder vom Nutzer bestätigt)."""
    return {w["gruppe"]: float(w.get("wahrscheinlichkeit") or 1.0) for w in werkzeuge}


def _vorab_starten(inhalt, content_type):
    """Erkennung + Verortung für dieses Foto (einmal pro Foto; läuft eine schon, wird sie geteilt)."""
    schluessel = hashlib.sha1(inhalt).hexdigest()
    task = _vorab.get(schluessel)
    if task and not (task.done() and (task.cancelled() or task.exception())):
        _vorab.move_to_end(schluessel)
        return task

    async def berechnen():
        bild_url = vision.bild_als_url(inhalt, content_type or "image/jpeg")
        bild_url = await asyncio.to_thread(clef.bild_vorbereiten, bild_url)
        erkannt = await asyncio.to_thread(vision.erkenne, bild_url)
        erkannt.pop("_bild", None)
        gewichte = _gewichte(erkannt["werkzeuge"])
        orte = {}
        if gewichte:
            orte = await asyncio.to_thread(clef.lokalisieren, bild_url, sorted(gewichte, key=gewichte.get, reverse=True))
        return {"erkannt": erkannt, "orte": orte}

    task = _vorab[schluessel] = asyncio.create_task(berechnen())
    while len(_vorab) > MAX_VORAB:
        _vorab.popitem(last=False)
    return task


def _schritt(id, label, status, detail=""):
    return {"typ": "schritt", "schritt": {"id": id, "label": label, "status": status, "detail": detail}}


async def _match_ablauf(inhalt, content_type, vorherige_match_id, kategorie, verwendung):
    """Die ganze Analyse als Folge von Ereignissen (siehe /api/match/stream)."""
    if not inhalt or len(inhalt) > MAX_BILD_BYTES:
        yield {"typ": "fehler", "status": 400, "detail": "Bild fehlt oder ist grösser als 8 MB"}
        return
    loop = asyncio.get_running_loop()
    ereignisse = asyncio.Queue()

    def senden(ereignis):  # auch aus Worker-Threads (Fortschritt der Bildsuche)
        loop.call_soon_threadsafe(ereignisse.put_nowait, ereignis)

    async def arbeit():
        try:
            await _analysieren(inhalt, content_type, vorherige_match_id, kategorie, verwendung, senden)
        except Exception as fehler:  # unerwartet: trotzdem sauber beenden statt hängen
            senden({"typ": "fehler", "status": 500, "detail": f"Analyse fehlgeschlagen: {fehler}"})

    aufgabe = asyncio.create_task(arbeit())
    try:
        while True:
            ereignis = await ereignisse.get()
            yield ereignis
            if ereignis["typ"] in ("ergebnis", "fehler"):
                break
    finally:
        if not aufgabe.done():
            aufgabe.cancel()


async def _analysieren(inhalt, content_type, vorherige_match_id, kategorie, verwendung, senden):
    schritte = []

    def fertig(id, label, status, detail):
        schritte.append({"id": id, "label": label, "status": status, "detail": detail})
        senden(_schritt(id, label, status, detail))

    messer = [r for r in load_pocket_knives() if matching.produkt_gruppen(r)]
    bild_url = vision.bild_als_url(inhalt, content_type or "image/jpeg")
    # Bei Clef läuft die visuelle Katalogsuche parallel zur Werkzeug- und Markenerkennung
    mit_bildsuche = vision.anbieter() == "clef" and clef.aktiv()
    senden(_schritt("vision", "Bild analysieren", "laeuft", "Marke, Messer und 32 Werkzeugtypen prüfen"))
    try:
        if mit_bildsuche:
            bild_url = await asyncio.to_thread(clef.bild_vorbereiten, bild_url)
    except Exception as fehler:
        senden({"typ": "fehler", "status": 400, "detail": f"Bild nicht lesbar: {fehler}"})
        return
    vorab = _vorab.get(hashlib.sha1(inhalt).hexdigest()) if mit_bildsuche else None

    async def erkennen():
        """(Erkennung, Orte) – aus dem Röntgenblick der Vorschau, sonst neu."""
        if vorab:
            try:
                ergebnis = copy.deepcopy(await asyncio.shield(vorab))
                return ergebnis["erkannt"], ergebnis["orte"]
            except Exception:
                pass  # Vorschau fehlgeschlagen: normal erkennen
        return await asyncio.to_thread(vision.erkenne, bild_url), None

    erkennung = asyncio.create_task(erkennen())
    bildsuche = None
    abbruch = threading.Event()  # gesetzt, sobald eine fremde Marke mit eigenem Katalog erkannt ist
    if mit_bildsuche:
        senden(_schritt("bildsuche", "Katalogbilder vergleichen", "laeuft",
                        f"{len(messer)} Katalogbilder, zwei Turniere in unterschiedlicher Reihenfolge"))

        def melden(text):
            if not abbruch.is_set():
                senden(_schritt("bildsuche", "Katalogbilder vergleichen", "laeuft", text))

        bildsuche = asyncio.create_task(asyncio.to_thread(clef.visuell_suchen, bild_url, messer, melden, abbruch))
        bildsuche.add_done_callback(lambda t: t.cancelled() or t.exception())  # Abbruch nicht als Fehler loggen

    try:
        erkannt, orte_vorab = await erkennung
    except vision.VisionNichtKonfiguriert as fehler:
        senden({"typ": "fehler", "status": 503, "detail": str(fehler)})
        return
    except Exception as fehler:  # Anbieterfehler (Netz, Quote, Inhaltsfilter)
        senden({"typ": "fehler", "status": 502, "detail": f"Bilderkennung fehlgeschlagen: {fehler}"})
        return
    info = erkannt.pop("modell_info")
    erkannt.pop("_bild", None)
    fertig("vision", "Bild analysiert", "ok",
           f"{erkannt['marke'] or 'Marke unklar'}, {len(erkannt['werkzeuge'])} Werkzeuge erkannt ({info['modell']})"
           + (", aus der Vorschau übernommen" if orte_vorab is not None else ""))

    # Fremde Marke mit eigenem Katalog (SWIZA, Leatherman, Gerber): Die Victorinox-Bildsuche kann dieses
    # Modell nicht finden, darum wird sie abgebrochen und das Modell im Katalog der Marke bestimmt.
    marke = erkannt.get("marke")
    marke_p = max((erkannt.get("marke_wahrscheinlichkeiten") or {}).values(), default=1.0)
    im_markenkatalog = (bool(marke) and marke != "Victorinox" and marke_p >= MARKE_SICHER
                        and konkurrenz.hat_katalog(marke))
    if im_markenkatalog and bildsuche:
        abbruch.set()
        fertig("bildsuche", "Katalogbilder verglichen", "ok",
               f"Übersprungen: {marke} erkannt ({marke_p:.0%}), Modell wird im {marke}-Katalog gesucht")
        bildsuche = None

    werkzeuge = erkannt["werkzeuge"]
    try:
        zugeordnet = await asyncio.to_thread(jev.werkzeuge_zuordnen, werkzeuge)
    except Exception as fehler:
        zugeordnet = None
        fertig("ocr", "Werkzeuge zugeordnet", "warnung",
               f"Jev nicht erreichbar, Zuordnung der Bilderkennung verwendet ({fehler})")
    if zugeordnet is not None:
        werkzeuge = zugeordnet
        fertig("ocr", "Werkzeuge zugeordnet", "ok", f"Jev: {len(werkzeuge)} Werkzeuge mit Konfidenz bestätigt")
    gewichte = _gewichte(werkzeuge)

    # Röntgenblick: erkannte Werkzeuge auf dem Foto verorten (läuft, während die Bildsuche weiterrechnet)
    modellsuche = None
    if im_markenkatalog and gewichte:
        senden(_schritt("markenkatalog", f"Modell im {marke}-Katalog suchen", "laeuft",
                        f"{len(konkurrenz.produkte_von_marke(marke))} {marke}-Modelle nach Werkzeugen und Bild vergleichen"))
        modellsuche = asyncio.create_task(_markenmodell(bild_url if mit_bildsuche else None, marke, dict(gewichte)))

    orte = {}
    if mit_bildsuche and gewichte:
        senden(_schritt("roentgen", "Werkzeuge auf dem Foto verorten", "laeuft", "Röntgenblick"))
        zu_verorten = sorted(gewichte, key=gewichte.get, reverse=True)
        if orte_vorab is not None:  # aus der Vorschau; nur Werkzeuge, die Jev neu zugeordnet hat, nachverorten
            orte = {g: orte_vorab[g] for g in zu_verorten if g in orte_vorab}
            zu_verorten = [g for g in zu_verorten if g not in orte_vorab]
        try:
            if zu_verorten:
                orte |= await asyncio.to_thread(clef.lokalisieren, bild_url, zu_verorten)
            fertig("roentgen", "Werkzeuge auf dem Foto verortet", "ok", f"{len(orte)} Werkzeuge markiert"
                   + (" (aus der Vorschau)" if orte_vorab is not None else ""))
        except Exception as fehler:
            fertig("roentgen", "Werkzeuge auf dem Foto verortet", "warnung", f"Nicht verfügbar ({fehler})")
    senden({"typ": "werkzeuge", "werkzeuge": _werkzeug_liste(gewichte, orte)})

    konkurrenz_ergebnis = {}
    if modellsuche:
        try:
            produkt, grund, anzahl = await modellsuche
            konkurrenz_ergebnis = {"konkurrenz_produkt": produkt}
            if produkt:
                fertig("markenkatalog", f"Modell im {marke}-Katalog bestimmt", "ok",
                       f"{produkt.name}{f' ({produkt.artikelnummer})' if produkt.artikelnummer else ''}: {grund}, "
                       f"{produkt.anzahl_gruppen} Werkzeuge laut {produkt.quelle}"
                       + ("" if produkt.vollstaendig else " (Liste unvollständig, erkannte bleiben dazu)"))
            else:
                fertig("markenkatalog", f"Modell im {marke}-Katalog gesucht", "warnung",
                       f"{anzahl} Kandidaten, {grund}; es zählen die erkannten Werkzeuge")
        except Exception as fehler:
            fertig("markenkatalog", f"Modell im {marke}-Katalog gesucht", "warnung", f"Nicht verfügbar ({fehler})")

    visuell = {}
    if bildsuche:
        try:
            visuell = dict(await bildsuche)
            fertig("bildsuche", "Katalogbilder verglichen", "ok",
                   f"Clef hat das Foto mit {len(messer)} Katalogbildern verglichen")
        except Exception as fehler:
            fertig("bildsuche", "Katalogbilder verglichen", "warnung",
                   f"Bildsuche fehlgeschlagen, nur Werkzeug-Matching ({fehler})")
    vorher = _matches.get(vorherige_match_id)
    if vorher:
        for g, p in vorher["gewichte"].items():
            gewichte[g] = max(gewichte.get(g, 0.0), p)
        if vorher["visuell"] and visuell:  # zwei Fotos: Mittelwert der Bildsuche
            visuell = {n: (visuell.get(n, 0) + vorher["visuell"].get(n, 0)) / 2 for n in visuell.keys() | vorher["visuell"].keys()}
        visuell = visuell or vorher["visuell"]

    kontext = {"erkannt": erkannt, "gewichte": gewichte, "visuell": visuell, "schritte": schritte, "orte": orte,
               "verwendung": (verwendung or "").strip()[:300], "kategorie": kategorie, "nutzer_werkzeuge": False,
               **konkurrenz_ergebnis}
    match_id = f"m_{uuid.uuid4().hex[:10]}"
    _matches[match_id] = kontext
    senden({"typ": "ergebnis", "ergebnis": await _auswerten(match_id, kontext)})


async def _markenmodell(bild_url, marke, gewichte):
    """Modell einer fremden Marke: Werkzeug-Score im Markenkatalog, dazu ein Bildvergleich (eine
    Clef-Anfrage) mit den besten Kandidaten, die ein Produktbild haben. -> (Produkt|None, Grund, Anzahl)"""
    bewertet = konkurrenz.kandidaten(marke, gewichte)
    bild = {}
    mit_bild = konkurrenz.fuer_bildvergleich(bewertet) if bild_url else []
    if mit_bild:
        try:
            bild = await asyncio.to_thread(clef.modell_waehlen, bild_url, konkurrenz.bild_rows(mit_bild))
        except Exception:
            bild = {}  # Bildvergleich ist nur ein Zusatz, Werkzeuge reichen auch
    produkt, grund = konkurrenz.waehle(bewertet, bild)
    return produkt, grund, len(bewertet)


def _werkzeug_liste(gewichte, orte):
    """Erkannte Werkzeuge mit Sicherheit und Position, sicherste zuerst (1.0 = sicher/vom Nutzer bestätigt)."""
    return sorted(({"gruppe": g, "label": GRUPPEN[g][0], "wahrscheinlichkeit": round(p, 2), "position": orte.get(g)}
                   for g, p in gewichte.items()),
                  key=lambda w: (-w["wahrscheinlichkeit"], w["label"]))


class Werkzeug(BaseModel):
    model_config = ConfigDict(extra="ignore")

    gruppe: str
    wahrscheinlichkeit: float | None = Field(None, ge=0, le=1, description="fehlt/1.0 = sicher (bestätigt)")


class WerkzeugKorrektur(BaseModel):
    """Komplette, vom Nutzer korrigierte Werkzeugliste. Was fehlt, gilt als entfernt."""

    model_config = ConfigDict(extra="forbid")

    werkzeuge: list[Werkzeug]


@app.get("/api/werkzeuge")
def get_werkzeuge():
    """Alle Werkzeuggruppen (für Vorschläge beim Hinzufügen)."""
    return [{"gruppe": g, "label": label, "beschreibung": beschreibung} for g, (label, beschreibung) in GRUPPEN.items()]


@app.post("/api/match/{match_id}/werkzeuge")
async def werkzeuge_korrigieren(match_id: str, korrektur: WerkzeugKorrektur):
    """Werkzeuge bestätigen/hinzufügen/entfernen und ohne neues Foto erneut suchen."""
    kontext = _matches.get(match_id)
    if not kontext:
        raise HTTPException(status_code=404, detail="Match nicht gefunden (Backend neu gestartet?), bitte neu scannen")
    unbekannt = [w.gruppe for w in korrektur.werkzeuge if w.gruppe not in GRUPPEN]
    if unbekannt:
        raise HTTPException(status_code=422, detail=f"Unbekannte Werkzeuge: {', '.join(unbekannt)}")
    alt = kontext["gewichte"]
    neu = {w.gruppe: 1.0 if w.wahrscheinlichkeit is None else w.wahrscheinlichkeit for w in korrektur.werkzeuge}
    bestaetigt = [g for g in neu if g in alt and alt[g] < 1.0 <= neu[g]]
    hinzu = [g for g in neu if g not in alt]
    weg = [g for g in alt if g not in neu]
    teile = [f"{len(bestaetigt)} bestätigt" if bestaetigt else "", f"{len(hinzu)} hinzugefügt" if hinzu else "",
             f"{len(weg)} entfernt" if weg else ""]
    kontext = dict(kontext, gewichte=neu, nutzer_werkzeuge=True, schritte=kontext["schritte"] + [
        {"id": "nutzer", "label": "Werkzeuge vom Nutzer korrigiert", "status": "ok",
         "detail": ", ".join(t for t in teile if t) or "unverändert"}])
    _matches[match_id] = kontext
    return await _auswerten(match_id, kontext)


async def _auswerten(match_id, kontext):
    """Erkennung (gecacht pro match_id) -> Kandidaten, Pfad, Rückfrage, Antwort für das Frontend."""
    erkannt, gewichte, visuell = kontext["erkannt"], kontext["gewichte"], kontext["visuell"]
    verwendung, kategorie = kontext["verwendung"], kontext["kategorie"]
    schritte = list(kontext["schritte"])
    erkannte_gruppen = set(gewichte)
    rows = load_pocket_knives()
    messer = [r for r in rows if matching.produkt_gruppen(r)]

    def kategorie_faktor(row):
        # Weicher Filter (Kategorie-Hinweis): andere Kategorien zählen halb, fallen aber nicht weg
        return 1.0 if not kategorie or kategorie in split_list(row["kategorien"], ";") else KATEGORIE_MALUS

    marke = erkannt["marke"]
    ist_victorinox = bool(marke and "victorinox" in marke.casefold())
    fremd = bool(marke) and not ist_victorinox
    schritte.append({"id": "marke", "label": "Marke bestimmt", "status": "ok" if marke else "warnung",
                     "detail": marke or "Marke nicht erkennbar"})
    # Nach der Ausstattung suchen: bei fremden Marken (kein Katalogbild kann dasselbe Modell zeigen)
    # und sobald der Nutzer die Werkzeuge korrigiert hat
    nach_ausstattung = (fremd or kontext["nutzer_werkzeuge"]) and bool(erkannte_gruppen)

    # Querverweis auf die Konkurrenz: steht das Produkt in der Tabelle aus
    # backend/data/training/konkurrenz.csv, kennen wir seine Werkzeugliste genau.
    # Das ist verlaesslicher als die Bilderkennung, die nur offene Werkzeuge sieht
    # und bei geschlossenen Messern danebenliegt.
    konkurrenz_produkt = None
    # Hat der Nutzer die Werkzeuge korrigiert, gilt seine Liste und nicht die Tabelle
    if fremd and erkannte_gruppen and not kontext["nutzer_werkzeuge"]:
        if "konkurrenz_produkt" in kontext:  # schon beim Foto im Markenkatalog bestimmt (_markenmodell)
            konkurrenz_produkt = kontext["konkurrenz_produkt"]
        else:
            try:
                konkurrenz_produkt = konkurrenz.finde_besten(marke, erkannte_gruppen)
            except Exception as fehler:
                schritte.append({"id": "ocr", "label": "Konkurrenz-Produkt zugeordnet", "status": "warnung",
                                 "detail": f"Konkurrenzdaten nicht nutzbar ({fehler})"})
            if konkurrenz_produkt:
                schritte.append({"id": "ocr", "label": "Konkurrenz-Produkt zugeordnet", "status": "ok",
                                 "detail": f"{konkurrenz_produkt.name} ({konkurrenz_produkt.artikelnummer}) – "
                                           f"{konkurrenz_produkt.anzahl_gruppen} Werkzeuge laut {konkurrenz_produkt.quelle}"})
        if konkurrenz_produkt:
            if konkurrenz_produkt.vollstaendig:  # komplette Werkzeugliste: sie gilt, alle Gruppen voll
                gewichte_aus_tabelle = {g: 1.0 for g in konkurrenz_produkt.werkzeug_gruppen}
            else:  # unvollständig (Gerber): bekannte Werkzeuge sicher, erkannte bleiben dazu
                gewichte_aus_tabelle = {**gewichte, **{g: 1.0 for g in konkurrenz_produkt.werkzeug_gruppen}}
            erkannte_gruppen = set(gewichte_aus_tabelle)

    # Fremde Marke: Kein Katalogbild kann dasselbe Modell zeigen, darum zählt die Ausstattung.
    # Zangen-Multitools (Leatherman, Gerber) bekommen zusätzlich die Swiss Tools als Ersatz.
    if konkurrenz_produkt:
        # Die Werkzeugliste aus der Querverweistabelle gilt: alle Gruppen zählen voll.
        gewichte = dict(gewichte_aus_tabelle)
    auswahl = messer
    if nach_ausstattung and gewichte.get("zange", 0.0) >= ZANGE_SICHER:
        auswahl = [r for r in load_empfehlbare() if matching.produkt_gruppen(r)]

    passung = {}  # artikelnummer -> z-Wert: wie gut das Produkt zum Verwendungszweck passt
    if verwendung:
        try:
            passung = await asyncio.to_thread(embeddings.verwendung_passung, verwendung, auswahl)
            schritte.append({"id": "verwendung", "label": "Verwendungszweck abgeglichen", "status": "ok",
                             "detail": f"„{verwendung}“ mit {len(auswahl)} Produktbeschreibungen verglichen (Embedding)"})
        except Exception as fehler:
            schritte.append({"id": "verwendung", "label": "Verwendungszweck abgeglichen", "status": "warnung",
                             "detail": f"Embedding nicht verfügbar ({fehler})"})

    def zweck_faktor(nummer):
        return math.exp(VERWENDUNG_GEWICHT * max(min(passung.get(nummer, 0.0), 3.0), -3.0))

    def zweck_grund(k):
        if passung.get(k["row"]["artikelnummer"], 0.0) >= 1.0:
            k["gruende"].append(f"Passt zum Einsatz „{verwendung}“")

    if nach_ausstattung:
        # 1. Verwendungszweck filtert: nur Produkte, die überdurchschnittlich zum Zweck passen
        if passung:
            passend = [r for r in auswahl if passung[r["artikelnummer"]] >= 0]
            if len(passend) < MIN_NACH_ZWECK:
                passend = sorted(auswahl, key=lambda r: -passung[r["artikelnummer"]])[:MIN_NACH_ZWECK]
            schritte.append({"id": "verwendung", "label": "Nach Einsatzzweck gefiltert", "status": "ok",
                             "detail": f"{len(passend)} von {len(auswahl)} Produkten passen zu „{verwendung}“"})
            auswahl = passend
        # 2. Ausstattung entscheidet, gewichtet mit Clefs Sicherheit je Werkzeug; Bild nur als Tiebreak
        kandidaten = matching.rangliste(erkannte_gruppen, auswahl, erkannt, top=len(auswahl), gewichte=gewichte)
        hoechste = max(visuell.values(), default=0.0) or 1.0
        for k in kandidaten:
            nummer = k["row"]["artikelnummer"]
            k["score"] = round(min(k["score"] * kategorie_faktor(k["row"])
                                   + GEWICHT_BILD_TIEBREAK * visuell.get(nummer, 0.0) / hoechste, 1.0), 4)
            zweck_grund(k)
        kandidaten = sorted(kandidaten, key=matching.sortierschluessel)[:3]
        schritte.append({"id": "suche", "label": "Ausstattung verglichen", "status": "ok" if kandidaten else "warnung",
                         "detail": f"{len(erkannte_gruppen)} Werkzeuge mit {len(auswahl)} Victorinox-Produkten verglichen"})
        eigenes = next((k for k in kandidaten if k["score"] >= 0.95 and ist_victorinox), None)
    elif visuell:
        # Victorinox (oder Marke unklar): Reihenfolge und Score aus der Bildsuche, die Werkzeuge
        # liefern die Begründung
        nach_nummer = {r["artikelnummer"]: r for r in messer}
        kandidaten = []
        # Kategorie und Verwendungszweck gewichten Clefs Wahrscheinlichkeiten, danach wieder auf
        # Summe 1 normiert: Passen Bild und Zweck zusammen, steigt die Sicherheit von Platz 1
        gewichtet = {n: p * kategorie_faktor(nach_nummer[n]) * zweck_faktor(n)
                     for n, p in visuell.items() if n in nach_nummer}
        summe = sum(gewichtet.values()) or 1.0
        gewichtet = {n: p / summe * sum(visuell.values()) for n, p in gewichtet.items()}
        for nummer, p in sorted(gewichtet.items(), key=lambda kv: -kv[1])[:3]:
            k = matching.bewerte(erkannte_gruppen, nach_nummer[nummer], erkannt) or {
                "row": nach_nummer[nummer], "gruppen": matching.produkt_gruppen(nach_nummer[nummer]),
                "gemeinsam": set(), "fehlend": set(), "zusaetzlich": set(), "gruende": []}
            k["score"] = round(p, 4)
            k["gruende"].insert(0, f"Bildähnlichkeit {visuell[nummer]:.0%}")
            zweck_grund(k)
            kandidaten.append(k)
        schritte.append({"id": "suche", "label": "Katalogbilder verglichen", "status": "ok",
                         "detail": f"Clef hat das Foto mit {len(messer)} Katalogbildern verglichen"})
        zweiter = kandidaten[1]["score"] if len(kandidaten) > 1 else 0.0
        eigenes = next((k for k in kandidaten[:1] if ist_victorinox and k["score"] >= VISUELL_SICHER
                        and k["score"] >= VISUELL_ABSTAND * zweiter), None)
    else:
        kandidaten = matching.rangliste(erkannte_gruppen, rows, erkannt, top=len(rows), gewichte=gewichte)
        for k in kandidaten:
            k["score"] = round(min(k["score"] * kategorie_faktor(k["row"]) * zweck_faktor(k["row"]["artikelnummer"]), 1.0), 4)
            zweck_grund(k)
        kandidaten = sorted(kandidaten, key=matching.sortierschluessel)[:3]
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

    return {
        "match_id": match_id,
        "pfad": pfad,
        "erkannt": {
            "marke": marke,
            "ist_victorinox": ist_victorinox,
            "modell": (konkurrenz_produkt.name if konkurrenz_produkt else erkannt["modell"]),
            "artikelnummer": (konkurrenz_produkt.artikelnummer if konkurrenz_produkt
                              else erkannt["artikelnummer_sichtbar"]),
            "kategorie": "Taschenmesser (SAK)" if erkannt["ist_taschenmesser"] else None,
            "konfidenz": erkannt["konfidenz"],
            "produkt": to_product(eigenes["row"]) if eigenes else None,
            "werkzeuge": _werkzeug_liste(gewichte, kontext.get("orte", {})),
            "merkmale": [{"key": "werkzeuge", "label": "Werkzeuge",
                          "quelle": (konkurrenz_produkt.quelle
                                     if konkurrenz_produkt
                                     else ("Nutzer" if kontext["nutzer_werkzeuge"] else "Bilderkennung")),
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


@app.get("/score_categories", response_model=CategoryScores)
def get_scores(q: str) -> CategoryScores:
    # Falls die Anfrage leer ist, leeres Dict zurückgeben
    if not q.strip():
        return CategoryScores(query=q, scores={cat: 0.0 for cat in CATEGORIES})

    if not EMBEDDINGS_AKTIV:
        raise HTTPException(status_code=503, detail="Embedding-Modul nicht verfuegbar")

    # Suchtext einbetten
    query_embedding = list(setup_embedding_model().embed([q]))[0]
    
    # Dictionary für die Antwort aufbauen
    scores_dict = {}
    for category, cat_emb in zip(CATEGORIES, generate_category_embeddings()):
        score = cosine_similarity(query_embedding, cat_emb)
        scores_dict[category] = round(score, 4)
        
    # Das Dictionary nach den höchsten Scores sortieren möchten
    sorted_scores_dict = dict(sorted(scores_dict.items(), key=lambda item: item[1], reverse=True))
    
    # Rückgabe validiert gegen Ihr Pydantic-Modell
    return CategoryScores(query=q, scores=sorted_scores_dict)


# --- Feedback -------------------------------------------------------------------
# Das Feedback landet für den Prototyp lokal (JSONL-Datei neben den Katalogdaten).
# Es gibt bewusst keinen Rückkanal in die Systeme des Kunden.

FEEDBACK_CSV = Path(__file__).resolve().parent.parent / "data" / "feedback.jsonl"


class FeedbackBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    match_id: str | None = None
    korrekt: bool = False
    gewaehlte_artikelnummer: str | None = None


@app.post("/api/feedback")
def feedback(body: FeedbackBody):
    """Nimmt das Nutzerfeedback entgegen und legt es lokal ab."""
    eintrag = {
        "zeit": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "match_id": body.match_id,
        "korrekt": body.korrekt,
        "gewaehlte_artikelnummer": body.gewaehlte_artikelnummer,
    }
    try:
        FEEDBACK_CSV.parent.mkdir(parents=True, exist_ok=True)
        with FEEDBACK_CSV.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
    except OSError as fehler:
        raise HTTPException(status_code=500, detail=f"Feedback konnte nicht gespeichert werden: {fehler}")
    return {"gespeichert": True, "anzahl": _feedback_anzahl()}


def _feedback_anzahl() -> int:
    if not FEEDBACK_CSV.exists():
        return 0
    return sum(1 for _ in FEEDBACK_CSV.open(encoding="utf-8"))
