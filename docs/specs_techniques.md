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

Voir `docs/benchmark.md`. Résumé : Prophet retenu pour sa gestion native de la
saisonnalité mensuelle, sa robustesse aux valeurs manquantes, et sa lisibilité
des composantes (tendance + saisonnalité) — critique pour un projet d'analyse économique.

---

## Décision technique #4 — Split d'évaluation temporel strict

Train : Jan 2020 → Dec 2024 (60 mois)  
Eval  : Jan 2025 → Dec 2025 (12 mois, held-out)

Justification : un split temporel strict (pas de shuffle) est impératif pour
les séries temporelles — mélanger des observations futures dans le train
introduit du data leakage et surestime les performances.

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
