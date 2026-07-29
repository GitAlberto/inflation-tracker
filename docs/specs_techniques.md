# Spécifications Techniques — Inflation Tracker (C15)

**Projet :** Inflation Tracker France — B3 RNCP Développeur IA  
**Auteur :** Alberto Bongue  
**Date :** 2026-07

---

## Architecture générale

```
5 sources publiques
    ↓ ETL (src/collect/)
Tables sources PostgreSQL
    ↓ Agrégation normalisée (src/aggregate/)
inflation_unified
    ↓                        ↓
API data (port 8001)    Modèle Prophet (model/)
    ↓                        ↓
             API modèle (port 8002)
                    ↓
          Application Streamlit (app/)
                    ↓
          Monitoring Prometheus + Grafana
```

---

## Décision technique #1 — Normalisation des données (C3)

### Problème : Garbage In, Garbage Out

Audit réalisé lors de l'intégration des sources : la colonne `valeur` de
`inflation_unified` contenait des grandeurs **incomparables** selon la source.

| Source | Valeur brute | Unité | Problème |
|---|---|---|---|
| INSEE | `119.17` | Indice base 100=2015 | ✅ Référence |
| DATAGOUV | `119.17` **et** `2.4` | Mélange indices + taux % | ❌ Aucun filtre sur UNIT_MEASURE |
| ECB | `2.4` | Taux ANR (Annual Rate) % | ❌ Pas un indice |
| EUROSTAT | `3.2` | Taux RCH_A % | ❌ Pas un indice |

De même, la colonne `categorie` avait 4 formats différents selon la source
(`"01 - Alimentation..."` vs `"01"` vs `"CP01"` vs `"010000"`).

### Solution appliquée

**Règle unique :** `inflation_unified.valeur` = **indice IPC base 100 = 2015** pour toutes les sources.

#### DATAGOUV (`collect_csv.py`)
```python
df = df[df["UNIT_MEASURE"] == "IX"]       # indices seulement, pas les taux %
df = df[df["IND_TYPE"]     == "IX"]       # valeur d'indice, pas variation YoY
df = df[df["GEO"]          == "F"]        # France nationale, pas les DOM/COM
df = df[df["PRODUCT_GROUP"] == "_Z"]      # agrégat COICOP pur, pas sous-groupes
# Note : BASE_PER = "2025" depuis le rebasage INSEE 2025 — voir ci-dessous
```

#### ECB (`load_ecb_to_db.py`)
```
# Avant : ICP/M.{PAYS}.N.{COICOP}.4.ANR  (taux de variation annuel %)
# Après : ICP/M.{PAYS}.N.{COICOP}.4.INX  (indice HICP base 2015=100)
```

#### EUROSTAT (`collect_eurostat_spark.py`)
```
# Avant : dataset prc_hicp_manr, UNIT_FILTRE = "RCH_A"  (taux %)
# Après : dataset prc_hicp_midx, UNIT_FILTRE = "I15"    (indice base 2015=100)
# Attention : prc_hicp_midx utilise "I15", pas "INX_A_AVG" (moyennes annuelles)
```

### Cas particulier : DATAGOUV rebasé 2025

En 2025, l'INSEE a rebasé toutes ses séries de 2015 vers 2025.
Le fichier DATAGOUV ne contient plus aucune donnée `BASE_PER = "2015"`.

**Conséquence :** DATAGOUV (base 2025) et INSEE/ECB/EUROSTAT (base 2015) ne sont
pas comparables en valeur absolue dans `inflation_unified`. Les tendances et
variations relatives restent valides.

**Décision :** conserver DATAGOUV malgré l'incompatibilité — c'est la seule source
couvrant la France depuis 1996. Toute interface utilisateur doit indiquer la base
de référence de la source affichée.

#### Catégories (`aggregate_clean.py`)
Chaque SQL extrait le code COICOP à 2 chiffres et le normalise via un CTE de 13 libellés :
`"XX - Label"` (ex: `"01 - Alimentation et boissons non alcoolisées"`).
Seul le niveau 1 (00–12) est conservé — les sous-catégories sont exclues.

### Impact sur le modèle Prophet

Prophet est entraîné sur `source='INSEE'` (base 100=2015). Ses prédictions sont donc
dans la même unité que toutes les sources après normalisation → overlay historique
cohérent dans l'application, métriques comparables entre sources.

---

## Décision technique #2 — API REST (C5/C9)

Deux APIs FastAPI séparées :
- **Port 8001** — API data : expose `inflation_unified` (3.68M lignes) + prix alimentaires
- **Port 8002** — API modèle : expose les 13 modèles Prophet + métriques

Séparation justifiée : cycle de vie différent (données vs modèle), scalabilité indépendante,
monitoring séparé (métriques Prometheus distinctes par API).

---

## Décision technique #3 — Prophet vs LSTM vs ARIMA (C7/C8)

Voir `veille_C6_final.pdf` — Section 3 (page 10) : tableau comparatif Prophet / ARIMA / LSTM
sur 10 critères ; Sections 5.1-5.3 (pages 14-16) : justification du choix Prophet.
Résumé : Prophet retenu pour sa gestion native de la saisonnalité mensuelle,
sa robustesse aux valeurs manquantes, et sa lisibilité des composantes
(tendance + saisonnalité) — critique pour un projet d'analyse économique.

---

## Décision technique #4 — Split d'évaluation temporel strict

Train : Jan 2020 → Dec 2024 (60 mois)  
Eval  : Jan 2025 → Dec 2025 (12 mois, held-out)

Justification : un split temporel strict (pas de shuffle) est impératif pour
les séries temporelles — mélanger des observations futures dans le train
introduit du data leakage et surestime les performances.

---

## Décision technique #5 — Exclusion catégorie 12 du modèle Prophet (C8)

**Catégorie concernée :** `12 - Biens et services divers` (soins personnels,
protection sociale, assurances, services financiers divers).

**Cause technique :** `model/train.py` charge dynamiquement toutes les catégories
présentes dans `inflation_unified` pour `source='INSEE'`. La série INSEE BDM
correspondant à la catégorie 12 n'a pas été intégrée dans `collect_insee_api.py`
— la donnée est absente de la base. Aucun `.pkl` ni entrée dans `metrics.json`
ne peuvent donc être générés pour cette catégorie.

**Justification métier :** la catégorie 12 regroupe des prix structurellement
hétérogènes (coiffure, frais bancaires, assurances) dont les mécanismes de
formation diffèrent fondamentalement des autres catégories. La saisonnalité
annuelle capturée par Prophet (cycles alimentaires, énergétiques) n'est pas
pertinente sur cette série — son exclusion est une décision de qualité modèle,
pas seulement une contrainte de données.

**Périmètre du modèle :** 12 catégories entraînées (COICOP 00–11), toutes avec
`n_train=60` et `n_eval=12`. MAE moyenne : 1.43 pts IPC.

---

## Décision technique #6 — Réentraînement manuel (C13)

Le réentraînement des modèles Prophet n'est pas automatisé en CI/CD.

**Raison :** l'entraînement nécessite CmdStan (compilateur C++ ~500 Mo) et
~15 minutes de calcul pour les 12 catégories. Ce coût est incompatible avec
un pipeline CI déclenché à chaque push. En CI, les tests nécessitant les `.pkl`
sont automatiquement skippés via le marqueur `@pytest.mark.skipif(CI=true)`.

**Procédure de réentraînement :**
```bash
python model/train.py          # génère les 12 .pkl + metrics.json
git add model/metrics.json     # versionné — trace les performances
# les .pkl sont dans .gitignore (binaires lourds, régénérables)
```

**Déclencheur :** à chaque mise à jour des données INSEE dans `inflation_unified`
(mensuelle) ou à chaque changement d'hyperparamètres Prophet.

---

## Limites connues

| Limite | Impact | Décision |
|---|---|---|
| JAVA_HOME hardcodé dans `collect_eurostat_spark.py` | PySpark échoue si Java n'est pas dans le PATH de la session courante | Documenté — fermer/rouvrir le terminal après installation Java suffit |
| OpenFoodFacts collecté mais non intégré en UI | Les prix alimentaires réels ne sont pas visualisés dans Streamlit | Volume insuffisant et couverture géographique partielle — backlog v2 |
| DATAGOUV rebasé 2025 | Valeurs absolues incomparables avec INSEE/ECB/Eurostat (base 2015) | Tendances relatives valides — note affichée dans specs_fonctionnelles |
| Catégorie 12 exclue du modèle | 12 catégories au lieu de 13 | Voir Décision technique #5 |

---

## Stack technique

| Composant | Technologie | Justification |
|---|---|---|
| Base de données | PostgreSQL 15 (Docker) | ACID, NUMERIC(10,4) sans erreur float |
| API | FastAPI + SQLAlchemy | Async, Pydantic validation, auto-docs |
| Modèle | Prophet (Meta) | Saisonnalité IPC mensuelle, robuste aux gaps |
| Application | Streamlit | Prototypage IA rapide, pas de JS requis |
| Monitoring | Prometheus + Grafana | Standard industrie, alertes MAE |
| CI/CD | GitHub Actions | Tests automatisés, skip intégration en CI |
| Big Data | PySpark (Eurostat 3.5M lignes) | Preuve traitement distribué (C2) |
