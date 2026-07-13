"""
=============================================================================
C9 — API modèle Prophet — inflation-tracker
=============================================================================
Application FastAPI exposant les prédictions du modèle Prophet IPC France.

Endpoints :
    GET /health                            Statut de l'API
    GET /predict/{categorie}?horizon=12    Prédictions N mois, 1 catégorie
    GET /predict?horizon=12               Prédictions N mois, toutes catégories
    GET /categories                        Catégories disponibles
    GET /metrics                           Métriques eval 2025 (toutes catégories)
    GET /metrics/{categorie}               Métriques eval 2025, 1 catégorie

Lancement :
    uvicorn api.model.main:app --reload --port 8002

Issue GitHub : #15 (C9)
=============================================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.model.routes.predict import router as predict_router

# Initialisation de l'application FastAPI avec métadonnées pour Swagger
app = FastAPI(
    title="Inflation Tracker — API Modèle",
    description=(
        "API REST exposant les prédictions du modèle Prophet "
        "entraîné sur l'IPC France INSEE (13 catégories, base 100 = 2015)."
    ),
    version="1.0.0",
    docs_url="/docs",      # Swagger UI accessible sur /docs
    redoc_url="/redoc",    # ReDoc accessible sur /redoc
)

# Middleware CORS : autorise toutes origines en développement
# À restreindre aux domaines connus en production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # origines autorisées
    allow_methods=["GET"],     # lecture seule — pas de modification possible
    allow_headers=["*"],       # tous les headers acceptés
)

# Inclusion du router de prédictions (préfixe /api pour cohérence avec api/data)
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
