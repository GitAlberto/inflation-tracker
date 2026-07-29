# Rapport Professionnel — Inflation Tracker

**Titre Professionnel :** Développeur en Intelligence Artificielle (B3 RNCP)  
**Candidat :** Alberto Bongue  
**Établissement :** Simplon / ECE Paris  
**Période du projet :** juin – août 2026  
**Dépôt Git :** https://github.com/GitAlberto/inflation-tracker  
**Branche principale :** AlbertoFinB3 → main  

---

## 1. Contexte et problème adressé

Le kebab coûtait 3,50 € en 2019. Il en coûte 7 € en 2026. L'inflation est un phénomène que tout le monde subit mais que personne ne comprend vraiment. Les données publiques existent — publiées chaque mois par l'INSEE, la BCE, Eurostat — mais elles sont dispersées, au format technique (SDMX, CSV multi-colonnes, API REST avec codes COICOP), et inaccessibles pour un utilisateur non statisticien.

**Objectif du projet :** concevoir et déployer un système complet de collecte, stockage, modélisation et visualisation de l'inflation en France, articulé en trois blocs techniques :

- **Bloc 1** — Construire le socle data : collecter 5 sources hétérogènes, les normaliser et les exposer via une API REST.
- **Bloc 2** — Entraîner un modèle de prédiction de l'IPC par catégorie COICOP, l'exposer via API, le monitorer.
- **Bloc 3** — Développer une application Streamlit accessible à l'utilisateur final, avec CI/CD, monitoring applicatif et gestion des incidents.

---

## 2. Architecture globale

```
Sources publiques (5)
  INSEE · BCE · Eurostat · OpenFoodFacts · data.gouv.fr
        ↓ Pipeline ETL Python (src/)
PostgreSQL 15 — table inflation_unified (3,68 M lignes)
        ↓                          ↓
API data FastAPI (8001)    Modèle Prophet (12 catégories)
        ↓                          ↓
              API modèle FastAPI (8002)
                      ↓
          Application Streamlit (8501)
                      ↓
     Prometheus (9090) + Grafana (3000)
```

L'ensemble est orchestré par `start.sh` : PostgreSQL démarre en Docker, Prometheus et Grafana en Docker, les APIs et Streamlit en processus Python natifs.

---

## BLOC 1 — Collecte, stockage, mise à disposition (C1–C5)

### C1 — Collecte de données multi-sources

**Ce que j'ai fait :** cinq collecteurs Python distincts, chacun adapté à la nature de sa source.

| Source | Script | Technologie | Volume |
|---|---|---|---|
| INSEE BDM | `src/collect/collect_insee_api.py` | API REST OAuth2 | ~13 séries mensuelles |
| data.gouv.fr | `src/collect/collect_csv.py` | CSV direct download | ~180 k lignes |
| Open Food Facts | `src/collect/scrape_openfoodfacts.py` | Scraping BeautifulSoup | ~5 k lignes |
| BCE | `src/collect/load_ecb_to_db.py` | API REST → PostgreSQL | ~50 k lignes |
| Eurostat | `src/collect/collect_eurostat_spark.py` | CSV bulk → PySpark | 3,51 M lignes |

**Incident rencontré :** l'installation de PySpark a échoué avec `Failed to build wheel for pyspark` — Java était absent du PATH de la session VS Code. Résolution : installation d'Eclipse Temurin JDK 21 (Adoptium), fermeture et réouverture de VS Code pour recharger les variables d'environnement.  
*(Captures : `C1_C21_erreur_pyspark_install.png`, `C21_installation_java21.png`, `C1_C21_pyspark_reparé.png`)*

**Résultat Eurostat :** 3 511 040 lignes traitées par Spark, chargées dans `eurostat_bulk` en ~6 minutes.  
*(Capture : `C1_C2_eurostat_pyspark_execution.png`)*

**Décision clé :** toutes les sources sont filtrées sur `geo=FR` dès la collecte, évitant de stocker des données inutiles pour le périmètre France du projet.

---

### C2 — Exploitation SQL des données

**Ce que j'ai fait :** deux fichiers de requêtes SQL documentées couvrant l'extraction et l'analyse.

- `src/sql/queries_extraction.sql` — extraction par source, jointures multi-sources, vérification de cohérence
- `src/sql/queries_analyse.sql` — tendances mensuelles, comparaisons inter-sources, détection d'anomalies

**Exemple de requête analytique :**
```sql
SELECT date_obs, categorie,
       valeur,
       valeur - LAG(valeur) OVER (PARTITION BY categorie ORDER BY date_obs) AS variation_mensuelle
FROM inflation_unified
WHERE source = 'INSEE' AND pays = 'FR'
ORDER BY categorie, date_obs;
```

Chaque requête est commentée : pourquoi ce filtre, pourquoi cette jointure, ce que le résultat prouve.

---

### C3 — Pipeline d'agrégation et nettoyage

**Problème identifié :** audit réalisé lors de l'intégration des sources — la colonne `valeur` contenait des grandeurs incomparables.

| Source | Valeur brute | Problème |
|---|---|---|
| INSEE | 119.17 (indice base 2015=100) | ✅ Référence |
| DATAGOUV | mélange indices + taux % | ❌ Filtre UNIT_MEASURE absent |
| ECB | 2.4 (taux ANR %) | ❌ Pas un indice |
| EUROSTAT | 3.2 (taux RCH_A %) | ❌ Mauvais dataset |

**Solution :** règle unique — `inflation_unified.valeur` = indice IPC base 100 = 2015 pour toutes les sources. Filtres appliqués : `UNIT_MEASURE='IX'` (DATAGOUV), dataset `prc_hicp_midx` avec `I15` (Eurostat), série `INX` (ECB).

**Colonne `base_ref` ajoutée** : trace la base de référence de chaque source (2015 ou 2025 pour DATAGOUV rebasé), permettant à l'application d'afficher un avertissement quand les bases sont incompatibles.

Script : `src/aggregate/aggregate_clean.py`

---

### C4 — Base de données PostgreSQL

**Schéma :** 6 tables créées via `src/database/schema.sql`.

| Table | Rôle |
|---|---|
| `ecb_hicp_raw` | Données brutes BCE (HICP zone euro) |
| `eurostat_bulk` | Données brutes Eurostat (PySpark) |
| `datagouv_ipc` | Données brutes data.gouv.fr |
| `insee_ipc` | Données brutes INSEE BDM |
| `openfoodfacts` | Prix alimentaires scrappés |
| `inflation_unified` | Table normalisée finale (toutes sources) |

*(Captures : `C4_creation_tables_pgadmin.png`, `C4_schema_tables_pgadmin.png`)*

**MCD Merise :** modélisé dans `docs/mcd.md` avec notation crow's foot (Mermaid erDiagram). 5 entités conceptuelles, 5 associations, cardinalités (1,1)→(0,N). Export PDF : `docs/mcd_merise_2026-07-29.pdf`.

**Registre RGPD :** `docs/registre_rgpd_inflation_tracker_fin.pdf`. Aucune donnée personnelle collectée. Données publiques sous licences ouvertes (Licence Ouverte INSEE, CC BY Eurostat, ODbL OpenFoodFacts). Principe de minimisation appliqué.

**Choix PostgreSQL :** type `NUMERIC(10,4)` pour les valeurs IPC — aucune erreur d'arrondi flottant, critique pour des comparaisons de séries économiques sur 30 ans.

---

### C5 — API REST données

**Ce que j'ai fait :** API FastAPI exposant `inflation_unified` avec 9 endpoints documentés.

| Endpoint | Description |
|---|---|
| `GET /api/inflation` | Données IPC avec filtres source/catégorie/date/pays |
| `GET /api/inflation/tendance` | Tendance mensuelle France |
| `GET /api/inflation/pays` | Codes pays disponibles (filtrable par source) |
| `GET /api/inflation/sources` | Sources disponibles |
| `GET /api/inflation/categories` | Catégories COICOP disponibles |
| `GET /api/prix-alimentaires` | Prix OpenFoodFacts |
| `GET /api/prix-alimentaires/categories` | Catégories alimentaires |
| `GET /api/prix-alimentaires/stats` | Statistiques prix |
| `GET /health` | Statut de l'API |

*(Capture : `C5_swagger_api_data.png`)*

**Authentification :** header `X-API-Key` obligatoire. Deux niveaux : clé admin (accès complet) et clé user (lecture publique). Implémenté dans `api/data/auth.py`.

---

## BLOC 2 — Modèle IA, API modèle, MLOps (C6–C13)

### C6 — Veille technologique

**Thématique :** ML appliqué à la prédiction de séries temporelles économiques (IPC, inflation).

**Sources consultées :** publications BCE (ECB Working Papers), documents méthodologiques INSEE, articles NeurIPS/ICML sur séries temporelles, documentation Prophet (Meta AI Research).

**Synthèse :** trois familles de modèles évaluées (ARIMA, Prophet, LSTM). Contraintes identifiées pour l'inflation : saisonnalité mensuelle forte, ruptures structurelles ponctuelles (COVID, guerre Ukraine), volume de données limité (~60 points d'entraînement par catégorie). Prophet ressort comme le seul modèle gérant nativement ces trois contraintes.

*(Capture : `C6_C7_ipc_rupture_ukraine.png` — rupture IPC 2021-2022 annotée)*

Document complet : `docs/veille_C6_final.pdf`

---

### C7 — Benchmark des algorithmes

**Modèles comparés :** Prophet (Meta), ARIMA(2,1,2), Holt-Winters (lissage exponentiel triple).

**Protocole :** entraînement sur IPC France Ensemble 2020–2024, évaluation sur 2025 (12 mois held-out). Même split pour les trois modèles.

| Modèle | MAE | MAPE | Verdict |
|---|---|---|---|
| Holt-Winters | 0.220 | 0.18% | 🥇 Meilleur MAE |
| **Prophet** | **0.262** | **0.22%** | 🥈 **Retenu** |
| ARIMA(2,1,2) | 0.977 | 0.81% | 🥉 Insuffisant |

**Pourquoi Prophet et pas Holt-Winters malgré un MAE légèrement supérieur :**
- Changepoints automatiques — détecte les ruptures structurelles (COVID 2020, guerre Ukraine 2022) sans reparamétrage manuel
- Intervalles de confiance natifs — requis pour l'affichage dans Streamlit
- Scalabilité — un même pipeline entraîne 12 catégories sans ajuster les hyperparamètres

*(Captures : `C7_eda_ipc_insee.png`, `C7_benchmark_predictions.png`, `C7_prophet_decomposition_ensemble.png`)*

Résultats numériques : `docs/benchmark_resultats.json`

---

### C8 — Entraînement du modèle Prophet

**Ce que j'ai fait :** 12 modèles Prophet entraînés, un par catégorie COICOP (00–11).

**Hyperparamètres :**
```python
Prophet(
    yearly_seasonality=True,       # saisonnalité annuelle IPC
    weekly_seasonality=False,      # données mensuelles — pas de saisonnalité hebdo
    daily_seasonality=False,
    changepoint_prior_scale=0.05   # régularisation — évite le surapprentissage
)
```

**Split d'évaluation temporel strict :**
- Train : jan. 2020 → déc. 2024 (60 points)
- Eval : jan. 2025 → déc. 2025 (12 points, jamais vus)

Un split temporel strict (pas de shuffle) est impératif pour les séries temporelles : mélanger des observations futures dans le train introduit du data leakage et surestime les performances.

**Résultats (eval 2025) :**

| Catégorie | MAE | MAPE |
|---|---|---|
| 00 - Ensemble | 0.26 | 0.22% |
| 05 - Meubles | 0.28 | 0.25% |
| 10 - Enseignement | 0.42 | 0.35% |
| 07 - Transports | 0.72 | 0.57% |
| 08 - Communications | 3.79 | 4.93% |
| 04 - Logement/énergie | 4.83 | 3.69% |
| **Moyenne (12 cat.)** | **1.43** | **1.31%** |

Les catégories 08 (Communications) et 04 (Logement/énergie) présentent des MAE élevés : chocs réglementaires et choc Ukraine sont des ruptures structurelles difficiles à prédire pour un modèle entraîné sur 60 points.

**Catégorie 12 exclue :** la série INSEE BDM de la catégorie 12 (Biens et services divers : coiffure, assurances, frais bancaires) n'a pas été intégrée dans le collecteur. De plus, ses mécanismes de formation de prix sont structurellement différents des autres catégories — la saisonnalité Prophet n'apporterait pas de valeur sur cette série.

*(Captures : `C8_predictions_prophet.png`, `C8_metriques_evaluation_terminal.png`, `C8_prophet_decomposition_alimentation.png`)*

Scripts : `model/train.py`, `model/evaluate.py` — Métriques : `model/metrics.json`

---

### C9 — API modèle REST

**Ce que j'ai fait :** API FastAPI exposant les 12 modèles Prophet avec 6 endpoints.

| Endpoint | Description |
|---|---|
| `GET /api/predict/{categorie}` | Prédiction Prophet pour une catégorie, horizon paramétrable |
| `GET /api/predict` | Prédictions toutes catégories |
| `GET /api/categories` | Liste des 12 catégories disponibles |
| `GET /api/metrics` | MAE/RMSE/MAPE toutes catégories |
| `GET /api/metrics/{categorie}` | Métriques d'une catégorie |
| `GET /health` | Statut de l'API modèle |

*(Capture : `C9_swagger_api_modele.png`)*

**Séparation des APIs justifiée :** cycle de vie différent (données stables vs modèles réentraînables), scalabilité indépendante, métriques Prometheus distinctes par API.

---

### C10 — Intégration client–API

**Ce que j'ai fait :** le client Streamlit (`app/api_client.py`) consomme l'API modèle avec authentification X-API-Key. Deux niveaux d'accès implémentés dans `api/model/auth.py` :

- `verify_user_key` → accepte `API_KEY` ou `API_KEY_USER` — routes publiques (`/predict/{categorie}`, `/categories`)
- `verify_admin_key` → accepte uniquement `API_KEY` — routes sensibles (`/metrics`, `/predict` toutes catégories)

**Incident postmortem :** lors du déploiement Docker, le client Streamlit envoyait la bonne clé mais l'API répondait 403. Cause racine : `load_dotenv(override=True)` dans `auth.py` écrasait la variable `API_KEY` injectée par Docker avec la valeur du fichier `.env` local. Correction : `override=False` + bloc `environment` dans `docker-compose.yml`.

*(Postmortem complet : `docs/incident_2026-07-25.md`)*

---

### C11 — Monitoring du modèle

**Stack :** Prometheus scrape l'API modèle toutes les 15 secondes via `/metrics-prometheus`. Grafana lit Prometheus et affiche le dashboard en temps réel (refresh 30s).

**Métriques exposées :**

| Métrique Prometheus | Type | Ce qu'elle mesure |
|---|---|---|
| `http_requests_total` | Counter | Requêtes par endpoint et code HTTP |
| `http_request_duration_seconds` | Histogram | Latence p50/p95/p99 |
| `predictions_total` | Counter | Prédictions par catégorie |
| `api_up` | Gauge | Disponibilité de l'API |

**Dashboard Grafana** (`monitoring/grafana/dashboards/model_dashboard.json`) — 11 panneaux :
- Stat : disponibilité, req/s, prédictions totales, top catégories, latence p95, taux erreurs
- Timeseries : latence p50/p95/p99, prédictions par catégorie, trafic par endpoint
- Bar gauge : MAE par catégorie (toutes les 12)

*(Captures : `C11_grafana_dashboard_edition.png`, `C11_C20_grafana_monitoring_live.png`)*

**Problème de synchronisation résolu :** le monitoring ne se mettait pas à jour en temps réel car les containers Docker `api_model` et `api_data` occupaient les ports 8001/8002, empêchant les processus natifs de `start.sh` de se lier. Prometheus scrapeait alors le mauvais processus. Correction dans `start.sh` : arrêt des containers API Docker avant le démarrage natif, démarrage de Prometheus avec `--no-deps`.

---

### C12 — Tests et couverture

**47 tests, couverture 93%**

| Fichier de test | Ce qui est testé |
|---|---|
| `tests/test_collect.py` | Collecteurs : retournent un DataFrame non vide, colonnes attendues |
| `tests/test_aggregate.py` | Pipeline : pas de nulls sur colonnes clés, normalisation COICOP |
| `tests/test_api_data.py` | Endpoints data : 200/401/403/422, pagination, filtres |
| `tests/test_model.py` | Slugify, compute_metrics, format metrics.json |
| `tests/test_api_model.py` | Endpoints modèle : health, categories, metrics, 404, 422 |

*(Capture : `C12_tests_couverture_93pct.png` — rapport pytest-cov, 305 statements, 22 miss)*

**Stratégie CI :** les tests nécessitant les `.pkl` ou PostgreSQL sont marqués `@pytest.mark.skipif(os.getenv("CI") == "true")` pour s'exécuter uniquement en local. En CI, seuls les tests unitaires purs tournent — aucune dépendance externe requise.

---

### C13 — CI/CD GitHub Actions

**Trois pipelines** déclenchés à chaque push et pull request :

| Workflow | Fichier | Ce qu'il exécute |
|---|---|---|
| CI — Bloc 1 Data | `.github/workflows/ci_data.yml` | Tests API data, ~20s |
| CI — Bloc 2 Modèle | `.github/workflows/ci_model.yml` | Tests modèle + API modèle, ~1min |
| CI — Bloc 3 App | `.github/workflows/ci_app.yml` | Lint + vérification imports Streamlit |

*(Captures : `C13_CI_pr55_success.png`, `C13_CI_pr60_success.png`)*

**Incident CI documenté :** PR #57 — 2 checks échouent sur CI modèle. Cause : les tests attendaient 13 catégories, le modèle n'en entraîne que 12. Commit correctif : `fix(C12/C13): test_list_available 13→12 catégories COICOP`. CI repasse au vert.  
*(Captures : `C21_incident_CI_pr57_echec.png`, `C21_CI_pr57_relance_fix.png`)*

**Réentraînement :** non automatisé en CI — l'entraînement Prophet nécessite CmdStan (~500 Mo, ~15 min). Le fichier `model/metrics.json` est versionné (trace les performances), les `.pkl` sont dans `.gitignore` (binaires lourds, régénérables).

---

## BLOC 3 — Application, CI/CD, monitoring applicatif (C14–C21)

### C14 — Spécifications fonctionnelles

**Document :** `docs/specs_fonctionnelles.md` — 9 user stories, 32 critères d'acceptation.

**Couverture :** 28/32 critères implémentés [x]. Les 4 restants sont documentés avec une note de périmètre :
- Sélection de pays : périmètre fixé à France (toutes sources filtrées geo=FR à la collecte)
- Source par défaut : INSEE sélectionné par défaut (source officielle de référence)
- Note « base 2025 » visible dans l'UI : documenté dans specs_techniques, non affiché dans Streamlit
- Barres 3 couleurs : 2 couleurs implémentées (vert ≤ 5 pts / rouge > 5 pts)

**MCD :** `docs/mcd.md` — modèle Merise avec 5 entités conceptuelles (SOURCE, CATEGORIE_COICOP, PAYS, OBSERVATION_IPC, PRIX_ALIMENTAIRE), 5 associations avec cardinalités (1,1)→(0,N).

---

### C15 — Spécifications techniques

**Document :** `docs/specs_techniques.md` — 6 décisions techniques documentées avec justification.

| Décision | Résumé |
|---|---|
| #1 Normalisation | Règle unique : indice base 100=2015 pour toutes les sources |
| #2 API séparées | API data (8001) et API modèle (8002) — cycles de vie différents |
| #3 Prophet | Changepoints + IC natifs + scalabilité — voir C7 |
| #4 Split temporel strict | Pas de shuffle — évite le data leakage sur séries temporelles |
| #5 Exclusion catégorie 12 | Série INSEE absente + hétérogénéité des prix divers |
| #6 Réentraînement manuel | CmdStan incompatible avec CI automatisé |

---

### C16 — Gestion de projet Agile (Kanban)

**Méthode :** Kanban (projet solo, périmètre évolutif, flux continu par compétence).

**Outil :** GitHub Projects — board 4 colonnes (Backlog / In Progress / Review / Done).

**Convention de commit :** `<type>(<compétences>): <description> #<issue>`  
Exemple : `feat(C8): modèle Prophet IPC France 13 catégories INSEE #14`

**Board :** https://github.com/users/GitAlberto/projects/2  
*(Captures : `C16_pull_request_diff.png`, `C16_pull_request_description.png`, `C13_C16_pr59_ci_checks.png`)*

---

### C17 — Application Streamlit

**Ce que j'ai fait :** application 4 pages avec thème financier (`app/theme.py`).

| Page | Contenu |
|---|---|
| Accueil | KPIs IPC 2022-2025, statut APIs (✅/❌), navigation |
| Analyse Historique | Graphique IPC multi-sources, slider période, multi-catégories (max 5), stats descriptives |
| Analyse par Catégorie | IPC + variation YoY, heatmap mensuelle, décomposition saisonnière |
| Prédictions Prophet | Courbe historique + prédiction + IC 80%, MAE/RMSE/MAPE en sidebar, tableau détaillé |
| Métriques Modèle | Bar chart MAE 12 catégories, scatter RMSE vs MAE, tableau complet |

**Performances :** données historiques en cache 5 min (`@st.cache_data(ttl=300)`), prédictions en cache 1 min (`ttl=60`). Chargement < 3s pour les données, < 15s pour les prédictions Prophet.

---

### C18 — CI/CD application

Le pipeline `.github/workflows/ci_app.yml` exécute à chaque push :
- Lint Flake8 de l'application Streamlit
- Vérification des imports (aucune dépendance cassée)
- Pas de test end-to-end — Streamlit nécessite un navigateur headless non disponible en CI standard.

---

### C19 — Conteneurisation Docker

**`docker-compose.yml`** — 4 services orchestrés :

| Service | Image | Port | Rôle |
|---|---|---|---|
| `postgres` | postgres:15 | 5437 | Base de données PostgreSQL |
| `prometheus` | prom/prometheus | 9090 | Collecte des métriques |
| `grafana` | grafana/grafana | 3000 | Dashboards monitoring |
| `api_data` | build local | 8001 | API data (Docker uniquement) |
| `api_model` | build local | 8002 | API modèle (Docker uniquement) |

**Décision architecturale :** en production (démo), les APIs et Streamlit tournent en processus Python natifs (`.venv`) pour éviter les délais de rebuild Docker à chaque modification. Prometheus et Grafana restent en Docker. Cette architecture hybride est documentée dans `start.sh`.

*(Capture : `C19_docker_compose_up.png`)*

---

### C20 — Monitoring applicatif

**Dashboard Grafana** provisionné automatiquement au démarrage (`monitoring/grafana/provisioning/`).

**Règles d'alertes** (`monitoring/alerts.yml`) :
```yaml
- alert: API_Indisponible
  expr: api_up == 0
  for: 1m

- alert: Latence_Elevee  
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
  for: 2m

- alert: Taux_Erreurs_Eleve
  expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
  for: 2m
```

*(Captures : `C11_C20_grafana_monitoring_live.png`, `C11_C20_grafana_monitoring_session2.png`)*

---

### C21 — Gestion des incidents

**Deux incidents documentés :**

**Incident 1 — 2026-07-18 : Erreur PySpark (JAVA_HOME)**
- Symptôme : `Failed to build wheel for pyspark` à l'installation
- Cause : Java 21 installé mais PATH non rechargé dans la session VS Code en cours
- Résolution : fermeture/réouverture de VS Code, PATH rechargé automatiquement
- Correctif : note ajoutée dans `docs/specs_techniques.md` (limites connues)
- *(Captures : `C1_C21_erreur_pyspark_install.png`, `C21_installation_java21.png`)*

**Incident 2 — 2026-07-25 : 403 Forbidden sur API modèle (Docker)**
- Symptôme : client Streamlit reçoit 403 avec la bonne clé API
- Cause : `load_dotenv(override=True)` dans `auth.py` écrasait la variable `API_KEY` injectée par Docker avec la valeur `.env` (différente en Docker vs local)
- Résolution : `override=False` + bloc `environment` dans `docker-compose.yml` pour forcer `POSTGRES_HOST=postgres` et `POSTGRES_PORT=5432` en contexte Docker
- Commit correctif : `fix(C5/C19): corriger connexion PostgreSQL API dans Docker`
- *(Postmortem : `docs/incident_2026-07-25.md`)*

---

## 3. Bilan et limites assumées

### Résultats techniques

| Indicateur | Valeur |
|---|---|
| Tests automatisés | 47/47 ✅ |
| Couverture de code | 93% |
| Pipelines CI/CD | 3 (data, modèle, app) — tous verts |
| Catégories prédites | 12 / 13 COICOP (exclusion catégorie 12 documentée) |
| MAE moyenne Prophet | 1.43 pts IPC (1.31% MAPE) |
| Volume données | 3,68 M lignes dans inflation_unified |
| Sources intégrées | 5 (INSEE, BCE, Eurostat, DATAGOUV, OpenFoodFacts) |

### Limites assumées

- **DATAGOUV rebasé 2025 :** les valeurs DATAGOUV (base 2025=100) ne sont pas comparables en valeur absolue avec INSEE/ECB/Eurostat (base 2015=100). Les tendances relatives restent valides. La colonne `base_ref` permet à l'application d'informer l'utilisateur.

- **Horizon Prophet :** la précision se dégrade au-delà de 12 mois et sur les catégories très volatiles (énergie, communications). L'application limite le slider à 36 mois avec avertissement.

- **OpenFoodFacts non visualisé :** collecté (~5 k lignes de prix alimentaires) mais non intégré dans les prédictions — volume insuffisant et couverture géographique partielle (produits nationaux/locaux mélangés).

- **Réentraînement manuel :** les modèles Prophet sont réentraînés à la demande (`python model/train.py`), pas automatiquement à chaque nouvelle donnée INSEE mensuelle. Un cron job ou un trigger webhook serait la prochaine étape.

### Perspectives

1. Automatiser le réentraînement mensuel (trigger sur nouvelles données INSEE)
2. Ajouter la catégorie 12 (Biens et services divers) si la série BDM est identifiée
3. Intégrer les prix OpenFoodFacts dans un modèle hybride indices + prix terrain
4. Déployer sur un serveur distant (VPS ou cloud) pour une démo accessible sans Docker local

---

*Rapport rédigé dans le cadre du titre professionnel B3 RNCP Développeur en Intelligence Artificielle — Simplon / ECE Paris — Soutenance : 27 août 2026.*
