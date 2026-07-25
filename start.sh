#!/usr/bin/env bash
# start.sh — Lance tous les services inflation-tracker

cd "$(dirname "$0")"
PY=".venv/Scripts/python"

# Charger les variables .env pour le healthcheck postgres
source <(grep -v '^\s*#' .env | grep -v '^\s*$') 2>/dev/null || true

echo "PostgreSQL → docker-compose up -d postgres"
docker-compose up -d postgres
until docker exec inflation_postgres pg_isready -U "${POSTGRES_USER}" -d inflation_tracker 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL prêt."

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
