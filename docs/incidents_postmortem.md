# Postmortems — Inflation Tracker

**Projet :** Inflation Tracker France — B3 RNCP Développeur en IA  
**Auteur :** Alberto Bongue

---

## Incident 1 — Pipeline ETL (2026-07-18)

**Sévérité :** Moyenne  
**Durée :** ~2h (détection → résolution)  
**Services impactés :** pipeline ETL, table `eurostat_bulk`, table `datagouv_ipc`

### Résumé

Lors de l'exécution de `python src/database/import_data.py`, deux sources de données
ont produit des résultats silencieusement incorrects :

1. **EUROSTAT** — 0 lignes insérées dans `eurostat_bulk` (attendu : ~27 000)
2. **DATAGOUV** — doublons et valeurs parasites dans `datagouv_ipc`

Le pipeline s'est terminé avec le statut `6 OK` sans lever d'exception,
masquant les anomalies dans les données chargées.

### Chronologie

| Heure | Événement |
|---|---|
| 12:53 | Lancement `import_data.py` — pipeline complet |
| 12:53 | Log `BASE_PER='2015' non trouvé — données conservées sans filtre de base` |
| 12:57 | Log `Filtrage unit=INX_A_AVG : 0 lignes conservées` |
| 12:57 | LOAD Eurostat : `insertion de 0 lignes dans eurostat_bulk` |
| 12:58 | Rapport final affiché `6 OK` — pas d'erreur levée |
| 13:10 | Inspection manuelle de `inflation_unified` : 33 702 lignes (attendu > 60 000) |
| 13:15 | Diagnostic : 3 causes racines identifiées |
| 14:30 | Corrections appliquées et pipeline re-testé |

### Causes racines

**1. Mauvais code d'unité Eurostat (`INX_A_AVG` → `I15`)**

Le script `collect_eurostat_spark.py` filtrait sur `unit = "INX_A_AVG"` après
avoir changé le dataset de `prc_hicp_manr` vers `prc_hicp_midx`.

`INX_A_AVG` est le code des moyennes annuelles, pas des indices mensuels.
Le dataset `prc_hicp_midx` utilise le code `I15` (Index 2015=100).

**Impact :** 0 ligne Eurostat dans `inflation_unified`. Perte de ~27 000 points
historiques couvrant 27 pays UE depuis 1997.

**2. Doublons DATAGOUV — dimensions non filtrées**

Le script `collect_csv.py` ne filtrait que `UNIT_MEASURE = "IX"`, laissant
passer trois dimensions cachées qui multipliaient les lignes par catégorie/mois :

- `GEO` : plusieurs territoires (France + DOM/COM comme "973" Guyane)
- `PRODUCT_GROUP` : sous-groupes produit ("4005", "4037") en plus de l'agrégat pur ("_Z")
- `IND_TYPE` : variations YoY (`"YOY"`) stockées avec `UNIT_MEASURE = "IX"` → valeurs 0.40
  mélangées aux indices (ex. 62.81)

**Impact :** 3+ lignes par (catégorie, date) dans `inflation_unified`. Valeurs parasites
rendant la colonne `valeur` incohérente.

**3. Rebasage INSEE 2015 → 2025 (non bloquant, documenté)**

Le fichier DATAGOUV `DS_IPC_PRINC_data.csv` ne contient plus de `BASE_PER = "2015"`.
INSEE a rebasé l'ensemble de ses séries vers 2025 en début d'année.

**Impact :** incompatibilité d'échelle entre DATAGOUV (base 2025=100) et les autres
sources (base 2015=100). Non bloquant pour les tendances, mais les valeurs absolues
ne sont pas comparables entre sources.

### Corrections appliquées

| Fichier | Correction |
|---|---|
| `collect_eurostat_spark.py` | `UNIT_FILTRE = "INX_A_AVG"` → `"I15"` |
| `collect_csv.py` | Ajout filtres `IND_TYPE="IX"`, `GEO="F"`, `PRODUCT_GROUP="_Z"` |
| `src/aggregate/README.md` | Documentation des divergences et état réel des données |
| `docs/specs_techniques.md` | Note sur BASE_PER=2025 et décision de conservation |

### Leçons apprises

**1. Un pipeline qui retourne `OK` ne garantit pas des données correctes.**  
Le log `0 lignes insérées` était présent mais noyé dans la sortie. Une validation
post-insertion (ex. `assert count > 1000`) aurait détecté l'anomalie immédiatement.

**2. Lire la documentation API avant de changer de dataset.**  
Le passage de `prc_hicp_manr` à `prc_hicp_midx` a été fait sans vérifier
les codes d'unité disponibles dans le nouveau dataset.

**3. Inspecter les données brutes avant de filtrer.**  
Un `df["UNIT_MEASURE"].value_counts()` au début de `transform()` aurait montré
immédiatement la présence de `"YOY"` avec `UNIT_MEASURE = "IX"`.

### Actions préventives

- [ ] Ajouter des assertions post-LOAD dans chaque script collect (`count > seuil`)
- [ ] Logger `value_counts()` des colonnes filtrées au début de chaque `transform()`
- [ ] Ajouter un test d'intégration vérifiant les volumes minimaux après pipeline

---

## Incident 2 — Authentification API (2026-07-25)

**Sévérité :** Haute  
**Durée :** ~30 min (détection → résolution)  
**Services impactés :** Application Streamlit — page Prédictions, page Analyse Historique

### Résumé

Après l'ajout de l'authentification `X-API-Key` sur les deux APIs (C9/C10),
l'application Streamlit affichait systématiquement :

> *"API modèle indisponible. Démarrez : uvicorn api.model.main:app --port 8002"*

pourtant les deux services uvicorn étaient bien démarrés et la variable `API_KEY`
correctement définie dans `.env`.

### Chronologie

| Heure | Événement |
|---|---|
| 14:10 | Ajout de `Security(verify_key)` sur les routers `api/data` et `api/model` |
| 14:15 | Redémarrage des APIs — Swagger `/docs` répond 200 avec le bon header |
| 14:20 | Ouverture de Streamlit page Prédictions → bannière rouge "API indisponible" |
| 14:25 | Test manuel `curl -H "X-API-Key: ..." http://localhost:8002/api/predict/...` → 200 OK |
| 14:30 | Diagnostic : `app/api_client.py` n'envoie aucun header → 403 sur tous les appels |
| 14:35 | Correction appliquée dans `api_client.py` et `data_client.py` |
| 14:40 | Page Prédictions opérationnelle — métriques MAE/RMSE/MAPE affichées |

### Cause racine

`app/api_client.py` et `app/data_client.py` effectuaient leurs requêtes HTTP
sans le header `X-API-Key` :

```python
# Avant (incorrect)
r = requests.get(f"{MODEL_URL}/api/predict/{categorie}", timeout=10)
```

Après l'activation de l'auth sur les routers, chaque appel retournait **HTTP 403**.
Le client capturait cette erreur comme une `RequestException` et renvoyait `None`.
Streamlit interprétait ce `None` comme une indisponibilité de l'API.

Le symptôme trompeur : l'API **fonctionnait correctement**, seul le client
Streamlit n'envoyait pas les credentials.

### Correction appliquée

Ajout du header dans les deux clients Streamlit :

```python
# app/api_client.py et app/data_client.py
_API_KEY = os.getenv("API_KEY", "")
_HEADERS  = {"X-API-Key": _API_KEY}

# Toutes les requêtes protégées reçoivent le header
r = requests.get(f"{MODEL_URL}/api/predict/{categorie}",
                 headers=_HEADERS, timeout=10)
```

La route `/health` reste publique (pas de header requis).

**Commit :** `92e3b7e` — `feat(C5/C9/C10/C12/C17/C20)`

### Leçons apprises

**1. Ajouter l'auth côté serveur implique de mettre à jour tous les clients.**  
L'authentification n'est complète que lorsque chaque consommateur de l'API
envoie les credentials. Un test d'intégration end-to-end (client → API) aurait
détecté l'erreur immédiatement.

**2. HTTP 403 ≠ service indisponible.**  
Le message "API indisponible" affiché par Streamlit était trompeur — l'API
répondait, mais refusait la requête non authentifiée. Distinguer les erreurs
réseau (timeout, connexion refusée) des erreurs HTTP métier (4xx) améliore
le diagnostic.

**3. Tester le flux complet après chaque changement de sécurité.**  
Après activation de l'auth, vérifier systématiquement : API seule (curl),
puis client (Streamlit), puis tests automatisés.

### Actions préventives

- [x] `tests/test_api.py` et `tests/test_api_model.py` configurés avec
      `X-API-Key` par défaut dans `TestClient` — un 403 fait échouer le test
- [ ] Ajouter un test d'intégration Streamlit → API vérifiant que le header
      est bien transmis sur chaque endpoint protégé
