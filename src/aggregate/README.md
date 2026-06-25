# src/aggregate — Agrégation et nettoyage (C3)

Ce dossier attend le script d'agrégation qui unifie les 5 sources (Semaine 3, C3).

## Fichier à créer

| Fichier | Rôle |
|---|---|
| `aggregate_clean.py` | Charge, nettoie, normalise et fusionne les 5 sources en un dataset unique |

## Transformations attendues

1. Suppression des doublons (même date + catégorie + source)
2. Homogénéisation des dates → ISO 8601 (`YYYY-MM-DD`)
3. Normalisation des catégories → nomenclature COICOP
4. Suppression des valeurs aberrantes (IPC < 0 ou > 200)
5. Conversion des unités → indice base 100 = 2015
6. Chargement dans la table `inflation_unified` de PostgreSQL

## Preuve requise (C3)

- Tableau avant/après nettoyage (nombre de lignes, nulls, doublons)
- Volume final chargé en base
- Screenshot du terminal d'exécution
