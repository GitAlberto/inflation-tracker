# src/aggregate — Agrégation et nettoyage (C3)

Script unique `aggregate_clean.py` — consolide 4 sources en `inflation_unified`.

---

## Principe : Garbage In, Garbage Out

> Si les données qui entrent dans le modèle ne sont pas homogènes, toute analyse
> et toute prédiction sont faussées — indépendamment de la qualité du modèle.

Problème identifié lors de l'audit des sources : chaque source stockait ses données
dans un format différent, rendant `inflation_unified` incohérente sur deux axes critiques.

---

## Divergences identifiées et corrigées

### 1. Unité de la colonne `valeur` — CRITIQUE

Le schéma déclare `-- Base 100 = 2015` pour la colonne `valeur`, mais sans correction
les sources versaient des grandeurs incomparables :

| Source | Valeur brute | Unité réelle |
|---|---|---|
| INSEE | `119.17` | Indice IPC base 100 = 2015 ✅ |
| DATAGOUV | `119.17` **et** `2.4` | **Mélange** : indices + taux % (aucun filtre) ❌ |
| ECB | `2.4` | Taux de variation annuel ANR en % ❌ |
| EUROSTAT | `3.2` | Taux de variation annuel RCH_A en % ❌ |

Comparer un indice de 119 avec un taux de 2.4% dans la même colonne est
un non-sens statistique qui invalide toute analyse comparative et toute prédiction.

**Correction appliquée :**

- **DATAGOUV** (`collect_csv.py`) — ajout filtre `UNIT_MEASURE = "IX"` (indices uniquement)
- **ECB** (`load_ecb_to_db.py`) — changement `ANR` → `INX` dans l'URL API ECB
- **EUROSTAT** (`collect_eurostat_spark.py`) — changement dataset `prc_hicp_manr` → `prc_hicp_midx`,
  filtre `RCH_A` → `I15` (le dataset `prc_hicp_midx` utilise `I15`, pas `INX_A_AVG`)

### 2. Doublons DATAGOUV (GEO, PRODUCT_GROUP, IND_TYPE) — CRITIQUE

Sans filtrage complémentaire, la même catégorie COICOP pour le même mois générait
plusieurs lignes dans DATAGOUV, selon 3 dimensions cachées :

| Dimension | Valeur souhaitée | Autres valeurs parasites |
|---|---|---|
| `GEO` | `"F"` (France nationale) | `"971"` Guadeloupe, `"973"` Guyane, etc. |
| `PRODUCT_GROUP` | `"_Z"` (agrégat pur COICOP) | `"4005"`, `"4037"` (sous-groupes produit) |
| `IND_TYPE` | `"IX"` (valeur d'indice) | `"YOY"` (variation YoY en points d'indice) |

La confusion `IND_TYPE = "YOY"` avec `UNIT_MEASURE = "IX"` générait des valeurs
comme `0.40` (variation) mélangées aux indices comme `62.81` — une incohérence
invisible sans inspection des données brutes.

**Correction appliquée :**

- **DATAGOUV** (`collect_csv.py`) — 3 filtres supplémentaires :
  `IND_TYPE = "IX"`, `GEO = "F"`, `PRODUCT_GROUP = "_Z"`

### 3. Base de référence de l'indice — DOCUMENTÉE (non bloquante)

En 2025, l'INSEE a rebasé l'ensemble de ses séries de 2015 vers 2025.
Le fichier DATAGOUV ne contient plus aucune donnée en `BASE_PER = "2015"`.

| Source | Base actuelle | Impact |
|---|---|---|
| INSEE API | 2015=100 | Référence modèle Prophet |
| DATAGOUV CSV | 2025=100 | Incompatible en valeur absolue |
| ECB API | 2015=100 | Compatible |
| EUROSTAT | 2015=100 | Compatible |

**Décision prise :** les données DATAGOUV base 2025 sont conservées (elles couvrent
1996–2026, aucune autre source n'a cette profondeur historique pour la France).
L'incompatibilité d'échelle est documentée — les tendances et variations relatives
restent valides, seule la comparaison d'une valeur absolue DATAGOUV avec une
valeur INSEE/ECB/EUROSTAT est à éviter.

### 3. Nomenclature `categorie` — SIGNIFICATIF

Chaque source utilisait son propre format de code de catégorie :

| Source | Format brut | Exemple |
|---|---|---|
| INSEE | Libellé complet | `"01 - Alimentation et boissons non alcoolisées"` |
| DATAGOUV | Code COICOP 2018 brut, hiérarchie complète | `"01"`, `"01.1"`, `"01.1.1.1"` |
| EUROSTAT | Préfixe CP + code, hiérarchie | `"CP01"`, `"CP0111"` |
| ECB | Code 6 chiffres zero-padded | `"010000"`, `"000000"` |

**Correction appliquée dans `aggregate_clean.py` :**

- Chaque SQL extrait le code COICOP à 2 chiffres propre à son format source
- Filtre sur le niveau 1 uniquement (pas les sous-catégories)
- JOIN avec un CTE `coicop_ref` de 13 libellés canoniques
- Résultat uniforme : `"01 - Alimentation et boissons non alcoolisées"` pour toutes les sources

---

## État après corrections

| Source | `valeur` | `categorie` | `pays` | `date_obs` |
|---|---|---|---|---|
| INSEE | Indice base 100=2015 ✅ | `"XX - Label"` ✅ | `"FR"` ✅ | DATE ✅ |
| DATAGOUV | Indice base 100=**2025** ⚠️ | `"XX - Label"` ✅ | `"FR"` ✅ | DATE ✅ |
| ECB | Indice base 100=2015 ✅ | `"XX - Label"` ✅ | ISO code ✅ | DATE ✅ |
| EUROSTAT | Indice base 100=2015 ✅ | `"XX - Label"` ✅ | ISO code ✅ | DATE ✅ |

⚠️ DATAGOUV base 2025 : incompatible en valeur absolue avec les autres sources.
L'évolution relative (direction, saisonnalité, tendance) reste exploitable.

---

## Cohérence avec le modèle Prophet (C8)

Le modèle Prophet est entraîné exclusivement sur `source='INSEE'`
(données base 100 = 2015, catégories niveau 1).

Ses prédictions produisent des valeurs dans la même échelle (ex: 121.5 pour début 2026).
Après normalisation, toutes les sources étant en base 100 = 2015, l'overlay historique
dans l'application Streamlit (page Prédictions) est cohérent :
une valeur historique DATAGOUV de 119 et une prédiction Prophet de 121
s'interprètent dans le même référentiel.

---

## Ordre d'exécution

```bash
# Étape 1 — Re-collecter les sources corrigées
python src/collect/collect_csv.py            # DATAGOUV : filtre IX + base 2015
python src/collect/load_ecb_to_db.py         # ECB : INX au lieu de ANR
python src/collect/collect_eurostat_spark.py # EUROSTAT : INX_A_AVG au lieu de RCH_A

# Étape 2 — INSEE n'a pas besoin d'être relancé (déjà correct)

# Étape 3 — Ré-agréger avec normalisation catégories
python src/aggregate/aggregate_clean.py
```

---

## Résultat final `inflation_unified`

Après pipeline complet (corrigé) :

| Source | Lignes | Depuis | Jusqu'à | Note |
|---|---|---|---|---|
| DATAGOUV | ~3 600* | 1996-01 | 2026-06 | Base 2025 ⚠️ |
| ECB | 28 080 | 1996-01 | 2025-12 | Base 2015 ✅ |
| EUROSTAT | ~27 000** | 1997-01 | 2025-12 | Base 2015 ✅ |
| INSEE | 864 | 2020-01 | 2025-12 | Base 2015 ✅ |

*DATAGOUV : après filtres IND_TYPE='IX', GEO='F', PRODUCT_GROUP='_Z' → 13 catégories × ~27 ans × 12 mois  
**EUROSTAT : après correction UNIT_FILTRE `RCH_A` → `I15` (run à relancer)
