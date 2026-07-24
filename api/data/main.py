"""
=============================================================================
C5 — API REST FastAPI — inflation-tracker (données)
=============================================================================
Exposition des données d'inflation issues de 5 sources via une API REST.

Endpoints :
    GET /health                              — état du service
    GET /api/inflation                       — données inflation_unified (3.68M lignes)
    GET /api/inflation/tendance              — moyenne mensuelle par pays/source
    GET /api/inflation/pays                  — liste des pays disponibles
    GET /api/inflation/sources               — liste des sources disponibles
    GET /api/inflation/categories            — liste des catégories COICOP
    GET /api/prix-alimentaires               — prix terrain Open Food Facts
    GET /api/prix-alimentaires/categories    — catégories alimentaires
    GET /api/prix-alimentaires/stats         — prix moyen/min/max par catégorie

Documentation interactive : http://localhost:8001/docs (Swagger UI)

Lancement :
    uvicorn api.data.main:app --reload --port 8001

Issue GitHub : #11 (C5 — exposition API données)
=============================================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.data.routes.inflation import router as inflation_router
from api.data.routes.prix import router as prix_router

app = FastAPI(
    title="Inflation Tracker — API Données",
    description=(
        "API REST exposant les données d'inflation consolidées depuis 5 sources : "
        "ECB (HICP France), INSEE (IPC France), data.gouv.fr (séries longues), "
        "Eurostat France (147 002 lignes), Open Food Facts (prix alimentaires terrain). "
        "Périmètre géographique : France uniquement."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(inflation_router, prefix="/api")
app.include_router(prix_router, prefix="/api")


@app.get("/health", tags=["health"])
def health():
    """Vérification que l'API est opérationnelle."""
    return {"status": "ok", "service": "inflation-tracker-api-data", "version": "1.0.0"}
