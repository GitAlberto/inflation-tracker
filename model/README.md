# model — Modèle de prédiction IA (C8)

Ce dossier attend le modèle Prophet de prédiction de l'IPC (Semaine 4, C8).

## Fichiers à créer

| Fichier | Rôle |
|---|---|
| `train.py` | Entraînement du modèle Prophet par catégorie |
| `predict.py` | Génération de prédictions à partir d'un modèle chargé |
| `evaluate.py` | Calcul des métriques (MAE, RMSE, visualisation) |
| `inflation_model.pkl` | Modèle sérialisé (non versionné — voir `.gitignore`) |
| `metrics.json` | Métriques d'entraînement par catégorie (versionné) |

## Choix technique

**Prophet (Meta)** — retenu après benchmark (voir `docs/benchmark.md`) :
- Gestion native de la saisonnalité annuelle
- Interprétable (composantes : tendance + saisonnalité)
- Déployable sans GPU
- Intégration simple avec FastAPI (`joblib`)

## Hyperparamètres clés

- `yearly_seasonality=True` — capture les cycles annuels de l'inflation
- `changepoint_prior_scale=0.05` — régularisation (à justifier au jury)
- `weekly_seasonality=False` — données mensuelles, pas hebdomadaires

## Preuve requise (C8)

- Graphique prédiction vs réel (historique + forecast)
- Décomposition des composantes Prophet (tendance + saisonnalité)
- `metrics.json` avec MAE par catégorie
- Notebook d'exploration : `notebooks/03_model_exploration.ipynb`
