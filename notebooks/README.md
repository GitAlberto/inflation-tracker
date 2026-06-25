# notebooks — Exploration et analyse (EDA)

Ce dossier attend les notebooks Jupyter d'exploration des données et du modèle.

## Fichiers à créer

| Fichier | Contenu | Semaine |
|---|---|---|
| `01_eda_insee.ipynb` | Analyse exploratoire des séries IPC INSEE | S2 |
| `02_eda_eurostat.ipynb` | Analyse exploratoire des données Eurostat | S2 |
| `03_model_exploration.ipynb` | Exploration Prophet : entraînement, prédiction, composantes | S4 |

## Rôle

Les notebooks servent à **explorer et comprendre** les données avant de coder les scripts.
Ils ne font pas partie du pipeline de production — ce sont des outils d'analyse.

## Preuve requise (C8)

`03_model_exploration.ipynb` est une preuve directe pour C8 :
- Visualisation des données d'entraînement
- Graphique prédiction vs réel
- Décomposition Prophet (tendance + saisonnalité + résidus)
- Discussion des choix d'hyperparamètres

## Conventions

- Utiliser des noms de cellules clairs
- Pas de credentials dans les notebooks
- Nettoyer les outputs avant commit (ou utiliser `.gitignore` sur les checkpoints)
