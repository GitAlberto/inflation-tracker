# inflation-tracker

Système complet de collecte, stockage, analyse et prédiction de l'inflation en France et en zone euro.  
Projet final B3 RNCP — Titre Professionnel Développeur en Intelligence Artificielle — Simplon / ECE Paris.

[![CI — Bloc 1 Data](https://github.com/GitAlberto/inflation-tracker/actions/workflows/ci_data.yml/badge.svg)](https://github.com/GitAlberto/inflation-tracker/actions/workflows/ci_data.yml)
[![CI — Bloc 2 Modèle](https://github.com/GitAlberto/inflation-tracker/actions/workflows/ci_model.yml/badge.svg)](https://github.com/GitAlberto/inflation-tracker/actions/workflows/ci_model.yml)
[![CI — Bloc 3 App](https://github.com/GitAlberto/inflation-tracker/actions/workflows/ci_app.yml/badge.svg)](https://github.com/GitAlberto/inflation-tracker/actions/workflows/ci_app.yml)

---

## Concept

Le kebab coûtait 3,50 € en 2019. Il en coûte 7 € en 2026.  
Ce projet agrège les données publiques (INSEE, BCE, Eurostat, OpenFoodFacts, data.gouv) pour rendre l'inflation lisible et prédire son évolution par catégorie de produit.

---

## Architecture

```
Sources (5)
  INSEE · BCE · Eurostat · OpenFoodFacts · data.gouv
        ↓
Pipeline ETL Python (src/)
  collect → aggregate → database
        ↓
PostgreSQL 15 (Docker, port 5437)
  table : inflation_unified (3,68 M lignes)
        ↓
API FastAPI data (port 8001)   ←→   Modèle Prophet (model/)
        ↓                                  ↓ 12 catégories .pkl
API FastAPI modèle (port 8002)        métriques MAE/RMSE/MAPE
        ↓
Application Streamlit (port 8501)
        ↓
Monitoring Prometheus (port 9090) + Grafana (port 3000)
```

---

## Blocs RNCP

| Bloc | Compétences | Statut |
|---|---|---|
| Bloc 1 — Collecte, stockage, API data | C1 à C5 | ✅ Complété |
| Bloc 2 — Modèle IA, API modèle, MLOps | C6 à C13 | ✅ Complété |
| Bloc 3 — Application, CI/CD, monitoring | C14 à C21 | ✅ Complété |

---

## Lancement rapide

```bash
# Prérequis : Docker Desktop en cours d'exécution, .venv activé
bash start.sh
```

`start.sh` démarre dans l'ordre :
1. PostgreSQL (Docker, port 5437)
2. Prometheus + Grafana (Docker, ports 9090 / 3000)
3. API data en Python natif (port 8001)
4. API modèle en Python natif (port 8002)
5. Application Streamlit (port 8501)

| Service | URL |
|---|---|
| Application | http://localhost:8501 |
| API data (Swagger) | http://localhost:8001/docs |
| API modèle (Swagger) | http://localhost:8002/docs |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |

---

## Tests

```bash
pytest tests/ -v --cov=api --cov=model
```

**47/47 tests passés — couverture 93%**  
Tests CI/CD : GitHub Actions (3 pipelines, sans PostgreSQL ni .pkl requis en CI).

---

## Résultats C8 — Prophet IPC France (éval 2025)

| Catégorie | MAE | MAPE |
|---|---|---|
| Ensemble hors énergie | 0.23 | 0.20% |
| 00 - Ensemble | 0.26 | 0.22% |
| 05 - Meubles, articles de ménage | 0.28 | 0.25% |
| 07 - Transports | 0.72 | 0.57% |
| 08 - Communications | 3.79 | 4.93% ⚡ chocs réglementaires |
| 04 - Logement, eau, gaz, électricité | 4.83 | 3.69% ⚡ choc Ukraine |
| **Moyenne (12 catégories)** | **1.43** | **1.31%** |

Hyperparamètres : `yearly_seasonality=True`, `changepoint_prior_scale=0.05`, mode additif.  
Split temporel strict : train 2020–2024 (60 pts) / éval 2025 (12 pts, held-out).

---

## Benchmark C7 — Prophet vs ARIMA vs Holt-Winters

| Modèle | MAE | MAPE |
|---|---|---|
| Holt-Winters | 0.22 | 0.18% 🥇 |
| Prophet | 0.26 | 0.22% 🥈 |
| ARIMA(2,1,2) | 0.98 | 0.81% 🥉 |

Prophet retenu pour la production : changepoints automatiques (chocs COVID/Ukraine), intervalles de confiance natifs, scalabilité sur 12 catégories sans reparamétrage.

---

## API data (C5) — endpoints principaux

| Route | Description |
|---|---|
| `GET /health` | Statut de l'API |
| `GET /api/inflation` | Données IPC (filtres source/catégorie/date) |
| `GET /api/inflation/tendance` | Tendance mensuelle France |
| `GET /api/inflation/pays` | Comparaison multi-pays |
| `GET /api/prix-alimentaires` | Prix OpenFoodFacts |

Authentification : header `X-API-Key` (deux niveaux : user / admin).

---

## Sources de données (C1)

| Source | Technologie | Données | Volume |
|---|---|---|---|
| API INSEE BDM | REST + OAuth2 | IPC France mensuel depuis 2000 | ~13 séries |
| data.gouv.fr | CSV direct | Séries longues IPC depuis 1996 | ~180 k lignes |
| Open Food Facts | Scraping BeautifulSoup | Prix alimentaires réels | ~5 k lignes |
| ECB API | REST → PostgreSQL | HICP zone euro 30 ans | ~50 k lignes |
| Eurostat bulk | CSV → PySpark | 27 pays × 100+ catégories × 30 ans | 3,5 M lignes |

---

## Structure

```
inflation-tracker/
├── src/
│   ├── collect/               # ETL 5 sources (C1)
│   ├── aggregate/             # nettoyage et fusion (C3)
│   ├── database/              # schema.sql, import (C4)
│   └── sql/                   # requêtes extraction et analyse (C2)
├── api/
│   ├── data/                  # API FastAPI données (C5)
│   └── model/                 # API FastAPI modèle + métriques Prometheus (C9/C11)
├── model/
│   ├── train.py               # entraînement Prophet (C8)
│   ├── predict.py             # prédictions CLI (C8)
│   ├── evaluate.py            # métriques + graphiques (C8/C12)
│   └── metrics.json           # MAE/RMSE/MAPE par catégorie
├── app/                       # Application Streamlit 4 pages (C17)
├── monitoring/
│   ├── prometheus.yml         # scraping API modèle toutes les 15s
│   ├── alerts.yml             # règles d'alertes MAE/latence/erreurs
│   └── grafana/               # dashboards provisionnés automatiquement
├── tests/                     # 47 tests pytest — 93% couverture (C12/C13)
├── .github/workflows/         # CI/CD 3 pipelines (C13/C18)
├── docs/                      # specs fonctionnelles, techniques, MCD, RGPD, incidents
├── preuves/                   # captures et preuves RNCP C1–C21
├── docker-compose.yml         # PostgreSQL + Prometheus + Grafana
├── start.sh                   # lancement complet en une commande
└── requirements.txt
```

---

## Documentation

| Document | Compétence | Lien |
|---|---|---|
| Spécifications fonctionnelles | C14 | `docs/specs_fonctionnelles.md` |
| Spécifications techniques | C15 | `docs/specs_techniques.md` |
| MCD Merise | C4/C14 | `docs/mcd.md` + `docs/mcd_merise_2026-07-29.pdf` |
| Registre RGPD | C4/C19 | `docs/registre_rgpd_inflation_tracker_fin.pdf` |
| Gestion de projet Agile | C16 | `docs/agile.md` |
| Incidents / postmortems | C21 | `docs/incident_2026-07-18.md`, `docs/incident_2026-07-25.md` |

---

Soutenance : 27 août 2026 — Simplon / ECE Paris.
