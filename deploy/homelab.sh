#!/usr/bin/env bash
# Deployment-Runbook fuer das Homelab (siehe README "Deployment auf dem Homelab").
#
#   ./deploy/homelab.sh sync     -> Repo von der lokalen Maschine auf das Homelab kopieren
#   ./deploy/homelab.sh up       -> Images bauen und Stack starten
#   ./deploy/homelab.sh serve     -> Stack ueber Tailscale Serve (HTTPS) veroeffentlichen
#   ./deploy/homelab.sh funnel    -> zusaetzlich ueber Tailscale Funnel (oeffentlich)
#   ./deploy/homelab.sh status    -> Status, erreichbare URLs
#   ./deploy/homelab.sh logs     -> Backend-Logs (live)
#
# Ziel-Homelab ist per ssh erreichbar; anpassen in deploy/homelab.env.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$REPO_ROOT/deploy/homelab.env"

if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  . "$ENV_FILE"
fi

HOMELAB_HOST="${HOMELAB_HOST:-simon@homelab}"
REMOTE_DIR="${REMOTE_DIR:-$HOME/dev/Zentralhack-Victorinox-Challenge}"
SERVE_PORT="${SERVE_PORT:-3100}"
FUNNEL_PORT="${FUNNEL_PORT:-3100}"
BACKEND_PORT="${BACKEND_PORT:-8100}"

cmd_sync() {
  echo ">> rsync -> $HOMELAB_HOST:$REMOTE_DIR"
  ssh "$HOMELAB_HOST" "mkdir -p '$REMOTE_DIR'"
  # katalog_kacheln ist der Bild-Cache der Clef-Bildsuche: er wird beim ersten
  # Start aus den Katalogbildern erzeugt und soll nicht uebertragen oder geloescht
  # werden (dann waechst er auf dem Homelab weiter).
  rsync -az --delete \
    --exclude '.git/' --exclude 'node_modules/' --exclude '__pycache__/' \
    --exclude '.venv/' --exclude '*.pyc' --exclude 'dist/' \
    --exclude 'backend/data/katalog_kacheln/' \
    "$REPO_ROOT/" "$HOMELAB_HOST:$REMOTE_DIR/"
  echo ">> sync fertig"
}

cmd_up() {
  # --no-cache: die Images enthalten den Quellcode (COPY . .). Ohne das nutzt Docker
  # den alten Layer und der Container laeuft mit dem Stand des letzten Builds.
  ssh "$HOMELAB_HOST" "cd '$REMOTE_DIR' && docker compose -f deploy/docker-compose.homelab.yml up -d --build --no-cache"
  sleep 3
  ssh "$HOMELAB_HOST" "cd '$REMOTE_DIR' && docker compose -f deploy/docker-compose.homelab.yml ps"
}

cmd_serve() {
  ssh "$HOMELAB_HOST" "tailscale serve --bg --https=443 http://127.0.0.1:$SERVE_PORT"
  ssh "$HOMELAB_HOST" "tailscale serve status"
}

cmd_funnel() {
  ssh "$HOMELAB_HOST" "tailscale funnel --bg --https=443 http://127.0.0.1:$FUNNEL_PORT"
  ssh "$HOMELAB_HOST" "tailscale funnel status"
}

cmd_status() {
  ssh "$HOMELAB_HOST" "cd '$REMOTE_DIR' && docker compose -f deploy/docker-compose.homelab.yml ps"
  echo
  echo "== Tailscale Serve =="
  ssh "$HOMELAB_HOST" "tailscale serve status"
  echo
  echo "== API =="
  ssh "$HOMELAB_HOST" "curl -sS http://127.0.0.1:$BACKEND_PORT/api/health || true"
  echo
}

cmd_logs() {
  ssh -t "$HOMELAB_HOST" "cd '$REMOTE_DIR' && docker compose -f deploy/docker-compose.homelab.yml logs -f backend"
}

case "${1:-status}" in
  sync) cmd_sync ;;
  up) cmd_up ;;
  serve) cmd_serve ;;
  funnel) cmd_funnel ;;
  status) cmd_status ;;
  logs) cmd_logs ;;
  *)
    echo "usage: $0 {sync|up|serve|funnel|status|logs}" >&2
    exit 1
    ;;
esac
