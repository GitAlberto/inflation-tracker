#!/usr/bin/env bash
# start.sh — Lance tous les services inflation-tracker
# Mode : APIs en Python natif (.venv) + monitoring Docker (Prometheus + Grafana)
# prometheus.yml utilise host.docker.internal:8002 pour scraper l'API native

cd "$(dirname "$0")"
PY=".venv/Scripts/python"

# Charger les variables .env pour le healthcheck postgres
source <(grep -v '^\s*#' .env | grep -v '^\s*$') 2>/dev/null || true

# --- PostgreSQL (Docker) ---
echo "PostgreSQL → docker-compose up -d postgres"
docker-compose up -d postgres
until docker exec inflation_postgres pg_isready -U "${POSTGRES_USER}" -d inflation_tracker 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL prêt."

# --- Arrêter les containers API Docker s'ils tournent ---
# Les ports 8001/8002 doivent être libres pour les processus natifs ci-dessous.
# Sans ça, uvicorn échoue silencieusement et Prometheus scrape le mauvais processus.
docker-compose stop api_data api_model 2>/dev/null

# --- Monitoring Docker (Prometheus + Grafana) ---
# Prometheus scrape host.docker.internal:8002 = l'API native ci-dessous.
# Les dashboards Grafana se rechargent toutes les 30s automatiquement.
echo "Monitoring → Prometheus :9090 / Grafana :3000"
# --no-deps : ne pas redémarrer api_model/api_data Docker (on les démarre nativement en dessous)
docker-compose up -d --no-deps prometheus grafana

# --- APIs en Python natif ---
echo "API data   → http://localhost:8001"
"$PY" -m uvicorn api.data.main:app --port 8001 --log-level warning &
P1=$!

echo "API modèle → http://localhost:8002"
"$PY" -m uvicorn api.model.main:app --port 8002 --log-level warning &
P2=$!

echo "Streamlit  → http://localhost:8501  (Ctrl+C pour tout arrêter)"
trap "kill $P1 $P2 2>/dev/null" INT TERM
"$PY" -m streamlit run app/main.py
kill $P1 $P2 2>/dev/null
