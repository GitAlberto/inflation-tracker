# api/data — API Data REST (C5)

Ce dossier attend l'API FastAPI de mise à disposition des données IPC (Semaine 3, C5).

## Fichiers à créer

| Fichier | Rôle |
|---|---|
| `main.py` | Application FastAPI avec les endpoints data |
| `schemas.py` | Modèles Pydantic pour les requêtes et réponses |
| `auth.py` | Vérification de la clé API (`X-API-Key`) |

## Endpoints attendus (minimum 5)

| Méthode | Route | Description |
|---|---|---|
| GET | `/ipc/{categorie}` | Valeurs IPC pour une catégorie et une période |
| GET | `/ipc/categories` | Liste toutes les catégories disponibles |
| GET | `/ipc/evolution/{annee}` | Évolution annuelle moyenne par catégorie |
| GET | `/ipc/compare` | Comparaison France vs zone euro |
| GET | `/health` | Statut de l'API |

## Preuve requise (C5)

- Capture Swagger UI (`/docs`)
- Exemple de requête + réponse JSON
- Test des codes HTTP 200, 401, 422

## Lancement

```bash
uvicorn api.data.main:app --reload --port 8001
```
