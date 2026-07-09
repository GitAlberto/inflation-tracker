-- =============================================================================
-- C2 — Requêtes SQL d'extraction — inflation-tracker
-- =============================================================================
-- Ces requêtes extraient les données brutes depuis les tables sources et la
-- table unifiée inflation_unified. Elles couvrent les cas d'usage principaux :
-- filtrage par pays, par source, par catégorie et par période.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Q1 — Volume de données par table source
-- Résultat attendu : 6 lignes, une par table
-- -----------------------------------------------------------------------------
SELECT 'ecb_hicp_raw'    AS table_source, COUNT(*) AS nb_lignes FROM ecb_hicp_raw
UNION ALL
SELECT 'insee_ipc',                        COUNT(*) FROM insee_ipc
UNION ALL
SELECT 'datagouv_ipc',                     COUNT(*) FROM datagouv_ipc
UNION ALL
SELECT 'openfoodfacts',                    COUNT(*) FROM openfoodfacts
UNION ALL
SELECT 'eurostat_bulk',                    COUNT(*) FROM eurostat_bulk
UNION ALL
SELECT 'inflation_unified',                COUNT(*) FROM inflation_unified
ORDER BY nb_lignes DESC;


-- -----------------------------------------------------------------------------
-- Q2 — IPC France toutes sources — catégorie "ensemble" — 2024
-- Comparaison des valeurs INSEE vs DATAGOUV sur la même période
-- -----------------------------------------------------------------------------
SELECT
    date_obs,
    source,
    categorie,
    valeur
FROM inflation_unified
WHERE pays        = 'FR'
  AND date_obs BETWEEN '2024-01-01' AND '2024-12-31'
  AND (
      (source = 'INSEE'    AND categorie ILIKE '%ensemble%')
   OR (source = 'DATAGOUV' AND categorie ILIKE '%ensemble%')
  )
ORDER BY date_obs, source;


-- -----------------------------------------------------------------------------
-- Q3 — Données Eurostat pour la France — toutes catégories — janvier 2024
-- Permet de voir la granularité des 441 catégories COICOP disponibles
-- -----------------------------------------------------------------------------
SELECT
    pays,
    coicop,
    date_obs,
    valeur,
    unite
FROM eurostat_bulk
WHERE pays     = 'FR'
  AND date_obs = '2024-01-01'
ORDER BY coicop
LIMIT 20;


-- -----------------------------------------------------------------------------
-- Q4 — Séries temporelles INSEE — catégorie alimentation — 2020 à 2025
-- 13 idbanks disponibles, ici on filtre sur la catégorie alimentation
-- -----------------------------------------------------------------------------
SELECT
    date_obs,
    categorie,
    valeur,
    idbank
FROM insee_ipc
WHERE categorie ILIKE '%alimentation%'
ORDER BY date_obs;


-- -----------------------------------------------------------------------------
-- Q5 — Prix alimentaires Open Food Facts — tomates — toutes variétés
-- Permet de comparer les prix terrain entre catégories de tomates
-- -----------------------------------------------------------------------------
SELECT
    produit,
    categorie,
    prix_unitaire,
    date_collecte
FROM openfoodfacts
WHERE categorie ILIKE '%tomat%'
ORDER BY categorie, prix_unitaire;


-- -----------------------------------------------------------------------------
-- Q6 — Données ECB — HICP France vs Allemagne — catégorie alimentaire (010000)
-- Comparaison directe des taux d'inflation alimentaire entre les deux pays
-- -----------------------------------------------------------------------------
SELECT
    time_period,
    ref_area    AS pays,
    coicop,
    obs_value   AS taux_inflation_pct
FROM ecb_hicp_raw
WHERE ref_area IN ('FR', 'DE')
  AND coicop    = '010000'
ORDER BY time_period, ref_area;


-- -----------------------------------------------------------------------------
-- Q7 — Extraction complète pour une période et un pays depuis inflation_unified
-- Requête type pour alimenter un graphique ou un export
-- -----------------------------------------------------------------------------
SELECT
    date_obs,
    pays,
    categorie,
    valeur,
    source
FROM inflation_unified
WHERE pays     = 'DE'
  AND source   = 'EUROSTAT'
  AND date_obs BETWEEN '2023-01-01' AND '2024-12-31'
ORDER BY date_obs, categorie
LIMIT 50;


-- -----------------------------------------------------------------------------
-- Q8 — Couverture temporelle par source dans inflation_unified
-- Montre la plage de dates disponible pour chaque source
-- -----------------------------------------------------------------------------
SELECT
    source,
    COUNT(*)         AS nb_lignes,
    MIN(date_obs)    AS date_debut,
    MAX(date_obs)    AS date_fin,
    COUNT(DISTINCT pays)      AS nb_pays,
    COUNT(DISTINCT categorie) AS nb_categories
FROM inflation_unified
GROUP BY source
ORDER BY source;
