"""
=============================================================================
C9 — Routes Prophet — API modèle — inflation-tracker
=============================================================================
Expose les prédictions Prophet et les métriques d'évaluation via FastAPI.

Endpoints :
    GET /predict/{categorie}?horizon=12   Prédictions N mois, 1 catégorie
    GET /predict?horizon=12               Prédictions N mois, toutes catégories
    GET /categories                       Liste des catégories disponibles
    GET /metrics                          Métriques eval 2025 (toutes catégories)
    GET /metrics/{categorie}              Métriques eval 2025, 1 catégorie

Issue GitHub : #15 (C9)
=============================================================================
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Security

from api.model.auth import verify_key

# Import des fonctions de prédiction depuis le package model/
# Fonctionne car model/__init__.py existe et le projet est lancé depuis la racine
from model.predict import list_available, predict_all, predict_one

# Compteur Prometheus — incrémenté à chaque prédiction réussie (C11)
from api.model.metrics import predictions_total

from api.model.schemas import (
    CategoryMetrics,
    MetricsResponse,
    PredictionPoint,
    PredictionResponse,
)

# Chemin vers metrics.json — défini une seule fois pour tous les endpoints
METRICS_PATH = Path(__file__).parent.parent.parent.parent / "model" / "metrics.json"

# dependencies=[Security(verify_key)] protège toutes les routes de ce router (C9)
router = APIRouter(tags=["predictions"], dependencies=[Security(verify_key)])


# =============================================================================
# Utilitaires internes
# =============================================================================

def _load_metrics() -> dict:
    """Charge metrics.json et lève 503 si absent (train.py non exécuté)."""
    if not METRICS_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="metrics.json introuvable — exécutez d'abord : python model/train.py",
        )
    with open(METRICS_PATH, encoding="utf-8") as f:
        return json.load(f)   # dict {categorie: {MAE, RMSE, MAPE_pct, n_train, n_eval}}


def _df_to_predictions(df, horizon: int, categorie: str) -> PredictionResponse:
    """Convertit le DataFrame predict_one() en PredictionResponse Pydantic."""
    # Conversion ligne par ligne en PredictionPoint
    points = [
        PredictionPoint(
            date_pred=row["date_pred"].date(),            # Timestamp → date Python
            yhat=round(float(row["yhat"]), 4),           # valeur centrale
            yhat_lower=round(float(row["yhat_lower"]), 4),  # borne basse IC 80%
            yhat_upper=round(float(row["yhat_upper"]), 4),  # borne haute IC 80%
        )
        for _, row in df.iterrows()
    ]

    # Variation totale = dernier yhat - premier yhat (tendance sur la période)
    variation = float(df["yhat"].iloc[-1] - df["yhat"].iloc[0])

    return PredictionResponse(
        categorie=categorie,
        horizon=horizon,
        predictions=points,
        variation_totale=round(variation, 4),
        generated_at=datetime.now(timezone.utc),   # horodatage UTC de la génération
    )


# =============================================================================
# Endpoints prédictions
# =============================================================================

@router.get(
    "/predict/{categorie}",
    response_model=PredictionResponse,
    summary="Prédictions Prophet pour une catégorie IPC",
)
def predict_categorie(
    categorie: str,
    horizon: Annotated[
        int,
        Query(ge=1, le=36, description="Nombre de mois à prédire (1-36)")
    ] = 12,
):
    """
    Retourne les prédictions Prophet sur N mois pour une catégorie IPC France.

    - **categorie** : nom exact (ex: `00 - Ensemble`, `01 - Alimentation et boissons non alcoolisées`)
    - **horizon** : nombre de mois (1 à 36, défaut 12)
    """
    # Vérification que la catégorie a bien un modèle entraîné
    available = list_available()
    if categorie not in available:
        raise HTTPException(
            status_code=404,
            detail=f"Catégorie '{categorie}' introuvable. Disponibles : {available}",
        )

    # Génération des prédictions via model/predict.py
    try:
        df = predict_one(categorie, horizon=horizon)
    except FileNotFoundError as exc:
        # .pkl absent malgré metrics.json présent (incohérence)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Incrémentation du compteur Prometheus par catégorie (C11)
    predictions_total.labels(categorie=categorie).inc()

    return _df_to_predictions(df, horizon, categorie)


@router.get(
    "/predict",
    response_model=dict[str, PredictionResponse],
    summary="Prédictions Prophet pour toutes les catégories IPC",
)
def predict_toutes(
    horizon: Annotated[
        int,
        Query(ge=1, le=36, description="Nombre de mois à prédire (1-36)")
    ] = 12,
):
    """
    Retourne les prédictions Prophet sur N mois pour les 13 catégories IPC France.

    Peut prendre quelques secondes (chargement de 13 modèles .pkl).
    """
    try:
        results = predict_all(horizon=horizon)   # dict {categorie: DataFrame}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not results:
        raise HTTPException(
            status_code=503,
            detail="Aucun modèle disponible — exécutez : python model/train.py",
        )

    # Conversion de chaque DataFrame en PredictionResponse
    return {cat: _df_to_predictions(df, horizon, cat) for cat, df in results.items()}


# =============================================================================
# Endpoint catégories disponibles
# =============================================================================

@router.get(
    "/categories",
    response_model=list[str],
    summary="Liste des catégories IPC disponibles",
)
def get_categories():
    """Retourne la liste des catégories pour lesquelles un modèle Prophet est disponible."""
    categories = list_available()   # lit metrics.json → retourne les clés

    if not categories:
        raise HTTPException(
            status_code=503,
            detail="Aucun modèle disponible — exécutez : python model/train.py",
        )

    return categories   # liste triée par ordre alphabétique (ordre de metrics.json)


# =============================================================================
# Endpoints métriques
# =============================================================================

@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Métriques d'évaluation Prophet — toutes catégories",
)
def get_metrics():
    """
    Retourne les métriques MAE/RMSE/MAPE d'évaluation (split 2025) pour les 13 catégories.

    Source : `model/metrics.json` généré par `model/train.py`.
    """
    raw = _load_metrics()   # {categorie: {MAE, RMSE, MAPE_pct, n_train, n_eval}}

    return MetricsResponse(
        nb_categories=len(raw),
        eval_period="2025-01 / 2025-12",   # période d'évaluation fixe
        metrics={cat: CategoryMetrics(**m) for cat, m in raw.items()},
    )


@router.get(
    "/metrics/{categorie}",
    response_model=CategoryMetrics,
    summary="Métriques d'évaluation Prophet — une catégorie",
)
def get_metrics_categorie(categorie: str):
    """
    Retourne les métriques MAE/RMSE/MAPE pour une catégorie spécifique.

    - **categorie** : nom exact de la catégorie (ex: `00 - Ensemble`)
    """
    raw = _load_metrics()   # chargement complet du fichier

    if categorie not in raw:
        raise HTTPException(
            status_code=404,
            detail=f"Catégorie '{categorie}' absente de metrics.json",
        )

    return CategoryMetrics(**raw[categorie])   # désérialisation Pydantic
