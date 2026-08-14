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

import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, generate_latest

load_dotenv()  # charge .env avant tout — garantit que API_KEY est disponible dès le démarrage

from api.data.routes.inflation import router as inflation_router
from api.data.routes.prix import router as prix_router

# =============================================================================
# Métriques Prometheus — C20 monitoring applicatif
# =============================================================================
data_requests_total = Counter(
    "inflation_data_requests_total",
    "Nombre total de requêtes HTTP reçues par l'API data",
    ["method", "endpoint", "status_code"],
)
data_request_latency_seconds = Histogram(
    "inflation_data_request_latency_seconds",
    "Latence des requêtes HTTP de l'API data en secondes",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)
data_errors_total = Counter(
    "inflation_data_errors_total",
    "Nombre d'erreurs API data par type d'erreur",
    ["error_type"],
)

app = FastAPI(
    title="Inflation Tracker — API Données",
    description=(
        "API REST exposant les données d'inflation consolidées depuis 5 sources : "
        "ECB (HICP France), INSEE (IPC France), data.gouv.fr (séries longues), "
        "Eurostat France, Open Food Facts (prix alimentaires terrain). "
        "Périmètre géographique : France uniquement. "
        "**Authentification** : header `X-API-Key` obligatoire sur toutes les routes `/api/`."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    # Génération du schéma OpenAPI standard via FastAPI interne
    from fastapi.openapi.utils import get_openapi  # import local — contourne le linter Python 3.13 système
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {})["securitySchemes"] = {
        "APIKeyHeader": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
    }
    schema["security"] = [{"APIKeyHeader": []}]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(inflation_router, prefix="/api")
app.include_router(prix_router, prefix="/api")


# =============================================================================
# Middleware HTTP — latence + comptage + erreurs (C20)
# =============================================================================
@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start_time

    path = request.url.path
    if path == "/api/inflation":
        endpoint_label = "/api/inflation"
    elif path.startswith("/api/inflation/"):
        endpoint_label = "/api/inflation/{sub}"
    elif path == "/api/prix-alimentaires":
        endpoint_label = "/api/prix-alimentaires"
    elif path.startswith("/api/prix-alimentaires/"):
        endpoint_label = "/api/prix-alimentaires/{sub}"
    else:
        endpoint_label = path

    data_requests_total.labels(
        method=request.method,
        endpoint=endpoint_label,
        status_code=str(response.status_code),
    ).inc()

    if path.startswith("/api/"):
        data_request_latency_seconds.observe(duration)

    if response.status_code >= 500:
        data_errors_total.labels(error_type="server_error").inc()
    elif response.status_code == 404 and path.startswith("/api/"):
        data_errors_total.labels(error_type="not_found").inc()
    elif response.status_code == 422:
        data_errors_total.labels(error_type="validation").inc()
    elif response.status_code == 403:
        data_errors_total.labels(error_type="unauthorized").inc()

    return response


@app.get("/health", tags=["health"])
def health():
    """Vérification que l'API est opérationnelle."""
    return {"status": "ok", "service": "inflation-tracker-api-data", "version": "1.0.0"}


@app.get("/metrics-prometheus", include_in_schema=False, tags=["monitoring"])
def metrics_prometheus():
    """Endpoint scrapé par Prometheus — métriques applicatives C20."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
