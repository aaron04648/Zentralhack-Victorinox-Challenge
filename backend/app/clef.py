"""Bilderkennung mit Cloudflare Clef (Entscheidungsmodell, multimodal) über OpenRouter.

Clef schreibt keinen Text, sondern beantwortet typisierte Fragen mit Wahrscheinlichkeiten.
Pro Foto wird gefragt:
- je Werkzeuggruppe ein "noul" (ja/nein): Ist dieses Werkzeug zu sehen?
- "choice" Marke, mit sichtbaren Merkmalen je Option (wie in docs/classification_recommendation.md)
- "noul" ist es überhaupt ein Taschenmesser/Multitool?

Ab welcher Wahrscheinlichkeit ein Werkzeug als erkannt gilt, ist pro Gruppe aus den
Trainingsbildern gelernt (training/clef_kalibrieren.py -> data/training/clef_schwellen.json),
weil Clefs Wahrscheinlichkeiten nur schwach kalibriert sind.

Konfiguration: OPENROUTER_API_KEY, optional CLEF_MODEL (Standard cloudflare/clef-flash),
CLEF_SCHWELLE (Fallback-Schwelle, Standard 0.5).
Endpoint und Bildformat: siehe tools/clef_client.py (Bilder nur eingebettet, max. 4 MiB).
"""

import base64
import hashlib
import io
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

from app.werkzeuge import GRUPPEN

API_URL = "https://openrouter.ai/api/alpha/decisions"
SCHWELLEN = Path(__file__).resolve().parent.parent / "data" / "training" / "clef_schwellen.json"
MAX_SEITE_PX = 768          # 32x32 px pro Token, 1024 Tokens pro Bild max.
FRAGEN_PRO_ANFRAGE = 12     # Werkzeugfragen werden in parallelen Paketen gestellt


class ClefNichtKonfiguriert(RuntimeError):
    pass


# Gruppe -> englische Beschreibung des sichtbaren Werkzeugs (Clef ist englisch-zentriert)
WERKZEUG_EN = {
    "klinge_gross": "a large main knife blade with a plain (smooth) edge",
    "klinge_klein": "a second, clearly shorter small knife blade",
    "klinge_wellenschliff": "a knife blade with a serrated (wavy, toothed) edge",
    "klinge_spezial": "a special blade: hook blade, curved blade, skinning blade or cable blade",
    "schere": "a small pair of scissors with a spring",
    "holzsaege": "a wood saw blade with large coarse teeth",
    "metallsaege": "a metal saw with very fine teeth",
    "metallfeile": "a metal file with a cross-hatched rasp surface",
    "nagelfeile": "a narrow nail file, often with a nail cleaner tip",
    "korkenzieher": "a spiral corkscrew",
    "dosenoeffner": "a hook-shaped can opener",
    "kapselheber": "a bottle opener (cap lifter) with a notch",
    "schraubendreher_flach": "a flat slotted screwdriver tip",
    "schraubendreher_kreuz": "a Phillips (cross-head) screwdriver tip",
    "mini_schraubendreher": "a tiny mini screwdriver",
    "ahle": "a pointed awl / reamer, possibly with a sewing eye",
    "zange": "pliers (combination or needle-nose pliers)",
    "pinzette": "tweezers",
    "zahnstocher": "a plastic toothpick",
    "kugelschreiber": "a ballpoint pen",
    "stecknadel": "a straight pin",
    "lupe": "a small magnifying glass lens",
    "led": "a built-in LED light",
    "massstab": "a ruler scale in cm or inches",
    "mehrzweckhaken": "a multi-purpose hook for carrying parcels",
    "fischentschupper": "a fish scaler with hook disgorger",
    "holzmeissel": "a wood chisel / scraper",
    "kistenoeffner": "a crate or parcel opener lever",
    "bits": "a bit holder or interchangeable screwdriver bits",
    "nagelpflege": "a nail clipper or cuticle pusher",
    "trageclip": "a pocket clip or belt clip",
    "drahtwerkzeug": "a wire stripper, wire bender or cable cutter notch",
}
assert set(WERKZEUG_EN) == set(GRUPPEN), "WERKZEUG_EN muss alle Gruppen abdecken"

# Option -> (Markenname für die API-Antwort, sichtbare Merkmale)
#
# Die Kriterien beschreiben, was *im Foto* zu sehen ist (Form des Emblems, Schalenfarbe,
# Prägung), nicht den Markennamen allein - sonst kann das Modell die Marke nicht
# unterscheiden. Gemessen auf den 12 Referenzfotos + dem SWIZA D03 (siehe
# tools/eval_marke_real.py): top-1 9/13.
#
# Wichtig: Victorinox und SWIZA tragen beide ein Kreuz. Der Unterschied ist die Form:
# Victorinox = Kreuz in einem Schild mit spitzen Schultern, SWIZA = Kreuz in einem
# runden Kreis bzw. abgerundetem Quadrat.
MARKEN = {
    "victorinox": ("Victorinox", "Victorinox Swiss Army Knife: a white cross inside a shield OUTLINE "
                                  "that has pointed shoulders and a flat bottom, brand name VICTORINOX "
                                  "usually printed on the scale or the blade"),
    "swiza": ("SWIZA", "SWIZA Swiss Army Knife: a white cross inside a plain CIRCLE badge, or a cross in "
                       "a rounded square, on a smooth black or coloured handle, brand name SWIZA printed "
                       "in block capitals on the blade or handle"),
    "wenger": ("Wenger", "Wenger Swiss Army Knife: a white cross in a rounded square, usually on red "
                          "scales, the name WENGER printed on the blade"),
    "leatherman": ("Leatherman", "Leatherman multitool: plier-based folding tool with solid stainless "
                                 "steel handles, no logo emblem"),
    "gerber": ("Gerber", "Gerber multitool or folding knife: the name GERBER printed on the blade or handle"),
    "roxon": ("Roxon", "ROXON Swiss Army Knife: black handle with a slender parallel metal frame, the name "
                        "ROXON printed in white capitals on the handle or blade"),
    "helton": ("The Helton", "The Helton Swiss Army Knife: plain black textured handle with no logo and no "
                             "lettering, narrow plain blade"),
    # "unclear" ist die Abstention-Option: das Modell soll ein Foto, auf dem sich keine
    # Marke sicher feststellen laesst, hier abgeben und nicht raten.
    "unclear": (None, "unclear: no logo and no lettering is readable, or the knife does not match any of "
                      "the brands above"),
    "andere": (None, "another or unknown brand, no readable logo or lettering"),
}


def aktiv():
    return bool(os.getenv("OPENROUTER_API_KEY"))


def modell():
    return os.getenv("CLEF_MODEL", "cloudflare/clef-flash")


@lru_cache
def schwellen():
    standard = float(os.getenv("CLEF_SCHWELLE", "0.5"))
    gelernt = json.loads(SCHWELLEN.read_text(encoding="utf-8")) if SCHWELLEN.exists() else {}
    return {g: float(gelernt.get(g, standard)) for g in GRUPPEN}, bool(gelernt)


def bild_vorbereiten(bild_url):
    """http(s)- oder data:-URL -> verkleinertes JPEG als data:-URL (Clef nimmt keine URLs)."""
    from PIL import Image

    if bild_url.startswith("data:"):
        daten = base64.b64decode(bild_url.split(",", 1)[1])
    else:
        req = urllib.request.Request(bild_url, headers={"User-Agent": "Mozilla/5.0 (ZentralHack)"})
        with urllib.request.urlopen(req, timeout=30) as res:
            daten = res.read()
    img = Image.open(io.BytesIO(daten))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        hintergrund = Image.new("RGB", img.size, (255, 255, 255))
        hintergrund.paste(img, mask=img.split()[-1])  # transparente Packshots auf Weiss
        img = hintergrund
    img = img.convert("RGB")
    img.thumbnail((MAX_SEITE_PX, MAX_SEITE_PX))
    puffer = io.BytesIO()
    img.save(puffer, "JPEG", quality=85)
    return f"data:image/jpeg;base64,{base64.b64encode(puffer.getvalue()).decode()}"


def entscheide(state, questions):
    if not aktiv():
        raise ClefNichtKonfiguriert("Kein OPENROUTER_API_KEY in .env gesetzt (für Clef)")
    daten = {"model": modell(), "state": state, "questions": questions}
    if any(teil.get("type") == "image_url" for teil in state):
        # Nur Cloudflare nimmt Bilder an; OpenRouter routet sonst teils zu DeepInfra/PrimeIntellect
        # ("does not accept image_url parts in state")
        daten["provider"] = {"only": ["cloudflare"]}
    body = json.dumps(daten).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost",
        "X-Title": "victorinox-product-match",
    })
    for versuch in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                return json.load(res).get("answers") or {}
        except urllib.error.HTTPError as fehler:
            text = fehler.read().decode(errors="replace")[:300]
            if fehler.code in (429, 500, 502, 503) and versuch < 3:
                time.sleep(2 ** versuch)
                continue
            raise RuntimeError(f"Clef {fehler.code}: {text}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            # Endpoint setzt laut Simons Messungen gelegentlich die Verbindung zurück
            if versuch == 3:
                raise
            time.sleep(2 ** versuch)


def _noul(text):
    return {"type": "noul", "instructions": text,
            "criteria": {"true": "yes, clearly visible", "false": "no, not visible"}}


def messer_sichtbar(bild_data_url):
    """Eine schnelle Clef-Frage für den Auto-Auslöser der Kamera: Wahrscheinlichkeit, dass ein Messer zu sehen ist."""
    state = [{"type": "text", "text": "Live camera frame:"},
             {"type": "image_url", "image_url": {"url": bild_data_url}}]
    antwort = entscheide(state, {"messer": _noul(
        "Is a pocket knife, folding knife or multitool clearly visible in this camera frame? "
        "Answer no for an empty background, a face, hands only, a phone or any other object.")})
    return float((antwort.get("messer") or {}).get("noul") or 0)


def wahrscheinlichkeiten(bild_data_url):
    """Alle Rohwahrscheinlichkeiten für ein Bild: {"werkzeuge": {gruppe: p}, "marke": {..}, "messer": p}."""
    state = [{"type": "text", "text": "Product photo of a pocket knife or multitool:"},
             {"type": "image_url", "image_url": {"url": bild_data_url}}]
    pakete = [list(WERKZEUG_EN)[i:i + FRAGEN_PRO_ANFRAGE] for i in range(0, len(WERKZEUG_EN), FRAGEN_PRO_ANFRAGE)]
    fragen = [{g: _noul(f"Does this knife have {WERKZEUG_EN[g]} visible in the photo?") for g in paket}
              for paket in pakete]
    fragen[0]["messer"] = _noul("Is this a pocket knife or multitool?")
    # Die Markenfrage kommt in eine eigene Anfrage: mit den 12 Werkzeugfragen im selben
    # Paket teilt sich die Wahrscheinlichkeitsmasse, und die Marke wird schlechter erkannt
    # (gemessen: 9/13 top-1 allein, 8/12 gebündelt).
    marken_frage = {"marke": {"type": "choice", "instructions": "Which brand is this pocket knife?",
                              "criteria": {k: v[1] for k, v in MARKEN.items()}}}
    with ThreadPoolExecutor(len(fragen) + 1) as pool:
        antworten = {}
        for teil in pool.map(lambda q: entscheide(state, q), [*fragen, marken_frage]):
            antworten.update(teil)
    marke = antworten.get("marke") or {}
    return {
        "werkzeuge": {g: float((antworten.get(g) or {}).get("noul") or 0) for g in WERKZEUG_EN},
        "marke": {k: float(v) for k, v in (marke.get("probabilities") or {}).items()},
        "marke_konfidenz": float(marke.get("confidence") or 0),
        "messer": float((antworten.get("messer") or {}).get("noul") or 0),
    }


def auswerten(roh):
    """Rohwahrscheinlichkeiten -> Erkennungsergebnis im Format von vision.erkenne."""
    grenzen, _ = schwellen()
    werkzeuge = [
        {"gruppe": g, "beschreibung": GRUPPEN[g][0], "sicher": p >= min(grenzen[g] + 0.2, 0.95),
         "wahrscheinlichkeit": round(p, 3)}
        for g, p in sorted(roh["werkzeuge"].items(), key=lambda kv: -kv[1]) if p >= grenzen[g]
    ]
    marken = roh["marke"]
    # "unclear"/"andere" sind Abstentions-Optionen: gewinnt eine davon, ist die Marke
    # nicht bestimmbar und wird als None gemeldet.
    beste = max(marken, key=marken.get) if marken else "andere"
    abstention = beste in ("unclear", "andere")
    werte = sorted(marken.values(), reverse=True) + [0, 0]
    # Konfidenz: hoechster Wert, aber nur so hoch, wie die Unterscheidung zwischen den
    # beiden besten Marken traegt. So faellt ein Foto, das keine Marke sicher zeigt
    # (Kandidat "unclear"), auf eine tiefe Konfidenz und loest eine Rueckfrage aus,
    # statt eine falsche Marke zu behaupten.
    if abstention:
        konfidenz = 0.0
    else:
        konfidenz = min(werte[0], max(werte[0] - werte[1], 0.0) + 0.5 * werte[0])
    return {
        "ist_taschenmesser": roh["messer"] >= 0.5,
        "marke": None if abstention else MARKEN.get(beste, (None,))[0],
        "marke_wahrscheinlichkeiten": {k: round(v, 3) for k, v in marken.items()},
        "modell": None,
        "artikelnummer_sichtbar": None,
        "geoeffnet": bool(werkzeuge),
        "werkzeuge": werkzeuge,
        "konfidenz": round(konfidenz, 3),
    }


def erkenne(bild_url):
    if not aktiv():
        raise ClefNichtKonfiguriert("Kein OPENROUTER_API_KEY in .env gesetzt (für Clef)")
    bild = bild_vorbereiten(bild_url)
    ergebnis = auswerten(wahrscheinlichkeiten(bild))
    _, kalibriert = schwellen()
    ergebnis["modell_info"] = {"modell": modell(), "art": "kalibrierte Schwellen" if kalibriert else "Standardschwelle"}
    ergebnis["_bild"] = bild  # für die Kandidatenauswahl, wird nicht ausgeliefert
    return ergebnis


# --- Visuelle Katalogsuche ---------------------------------------------------------------
# Clef nimmt höchstens 4 Bilder pro Anfrage. Darum werden die Katalogbilder zu beschrifteten
# 3x3-Rastern zusammengesetzt (27 Produkte pro Anfrage + Kundenfoto) und in Turnierrunden
# verglichen: Die besten 3 je Anfrage kommen weiter, bis eine Runde alle Finalisten fasst.
# Zwei Turniere mit unterschiedlicher Reihenfolge, deren Finalwahrscheinlichkeiten addiert
# werden, sind deutlich stabiler als eines (Clef bevorzugt sonst je nach Position).
KACHELN = Path(__file__).resolve().parent.parent / "data" / "katalog_kacheln"
KACHEL_PX = 320
RASTER = 3                  # 3x3 Kacheln pro Rasterbild (1024 px, Clef-Maximum)
RASTER_PRO_ANFRAGE = 3      # + Kundenfoto = 4 Bilder
WEITER_PRO_RUNDE = 3


def _kachel(row):
    """Katalogbild verkleinert, auf Platte gecacht (einmalig ca. 180 Downloads)."""
    pfad = KACHELN / f"{row['artikelnummer']}.jpg"
    if not pfad.exists():
        from PIL import Image

        KACHELN.mkdir(parents=True, exist_ok=True)
        url = row["bild_url"]
        if "imageengine.victorinox.com" in url:  # Victorinox-CDN: verkleinert und als JPEG ausliefern
            url += "?io=transform:fill,width:768&format=jpg"
        req = urllib.request.Request(url,
                                     headers={"User-Agent": "Mozilla/5.0 (ZentralHack)"})
        with urllib.request.urlopen(req, timeout=30) as res:
            img = Image.open(io.BytesIO(res.read())).convert("RGB")
        img.thumbnail((KACHEL_PX, KACHEL_PX))
        img.save(pfad, "JPEG", quality=80)
    return pfad


def kacheln_vorbereiten(rows):
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(_kachel, [r for r in rows if r.get("bild_url")]))


def _raster(rows, buchstabe):
    from PIL import Image, ImageDraw, ImageFont

    t = 1024 // RASTER
    img = Image.new("RGB", (t * RASTER, t * RASTER), "white")
    zeichnen = ImageDraw.Draw(img)
    schrift = ImageFont.load_default(size=t // 7)
    for i, row in enumerate(rows):
        kachel = Image.open(_kachel(row))
        kachel.thumbnail((t - 8, t - 8))
        x, y = (i % RASTER) * t, (i // RASTER) * t
        img.paste(kachel, (x + 4, y + 4))
        zeichnen.rectangle([x, y, x + t - 1, y + t - 1], outline="black", width=2)
        zeichnen.text((x + 8, y + 6), f"{buchstabe}{i + 1}", fill="blue", font=schrift)
    puffer = io.BytesIO()
    img.save(puffer, "JPEG", quality=85)
    return f"data:image/jpeg;base64,{base64.b64encode(puffer.getvalue()).decode()}"


class Abgebrochen(Exception):
    """Die Bildsuche wurde abgebrochen (z. B. weil eine fremde Marke erkannt wurde)."""


def _runde(bild_data_url, rows):
    """Eine Clef-Anfrage: welches der bis zu 27 Katalogbilder zeigt dasselbe Modell? -> {artikelnummer: p}"""
    pro_raster = RASTER * RASTER
    state = [{"type": "text", "text": "CUSTOMER PHOTO of a pocket knife (any angle, maybe open or closed):"},
             {"type": "image_url", "image_url": {"url": bild_data_url}},
             {"type": "text", "text": "Catalogue sheets follow. Each tile shows one candidate product and is "
                                      "labelled with its id in blue (e.g. A1)."}]
    ids = {}
    for b, start in zip("ABC", range(0, len(rows), pro_raster)):
        teil = rows[start:start + pro_raster]
        state += [{"type": "text", "text": f"Sheet {b}:"},
                  {"type": "image_url", "image_url": {"url": _raster(teil, b)}}]
        ids.update({f"{b}{i + 1}": row for i, row in enumerate(teil)})
    antwort = entscheide(state, {"produkt": {
        "type": "choice",
        "instructions": "Which catalogue tile shows the same knife model as the customer photo? "
                        "Compare handle colour and material, size, number and type of tools.",
        "criteria": {i: f"catalogue tile {i}" for i in ids},
    }}).get("produkt") or {}
    p = antwort.get("probabilities") or {}
    return {row["artikelnummer"]: float(p.get(i, 0)) for i, row in ids.items()}


def _turnier(bild_data_url, rows, melde=lambda runde, vorher, nachher: None, abbruch=None):
    pro_anfrage = RASTER * RASTER * RASTER_PRO_ANFRAGE

    def pruefen():
        if abbruch is not None and abbruch.is_set():
            raise Abgebrochen()

    runde = 1
    with ThreadPoolExecutor(8) as pool:
        while len(rows) > pro_anfrage:
            pruefen()
            gruppen = [rows[i:i + pro_anfrage] for i in range(0, len(rows), pro_anfrage)]
            nach_nummer = {r["artikelnummer"]: r for r in rows}
            vorher = len(rows)
            rows = [nach_nummer[n] for e in pool.map(lambda g: _runde(bild_data_url, g), gruppen)
                    for n in sorted(e, key=e.get, reverse=True)[:WEITER_PRO_RUNDE]]
            melde(runde, vorher, len(rows))
            runde += 1
    pruefen()
    ergebnis = _runde(bild_data_url, rows)
    melde(runde, len(rows), 0)
    return ergebnis


def visuell_suchen(bild_data_url, rows, fortschritt=None, abbruch=None):
    """Kundenfoto gegen alle Katalogbilder -> [(artikelnummer, Wahrscheinlichkeit)], beste zuerst.

    fortschritt: optional fortschritt(text), wird nach jeder Turnierrunde aufgerufen (Live-Ablauf).
    abbruch: optional threading.Event; ist es gesetzt, endet die Suche vor der nächsten Runde mit Abgebrochen.

    Auf zurückgehaltenen Katalogansichten und den Kundenfotos deutlich besser als das
    Werkzeug-Matching (siehe README, training/evaluieren.py --bildwahl).
    """
    rows = [r for r in rows if r.get("bild_url")]
    gemischt = sorted(rows, key=lambda r: hashlib.md5(r["artikelnummer"].encode()).hexdigest())
    def melder(durchgang):
        def melde(runde, vorher, nachher):
            if fortschritt:
                fortschritt(f"Durchgang {durchgang}, Runde {runde}: {vorher} Katalogbilder → "
                            + (f"{nachher} weiter" if nachher else "Finale entschieden"))
        return melde

    with ThreadPoolExecutor(2) as pool:
        ergebnisse = list(pool.map(lambda args: _turnier(bild_data_url, args[0], melder(args[1]), abbruch),
                                   [(rows, 1), (gemischt, 2)]))
    summe = {}
    for e in ergebnisse:
        for n, p in e.items():
            summe[n] = summe.get(n, 0.0) + p / len(ergebnisse)
    return sorted(summe.items(), key=lambda kv: -kv[1])


def modell_waehlen(bild_data_url, kandidaten):
    """Eine Clef-Anfrage: welcher der (höchstens 27) Kandidaten einer Marke ist auf dem Foto?

    kandidaten: [{"artikelnummer": schluessel, "bild_url": ...}] -> {schluessel: Wahrscheinlichkeit}
    """
    if not kandidaten:
        return {}
    return _runde(bild_data_url, kandidaten[:RASTER * RASTER * RASTER_PRO_ANFRAGE])


# --- Röntgenblick: Wo auf dem Foto ist welches Werkzeug? ------------------------------------
# Clef liefert keine Koordinaten. Darum wird ein beschriftetes Raster über das Foto gelegt und
# pro Werkzeug gefragt, in welcher Zelle es liegt. Die Position ist der mit Clefs
# Wahrscheinlichkeiten gewichtete Mittelpunkt der Zellen.
ORT_RASTER = 4              # 4x4 Zellen, Spalten A-D, Zeilen 1-4
ORT_MAX_WERKZEUGE = 12


def _ort_raster(bild_data_url):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(io.BytesIO(base64.b64decode(bild_data_url.split(",", 1)[1]))).convert("RGB")
    zeichnen = ImageDraw.Draw(img, "RGBA")
    b, h = img.size
    schrift = ImageFont.load_default(size=max(min(b, h) // 18, 12))
    for i in range(1, ORT_RASTER):
        zeichnen.line([(b * i / ORT_RASTER, 0), (b * i / ORT_RASTER, h)], fill=(0, 90, 255, 170), width=2)
        zeichnen.line([(0, h * i / ORT_RASTER), (b, h * i / ORT_RASTER)], fill=(0, 90, 255, 170), width=2)
    for s in range(ORT_RASTER):
        for z in range(ORT_RASTER):
            zeichnen.text((b * s / ORT_RASTER + 4, h * z / ORT_RASTER + 2), f"{'ABCD'[s]}{z + 1}",
                          fill=(0, 90, 255, 230), font=schrift)
    puffer = io.BytesIO()
    img.save(puffer, "JPEG", quality=85)
    return f"data:image/jpeg;base64,{base64.b64encode(puffer.getvalue()).decode()}"


def lokalisieren(bild_data_url, gruppen):
    """-> {gruppe: {"x": 0..1, "y": 0..1, "sicherheit": 0..1}} für die übergebenen Werkzeuge."""
    gruppen = [g for g in gruppen if g in WERKZEUG_EN][:ORT_MAX_WERKZEUGE]
    if not gruppen:
        return {}
    zellen = {f"{'ABCD'[s]}{z + 1}": ((s + 0.5) / ORT_RASTER, (z + 0.5) / ORT_RASTER)
              for s in range(ORT_RASTER) for z in range(ORT_RASTER)}
    state = [{"type": "text", "text": "Photo of a pocket knife with a labelled blue grid "
                                      "(columns A-D left to right, rows 1-4 top to bottom):"},
             {"type": "image_url", "image_url": {"url": _ort_raster(bild_data_url)}}]
    fragen = {g: {"type": "choice",
                  "instructions": f"In which grid cell is the tip or most visible part of {WERKZEUG_EN[g]}?",
                  "criteria": {zelle: f"grid cell {zelle}" for zelle in zellen}} for g in gruppen}
    pakete = [dict(list(fragen.items())[i:i + FRAGEN_PRO_ANFRAGE]) for i in range(0, len(fragen), FRAGEN_PRO_ANFRAGE)]
    with ThreadPoolExecutor(len(pakete)) as pool:
        antworten = {}
        for teil in pool.map(lambda q: entscheide(state, q), pakete):
            antworten.update(teil)
    orte = {}
    for g in gruppen:
        p = (antworten.get(g) or {}).get("probabilities") or {}
        if not any(p.get(z) for z in zellen):
            continue
        # Nur um die wahrscheinlichste Zelle mitteln: bei unsicheren Antworten zöge der Mittelwert
        # über alle Zellen den Punkt sonst in die Bildmitte
        beste = max(zellen, key=lambda z: p.get(z, 0))
        nachbarn = [z for z in zellen if abs(zellen[z][0] - zellen[beste][0]) <= 1.01 / ORT_RASTER
                    and abs(zellen[z][1] - zellen[beste][1]) <= 1.01 / ORT_RASTER]
        summe = sum(p.get(z, 0) for z in nachbarn)
        orte[g] = {"x": round(sum(zellen[z][0] * p.get(z, 0) for z in nachbarn) / summe, 3),
                   "y": round(sum(zellen[z][1] * p.get(z, 0) for z in nachbarn) / summe, 3),
                   "sicherheit": round(p[beste], 2)}
    return orte
