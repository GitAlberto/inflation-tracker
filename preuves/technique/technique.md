# Preuves techniques — Inflation Tracker (C1–C21)

**Projet :** Inflation Tracker France — B3 RNCP Développeur en IA  
**Auteur :** Alberto Bongue  
**Dossier :** `preuves/technique/`

Chaque capture est nommée `Cx_description.png` pour permettre la navigation rapide.  
2 fichiers préfixés `DOUBLON_` sont à supprimer manuellement.

---

## C1 — Collecte multi-sources

| Fichier | Ce que ça montre |
|---|---|
| `C1_source_insee_ipc_graphique.png` | Site INSEE : IPC France base 2015=100, jan. 2015 → déc. 2025 (119.76). Source officielle des données d'entraînement Prophet. |
| `C1_source_ecb_hicp.png` | Site BCE : HICP inflation rate zone euro 2019–2026. Pic à ~10% en 2022-2023. Preuve de la source ECB collectée via API. |
| `C1_C2_eurostat_pyspark_execution.png` | Terminal VS Code : exécution PySpark Eurostat — 3 511 040 lignes × 5 colonnes traitées, chargées dans `eurostat_bulk` PostgreSQL. Date : 2026-07-04. |
| `C1_C21_erreur_pyspark_install.png` | Erreur pip install pyspark : `Failed to build wheel for pyspark`. Incident initial déclenché par l'absence de Java dans le PATH. |
| `C1_C21_pyspark_reparé.png` | Pip install PySpark réussi après installation Java 21. `pyspark==3.5.1` satisfait. |

---

## C2 — Requêtes SQL

Les requêtes SQL sont dans `src/sql/queries_extraction.sql` et `src/sql/queries_analyse.sql`.  
La capture `C1_C2_eurostat_pyspark_execution.png` (ci-dessus) montre aussi le résultat d'une requête Spark SQL sur Eurostat.

---

## C4 — Base de données PostgreSQL

| Fichier | Ce que ça montre |
|---|---|
| `C4_creation_tables_pgadmin.png` | pgAdmin 4 : exécution de `schema.sql`, 5 tables créées (`ecb_hicp_raw`, `eurostat_bulk`, `inflation_unified`, `insee_ipc`, `openfoodfacts`). Query OK en 544 ms. |
| `C4_schema_tables_pgadmin.png` | pgAdmin 4 : diagramme ERD des 6 tables avec leurs colonnes et clés primaires. Vue structurelle du schéma final. |

MCD Merise : `docs/mcd.md`, `docs/mcd_merise_2026-07-29.pdf`, `docs/mcd_merise_2026-07-29.png`.

---

## C5 — API data REST

| Fichier | Ce que ça montre |
|---|---|
| `C5_swagger_api_data.png` | Swagger UI `localhost:8001/docs` : 9 endpoints documentés (GET /api/inflation, /tendance, /pays, /sources, /categories, /api/prix-alimentaires/*, /health). OpenAPI 3.1. |

---

## C6 — Veille technologique

| Fichier | Ce que ça montre |
|---|---|
| `C6_C7_ipc_rupture_ukraine.png` | Graphique INSEE annoté manuellement : rupture structurelle IPC 2021-2022 (Guerre Ukraine-Russie), cercle rouge pointillé. Utilisé dans la veille pour contextualiser le choix de Prophet avec changepoints. |

Veille complète : `docs/veille_C6_final.pdf`.

---

## C7 — Benchmark des modèles

| Fichier | Ce que ça montre |
|---|---|
| `C7_eda_ipc_insee.png` | EDA : IPC France Ensemble (base 100=2015) 2020–2026 + variation mensuelle (%). Pic 2022-2023 visible. |
| `C7_benchmark_predictions.png` | Benchmark Prophet vs ARIMA(2,1,2) vs Holt-Winters sur IPC France Ensemble. Prédictions 2025 vs réel. MAE : Holt-Winters 0.220, Prophet 0.262, ARIMA 0.977. |
| `C7_prophet_decomposition_ensemble.png` | Décomposition Prophet IPC France Ensemble : tendance (2020–2026) + saisonnalité annuelle. Justifie le choix de Prophet pour sa lisibilité des composantes. |

Benchmark détaillé : `docs/benchmark_resultats.json`.

---

## C8 — Modèle Prophet

| Fichier | Ce que ça montre |
|---|---|
| `C8_predictions_prophet.png` | Prédiction Prophet IPC '00 - Ensemble' 12 mois (2026) : historique réel (bleu foncé), prédiction (vert), IC 80% (zone). MAE=0.2624, RMSE=0.3233, MAPE=0.22%. |
| `C8_metriques_evaluation_terminal.png` | Terminal : sortie de `python evaluate.py` — tableau MAE/RMSE/MAPE pour 12 catégories, split train 2020-2024 / eval 2025. Moyenne MAE=1.4302, MAPE=1.31%. |
| `C8_prophet_decomposition_alimentation.png` | Décomposition Prophet IPC Alimentation France (INSEE 2020-2025) : tendance fortement croissante 2022-2023 (choc alimentaire post-Ukraine) + saisonnalité annuelle marquée. |

---

## C9 — API modèle REST

| Fichier | Ce que ça montre |
|---|---|
| `C9_swagger_api_modele.png` | Swagger UI `localhost:8002/docs` : 6 endpoints (GET /api/predict/{categorie}, /api/predict, /api/categories, /api/metrics, /api/metrics/{categorie}, /health). 12 catégories COICOP 00-11. |

---

## C11 / C20 — Monitoring Prometheus + Grafana

| Fichier | Ce que ça montre |
|---|---|
| `C11_grafana_dashboard_edition.png` | Dashboard Grafana en mode édition : panneaux Statut API (heatmap), Prédictions=13, Taux erreurs, Latence p95=95ms, MAE par catégorie (barres), Prédictions par catégorie (timeseries). |
| `C11_C20_grafana_monitoring_live.png` | Dashboard Grafana en production : API Disponibilité=UP (vert), 5 prédictions, Latence p95=433ms, Top catégories (00-Ensemble×2, 01-Alimentation×2, 06-Santé×1), Trafic par endpoint en temps réel. |
| `C11_C20_grafana_monitoring_session2.png` | Autre session Grafana : 23 prédictions cumulées, Latence p95=800ms, Top catégories (00-Ensemble×7, 02-Boissons×3, 04-Logement×3), histogramme latence, trafic multi-endpoints. |

---

## C12 — Tests et couverture

| Fichier | Ce que ça montre |
|---|---|
| `C12_tests_couverture_93pct.png` | Rapport pytest-cov : TOTAL 305 statements, 22 Miss, **93% couverture**. Détail par fichier (api/data/*, api/model/*). |

---

## C13 — CI/CD GitHub Actions

| Fichier | Ce que ça montre |
|---|---|
| `C13_CI_pr55_en_cours.png` | PR #55 (tests modèle + CI) : 1 check en cours, 3 successful. CI en cours d'exécution. |
| `C13_CI_pr55_success.png` | PR #55 : **All checks have passed** — 4 successful checks (CI data ×2, CI modèle ×2). |
| `C13_CI_pr56_en_cours.png` | PR #56 (pipeline ETL + Streamlit) : 2 in progress, 2 successful. CI data passe, CI modèle en cours. |
| `C13_CI_pr60_success.png` | PR #60 (auth X-API-Key + monitoring + tests) : 1 in progress, 5 successful (CI data ×2, CI app ×2, CI modèle push). |
| `C13_C16_pr59_ci_checks.png` | PR #59 (filtrage France + UI) : PR ouverte avec description complète, 3 checks en cours. |

---

## C16 — Gestion de projet Agile

| Fichier | Ce que ça montre |
|---|---|
| `C16_pull_request_diff.png` | GitHub "Comparing changes" AlbertoFinB3 → main : 1 commit, 6 files changed, diff API/data/routes/inflation.py (ajout filtre source sur /pays). |
| `C16_pull_request_description.png` | Formulaire "Open a pull request" rempli : titre + description Markdown détaillant les changements (filtrage France sur 4 collecteurs, suppression selectbox pays, API /pays). |

Kanban et backlog : `docs/agile.md`, board GitHub Projects.

---

## C19 — Conteneurisation Docker

| Fichier | Ce que ça montre |
|---|---|
| `C19_docker_compose_up.png` | Terminal : `docker-compose down` (4 containers removed) puis `docker-compose up -d` (4 containers started : postgres, prometheus, grafana, network). |

---

## C21 — Incident / postmortem

| Fichier | Ce que ça montre |
|---|---|
| `C1_C21_erreur_pyspark_install.png` | Incident PySpark : erreur `Failed to build wheel for pyspark` — Java absent du PATH. |
| `C21_installation_java21.png` | Résolution : installation Eclipse Temurin JDK 21 (Adoptium) via installateur Windows. |
| `C1_C21_pyspark_reparé.png` | Après résolution : pip install PySpark réussi, `pyspark==3.5.1` satisfait. |
| `C21_incident_CI_pr57_echec.png` | CI échoue sur PR #57 (feat C8/C14/...) : 2 failing (CI modèle ×2), cause racine — tests attendaient 13 catégories, modèle n'en entraîne que 12. |
| `C21_CI_pr57_relance_fix.png` | Relance CI après commit correctif `fix(C12/C13): test_list_available 13→12` : 4 checks in progress, retour à la normale. |

Postmortems complets : `docs/incident_2026-07-18.md`, `docs/incident_2026-07-25.md`.

---

## Fichiers à supprimer (doublons)

| Fichier | Raison |
|---|---|
| `DOUBLON_C8_predictions_prophet.png` | Même graphique que `C8_predictions_prophet.png`, version fenêtre matplotlib |
| `DOUBLON_C16_pull_request_diff.png` | Même PR que `C16_pull_request_diff.png`, zoom légèrement différent |
