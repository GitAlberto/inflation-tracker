# src/collect — Scripts de collecte (C1)

Ce dossier attend les 5 scripts de collecte des sources de données (Semaine 1-2, C1).

## Fichiers à créer

| Fichier | Source | Technologie |
|---|---|---|
| `collect_insee_api.py` | API INSEE BDM | `requests` + clé API |
| `collect_csv.py` | data.gouv.fr | `pandas.read_csv()` |
| `scrape_openfoodfacts.py` | Open Food Facts | `requests` + `BeautifulSoup` |
| `load_ecb_to_db.py` | API ECB | `requests` + `SQLAlchemy` |
| `collect_eurostat_spark.py` | Eurostat bulk | `PySpark` |

## Preuve requise (C1)

Pour chaque script :
- Log d'exécution montrant les données collectées
- Fichier brut produit dans `data/raw/`
- Screenshot du terminal

## Conventions

- Chaque script est autonome et exécutable seul
- Variables d'environnement dans `.env` (jamais de credentials dans le code)
- Timeout explicite sur chaque appel HTTP
