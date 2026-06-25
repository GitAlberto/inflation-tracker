# 🗺️ Roadmap — inflation-tracker
## Titre Professionnel Développeur en Intelligence Artificielle — C1 à C21

---

## 🎯 Concept du projet

### Problème adressé

Le kebab coûtait 3,50€ en 2019. Il en coûte 7€ en 2026. Pourquoi ? Et jusqu'où ces prix vont-ils encore monter ?

L'inflation est un phénomène que tout le monde subit mais que personne ne comprend vraiment. Les données existent — publiées chaque mois par l'INSEE, la BCE, Eurostat — mais elles sont dispersées, techniques, inaccessibles au grand public. Il n'existe pas d'outil simple qui agrège ces sources, les rende lisibles, et permette de prédire l'évolution des prix par catégorie de produit.

### Solution

**inflation-tracker** est un système complet de collecte, stockage, analyse et prédiction de l'inflation. Il agrège 5 sources de données hétérogènes dans une base PostgreSQL unifiée, expose ces données via une API REST, entraîne un modèle de prédiction de l'IPC par catégorie, et les présente dans une application Streamlit accessible à l'utilisateur final.

### Architecture globale du système

```
┌─────────────────────────────────────────────────────────────┐
│                     SOURCES DE DONNÉES                      │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ API      │ CSV      │ Scraping │ BDD      │ Big Data        │
│ INSEE    │ data.    │ Open     │ simulée  │ Eurostat bulk   │
│ BDM      │ gouv.fr  │ FoodFacts│ ← ECB   │ → PySpark       │
└────┬─────┴────┬─────┴────┬─────┴────┬─────┴────────┬────────┘
     │          │          │          │               │
     └──────────┴──────────┴──────────┴───────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Pipeline Python   │
                    │  Nettoyage /       │
                    │  Agrégation / C3   │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  PostgreSQL Final  │
                    │  Base unifiée      │
                    │  RGPD compliant    │
                    └─────────┬──────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    ┌─────────▼──────┐ ┌──────▼──────┐ ┌─────▼──────────┐
    │  API Data REST │ │  Modèle IA  │ │  Application   │
    │  FastAPI / C5  │ │  Prophet /  │ │  Streamlit     │
    │                │ │  LSTM / C8  │ │  Bloc 3        │
    └────────────────┘ └──────┬──────┘ └────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  API Modèle REST   │
                    │  /predict / C9     │
                    └────────────────────┘
```

### Les 5 sources de données

| # | Source | Technologie | Données collectées | Légal |
|---|--------|-------------|-------------------|-------|
| 1 | API INSEE BDM | API REST + clé gratuite | IPC France par catégorie, mensuel depuis 2000 | Licence Ouverte |
| 2 | data.gouv.fr | CSV direct download | Séries longues IPC depuis 1990, toutes catégories | Licence Ouverte |
| 3 | Open Food Facts | Scraping web (BeautifulSoup) | Prix produits alimentaires réels par catégorie | ODbL — scraping autorisé |
| 4 | BDD simulée ← ECB API | PostgreSQL pré-chargé via API ECB | Historique HICP zone euro 30 ans | ECB Open Data |
| 5 | Eurostat bulk | CSV massif → PySpark | 27 pays × 100+ catégories × 30 ans | CC BY |

### Destination finale

Toutes les sources sont nettoyées, normalisées et chargées dans une **base PostgreSQL unifiée**. C'est cette base qui alimente l'API data (Bloc 1), le modèle IA (Bloc 2), et l'application Streamlit (Bloc 3).

### Lien entre les 3 blocs

- **Bloc 1** → construit le socle data : collecte, nettoyage, stockage, API de mise à disposition
- **Bloc 2** → entraîne un modèle de prédiction IPC, l'expose via API, le monitore
- **Bloc 3** → application Streamlit qui consomme l'API du Bloc 2 et visualise les prédictions

---

## 📁 Structure du projet

```
inflation-tracker/
│
├── .github/
│   └── workflows/
│       ├── ci_data.yml              # CI/CD Bloc 1
│       ├── ci_model.yml             # CI/CD Bloc 2
│       └── ci_app.yml               # CI/CD Bloc 3
│
├── data/
│   ├── raw/                         # Données brutes par source
│   │   ├── insee_api/
│   │   ├── csv_datagouv/
│   │   ├── scraping_openfoodfacts/
│   │   ├── bdd_ecb/
│   │   └── bigdata_eurostat/
│   └── processed/                   # Données nettoyées prêtes pour PostgreSQL
│
├── src/
│   ├── collect/
│   │   ├── collect_insee_api.py     # C1 — collecte API INSEE BDM
│   │   ├── collect_csv.py           # C1 — lecture CSV data.gouv.fr
│   │   ├── scrape_openfoodfacts.py  # C1 — scraping Open Food Facts
│   │   ├── load_ecb_to_db.py        # C1/C4 — chargement BDD simulée
│   │   └── collect_eurostat_spark.py # C1 — big data PySpark
│   ├── sql/
│   │   ├── queries_extraction.sql   # C2 — requêtes SQL documentées
│   │   └── queries_analyse.sql      # C2 — requêtes analytiques
│   ├── aggregate/
│   │   └── aggregate_clean.py       # C3 — agrégation et nettoyage
│   └── database/
│       ├── schema.sql               # C4 — MCD/MPD + création tables
│       ├── import_data.py           # C4 — script d'import
│       └── rgpd_register.md         # C4 — registre RGPD
│
├── api/
│   ├── data/
│   │   ├── main.py                  # C5 — API data REST FastAPI
│   │   ├── schemas.py
│   │   └── auth.py
│   └── model/
│       ├── main.py                  # C9 — API modèle REST FastAPI
│       ├── schemas.py
│       └── auth.py
│
├── model/
│   ├── train.py                     # C8 — entraînement modèle
│   ├── predict.py                   # C8 — prédiction
│   ├── evaluate.py                  # C8/C12 — évaluation métriques
│   ├── inflation_model.pkl          # Modèle sérialisé
│   └── metrics.json                 # Métriques entraînement
│
├── app/
│   ├── main.py                      # C17 — Interface Streamlit
│   ├── api_client.py                # C10 — Client API modèle
│   └── currency.py                  # Conversion devises
│
├── monitoring/
│   ├── prometheus.yml               # Config Prometheus — targets à scraper
│   ├── alerts.yml                   # Règles d'alertes Prometheus
│   └── grafana/
│       ├── dashboards/
│       │   ├── model_dashboard.json # C11 — dashboard métriques modèle
│       │   └── app_dashboard.json   # C20 — dashboard métriques app
│       └── provisioning/
│           └── datasources.yml      # Config datasource Prometheus → Grafana
│
├── tests/
│   ├── test_collect.py              # C12 — tests collecte
│   ├── test_aggregate.py            # C12 — tests agrégation
│   ├── test_api_data.py             # C12 — tests API data
│   ├── test_model.py                # C12 — tests modèle
│   ├── test_api_model.py            # C12 — tests API modèle
│   └── test_app.py                  # C18 — tests application
│
├── docs/
│   ├── veille.md                    # C6
│   ├── benchmark.md                 # C7
│   ├── specs_fonctionnelles.md      # C14
│   ├── specs_techniques.md          # C15
│   ├── agile.md                     # C16
│   ├── monitoring.md                # C11/C20
│   └── incident.md                  # C21
│
├── notebooks/
│   ├── 01_eda_insee.ipynb
│   ├── 02_eda_eurostat.ipynb
│   └── 03_model_exploration.ipynb
│
├── .env                             # Non versionné
├── .gitignore
├── docker-compose.yml               # PostgreSQL + Prometheus + Grafana
├── requirements.txt
└── README.md
```

---

## ⏱️ Planning global — 8 semaines (25 juin → 20 août)

| Semaine | Dates | Focus | Compétences |
|---|---|---|---|
| S1 | 25 juin – 1 juil | Init + BDD simulée + CSV | C1 (partiel), C4 |
| S2 | 2 – 8 juil | API INSEE + Scraping + PySpark | C1 (complet), C2 |
| S3 | 9 – 15 juil | Agrégation + PostgreSQL final + API data | C3, C4, C5 |
| S4 | 16 – 22 juil | Veille + Benchmark + Modèle IA | C6, C7, C8 |
| S5 | 23 – 29 juil | API modèle + Intégration + Monitoring modèle | C9, C10, C11 |
| S6 | 30 juil – 5 août | Tests + CI/CD Bloc 1 & 2 | C12, C13 |
| S7 | 6 – 12 août | Application Streamlit + CI/CD Bloc 3 + Incident | C14–C21 |
| S8 | 13 – 20 août | Rapports + Slides + Révision + Soutenance blanche | Tout |

**Règle absolue** : capturer chaque erreur, chaque choix technique, chaque résultat en temps réel. Le dossier de preuves se construit au fur et à mesure — pas à la fin.

---

## BLOC 1 — C1 à C5 : Collecte, stockage, mise à disposition

---

### Phase 0 — Initialisation (Jour 1 — ce soir)
**Durée** : 20 minutes

- Créer le repo Git `inflation-tracker`
- Créer la structure de dossiers complète
- Créer `.gitignore`, `requirements.txt` de base, `README.md`
- Créer `docker-compose.yml` pour PostgreSQL local
- Premier commit + push
- **Capturer** : screenshot de la structure Git initiale → preuve C1 amorce

---

### Phase 1 — BDD simulée ECB (C1, C4)
**Durée** : 2-3 jours — Semaine 1
**Compétences** : C1 (source BDD), C4

**Ce qu'on fait**

Interroger l'API ECB pour récupérer l'historique HICP zone euro et le charger dans PostgreSQL. C'est la source "base de données" du référentiel.

```python
# src/collect/load_ecb_to_db.py
import requests
import pandas as pd
from sqlalchemy import create_engine

def fetch_ecb_hicp():
    url = "https://data-api.ecb.europa.eu/service/data/ICP/M.U2.N.000000.4.ANR"
    r = requests.get(url, params={"format": "csvdata"}, timeout=10)
    r.raise_for_status()
    return pd.read_csv(pd.io.common.StringIO(r.text))

def load_to_postgres(df, engine):
    df.to_sql("ecb_hicp_raw", engine, if_exists="replace", index=False)
    print(f"Chargé {len(df)} lignes dans ecb_hicp_raw")
```

**MCD/MPD à produire** (C4)

```
ecb_hicp_raw : id_pk | time_period | obs_value | ref_area | country | unit
insee_ipc    : id_pk | date_obs | valeur | categorie | sous_categorie | source
openfoodfacts: id_pk | produit | categorie | prix_unitaire | date_collecte | url
eurostat_bulk: id_pk | pays | coicop | date_obs | valeur | unite
inflation_unified : id_pk | date_obs | pays | categorie | valeur | source | created_at
```

**Registre RGPD** (C4)

Open Food Facts peut contenir des données de produits avec marques et localisations. Documenter dans `docs/rgpd_register.md` : aucune donnée personnelle collectée, données de prix publiques, principe de minimisation appliqué.

**Livrables phase 1**
- `src/collect/load_ecb_to_db.py` fonctionnel
- `src/database/schema.sql` avec MCD/MPD commenté
- `src/database/import_data.py`
- `docs/rgpd_register.md`
- PostgreSQL qui tourne en local (Docker)
- **Captures** : schéma BDD, données chargées, commande d'exécution

---

### Phase 2 — Collecte multi-sources (C1)
**Durée** : 4-5 jours — Semaine 2
**Compétence** : C1

**Source 1 — API INSEE BDM**

```python
# src/collect/collect_insee_api.py
import requests

INSEE_API_KEY = os.getenv("INSEE_API_KEY")
BASE_URL = "https://api.insee.fr/series/BDM/V1/data/SERIES_BDM"

def fetch_ipc_series(idbank: str) -> dict:
    """
    Fetch une série IPC par son identifiant INSEE.
    Ex: 001763415 = IPC alimentation France
    """
    headers = {"Authorization": f"Bearer {INSEE_API_KEY}"}
    r = requests.get(f"{BASE_URL}/{idbank}", headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()
```

Séries à collecter :
- `001763415` — IPC alimentation
- `001768560` — IPC énergie
- `001768618` — IPC services
- `001763852` — IPC logement
- `001763853` — IPC ensemble hors tabac

**Source 2 — CSV data.gouv.fr**

```python
# src/collect/collect_csv.py
import pandas as pd

CSV_URL = "https://www.data.gouv.fr/api/1/datasets/r/..."

def load_ipc_csv() -> pd.DataFrame:
    df = pd.read_csv(CSV_URL, sep=";", encoding="utf-8")
    return df
```

**Source 3 — Scraping Open Food Facts**

```python
# src/scrape_openfoodfacts.py
import requests
from bs4 import BeautifulSoup

def scrape_category_prices(category: str, pages: int = 5) -> list:
    """
    Scrape les prix de produits d'une catégorie sur Open Food Facts.
    Licence ODbL — scraping autorisé.
    """
    results = []
    for page in range(1, pages + 1):
        url = f"https://fr.openfoodfacts.org/categorie/{category}/{page}.json"
        r = requests.get(url, timeout=10)
        data = r.json()
        for product in data.get("products", []):
            results.append({
                "produit": product.get("product_name"),
                "categorie": category,
                "prix_unitaire": product.get("price"),
                "date_collecte": datetime.utcnow().isoformat(),
                "url": f"https://fr.openfoodfacts.org/produit/{product.get('id')}"
            })
    return results
```

**Source 5 — Big Data Eurostat + PySpark**

```python
# src/collect/collect_eurostat_spark.py
from pyspark.sql import SparkSession
import requests

def download_eurostat_bulk(dataset_code: str = "prc_hicp_manr"):
    """
    Télécharge le bulk CSV Eurostat et le traite avec PySpark.
    Volume : ~500Mo décompressé, plusieurs millions de lignes.
    """
    spark = SparkSession.builder \
        .appName("InflationTracker") \
        .getOrCreate()

    url = f"https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{dataset_code}/?format=CSV"
    # Téléchargement + lecture Spark
    df = spark.read.csv(url, header=True, inferSchema=True)
    df.createOrReplaceTempView("eurostat_hicp")
    
    # Requête Spark SQL
    result = spark.sql("""
        SELECT geo, time, obsValue, coicop
        FROM eurostat_hicp
        WHERE geo = 'FR'
        ORDER BY time DESC
    """)
    return result
```

**Livrables phase 2**
- 5 scripts de collecte fonctionnels
- Logs d'exécution pour chaque source
- Arborescence `data/raw/` peuplée
- **Captures** : terminal d'exécution de chaque script, logs, fichiers bruts produits

---

### Phase 3 — SQL, agrégation, nettoyage (C2, C3)
**Durée** : 3 jours — Semaine 2-3
**Compétences** : C2, C3

**C2 — Requêtes SQL documentées**

```sql
-- queries_extraction.sql

-- Extraction IPC alimentation France depuis ECB
SELECT
    time_period,
    obs_value AS ipc_alimentation,
    'ECB' AS source
FROM ecb_hicp_raw
WHERE ref_area = 'FR'
  AND time_period >= '2019-01'
ORDER BY time_period;

-- Jointure IPC INSEE + Eurostat par catégorie
SELECT
    i.date_obs,
    i.categorie,
    i.valeur AS ipc_insee,
    e.valeur AS ipc_eurostat,
    ABS(i.valeur - e.valeur) AS ecart
FROM insee_ipc i
LEFT JOIN eurostat_bulk e
    ON i.date_obs = e.date_obs
    AND i.categorie = e.coicop
WHERE i.date_obs >= '2015-01-01'
ORDER BY i.date_obs;
```

Chaque requête est documentée : pourquoi cette sélection, ce filtre, cette jointure.

**C3 — Agrégation et nettoyage**

```python
# src/aggregate/aggregate_clean.py

def aggregate_all_sources(conn) -> pd.DataFrame:
    """
    Agrège les 5 sources dans un jeu de données unifié.
    Règles appliquées :
    - Suppression des doublons (même date + même catégorie + même source)
    - Homogénéisation des formats de date → ISO 8601
    - Normalisation des catégories → nomenclature COICOP
    - Suppression des valeurs nulles ou aberrantes (IPC < 0 ou > 200)
    - Conversion des unités → indice base 100 = 2015
    """
    dfs = []
    # Chargement de chaque source...
    # Nettoyage et normalisation...
    # Union finale...
    return df_unified
```

**Livrables phase 3**
- `src/sql/queries_extraction.sql` avec 5+ requêtes documentées
- `src/aggregate/aggregate_clean.py` fonctionnel
- Dataset final dans PostgreSQL
- **Captures** : résultats des requêtes SQL, tableau avant/après nettoyage, volume final

---

### Phase 4 — API data REST (C5)
**Durée** : 3 jours — Semaine 3
**Compétence** : C5

```python
# api/data/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import APIKeyHeader

app = FastAPI(title="Inflation Tracker — API Data", version="1.0.0")

@app.get("/ipc/{categorie}")
async def get_ipc(categorie: str, start: str, end: str, api_key: str = Depends(verify_key)):
    """
    Retourne les valeurs IPC pour une catégorie et une période.
    Catégories : alimentation, energie, services, logement, ensemble
    """
    ...

@app.get("/ipc/categories")
async def list_categories(api_key: str = Depends(verify_key)):
    """Liste toutes les catégories disponibles"""
    ...

@app.get("/ipc/evolution/{annee}")
async def get_evolution(annee: int, api_key: str = Depends(verify_key)):
    """Évolution annuelle moyenne de l'IPC par catégorie"""
    ...
```

**Livrables phase 4**
- `api/data/main.py` avec 5+ endpoints
- Documentation OpenAPI via `/docs`
- Authentification X-API-Key
- Tests des endpoints
- **Captures** : Swagger UI, requête/réponse exemple

---

## BLOC 2 — C6 à C13 : Service IA, API modèle, MLOps

---

### Phase 5 — Veille et benchmark (C6, C7)
**Durée** : 2 jours — Semaine 4
**Compétences** : C6, C7

**C6 — Veille** (`docs/veille.md`)

Thématique : ML appliqué à la prédiction de séries temporelles économiques (IPC, inflation)

Contenu :
- État de l'art : ARIMA, Prophet, LSTM, XGBoost sur séries temporelles
- Réglementation : RGPD sur les données économiques, réutilisation des données BCE/INSEE
- Sources qualifiées : publications BCE, documents INSEE, papers NeurIPS/ICML
- Synthèse et recommandation

**C7 — Benchmark** (`docs/benchmark.md`)

Services comparés :

| Critère | Prophet (Meta) | LSTM (Keras) | XGBoost |
|---|---|---|---|
| Performance séries temporelles | Très bonne | Excellente | Bonne |
| Complexité | Faible | Élevée | Moyenne |
| Interprétabilité | Bonne (composantes) | Faible | Moyenne |
| Saisonnalité native | Oui | Non (à coder) | Non |
| Éco-responsabilité | Légère | Lourde (GPU) | Moyenne |
| Intégration FastAPI | Simple (joblib) | Moyenne (h5) | Simple |

**Choix retenu : Prophet** — capte naturellement la saisonnalité annuelle de l'inflation (hausse estivale des prix, effets janvier), interprétable, déployable sans GPU.

---

### Phase 6 — Modèle IA (C8)
**Durée** : 3-4 jours — Semaine 4
**Compétence** : C8

```python
# model/train.py
from prophet import Prophet
import pandas as pd
import json
import joblib

def train_inflation_model(df: pd.DataFrame, categorie: str) -> Prophet:
    """
    Entraîne un modèle Prophet pour prédire l'IPC d'une catégorie.
    Input : df avec colonnes ds (date) et y (valeur IPC)
    """
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=0.05  # Régularisation — justifier ce choix
    )
    model.fit(df)
    return model

def evaluate_model(model: Prophet, df_test: pd.DataFrame) -> dict:
    forecast = model.predict(df_test)
    mae = abs(forecast["yhat"] - df_test["y"]).mean()
    return {"mae": round(mae, 4), "categorie": "alimentation"}
```

**Questions à savoir répondre au jury**
- Pourquoi Prophet et pas ARIMA ?
- Qu'est-ce que `changepoint_prior_scale` et pourquoi 0.05 ?
- Comment interprètes-tu les composantes du modèle ?
- Qu'est-ce que le MAE et pourquoi pas le RMSE ici ?

**Livrables phase 6**
- `model/train.py` fonctionnel
- `model/inflation_model.pkl` (sérialisé)
- `model/metrics.json` avec MAE par catégorie
- `notebooks/03_model_exploration.ipynb`
- **Captures** : graphique prédiction vs réel, décomposition des composantes Prophet

---

### Phase 7 — API modèle + Intégration (C9, C10)
**Durée** : 3 jours — Semaine 5
**Compétences** : C9, C10

**C9 — API modèle**

```python
# api/model/main.py
@app.post("/predict")
async def predict_inflation(request: PredictionRequest, api_key: str = Depends(verify_key)):
    """
    Prédit l'IPC pour une catégorie sur N mois futurs.
    Input : {"categorie": "alimentation", "periodes": 6}
    Output : {"predictions": [...], "mae": 0.42, "model_version": "1.0.0"}
    """
    model = load_model(request.categorie)
    future = model.make_future_dataframe(periods=request.periodes, freq="M")
    forecast = model.predict(future)
    return {
        "predictions": forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(request.periodes).to_dict("records"),
        "mae": get_model_metrics(request.categorie)["mae"],
        "model_version": "1.0.0"
    }
```

**C10 — Client dans l'application**

```python
# app/api_client.py
def predict_ipc(categorie: str, periodes: int) -> dict | None:
    try:
        r = requests.post(
            f"{API_URL}/predict",
            headers={"X-API-Key": API_KEY},
            json={"categorie": categorie, "periodes": periodes},
            timeout=5
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None
```

---

### Phase 8 — Monitoring modèle (C11)
**Durée** : 2 jours — Semaine 5
**Compétence** : C11

**Stack de monitoring**

```
API FastAPI (/metrics) → Prometheus → Grafana (dashboard)
                                    → alertes (règles alerts.yml)
```

**Exposition des métriques dans l'API modèle**

```python
# api/model/main.py
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

# Métriques exposées sur /metrics
predictions_total = Counter(
    "predictions_total",
    "Nombre total de prédictions",
    ["categorie"]
)
prediction_latency = Histogram(
    "prediction_latency_seconds",
    "Latence des prédictions en secondes"
)
prediction_mae = Gauge(
    "prediction_mae",
    "MAE du modèle en production",
    ["categorie"]
)
api_errors_total = Counter(
    "api_errors_total",
    "Nombre d'erreurs API",
    ["error_type"]
)

# Montage endpoint /metrics — Prometheus vient scraper ici
app.mount("/metrics", make_asgi_app())
```

**Config Prometheus** (`monitoring/prometheus.yml`)

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'inflation_model_api'
    static_configs:
      - targets: ['localhost:8000']

  - job_name: 'inflation_data_api'
    static_configs:
      - targets: ['localhost:8001']

  - job_name: 'inflation_app'
    static_configs:
      - targets: ['localhost:8501']
```

**Règles d'alertes** (`monitoring/alerts.yml`)

```yaml
groups:
  - name: inflation_tracker
    rules:
      - alert: MAE_Trop_Elevee
        expr: prediction_mae > 2
        for: 5m
        annotations:
          summary: "MAE du modèle dépasse 2 points IPC — dérive détectée"

      - alert: Latence_Elevee
        expr: prediction_latency_seconds > 2
        for: 2m
        annotations:
          summary: "Latence API prédiction > 2s"

      - alert: Taux_Erreurs_Eleve
        expr: rate(api_errors_total[5m]) > 0.05
        annotations:
          summary: "Taux d'erreurs API > 5%"
```

**Docker Compose** (`docker-compose.yml`)

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: inflation_tracker
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"

  prometheus:
    image: prom/prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/alerts.yml:/etc/prometheus/alerts.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

**Métriques à suivre sur Grafana**

| Métrique Prometheus | Panel Grafana | Seuil d'alerte |
|---|---|---|
| `prediction_mae` | Jauge temps réel | > 2 points IPC |
| `prediction_latency_seconds` | Histogramme | > 2s |
| `predictions_total` | Compteur par catégorie | — |
| `api_errors_total` | Taux d'erreurs | > 5% |

**Livrables phase 8**
- `monitoring/prometheus.yml` configuré
- `monitoring/alerts.yml` avec 3+ règles
- `monitoring/grafana/dashboards/model_dashboard.json` importé
- Dashboard Grafana accessible sur `localhost:3000`
- **Captures** : dashboard Grafana avec métriques en temps réel, règle d'alerte déclenchée

---

### Phase 9 — Tests + CI/CD Bloc 1 & 2 (C12, C13)
**Durée** : 3 jours — Semaine 6
**Compétences** : C12, C13

**Tests à couvrir**
- `test_collect.py` : chaque collecteur retourne un DataFrame non vide
- `test_aggregate.py` : dataset final a les colonnes attendues, pas de nulls sur colonnes clés
- `test_api_data.py` : endpoints 200/401/422
- `test_model.py` : MAE < seuil, format prédiction correct
- `test_api_model.py` : `/predict` retourne les bons champs

**CI/CD Bloc 2** (`.github/workflows/ci_model.yml`)
```yaml
name: CI — Modèle IA
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pytest tests/test_model.py tests/test_api_model.py --cov=model --cov=api/model
```

---

## BLOC 3 — C14 à C21 : Application Streamlit

---

### Phase 10 — Spécifications (C14, C15, C16)
**Durée** : 1 jour — Semaine 7
**Compétences** : C14, C15, C16

**C14 — User stories**

| ID | User Story | Critère d'acceptation |
|---|---|---|
| US1 | En tant qu'utilisateur, je veux voir l'évolution historique de l'IPC par catégorie | Graphique interactif avec slider de dates |
| US2 | En tant qu'utilisateur, je veux obtenir une prédiction d'inflation sur 6 mois | Courbe de prédiction avec intervalle de confiance |
| US3 | En tant qu'utilisateur, je veux comprendre pourquoi un produit a augmenté | Décomposition des composantes (tendance + saisonnalité) |
| US4 | En tant qu'utilisateur, je veux être informé si l'API est indisponible | Message clair sans crash |

**C15 — Architecture**

Stack : Streamlit → API modèle FastAPI → PostgreSQL → Modèle Prophet

**C16 — Agile**

Backlog dans `docs/agile.md`, tableau kanban GitHub Projects (colonnes : To Do / In Progress / Done), daily solo 5 min/jour documenté.

---

### Phase 11 — Application Streamlit (C17)
**Durée** : 3 jours — Semaine 7
**Compétence** : C17

```python
# app/main.py
import streamlit as st
from app.api_client import predict_ipc, get_historical_ipc
import plotly.graph_objects as go

st.set_page_config(page_title="Inflation Tracker", page_icon="📈")
st.title("📈 Inflation Tracker France")
st.caption("Comprendre et prédire l'évolution des prix")

categorie = st.selectbox(
    "Catégorie de produit",
    ["alimentation", "energie", "services", "logement", "ensemble"]
)
periodes = st.slider("Mois de prédiction", 1, 12, 6)

col1, col2 = st.columns(2)
with col1:
    if st.button("Voir la prédiction"):
        result = predict_ipc(categorie, periodes)
        if result:
            # Affichage graphique Plotly
            fig = go.Figure()
            # Historique + prédiction + intervalle de confiance
            st.plotly_chart(fig, use_container_width=True)
            st.info(f"MAE du modèle : {result['mae']} points IPC")
        else:
            st.error("Service de prédiction indisponible.")

with col2:
    st.metric("Inflation 2022", "+5,2%", delta="pic historique")
    st.metric("Inflation 2024", "+2,0%", delta="-3,2%")
    st.metric("Inflation 2025", "+0,9%", delta="-1,1%")
```

---

### Phase 12 — Monitoring app + CI/CD + Incident (C18, C19, C20, C21)
**Durée** : 2-3 jours — Semaine 7
**Compétences** : C18, C19, C20, C21

**C20 — Monitoring applicatif**

Même stack Prometheus + Grafana que pour le modèle. On ajoute un exporter dans l'application Streamlit :

```python
# app/main.py — ajout des métriques applicatives
from prometheus_client import Counter, Histogram

app_requests_total = Counter("app_requests_total", "Requêtes utilisateur", ["categorie"])
app_latency = Histogram("app_latency_seconds", "Temps de réponse Streamlit")
app_api_errors = Counter("app_api_errors_total", "Erreurs appel API modèle")
```

Dashboard Grafana dédié (`monitoring/grafana/dashboards/app_dashboard.json`) avec panels :
- Nombre de requêtes utilisateur par catégorie
- Taux d'erreurs appel API modèle
- Latence Streamlit end-to-end

**C21 — Incident à documenter**

Exemples typiques qui arriveront naturellement :
- Catégorie identique en départ et arrivée (déjà identifié sur les projets précédents)
- Erreur si l'API modèle n'est pas lancée avant Streamlit
- Timeout si PySpark manque de RAM
- Encoding error sur les données Eurostat

Documenter dans `docs/incident.md` : description → cause → reproduction → correction → commit correctif → test de non-régression.

**CI/CD Bloc 3** (`.github/workflows/ci_app.yml`) — même structure que Blocs 1 & 2.

---

### Phase 13 — Rapports + Slides + Soutenance blanche (Semaine 8)
**Durée** : 1 semaine entière
**Tout**

**Structure du rapport professionnel (par bloc)**

Chaque rapport suit exactement cette structure :
1. Contexte, acteurs, objectifs, contraintes
2. Spécifications fonctionnelles et techniques
3. Réalisation (data / IA / application)
4. Tests, CI/CD, monitoring, sécurité, RGPD
5. Bilan, limites, décisions, perspectives

Chaque section contient : une décision technique + une preuve + une capture + un lien Git.

**Structure de la soutenance**

1. Contexte et problème — "Le kebab à 3,50€ → 7€, pourquoi ?"
2. Architecture globale — schéma des 3 blocs
3. Bloc 1 — preuves C1 à C5 (captures terminal, SQL, Swagger)
4. Bloc 2 — preuves C6 à C13 (benchmark, graphique Prophet, Prometheus)
5. Bloc 3 — preuves C14 à C21 (Streamlit live, CI vert, incident résolu)
6. Démo live — formulaire → prédiction → graphique
7. Bilan et limites assumées

**Règle d'or du coaching ECE** : chaque slide comporte le bandeau *"Compétences prouvées : Cx, Cy"*. Si on enlève le titre, le jury comprend encore quelle compétence est prouvée.

---

## ✅ Matrice de preuves — C1 à C21

| Compétence | Preuve technique | Fichier Git | Slide |
|---|---|---|---|
| C1 | 5 scripts de collecte + logs d'exécution | `src/collect/` | 3 |
| C2 | Requêtes SQL documentées + résultats | `src/sql/queries_extraction.sql` | 4 |
| C3 | Script agrégation + tableau avant/après | `src/aggregate/aggregate_clean.py` | 4 |
| C4 | MCD/MPD + script import + registre RGPD | `src/database/` | 5 |
| C5 | API FastAPI + Swagger + tests endpoints | `api/data/` | 6 |
| C6 | Veille avec sources qualifiées + synthèse | `docs/veille.md` | 8 |
| C7 | Benchmark Prophet vs LSTM vs XGBoost | `docs/benchmark.md` | 9 |
| C8 | Modèle Prophet entraîné + métriques | `model/` | 10 |
| C9 | API modèle `/predict` + Swagger + tests | `api/model/` | 11 |
| C10 | Client Streamlit → API → affichage résultat | `app/api_client.py` | 12 |
| C11 | Dashboard Grafana modèle + alertes Prometheus | `monitoring/grafana/dashboards/model_dashboard.json` | 13 |
| C12 | pytest 15+ tests, couverture > 80% | `tests/` | 14 |
| C13 | GitHub Actions CI/CD modèle — badge vert | `.github/workflows/ci_model.yml` | 15 |
| C14 | User stories + critères d'acceptation | `docs/specs_fonctionnelles.md` | 17 |
| C15 | Architecture + DFD + POC | `docs/specs_techniques.md` | 17 |
| C16 | Kanban GitHub Projects + backlog + daily | `docs/agile.md` | 18 |
| C17 | Streamlit fonctionnel + gestion erreurs | `app/main.py` | 19 |
| C18 | GitHub Actions CI app — badge vert | `.github/workflows/ci_app.yml` | 20 |
| C19 | Pipeline livraison continue documenté | `.github/workflows/ci_app.yml` | 20 |
| C20 | Dashboard Grafana app + métriques Prometheus + alertes | `monitoring/grafana/dashboards/app_dashboard.json` | 21 |
| C21 | Incident documenté + commit correctif | `docs/incident.md` | 22 |

**Règle absolue** : aucune compétence ne reste au statut "on l'a fait". Chaque ligne de ce tableau doit être complétée avant la soutenance blanche.

---

## 🎯 Checklist finale avant soutenance (20 août)

### Technique
- [ ] Repo Git accessible publiquement
- [ ] README reproductible en 3 commandes
- [ ] Docker-compose lance PostgreSQL + Prometheus + Grafana en une commande
- [ ] Tous les tests passent en local ET en CI
- [ ] Les 3 pipelines CI/CD sont verts sur GitHub
- [ ] Dashboard Grafana accessible sur localhost:3000 avec métriques réelles
- [ ] Démo préparée **hors internet** (données en cache local)

### Dossier de preuves
- [ ] Matrice C1-C21 complète avec localisation dans Git
- [ ] Captures lisibles pour chaque compétence
- [ ] Rapport professionnel rédigé (pas juste un README)
- [ ] Slides avec bandeau compétences sur chaque slide
- [ ] Décisions techniques écrites et justifiées
- [ ] Limites assumées et documentées

### Soutenance
- [ ] Ouverture : "Le kebab coûtait 3,50€, aujourd'hui 7€ — voici pourquoi"
- [ ] Démo live : formulaire → prédiction → graphique
- [ ] Chaque question technique préparée à voix haute
- [ ] Incident C21 raconté avec la trace Git

---

*Roadmap générée le 25/06/2026 — Projet inflation-tracker — C1 à C21*
*Mise à jour : monitoring Prometheus + Grafana (remplacement loggers manuels)*
*Soutenance cible : 27 août 2026*
