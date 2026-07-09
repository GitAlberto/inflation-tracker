"""
C5 — Tests automatisés de l'API REST inflation-tracker
Issue GitHub : #11

Exécution :
    pytest tests/test_api.py -v

Preuves générées :
    pytest tests/test_api.py -v --tb=short > tests/resultats_tests_api.txt
"""

from fastapi.testclient import TestClient

from api.data.main import app

client = TestClient(app)


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

def test_inflation_sans_filtre_retourne_donnees():
    r = client.get("/api/inflation?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert len(body["data"]) == 5
    assert body["limit"] == 5


def test_inflation_filtre_pays_source():
    r = client.get("/api/inflation?pays=FR&source=INSEE&limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 936
    for row in body["data"]:
        assert row["pays"] == "FR"
        assert row["source"] == "INSEE"


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


def test_inflation_pays_inexistant_retourne_vide():
    r = client.get("/api/inflation?pays=XX&limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["data"] == []


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

def test_tendance_retourne_12_points_annee():
    r = client.get(
        "/api/inflation/tendance?pays=DE&source=EUROSTAT"
        "&date_debut=2024-01-01&date_fin=2024-12-31"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["nb_points"] == 12
    assert body["pays"] == "DE"
    assert body["source"] == "EUROSTAT"
    for point in body["data"]:
        assert "mois" in point
        assert "valeur_moy" in point
        assert "nb_categories" in point


def test_tendance_params_obligatoires():
    r = client.get("/api/inflation/tendance")
    assert r.status_code == 422  # pays et source obligatoires


# =============================================================================
# /api/inflation/pays — sources — categories
# =============================================================================

def test_liste_pays():
    r = client.get("/api/inflation/pays")
    assert r.status_code == 200
    pays = r.json()["pays"]
    assert "FR" in pays
    assert "DE" in pays
    assert len(pays) > 10  # 27 pays UE minimum


def test_liste_sources():
    r = client.get("/api/inflation/sources")
    assert r.status_code == 200
    sources = r.json()["sources"]
    assert set(sources) == {"ECB", "INSEE", "DATAGOUV", "EUROSTAT"}


def test_liste_categories_filtree_par_source():
    r = client.get("/api/inflation/categories?source=INSEE")
    assert r.status_code == 200
    cats = r.json()["categories"]
    assert len(cats) == 13  # 13 séries IPC INSEE
    assert "00 - Ensemble" in cats


# =============================================================================
# /api/prix-alimentaires
# =============================================================================

def test_prix_alimentaires_retourne_donnees():
    r = client.get("/api/prix-alimentaires?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert len(body["data"]) == 10


def test_prix_alimentaires_filtre_categorie():
    r = client.get("/api/prix-alimentaires?categorie=tomatoes&limit=50")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 27
    for row in body["data"]:
        assert "tomat" in row["categorie"].lower()


def test_prix_alimentaires_stats_pommes():
    r = client.get("/api/prix-alimentaires/stats?categorie=apples")
    assert r.status_code == 200
    data = r.json()["data"]
    pommes = next(d for d in data if d["categorie"] == "apples")
    assert pommes["prix_moy"] == 3.38
    assert pommes["prix_min"] == 1.99
    assert pommes["prix_max"] == 4.3
    assert pommes["nb_produits"] == 14


def test_prix_alimentaires_categories():
    r = client.get("/api/prix-alimentaires/categories")
    assert r.status_code == 200
    cats = r.json()["categories"]
    assert len(cats) > 0
    assert "tomatoes" in cats
    assert "apples" in cats
