# api — APIs REST FastAPI

Ce dossier contient les deux APIs du projet.

## Structure

```
api/
├── data/   → API de mise à disposition des données IPC (C5)
└── model/  → API de prédiction du modèle Prophet (C9)
```

## Deux APIs distinctes

| API | Port | Rôle | Compétence |
|---|---|---|---|
| `api/data/` | 8001 | Expose les données PostgreSQL | C5 |
| `api/model/` | 8000 | Expose les prédictions du modèle | C9 |

## Technologie

FastAPI — documentation automatique sur `/docs` (Swagger UI).
Authentification par `X-API-Key` header.
