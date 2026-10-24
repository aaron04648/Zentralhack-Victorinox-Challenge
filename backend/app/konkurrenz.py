"""Konkurrenz-Produkte: Modell einer fremden Marke bestimmen und seine Werkzeugliste verwenden.

Quellen (alle beim ersten Aufruf geladen und zusammengeführt):
- backend/data/training/konkurrenz.csv     SWIZA-Webshop (swiza.com): Werkzeuglisten + Produktbilder
- backend/data/kataloge/swiza.json         SWIZA-Katalog (PDF, OCR): alle Modelle mit Werkzeugliste
- backend/data/kataloge/leatherman_2019.json  Leatherman-Katalog 2019: Werkzeugliste, keine Bilder
- backend/data/kataloge/gerber.json        Gerber-Katalog: nur Beschreibungen, Werkzeugliste darum unvollständig

Ein geschlossenes Messer zeigt seine Werkzeuge nicht, das Foto taugt dann nur für die Marke.
Darum: Marke erkannt -> nur im Katalog dieser Marke das Modell suchen (über die sichtbaren
Werkzeuge, wo es Bilder gibt zusätzlich per Bildvergleich) und dann mit dessen kompletter
Werkzeugliste im Victorinox-Sortiment suchen. Das ist schneller als die Bildsuche über alle
Victorinox-Bilder, die bei einer fremden Marke ohnehin nicht dasselbe Modell finden kann.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.werkzeuge import gruppen

DATA = Path(__file__).resolve().parent.parent / "data"
KONKURRENZ_CSV = DATA / "training" / "konkurrenz.csv"
KATALOGE = {  # Datei -> Werkzeugliste vollständig?
    "swiza.json": True,
    "leatherman_2019.json": True,
    "gerber.json": False,  # Werkzeuge nur aus der Beschreibung gelesen
}

# Marke -> Normalform, wie sie die Bilderkennung meldet.
MARKEN_ALIASSE = {
    "swiza": "SWIZA",
    "roxon": "ROXON",
    "helton": "The Helton",
    "the helton": "The Helton",
    "leatherman": "Leatherman",
    "gerber": "Gerber",
    "wenger": "Wenger",
}

MIN_ABDECKUNG = 0.5        # Anteil der erkannten Werkzeuge (gewichtet), die das Modell haben muss
MAX_ZUSATZ = 4             # Modelle mit viel mehr Werkzeugen als erkannt sind geraten
MAX_BILDVERGLEICH = 27     # so viele Kandidaten passen in eine Clef-Anfrage (3 Raster à 9)
MIN_GEMEINSAM_TEILWEISE = 2  # unvollständige Liste: so viele bekannte Werkzeuge müssen erkannt sein
GERBER_KATEGORIEN = {"knives", "multi-tools"}  # Taschenlampen, Äxte, Ausrüstung sind kein Ersatzfall


@dataclass
class KonkurrenzProdukt:
    marke: str
    artikelnummer: str
    name: str
    werkzeuge_text: str
    werkzeug_gruppen: frozenset[str] = field(default_factory=frozenset)
    bild_urls: tuple[str, ...] = ()
    vollstaendig: bool = True          # False: Werkzeugliste nur teilweise bekannt (Gerber)
    kategorie: str | None = None
    quelle: str = ""
    varianten: tuple[str, ...] = ()

    @property
    def anzahl_gruppen(self) -> int:
        return len(self.werkzeug_gruppen)

    @property
    def schluessel(self) -> str:
        """Eindeutig und dateinamentauglich (Kachel-Cache der Bildsuche)."""
        return re.sub(r"[^A-Za-z0-9._-]", "_", f"{self.marke}_{self.artikelnummer or self.name}")


def _aus_csv() -> list[KonkurrenzProdukt]:
    if not KONKURRENZ_CSV.exists():
        return []
    out = []
    with KONKURRENZ_CSV.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            out.append(KonkurrenzProdukt(
                marke=(row.get("marke") or "").strip(),
                artikelnummer=(row.get("artikelnummer") or "").strip(),
                name=(row.get("name") or "").strip(),
                werkzeuge_text=(row.get("werkzeuge_text") or "").strip(),
                werkzeug_gruppen=frozenset(g.strip() for g in (row.get("werkzeug_gruppen") or "").split(",") if g.strip()),
                bild_urls=tuple(u.strip() for u in (row.get("bild_urls") or "").split() if u.strip()),
                quelle=(row.get("quelle") or "webshop").strip(),
            ))
    return out


def _gerber_werkzeuge(p) -> list[str]:
    """Gerber hat keine Werkzeuglisten: Werkzeuge aus Name, Beschreibung und Ausführungen lesen."""
    texte = [p.get("name") or "", p.get("beschreibung") or ""]
    texte += [a for v in p.get("varianten") or [] for a in v.get("ausfuehrung") or []]
    teile = [t.strip() for s in texte for t in re.split(r"[,;+.]| and | with ", s) if t.strip()]
    werkzeuge = [t for t in teile if gruppen([t])]
    kategorie = (p.get("kategorie") or "").lower()
    if kategorie == "multi-tools":
        werkzeuge.append("pliers")          # Gerber-Multitools sind Zangen-Tools
    if kategorie in ("knives", "multi-tools"):
        werkzeuge.append("Blade")
    return werkzeuge


def _aus_katalog(datei, vollstaendig) -> list[KonkurrenzProdukt]:
    pfad = DATA / "kataloge" / datei
    if not pfad.exists():
        return []
    out = []
    for p in json.loads(pfad.read_text(encoding="utf-8"))["produkte"]:
        if not vollstaendig and (p.get("kategorie") or "").lower() not in GERBER_KATEGORIEN:
            continue
        werkzeuge = p.get("werkzeuge") or (_gerber_werkzeuge(p) if not vollstaendig else [])
        g = gruppen(werkzeuge)
        if not g:
            continue
        out.append(KonkurrenzProdukt(
            marke=p["marke"],
            artikelnummer=p.get("artikelnummer") or "",
            name=p.get("modell") or p["name"],
            werkzeuge_text=", ".join(werkzeuge),
            werkzeug_gruppen=frozenset(g),
            vollstaendig=vollstaendig,
            kategorie=p.get("kategorie"),
            quelle=f"Katalog {p['marke']}",
            varianten=tuple(v["artikelnummer"] for v in p.get("varianten") or [] if v.get("artikelnummer")),
        ))
    return out


@lru_cache(maxsize=1)
def produkte() -> list[KonkurrenzProdukt]:
    """Alle Konkurrenzprodukte. Webshop-Einträge (mit Bildern) haben Vorrang vor Katalogeinträgen
    desselben Modells; Katalogmodelle ohne Webshop-Eintrag kommen dazu."""
    webshop = _aus_csv()
    bekannt = {p.artikelnummer for p in webshop}
    out = list(webshop)
    for datei, vollstaendig in KATALOGE.items():
        for p in _aus_katalog(datei, vollstaendig):
            nummern = {p.artikelnummer, *p.varianten}
            # SWIZA: Katalog "KNI.0036" mit Varianten "KNI.0036.1010", Webshop führt die Varianten einzeln
            if nummern & bekannt or any(n.startswith(p.artikelnummer + ".") for n in bekannt if p.artikelnummer):
                continue
            out.append(p)
    return out


def marke_normalisiert(marke: str | None) -> str | None:
    """Die Marke aus der Bilderkennung auf die Schreibweise der Daten bringen."""
    if not marke:
        return None
    return MARKEN_ALIASSE.get(marke.casefold().strip())


def produkte_von_marke(marke: str | None) -> list[KonkurrenzProdukt]:
    """Alle bekannten Produkte einer Marke."""
    normalisiert = marke_normalisiert(marke)
    if not normalisiert:
        return []
    return [p for p in produkte() if p.marke.casefold() == normalisiert.casefold()]


def hat_katalog(marke: str | None) -> bool:
    return bool(produkte_von_marke(marke))


def kandidaten(marke: str | None, gewichte: dict[str, float]) -> list[tuple[float, KonkurrenzProdukt]]:
    """Modelle der Marke, deren Werkzeugliste zu den erkannten Werkzeugen passt, bestes zuerst.

    gewichte: Gruppe -> Wahrscheinlichkeit aus der Bilderkennung. Score = gewichtete Abdeckung
    der erkannten Werkzeuge, abzüglich eines kleinen Abzugs pro zusätzlichem Werkzeug (bei
    gleicher Abdeckung gewinnt das Modell, das am wenigsten dazu raten muss). Bei unvollständigen
    Werkzeuglisten (Gerber) zählt umgekehrt, wie viele der bekannten Werkzeuge erkannt wurden.
    """
    summe = sum(gewichte.values())
    if not summe:
        return []
    bewertet = []
    for p in produkte_von_marke(marke):
        gemeinsam = p.werkzeug_gruppen & gewichte.keys()
        if p.vollstaendig:
            abdeckung = sum(gewichte[g] for g in gemeinsam) / summe
            zusatz = len(p.werkzeug_gruppen - gewichte.keys())
            if abdeckung < MIN_ABDECKUNG or zusatz > MAX_ZUSATZ + len(gewichte) // 3:
                continue
            score = abdeckung - 0.03 * zusatz
        else:
            if len(gemeinsam) < MIN_GEMEINSAM_TEILWEISE:
                continue
            score = sum(gewichte[g] for g in gemeinsam) / len(p.werkzeug_gruppen)
            if score < MIN_ABDECKUNG:
                continue
        bewertet.append((round(score, 4), p))
    bewertet.sort(key=lambda kv: (-kv[0], kv[1].anzahl_gruppen, kv[1].name))
    return bewertet


def fuer_bildvergleich(bewertet: list[tuple[float, KonkurrenzProdukt]]) -> list[KonkurrenzProdukt]:
    """Die besten Kandidaten mit Produktbild (für eine Clef-Anfrage)."""
    return [p for _, p in bewertet if p.bild_urls][:MAX_BILDVERGLEICH]


def bild_rows(produkte_liste):
    """Format der Clef-Bildsuche: {"artikelnummer": Schlüssel, "bild_url": erstes Produktbild}."""
    return [{"artikelnummer": p.schluessel, "bild_url": p.bild_urls[0]} for p in produkte_liste if p.bild_urls]


def waehle(bewertet, bild_wahrscheinlichkeiten=None) -> tuple[KonkurrenzProdukt | None, str]:
    """Bestes Modell aus Werkzeug-Score und (falls vorhanden) Bildvergleich -> (Produkt, Begründung).

    Ohne Bildvergleich wird nur ein Modell genannt, wenn es nach Werkzeugen eindeutig vorne liegt
    oder alle gleichauf liegenden dieselbe Werkzeugliste haben (z. B. Farbvarianten).
    """
    if not bewertet:
        return None, "kein Modell der Marke passt zu den erkannten Werkzeugen"
    bild = bild_wahrscheinlichkeiten or {}
    if bild:
        nach_schluessel = {p.schluessel: (s, p) for s, p in bewertet}
        kombiniert = sorted(((s * (0.25 + bild.get(k, 0.0)), p, bild.get(k, 0.0))
                             for k, (s, p) in nach_schluessel.items() if k in bild),
                            key=lambda t: -t[0])
        if kombiniert and kombiniert[0][2] >= 0.3:
            _, p, wahrscheinlichkeit = kombiniert[0]
            return p, f"Bildvergleich {wahrscheinlichkeit:.0%} + Werkzeuge"
    bester_score, bestes = bewertet[0]
    gleichauf = [p for s, p in bewertet if s >= bester_score - 1e-9]
    # Gleich ausgestattet heisst nur bei vollständigen Listen "Variante desselben Modells"
    if len(gleichauf) == 1 or (bestes.vollstaendig and all(p.werkzeug_gruppen == bestes.werkzeug_gruppen for p in gleichauf)):
        return bestes, "Werkzeuge" + (f" ({len(gleichauf)} Varianten gleich ausgestattet)" if len(gleichauf) > 1 else "")
    return None, f"{len(gleichauf)} Modelle gleich gut passend, keines eindeutig"


def finde_besten(marke: str | None, erkannte_gruppen: set[str]) -> KonkurrenzProdukt | None:
    """Kompatibel zur früheren Schnittstelle: alle erkannten Gruppen gelten als sicher."""
    produkt, _ = waehle(kandidaten(marke, {g: 1.0 for g in erkannte_gruppen}))
    return produkt


def artikelnummer_aus_text(text: str) -> str | None:
    """Eine Artikelnummer aus einem Freitextfeld ziehen (z. B. "SKU KNI.0036.1010")."""
    match = re.search(r"\b([A-Z]{3}\.[0-9]{4}\.[0-9]{4}(?:\.[A-Z0-9]+)?)\b", text or "")
    return match.group(1) if match else None
