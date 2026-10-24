"""Gemeinsame Helfer für die Katalog-Importe: Textbausteine mit Position/Schrift und JSON-Ausgabe."""

import json
import re
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
KATALOGE_PDF = REPO / "catalogues"
KATALOGE_JSON = REPO / "backend" / "data" / "kataloge"


def text(s):
    """Unsichtbare und geschützte Leerzeichen aus PDF-Texten entfernen."""
    return re.sub(r"[​  ]", "", s.replace("\xa0", " ")).strip()


def spans(page):
    """Alle Textbausteine einer Seite: Text, Position, Schrift, Grösse, Farbe."""
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for s in line["spans"]:
                t = text(s["text"])
                if t:
                    out.append({"t": t, "x": s["bbox"][0], "y": s["bbox"][1], "x1": s["bbox"][2],
                                "font": s["font"], "size": round(s["size"], 1), "color": s["color"]})
    return out


def zahl(wert):
    """'91' -> 91, '3.4' -> 3.4, sonst None."""
    try:
        f = float(str(wert).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else f


def schreibe(produkte, datei, **kopf):
    """Ein Produkt pro Zeile: kompakt und in Git-Diffs pro Produkt lesbar."""
    KATALOGE_JSON.mkdir(parents=True, exist_ok=True)
    pfad = KATALOGE_JSON / datei
    kopf = {**kopf, "extrahiert_am": date.today().isoformat(), "anzahl": len(produkte)}
    head = json.dumps(kopf, ensure_ascii=False, indent=2)[:-2]
    zeilen = ",\n".join("    " + json.dumps(p, ensure_ascii=False) for p in produkte)
    pfad.write_text(f'{head},\n  "produkte": [\n{zeilen}\n  ]\n}}\n', encoding="utf-8")
    return pfad
