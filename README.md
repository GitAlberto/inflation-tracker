# inflation-tracker

Système complet de collecte, stockage, analyse et prédiction de l'inflation en France et en zone euro.  
Projet final B3 RNCP — Titre Professionnel Développeur en IA.

## Concept

Le kebab coûtait 3,50 € en 2019. Il en coûte 7 € en 2026.  
Ce projet agrège les données publiques (INSEE, BCE, Eurostat, OpenFoodFacts, data.gouv) pour rendre l'inflation lisible et prédire son évolution par catégorie de produit.

## Architecture

```
Sources (5)
  INSEE · BCE · Eurostat · OpenFoodFacts · data.gouv
        ↓
Pipeline Python (src/)
  collect → aggregate → database
        ↓
PostgreSQL 15 (Docker, port 5437)
  table : inflation_unified
        ↓
API FastAPI (api/data/, port 8001)   ←→   Modèle Prophet (model/)
        ↓                                          ↓
API Modèle (api/model/, port 8002)         13 catégories INSEE
        ↓
Application Streamlit (app/, port 8501)
        ↓
Monitoring Prometheus + Grafana
```

## Blocs RNCP

| Bloc | Compétences | Statut |
|---|---|---|
| Bloc 1 — Collecte, stockage, API data | C1 à C5 | ✅ Complété |
| Bloc 2 — Modèle IA, API modèle, MLOps | C6 à C13 | 🔄 En cours (C8 ✅) |
| Bloc 3 — Application, CI/CD, monitoring | C14 à C21 | ⏳ À venir |

## Avancement

### Bloc 1 — Collecte & API

| Compétence | Description | Fichier(s) |
|---|---|---|
| C1 | Collecte 5 sources + table `inflation_unified` | `src/collect/`, `src/database/schema.sql` |
| C2 | Requêtes SQL extraction et analyse inflation | `src/sql/queries_extraction.sql`, `src/sql/queries_analyse.sql` |
| C3 | Pipeline d'agrégation et nettoyage | `src/aggregate/aggregate_clean.py` |
| C4 | Stockage PostgreSQL (TRUNCATE+append) | `src/database/` |
| C5 | API REST FastAPI — 9 endpoints données IPC | `api/data/` |

### Bloc 2 — Modèle IA

| Compétence | Description | Fichier(s) |
|---|---|---|
| C7 | Benchmark Prophet vs ARIMA vs Holt-Winters | `notebooks/benchmark_modeles.ipynb` |
| C8 | Modèle Prophet IPC France × 13 catégories | `model/train.py`, `model/predict.py`, `model/evaluate.py` |

## Résultats C8 — Prophet IPC France (éval 2025)

| Catégorie | MAE | MAPE |
|---|---|---|
| Ensemble hors énergie | 0.2330 | 0.20% |
| 00 - Ensemble | 0.2624 | 0.22% |
| 05 - Meubles, articles de ménage | 0.2848 | 0.25% |
| 07 - Transports | 0.7174 | 0.57% |
| 04 - Logement, eau, gaz, électricité | 4.8327 | 3.69% ⚡ choc Ukraine |
| 08 - Communications | 3.7871 | 4.93% ⚡ chocs réglementaires |
| **Moyenne (13 catégories)** | **1.4302** | **1.31%** |

Hyperparamètres : `yearly_seasonality=True`, `changepoint_prior_scale=0.05`, mode additif.  
Split : train 2020-2024 (60 pts) / éval 2025 (12 pts).

## Benchmark C7 — Prophet vs ARIMA vs Holt-Winters

| Modèle | MAE | MAPE |
|---|---|---|
| Holt-Winters | 0.2198 | 0.18% 🥇 |
| Prophet | 0.2624 | 0.22% 🥈 |
| ARIMA(2,1,2) | 0.9773 | 0.81% 🥉 |

Prophet retenu pour la production malgré un MAE légèrement supérieur à Holt-Winters : changepoints automatiques (chocs COVID/Ukraine), intervalles de confiance natifs, scalabilité sur 13 catégories sans reparamétrage.

## Lancement

### Prérequis

```bash
pip install -r requirements.txt
# Prophet nécessite CmdStan (Windows : via Scoop → scoop install mingw)
```

### Base de données

```bash
docker-compose up -d          # PostgreSQL 15 sur port 5437
python src/collect/...        # collecte des 5 sources
python src/aggregate/aggregate_clean.py   # agrégation → inflation_unified
```

### API données (C5)

```bash
uvicorn api.data.main:app --reload --port 8001
# Swagger : http://localhost:8001/docs
```

Endpoints principaux :

| Route | Description |
|---|---|
| `GET /health` | Statut de l'API |
| `GET /api/inflation` | Données IPC (pagination + filtres pays/source/catégorie/date) |
| `GET /api/inflation/tendance` | Tendance mensuelle France |
| `GET /api/inflation/pays` | Comparaison multi-pays |
| `GET /api/prix-alimentaires` | Prix OpenFoodFacts |

### Modèle Prophet (C8)

```bash
# Entraîner les 13 modèles (génère model/metrics.json)
python model/train.py

# Prédictions 12 mois — catégorie spécifique
python model/predict.py --categorie "00 - Ensemble" --horizon 12

# Prédictions toutes catégories
python model/predict.py --all --horizon 12

# Graphiques et métriques d'évaluation
python model/evaluate.py
```

### Tests

```bash
pytest tests/ -v               # 16 tests API data
pytest tests/ --cov=api        # avec couverture
```

## Structure

```
inflation-tracker/
├── src/
│   ├── collect/               # collecteurs par source (C1)
│   ├── aggregate/             # nettoyage et fusion (C3)
│   ├── database/              # schema.sql, init (C4)
│   └── sql/                   # requêtes extraction et analyse (C2)
├── api/
│   ├── data/                  # API FastAPI données (C5)
│   └── model/                 # API FastAPI modèle (C9 — à venir)
├── model/
│   ├── train.py               # entraînement Prophet (C8)
│   ├── predict.py             # prédictions CLI (C8)
│   ├── evaluate.py            # métriques + graphiques (C8)
│   └── metrics.json           # MAE/RMSE/MAPE par catégorie
├── notebooks/
│   └── benchmark_modeles.ipynb  # benchmark C7
├── tests/                     # tests API (C5)
├── preuves/                   # captures et preuves RNCP
├── docs/                      # documentation technique
└── requirements.txt
```

## Planning

8 semaines — 25 juin → 27 août 2026.  
Détail des sprints : `ROADMAP_INFLATION_COMPLET.md`.
