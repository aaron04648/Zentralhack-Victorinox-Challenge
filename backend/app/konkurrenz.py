"""Konkurrenz-Produkte und ihre Querverweise auf den Victorinox-Katalog.

`backend/data/training/konkurrenz.csv` enthaelt die Werkzeuglisten der
Konkurrenzprodukte (Stand: swiza.com). Das ist genau die Art von Information,
die die Bilderkennung nicht liefern kann: ein *geschlossenes* Messer zeigt seine
Werkzeuge nicht, das Foto taugt dann nur noch fuer die Marke.

Deshalb: ist die Marke erkannt und gehoert sie zu einem bekannten
Konkurrenzhersteller, dann suchen wir das konkrete Konkurrenzprodukt (ueber
die sichtbaren Werkzeuge) und benutzen dessen exakte Werkzeugliste fuer den
Abgleich mit dem Victorinox-Katalog. Das ist der dokumentierte Ablauf aus
docs/classification_recommendation.md (§8): die Werkzeugliste des Katalogs ist
der eigentliche Discriminator, nicht das Foto.

Die Kandidaten werden zusaetzlich ueber ihre Katalogbilder identifiziert: die
Bildsuche vergleicht das Foto mit den Produktbildern der Konkurrenz.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

KONKURRENZ_CSV = Path(__file__).resolve().parent.parent / "data" / "training" / "konkurrenz.csv"

# Marke -> Normalform, wie sie die Bilderkennung meldet.
MARKEN_ALIASSE = {
    "swiza": "SWIZA",
    "roxon": "ROXON",
    "helton": "The Helton",
    "leatherman": "Leatherman",
    "gerber": "Gerber",
    "wenger": "Wenger",
}


@dataclass
class KonkurrenzProdukt:
    marke: str
    artikelnummer: str
    name: str
    werkzeuge_text: str
    werkzeug_gruppen: frozenset[str] = field(default_factory=frozenset)
    bild_urls: tuple[str, ...] = ()

    @property
    def anzahl_gruppen(self) -> int:
        return len(self.werkzeug_gruppen)


@lru_cache(maxsize=1)
def produkte() -> list[KonkurrenzProdukt]:
    """Alle Konkurrenzprodukte aus der Querverweistabelle."""
    if not KONKURRENZ_CSV.exists():
        return []
    out: list[KonkurrenzProdukt] = []
    with KONKURRENZ_CSV.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            gruppen = frozenset(
                g.strip() for g in (row.get("werkzeug_gruppen") or "").split(",") if g.strip()
            )
            bilder = tuple(
                url.strip() for url in (row.get("bild_urls") or "").split() if url.strip()
            )
            out.append(KonkurrenzProdukt(
                marke=(row.get("marke") or "").strip(),
                artikelnummer=(row.get("artikelnummer") or "").strip(),
                name=(row.get("name") or "").strip(),
                werkzeuge_text=(row.get("werkzeuge_text") or "").strip(),
                werkzeug_gruppen=gruppen,
                bild_urls=bilder,
            ))
    return out


def marke_normalisiert(marke: str | None) -> str | None:
    """Die Marke aus der Bilderkennung auf die Schreibweise der Tabelle bringen."""
    if not marke:
        return None
    return MARKEN_ALIASSE.get(marke.casefold().strip())


def produkte_von_marke(marke: str | None) -> list[KonkurrenzProdukt]:
    """Alle bekannten Konkurrenzprodukte einer Marke."""
    normalisiert = marke_normalisiert(marke)
    if not normalisiert:
        return []
    return [p for p in produkte() if p.marke.casefold() == normalisiert.casefold()]


def finde_nach_werkzeugen(marke: str | None, erkannte_gruppen: set[str]) -> list[KonkurrenzProdukt]:
    """Die Konkurrenzprodukte, deren Werkzeugliste am besten zu den erkannten passt.

    Der Score ist die Abdeckung: Anteil der erkannten Werkzeuggruppen, die das
    Konkurrenzprodukt ebenfalls hat. Das ist bewusst konservativ - die
    Bilderkennung sieht nur, was offen liegt, also deckt ein Produkt mit
    zusaetzlichen Werkzeugen mehr Gruppen ab, ohne dass man daraus mehr ableiten kann.
    """
    if not erkannte_gruppen:
        return []
    kandidaten = produkte_von_marke(marke)
    if not kandidaten:
        return []
    bewertet = []
    for produkt in kandidaten:
        if not produkt.werkzeug_gruppen:
            continue
        gemeinsam = erkannte_gruppen & produkt.werkzeug_gruppen
        abdeckung = len(gemeinsam) / len(erkannte_gruppen)
        # Nur Produkte, deren Werkzeugliste weitgehend im Foto wiederzuerkennen ist.
        if abdeckung < 0.5:
            continue
        bewertet.append((abdeckung, produkt))
    bewertet.sort(key=lambda kv: (-kv[0], kv[1].name))
    return [p for _, p in bewertet]


def finde_besten(marke: str | None, erkannte_gruppen: set[str]) -> KonkurrenzProdukt | None:
    """Das beste passende Konkurrenzprodukt, oder None wenn es keines gibt.

    "Bestes" heisst: die Werkzeugliste deckt die im Foto erkannten Gruppen
    moeglichst vollstaendig ab und hat nicht wesentlich mehr Werkzeuge.
    """
    treffer = finde_nach_werkzeugen(marke, erkannte_gruppen)
    if not treffer:
        return None
    erkannt_anzahl = len(erkannte_gruppen)
    bestes = treffer[0]
    beste_abdeckung = len(erkannte_gruppen & bestes.werkzeug_gruppen) / erkannt_anzahl
    # Ein Produkt mit sehr viel mehr Werkzeugen passt schlechter: im Foto sind nur
    # die offenen Werkzeuge zu sehen, der Rest ist dann geraten.
    if len(bestes.werkzeug_gruppen) > erkannt_anzahl + 4:
        return None
    return bestes


def modellname_erkennen(marke: str | None, erkannte_gruppen: set[str]) -> str | None:
    """Der Name des erkannten Konkurrenzprodukts (z. B. "D03 AM"), falls eindeutig."""
    treffer = finde_nach_werkzeugen(marke, erkannte_gruppen)
    if not treffer:
        return None
    bester = treffer[0]
    if len(treffer) > 1 and treffer[1].werkzeug_gruppen == bester.werkzeug_gruppen:
        # Gleiche Werkzeugliste (z. B. Farbvarianten): erst den Namen nehmen, der
        # im Bild tatsaechlich erkannt wurde - sonst ist die Aussage unsicher.
        return bester.name
    return bester.name


def artikelnummer_aus_text(text: str) -> str | None:
    """Eine Artikelnummer aus einem Freitextfeld ziehen (z. B. "SKU KNI.0036.1010")."""
    match = re.search(r"\b([A-Z]{3}\.[0-9]{4}\.[0-9]{4}(?:\.[A-Z0-9]+)?)\b", text or "")
    return match.group(1) if match else None
