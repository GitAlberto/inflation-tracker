-- =============================================================================
-- C2 — Requêtes SQL analytiques — inflation-tracker
-- =============================================================================
-- Ces requêtes produisent des indicateurs statistiques et des analyses
-- comparatives à partir de inflation_unified. Elles sont conçues pour
-- répondre à des questions métier : quelle catégorie a le plus augmenté ?
-- Note : inflation_unified ne contient que des données France — aucun filtre
-- pays n'est nécessaire sur cette table.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- A1 — Inflation moyenne annuelle (EUROSTAT) — 2020 à 2024
-- Agrégation : moyenne de toutes les catégories COICOP par an
-- -----------------------------------------------------------------------------
SELECT
    EXTRACT(YEAR FROM date_obs)::INT    AS annee,
    ROUND(AVG(valeur), 2)               AS inflation_moy_pct,
    COUNT(DISTINCT categorie)           AS nb_categories
FROM inflation_unified
WHERE source   = 'EUROSTAT'
  AND date_obs BETWEEN '2020-01-01' AND '2024-12-31'
GROUP BY annee
ORDER BY annee;

-- 13 = 12 catégories + 1 indice d'ensemble (00).
-- -----------------------------------------------------------------------------
-- A2 — Pic d'inflation : année et valeur maximale (EUROSTAT)
-- Identifie l'année où l'inflation a culminé
-- -----------------------------------------------------------------------------
SELECT
    EXTRACT(YEAR FROM date_obs)::INT AS annee_pic,
    ROUND(MAX(valeur), 2)            AS inflation_max_pct
FROM inflation_unified
WHERE source = 'EUROSTAT'
GROUP BY EXTRACT(YEAR FROM date_obs)
HAVING MAX(valeur) = (
    SELECT MAX(valeur)
    FROM inflation_unified i2
    WHERE i2.source = 'EUROSTAT'
)
ORDER BY inflation_max_pct DESC;


-- -----------------------------------------------------------------------------
-- A3 — Top 10 catégories COICOP les plus inflationnistes (EUROSTAT)
-- Classement sur la moyenne 2022-2023 (période de forte inflation)
-- -----------------------------------------------------------------------------
SELECT
    categorie,
    ROUND(AVG(valeur), 2)   AS inflation_moy_pct,
    ROUND(MAX(valeur), 2)   AS pic_pct,
    COUNT(*)                AS nb_observations
FROM inflation_unified
WHERE source   = 'EUROSTAT'
  AND date_obs BETWEEN '2022-01-01' AND '2023-12-31'
GROUP BY categorie
ORDER BY inflation_moy_pct DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- A4 — France vs Zone Euro (ECB) — 2020 à 2025
-- Comparaison directe depuis ecb_hicp_raw qui contient 6 pays.
-- inflation_unified ne contenant que la France, cette comparaison
-- doit obligatoirement interroger la table source ECB multi-pays.
-- -----------------------------------------------------------------------------
SELECT
    time_period                                                 AS date_obs,
    MAX(CASE WHEN ref_area = 'FR' THEN obs_value END)          AS france,
    MAX(CASE WHEN ref_area = 'U2' THEN obs_value END)          AS zone_euro
FROM ecb_hicp_raw
WHERE ref_area  IN ('FR', 'U2')
  AND coicop    = '000000'
  AND time_period BETWEEN '2020-01-01' AND '2025-12-31'
GROUP BY time_period
ORDER BY time_period;


-- -----------------------------------------------------------------------------
-- A5 — Volatilité de l'inflation par catégorie (écart-type) — EUROSTAT
-- Les catégories avec le plus grand écart-type ont eu l'inflation la plus instable
-- -----------------------------------------------------------------------------
SELECT
    categorie,
    ROUND(AVG(valeur), 2)    AS inflation_moy,
    ROUND(STDDEV(valeur), 2) AS ecart_type,
    ROUND(MIN(valeur), 2)    AS min_pct,
    ROUND(MAX(valeur), 2)    AS max_pct
FROM inflation_unified
WHERE source   = 'EUROSTAT'
  AND date_obs BETWEEN '2020-01-01' AND '2024-12-31'
GROUP BY categorie
ORDER BY ecart_type DESC;


-- -----------------------------------------------------------------------------
-- A6 — Évolution IPC base 2015 — INSEE — toutes catégories — 2020-2025
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
  AND date_obs BETWEEN '2020-01-01' AND '2025-12-31'
ORDER BY categorie, date_obs;


-- -----------------------------------------------------------------------------
-- A7 — Prix alimentaires Open Food Facts vs IPC officiel INSEE
-- Compare le prix moyen terrain (€/produit) à l'indice IPC alimentation officiel
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
-- A8 — Nombre de mois d'inflation > 5% par catégorie (EUROSTAT)
-- Indicateur de durée de la crise inflationniste 2021-2023 par secteur
-- -----------------------------------------------------------------------------
WITH mois_hauts AS (
    SELECT
        categorie,
        date_obs,
        ROUND(AVG(valeur), 2) AS inflation_moy,
        CASE WHEN AVG(valeur) > 5 THEN 1 ELSE 0 END AS above_5pct
    FROM inflation_unified
    WHERE source = 'EUROSTAT'
    GROUP BY categorie, date_obs
)
SELECT
    categorie,
    COUNT(*) FILTER (WHERE above_5pct = 1) AS nb_mois_inflation_sup_5pct,
    ROUND(MAX(inflation_moy), 2)           AS pic_inflation
FROM mois_hauts
GROUP BY categorie
ORDER BY nb_mois_inflation_sup_5pct DESC;