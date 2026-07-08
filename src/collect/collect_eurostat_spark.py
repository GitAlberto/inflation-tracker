"""
=============================================================================
C1 — Collecte source "Big Data" via Eurostat bulk download + PySpark
=============================================================================
Ce script représente la source de type "Big Data" du référentiel C1.
On télécharge le dataset HICP complet d'Eurostat (27 pays UE × 100+ catégories
COICOP × ~30 ans) et on le traite avec PySpark pour démontrer la compétence
traitement distribué.

Architecture ETL :
    1. EXTRACT  → download_bulk()
                  Téléchargement HTTP du fichier TSV.GZ (bulk Eurostat)
                  → data/raw/bigdata_eurostat/prc_hicp_manr_raw.tsv.gz
    2. TRANSFORM → transform_with_spark()
                  Lecture + traitement PySpark du TSV brut
                  → data/processed/bigdata_eurostat/eurostat_clean.csv
    3. LOAD     → load_to_postgres()
                  Chargement pandas → PostgreSQL (table eurostat_bulk)

Pourquoi PySpark ?
    Le fichier prc_hicp_manr contient ~200 000+ lignes après dépivotage.
    PySpark démontre la maîtrise du traitement de données volumineuses (C1)
    en mode distribué local, même sur une seule machine.

=============================================================================
Format du fichier source (prc_hicp_manr.tsv de Eurostat Bulk Download) :
=============================================================================
    URL      : https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/
               data/prc_hicp_manr/?format=TSV&compressed=true
    Format   : TSV compressé GZIP (.tsv.gz)
    Encodage : UTF-8
    Séparateur : tabulation (\t) entre la clé composite et les valeurs
               virgule (,) à l'intérieur de la clé composite
    Structure : FORMAT LARGE (wide) — une ligne par combinaison de dimensions

    Première ligne (en-tête) :
        "freq,unit,coicop,geo\time" | "2024-12" | "2024-11" | ... | "1996-01"
        - La première colonne contient 4 dimensions séparées par des virgules
        - Les colonnes suivantes sont des périodes mensuelles (YYYY-MM)
          en ordre DÉCROISSANT (la plus récente en premier)

    Lignes de données (exemple) :
        "M,RCH_A,CP00,AT"  | "2.1 p"  | "2.8"  | "3.1 p" | ...
        "M,RCH_A,CP00,BE"  | "1.9"    | "2.4"  | "2.7"   | ...
        "M,RCH_A,CP01,FR"  | "3.2"    | "3.5"  | "4.1"   | ...

    Décomposition de la clé composite :
        freq   : fréquence → toujours "M" (mensuel) dans ce dataset
        unit   : unité → "RCH_A" = taux de variation annuel en %
                          "INX_A_AVG" = indice base 2015=100
        coicop : catégorie COICOP → "CP00" (all-items), "CP01" (alimentation),
                 "CP02" (alcool/tabac) ... "CP12" (biens divers)
                 + sous-catégories : "CP0111", "CP0112", ...
        geo    : pays ISO2 → "AT", "BE", "BG", "CY", "CZ", "DE", "DK",
                 "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IE", "IT",
                 "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE",
                 "SI", "SK" + zones agrégées : "EA", "EU27_2020"

    Valeurs :
        - Numérique (ex: "2.1") — valeur de l'indice ou du taux
        - Avec flag de qualité (ex: "2.1 p") — "p"=provisoire, "e"=estimé
        - ":" — valeur manquante (à convertir en NULL)
        - Vide ("") — valeur non disponible

    Volume après dépivotage (wide → long) :
        ~800 combinaisons freq×unit×coicop×geo × ~340 périodes ≈ ~270 000 lignes
        En filtrant unit=RCH_A (taux annuel) : ~150 000 lignes utiles

Table cible : eurostat_bulk (voir src/database/schema.sql)
    time_period ← colonne date dépivotée (YYYY-MM)
    obs_value   ← valeur numérique (flag supprimé)
    geo         ← code pays (ex: "FR", "DE")
    coicop      ← catégorie COICOP (ex: "CP01")
    unit        ← unité de mesure (ex: "RCH_A")

RGPD : aucune donnée personnelle — statistiques officielles Eurostat.
Licence : Creative Commons Attribution 4.0 (CC BY 4.0).
Issue GitHub : #7 (C1 — source Big Data)
=============================================================================
"""

import setuptools  # noqa: F401 — doit être importé avant pyspark sur Python 3.12+
import os
import sys
import gzip
import logging
from pathlib import Path

import requests
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL as SAUrl
from dotenv import load_dotenv

# =============================================================================
# JAVA_HOME — requis par PySpark pour trouver la JVM
# On le définit ici avant d'importer pyspark, pour éviter l'erreur
# "Java gateway process exited before sending its port number" si JAVA_HOME
# n'est pas défini dans les variables d'environnement système.
# Eclipse Temurin 21 est installé à ce chemin sur la machine de développement.
# =============================================================================
_JAVA_HOME_DEFAULT = r"C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot"
if not os.environ.get("JAVA_HOME"):
    os.environ["JAVA_HOME"] = _JAVA_HOME_DEFAULT

# PYSPARK_PYTHON — force PySpark à utiliser le Python du venv, pas le Python
# système. Sur Windows, `python` dans le PATH système redirige vers le Microsoft
# Store (non installé), ce qui fait échouer les workers Spark avec "Python not found".
# sys.executable = chemin absolu vers le Python actuellement en cours d'exécution,
# soit .venv/Scripts/python.exe — c'est exactement ce qu'on veut.
os.environ["PYSPARK_PYTHON"]        = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

# =============================================================================
# Chemins du projet
# =============================================================================
ROOT          = Path(__file__).parent.parent.parent
ENV_PATH      = ROOT / ".env"
RAW_DIR       = ROOT / "data" / "raw" / "bigdata_eurostat"
PROCESSED_DIR = ROOT / "data" / "processed" / "bigdata_eurostat"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(dotenv_path=ENV_PATH, override=True)

for _pg_var in ["PGPASSWORD", "PGUSER", "PGHOST", "PGPORT", "PGDATABASE", "PGPASSFILE"]:
    os.environ.pop(_pg_var, None)

# =============================================================================
# Logger
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================
# URL Eurostat API bulk download — format TSV compressé GZIP
# dataset prc_hicp_manr = HICP monthly rates of change (taux de variation mensuel)
EUROSTAT_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/"
    "data/prc_hicp_manr/?format=TSV&compressed=true"
)

# On filtre sur RCH_A (Annual Rate of Change) — c'est l'indicateur d'inflation
# comparable avec les données ECB et INSEE du projet
UNIT_FILTRE = "RCH_A"

# Connexion PostgreSQL
DB_URL = SAUrl.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    database=os.getenv("POSTGRES_DB", "inflation_tracker"),
)


# =============================================================================
# ÉTAPE 1 — EXTRACT
# =============================================================================
def download_bulk() -> Path:
    """
    Télécharge le fichier bulk TSV.GZ depuis l'API Eurostat et le sauvegarde
    dans data/raw/bigdata_eurostat/prc_hicp_manr_raw.tsv.gz.

    Le fichier est sauvegardé tel quel (compressé) pour conserver la donnée
    brute originale. La décompression se fait dans transform_with_spark().

    Returns:
        Path: chemin vers le fichier .tsv.gz téléchargé
    """
    log.info("=" * 60)
    log.info("ETAPE 1 — EXTRACT : téléchargement Eurostat bulk")
    log.info(f"URL : {EUROSTAT_URL}")

    r = requests.get(
        EUROSTAT_URL,
        headers={"User-Agent": "inflation-tracker/1.0 (bonguelealberto@gmail.com)"},
        timeout=120,
        stream=True
    )
    r.raise_for_status()

    raw_path = RAW_DIR / "prc_hicp_manr_raw.tsv.gz"

    # Écriture en mode binaire — le fichier est compressé GZIP
    with open(raw_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    size_mb = raw_path.stat().st_size / (1024 * 1024)
    log.info(f"Fichier téléchargé : {raw_path} ({size_mb:.1f} Mo)")
    return raw_path


# =============================================================================
# ÉTAPE 2 — TRANSFORM (PySpark)
# =============================================================================
def transform_with_spark(raw_path: Path) -> pd.DataFrame:
    """
    Traite le fichier TSV Eurostat avec PySpark :
        1. Décompression GZIP + lecture du TSV en mémoire
        2. Création d'un DataFrame Spark depuis le contenu TSV
        3. Séparation de la colonne clé composite (freq,unit,coicop,geo)
        4. Dépivotage (wide → long) : une colonne par période → une ligne par observation
        5. Nettoyage des valeurs (suppression des flags "p", "e", etc.)
        6. Filtrage sur unit=RCH_A (taux annuel de variation)
        7. Conversion en pandas pour le chargement PostgreSQL

    Pourquoi PySpark pour ce traitement ?
        - Le fichier wide a ~800 lignes × ~350 colonnes = 280 000 cellules
        - Le dépivotage crée ~270 000 lignes — PySpark gère cela efficacement
        - Démontre la compétence Big Data / traitement distribué (C1)

    Args:
        raw_path (Path): chemin vers le fichier .tsv.gz brut

    Returns:
        pd.DataFrame: données nettoyées, format long, prêtes pour PostgreSQL
    """
    log.info("=" * 60)
    log.info("ETAPE 2 — TRANSFORM : traitement PySpark")

    # --- Initialisation SparkSession ---
    # master("local[*]") = mode local, tous les cœurs disponibles
    # arrow désactivé : évite les conflits de sérialisation Python/JVM sur Windows
    # avec un chemin contenant des espaces
    spark = (SparkSession.builder
             .appName("inflation-tracker-eurostat")
             .master("local[*]")
             .config("spark.driver.memory", "2g")
             .config("spark.sql.shuffle.partitions", "4")
             .config("spark.sql.execution.arrow.pyspark.enabled", "false")
             .getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    log.info("SparkSession initialisée (mode local)")

    # --- Décompression GZIP → fichier TSV temporaire ---
    # On écrit le TSV décompressé sur disque pour le lire avec spark.read.csv().
    # Pourquoi ne pas passer par pandas + createDataFrame(pandas_df) ?
    # Sur Windows avec un chemin contenant des espaces, createDataFrame() déclenche
    # des Python workers (processus enfants) que Spark lance via le PATH système.
    # Le PATH système sur cette machine redirige 'python' vers le Microsoft Store,
    # causant un crash "Python worker exited unexpectedly".
    # spark.read.csv() utilise le lecteur JVM natif — aucun Python worker nécessaire.
    log.info("Décompression GZIP → TSV temporaire...")
    tsv_path = RAW_DIR / "prc_hicp_manr_raw.tsv"
    with gzip.open(raw_path, "rb") as f_in:
        with open(tsv_path, "wb") as f_out:
            f_out.write(f_in.read())
    log.info(f"TSV décompressé : {tsv_path}")

    # --- Lecture directe avec Spark (JVM natif, sans Python workers) ---
    # nullValue=":" → les ":" Eurostat (valeurs manquantes) deviennent null
    df_spark = (spark.read
                .option("sep", "\t")
                .option("header", "true")
                .option("nullValue", ":")
                .option("encoding", "UTF-8")
                .csv(str(tsv_path)))

    nb_lignes = df_spark.count()
    nb_cols   = len(df_spark.columns)
    log.info(f"Fichier TSV lu : {nb_lignes} lignes × {nb_cols} colonnes")

    # --- Normalisation du nom de la première colonne ---
    # Le nom de la première colonne contient un backslash : "freq,unit,coicop,geo\time"
    # On le renomme pour faciliter la manipulation
    premiere_col = df_spark.columns[0]
    df_spark = df_spark.withColumnRenamed(premiere_col, "cle_composite")
    log.info(f"Première colonne renommée : '{premiere_col}' → 'cle_composite'")

    # --- Séparation de la clé composite ---
    # Format : "M,RCH_A,CP00,AT" → freq="M", unit="RCH_A", coicop="CP00", geo="AT"
    df_spark = (df_spark
                .withColumn("freq",   F.split(F.col("cle_composite"), ",")[0])
                .withColumn("unit",   F.split(F.col("cle_composite"), ",")[1])
                .withColumn("coicop", F.split(F.col("cle_composite"), ",")[2])
                .withColumn("geo",    F.split(F.col("cle_composite"), ",")[3])
                .drop("cle_composite"))

    # --- Filtrage sur unit=RCH_A AVANT le dépivotage ---
    # Réduire les données avant le stack() pour gagner en performance
    df_spark = df_spark.filter(F.col("unit") == UNIT_FILTRE)
    log.info(f"Filtrage unit={UNIT_FILTRE} : {df_spark.count()} lignes conservées")

    # --- Dépivotage (wide → long) avec stack() ---
    # Les colonnes de dates sont toutes celles sauf freq, unit, coicop, geo
    colonnes_dates = [c for c in df_spark.columns if c not in ("freq", "unit", "coicop", "geo")]
    log.info(f"Colonnes de dates à dépivater : {len(colonnes_dates)} périodes")

    # Construction de l'expression stack() pour PySpark
    # stack(N, 'date1', col1, 'date2', col2, ...) → (time_period, obs_value_raw)
    stack_expr = f"stack({len(colonnes_dates)}, " + ", ".join(
        [f"'{c}', `{c}`" for c in colonnes_dates]
    ) + ") as (time_period, obs_value_raw)"

    df_long = df_spark.select(
        "freq", "unit", "coicop", "geo",
        F.expr(stack_expr)
    )

    # --- Nettoyage de obs_value_raw ---
    # Les valeurs peuvent contenir des flags qualité : "2.1 p", "3.5 e"
    # On supprime tout ce qui n'est pas le nombre lui-même
    df_long = (df_long
               .withColumn("obs_value_str",
                           F.trim(F.regexp_replace(F.col("obs_value_raw"), r"[a-zA-Z\s]+", "")))
               .withColumn("obs_value",
                           F.col("obs_value_str").cast("double"))
               .drop("obs_value_raw", "obs_value_str"))

    # --- Suppression des lignes sans valeur ---
    nb_avant = df_long.count()
    df_long = df_long.filter(F.col("obs_value").isNotNull())
    nb_apres = df_long.count()
    log.info(f"Suppression des NaN : {nb_avant} → {nb_apres} lignes valides")

    # --- Conversion en pandas pour le chargement PostgreSQL ---
    log.info("Conversion Spark → pandas...")
    df_clean = df_long.select(
        "time_period", "obs_value", "geo", "coicop", "unit"
    ).toPandas()

    df_clean = df_clean.sort_values(["geo", "coicop", "time_period"]).reset_index(drop=True)

    log.info(f"Aperçu :\n{df_clean.head(5).to_string()}")
    log.info(f"Résultat : {len(df_clean)} lignes × {len(df_clean.columns)} colonnes")

    # --- Sauvegarde processed ---
    processed_path = PROCESSED_DIR / "eurostat_clean.csv"
    df_clean.to_csv(processed_path, index=False, encoding="utf-8")
    log.info(f"Données nettoyées sauvegardées : {processed_path}")

    spark.stop()
    log.info("SparkSession arrêtée")

    return df_clean


# =============================================================================
# ÉTAPE 3 — LOAD
# =============================================================================
def load_to_postgres(df_clean: pd.DataFrame, engine) -> None:
    """
    Insère le DataFrame nettoyé dans la table eurostat_bulk de PostgreSQL.

    Args:
        df_clean (pd.DataFrame): données nettoyées issues de transform_with_spark()
        engine (Engine)        : connexion SQLAlchemy à PostgreSQL
    """
    log.info("=" * 60)
    log.info(f"ETAPE 3 — LOAD : insertion de {len(df_clean)} lignes dans eurostat_bulk")

    # Vider la table sans la recréer — préserve les contraintes UUID/index du schema.sql
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT to_regclass('public.eurostat_bulk')")).scalar()
        if exists:
            conn.execute(text("TRUNCATE TABLE eurostat_bulk CASCADE"))

    df_clean.to_sql(
        name="eurostat_bulk",
        con=engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000
    )

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM eurostat_bulk")).scalar()
        log.info(f"Vérification PostgreSQL : {count} lignes dans eurostat_bulk")


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================
def main():
    log.info("=" * 60)
    log.info("DEBUT COLLECTE EUROSTAT BULK — PySpark (C1, issue #7)")
    log.info("=" * 60)

    try:
        # --- EXTRACT ---
        raw_path = download_bulk()

        # --- TRANSFORM ---
        df_clean = transform_with_spark(raw_path)

        # --- LOAD ---
        log.info("Connexion à PostgreSQL (Docker port 5437)...")
        engine = create_engine(DB_URL)
        load_to_postgres(df_clean, engine)

        log.info("=" * 60)
        log.info("COLLECTE EUROSTAT TERMINÉE AVEC SUCCÈS")
        log.info("  Raw      : data/raw/bigdata_eurostat/prc_hicp_manr_raw.tsv.gz")
        log.info("  Processed: data/processed/bigdata_eurostat/eurostat_clean.csv")
        log.info("  Base     : table eurostat_bulk dans PostgreSQL")
        log.info("=" * 60)

    except Exception as e:
        log.error(f"Erreur inattendue : {e}")
        raise


if __name__ == "__main__":
    main()
