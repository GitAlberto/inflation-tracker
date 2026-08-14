#!/usr/bin/env bash
# start.sh — Lance tous les services inflation-tracker en une commande
# APIs + monitoring en Docker, Streamlit en natif (.venv)

set -e
cd "$(dirname "$0")"
PY=".venv/Scripts/python"

# Charger les variables .env pour le healthcheck postgres
source <(grep -v '^\s*#' .env | grep -v '^\s*$') 2>/dev/null || true

# --- Tous les services Docker (rebuild automatique si image modifiée) ---
echo ">>> Démarrage Docker (postgres + api_data + api_model + prometheus + grafana)..."
docker-compose up -d --build postgres api_data api_model prometheus grafana

# --- Attendre PostgreSQL ---
echo ">>> Attente PostgreSQL..."
until docker exec inflation_postgres pg_isready -U "${POSTGRES_USER}" -d inflation_tracker 2>/dev/null; do
  sleep 1
done
echo "    PostgreSQL prêt."

# --- Attendre les APIs ---
echo ">>> Attente API data  (http://localhost:8001/health)..."
until curl -sf http://localhost:8001/health > /dev/null 2>&1; do sleep 1; done
echo "    API data prête."

echo ">>> Attente API modèle (http://localhost:8002/health)..."
until curl -sf http://localhost:8002/health > /dev/null 2>&1; do sleep 1; done
echo "    API modèle prête."

echo ""
echo "  Prometheus → http://localhost:9090"
echo "  Grafana    → http://localhost:3000  (admin / voir GRAFANA_PASSWORD dans .env)"
echo "  API data   → http://localhost:8001/docs"
echo "  API modèle → http://localhost:8002/docs"
echo "  Streamlit  → http://localhost:8501"
echo ""
echo "  Ctrl+C pour tout arrêter."
echo ""

# --- Streamlit en natif — Ctrl+C arrête tout ---
trap "echo ''; echo 'Arrêt des services Docker...'; docker-compose stop api_data api_model prometheus grafana; exit 0" INT TERM
"$PY" -m streamlit run app/main.py