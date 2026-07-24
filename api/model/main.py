"""
=============================================================================
C9/C11 — API modèle Prophet — inflation-tracker
=============================================================================
Application FastAPI exposant les prédictions du modèle Prophet IPC France.

Endpoints métier (préfixe /api) :
    GET /predict/{categorie}?horizon=12    Prédictions N mois, 1 catégorie
    GET /predict?horizon=12               Prédictions N mois, toutes catégories
    GET /categories                        Catégories disponibles
    GET /metrics                           Métriques eval 2025 (toutes catégories)
    GET /metrics/{categorie}               Métriques eval 2025, 1 catégorie

Endpoints infrastructure :
    GET /health                            Statut de l'API
    GET /metrics-prometheus                Métriques Prometheus (scrapées par Prometheus)

Lancement :
    uvicorn api.model.main:app --reload --port 8002

Issues GitHub : #15 (C9), #17 (C11)
=============================================================================
"""

import json
import time
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.model.metrics import (
    api_errors_total,
    api_requests_total,
    prediction_latency_seconds,
    prediction_mae,
)
from api.model.routes.predict import router as predict_router

# Chemin vers metrics.json pour initialiser les jauges MAE au démarrage
METRICS_JSON = Path(__file__).parent.parent.parent / "model" / "metrics.json"


# =============================================================================
# Lifespan — initialisation des jauges MAE au démarrage (C11)
# =============================================================================

@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Initialise les jauges Prometheus prediction_mae depuis metrics.json.

    Exécuté une seule fois au démarrage de l'API — permet à Grafana d'afficher
    les MAE par catégorie dès le premier scrape Prometheus (sans attendre une requête).
    """
    if METRICS_JSON.exists():
        with open(METRICS_JSON, encoding="utf-8") as f:
            raw = json.load(f)   # {categorie: {MAE, RMSE, MAPE_pct, ...}}
        for cat, m in raw.items():
            prediction_mae.labels(categorie=cat).set(m["MAE"])   # une jauge par catégorie
    yield   # l'application tourne ici jusqu'à l'arrêt


# =============================================================================
# Application FastAPI
# =============================================================================

app = FastAPI(
    title="Inflation Tracker — API Modèle",
    description=(
        "API REST exposant les prédictions du modèle Prophet "
        "entraîné sur l'IPC France INSEE (12 catégories COICOP 00-11, base 100 = 2015). "
        "Métriques Prometheus disponibles sur /metrics-prometheus."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,   # remplace @app.on_event("startup") déprécié
)

# Middleware CORS — lecture seule, toutes origines acceptées en développement
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# =============================================================================
# Middleware HTTP — latence + comptage requêtes + détection erreurs (C11)
# =============================================================================

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """
    Intercepte chaque requête HTTP pour :
    - Mesurer la latence des endpoints /predict (Histogram)
    - Compter toutes les requêtes par méthode/route/statut (Counter)
    - Détecter et compter les erreurs serveur (Counter)
    """
    start_time = time.perf_counter()   # horodatage avant traitement

    response = await call_next(request)   # traitement de la requête

    duration = time.perf_counter() - start_time   # durée en secondes

    # Normalisation du chemin : /api/predict/00%20-%20Ensemble → /api/predict/{categorie}
    path = request.url.path
    if path.startswith("/api/predict/"):
        endpoint_label = "/api/predict/{categorie}"
    elif path.startswith("/api/metrics/"):
        endpoint_label = "/api/metrics/{categorie}"
    else:
        endpoint_label = path   # route exacte pour les autres endpoints

    # Comptage de chaque requête par méthode + route normalisée + code statut
    api_requests_total.labels(
        method=request.method,
        endpoint=endpoint_label,
        status_code=str(response.status_code),
    ).inc()

    # Mesure de latence uniquement pour les endpoints de prédiction (les plus coûteux)
    if "/predict" in path:
        prediction_latency_seconds.observe(duration)

    # Comptage des erreurs serveur (5xx) et not found (404) séparément
    if response.status_code >= 500:
        api_errors_total.labels(error_type="server_error").inc()
    elif response.status_code == 404 and path.startswith("/api/"):
        api_errors_total.labels(error_type="not_found").inc()
    elif response.status_code == 422:
        api_errors_total.labels(error_type="validation").inc()

    return response


# =============================================================================
# Inclusion du router métier
# =============================================================================

app.include_router(predict_router, prefix="/api")


# =============================================================================
# Health check
# =============================================================================

@app.get("/health", tags=["health"], summary="Statut de l'API modèle")
def health():
    """Vérifie que l'API modèle Prophet est opérationnelle."""
    return {
        "status": "ok",
        "service": "inflation-tracker-api-model",
        "version": "1.0.0",
    }


# =============================================================================
# Endpoint Prometheus /metrics-prometheus (C11)
# =============================================================================

@app.get("/metrics-prometheus", include_in_schema=False, tags=["monitoring"])
def metrics_prometheus():
    """Endpoint scrapé par Prometheus — retourne les métriques au format text/plain."""
    # generate_latest() sérialise tous les métriques prometheus_client enregistrés
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
