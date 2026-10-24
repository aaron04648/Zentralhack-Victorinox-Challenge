# Deployment auf dem Homelab

Das Homelab (`simon@homelab`) betreibt Backend und Frontend als Docker-Container
und stellt die App über **Tailscale Serve** mit HTTPS bereit. Der Weg von der
lokalen Maschine zum Homelab ist ein `rsync`; gebaut und gestartet wird auf
dem Homelab.

## Warum das Homelab?

| | lokal | Homelab |
| --- | --- | --- |
| CPU | 8 Kerne, schwach | 16 Kerne |
| RAM | 7,6 GB (davon ~2 GB frei) | 62 GB (55 GB frei) |
| Docker | nur Client | Server + Compose |
| Netzausgang | ja | ja (npm, PyPI, OpenRouter) |

Der Build läuft komplett auf dem Homelab (`docker compose build`), die lokale
Maschine muss weder Node noch Python-Pakete installieren.

## Schnellstart

```bash
# alles in einem Schritt: übertragen, bauen, starten
./deploy/homelab.sh sync && ./deploy/homelab.sh up

# Status und erreichbare URL
./deploy/homelab.sh status
```

Danach ist die App erreichbar unter

```
https://homelab.tailb8858a.ts.net/
```

Diese URL funktioniert auf jedem Gerät, das im selben Tailnet ist (z. B. dem
Pixel) – ohne Mobilfunk, ohne VPN-Setup, mit gültigem TLS-Zertifikat.

## Die Befehle

| Befehl | Wirkung |
| --- | --- |
| `./deploy/homelab.sh sync` | Repo per `rsync` auf das Homelab kopieren (ohne `.git`, `node_modules`, `__pycache__`, `backend/data/katalog_kacheln`) |
| `./deploy/homelab.sh up` | Images ohne Cache bauen, Container neu erstellen, Status zeigen |
| `./deploy/homelab.sh serve` | Tailscale Serve (HTTPS) aktivieren |
| `./deploy/homelab.sh status` | Container-Status, Tailscale-Serve-Status, API-Health |
| `./deploy/homelab.sh logs` | Backend-Logs live |

Die Zielwerte (Host, Pfad, Ports) stehen in `deploy/homelab.env`.

## Aufbau

```
deploy/
  homelab.sh                    Runbook-Skript (sync/up/serve/status/logs)
  homelab.env                   Host, Pfad, Ports
  docker-compose.homelab.yml    Compose-Stack für das Homelab
backend/Dockerfile              Backend-Image (patcht den Embedding-Zugriff, s. u.)
frontend/Dockerfile.prod        Produktions-Build: vite build -> nginx
frontend/nginx.conf             SPA-Fallback + /api-Proxy zum Backend
```

* **Frontend** läuft als nginx mit dem gebauten React-Bundle. nginx liefert
  `/index.html` für alle unbekannten Pfade (react-router) und leitet `/api/`
  an das Backend weiter. Für die Demo ist das stabiler als der Vite-Dev-Server.
* **Backend** läuft ohne `--reload` (siehe Hinweis unten).

### Ports auf dem Homelab

| Port | Dienst | Bindung |
| --- | --- | --- |
| 3100 | Frontend (nginx) | `127.0.0.1` |
| 8100 | Backend (FastAPI) | `127.0.0.1` |

Beide sind nur an localhost gebunden – nach aussen geht alles über
Tailscale Serve auf Port 443. (Port 3000 und 8000 sind auf dem Homelab
belegt: 3000 durch `panopticon`, 8000 war der erste Versuch.)

## Zwei Stolperfallen, die schon Zeit gekostet haben

**1. `--reload` im Container.** Uvicorns Reload-Prozess startet die App in
einem zweiten Interpreter. Dort ist die Bindung von Modulnamen anders, und
`from app import embeddings` blieb unbound – der Startup-Handler brach mit
`NameError` ab, obwohl der Name in `__dict__` stand. Im Container läuft der
Backend deshalb ohne `--reload`; lokal weiterhin mit.

CPython 3.12 spezialisiert `LOAD_GLOBAL` an der Stelle, an der der Name
gebunden wurde. `import app.embeddings as embeddings` auf Modulebene erzeugt
einen Namen, der gleichzeitig globale Variable und Submodul des Pakets `app`
ist – die Spezialisierung findet ihn dann nicht mehr. Deshalb greift der
Backend im Container über `sys.modules["app.embeddings"]` zu. Das
`backend/Dockerfile` patcht das beim Build, damit es unabhängig vom Stand der
Quelldatei gilt.

**2. Docker-Layer-Cache.** Die Images enthalten den Quellcode (`COPY . .`).
Ohne `--no-cache` läuft der Container mit dem Stand des letzten Builds und
zeigt alte Fehler. `deploy/homelab.sh up` baut deshalb ohne Cache und
erstellt die Container neu.

## Tailscale Serve

```bash
# einmalig auf dem Homelab
sudo tailscale set --operator=$USER      # erlaubt tailscale serve ohne sudo
tailscale serve --bg --https=443 http://127.0.0.1:3100
```

Das ergibt `https://homelab.tailb8858a.ts.net/` mit echtem Zertifikat.

**Tailscale Funnel** (öffentlich erreichbar, ohne Tailnet) ist eine Option,
wenn das Pixel im WLAN kein Tailscale hat:

```bash
tailscale funnel --bg --https=443 http://127.0.0.1:3100
```

Funnel muss einmalig in der Tailscale-Adminoberfläche aktiviert werden
(`https://login.tailscale.com/f/funnel?node=...`) – das geht nicht per CLI.

## Konfiguration

`deploy/docker-compose.homelab.yml` liest `.env` aus dem Repo-Root:

| Variable | Wirkung |
| --- | --- |
| `OPENROUTER_API_KEY` | Clef (Bilderkennung + Marke + Katalogbildsuche) – ohne Key antwortet `/api/match` mit 503 und das Frontend nutzt den Mock |
| `TYPESAFE_API_KEY` | Jev (Werkzeugzuordnung) – optional, ohne Key nutzt die Pipeline die Bilderkennung direkt |

## Was der Demo-Pfad braucht

Der Aufruf `/api/match` dauert **10–20 Sekunden**: das Bild geht an Clef
(3 parallele Pakete mit je 12 Fragen, plus ein eigenes Paket für die Marke),
parallel läuft die Bildsuche über 151 Katalogbilder in zwei Turnieren.

Bei 12 Bildern im Turnier und 4 Bildern pro Anfrage (3 Kachelraster + 1
Kundenfoto) sind das rund 30 Anfragen pro Analyse.

## Problembehebung

```bash
./deploy/homelab.sh logs            # Backend-Logs
ssh simon@homelab 'docker logs --since 5m deploy-backend-1'
ssh simon@homelab 'docker logs --since 5m deploy-frontend-1'

# Neustart
./deploy/homelab.sh up

# Nur der Katalogbild-Cache (wird beim ersten Start erzeugt, ~180 Downloads)
ssh simon@homelab 'ls ~/dev/Zentralhack-Victorinox-Challenge/backend/data/katalog_kacheln | wc -l'
```
