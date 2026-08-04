# Kanban — Inflation Tracker · RNCP B3
> Référence officielle : PDF Simplon / ECE K. Kadri 2026  
> Board Jira : (URL à compléter)

---

## Légende statuts

| Icône | Colonne |
|---|---|
| ✅ | Done |
| 🔄 | In Progress |
| 👀 | Review |
| 📋 | Backlog |

---

## BLOC 1 — Données exploitables (C1-C5)

---

### C1 — Extraction multi-sources · ✅ Done

**Epic :** Bloc 1 — Données exploitables  
**Feature :** Collecte automatisée depuis 4 sources IPC hétérogènes (INSEE, ECB, Eurostat, data.gouv)

**US1 — Collecte INSEE BDM SDMX**  
En tant que data engineer, je collecte les données IPC via l'API INSEE BDM avec authentification OAuth2, afin d'avoir la source officielle IPC France.  
→ `src/collect/collect_insee_api.py`

**US2 — Collecte ECB HICP**  
En tant que data engineer, je collecte les données HICP via l'API publique BCE, afin d'avoir la référence zone euro.  
→ `src/collect/load_ecb_to_db.py`

**US3 — Collecte Eurostat via PySpark**  
En tant que data engineer, je collecte le bulk TSV Eurostat via PySpark, afin d'avoir une couverture UE large.  
→ `src/collect/collect_eurostat_spark.py`

**US4 — Collecte data.gouv.fr**  
En tant que data engineer, je collecte le CSV institutionnel data.gouv.fr, afin d'avoir une 4e source de cross-validation.  
→ `src/collect/collect_csv.py`

**US5 — Scraping Open Food Facts (OFF)**  
En tant que data engineer, je collecte les prix alimentaires réels via l'API Open Food Facts, afin d'enrichir les données IPC avec des prix produits concrets.  
→ `src/collect/scrape_openfoodfacts.py`

---

### C2 — Requêtes SQL · ✅ Done

**Epic :** Bloc 1 — Données exploitables  
**Feature :** Requêtes SQL documentées sur inflation_unified (3,68M lignes) — DDL + lecture + agrégation

**US1 — Schéma DDL PostgreSQL**  
En tant que data engineer, je définis le schéma PostgreSQL avec clés primaires et index de performance, afin de structurer la base de données.  
→ `src/database/schema.sql`

**US2 — Requêtes de lecture API (SELECT, WHERE, ORDER BY, GROUP BY)**  
En tant que développeur, j'écris et documente les requêtes SQL de tous les endpoints REST, afin d'exposer les données IPC.  
→ `api/data/routes/inflation.py`

**US3 — Requête MIN/MAX date par source**  
En tant que développeur, j'écris la requête SELECT MIN/MAX sur date_obs filtrée par source, afin de calibrer dynamiquement les sliders Streamlit.  
→ `api/data/routes/inflation.py` — endpoint `/date-range`

---

### C3 — Agrégation / nettoyage · ✅ Done

**Epic :** Bloc 1 — Données exploitables  
**Feature :** Pipeline ETL normalisant 4 sources hétérogènes en table unifiée `inflation_unified`

**US1 — Normalisation format COICOP**  
En tant que data engineer, je normalise les 4 sources au format `XX - Label`, afin d'avoir un format homogène cross-sources.  
→ `src/pipeline/aggregate_clean.py`

**US2 — Déduplication et typage**  
En tant que data engineer, je déduplique les lignes et type les colonnes (date_obs DATE, valeur NUMERIC), afin de garantir la qualité des données.  
→ `src/pipeline/aggregate_clean.py`

**US3 — Filtrage géographique France**  
En tant que data engineer, je filtre sur pays=FR à la collecte sur toutes les sources, afin de respecter le périmètre projet.  
→ `src/collect/collect_*.py`

---

### C4 — Base de données RGPD · ✅ Done

**Epic :** Bloc 1 — Données exploitables  
**Feature :** PostgreSQL 15 avec schéma 6 tables + registre de traitement RGPD

**US1 — Schéma PostgreSQL complet**  
En tant que data engineer, je crée le schéma avec 6 tables, clés primaires et index de performance, afin d'avoir une base structurée.  
→ `src/database/schema.sql`

**US2 — Registre RGPD**  
En tant que responsable traitement, je documente le registre RGPD (finalité, données traitées, durée conservation, absence de données personnelles), afin de respecter le cadre légal.  
→ `docs/rgpd_register.md`

---

### C5 — API data REST · ✅ Done

**Epic :** Bloc 1 — Données exploitables  
**Feature :** API FastAPI port 8001 avec 8 endpoints, auth X-API-Key 2 niveaux, documentation OpenAPI

**US1 — Endpoints données IPC**  
En tant que développeur, je crée les endpoints `/api/inflation`, `/tendance`, `/sources`, `/categories`, `/pays`, `/date-range`, afin d'exposer les données IPC via REST.  
→ `api/data/routes/inflation.py`

**US2 — Authentification X-API-Key (admin / user)**  
En tant que développeur, j'implémente l'auth X-API-Key avec 2 niveaux d'accès, afin de sécuriser l'API.  
→ `api/data/auth.py`

**US3 — Documentation OpenAPI auto-générée**  
En tant qu'utilisateur API, j'accède à la documentation Swagger sans code supplémentaire, afin de comprendre et tester tous les endpoints.  
→ `http://localhost:8001/docs`

---

## BLOC 2 — Service IA intégré et industrialisable (C6-C13)

---

### C6 — Veille technique / réglementaire · ✅ Done

**Epic :** Bloc 2 — Service IA intégré  
**Feature :** Document de veille sur outils de collecte, traitement et prédiction de données économiques

**US1 — Sélection de sources qualifiées**  
En tant qu'apprenant, je sélectionne 8+ sources qualifiées (officielles, académiques, techniques), afin de démontrer une démarche de veille rigoureuse.  
→ `veille_C6_final.docx`

**US2 — Synthèse et justification des choix techniques**  
En tant qu'apprenant, je rédige une synthèse comparative justifiant les choix technologiques du projet (Prophet vs alternatives, FastAPI vs Flask, etc.), afin de prouver l'analyse critique.  
→ `veille_C6_final.docx`

---

### C7 — Benchmark services IA · ✅ Done

**Epic :** Bloc 2 — Service IA intégré  
**Feature :** Comparaison Prophet / ARIMA / LSTM sur séries IPC France avec décision argumentée

**US1 — Tableau comparatif sur données réelles**  
En tant que data scientist, je compare Prophet, ARIMA/SARIMA et PyTorch LSTM selon 10 critères (facilité, interprétabilité, saisonnalité, volume, intégration FastAPI…), afin de choisir objectivement le modèle de prédiction.  
→ `veille_C6_final.pdf` — Section 3, page 10

**US2 — Décision argumentée Prophet retenu**  
En tant que data scientist, je documente la décision de retenir Prophet sur 6 critères (saisonnalité Fourier, 72 obs. suffisantes, interprétabilité, intégration Python, changepoints, MAPE < 5% 12/12), afin de justifier le choix devant le jury.  
→ `veille_C6_final.pdf` — Section 5.1, pages 14-15

**US3 — Justification des modèles écartés**  
En tant que data scientist, je documente pourquoi LSTM (données insuffisantes, boîte noire, GPU requis) et ARIMA (saisonnalité unique, ordres manuels) ont été écartés, afin de prouver une démarche de benchmark rigoureuse.  
→ `veille_C6_final.pdf` — Sections 5.2 et 5.3, page 16

---

### C8 — Paramétrage service IA · ✅ Done

**Epic :** Bloc 2 — Service IA intégré  
**Feature :** Modèle Prophet entraîné sur 12 catégories COICOP France (base IPC 2015=100)

**US1 — Entraînement 12 modèles Prophet**  
En tant que data scientist, j'entraîne un modèle Prophet par catégorie COICOP France, afin d'avoir un service de prédiction granulaire par catégorie.  
→ `model/train.py`

**US2 — Métriques d'évaluation**  
En tant que data scientist, je calcule et stocke MAE/RMSE/MAPE par catégorie sur split 2025, afin de documenter les performances du modèle.  
→ `model/metrics.json`

**US3 — Sérialisation des modèles**  
En tant que data scientist, je sérialise les 12 modèles en fichiers `.pkl`, afin de les charger à la demande sans ré-entraînement.  
→ `model/*.pkl`

---

### C9 — API modèle IA · ✅ Done

**Epic :** Bloc 2 — Service IA intégré  
**Feature :** API FastAPI port 8002 exposant les prédictions Prophet avec auth, tests et documentation

**US1 — Endpoint prédictions par catégorie**  
En tant que développeur, je crée l'endpoint `GET /predict/{categorie}?horizon=N` retournant les prédictions avec intervalles de confiance 80%, afin d'exposer le modèle via REST.  
→ `api/model/routes/predict.py`

**US2 — Endpoints métriques modèle**  
En tant que développeur, je crée les endpoints `/metrics` et `/metrics/{categorie}` (admin only), afin d'exposer les performances du modèle via REST.  
→ `api/model/routes/metrics.py`

**US3 — Auth X-API-Key sur API modèle**  
En tant que développeur, j'implémente l'auth X-API-Key (admin/user) sur l'API modèle, afin de sécuriser l'accès aux prédictions.  
→ `api/model/auth.py`

---

### C10 — Intégration dans application · ✅ Done

**Epic :** Bloc 2 — Service IA intégré  
**Feature :** Pages Streamlit connectées à l'API modèle Prophet (appels HTTP réels, erreurs gérées)

**US1 — Page Prédictions (appel réel API modèle)**  
En tant qu'utilisateur, je visualise les prédictions Prophet par catégorie avec IC 80% dans Streamlit, afin d'anticiper l'évolution de l'inflation.  
→ `app/pages/3_Predictions.py`

**US2 — Page Métriques modèle (appel réel API modèle)**  
En tant qu'utilisateur, je consulte les performances MAE/RMSE/MAPE dans Streamlit, afin d'évaluer la fiabilité des prédictions.  
→ `app/pages/4_Metriques_Modele.py`

**US3 — Gestion des erreurs API modèle**  
En tant qu'utilisateur, je vois un message clair si l'API modèle est indisponible, afin de comprendre l'état du service sans message technique.  
→ `app/api_client.py`

---

### C11 — Monitoring modèle · ✅ Done

**Epic :** Bloc 2 — Service IA intégré  
**Feature :** Métriques Prometheus + dashboard Grafana dédié au modèle Prophet

**US1 — Compteurs Prometheus API modèle**  
En tant qu'ops, je définis les métriques Prometheus (predictions_total par catégorie, latence), afin de monitorer l'usage du modèle en production.  
→ `api/model/metrics.py`

**US2 — Dashboard Grafana modèle**  
En tant qu'ops, je crée un dashboard Grafana avec panels MAE/catégorie, volume prédictions, latence P50/P95/P99, afin de détecter toute dégradation de performance.  
→ `monitoring/grafana/dashboards/model_dashboard.json`

---

### C12 — Tests automatisés modèle / data · ✅ Done

**Epic :** Bloc 2 — Service IA intégré  
**Feature :** Suite pytest 47 tests — 93% couverture — 2 APIs couvertes

**US1 — Tests API data (27 tests)**  
En tant que développeur, j'écris 27 tests couvrant tous les endpoints de l'API data (GET, filtres, auth, erreurs 4xx), afin de garantir la non-régression.  
→ `tests/test_api.py`

**US2 — Tests API modèle (20 tests)**  
En tant que développeur, j'écris 20 tests couvrant tous les endpoints de l'API modèle (predict, métriques, auth), afin de garantir la non-régression.  
→ `tests/test_api_model.py`

---

### C13 — Livraison continue modèle (MLOps) · ✅ Done

**Epic :** Bloc 2 — Service IA intégré  
**Feature :** Pipeline GitHub Actions : install → pytest → rapport couverture à chaque push

**US1 — Workflow GitHub Actions CI**  
En tant que DevOps, je configure GitHub Actions pour exécuter pytest + coverage à chaque push sur toutes les branches, afin d'automatiser la validation du service IA.  
→ `.github/workflows/`

**US2 — Rapport couverture visible sur chaque commit**  
En tant que DevOps, je génère un rapport de couverture (93%) visible sur chaque run CI, afin de tracer la qualité du code dans le temps.  
→ `.github/workflows/` — step coverage report

---

## BLOC 3 — Application IA complète (C14-C21)

---

### C14 — Analyse besoin application · ✅ Done

**Epic :** Bloc 3 — Application IA complète  
**Feature :** Spécifications fonctionnelles avec personas, user stories et critères d'acceptation

**US1 — Définition des personas**  
En tant que chef de projet, je définis 3 personas (data analyst, économiste, ops), afin de cadrer les besoins utilisateurs réels de l'application.  
→ `docs/specs_fonctionnelles.md`

**US2 — User stories avec critères d'acceptation**  
En tant que chef de projet, je rédige les user stories avec critères d'acceptation mesurables, afin de cadrer le développement sur des besoins concrets.  
→ `docs/specs_fonctionnelles.md`

---

### C15 — Architecture technique · ✅ Done

**Epic :** Bloc 3 — Application IA complète  
**Feature :** Document de specs techniques + schéma fonctionnel 4 couches du flux de données end-to-end

**US1 — Document specs techniques**  
En tant qu'architecte, je documente la stack complète (PostgreSQL, FastAPI x2, Streamlit, Prophet, Prometheus, Grafana, Docker) avec justification de chaque choix, afin d'argumenter l'architecture devant le jury.  
→ `docs/specs_techniques.md`

**US2 — Schéma d'architecture flux de données**  
En tant qu'architecte, je crée le schéma fonctionnel 4 couches (Sources → ETL Python → PostgreSQL → Exposition APIs + Modèle IA → Streamlit + Grafana), afin d'avoir une slide d'architecture claire pour la soutenance.  
→ `veille_C6_final.pdf` — page 4 (schéma complet avec 5 sources, scripts ETL, 6 tables, APIs, Streamlit, Grafana)

---

### C16 — Coordination agile · ✅ Done

**Epic :** Bloc 3 — Application IA complète  
**Feature :** Pilotage Kanban Jira avec issues C1-C21, convention de commits et documentation méthode

**US1 — Board Kanban Jira**  
En tant que chef de projet, je maintiens un board avec issues liées aux compétences RNCP et statuts à jour, afin de tracer l'avancement de manière agile.  
→ Jira (board en ligne)

**US2 — Convention de commits feat(CX)**  
En tant que chef de projet, j'applique la convention `feat(CX): description #issue` à chaque commit, afin d'assurer la traçabilité compétence ↔ code.  
→ `git log` (historique commits)

**US3 — Documentation méthode agile**  
En tant que chef de projet, je documente la méthode, le workflow et les rituels, afin de prouver une démarche agile structurée.  
→ `docs/agile.md`

---

### C17 — Développement application · ✅ Done

**Epic :** Bloc 3 — Application IA complète  
**Feature :** Application Streamlit 4 pages avec thème financier, auth, sliders dynamiques et gestion des erreurs

**US1 — Page Analyse Historique**  
En tant qu'utilisateur, je visualise les courbes IPC multi-catégories avec slider dynamique et statistiques descriptives, afin d'analyser l'historique d'inflation.  
→ `app/pages/1_Analyse_Historique.py`

**US2 — Page Analyse Catégorie**  
En tant qu'utilisateur, je consulte les KPIs, la variation YoY et la heatmap saisonnière d'une catégorie IPC, afin d'analyser une catégorie en profondeur.  
→ `app/pages/2_Analyse_Categorie.py`

**US3 — Page Prédictions**  
En tant qu'utilisateur, je visualise les prédictions Prophet 1-24 mois avec intervalles de confiance 80%, afin d'anticiper l'évolution de l'inflation.  
→ `app/pages/3_Predictions.py`

**US4 — Page Métriques modèle**  
En tant qu'utilisateur, je consulte les performances du modèle par catégorie (MAE/RMSE/MAPE), afin d'évaluer la fiabilité des prédictions.  
→ `app/pages/4_Metriques_Modele.py`

---

### C18 — Intégration continue · ✅ Done

**Epic :** Bloc 3 — Application IA complète  
**Feature :** GitHub Actions déclenchant pytest à chaque push et pull request

**US1 — Workflow CI automatique**  
En tant que DevOps, je configure GitHub Actions pour déclencher pytest à chaque push et PR sur toutes les branches, afin de détecter les régressions avant tout merge.  
→ `.github/workflows/`

---

### C19 — Livraison continue app · ✅ Done

**Epic :** Bloc 3 — Application IA complète  
**Feature :** Docker Compose pour l'infrastructure + script démarrage one-shot

**US1 — Docker Compose infrastructure**  
En tant que DevOps, je conteneurise PostgreSQL, Prometheus et Grafana via Docker Compose avec volumes nommés, afin de garantir la reproductibilité de l'environnement.  
→ `docker-compose.yml`

**US2 — Script démarrage one-shot**  
En tant qu'ops, je lance toute l'application (postgres + API data + API modèle + Streamlit) en une seule commande, afin de simplifier le déploiement et la démonstration jury.  
→ `start.sh`

---

### C20 — Monitoring applicatif · ✅ Done

**Epic :** Bloc 3 — Application IA complète  
**Feature :** Prometheus + 2 dashboards Grafana (overview système + modèle) + alertes

**US1 — Dashboard Grafana overview système**  
En tant qu'ops, je surveille l'état global du système (statut APIs, latence, taux d'erreur, volume requêtes) via un dashboard Grafana, afin de détecter les incidents.  
→ `monitoring/grafana/dashboards/overview_dashboard.json`

**US2 — Alertes Grafana sur seuils critiques**  
En tant qu'ops, je configure des alertes sur seuils critiques (latence P95 > 2s, taux erreur > 5%), afin d'être notifié automatiquement en cas d'incident.  
→ `monitoring/grafana/alerting/` *(📋 Backlog)*

---

### C21 — Incident technique · ✅ Done

**Epic :** Bloc 3 — Application IA complète  
**Feature :** Postmortem incident auth X-API-Key (2026-07-25) + correction commitée + test de non-régression

**US1 — Postmortem format SRE**  
En tant que tech lead, je documente l'incident (header X-API-Key absent → 403 → "API indisponible") avec chronologie, cause racine et correction, afin de prouver une démarche de fiabilité professionnelle.  
→ `docs/incident_2026-07-25.md`

**US2 — Correction et test de non-régression**  
En tant que développeur, je corrige l'incident (injection `_HEADERS` dans le client Streamlit) et relance les 47 tests pour prouver la non-régression.  
→ `app/data_client.py` + résultat `47/47 PASSED`
