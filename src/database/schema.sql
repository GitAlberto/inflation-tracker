-- =============================================================================
-- inflation-tracker — Schéma PostgreSQL
-- Compétence C4 — Modélisation et création de la base de données
-- =============================================================================
-- MCD : 5 tables sources + 1 table unifiée (source de vérité)
-- Toutes les valeurs sont normalisées en base 100 = 2015 après agrégation (C3)
-- =============================================================================

-- Nettoyage si le schéma existe déjà (pratique pour les tests)
DROP TABLE IF EXISTS inflation_unified CASCADE;
DROP TABLE IF EXISTS eurostat_bulk CASCADE;
DROP TABLE IF EXISTS openfoodfacts CASCADE;
DROP TABLE IF EXISTS insee_ipc CASCADE;
DROP TABLE IF EXISTS ecb_hicp_raw CASCADE;

-- =============================================================================
-- TABLE 1 : ecb_hicp_raw
-- Source : API ECB (Banque Centrale Européenne)
-- Contenu : HICP (Harmonised Index of Consumer Prices) zone euro, mensuel
-- =============================================================================
CREATE TABLE ecb_hicp_raw (
    id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    time_period VARCHAR(7)      NOT NULL,   -- Format YYYY-MM ex: "2024-01"
    obs_value   NUMERIC(10, 4),             -- Valeur de l'indice HICP
    ref_area    VARCHAR(10)     NOT NULL,   -- Zone géo ex: "U2" (zone euro), "FR"
    unit        VARCHAR(50),               -- Unité ex: "INX_A_AVG"
    created_at  TIMESTAMP       DEFAULT NOW()
);

-- =============================================================================
-- TABLE 2 : insee_ipc
-- Source : API INSEE BDM
-- Contenu : Indice des Prix à la Consommation France, mensuel par catégorie
-- =============================================================================
CREATE TABLE insee_ipc (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    date_obs        DATE            NOT NULL,   -- Date d'observation (1er du mois)
    valeur          NUMERIC(10, 4)  NOT NULL,   -- Valeur IPC
    categorie       VARCHAR(100)    NOT NULL,   -- Catégorie ex: "alimentation"
    sous_categorie  VARCHAR(100),               -- Sous-catégorie COICOP
    idbank          VARCHAR(20),               -- Identifiant série INSEE
    source          VARCHAR(50)     DEFAULT 'INSEE',
    created_at      TIMESTAMP       DEFAULT NOW()
);

-- =============================================================================
-- TABLE 3 : openfoodfacts
-- Source : Scraping Open Food Facts (licence ODbL)
-- Contenu : Prix de produits alimentaires par catégorie
-- RGPD : aucune donnée personnelle — prix publics uniquement
-- =============================================================================
CREATE TABLE openfoodfacts (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    produit         VARCHAR(255),               -- Nom du produit
    categorie       VARCHAR(100)    NOT NULL,   -- Catégorie alimentaire
    prix_unitaire   NUMERIC(10, 2),             -- Prix en euros
    date_collecte   DATE            NOT NULL,   -- Date du scraping
    url             TEXT,                       -- URL produit Open Food Facts
    created_at      TIMESTAMP       DEFAULT NOW()
);

-- =============================================================================
-- TABLE 4 : eurostat_bulk
-- Source : Eurostat bulk CSV traité via PySpark
-- Contenu : HICP 27 pays UE x 100+ catégories COICOP x 30 ans
-- =============================================================================
CREATE TABLE eurostat_bulk (
    id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    pays        VARCHAR(10)     NOT NULL,   -- Code pays ISO ex: "FR", "DE"
    coicop      VARCHAR(20)     NOT NULL,   -- Code COICOP ex: "CP01"
    date_obs    DATE            NOT NULL,   -- Date d'observation
    valeur      NUMERIC(10, 4),             -- Valeur HICP
    unite       VARCHAR(50),               -- Unité ex: "INX_A_AVG"
    created_at  TIMESTAMP       DEFAULT NOW()
);

-- =============================================================================
-- TABLE 5 : inflation_unified
-- Table finale unifiée — source de vérité du projet
-- Alimentée par src/aggregate/aggregate_clean.py (C3)
-- Exposée par l'API data (C5) et consommée par le modèle Prophet (C8)
-- =============================================================================
CREATE TABLE inflation_unified (
    id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    date_obs    DATE            NOT NULL,
    pays        VARCHAR(10)     NOT NULL DEFAULT 'FR',
    categorie   VARCHAR(100)    NOT NULL,
    valeur      NUMERIC(10, 4)  NOT NULL,   -- Base 100 = 2015
    source      VARCHAR(50)     NOT NULL,
    created_at  TIMESTAMP       DEFAULT NOW(),
    UNIQUE (date_obs, pays, categorie, source)
);

-- =============================================================================
-- INDEX — optimisation des requêtes fréquentes
-- =============================================================================
CREATE INDEX idx_ecb_time       ON ecb_hicp_raw (time_period);
CREATE INDEX idx_ecb_ref_area   ON ecb_hicp_raw (ref_area);

CREATE INDEX idx_insee_date     ON insee_ipc (date_obs);
CREATE INDEX idx_insee_cat      ON insee_ipc (categorie);

CREATE INDEX idx_off_date       ON openfoodfacts (date_collecte);
CREATE INDEX idx_off_cat        ON openfoodfacts (categorie);

CREATE INDEX idx_euro_pays      ON eurostat_bulk (pays);
CREATE INDEX idx_euro_date      ON eurostat_bulk (date_obs);
CREATE INDEX idx_euro_coicop    ON eurostat_bulk (coicop);

CREATE INDEX idx_unified_date   ON inflation_unified (date_obs);
CREATE INDEX idx_unified_cat    ON inflation_unified (categorie);
CREATE INDEX idx_unified_pays   ON inflation_unified (pays);
CREATE INDEX idx_unified_source ON inflation_unified (source);
