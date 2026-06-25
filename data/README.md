# data — Données du projet

Ce dossier contient toutes les données du projet, organisées en deux niveaux.

## Structure

```
data/
├── raw/        → données brutes telles que collectées depuis les sources
└── processed/  → données nettoyées et normalisées, prêtes pour PostgreSQL
```

## Règle absolue

Les données brutes (`raw/`) ne sont **pas versionnées** (`.gitignore`).
Seule la structure (`.gitkeep` + `README.md`) est committée.

Les données réelles vivent localement ou dans un stockage externe.
