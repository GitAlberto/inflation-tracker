# data/raw — Données brutes

Ce dossier attend les données brutes collectées depuis les 5 sources (Semaine 1-2, C1).

## Sources

| Dossier | Source | Technologie | Format |
|---|---|---|---|
| `insee_api/` | API INSEE BDM | REST + clé API | JSON |
| `csv_datagouv/` | data.gouv.fr | CSV direct download | CSV |
| `scraping_openfoodfacts/` | Open Food Facts | BeautifulSoup | JSON/CSV |
| `bdd_ecb/` | API ECB | REST | CSV |
| `bigdata_eurostat/` | Eurostat bulk | PySpark | CSV compressé |

## Non versionné

Ces fichiers ne sont pas commités (voir `.gitignore`).
Seule la structure de dossiers est versionnée via `.gitkeep`.
