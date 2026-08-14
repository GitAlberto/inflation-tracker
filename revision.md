# Révision soutenance — extraits de code commentés

---

## C1 — Capture 1 : dépivotage PySpark (`collect_eurostat_spark.py`, lignes 288–329)

**Contexte** : le fichier Eurostat est en format **wide** — une ligne par combinaison pays/catégorie, une colonne par période mensuelle. Il faut le dépivater en **long** : une ligne = une observation.

```python
# --- Séparation de la clé composite ---
# La première colonne contient "M,I15,CP00,FR" — 4 dimensions en une seule chaîne
df_spark = (df_spark
            .withColumn("freq",   F.split(F.col("cle_composite"), ",")[0])  # "M" = mensuel
            .withColumn("unit",   F.split(F.col("cle_composite"), ",")[1])  # "I15" = indice base 2015=100
            .withColumn("coicop", F.split(F.col("cle_composite"), ",")[2])  # "CP00" = catégorie COICOP
            .withColumn("geo",    F.split(F.col("cle_composite"), ",")[3])  # "FR" = pays
            .drop("cle_composite"))  # supprime la colonne source, maintenant décomposée

# F.split() coupe la chaîne sur "," → retourne un ArrayType ; [0],[1]... = index dans le tableau
# .withColumn() ajoute/remplace une colonne — Spark est immutable : chaque appel crée un nouveau DataFrame

# --- Filtrage AVANT le dépivotage ---
df_spark = df_spark.filter(F.col("unit") == UNIT_FILTRE)  # garde "I15" seulement — cohérence indices avec INSEE et DATAGOUV
df_spark = df_spark.filter(F.col("geo") == "FR")          # France uniquement — filtrer AVANT stack() divise le volume traité par 27

# --- Dépivotage (wide → long) avec stack() ---
colonnes_dates = [c for c in df_spark.columns if c not in ("freq", "unit", "coicop", "geo")]
# list comprehension : récupère toutes les colonnes sauf les 4 dimensions fixes
# résultat : ~350 noms de colonnes "2024-12", "2024-11", ... "1996-01"

stack_expr = f"stack({len(colonnes_dates)}, " + ", ".join(
    [f"'{c}', `{c}`" for c in colonnes_dates]  # paire : 'nom_col' (string) + `nom_col` (valeur, backticks car tirets dans le nom)
) + ") as (time_period, obs_value_raw)"
# stack(350, '2024-12', `2024-12`, '2024-11', `2024-11`, ...) as (time_period, obs_value_raw)
# transforme 350 colonnes en 350 lignes — expression SQL construite dynamiquement depuis la liste réelle des colonnes

df_long = df_spark.select(
    "freq", "unit", "coicop", "geo",  # conserve les 4 dimensions fixes sur chaque ligne produite
    F.expr(stack_expr)                # F.expr() évalue la string SQL → seul moyen d'utiliser stack() depuis Python PySpark
)

# AVANT (wide) : CP00 | FR | 119.8 p | 118.5 | 117.3   (3 colonnes de dates)
# APRÈS (long) : CP00 | FR | 2024-12 | 119.8 p
#                CP00 | FR | 2024-11 | 118.5
#                CP00 | FR | 2024-10 | 117.3

# --- Nettoyage des flags qualité Eurostat ---
# Les valeurs brutes contiennent des flags : "119.8 p" (provisoire), "2.1 e" (estimé)
df_long = (df_long
           .withColumn("obs_value_str",
                       F.trim(                                                    # supprime les espaces résiduels en bord de chaîne
                           F.regexp_replace(F.col("obs_value_raw"),
                                            r"[a-zA-Z\s]+",                      # regex : toute lettre ou espace
                                            "")))                                 # remplacé par rien → "119.8 p" → "119.8"
           .withColumn("obs_value",
                       F.col("obs_value_str").cast("double"))                    # convertit "119.8" en float ; retourne null si impossible
           .drop("obs_value_raw", "obs_value_str"))                              # supprime les colonnes intermédiaires de travail

nb_avant = df_long.count()
df_long = df_long.filter(F.col("obs_value").isNotNull())  # élimine les null = valeurs manquantes Eurostat codées ":" dans le fichier source
nb_apres = df_long.count()
```

---

## C1 — Capture 2 : requête API INSEE BDM (`collect_insee_api.py`, lignes 220–241)

**Contexte** : l'API INSEE BDM (Banque de Données Macro-économiques) permet de récupérer les 13 séries IPC en une seule requête HTTP grâce au mécanisme multi-idbank.

```python
    idbanks_str = "+".join(idbanks.keys())  # joint les 13 identifiants INSEE par "+" → "001759970+001763417+..."
    url = f"{BDM_DATA_URL}/{idbanks_str}"   # URL finale : https://api.insee.fr/.../SERIES_BDM/001759970+001763417+...
    # l'API BDM supporte nativement plusieurs idbanks dans l'URL — une seule requête pour toutes les séries IPC

    params: dict[str, str] = {"startPeriod": START_PERIOD}  # annotation de type explicite : clés ET valeurs sont des strings
    # startPeriod = "2020-01" (lu depuis .env) — ne télécharge pas toute l'historique depuis 1990
    if END_PERIOD:               # END_PERIOD = "" par défaut → l'API retourne jusqu'aux données les plus récentes
        params["endPeriod"] = END_PERIOD  # n'ajoute ce paramètre que s'il est défini — évite d'envoyer endPeriod=""

    headers: dict[str, str] = {"Accept": "application/xml"}  # demande explicitement du SDMX-XML ; sans ça l'API pourrait retourner du JSON
    if token:                    # token = None si OAuth2 absent ou échoué → on reste en accès public
        headers["Authorization"] = f"Bearer {token}"  # format standard OAuth2 ; "Bearer" = porteur du token

    log.info(f"GET {url}")
    r = requests.get(url, params=params, headers=headers, timeout=60)
    # params encodés automatiquement en query string : ?startPeriod=2020-01
    # timeout=60 : 60 secondes max — le fichier XML avec 13 séries peut être volumineux

    r.raise_for_status()  # lève une HTTPError si code >= 400 (401 non autorisé, 429 trop de requêtes, 500 serveur...)
    # sans cette ligne une erreur HTTP passerait silencieusement — r.text serait une page d'erreur HTML

    log.info(f"Réponse : HTTP {r.status_code} — {len(r.content):,} octets reçus")
    # len(r.content) = taille en bytes ; :, = formatage Python avec séparateur de milliers → ex : 245,800 octets
    return r.text  # corps de la réponse décodé en string UTF-8 par requests → le XML SDMX brut transmis à transform()
```

---

## C6/C7 — Benchmark modèles : pourquoi Prophet plutôt que Holt-Winters ?

**Contexte** : le benchmark (`Benchmark — IPC France Ensemble — Prédictions vs Réel 2025`) compare trois modèles sur les données 2025 (test set) après entraînement sur 2020-2024.

| Modèle | MAE | MAPE |
|---|---|---|
| Holt-Winters | 0.220 | 0.18% |
| Prophet | 0.262 | 0.22% |
| ARIMA(2,1,2) | 0.977 | 0.81% |

**Holt-Winters performe légèrement mieux que Prophet** sur ces métriques.

### Pourquoi LSTM n'est pas dans le benchmark (alors qu'il est dans la veille)

LSTM est étudié en veille (section 2.2) puis **explicitement écarté** (section 5.2) :
- nécessite un GPU et beaucoup de données (séries longues de milliers de points)
- risque fort de surapprentissage sur une série courte de 60 mois
- implémentation disproportionnée par rapport au gain attendu

Holt-Winters le remplace dans le benchmark comme deuxième référence classique — il figure aussi dans la veille (section 2.1).

### Pourquoi retenir Prophet malgré une MAE légèrement supérieure

Question probable du jury : *"Holt-Winters est meilleur sur les métriques, pourquoi avoir choisi Prophet ?"*

Réponse :
1. **Intervalles de confiance** — Prophet produit des IC 80% (zone verte sur le graphique) ; Holt-Winters n'en fournit pas nativement
2. **Interprétabilité** — Prophet décompose la prédiction en trend + saisonnalité + effets jours fériés, lisibles séparément
3. **Robustesse aux données manquantes** — Prophet gère nativement les trous dans la série ; Holt-Winters nécessite une série continue
4. **Chocs exogènes** — Prophet permet d'ajouter des régresseurs externes (ex : choc Covid, prix énergie) ; Holt-Winters non
5. **Écart de MAE minime** — 0.04 pt d'indice IPC (base 100) est négligeable en pratique

Conclusion : **l'écart de performance est marginal, le gain en interprétabilité et en flexibilité justifie le choix Prophet**.

---

## C7/C8 — Pourquoi réentraîner sur toutes les données après l'évaluation ?

Dans `model/train.py`, `train_one()` crée **deux modèles distincts** :

```python
# Modèle 1 — évaluation honnête (ne voit jamais 2025)
model_eval = Prophet(**PROPHET_PARAMS)
model_eval.fit(train)   # entraîné sur 2020-2024 uniquement

# Modèle 2 — production (toutes les données disponibles)
model_prod = Prophet(**PROPHET_PARAMS)
model_prod.fit(df_prophet)   # entraîné sur 2020-2025
```

**Deux objectifs, deux modèles :**

| | `model_eval` | `model_prod` |
|---|---|---|
| Données | 2020–2024 (60 pts) | 2020–2025 (72 pts) |
| But | calculer MAE/RMSE/MAPE | prédire 2026 et après |
| Sauvegardé ? | non — jeté après métriques | oui → `prophet_*.pkl` |

**Pourquoi c'est obligatoire :**
- Si on évaluait sur `model_prod`, le modèle aurait "vu" 2025 pendant l'entraînement → les métriques seraient biaisées (data leakage), pas représentatives des vraies performances
- Une fois les métriques validées (le modèle est "bon"), il serait dommage de ne pas lui donner toutes les données disponibles pour prédire l'avenir — plus de données = tendance récente mieux capturée

**Analogie** : on passe un examen blanc sur le cours de 4 ans (évaluation honnête) → on valide le niveau → on révise en ajoutant l'année 5 avant le vrai examen (production).

---

## C13 — Pipeline CI GitHub Actions : la CI valide, elle n'entraîne pas

**Fichier** : `.github/workflows/ci_model.yml` — lignes 11-42

**Ce que fait le pipeline à chaque push/PR vers `main` :**

1. Checkout du code (`.pkl` inclus car committés)
2. Installation Python 3.12 + `pip install -r requirements.txt`
3. `pytest tests/test_model.py -v` — 17 tests sur les `.pkl` déjà présents
4. Upload du rapport de couverture

**Ce que le pipeline NE fait PAS — et pourquoi :**

CmdStan (~500 Mo, moteur C++ de Prophet) n'est pas compilé en CI — trop lourd pour GitHub Actions.
→ L'entraînement reste manuel en local : `python model/train.py`
→ Les 12 `.pkl` + `metrics.json` sont committés dans le repo (12 × 17 Ko = 204 Ko)
→ La CI les récupère via `checkout` et exécute les tests dessus

**Preuve dans le workflow :**
```yaml
- name: Install dependencies
  run: pip install -r requirements.txt
  # CmdStan (C++) n'est PAS compilé
  # → les tests nécessitant les .pkl sont automatiquement skippés

- name: Run model unit tests (C12)
  run: pytest tests/test_model.py -v
  env:
    CI: "true"   # active les skipif sur les tests nécessitant des ressources externes
```

**À retenir pour la soutenance :**
*"La CI ne réentraîne rien — elle vérifie que ce qui a été entraîné localement reste fiable."*
Automatiser un entraînement Prophet en CI sans CmdStan = impossible. C'est un choix documenté, pas un oubli.

---

## C18/C19 — Comment CI et CD fonctionnent ensemble dans le projet

### Le flux complet

```
git push main
    │
    ├── GitHub Actions (CI) — déclenché immédiatement
    │       ├── ci_model.yml  → pytest test_model.py  (17 tests Prophet)
    │       ├── ci_app.yml    → syntax check + ruff lint Streamlit
    │       └── ci_data.yml   → pytest test_api.py    (19 tests API data)
    │
    └── Railway (CD) — déclenché en parallèle
            ├── détecte le push sur main
            ├── build du Dockerfile (app/Dockerfile)
            └── déploie l'application Streamlit en production
```

### CI — GitHub Actions (C18)

**3 workflows indépendants**, chacun déclenché sur push/PR vers `main` :

| Workflow | Fichier | Ce qu'il vérifie |
|---|---|---|
| CI Modèle | `ci_model.yml` | 17 tests Prophet (slugify, métriques, metrics.json) |
| CI App | `ci_app.yml` | Syntaxe Python + lint ruff sur les 8 pages Streamlit |
| CI Data | `ci_data.yml` | 19 tests API data (routes, filtres, pagination) |

La CI **ne déploie rien** — elle valide uniquement que le code est correct.

### CD — Railway (C19)

Railway est connecté au repo GitHub. À chaque push sur `main` :
1. Railway détecte le push automatiquement
2. Lit `app/Dockerfile` → build de l'image Python 3.12-slim
3. Lance `streamlit run app/main.py --server.port=8501`
4. L'application est accessible en production

**Ce que Railway NE fait PAS** : exécuter les tests. CI et CD sont deux systèmes séparés mais enchaînés par le même événement (git push).

### Différence CI vs CD

| | CI (GitHub Actions) | CD (Railway) |
|---|---|---|
| Déclencheur | push/PR | push sur main |
| But | valider le code | livrer l'application |
| Résultat | PASSED / FAILED | app déployée en production |
| Rollback | non applicable | Railway revient à la version précédente |

### Ce qui reste manuel

- Réentraînement Prophet (`python model/train.py`) — CmdStan incompatible CI
- Commit des `.pkl` après réentraînement
- Déploiement des APIs data et modèle (pas connectées à Railway dans la config actuelle)