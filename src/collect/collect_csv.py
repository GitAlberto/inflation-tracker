"""
=============================================================================
C1 — Collecte source "CSV" via data.gouv.fr (INSEE séries longues IPC)
=============================================================================
Ce script représente la source de type "fichier CSV" du référentiel C1.
On télécharge le fichier CSV des séries longues de l'IPC publié par l'INSEE
sur data.gouv.fr et on le charge dans notre PostgreSQL.

Source :
    INSEE — Indice des prix à la consommation, jeu de données principal
    Publié sur : https://www.data.gouv.fr
    Fichier ZIP : DS_IPC_PRINC_CSV_FR.zip
    Licence : Licence Ouverte Etalab v2.0 (réutilisation libre)

Format du fichier source (DS_IPC_PRINC_data.csv dans le ZIP) :
    - Séparateur : point-virgule (;)
    - Encodage   : UTF-8
    - Structure  : format LONG — une ligne par observation (pas de pivot nécessaire)
    - Volume     : ~444 000 lignes × 16 colonnes (toutes fréquences confondues)
    - Colonnes exactes :
        IDX_TYPE        — type d'indice (ex: "CPI")
        IND_TYPE        — type d'indicateur (ex: "IX" = index)
        PRODUCT_GROUP   — groupe produit (ex: "_Z")
        COICOP_2018     — code COICOP (ex: "01.1.3", "05.3.1.1") → notre "categorie"
        OBS_STATUS      — statut observation (ex: "A" = normal)
        SEASONAL_ADJUST — ajustement saisonnier (ex: "N" = non ajusté)
        GEO             — code pays (ex: "F" = France)
        GEO_OBJECT      — libellé pays (ex: "FRANCE")
        TPH_CPI         — type ménage (ex: "_T" = tous ménages)
        UNIT_MEASURE    — unité (ex: "IX" = indice, "RCH_A" = taux annuel)
        FREQ            — fréquence : "M"=mensuel, "A"=annuel, "Q"=trimestriel
        DECIMALS        — nombre de décimales (ex: 2)
        CONF_STATUS     — statut confidentialité (ex: "F" = libre)
        BASE_PER        — période de base (ex: "2025")
        TIME_PERIOD     — période d'observation (ex: "2024-01") → notre "date_obs"
        OBS_VALUE       — valeur de l'indice (ex: 113.35) → notre "valeur"
    - On filtre sur FREQ='M' (mensuel) → ~150 000 lignes utiles

Architecture ETL :
    1. EXTRACT  → téléchargement CSV → data/raw/csv_datagouv/ipc_raw.csv
    2. TRANSFORM → pivot wide→long, normalisation dates et catégories
                 → data/processed/csv_datagouv/ipc_clean.csv
    3. LOAD     → insertion dans PostgreSQL table datagouv_ipc

Table cible : datagouv_ipc (voir src/database/schema.sql)
Issue GitHub : #5 (C1 — source CSV)
=============================================================================
"""

import io
import os
import zipfile
import logging
import requests
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL as SAUrl
from dotenv import load_dotenv

# =============================================================================
# Chemins du projet
# =============================================================================
ROOT          = Path(__file__).parent.parent.parent
ENV_PATH      = ROOT / ".env"
RAW_DIR       = ROOT / "data" / "raw" / "csv_datagouv"
PROCESSED_DIR = ROOT / "data" / "processed" / "csv_datagouv"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(dotenv_path=ENV_PATH, override=True)

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
# Découverte dynamique de l'URL via l'API data.gouv.fr
#
# Plutôt que de hardcoder une URL qui change à chaque mise à jour INSEE,
# on interroge l'API data.gouv.fr pour trouver la ressource CSV courante
# dans le dataset IPC de l'INSEE.
#
# Organisation INSEE sur data.gouv.fr : 534fff75a3a7292c64a77de4
# Dataset IPC séries longues : 5c4e3ff706e3e76ee3e85be5
#
# Fallback : si l'API data.gouv.fr est indisponible, utiliser la variable
# d'environnement CSV_DATAGOUV_URL dans le .env.
# =============================================================================
# Recherche par mots-clés dans l'API data.gouv.fr — plus robuste qu'un ID hardcodé
DATAGOUV_SEARCH_URL = "https://www.data.gouv.fr/api/1/datasets/"
DATAGOUV_SEARCH_Q   = "indices prix consommation valeurs mensuelles"
CSV_URL_FALLBACK    = os.getenv("CSV_DATAGOUV_URL", "")

# =============================================================================
# Connexion PostgreSQL
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
def get_csv_url() -> str:
    """
    Trouve l'URL de téléchargement du CSV IPC via l'API data.gouv.fr.

    On interroge l'API data.gouv.fr pour obtenir la liste des ressources du
    dataset IPC et on retourne l'URL de la première ressource CSV trouvée.
    Cela évite de hardcoder une URL qui change à chaque mise à jour INSEE.

    Returns:
        str: URL de téléchargement du CSV IPC

    Raises:
        RuntimeError: si aucune ressource CSV n'est trouvée dans le dataset
    """
    # Fallback : URL manuelle dans .env (si data.gouv.fr est indisponible)
    if CSV_URL_FALLBACK:
        log.info(f"URL depuis .env (CSV_DATAGOUV_URL) : {CSV_URL_FALLBACK}")
        return CSV_URL_FALLBACK

    log.info(f"Recherche dataset IPC via API data.gouv.fr (q={DATAGOUV_SEARCH_Q!r})")
    r = requests.get(
        DATAGOUV_SEARCH_URL,
        params={"q": DATAGOUV_SEARCH_Q, "page_size": 10},
        timeout=30
    )
    r.raise_for_status()

    datasets = r.json().get("data", [])

    # On parcourt les datasets et leurs ressources pour trouver un CSV IPC
    for dataset in datasets:
        for resource in dataset.get("resources", []):
            fmt   = resource.get("format", "").lower()
            titre = resource.get("title", "").lower()
            url   = resource.get("url", "")
            if fmt == "csv" and any(k in titre for k in ("valeurs_mensuelles", "ipc", "prix")):
                log.info(f"Ressource trouvée : '{resource.get('title')}' → {url}")
                return url

    raise RuntimeError(
        "Aucune ressource CSV IPC trouvée sur data.gouv.fr. "
        "Ajouter CSV_DATAGOUV_URL dans le .env avec l'URL directe du fichier."
    )


def fetch_csv() -> pd.DataFrame:
    """
    Télécharge le CSV depuis data.gouv.fr/INSEE et le sauvegarde dans data/raw/.

    Le CSV INSEE est en format large (wide) :
        - Une ligne = une série IPC (ex: "Alimentation hors alcool et tabac")
        - Une colonne = une période mensuelle (ex: "janv.-96", "févr.-96"...)

    On sauvegarde d'abord le fichier brut SANS modification, puis on retourne
    le DataFrame pour l'étape de transformation.

    Returns:
        pd.DataFrame: CSV brut tel que téléchargé (format large)
    """
    log.info("=" * 60)
    log.info("ETAPE 1 — EXTRACT : téléchargement CSV INSEE data.gouv.fr")

    csv_url = get_csv_url()
    log.info(f"URL : {csv_url}")

    # timeout=60 — le fichier peut être volumineux (~5Mo)
    r = requests.get(csv_url, timeout=60)
    r.raise_for_status()

    # Le fichier téléchargé est un ZIP contenant deux fichiers :
    #   - DS_IPC_PRINC_data.csv     : les données (séries temporelles IPC)
    #   - DS_IPC_PRINC_metadata.csv : description des séries
    # On extrait le fichier data directement en mémoire avec zipfile + BytesIO
    zip_buffer = io.BytesIO(r.content)

    with zipfile.ZipFile(zip_buffer) as zf:
        # Liste les fichiers dans le ZIP pour log et vérification
        noms = zf.namelist()
        log.info(f"Fichiers dans le ZIP : {noms}")

        # On cherche le fichier de données en excluant explicitement les métadonnées
        # "metadata" contient "data" → on filtre sur le suffixe _data.csv
        nom_data = next(
            (n for n in noms if n.endswith("_data.csv") and "metadata" not in n.lower()),
            None
        )
        if nom_data is None:
            raise RuntimeError(f"Aucun fichier *_data.csv trouvé dans le ZIP. Contenu : {noms}")

        log.info(f"Lecture du fichier de données : {nom_data}")

        # Lecture des bytes du CSV depuis le ZIP
        csv_bytes = zf.read(nom_data)

    # Sauvegarde du CSV brut extrait dans data/raw/
    raw_path = RAW_DIR / "ipc_raw.csv"
    raw_path.write_bytes(csv_bytes)
    log.info(f"CSV brut sauvegardé dans : {raw_path}")

    # Détection de l'encodage : UTF-8 → cp1252 (Windows) → latin-1
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            texte = csv_bytes.decode(encoding)
            log.info(f"Encodage détecté : {encoding}")
            break
        except UnicodeDecodeError:
            continue

    # Lecture pandas avec on_bad_lines='skip' pour les lignes de métadonnées
    # en tête de fichier qui ont un nombre de colonnes différent
    df_raw = pd.read_csv(
        pd.io.common.StringIO(texte),
        sep=";",
        low_memory=False,
        on_bad_lines="skip"
    )

    log.info(f"CSV téléchargé : {df_raw.shape[0]} lignes × {df_raw.shape[1]} colonnes")
    log.info(f"Colonnes : {list(df_raw.columns)}")
    log.info(f"5 premières lignes :\n{df_raw.head().to_string()}")

    # Sauvegarde brute — nom fixe, écrase le précédent
    raw_path = RAW_DIR / "ipc_raw.csv"
    df_raw.to_csv(raw_path, index=False, encoding="utf-8")
    log.info(f"Données brutes sauvegardées dans : {raw_path}")

    return df_raw


# =============================================================================
# ÉTAPE 2 — TRANSFORM
# =============================================================================
def transform(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise le CSV INSEE (déjà en format long) pour correspondre au schéma
    de la table datagouv_ipc.

    Le fichier DS_IPC_PRINC_data.csv est DÉJÀ en format long — pas de pivot.
    Colonnes utiles :
        COICOP_2018  → categorie  (code COICOP ex: "01.1.3", "05.3.1.1")
        TIME_PERIOD  → date_obs   (ex: "2024-01" pour mensuel, "2024" pour annuel)
        OBS_VALUE    → valeur     (valeur de l'indice IPC)
        FREQ         → filtre sur 'M' (mensuel) uniquement
        UNIT_MEASURE → code_coicop (on le garde comme métadonnée)

    Args:
        df_raw (pd.DataFrame): données brutes avec 16 colonnes

    Returns:
        pd.DataFrame: données nettoyées prêtes pour PostgreSQL
    """
    log.info("=" * 60)
    log.info("ETAPE 2 — TRANSFORM : normalisation format long INSEE")

    df = df_raw.copy()

    # --- Filtre 1 : fréquence mensuelle ---
    # Le fichier contient FREQ='A' (annuel), 'M' (mensuel), 'Q' (trimestriel)
    freq_disponibles = df["FREQ"].unique()
    log.info(f"Fréquences disponibles : {freq_disponibles}")
    if "M" in freq_disponibles:
        df = df[df["FREQ"] == "M"].copy()
        log.info(f"Filtre FREQ='M' : {len(df)} lignes mensuelles")
    else:
        log.warning("Pas de données mensuelles — on garde toutes les fréquences")

    # --- Filtre 2 : unité = indice (IX) uniquement ---
    # UNIT_MEASURE peut être :
    #   "IX"    → indice IPC (ex: 119.17)  ← ce qu'on veut
    #   "RCH_A" → taux de variation annuel en % (ex: 2.4)  ← à exclure
    #   "RCH_M" → taux mensuel %  ← à exclure
    # Mélanger indices et taux dans la même colonne 'valeur' = non-sens
    unites_disponibles = df["UNIT_MEASURE"].unique()
    log.info(f"Unités disponibles : {unites_disponibles}")
    df = df[df["UNIT_MEASURE"] == "IX"].copy()
    log.info(f"Filtre UNIT_MEASURE='IX' : {len(df)} lignes indices")

    # --- Filtre 3 : indicateur = valeur d'indice (pas variation YoY) ---
    # IND_TYPE distingue la valeur brute de l'indice de ses dérivés :
    #   "IX"  → valeur de l'indice (ex: 62.81)  ← ce qu'on veut
    #   "YOY" → variation année-sur-année, parfois stockée avec UNIT_MEASURE="IX"
    #           (ex: 0.40 = variation de 0.40 point d'indice) — valeur parasite
    # Sans ce filtre, des lignes avec valeur 0.40 se glissent dans les indices.
    if "IND_TYPE" in df.columns:
        types_ind = df["IND_TYPE"].unique()
        log.info(f"IND_TYPE disponibles : {types_ind}")
        df = df[df["IND_TYPE"] == "IX"].copy()
        log.info(f"Filtre IND_TYPE='IX' : {len(df)} lignes valeurs d'indice")
    else:
        log.warning("Colonne IND_TYPE absente — filtre YoY ignoré")

    # --- Filtre 4 : France nationale uniquement (pas les DOM/COM) ---
    # GEO code le territoire géographique :
    #   "F"   → France métropolitaine (national)  ← ce qu'on veut
    #   "973" → Guyane, "971" → Guadeloupe, etc.
    # Sans ce filtre, la même catégorie COICOP pour le même mois
    # génère 3 lignes ou plus (une par territoire), causant des doublons
    # dans inflation_unified après l'agrégation.
    if "GEO" in df.columns:
        geos = df["GEO"].unique()
        log.info(f"GEO disponibles ({len(geos)}) : {geos[:20]}")
        df = df[df["GEO"] == "F"].copy()
        log.info(f"Filtre GEO='F' : {len(df)} lignes France nationale")
    else:
        log.warning("Colonne GEO absente — filtre territoire ignoré")

    # --- Filtre 5 : pas de subdivision par groupe produit ---
    # PRODUCT_GROUP filtre les sous-divisions par type de produit :
    #   "_Z"  → aucun groupe produit (agrégat pur COICOP)  ← ce qu'on veut
    #   "4005", "4037", etc. → sous-groupes spécifiques (alimentation bio, etc.)
    # Sans ce filtre, une catégorie COICOP peut avoir plusieurs lignes par mois
    # selon le découpage produit, générant là aussi des doublons.
    if "PRODUCT_GROUP" in df.columns:
        pg_vals = df["PRODUCT_GROUP"].unique()
        log.info(f"PRODUCT_GROUP disponibles ({len(pg_vals)}) : {pg_vals[:10]}")
        df = df[df["PRODUCT_GROUP"] == "_Z"].copy()
        log.info(f"Filtre PRODUCT_GROUP='_Z' : {len(df)} lignes agrégat COICOP pur")
    else:
        log.warning("Colonne PRODUCT_GROUP absente — filtre groupe produit ignoré")

    # --- Filtre 6 : base de référence ---
    # BASE_PER indique la période de base de l'indice.
    # Depuis 2025, l'INSEE a rebasé l'ensemble de ses séries de 2015 vers 2025.
    # Le fichier DATAGOUV ne contient donc plus de données en base 2015.
    # On log l'information mais on conserve les données (base 2025) plutôt que
    # de rejeter toute la source — l'évolution relative reste exploitable.
    # NOTE : cela crée une incompatibilité d'échelle avec les séries INSEE API
    # (base 2015=100) utilisées par le modèle Prophet. Voir specs_techniques.md.
    bases_disponibles = df["BASE_PER"].unique()
    log.info(f"Bases disponibles : {bases_disponibles}")
    if "2015" in [str(b) for b in bases_disponibles]:
        df = df[df["BASE_PER"].astype(str) == "2015"].copy()
        log.info(f"Filtre BASE_PER='2015' : {len(df)} lignes base 100=2015")
    else:
        log.warning(
            f"BASE_PER='2015' non trouvé (bases actuelles : {bases_disponibles}). "
            "INSEE a rebasé en 2025. Données conservées en base 2025. "
            "Incompatibilité d'échelle avec INSEE API (base 2015) — documentée."
        )

    # --- Renommage des colonnes vers notre convention ---
    df = df.rename(columns={
        "COICOP_2018":  "categorie",    # code COICOP ex: "01.1.3"
        "TIME_PERIOD":  "time_period",  # ex: "2024-01"
        "OBS_VALUE":    "valeur",       # valeur de l'indice base 100=2015
        "UNIT_MEASURE": "unite",        # "IX" (index) — gardé pour traçabilité
    })

    # --- Conversion des dates ---
    # TIME_PERIOD mensuel au format "YYYY-MM" → date PostgreSQL (1er du mois)
    df["date_obs"] = pd.to_datetime(
        df["time_period"].astype(str) + "-01",
        format="%Y-%m-%d",
        errors="coerce"
    )

    # --- Conversion des valeurs ---
    df["valeur"] = pd.to_numeric(df["valeur"], errors="coerce")

    # --- Nettoyage ---
    nb_avant = len(df)
    df = df.dropna(subset=["date_obs", "valeur", "categorie"])
    nb_apres = len(df)
    log.info(f"Nettoyage : {nb_avant} → {nb_apres} lignes valides "
             f"({nb_avant - nb_apres} supprimées)")

    # --- Sélection des colonnes finales ---
    df["source"] = "data.gouv.fr"
    df_clean = df[["date_obs", "valeur", "categorie", "source"]].copy()
    df_clean = df_clean.sort_values(["categorie", "date_obs"]).reset_index(drop=True)

    log.info(f"Aperçu :\n{df_clean.head(5).to_string()}")

    # Sauvegarde processed — nom fixe, écrase le précédent
    processed_path = PROCESSED_DIR / "ipc_clean.csv"
    df_clean.to_csv(processed_path, index=False, encoding="utf-8")
    log.info(f"Données nettoyées sauvegardées dans : {processed_path}")

    return df_clean


# =============================================================================
# ÉTAPE 3 — LOAD
# =============================================================================
def load_to_postgres(df_clean: pd.DataFrame, engine) -> None:
    """
    Insère le DataFrame nettoyé dans la table datagouv_ipc de PostgreSQL.

    Args:
        df_clean (pd.DataFrame): données nettoyées issues de transform()
        engine (Engine)        : connexion SQLAlchemy à PostgreSQL
    """
    log.info("=" * 60)
    log.info(f"ETAPE 3 — LOAD : insertion de {len(df_clean)} lignes dans datagouv_ipc")

    # Vider la table sans la recréer — préserve les contraintes UUID/index du schema.sql
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT to_regclass('public.datagouv_ipc')")).scalar()
        if exists:
            conn.execute(text("TRUNCATE TABLE datagouv_ipc CASCADE"))

    df_clean.to_sql(
        name="datagouv_ipc",
        con=engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500
    )

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM datagouv_ipc")).scalar()
        log.info(f"Vérification PostgreSQL : {count} lignes dans datagouv_ipc")


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================
def main():
    log.info("=" * 60)
    log.info("DEBUT COLLECTE CSV — Source data.gouv.fr INSEE (C1, issue #5)")
    log.info("=" * 60)

    try:
        df_raw   = fetch_csv()
        df_clean = transform(df_raw)

        log.info("Connexion à PostgreSQL (Docker port 5437)...")
        engine = create_engine(DB_URL)
        load_to_postgres(df_clean, engine)

        log.info("=" * 60)
        log.info("COLLECTE CSV TERMINÉE AVEC SUCCÈS")
        log.info("  Raw      : data/raw/csv_datagouv/ipc_raw.csv")
        log.info("  Processed: data/processed/csv_datagouv/ipc_clean.csv")
        log.info("  Base     : table datagouv_ipc dans PostgreSQL")
        log.info("=" * 60)

    except requests.exceptions.Timeout:
        log.error("Timeout : le serveur INSEE n'a pas répondu en 60 secondes")
        raise
    except requests.exceptions.HTTPError as e:
        log.error(f"Erreur HTTP : {e}")
        raise
    except Exception as e:
        log.error(f"Erreur inattendue : {e}")
        raise


if __name__ == "__main__":
    main()
