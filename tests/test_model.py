"""
=============================================================================
C12 — Tests unitaires modèle Prophet — inflation-tracker
=============================================================================
Tests purs (sans base de données, sans .pkl) pour les fonctions utilitaires
de model/train.py et model/predict.py.

Ces tests s'exécutent en local ET en CI sans aucune dépendance externe.

Couvre :
    - slugify()         : conversion nom catégorie → nom de fichier
    - compute_metrics() : calcul MAE / RMSE / MAPE
    - list_available()  : lecture metrics.json
    - metrics.json      : structure et cohérence des valeurs

Lancement :
    pytest tests/test_model.py -v

Issue GitHub : #18 (C12)
=============================================================================
"""

import json
from pathlib import Path

import numpy as np
import pytest

# Import des fonctions utilitaires — aucune dépendance PostgreSQL ou .pkl
from model.predict import list_available, slugify
from model.train import compute_metrics


# =============================================================================
# slugify() — conversion nom catégorie → slug de fichier
# =============================================================================

def test_slugify_ensemble():
    """Cas de base : '00 - Ensemble' → '00_ensemble'."""
    assert slugify("00 - Ensemble") == "00_ensemble"


def test_slugify_minuscules():
    """Le slug doit être entièrement en minuscules."""
    result = slugify("01 - Alimentation")
    assert result == result.lower()   # pas de majuscules dans le slug


def test_slugify_sans_espaces():
    """Les espaces doivent être remplacés par des underscores."""
    result = slugify("07 - Transports")
    assert " " not in result   # aucun espace dans le nom de fichier


def test_slugify_sans_tirets():
    """Les tirets et caractères spéciaux doivent être remplacés par _."""
    result = slugify("00 - Ensemble")
    assert "-" not in result   # pas de tirets dans le slug


def test_slugify_caracteres_accentues():
    """Les accents doivent être remplacés (non-ASCII → _)."""
    result = slugify("04 - Logement, eau, gaz, électricité")
    assert "é" not in result   # caractère accentué absent du slug
    assert "," not in result   # virgule absente du slug


def test_slugify_sans_underscore_initial():
    """Pas d'underscore en début ou fin de slug."""
    result = slugify("00 - Ensemble")
    assert not result.startswith("_")   # pas de _ initial
    assert not result.endswith("_")     # pas de _ final


# =============================================================================
# compute_metrics() — MAE / RMSE / MAPE
# =============================================================================

def test_compute_metrics_prediction_parfaite():
    """Prédiction identique aux vraies valeurs → MAE=0, RMSE=0, MAPE=0."""
    y = np.array([100.0, 101.0, 102.0, 103.0])
    m = compute_metrics(y, y)   # prédiction parfaite
    assert m["MAE"] == 0.0
    assert m["RMSE"] == 0.0
    assert m["MAPE_pct"] == 0.0


def test_compute_metrics_valeurs_connues():
    """MAE = 2 sur erreurs constantes de ±2 pts IPC."""
    y_true = np.array([100.0, 100.0])
    y_pred = np.array([102.0, 98.0])   # erreur absolue = 2 à chaque fois
    m = compute_metrics(y_true, y_pred)
    assert m["MAE"] == pytest.approx(2.0)    # (2 + 2) / 2 = 2
    assert m["MAPE_pct"] == pytest.approx(2.0)   # (2% + 2%) / 2 = 2%


def test_compute_metrics_rmse_superieur_mae():
    """RMSE ≥ MAE — propriété mathématique fondamentale des métriques d'erreur."""
    y_true = np.array([100.0, 105.0, 110.0, 95.0])
    y_pred = np.array([101.0, 103.0, 115.0, 93.0])   # erreurs variables
    m = compute_metrics(y_true, y_pred)
    assert m["RMSE"] >= m["MAE"]   # RMSE pénalise plus les grandes erreurs


def test_compute_metrics_cles_presentes():
    """Le dict de métriques doit contenir exactement MAE, RMSE, MAPE_pct."""
    y = np.array([100.0, 105.0, 110.0])
    m = compute_metrics(y, y + 1.0)   # erreur constante de 1 pt IPC
    assert set(m.keys()) >= {"MAE", "RMSE", "MAPE_pct"}   # clés requises présentes


def test_compute_metrics_positifs():
    """MAE et RMSE doivent toujours être positifs ou nuls."""
    y_true = np.array([100.0, 102.0, 98.0])
    y_pred = np.array([101.0, 100.0, 99.0])
    m = compute_metrics(y_true, y_pred)
    assert m["MAE"] >= 0       # erreur absolue toujours positive
    assert m["RMSE"] >= 0      # idem
    assert m["MAPE_pct"] >= 0  # pourcentage toujours positif


# =============================================================================
# list_available() — lecture de metrics.json
# =============================================================================

def test_list_available_retourne_liste():
    """list_available() doit retourner une liste (éventuellement vide si pas de metrics.json)."""
    result = list_available()
    assert isinstance(result, list)   # toujours une liste, jamais None


def test_list_available_13_categories():
    """13 catégories IPC France doivent être disponibles après train.py."""
    cats = list_available()
    assert len(cats) == 13   # 13 modèles Prophet entraînés en C8


def test_list_available_contient_ensemble():
    """La catégorie agrégée '00 - Ensemble' doit toujours être disponible."""
    cats = list_available()
    assert "00 - Ensemble" in cats   # catégorie principale IPC France


# =============================================================================
# metrics.json — structure et cohérence
# =============================================================================

def test_metrics_json_existe():
    """metrics.json doit exister après exécution de model/train.py."""
    path = Path("model/metrics.json")
    assert path.exists(), "metrics.json introuvable — exécutez : python model/train.py"


def test_metrics_json_cles_requises():
    """Chaque entrée de metrics.json doit contenir MAE, RMSE, MAPE_pct, n_train, n_eval."""
    path = Path("model/metrics.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for cat, m in data.items():
        assert "MAE" in m,       f"Clé MAE manquante pour '{cat}'"
        assert "RMSE" in m,      f"Clé RMSE manquante pour '{cat}'"
        assert "MAPE_pct" in m,  f"Clé MAPE_pct manquante pour '{cat}'"
        assert "n_train" in m,   f"Clé n_train manquante pour '{cat}'"
        assert "n_eval" in m,    f"Clé n_eval manquante pour '{cat}'"


def test_metrics_json_mae_positif():
    """Toutes les MAE doivent être positives et RMSE ≥ MAE pour chaque catégorie."""
    path = Path("model/metrics.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for cat, m in data.items():
        assert m["MAE"] >= 0,             f"MAE négative pour '{cat}'"
        assert m["RMSE"] >= m["MAE"],     f"RMSE < MAE pour '{cat}' (incohérent)"
        assert m["n_train"] == 60,        f"n_train ≠ 60 pour '{cat}' (split 2020-2024)"
        assert m["n_eval"] == 12,         f"n_eval ≠ 12 pour '{cat}' (2025 = 12 mois)"
