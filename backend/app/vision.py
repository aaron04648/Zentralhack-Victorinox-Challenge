"""Bilderkennung: Werkzeuge, Marke und Modell eines Taschenmessers aus einem Foto.

Anbieter (VISION_ANBIETER): "clef" (Standard, sobald OPENROUTER_API_KEY gesetzt ist, siehe
app/clef.py) oder "openai". Der OpenAI-Weg nutzt eine OpenAI-kompatible API:
- Azure OpenAI: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT
- OpenAI:       OPENAI_API_KEY, OPENAI_MODEL

Ist ein fine-getuntes Modell konfiguriert (VISION_FT_DEPLOYMENT), wird es ohne
Beispielbilder aufgerufen. Sonst bekommt das Basismodell Referenzbilder mit
bekannten Werkzeugen als Beispiele (Few-Shot, data/training/referenzen.json).
Training (training/finetune.py) und Inferenz nutzen dieselben Nachrichten,
damit das fine-getunte Modell genau das gelernte Format sieht.
"""

import base64
import json
import os
from functools import lru_cache
from pathlib import Path

from app import clef
from app.werkzeuge import GRUPPEN

REFERENZEN = Path(__file__).resolve().parent.parent / "data" / "training" / "referenzen.json"
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")


class VisionNichtKonfiguriert(RuntimeError):
    pass


SYSTEM_PROMPT = (
    "Du bist Produktexperte für Taschenmesser und Multitools aller Marken. "
    "Du bekommst ein Foto und bestimmst die sichtbaren Werkzeuge, die Marke und wenn möglich das Modell. "
    "Verwende für Werkzeuge ausschliesslich diese Gruppen-Keys:\n"
    + "\n".join(f"- {key}: {label} ({beschreibung})" for key, (label, beschreibung) in GRUPPEN.items())
    + "\n\nRegeln: Nur Werkzeuge angeben, die auf dem Foto zu sehen oder eindeutig erkennbar sind. "
    "Kombinierte Werkzeuge einzeln angeben (z. B. Kapselheber mit Schraubendreher = "
    "kapselheber + schraubendreher_flach). Pinzette und Zahnstocher nur, wenn sichtbar. "
    "Nichts erfinden; Unsicheres mit \"sicher\": false markieren.\n"
    "Antworte nur mit JSON in genau diesem Format:\n"
    '{"ist_taschenmesser": true, "marke": "Victorinox" | null, "modell": "Spartan" | null, '
    '"artikelnummer_sichtbar": null, "geoeffnet": true, '
    '"werkzeuge": [{"gruppe": "<key>", "beschreibung": "<was du siehst>", "sicher": true}], '
    '"konfidenz": 0.0}'
)
USER_PROMPT = "Welche Werkzeuge hat dieses Messer? Marke und Modell?"


def bild_als_url(bild: bytes, mime="image/jpeg"):
    return f"data:{mime};base64,{base64.b64encode(bild).decode()}"


def antwort_fuer(werkzeug_gruppen, marke=None, modell=None):
    """Zielantwort für ein Trainings- oder Referenzbild mit bekannten Werkzeugen."""
    return json.dumps({
        "ist_taschenmesser": True,
        "marke": marke,
        "modell": modell,
        "artikelnummer_sichtbar": None,
        "geoeffnet": True,
        "werkzeuge": [
            {"gruppe": key, "beschreibung": GRUPPEN[key][0], "sicher": True}
            for key in sorted(werkzeug_gruppen) if key in GRUPPEN
        ],
        "konfidenz": 1.0,
    }, ensure_ascii=False)


def bild_nachricht(bild_url):
    return {"role": "user", "content": [
        {"type": "text", "text": USER_PROMPT},
        {"type": "image_url", "image_url": {"url": bild_url}},
    ]}


def nachrichten(bild_url, beispiele=()):
    """System-Prompt, optionale Beispiele (Bild -> Antwort) und das zu prüfende Bild."""
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for beispiel in beispiele:
        msgs.append(bild_nachricht(beispiel["bild_url"]))
        msgs.append({"role": "assistant", "content": antwort_fuer(
            beispiel["werkzeug_gruppen"], beispiel.get("marke"), beispiel.get("modell"))})
    msgs.append(bild_nachricht(bild_url))
    return msgs


@lru_cache
def client():
    if os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"):
        from openai import AzureOpenAI
        return AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=API_VERSION,
        )
    if os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI
        return OpenAI()
    raise VisionNichtKonfiguriert(
        "Kein Vision-Modell konfiguriert (AZURE_OPENAI_* oder OPENAI_API_KEY in .env setzen)")


def modell_name():
    """(Deployment/Modell, ist_finetuned)"""
    if os.getenv("VISION_FT_DEPLOYMENT"):
        return os.environ["VISION_FT_DEPLOYMENT"], True
    if os.getenv("AZURE_OPENAI_ENDPOINT"):
        return os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"), False
    return os.getenv("OPENAI_MODEL", "gpt-4o"), False


@lru_cache
def referenzen():
    if not REFERENZEN.exists():
        return []
    anzahl = int(os.getenv("VISION_FEWSHOT", "4"))
    return json.loads(REFERENZEN.read_text(encoding="utf-8"))[:anzahl]


def bereinigen(roh):
    """Nur bekannte Gruppen, jede höchstens einmal; unsichere Werkzeuge bleiben markiert."""
    werkzeuge, gesehen = [], set()
    for w in roh.get("werkzeuge") or []:
        key = (w.get("gruppe") or "").strip()
        if key in GRUPPEN and key not in gesehen:
            gesehen.add(key)
            werkzeuge.append({
                "gruppe": key,
                "beschreibung": (w.get("beschreibung") or "").strip(),
                "sicher": bool(w.get("sicher", True)),
            })
    try:
        konfidenz = min(max(float(roh.get("konfidenz") or 0), 0.0), 1.0)
    except (TypeError, ValueError):
        konfidenz = 0.0
    return {
        "ist_taschenmesser": bool(roh.get("ist_taschenmesser", True)),
        "marke": roh.get("marke") or None,
        "modell": roh.get("modell") or None,
        "artikelnummer_sichtbar": roh.get("artikelnummer_sichtbar") or None,
        "geoeffnet": bool(roh.get("geoeffnet", True)),
        "werkzeuge": werkzeuge,
        "konfidenz": konfidenz,
    }


def anbieter():
    gewaehlt = os.getenv("VISION_ANBIETER", "").strip().lower()
    if gewaehlt in ("clef", "openai"):
        return gewaehlt
    return "clef" if clef.aktiv() else "openai"


def erkenne(bild_url):
    """bild_url: http(s)-URL oder data:-URL. Gibt das bereinigte Erkennungsergebnis zurück.

    "modell_info" beschreibt das verwendete Modell (für die Agenten-Schritte im Frontend).
    """
    if anbieter() == "clef":
        try:
            return clef.erkenne(bild_url)
        except clef.ClefNichtKonfiguriert as fehler:
            raise VisionNichtKonfiguriert(str(fehler)) from None
    return _erkenne_openai(bild_url)


def _erkenne_openai(bild_url):
    modell, finetuned = modell_name()
    beispiele = () if finetuned else referenzen()
    res = client().chat.completions.create(
        model=modell,
        messages=nachrichten(bild_url, beispiele),
        response_format={"type": "json_object"},
        temperature=0,
    )
    roh = json.loads(res.choices[0].message.content or "{}")
    ergebnis = bereinigen(roh)
    ergebnis["modell_info"] = {"modell": modell,
                               "art": "fine-getunt" if finetuned else f"{len(beispiele)} Referenzbilder"}
    return ergebnis
