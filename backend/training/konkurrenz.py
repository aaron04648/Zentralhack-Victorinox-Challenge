"""Trainingsdaten von Konkurrenzmarken (aktuell: SWIZA, Shopify-Shop swiza.com).

Pro Messer: Produktbilder und die Werkzeuge aus dem Feld "tools_description" der
Produktseite, übersetzt in die Werkzeuggruppen aus app/werkzeuge.py. Auf manchen Seiten ist
die Liste abgeschnitten (z. B. fehlen bei "D03 AM HEIMAT" Klinge und Kapselheber); Messer,
deren Liste keine Klinge nennt, werden deshalb als unvollständig verworfen.

Ausgabe: data/training/konkurrenz.csv (nur fürs Training, nicht für den Test)
Aufruf:  python -m training.konkurrenz
"""

import csv
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "training" / "konkurrenz.csv"
SHOP = "https://swiza.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/130.0 (ZentralHack training)"}
PAUSE_S = 1.5  # höflich bleiben, Shopify drosselt schnell
MAX_BILDER = 3

# Englische Werkzeugnamen -> Gruppen-Keys (erste passende Regel je Teilstück gewinnt)
REGELN = [
    (r"serrated", "klinge_wellenschliff"),
    (r"scissor", "schere"),
    (r"corkscrew", "korkenzieher"),
    (r"awl|reamer", "ahle"),
    (r"can opener", "dosenoeffner"),
    (r"bottle opener|cap lifter", "kapselheber"),
    (r"phillips|cross", "schraubendreher_kreuz"),
    (r"bit", "bits"),
    (r"wire|stripper", "drahtwerkzeug"),
    (r"tweezer", "pinzette"),
    (r"toothpick", "zahnstocher"),
    (r"wood saw|saw", "holzsaege"),
    (r"nail file|file", "nagelfeile"),
    (r"plier", "zange"),
    (r"hook", "mehrzweckhaken"),
    (r"scaler|fish", "fischentschupper"),
    (r"ruler|scale \(cm", "massstab"),
    (r"pen\b|ballpoint", "kugelschreiber"),
    (r"led|light", "led"),
    (r"magnif", "lupe"),
    (r"chisel", "holzmeissel"),
    (r"small blade", "klinge_klein"),
]
# Zusätzlich zu obigem: ein Schraubendreher steckt oft im Dosen-/Kapselöffner
SCHRAUBENDREHER = re.compile(r"screwdriver|screw driver", re.I)


def get(url):
    for versuch in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.read().decode("utf-8")
        except urllib.error.HTTPError as fehler:
            if fehler.code != 429 or versuch == 3:
                raise
            time.sleep(20 * (versuch + 1))


def vollstaendig(text):
    return re.search(r"\bblade\b", text, re.I) is not None


def gruppen_aus_text(text):
    result = {"klinge_gross"}
    for teil in re.split(r",|;|/|&|\n| and ", text):
        teil = teil.strip().lower()
        for muster, key in REGELN:
            if re.search(muster, teil):
                result.add(key)
                break
        if SCHRAUBENDREHER.search(teil) and "phillips" not in teil:
            result.add("schraubendreher_flach")
    return result


def feld(seite, name):
    m = re.search(r'"%s"\s*:\s*"((?:[^"\\]|\\.)*)"' % name, seite)
    return html.unescape(json.loads(f'"{m.group(1)}"')) if m else ""


def main():
    produkte, page = [], 1
    while True:
        teil = json.loads(get(f"{SHOP}/products.json?limit=250&page={page}"))["products"]
        produkte += teil
        if len(teil) < 250:
            break
        page += 1
    messer = [p for p in produkte if any((v.get("sku") or "").startswith("KN") for v in p["variants"])]
    print(f"  {len(messer)} Messer von {len(produkte)} Produkten", file=sys.stderr)

    rows = []
    for i, p in enumerate(messer, 1):
        time.sleep(PAUSE_S)
        tools = feld(get(f"{SHOP}/products/{p['handle']}"), "tools_description")
        print(f"\r  {i}/{len(messer)} {p['title'][:40]:40}", end="", file=sys.stderr)
        if not tools or not vollstaendig(tools):
            continue
        # Produktfotos sind aufgeklappt mit sichtbaren Werkzeugen; einheitlich 768 px
        bilder = [img["src"].split("?")[0] + "?width=768&format=pjpg" for img in p["images"][:MAX_BILDER]]
        rows.append({
            "quelle": "swiza.com",
            "marke": "SWIZA",
            "artikelnummer": p["variants"][0].get("sku") or p["handle"],
            "name": p["title"],
            "werkzeuge_text": tools,
            "werkzeug_gruppen": ", ".join(sorted(gruppen_aus_text(tools))),
            "bild_urls": " ".join(bilder),
            "url": f"{SHOP}/products/{p['handle']}",
        })
    print(file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} Messer mit vollständigen Werkzeugangaben -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
