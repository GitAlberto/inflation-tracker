"""
=============================================================================
C10 — Client API modèle — inflation-tracker
=============================================================================
Module HTTP qui appelle l'API modèle Prophet (api/model/, port 8002)
depuis l'application Streamlit.

Toutes les fonctions retournent None si l'API est indisponible,
ce qui permet à Streamlit d'afficher un message d'erreur gracieux
sans lever d'exception et sans crasher l'interface.

Issue GitHub : #16 (C10)
=============================================================================
"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Chargement de .env pour MODEL_API_URL et MODEL_API_TIMEOUT
ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", override=True)

# URL de base de l'API modèle — surchargeable via .env pour le déploiement
MODEL_API_URL = os.getenv("MODEL_API_URL", "http://localhost:8002")
# Clé API — lue depuis .env, envoyée dans chaque requête via header X-API-Key (C9/C10)
_API_KEY = os.getenv("API_KEY", "")
# Header d'authentification injecté dans toutes les requêtes protégées
_HEADERS = {"X-API-Key": _API_KEY}

# Timeout standard (secondes) pour les appels rapides (health, categories, metrics)
_TIMEOUT_SHORT = int(os.getenv("MODEL_API_TIMEOUT", "10"))

# Timeout étendu pour predict_all (chargement de 12 modèles en mémoire)
_TIMEOUT_LONG = max(_TIMEOUT_SHORT, 60)


# =============================================================================
# Santé de l'API
# =============================================================================

def get_health() -> dict | None:
    """
    Vérifie que l'API modèle est opérationnelle.

    Returns:
        dict {"status": "ok", "service": ..., "version": ...}
        ou None si l'API est inaccessible (service non démarré, réseau)
    """
    try:
        resp = requests.get(f"{MODEL_API_URL}/health", timeout=_TIMEOUT_SHORT)
        resp.raise_for_status()   # lève RequestException si status >= 400
        return resp.json()
    except requests.RequestException:
        return None   # API indisponible — Streamlit affichera un warning


# =============================================================================
# Catégories disponibles
# =============================================================================

def get_categories() -> list[str] | None:
    """
    Retourne la liste des catégories IPC pour lesquelles un modèle est disponible.

    Returns:
        list[str] de noms de catégories (ex: ["00 - Ensemble", "01 - Alimentation..."])
        ou None si erreur
    """
    try:
        resp = requests.get(f"{MODEL_API_URL}/api/categories", headers=_HEADERS, timeout=_TIMEOUT_SHORT)
        resp.raise_for_status()
        return resp.json()   # liste de strings
    except requests.RequestException:
        return None


# =============================================================================
# Métriques d'évaluation
# =============================================================================

def get_metrics() -> dict | None:
    """
    Retourne les métriques MAE/RMSE/MAPE pour toutes les catégories.

    Returns:
        dict avec clés "nb_categories", "eval_period", "metrics"
        ou None si erreur
    """
    try:
        resp = requests.get(f"{MODEL_API_URL}/api/metrics", headers=_HEADERS, timeout=_TIMEOUT_SHORT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


def get_metrics_categorie(categorie: str) -> dict | None:
    """
    Retourne les métriques MAE/RMSE/MAPE pour une catégorie spécifique.

    Args:
        categorie : nom exact de la catégorie (ex: "00 - Ensemble")

    Returns:
        dict avec clés "MAE", "RMSE", "MAPE_pct", "n_train", "n_eval"
        ou None si erreur ou catégorie inconnue
    """
    try:
        resp = requests.get(
            f"{MODEL_API_URL}/api/metrics/{categorie}",
            headers=_HEADERS,
            timeout=_TIMEOUT_SHORT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


# =============================================================================
# Prédictions
# =============================================================================

def predict_categorie(categorie: str, horizon: int = 12) -> dict | None:
    """
    Appelle GET /api/predict/{categorie}?horizon=N sur l'API modèle.

    Args:
        categorie : nom exact de la catégorie IPC (ex: "00 - Ensemble")
        horizon   : nombre de mois à prédire (1 à 36, défaut 12)

    Returns:
        dict avec clés "categorie", "horizon", "predictions", "variation_totale", "generated_at"
        Chaque prediction : {"date_pred": "YYYY-MM-DD", "yhat": ..., "yhat_lower": ..., "yhat_upper": ...}
        ou None si l'API est indisponible ou la catégorie introuvable
    """
    try:
        resp = requests.get(
            f"{MODEL_API_URL}/api/predict/{categorie}",
            params={"horizon": horizon},
            headers=_HEADERS,
            timeout=_TIMEOUT_SHORT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


def predict_all(horizon: int = 12) -> dict | None:
    """
    Appelle GET /api/predict?horizon=N pour toutes les catégories.

    Note : peut prendre jusqu'à 30 secondes (chargement de 13 modèles .pkl).
    Un timeout long est utilisé automatiquement.

    Args:
        horizon : nombre de mois à prédire

    Returns:
        dict {categorie: PredictionResponse} pour les 13 catégories
        ou None si l'API est indisponible
    """
    try:
        resp = requests.get(
            f"{MODEL_API_URL}/api/predict",
            params={"horizon": horizon},
            headers=_HEADERS,
            timeout=_TIMEOUT_LONG,   # timeout étendu : 12 modèles à charger
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None
