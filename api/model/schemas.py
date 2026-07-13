"""
=============================================================================
C9 — Schémas Pydantic — API modèle Prophet — inflation-tracker
=============================================================================
Définit les modèles de données pour les requêtes et réponses de l'API modèle.

Issue GitHub : #15 (C9)
=============================================================================
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


# =============================================================================
# Prédictions
# =============================================================================

class PredictionPoint(BaseModel):
    """Un point de prédiction Prophet pour un mois donné."""
    date_pred: date = Field(..., description="Premier jour du mois prédit (YYYY-MM-DD)")
    yhat: float      = Field(..., description="Indice IPC prédit (base 100 = 2015)")
    yhat_lower: float = Field(..., description="Borne basse intervalle de confiance 80%")
    yhat_upper: float = Field(..., description="Borne haute intervalle de confiance 80%")


class PredictionResponse(BaseModel):
    """Réponse complète d'un endpoint /predict — inclut série + méta-données."""
    categorie: str                          # nom exact de la catégorie IPC
    horizon: int                            # nombre de mois prédits
    predictions: list[PredictionPoint]      # série temporelle de prédictions
    variation_totale: float = Field(        # variation IPC sur la période (yhat[-1] - yhat[0])
        ...,
        description="Variation en points IPC entre le premier et le dernier mois prédit"
    )
    generated_at: datetime                  # horodatage de la génération (UTC)


# =============================================================================
# Métriques
# =============================================================================

class CategoryMetrics(BaseModel):
    """Métriques d'évaluation Prophet pour une catégorie — issues de metrics.json."""
    MAE: float       # Mean Absolute Error sur la période d'évaluation 2025
    RMSE: float      # Root Mean Squared Error
    MAPE_pct: float  # Mean Absolute Percentage Error (en %)
    n_train: int     # nombre de points d'entraînement (60 = 2020-2024)
    n_eval: int      # nombre de points d'évaluation (12 = 2025)


class MetricsResponse(BaseModel):
    """Réponse de l'endpoint /metrics — métriques de toutes les catégories."""
    nb_categories: int                        # nombre de modèles disponibles (13)
    eval_period: str                          # période d'évaluation ex: "2025-01 / 2025-12"
    metrics: dict[str, CategoryMetrics]       # {categorie: métriques}
