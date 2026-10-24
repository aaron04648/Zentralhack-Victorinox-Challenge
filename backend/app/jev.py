"""TypeSafe Jev: kalibrierte Entscheidungen auf Text (kein Bild-Input).

Jev bekommt die Textbeschreibungen der Bilderkennung und entscheidet:
1. welcher Werkzeuggruppe jede beschriebene Komponente angehört (Choice, mit Wahrscheinlichkeit),
2. ob die Top-Kandidaten sicher genug unterscheidbar sind oder nachgefragt werden muss (Noul).

Konfiguration: TYPESAFE_API_KEY, optional TYPESAFE_MODEL (Standard "jev-latest").
Ohne Key liefern die Funktionen None; der Aufrufer nutzt dann seine Regel-Fallbacks.
API: https://docs.typesafe.ai/introduction/quickstart
"""

import json
import os
import urllib.request

from app.werkzeuge import GRUPPEN

API_URL = os.getenv("TYPESAFE_API_URL", "https://api.typesafe.ai/v1/systemone")
KEINE_GRUPPE = "keine"


def aktiv():
    return bool(os.getenv("TYPESAFE_API_KEY"))


def system_one(state, questions):
    body = json.dumps({
        "state": state,
        "model": os.getenv("TYPESAFE_MODEL", "jev-latest"),
        "questions": questions,
    }).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.load(res)["answers"]


def werkzeuge_zuordnen(werkzeuge):
    """Ordnet jede Beschreibung der Bilderkennung einer Gruppe zu.

    werkzeuge: [{"gruppe", "beschreibung", "sicher"}] aus vision.erkenne
    Rückgabe: [{"gruppe", "beschreibung", "konfidenz"}] ohne "keine"-Treffer, oder None ohne Jev.
    """
    if not aktiv() or not werkzeuge:
        return None
    kriterien = {key: f"{label}: {beschreibung}" for key, (label, beschreibung) in GRUPPEN.items()}
    kriterien[KEINE_GRUPPE] = "Kein Werkzeug oder passt in keine Gruppe (z. B. Ring, Öse, Schale)"
    questions = {
        f"w{i}": {
            "type": "choice",
            "instructions": f"Zu welcher Werkzeuggruppe eines Taschenmessers gehört Komponente {i}?",
            "criteria": kriterien,
        }
        for i in range(len(werkzeuge))
    }
    state = "Komponenten, die die Bilderkennung auf dem Foto beschrieben hat:\n" + "\n".join(
        f"{i}: {w['beschreibung'] or GRUPPEN[w['gruppe']][0]} (Vorschlag Bilderkennung: {w['gruppe']})"
        for i, w in enumerate(werkzeuge)
    )
    antworten = system_one(state, questions)
    result = []
    for i, w in enumerate(werkzeuge):
        a = antworten.get(f"w{i}") or {}
        if a.get("choice") and a["choice"] != KEINE_GRUPPE:
            result.append({"gruppe": a["choice"], "beschreibung": w["beschreibung"],
                           "konfidenz": float(a.get("confidence") or 0)})
    return result


def rueckfrage_noetig(erkannt, kandidaten):
    """Wahrscheinlichkeit (0..1), dass die Top-Kandidaten nicht sicher unterscheidbar sind; None ohne Jev."""
    if not aktiv() or not kandidaten:
        return None
    state = {
        "erkannt": {
            "marke": erkannt.get("marke"),
            "modell": erkannt.get("modell"),
            "werkzeuge": [GRUPPEN[w["gruppe"]][0] for w in erkannt["werkzeuge"]],
            "messer_geoeffnet": erkannt.get("geoeffnet"),
        },
        "kandidaten": [
            {"name": k["produkt"]["name"], "score": round(k["score"], 3),
             "werkzeuge": [GRUPPEN[g][0] for g in sorted(k["gruppen"])]}
            for k in kandidaten[:3]
        ],
    }
    antworten = system_one(json.dumps(state, ensure_ascii=False), {
        "unklar": {
            "type": "noul",
            "instructions": "Die erkannten Merkmale reichen nicht aus, um den besten Kandidaten "
                            "sicher von den anderen zu unterscheiden; ein weiteres Foto wäre nötig.",
        },
    })
    return float((antworten.get("unklar") or {}).get("noul") or 0)
