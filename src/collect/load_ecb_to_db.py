"""
=============================================================================
C1 — Collecte source "BDD simulée" via API ECB (Banque Centrale Européenne)
=============================================================================
Ce script représente la source de type "base de données relationnelle externe"
du référentiel C1. On interroge l'API publique de la BCE pour récupérer
l'historique du HICP (Harmonised Index of Consumer Prices = IPC harmonisé
de la zone euro) et on charge ces données dans notre PostgreSQL.

Architecture ETL du script :
    1. EXTRACT  → fetch_ecb_hicp()
                  Appel API ECB → sauvegarde CSV brut dans data/raw/
    2. TRANSFORM → transform()
                  Lecture data/raw/ → nettoyage → sauvegarde dans data/processed/
    3. LOAD     → load_to_postgres()
                  Lecture data/processed/ → insertion dans PostgreSQL

Pourquoi séparer les étapes ?
    - Traçabilité : data/raw/ conserve la réponse brute de l'API sans modification
    - Rejouabilité : on peut relancer transform() et load() sans rappeler l'API
    - Débogage : si la DB est down, les CSV sont déjà sauvegardés
    - Preuves RNCP : chaque étape produit un fichier inspectable

Données collectées :
    - Fréquence : mensuelle (M)
    - Pays : FR, DE, ES, IT, PT, NL (6 pays zone euro)
    - Catégories COICOP : CP00 (ensemble) + CP01 à CP12 (13 catégories)
    - Indicateur : indice HICP base 2015=100 (INX) — cohérent avec INSEE et DATAGOUV
    - Volume estimé : 6 pays × 13 catégories × ~350 mois ≈ 27 000 lignes

Table cible : ecb_hicp_raw (voir src/database/schema.sql)
Issue GitHub : #4
=============================================================================
"""

import os
import io
import logging
from pathlib import Path

import requests
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL as SAUrl
from dotenv import load_dotenv

# =============================================================================
# Chemins du projet
# =============================================================================
# Path(__file__) = src/collect/load_ecb_to_db.py
# .parent.parent.parent = racine du projet
ROOT = Path(__file__).parent.parent.parent

ENV_PATH       = ROOT / ".env"
RAW_DIR        = ROOT / "data" / "raw" / "bdd_ecb"       # sous-dossier dédié à la source ECB
PROCESSED_DIR  = ROOT / "data" / "processed" / "bdd_ecb" # idem côté processed

# Création des dossiers si absents (au cas où les .gitkeep auraient été supprimés)
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# override=True : les valeurs du .env écrasent les variables système éventuelles
load_dotenv(dotenv_path=ENV_PATH, override=True)

# -----------------------------------------------------------------------------
# Purge des variables d'environnement PostgreSQL système (PG*)
# Sur Windows, psycopg2 lit automatiquement PGPASSWORD, PGUSER, PGHOST, etc.
# depuis l'environnement système. Si ces variables contiennent des accents
# (ex: un message d'erreur en français de PostgreSQL 18), psycopg2 plante
# avec UnicodeDecodeError. On les supprime ici pour forcer l'utilisation
# exclusive de nos valeurs .env qui pointent vers le Docker sur port 5437.
# -----------------------------------------------------------------------------
for _pg_var in ["PGPASSWORD", "PGUSER", "PGHOST", "PGPORT", "PGDATABASE", "PGPASSFILE"]:
    os.environ.pop(_pg_var, None)

# =============================================================================
# Configuration du logger
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# =============================================================================
# Paramètres de collecte ECB
#
# PAYS : 6 pays de la zone euro séparés par "+"
#   FR=France, DE=Allemagne, ES=Espagne, IT=Italie, PT=Portugal, NL=Pays-Bas
#
# COICOP : 12 catégories standardisées de l'IPC
#   CP01=Alimentation, CP02=Alcool/Tabac, CP03=Habillement, CP04=Logement,
#   CP05=Ameublement, CP06=Santé, CP07=Transport, CP08=Communications,
#   CP09=Loisirs, CP10=Éducation, CP11=Restaurants, CP12=Biens divers
#
# Structure URL ECB : ICP/{freq}.{pays}.{ajust}.{coicop}.{suffix}.{indicateur}
#   - M   : fréquence mensuelle
#   - N   : non ajusté saisonnièrement
#   - 4   : type d'indice
#   - ANR : Annual Rate (taux de variation annuel en %)
#
# L'opérateur "+" dans l'URL signifie "OU" → l'API retourne toutes les séries
# correspondant à chaque combinaison pays × catégorie COICOP
# =============================================================================
PAYS = "FR+DE+ES+IT+PT+NL"

# Dans le dataset ECB ICP, les catégories COICOP sont encodées en 6 chiffres :
#   000000 = tous articles (agrégat total) — c'était l'ancienne URL
#   010000 = COICOP 01 — Alimentation et boissons non alcoolisées
#   020000 = COICOP 02 — Boissons alcoolisées et tabac
#   030000 = COICOP 03 — Articles d'habillement et chaussures
#   040000 = COICOP 04 — Logement, eau, électricité, gaz
#   050000 = COICOP 05 — Ameublement, équipement ménager
#   060000 = COICOP 06 — Santé
#   070000 = COICOP 07 — Transports
#   080000 = COICOP 08 — Communications
#   090000 = COICOP 09 — Loisirs et culture
#   100000 = COICOP 10 — Enseignement
#   110000 = COICOP 11 — Restaurants et hôtels
#   120000 = COICOP 12 — Biens et services divers
COICOP = (
    "000000"                                          # 00 — Ensemble (agrégat total)
    "+010000+020000+030000+040000+050000+060000"
    "+070000+080000+090000+100000+110000+120000"
)

# Changement ANR → INX :
# ANR (Annual Rate) = taux de variation annuel en % → incompatible avec indices
# INX (Index)       = indice HICP base 2015=100 → cohérent avec INSEE et DATAGOUV
# Raison : inflation_unified doit contenir uniquement des indices base 100=2015.
ECB_URL = f"https://data-api.ecb.europa.eu/service/data/ICP/M.{PAYS}.N.{COICOP}.4.INX"

# =============================================================================
# Connexion PostgreSQL via SAUrl.create()
# On utilise SAUrl.create() au lieu d'une f-string pour éviter que des
# caractères spéciaux dans le mot de passe cassent le parsing de l'URL.
# =============================================================================
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
def fetch_ecb_hicp() -> pd.DataFrame:
    """
    Appelle l'API ECB, sauvegarde la réponse brute dans data/raw/, et retourne
    le DataFrame brut pour l'étape suivante.

    Le fichier raw est sauvegardé AVANT toute transformation — c'est la réponse
    exacte de l'API, non modifiée. Cela permet de rejouer transform() sans
    rappeler l'API si besoin. Le fichier a un nom fixe (ecb_raw.csv) — chaque
    exécution écrase le précédent pour ne pas accumuler de fichiers.

    Returns:
        pd.DataFrame: données brutes telles que retournées par l'API ECB
    """
    log.info("=" * 60)
    log.info("ETAPE 1 — EXTRACT : appel API ECB")
    log.info(f"URL : {ECB_URL}")

    # format=csvdata → réponse CSV directement lisible par pandas
    # timeout=60 → l'API ECB peut être lente sur des requêtes multi-séries
    r = requests.get(ECB_URL, params={"format": "csvdata"}, timeout=60)
    r.raise_for_status()  # lève une exception si 4xx ou 5xx

    # Lecture du CSV depuis la mémoire (pas de fichier temporaire intermédiaire)
    df_raw = pd.read_csv(io.StringIO(r.text))

    log.info(f"Reponse API : {len(df_raw)} lignes recues")
    log.info(f"Colonnes disponibles : {list(df_raw.columns)}")

    # --- Sauvegarde dans data/raw/ ---
    # Le fichier raw conserve la réponse brute de l'API sans aucune modification
    raw_path = RAW_DIR / "ecb_raw.csv"
    df_raw.to_csv(raw_path, index=False, encoding="utf-8")
    log.info(f"Donnees brutes sauvegardees dans : {raw_path}")

    return df_raw


# =============================================================================
# ÉTAPE 2 — TRANSFORM
# =============================================================================
def transform(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoie et normalise les données brutes ECB, sauvegarde le résultat dans
    data/processed/, et retourne le DataFrame propre pour l'étape de chargement.

    Transformations appliquées :
        1. Normalisation des noms de colonnes (uppercase + strip espaces)
        2. Renommage vers notre convention de nommage (snake_case)
        3. Sélection des colonnes utiles uniquement (celles de notre table SQL)
        4. Conversion obs_value en numérique (certaines valeurs peuvent être "-")
        5. Suppression des lignes sans valeur (NaN obs_value ou time_period)

    Le fichier a un nom fixe (ecb_clean.csv) — chaque exécution écrase le
    précédent pour ne pas accumuler de fichiers.

    Args:
        df_raw (pd.DataFrame): données brutes issues de fetch_ecb_hicp()

    Returns:
        pd.DataFrame: données nettoyées prêtes pour l'insertion en base
    """
    log.info("=" * 60)
    log.info("ETAPE 2 — TRANSFORM : nettoyage et normalisation")

    df = df_raw.copy()

    # Étape 1 : normalisation des noms de colonnes
    # L'API ECB utilise parfois des espaces ou des casses différentes selon les versions
    df.columns = [c.strip().upper() for c in df.columns]

    # Étape 2 : renommage vers notre convention snake_case
    # On mappe les noms de colonnes ECB vers les colonnes de notre table ecb_hicp_raw
    rename_map = {
        "TIME_PERIOD":  "time_period",  # ex: "2024-01" → période mensuelle YYYY-MM
        "OBS_VALUE":    "obs_value",    # ex: "2.4" → taux de variation annuel en %
        "REF_AREA":     "ref_area",     # ex: "FR", "DE", "ES"...
        "ICP_ITEM":     "coicop",       # ex: "CP01", "CP04"... → catégorie COICOP
        "UNIT_MEASURE": "unit",         # ex: "PC" → pourcentage
    }
    df = df.rename(columns=rename_map)

    # Étape 3 : sélection des colonnes qui correspondent à notre table SQL
    # On filtre uniquement celles qui existent dans le DataFrame (sécurité)
    colonnes_cibles   = ["time_period", "obs_value", "ref_area", "coicop", "unit"]
    colonnes_presentes = [c for c in colonnes_cibles if c in df.columns]
    df = df[colonnes_presentes].copy()

    # Étape 4a : normalisation du code COICOP
    # pandas lit ICP_ITEM comme un entier → "010000" devient 10000 (zéro de tête perdu)
    # On force en string puis on remet le padding à 6 caractères pour que
    # "10000" redevienne "010000" (COICOP 01 Alimentation) sans ambiguïté avec
    # "100000" (COICOP 10 Enseignement)
    if "coicop" in df.columns:
        df["coicop"] = df["coicop"].astype(str).str.zfill(6)

    # Étape 4b : conversion de obs_value en numérique
    # L'API peut retourner "-" ou "" pour les valeurs manquantes → mis à NaN
    df["obs_value"] = pd.to_numeric(df["obs_value"], errors="coerce")

    # Étape 5 : suppression des lignes sans valeur exploitable
    nb_avant = len(df)
    df = df.dropna(subset=["time_period", "obs_value"])
    nb_apres = len(df)
    log.info(f"Nettoyage : {nb_avant} → {nb_apres} lignes valides "
             f"({nb_avant - nb_apres} lignes supprimees)")

    # Aperçu des premières lignes pour vérification visuelle dans les logs
    log.info(f"Apercu :\n{df.head(5).to_string()}")

    # --- Sauvegarde dans data/processed/ ---
    # Le fichier processed est la version nettoyée, prête pour la base de données
    processed_path = PROCESSED_DIR / "ecb_clean.csv"
    df.to_csv(processed_path, index=False, encoding="utf-8")
    log.info(f"Donnees nettoyees sauvegardees dans : {processed_path}")

    return df


# =============================================================================
# ÉTAPE 3 — LOAD
# =============================================================================
def load_to_postgres(df_clean: pd.DataFrame, engine) -> None:
    """
    Insère le DataFrame nettoyé dans la table ecb_hicp_raw de PostgreSQL.

    On utilise if_exists="replace" pour écraser les données existantes à chaque
    exécution — ce script est idempotent (peut être relancé sans créer de doublons).
    L'UUID et created_at sont gérés par PostgreSQL (DEFAULT gen_random_uuid()
    et DEFAULT NOW() dans le schéma), donc on ne les passe pas ici.

    Args:
        df_clean (pd.DataFrame): données nettoyées issues de transform()
        engine (Engine)        : connexion SQLAlchemy à PostgreSQL
    """
    log.info("=" * 60)
    log.info(f"ETAPE 3 — LOAD : insertion de {len(df_clean)} lignes dans ecb_hicp_raw")

    # method="multi" + chunksize=500 : insère par lots de 500 lignes
    # pour éviter de dépasser la limite de paramètres PostgreSQL (~65 000)
    # Vider la table sans la recréer — préserve les contraintes UUID/index du schema.sql
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT to_regclass('public.ecb_hicp_raw')")).scalar()
        if exists:
            conn.execute(text("TRUNCATE TABLE ecb_hicp_raw CASCADE"))

    df_clean.to_sql(
        name="ecb_hicp_raw",
        con=engine,
        if_exists="append",    # append : schéma préexistant préservé
        index=False,
        method="multi",
        chunksize=500
    )

    # Vérification : recompte les lignes insérées pour confirmer le succès
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM ecb_hicp_raw")).scalar()
        log.info(f"Verification PostgreSQL : {count} lignes dans ecb_hicp_raw")


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================
def main():
    """
    Orchestre les 3 étapes ETL : Extract → Transform → Load.

    Les fichiers raw et processed ont un nom fixe par source — chaque exécution
    écrase le précédent pour ne pas accumuler de fichiers.
    """
    log.info("=" * 60)
    log.info("DEBUT COLLECTE ECB — Source BDD simulee (C1, issue #4)")
    log.info("=" * 60)

    try:
        # --- EXTRACT ---
        df_raw = fetch_ecb_hicp()

        # --- TRANSFORM ---
        df_clean = transform(df_raw)

        # --- LOAD ---
        log.info("Connexion a PostgreSQL (Docker port 5437)...")
        engine = create_engine(DB_URL)
        load_to_postgres(df_clean, engine)

        log.info("=" * 60)
        log.info("COLLECTE ECB TERMINEE AVEC SUCCES")
        log.info("  Raw      : data/raw/bdd_ecb/ecb_raw.csv")
        log.info("  Processed: data/processed/bdd_ecb/ecb_clean.csv")
        log.info("  Base     : table ecb_hicp_raw dans PostgreSQL")
        log.info("=" * 60)

    except requests.exceptions.Timeout:
        log.error("Timeout : l'API ECB n'a pas repondu en 60 secondes")
        raise
    except requests.exceptions.HTTPError as e:
        log.error(f"Erreur HTTP API ECB : {e}")
        raise
    except Exception as e:
        log.error(f"Erreur inattendue : {e}")
        raise


if __name__ == "__main__":
    # Lancement direct : python src/collect/load_ecb_to_db.py
    main()
