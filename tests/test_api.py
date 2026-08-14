"""
C5/C12 — Tests automatisés de l'API data REST inflation-tracker
Issue GitHub : #11 (C5), #18 (C12)

Exécution :
    pytest tests/test_api.py -v

Tests CI (sans DB) :
    pytest tests/test_api.py -v -m "not requires_db"

Preuves générées :
    pytest tests/test_api.py -v --tb=short > tests/resultats_tests_api.txt
"""

import os

import pytest
from fastapi.testclient import TestClient

# Valeur de repli pour CI (pas de .env) — définie avant l'import pour que
# load_dotenv dans database.py ne la trouve pas déjà dans l'env
os.environ.setdefault("API_KEY", "test-key")

from api.data.main import app  # noqa: E402

# Lire la clé effective APRÈS que load_dotenv ait tourné pendant l'import
_TEST_KEY = os.getenv("API_KEY", "test-key")

# Toutes les routes protégées par X-API-Key — le client l'envoie par défaut
client = TestClient(app, headers={"X-API-Key": _TEST_KEY})

# Marqueur : tests nécessitant une base PostgreSQL peuplée
# → passent en local avec Docker, skippés en CI (pas de données chargées)
requires_db = pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Requires a populated PostgreSQL database — skipped in CI",
)


# =============================================================================
# Health
# =============================================================================

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "inflation-tracker-api-data"


# =============================================================================
# /api/inflation
# =============================================================================

@requires_db
def test_inflation_sans_filtre_retourne_donnees():
    r = client.get("/api/inflation?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert len(body["data"]) == 5
    assert body["limit"] == 5


@requires_db
def test_inflation_filtre_source():
    r = client.get("/api/inflation?source=INSEE&limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    for row in body["data"]:
        assert row["source"] == "INSEE"


@requires_db
def test_inflation_filtre_date():
    r = client.get(
        "/api/inflation?pays=FR&source=INSEE"
        "&categorie=00&date_debut=2025-12-01&date_fin=2025-12-31"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["data"][0]["valeur"] == "120.9000"
    assert body["data"][0]["date_obs"] == "2025-12-01"


@requires_db
def test_inflation_pagination():
    r1 = client.get("/api/inflation?source=ECB&limit=5&offset=0")
    r2 = client.get("/api/inflation?source=ECB&limit=5&offset=5")
    assert r1.status_code == 200
    assert r2.status_code == 200
    ids1 = [row["date_obs"] + row["categorie"] for row in r1.json()["data"]]
    ids2 = [row["date_obs"] + row["categorie"] for row in r2.json()["data"]]
    assert ids1 != ids2


def test_inflation_limit_max_1000():
    r = client.get("/api/inflation?limit=1001")
    assert r.status_code == 422  # validation Pydantic


# =============================================================================
# /api/inflation/tendance
# =============================================================================

@requires_db
def test_tendance_retourne_12_points_annee():
    r = client.get(
        "/api/inflation/tendance?source=INSEE"
        "&date_debut=2024-01-01&date_fin=2024-12-31"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["nb_points"] == 12
    assert body["pays"] == "FR"
    assert body["source"] == "INSEE"
    for point in body["data"]:
        assert "mois" in point
        assert "valeur_moy" in point
        assert "nb_categories" in point


def test_tendance_params_obligatoires():
    r = client.get("/api/inflation/tendance")
    assert r.status_code == 422  # source obligatoire


# =============================================================================
# /api/inflation/sources — categories
# =============================================================================

@requires_db
def test_liste_sources():
    r = client.get("/api/inflation/sources")
    assert r.status_code == 200
    sources = r.json()["sources"]
    assert set(sources) == {"ECB", "INSEE", "DATAGOUV", "EUROSTAT"}


@requires_db
def test_liste_categories_filtree_par_source():
    r = client.get("/api/inflation/categories?source=INSEE")
    assert r.status_code == 200
    cats = r.json()["categories"]
    assert len(cats) == 12  # 12 catégories COICOP normalisées (00-11)
    assert "00 - Ensemble" in cats


# =============================================================================
# /api/inflation/top-categories
# =============================================================================

@requires_db
def test_top_categories_retourne_n_resultats():
    r = client.get("/api/inflation/top-categories?source=EUROSTAT&limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "EUROSTAT"
    assert body["nb_categories"] == 5
    assert len(body["data"]) == 5
    rangs = [row["rang"] for row in body["data"]]
    assert rangs == [1, 2, 3, 4, 5]
    # tri décroissant vérifié
    moyennes = [row["inflation_moy"] for row in body["data"]]
    assert moyennes == sorted(moyennes, reverse=True)


@requires_db
def test_top_categories_pic_superieur_ou_egal_moy():
    r = client.get("/api/inflation/top-categories?source=INSEE&limit=3")
    assert r.status_code == 200
    for row in r.json()["data"]:
        assert row["pic"] >= row["inflation_moy"]


# =============================================================================
# /api/inflation/comparaison-sources
# =============================================================================

def test_comparaison_sources_categorie_obligatoire():
    r = client.get("/api/inflation/comparaison-sources")
    assert r.status_code == 422


@requires_db
def test_comparaison_sources_alimentation():
    r = client.get("/api/inflation/comparaison-sources?categorie=alimentation")
    assert r.status_code == 200
    body = r.json()
    assert body["nb_sources"] > 0
    sources = [row["source"] for row in body["data"]]
    assert "INSEE" in sources
    for row in body["data"]:
        assert row["valeur_max"] >= row["valeur_moy"] >= row["valeur_min"]
        assert row["nb_observations"] > 0


# =============================================================================
# /api/inflation/resume
# =============================================================================

@requires_db
def test_resume_structure():
    r = client.get("/api/inflation/resume")
    assert r.status_code == 200
    body = r.json()
    assert body["total_observations"] > 0
    assert body["nb_sources"] == 4
    assert set(s["source"] for s in body["sources"]) == {"ECB", "INSEE", "DATAGOUV", "EUROSTAT"}
    ipc = body["derniere_valeur_ipc"]
    assert ipc["valeur"] is not None
    assert ipc["source"] == "INSEE"
    assert ipc["categorie"] == "00 - Ensemble"


# =============================================================================
# /api/prix-alimentaires
# =============================================================================

@requires_db
def test_prix_alimentaires_retourne_donnees():
    r = client.get("/api/prix-alimentaires?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert len(body["data"]) == 10


@requires_db
def test_prix_alimentaires_filtre_categorie():
    r = client.get("/api/prix-alimentaires?categorie=tomatoes&limit=50")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0   # volume variable selon les données Open Food Facts chargées
    for row in body["data"]:
        assert "tomat" in row["categorie"].lower()


@requires_db
def test_prix_alimentaires_stats_pommes():
    r = client.get("/api/prix-alimentaires/stats?categorie=apples")
    assert r.status_code == 200
    data = r.json()["data"]
    pommes = next(d for d in data if d["categorie"] == "apples")
    assert pommes["prix_moy"] > 0           # prix moyen positif (variable selon données)
    assert pommes["prix_min"] >= 0          # valeur positive
    assert pommes["prix_max"] >= pommes["prix_moy"]  # cohérence min/max/moy
    assert pommes["nb_produits"] > 0


@requires_db
def test_prix_alimentaires_categories():
    r = client.get("/api/prix-alimentaires/categories")
    assert r.status_code == 200
    cats = r.json()["categories"]
    assert len(cats) > 0
    assert "tomatoes" in cats
    assert "apples" in cats
