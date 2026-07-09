"""
=============================================================================
C3 — Agrégation et nettoyage — 4 sources → inflation_unified
=============================================================================
Ce script est le cœur de la compétence C3 (nettoyage et transformation des
données). Il consolide les 4 sources d'indices en une table unifiée, normalisée
et exploitable par les étapes suivantes (API C5, modèle Prophet C8, Grafana C9).

Sources agrégées (4 sur 5 — openfoodfacts exclu) :
    ECB       → ecb_hicp_raw    — HICP zone euro, taux de variation annuel
    INSEE     → insee_ipc        — IPC France base 2015, indices mensuels
    DATAGOUV  → datagouv_ipc    — IPC France séries longues (depuis 1996)
    EUROSTAT  → eurostat_bulk   — HICP 27 pays UE, taux annuel (3.5M lignes)

Pourquoi openfoodfacts est exclu :
    La table openfoodfacts contient des prix en euros (€) relevés en rayon,
    pas des indices statistiques normalisés. Les mélanger avec des indices
    base 100 = 2015 créerait une incohérence sémantique dans la colonne valeur.
    openfoodfacts est utilisé directement par l'API (C5) pour l'analyse des
    prix alimentaires, pas dans la table unifiée.

Table cible : inflation_unified (voir src/database/schema.sql)
    date_obs  : DATE NOT NULL               — premier jour du mois
    pays      : VARCHAR(10) NOT NULL        — code pays ISO : "FR", "DE", "AT"…
    categorie : VARCHAR(100) NOT NULL       — code COICOP ou libellé catégorie
    valeur    : NUMERIC(10,4) NOT NULL      — valeur de l'indice ou taux
    source    : VARCHAR(50) NOT NULL        — "ECB", "INSEE", "DATAGOUV", "EUROSTAT"
    UNIQUE (date_obs, pays, categorie, source)

Stratégie d'insertion :
    INSERT ... ON CONFLICT DO NOTHING → idempotent (relançable sans doublons)
    SQL pur (pas de pandas) → optimal pour les 3.5M lignes Eurostat

Issue GitHub : #10 (C3 — agrégation et nettoyage)
=============================================================================
"""

import os
import logging
import time
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL as SAUrl
from dotenv import load_dotenv

# =============================================================================
# Configuration
# =============================================================================
ROOT     = Path(__file__).parent.parent.parent
ENV_PATH = ROOT / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)

for _pg_var in ["PGPASSWORD", "PGUSER", "PGHOST", "PGPORT", "PGDATABASE", "PGPASSFILE"]:
    os.environ.pop(_pg_var, None)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DB_URL = SAUrl.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    database=os.getenv("POSTGRES_DB", "inflation_tracker"),
)

# =============================================================================
# Requêtes SQL d'agrégation par source
# Chaque requête sélectionne les colonnes et les mappe vers inflation_unified.
# ON CONFLICT DO NOTHING assure l'idempotence grâce à la contrainte UNIQUE.
# =============================================================================

# ECB : time_period VARCHAR "YYYY-MM" → DATE via concat + cast
# ref_area = code pays, coicop = code COICOP, obs_value = valeur
SQL_ECB = """
INSERT INTO inflation_unified (date_obs, pays, categorie, valeur, source)
SELECT
    (time_period || '-01')::DATE  AS date_obs,
    ref_area                      AS pays,
    coicop                        AS categorie,
    obs_value                     AS valeur,
    'ECB'                         AS source
FROM ecb_hicp_raw
WHERE obs_value IS NOT NULL
  AND time_period IS NOT NULL
  AND ref_area    IS NOT NULL
  AND coicop      IS NOT NULL
ON CONFLICT (date_obs, pays, categorie, source) DO NOTHING
"""

# INSEE : date_obs est déjà DATE, valeur est l'indice IPC base 2015
# pays fixé à 'FR' (données France uniquement)
SQL_INSEE = """
INSERT INTO inflation_unified (date_obs, pays, categorie, valeur, source)
SELECT
    date_obs,
    'FR'        AS pays,
    categorie,
    valeur,
    'INSEE'     AS source
FROM insee_ipc
WHERE valeur   IS NOT NULL
  AND categorie IS NOT NULL
ON CONFLICT (date_obs, pays, categorie, source) DO NOTHING
"""

# DATAGOUV : même structure qu'INSEE — séries longues IPC France depuis 1996
# source déjà présente dans la table mais on uniformise à 'DATAGOUV'
SQL_DATAGOUV = """
INSERT INTO inflation_unified (date_obs, pays, categorie, valeur, source)
SELECT
    date_obs,
    'FR'        AS pays,
    categorie,
    valeur,
    'DATAGOUV'  AS source
FROM datagouv_ipc
WHERE valeur   IS NOT NULL
  AND categorie IS NOT NULL
ON CONFLICT (date_obs, pays, categorie, source) DO NOTHING
"""

# EUROSTAT : pays et date_obs déjà au bon format, coicop = catégorie HICP
# Filtre : valeur NOT NULL (les NaN ont déjà été supprimés à l'import)
SQL_EUROSTAT = """
INSERT INTO inflation_unified (date_obs, pays, categorie, valeur, source)
SELECT
    date_obs,
    pays,
    coicop      AS categorie,
    valeur,
    'EUROSTAT'  AS source
FROM eurostat_bulk
WHERE valeur IS NOT NULL
  AND pays   IS NOT NULL
  AND coicop IS NOT NULL
ON CONFLICT (date_obs, pays, categorie, source) DO NOTHING
"""

SOURCES = [
    ("ECB",      SQL_ECB),
    ("INSEE",    SQL_INSEE),
    ("DATAGOUV", SQL_DATAGOUV),
    ("EUROSTAT", SQL_EUROSTAT),
]


def aggregate(engine) -> None:
    """
    Vide inflation_unified puis insère les données agrégées des 4 sources.

    Utilise SQL pur (INSERT ... SELECT) sans passer par pandas pour éviter
    de charger 3.5M lignes Eurostat en mémoire. Chaque INSERT est idempotent
    grâce à ON CONFLICT DO NOTHING sur la contrainte UNIQUE.
    """
    log.info("=" * 60)
    log.info("DEBUT AGREGATION — inflation_unified (C3, issue #10)")
    log.info("=" * 60)

    with engine.begin() as conn:
        # Vider la table sans la recréer (préserve UUID et contraintes)
        exists = conn.execute(
            text("SELECT to_regclass('public.inflation_unified')")
        ).scalar()
        if exists:
            conn.execute(text("TRUNCATE TABLE inflation_unified CASCADE"))
            log.info("inflation_unified vidée (TRUNCATE CASCADE)")

    total_inseres = 0

    for label, sql in SOURCES:
        log.info(f"[{label}] Insertion en cours...")
        debut = time.time()

        with engine.begin() as conn:
            result = conn.execute(text(sql))
            nb     = result.rowcount

        duree = round(time.time() - debut, 1)
        log.info(f"[{label}] {nb:>10,} lignes insérées en {duree}s")
        total_inseres += nb

    # Vérification finale
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM inflation_unified")).scalar()
        detail = conn.execute(text("""
            SELECT source, COUNT(*) AS nb, MIN(date_obs) AS debut, MAX(date_obs) AS fin
            FROM inflation_unified
            GROUP BY source
            ORDER BY source
        """)).fetchall()

    log.info("=" * 60)
    log.info(f"AGREGATION TERMINÉE — {count:,} lignes dans inflation_unified")
    log.info("=" * 60)
    for row in detail:
        log.info(f"  {row.source:12} : {row.nb:>10,} lignes  ({row.debut} → {row.fin})")
    log.info("=" * 60)


def main() -> None:
    engine = create_engine(DB_URL)
    aggregate(engine)


if __name__ == "__main__":
    main()
