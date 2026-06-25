# src — Code source Python (Bloc 1)

Ce dossier contient tout le code Python du pipeline de données (C1 à C5).

## Structure

```
src/
├── collect/    → scripts de collecte des 5 sources (C1)
├── sql/        → requêtes SQL documentées (C2)
├── aggregate/  → nettoyage et agrégation (C3)
└── database/   → schéma, import, RGPD (C4)
```

## Ordre d'exécution

1. `collect/` — collecter les données brutes
2. `aggregate/` — nettoyer et agréger
3. `database/` — importer dans PostgreSQL
4. L'API data (`api/data/`) expose ensuite la base

## Compétences couvertes

C1 (collecte), C2 (SQL), C3 (agrégation), C4 (base de données)
