"""Bewertung der Katalogprodukte gegen die erkannten Werkzeuggruppen.

Score 0..1 pro Produkt:
- Abdeckung (Recall): Anteil der erkannten Werkzeuge, die das Produkt auch hat. Am wichtigsten,
  denn ein Ersatz soll mindestens können, was das fotografierte Messer kann.
- Präzision: Anteil der Produktwerkzeuge, die auch erkannt wurden. Zusätzliche Werkzeuge
  kosten nur wenig, weil auf einem Foto oft nicht alles sichtbar ist (z. B. Pinzette in der Schale).
- Kleiner Bonus für lieferbare Produkte; sichtbare Artikelnummer bzw. erkannter Modellname
  einer Victorinox-Ware schlagen alles andere.
"""

from app.werkzeuge import GRUPPEN

GEWICHT_ABDECKUNG = 0.65
GEWICHT_PRAEZISION = 0.30
BONUS_LIEFERBAR = 0.05
# Stecken in der Schale und sind auf Fotos selten zu sehen: zählen nicht gegen ein Produkt
SCHALENTEILE = {"pinzette", "zahnstocher", "kugelschreiber", "stecknadel"}


def produkt_gruppen(row):
    return {g.strip() for g in row.get("werkzeug_gruppen", "").split(",") if g.strip()}


def name_passt(modell, produktname):
    if not modell:
        return False
    a, b = modell.casefold().strip(), produktname.casefold().strip()
    return a == b or (len(a) >= 4 and (a in b or b in a))


def bewerte(erkannte_gruppen, row, erkannt=None, gewichte=None):
    """gewichte: optional {gruppe: Wahrscheinlichkeit}; unsichere Werkzeuge zählen dann weniger."""
    gruppen = produkt_gruppen(row)
    if not gruppen or not erkannte_gruppen:
        return None
    gemeinsam = erkannte_gruppen & gruppen
    sichtbar = gruppen - (SCHALENTEILE - erkannte_gruppen)
    if gewichte:
        w = lambda g: gewichte.get(g, 1.0)
        abdeckung = sum(map(w, gemeinsam)) / (sum(map(w, erkannte_gruppen)) or 1.0)
        # Produktwerkzeuge, die nicht erkannt wurden, zählen voll; erkannte mit ihrem Gewicht
        praezision = sum(map(w, gemeinsam)) / ((sum(map(w, gemeinsam)) + len(sichtbar - gemeinsam)) or 1.0)
    else:
        abdeckung = len(gemeinsam) / len(erkannte_gruppen)
        praezision = len(gemeinsam) / len(sichtbar) if sichtbar else 0.0
    lieferbar = row.get("lagerstatus") == "inStock"
    score = GEWICHT_ABDECKUNG * abdeckung + GEWICHT_PRAEZISION * praezision + (BONUS_LIEFERBAR if lieferbar else 0)

    gruende = []
    fehlend = erkannte_gruppen - gruppen
    zusaetzlich = gruppen - erkannte_gruppen
    if not fehlend:
        gruende.append(f"Alle {len(erkannte_gruppen)} erkannten Werkzeuge vorhanden")
    else:
        gruende.append(f"{len(gemeinsam)} von {len(erkannte_gruppen)} erkannten Werkzeugen vorhanden")
    if zusaetzlich:
        gruende.append(f"{len(zusaetzlich)} zusätzliche Werkzeuge")
    if lieferbar:
        gruende.append("An Lager")

    erkannt = erkannt or {}
    marke = (erkannt.get("marke") or "").casefold()
    if erkannt.get("artikelnummer_sichtbar") and erkannt["artikelnummer_sichtbar"] in (
            row["artikelnummer"], *row.get("varianten_artikelnummern", "").replace(" ", "").split(",")):
        score = 1.0
        gruende.insert(0, "Artikelnummer auf dem Foto erkannt")
    elif "victorinox" in marke and name_passt(erkannt.get("modell"), row["name"]):
        score = max(score, 0.95)
        gruende.insert(0, f"Modell „{erkannt['modell']}“ erkannt")

    return {
        "row": row,
        "score": round(min(score, 1.0), 4),
        "gruppen": gruppen,
        "gemeinsam": gemeinsam,
        "fehlend": fehlend,
        "zusaetzlich": zusaetzlich,
        "gruende": gruende,
    }


def rangliste(erkannte_gruppen, rows, erkannt=None, top=3, gewichte=None):
    bewertet = [b for row in rows if (b := bewerte(erkannte_gruppen, row, erkannt, gewichte))]
    bewertet.sort(key=lambda b: (-b["score"], len(b["zusaetzlich"]), b["row"]["name"]))
    return bewertet[:top]


def begruendung(b):
    labels = lambda keys: ", ".join(GRUPPEN[k][0] for k in sorted(keys))
    text = f"{b['row']['name']} deckt {len(b['gemeinsam'])} der erkannten Werkzeuge ab"
    if b["gemeinsam"]:
        text += f" ({labels(b['gemeinsam'])})"
    text += "."
    if b["fehlend"]:
        text += f" Es fehlt: {labels(b['fehlend'])}."
    if b["zusaetzlich"]:
        text += f" Zusätzlich vorhanden: {labels(b['zusaetzlich'])}."
    return text
