# inflation-tracker

Système complet de collecte, stockage, analyse et prédiction de l'inflation en France et en zone euro.

## Concept

Le kebab coûtait 3,50€ en 2019. Il en coûte 7€ en 2026.
Ce projet agrège les données publiques (INSEE, BCE, Eurostat) pour rendre l'inflation lisible et prédire son évolution par catégorie de produit.

## Architecture

```
Sources (5) → Pipeline Python → PostgreSQL → API FastAPI → Modèle Prophet → Streamlit
```

## Blocs

- **Bloc 1** — Collecte, stockage, API data (C1 à C5)
- **Bloc 2** — Modèle IA, API modèle, MLOps (C6 à C13)
- **Bloc 3** — Application Streamlit, CI/CD, monitoring (C14 à C21)

## Lancement rapide

> À remplir en S3 quand Docker Compose sera configuré.

```bash
docker-compose up -d
pip install -r requirements.txt
```

## Planning

8 semaines — 25 juin → 27 août 2026. Voir `ROADMAP_INFLATION_COMPLET.md`.
