-- =============================================================================
-- C2 — Requêtes SQL analytiques — inflation-tracker
-- =============================================================================
-- Ces requêtes produisent des indicateurs statistiques et des analyses
-- comparatives à partir de inflation_unified. Elles sont conçues pour
-- répondre à des questions métier : quelle catégorie a le plus augmenté ?
-- quelle différence entre France et Allemagne ? quand l'inflation a-t-elle
-- culminé ?
-- =============================================================================


-- -----------------------------------------------------------------------------
-- A1 — Inflation moyenne annuelle par pays (EUROSTAT) — 2020 à 2024
-- Agrégation : moyenne de toutes les catégories COICOP par pays et par an
-- -----------------------------------------------------------------------------
SELECT
    pays,
    EXTRACT(YEAR FROM date_obs)::INT    AS annee,
    ROUND(AVG(valeur), 2)               AS inflation_moy_pct,
    COUNT(DISTINCT categorie)           AS nb_categories
FROM inflation_unified
WHERE source   = 'EUROSTAT'
  AND date_obs BETWEEN '2020-01-01' AND '2024-12-31'
GROUP BY pays, annee
ORDER BY pays, annee;


-- -----------------------------------------------------------------------------
-- A2 — Pic d'inflation : année et valeur maximale par pays (EUROSTAT)
-- Identifie l'année où l'inflation a culminé dans chaque pays
-- -----------------------------------------------------------------------------
SELECT
    pays,
    EXTRACT(YEAR FROM date_obs)::INT AS annee_pic,
    ROUND(MAX(valeur), 2)            AS inflation_max_pct
FROM inflation_unified
WHERE source = 'EUROSTAT'
GROUP BY pays, EXTRACT(YEAR FROM date_obs)
HAVING MAX(valeur) = (
    SELECT MAX(valeur)
    FROM inflation_unified i2
    WHERE i2.pays = inflation_unified.pays
      AND i2.source = 'EUROSTAT'
)
ORDER BY inflation_max_pct DESC;


-- -----------------------------------------------------------------------------
-- A3 — Top 10 catégories COICOP les plus inflationnistes en France (EUROSTAT)
-- Classement sur la moyenne 2022-2023 (période de forte inflation)
-- -----------------------------------------------------------------------------
SELECT
    categorie,
    ROUND(AVG(valeur), 2)   AS inflation_moy_pct,
    ROUND(MAX(valeur), 2)   AS pic_pct,
    COUNT(*)                AS nb_observations
FROM inflation_unified
WHERE pays     = 'FR'
  AND source   = 'EUROSTAT'
  AND date_obs BETWEEN '2022-01-01' AND '2023-12-31'
GROUP BY categorie
ORDER BY inflation_moy_pct DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- A4 — Comparaison France / Allemagne / Zone Euro (ECB) — 2020 à 2025
-- Évolution mensuelle côte à côte pour les 3 zones économiques clés
-- -----------------------------------------------------------------------------
SELECT
    date_obs,
    MAX(CASE WHEN pays = 'FR' THEN valeur END) AS france,
    MAX(CASE WHEN pays = 'DE' THEN valeur END) AS allemagne,
    MAX(CASE WHEN pays = 'U2' THEN valeur END) AS zone_euro
FROM inflation_unified
WHERE source   = 'ECB'
  AND pays     IN ('FR', 'DE', 'U2')
  AND categorie = '000000'
  AND date_obs BETWEEN '2020-01-01' AND '2025-12-31'
GROUP BY date_obs
ORDER BY date_obs;


-- -----------------------------------------------------------------------------
-- A5 — Volatilité de l'inflation par pays (écart-type)
-- Les pays avec le plus grand écart-type ont eu l'inflation la plus instable
-- -----------------------------------------------------------------------------
SELECT
    pays,
    ROUND(AVG(valeur), 2)    AS inflation_moy,
    ROUND(STDDEV(valeur), 2) AS ecart_type,
    ROUND(MIN(valeur), 2)    AS min_pct,
    ROUND(MAX(valeur), 2)    AS max_pct
FROM inflation_unified
WHERE source   = 'EUROSTAT'
  AND date_obs BETWEEN '2020-01-01' AND '2024-12-31'
GROUP BY pays
ORDER BY ecart_type DESC
LIMIT 15;


-- -----------------------------------------------------------------------------
-- A6 — Évolution IPC France base 2015 — INSEE — toutes catégories — 2020-2025
-- Fenêtre glissante 12 mois pour lisser les variations saisonnières
-- -----------------------------------------------------------------------------
SELECT
    date_obs,
    categorie,
    valeur,
    ROUND(
        AVG(valeur) OVER (
            PARTITION BY categorie
            ORDER BY date_obs
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ), 2
    ) AS moyenne_12_mois
FROM inflation_unified
WHERE source   = 'INSEE'
  AND pays     = 'FR'
  AND date_obs BETWEEN '2020-01-01' AND '2025-12-31'
ORDER BY categorie, date_obs;


-- -----------------------------------------------------------------------------
-- A7 — Prix alimentaires Open Food Facts vs IPC officiel France (INSEE)
-- Compare le prix moyen terrain (€/kg) à l'indice IPC alimentation officiel
-- Période de référence : date de collecte Open Food Facts = juillet 2026
-- -----------------------------------------------------------------------------
SELECT
    'Open Food Facts (terrain)'     AS source,
    'alimentation'                  AS categorie,
    ROUND(AVG(o.prix_unitaire), 2)  AS valeur,
    '€ / produit'                   AS unite,
    MAX(o.date_collecte)            AS date_ref
FROM openfoodfacts o
WHERE o.prix_unitaire IS NOT NULL

UNION ALL

SELECT
    'INSEE (officiel)'              AS source,
    i.categorie,
    ROUND(AVG(i.valeur), 2)         AS valeur,
    'indice base 100 = 2015'        AS unite,
    MAX(i.date_obs)                 AS date_ref
FROM inflation_unified i
WHERE i.source   = 'INSEE'
  AND i.categorie ILIKE '%alimentation%'
GROUP BY i.categorie;


-- -----------------------------------------------------------------------------
-- A8 — Nombre de mois consécutifs d'inflation > 5% par pays (EUROSTAT)
-- Indicateur de durée de la crise inflationniste 2021-2023
-- -----------------------------------------------------------------------------
WITH mois_hauts AS (
    SELECT
        pays,
        date_obs,
        ROUND(AVG(valeur), 2) AS inflation_moy,
        CASE WHEN AVG(valeur) > 5 THEN 1 ELSE 0 END AS above_5pct
    FROM inflation_unified
    WHERE source = 'EUROSTAT'
    GROUP BY pays, date_obs
)
SELECT
    pays,
    COUNT(*) FILTER (WHERE above_5pct = 1) AS nb_mois_inflation_sup_5pct,
    ROUND(MAX(inflation_moy), 2)           AS pic_inflation
FROM mois_hauts
GROUP BY pays
ORDER BY nb_mois_inflation_sup_5pct DESC
LIMIT 15;
