# api/model — API Modèle REST (C9)

Ce dossier attend l'API FastAPI qui expose les prédictions du modèle Prophet (Semaine 5, C9).

## Fichiers à créer

| Fichier | Rôle |
|---|---|
| `main.py` | Application FastAPI avec l'endpoint `/predict` + métriques Prometheus |
| `schemas.py` | Modèles Pydantic : `PredictionRequest`, `PredictionResponse` |
| `auth.py` | Vérification de la clé API (`X-API-Key`) |

## Endpoints attendus

| Méthode | Route | Description |
|---|---|---|
| POST | `/predict` | Prédiction IPC pour une catégorie sur N mois |
| GET | `/metrics` | Métriques Prometheus (scrapées par Prometheus) |
| GET | `/health` | Statut de l'API et version du modèle |
| GET | `/docs` | Swagger UI automatique |

## Format de l'endpoint `/predict`

```json
// Requête
{"categorie": "alimentation", "periodes": 6}

// Réponse
{
  "predictions": [{"ds": "2026-07-01", "yhat": 135.2, "yhat_lower": 133.1, "yhat_upper": 137.3}],
  "mae": 0.42,
  "model_version": "1.0.0"
}
```

## Preuve requise (C9)

- Capture Swagger UI (`/docs`)
- Exemple de requête `/predict` + réponse
- Métriques Prometheus visibles sur `/metrics`

## Lancement

```bash
uvicorn api.model.main:app --reload --port 8000
```
