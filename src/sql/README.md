# src/sql — Requêtes SQL documentées (C2)

Ce dossier attend les requêtes SQL d'extraction et d'analyse (Semaine 3, C2).

## Fichiers à créer

| Fichier | Contenu |
|---|---|
| `queries_extraction.sql` | Requêtes de sélection et jointure entre les tables sources |
| `queries_analyse.sql` | Requêtes analytiques : évolutions, moyennes, comparaisons |

## Exigence C2

Chaque requête doit être **documentée** :
- Commentaire expliquant le pourquoi de la sélection
- Justification des filtres et jointures
- Résultat attendu (exemple ou description)

## Requêtes minimales

- Extraction IPC alimentation France depuis ECB
- Jointure IPC INSEE + Eurostat par catégorie
- Évolution annuelle moyenne par catégorie
- Top 5 catégories avec la plus forte hausse sur 5 ans
- Comparaison France vs zone euro (HICP)
