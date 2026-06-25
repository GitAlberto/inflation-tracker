# src/database — Schéma, import, RGPD (C4)

Ce dossier attend les scripts de création et gestion de la base PostgreSQL (Semaine 1-3, C4).

## Fichiers à créer

| Fichier | Rôle |
|---|---|
| `schema.sql` | MCD/MPD commenté + instructions `CREATE TABLE` |
| `import_data.py` | Script d'import des données nettoyées dans PostgreSQL |
| `rgpd_register.md` | Registre de traitement RGPD du projet |

## Tables PostgreSQL

```
ecb_hicp_raw     → données brutes ECB chargées directement
insee_ipc        → séries IPC INSEE par catégorie
openfoodfacts    → prix produits Open Food Facts
eurostat_bulk    → HICP Eurostat 27 pays
inflation_unified → table finale unifiée (source de vérité)
```

## Preuve requise (C4)

- Schéma BDD avec le MCD/MPD (diagramme ou SQL commenté)
- Capture `\dt` dans psql montrant les tables créées
- Registre RGPD complété dans `rgpd_register.md`
