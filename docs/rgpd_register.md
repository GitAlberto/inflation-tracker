# Registre des traitements de données — inflation-tracker
**Compétence C4 — Modélisation et création de la base de données**
**Responsable du traitement** : Alberto Bongue
**Date de création** : 2026-06-29
**Mise à jour** : 2026-06-29

---

## Contexte

Le projet inflation-tracker collecte des données économiques publiques issues de
5 sources hétérogènes pour analyser et prédire l'évolution de l'inflation en France
et en Europe. Ce registre documente chaque traitement au regard du RGPD
(Règlement Général sur la Protection des Données — UE 2016/679).

**Conclusion générale** : aucune donnée à caractère personnel n'est collectée,
traitée ou stockée dans ce projet. Toutes les données sont des statistiques
économiques agrégées ou des informations publiques sur des produits commerciaux.

---

## Source 1 — API ECB (Banque Centrale Européenne)

| Champ | Valeur |
|---|---|
| Source | https://data-api.ecb.europa.eu |
| Licence | ECB Open Data (réutilisation libre) |
| Données collectées | HICP (Harmonised Index of Consumer Prices) — taux de variation annuel mensuel |
| Granularité | 6 pays × 12 catégories COICOP × ~30 ans |
| Table cible | `ecb_hicp_raw` |
| Données personnelles | **Aucune** — indices statistiques agrégés par pays et catégorie |
| Base légale RGPD | Sans objet (pas de données personnelles) |
| Rétention | Illimitée — données historiques publiques |
| Minimisation | Seules les colonnes utiles sont conservées (time_period, obs_value, ref_area, coicop, unit) |

---

## Source 2 — API INSEE BDM

| Champ | Valeur |
|---|---|
| Source | https://api.insee.fr/series/BDM/V1 |
| Licence | Licence Ouverte Etalab v2.0 |
| Données collectées | IPC France par catégorie COICOP, séries mensuelles |
| Granularité | Séries par identifiant INSEE (idbank), mensuel depuis ~2000 |
| Table cible | `insee_ipc` |
| Données personnelles | **Aucune** — indices officiels publiés par l'INSEE |
| Base légale RGPD | Sans objet (pas de données personnelles) |
| Rétention | Illimitée — données officielles de référence |
| Minimisation | Seuls les identifiants de séries pertinents sont interrogés |

---

## Source 3 — CSV data.gouv.fr

| Champ | Valeur |
|---|---|
| Source | https://www.data.gouv.fr |
| Licence | Licence Ouverte Etalab v2.0 |
| Données collectées | Séries longues IPC France depuis 1990, toutes catégories |
| Granularité | Mensuel, toutes catégories COICOP niveau 1 |
| Table cible | `datagouv_ipc` |
| Données personnelles | **Aucune** — fichiers statistiques officiels de l'INSEE publiés sur data.gouv.fr |
| Base légale RGPD | Sans objet (pas de données personnelles) |
| Rétention | Illimitée — données historiques officielles |
| Minimisation | Colonnes non pertinentes supprimées lors du nettoyage |

---

## Source 4 — Scraping Open Food Facts

| Champ | Valeur |
|---|---|
| Source | https://fr.openfoodfacts.org |
| Licence | Open Database Licence (ODbL) — scraping explicitement autorisé |
| Données collectées | Nom du produit, catégorie alimentaire, prix unitaire, URL produit |
| Granularité | Produit par produit, catégories alimentaires sélectionnées |
| Table cible | `openfoodfacts` |
| Données personnelles | **Aucune** — données de produits commerciaux publics (marques, prix publics) |
| Base légale RGPD | Sans objet (pas de données personnelles) |
| Rétention | Limitée à la date de collecte — pas de suivi historique par produit |
| Minimisation | Prix, catégorie et URL uniquement — aucune donnée sur les acheteurs |
| Note légale | Open Food Facts autorise explicitement le scraping de son API publique sous licence ODbL. Les données collectées ne contiennent aucune information relative à des personnes physiques. |

---

## Source 5 — Eurostat bulk + PySpark

| Champ | Valeur |
|---|---|
| Source | https://ec.europa.eu/eurostat |
| Licence | Creative Commons Attribution 4.0 (CC BY 4.0) |
| Données collectées | HICP 27 pays UE × 100+ catégories COICOP × 30 ans (dataset prc_hicp_manr) |
| Granularité | Mensuel, niveau pays |
| Table cible | `eurostat_bulk` |
| Données personnelles | **Aucune** — statistiques officielles agrégées au niveau national |
| Base légale RGPD | Sans objet (pas de données personnelles) |
| Rétention | Illimitée — données historiques officielles |
| Minimisation | Filtrage PySpark sur les colonnes utiles uniquement avant chargement PostgreSQL |

---

## Principes RGPD appliqués au projet

### Minimisation des données (Art. 5.1.c)
Seules les colonnes strictement nécessaires à l'analyse de l'inflation sont
conservées. Les métadonnées techniques des API (codes de version, identifiants
internes, champs administratifs) sont supprimées lors de l'étape Transform du
pipeline ETL.

### Limitation de la conservation (Art. 5.1.e)
Les données brutes (`data/raw/`) et nettoyées (`data/processed/`) sont écrasées
à chaque nouvelle collecte — un seul exemplaire est conservé par source.
Les données historiques en base PostgreSQL sont conservées indéfiniment car elles
constituent la valeur analytique du projet.

### Intégrité et confidentialité (Art. 5.1.f)
- Base PostgreSQL accessible uniquement en local via Docker (port 5437)
- Credentials stockés dans `.env` non versionné (`.gitignore`)
- Aucune exposition publique de la base de données

### Droits des personnes concernées
Sans objet — aucune donnée à caractère personnel n'est traitée.
Ce projet ne relève pas des obligations liées aux droits d'accès, de rectification
ou d'effacement prévus aux Art. 15 à 22 du RGPD.

---

## Tableau récapitulatif

| Source | Table | Données perso | Licence | Scraping autorisé |
|---|---|---|---|---|
| ECB API | ecb_hicp_raw | Non | ECB Open Data | Oui (API publique) |
| INSEE BDM | insee_ipc | Non | Etalab v2.0 | Oui (API publique) |
| data.gouv.fr | datagouv_ipc | Non | Etalab v2.0 | Oui (open data) |
| Open Food Facts | openfoodfacts | Non | ODbL | Oui (explicitement) |
| Eurostat bulk | eurostat_bulk | Non | CC BY 4.0 | Oui (bulk download) |

**Risque RGPD global : nul** — projet 100% données publiques sans données personnelles.
