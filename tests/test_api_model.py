"""
=============================================================================
C9 — Tests API modèle Prophet — inflation-tracker
=============================================================================
Tests d'intégration de l'API modèle via FastAPI TestClient.

Couvre :
    - Health check
    - Liste des catégories
    - Métriques toutes catégories + une catégorie
    - Prédictions une catégorie + toutes catégories
    - Validation des paramètres (horizon hors bornes → 422)
    - Codes d'erreur (catégorie inexistante → 404)

Lancement :
    pytest tests/test_api_model.py -v

Issue GitHub : #15 (C9)
=============================================================================
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.model.main import app   # import de l'application FastAPI C9

# Client de test FastAPI — simule des requêtes HTTP sans démarrer un serveur réel
client = TestClient(app)

# Catégorie valide utilisée dans tous les tests de prédiction
CAT_VALID = "00 - Ensemble"
# Catégorie qui n'existe pas dans metrics.json
CAT_INVALID = "99 - Catégorie inexistante"

# Marqueur : tests nécessitant les modèles .pkl entraînés localement
# → passent en local après model/train.py, skippés en CI (fichiers gitignorés)
requires_models = pytest.mark.skipif(
    not Path("model/prophet_00_ensemble.pkl").exists(),
    reason="Requires trained Prophet models (.pkl) — run model/train.py first",
)


# =============================================================================
# Health check
# =============================================================================

def test_health():
    """L'API modèle doit répondre 200 avec le bon nom de service."""
    resp = client.get("/health")                              # requête GET /health
    assert resp.status_code == 200                            # code HTTP attendu
    data = resp.json()
    assert data["status"] == "ok"                            # API opérationnelle
    assert data["service"] == "inflation-tracker-api-model"  # nom de service C9
    assert data["version"] == "1.0.0"                        # version courante


# =============================================================================
# Catégories disponibles
# =============================================================================

def test_categories_returns_list():
    """GET /categories doit retourner une liste non vide de catégories."""
    resp = client.get("/api/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)          # réponse de type liste
    assert len(data) > 0                   # au moins une catégorie disponible


def test_categories_contains_ensemble():
    """La catégorie '00 - Ensemble' doit être dans la liste."""
    resp = client.get("/api/categories")
    assert resp.status_code == 200
    assert CAT_VALID in resp.json()        # catégorie principale toujours présente


def test_categories_count():
    """L'API doit exposer les 13 catégories INSEE entraînées."""
    resp = client.get("/api/categories")
    assert resp.status_code == 200
    assert len(resp.json()) == 13          # 13 modèles Prophet entraînés en C8


# =============================================================================
# Métriques
# =============================================================================

def test_metrics_structure():
    """GET /metrics doit retourner nb_categories, eval_period et metrics."""
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "nb_categories" in data         # nombre de modèles
    assert "eval_period" in data           # période d'évaluation
    assert "metrics" in data               # dict de métriques par catégorie
    assert data["nb_categories"] == 13     # 13 catégories entraînées


def test_metrics_categorie_valide():
    """GET /metrics/{categorie} doit retourner MAE, RMSE, MAPE_pct, n_train, n_eval."""
    resp = client.get(f"/api/metrics/{CAT_VALID}")
    assert resp.status_code == 200
    data = resp.json()
    assert "MAE" in data                   # erreur absolue moyenne
    assert "RMSE" in data                  # erreur quadratique
    assert "MAPE_pct" in data              # erreur relative en %
    assert "n_train" in data               # nb points d'entraînement
    assert "n_eval" in data                # nb points d'évaluation
    assert data["n_train"] == 60           # 2020-2024 = 60 mois
    assert data["n_eval"] == 12            # 2025 = 12 mois


def test_metrics_categorie_invalide():
    """GET /metrics/{categorie} avec catégorie inconnue doit retourner 404."""
    resp = client.get(f"/api/metrics/{CAT_INVALID}")
    assert resp.status_code == 404         # catégorie absente de metrics.json


# =============================================================================
# Prédictions — une catégorie
# =============================================================================

@requires_models
def test_predict_categorie_defaut():
    """GET /predict/{categorie} doit retourner 12 prédictions par défaut."""
    resp = client.get(f"/api/predict/{CAT_VALID}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["categorie"] == CAT_VALID  # catégorie correcte dans la réponse
    assert data["horizon"] == 12           # horizon par défaut
    assert len(data["predictions"]) == 12  # 12 points de prédiction
    assert "variation_totale" in data      # variation IPC calculée
    assert "generated_at" in data          # horodatage présent


@requires_models
def test_predict_categorie_structure_point():
    """Chaque point de prédiction doit contenir date_pred, yhat, yhat_lower, yhat_upper."""
    resp = client.get(f"/api/predict/{CAT_VALID}")
    assert resp.status_code == 200
    point = resp.json()["predictions"][0]  # premier point de prédiction
    assert "date_pred" in point            # date au format YYYY-MM-DD
    assert "yhat" in point                 # valeur centrale
    assert "yhat_lower" in point           # borne basse IC 80%
    assert "yhat_upper" in point           # borne haute IC 80%
    # L'intervalle de confiance doit être cohérent : lower <= yhat <= upper
    assert point["yhat_lower"] <= point["yhat"] <= point["yhat_upper"]


@requires_models
def test_predict_categorie_horizon_custom():
    """GET /predict/{categorie}?horizon=6 doit retourner exactement 6 prédictions."""
    resp = client.get(f"/api/predict/{CAT_VALID}?horizon=6")
    assert resp.status_code == 200
    data = resp.json()
    assert data["horizon"] == 6            # horizon transmis
    assert len(data["predictions"]) == 6   # exactement 6 points


def test_predict_categorie_horizon_invalide():
    """horizon > 36 doit être rejeté avec 422 (validation Pydantic)."""
    resp = client.get(f"/api/predict/{CAT_VALID}?horizon=50")
    assert resp.status_code == 422         # Unprocessable Entity — hors borne max


def test_predict_categorie_invalide():
    """GET /predict/{categorie} avec catégorie inconnue doit retourner 404."""
    resp = client.get(f"/api/predict/{CAT_INVALID}")
    assert resp.status_code == 404         # catégorie sans modèle entraîné


# =============================================================================
# Prédictions — toutes catégories
# =============================================================================

@requires_models
def test_predict_toutes():
    """GET /predict doit retourner un dict avec les 13 catégories."""
    resp = client.get("/api/predict")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)          # réponse de type dict
    assert len(data) == 13                 # 13 catégories Prophet


@requires_models
def test_predict_toutes_contient_ensemble():
    """GET /predict doit inclure la catégorie '00 - Ensemble'."""
    resp = client.get("/api/predict")
    assert resp.status_code == 200
    assert CAT_VALID in resp.json()        # catégorie principale présente
