# data/processed — Données nettoyées

Ce dossier attend les données intermédiaires après nettoyage et normalisation (Semaine 3, C3).

## Contenu attendu

- `unified_ipc.parquet` ou `unified_ipc.csv` — dataset final agrégé toutes sources
- Un fichier par source nettoyée si nécessaire : `insee_clean.csv`, `ecb_clean.csv`, etc.

## Ce que le nettoyage fait

- Suppression des doublons
- Homogénéisation des dates → ISO 8601
- Normalisation des catégories → nomenclature COICOP
- Suppression des valeurs nulles ou aberrantes (IPC < 0 ou > 200)
- Conversion des unités → indice base 100 = 2015

## Script source

`src/aggregate/aggregate_clean.py`

## Destination finale

Ces données sont ensuite importées dans **PostgreSQL** (`inflation_unified`).
Le contenu de ce dossier n'est pas versionné (`.gitignore`).
