"""Öffentlicher https-Tunnel fürs Handy (cloudflared Quick Tunnel), nur solange er gebraucht wird.

In vielen WLANs (Schule, Firma, Hackathon) sehen sich die Geräte gegenseitig nicht, das Handy
erreicht den Computer also nicht über seine IP. Darum öffnet "Mit Handy scannen" einen Tunnel
https://<zufall>.trycloudflare.com -> dieses Backend und schliesst ihn wieder, sobald das Foto da ist.

Über den Tunnel ist nur die kleine Handy-Seite /h/... erreichbar (siehe Middleware in main.py),
nicht die übrige API: wer die zufällige Adresse kennt, kann damit kein Clef-Guthaben verbrauchen.
"""

import json
import re
import shutil
import subprocess
import threading
import time
import urllib.request

ZIEL = "http://localhost:8000"
START_TIMEOUT_S = 30
BEREIT_TIMEOUT_S = 30          # neue trycloudflare-Adressen brauchen ein paar Sekunden im DNS
# DNS-over-HTTPS statt des lokalen Resolvers: Wer die neue Adresse zu früh nachschlägt, bekommt
# "gibt es nicht" und merkt sich das minutenlang (Docker, Handy). Darum erst zeigen, wenn sie auflöst.
DOH_URL = "https://cloudflare-dns.com/dns-query?name={}&type=A"
URL_MUSTER = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

_lock = threading.Lock()
_prozess = None
_url = None


def verfuegbar():
    return shutil.which("cloudflared") is not None


def offen():
    return _prozess is not None and _prozess.poll() is None


def oeffnen():
    """Tunnel starten (oder den laufenden wiederverwenden) und warten, bis er erreichbar ist -> URL."""
    global _prozess, _url
    with _lock:
        if offen() and _url:
            return _url
        prozess = subprocess.Popen(
            ["cloudflared", "tunnel", "--no-autoupdate", "--url", ZIEL],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
        )
        gefunden = threading.Event()
        verbunden = threading.Event()
        url = []

        def lesen():  # cloudflared schreibt die Adresse ins Log; danach weiter leeren, sonst blockiert die Pipe
            for zeile in prozess.stderr:
                if not url and (treffer := URL_MUSTER.search(zeile)):
                    url.append(treffer.group(0))
                    gefunden.set()
                if "Registered tunnel connection" in zeile:
                    verbunden.set()

        threading.Thread(target=lesen, daemon=True).start()
        if not gefunden.wait(START_TIMEOUT_S):
            prozess.terminate()
            raise RuntimeError("cloudflared hat keine Tunnel-Adresse geliefert")
        _prozess, _url = prozess, url[0]

        frist = time.time() + BEREIT_TIMEOUT_S
        verbunden.wait(BEREIT_TIMEOUT_S)
        host = _url.removeprefix("https://")
        while time.time() < frist:
            if _dns_bereit(host):
                return _url
            time.sleep(1)
        return _url  # meist trotzdem gleich erreichbar; das Handy lädt notfalls neu


def _dns_bereit(host):
    req = urllib.request.Request(DOH_URL.format(host), headers={"Accept": "application/dns-json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return bool(json.load(res).get("Answer"))
    except Exception:
        return False


def schliessen():
    global _prozess, _url
    with _lock:
        if _prozess is not None:
            _prozess.terminate()
            try:
                _prozess.wait(5)
            except subprocess.TimeoutExpired:
                _prozess.kill()
        _prozess, _url = None, None
