"""
=============================================================================
C1 — Collecte source "API REST" via INSEE BDM (Banque de Données Macro-économiques)
=============================================================================
Ce script représente la source de type "API REST" du référentiel C1.
On collecte les Indices des Prix à la Consommation (IPC) via l'API SDMX
de l'INSEE (Institut National de la Statistique et des Études Économiques).

Source utilisée :
    API INSEE BDM — https://api.insee.fr/series/BDM/V1/
    Licence  : Licence Ouverte / Open Licence 2.0 (Etalab)
    Format   : SDMX-XML 2.1 (Statistical Data and Metadata eXchange)

Pourquoi "API REST" pour C1 ?
    L'INSEE publie ses statistiques via une API REST standardisée SDMX.
    Les séries IPC sont publiques (pas de token requis), mais l'API supporte
    OAuth2 Client Credentials pour les données restreintes. Ce script
    implémente le flux complet OAuth2 avec repli sur l'accès public si le
    token est absent ou inaccessible.

Format de l'API INSEE BDM :
    Endpoint : GET /series/BDM/V1/data/SERIES_BDM/{idbanks}
    idbanks  : identifiants de série INSEE, séparés par '+' pour multi-requête
    Params   : startPeriod (YYYY-MM), endPeriod (YYYY-MM), lastNObservations
    Auth     : Bearer token OAuth2 (optionnel pour données publiques)
    Réponse  : SDMX-XML 2.1 StructureSpecificData

Structure XML retournée (namespace dynamique, accès par nom local) :
    <DataSet>
        <Series IDBANK="001759970" FREQ="M" TITLE_FR="IPC Base 2015 - Ensemble">
            <Obs TIME_PERIOD="2024-01" OBS_VALUE="119.17" OBS_STATUS="A"/>
            <Obs TIME_PERIOD="2023-12" OBS_VALUE="118.90" OBS_STATUS="A"/>
            ...
        </Series>
        ...
    </DataSet>

    OBS_STATUS : "A" = définitif, "P" = provisoire, "E" = estimé

Séries IPC collectées (Base 2015, France entière, Ensemble des ménages, brut) :
    Toutes ont LAST_UPDATE="2026-01-15" — données jusqu'à fin 2025.
    Découverte via : /data/IPC-2015/M.IPC.SO.00+01+...+12.SO.INDICE.ENSEMBLE.FE.SO.BRUT.2015.TRUE
    COICOP 00 — Ensemble                          : 001759970
    COICOP 01 — Alimentation et boissons           : 001763417
    COICOP 02 — Boissons alcoolisées, tabac        : 001763491
    COICOP 03 — Habillement et chaussures          : 001763508
    COICOP 04 — Logement, eau, gaz, électricité    : 001763529
    COICOP 05 — Meubles, articles de ménage        : 001763565
    COICOP 06 — Santé                              : 001763620
    COICOP 07 — Transports                         : 001763641
    COICOP 08 — Communications                     : 001763683
    COICOP 09 — Loisirs et culture                 : 001763698
    COICOP 10 — Enseignement                       : 001763774
    COICOP 11 — Restaurants et hôtels              : 001763781
    Agrégat  — Ensemble hors énergie               : 001763851

Table cible : insee_ipc (voir src/database/schema.sql)
    date_obs      ← TIME_PERIOD + "-01" converti en DATE
    valeur        ← OBS_VALUE (indice IPC, base 100 = 2015)
    categorie     ← libellé court normalisé (ex : "01 - Alimentation…")
    sous_categorie← TITLE_FR complet retourné par l'API
    idbank        ← IDBANK (identifiant série INSEE)
    source        ← 'INSEE'

RGPD : aucune donnée personnelle — statistiques publiques INSEE.
Issue GitHub : #8 (C1 — source API REST avec authentification OAuth2)
=============================================================================
"""

import os
import logging
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

import requests
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL as SAUrl
from dotenv import load_dotenv

# =============================================================================
# Chemins du projet
# =============================================================================
ROOT          = Path(__file__).parent.parent.parent
ENV_PATH      = ROOT / ".env"
RAW_DIR       = ROOT / "data" / "raw" / "api_insee"
PROCESSED_DIR = ROOT / "data" / "processed" / "api_insee"

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
BDM_DATA_URL = "https://api.insee.fr/series/BDM/V1/data/SERIES_BDM"
TOKEN_URL    = "https://portail-api.insee.fr/token"

# Séries IPC Base 2015 — France entière — Ensemble des ménages — Brut
# Découverte via dataflow IPC-2015 avec filtre COICOP 00-12, NATURE=INDICE
# Toutes actives : LAST_UPDATE="2026-01-15", données jusqu'en 2025-12
IDBANKS_IPC: dict[str, str] = {
    "001759970": "00 - Ensemble",
    "001763417": "01 - Alimentation et boissons non alcoolisées",
    "001763491": "02 - Boissons alcoolisées, tabac et stupéfiants",
    "001763508": "03 - Articles d'habillement et chaussures",
    "001763529": "04 - Logement, eau, gaz, électricité et autres combustibles",
    "001763565": "05 - Meubles, articles de ménage et entretien courant du foyer",
    "001763620": "06 - Santé",
    "001763641": "07 - Transports",
    "001763683": "08 - Communications",
    "001763698": "09 - Loisirs et culture",
    "001763774": "10 - Enseignement",
    "001763781": "11 - Restaurants et hôtels",
    "001763851": "Ensemble hors énergie",
}

START_PERIOD = os.getenv("INSEE_START_PERIOD", "2020-01")
END_PERIOD   = os.getenv("INSEE_END_PERIOD", "")  # vide = jusqu'à aujourd'hui

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
# Authentification OAuth2
# =============================================================================
def get_oauth2_token() -> str | None:
    """
    Obtient un token OAuth2 via le flux Client Credentials INSEE.

    L'API BDM est accessible sans token pour les données IPC publiques.
    Le token est requis uniquement pour les séries restreintes (données
    entreprises, séries premium). Cette implémentation démontre la
    compétence C1 (OAuth2 sur API REST) en incluant le flux complet avec
    repli gracieux sur l'accès public.

    Flux OAuth2 Client Credentials :
        POST https://portail-api.insee.fr/token
        Authorization: Basic base64(client_id:client_secret)
        Body: grant_type=client_credentials

    Returns:
        str | None : Bearer token si authentification réussie, None sinon
    """
    client_id     = os.getenv("INSEE_CLIENT_ID")
    client_secret = os.getenv("INSEE_CLIENT_SECRET")

    if not client_id or not client_secret:
        log.info("INSEE_CLIENT_ID / SECRET absents du .env — accès public (sans token)")
        return None

    try:
        r = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            timeout=15,
        )
        if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("application/json"):
            token = r.json().get("access_token")
            log.info("Token OAuth2 INSEE obtenu")
            return token
        log.warning(f"Token OAuth2 non obtenu (HTTP {r.status_code}) — accès public utilisé")
        return None
    except Exception as exc:
        log.warning(f"OAuth2 inaccessible ({exc}) — accès public utilisé")
        return None


# =============================================================================
# ÉTAPE 1 — EXTRACT
# =============================================================================
def extract_bdm(idbanks: dict[str, str], token: str | None = None) -> str:
    """
    Interroge l'API INSEE BDM pour les séries IPC demandées.

    Toutes les séries sont récupérées en une seule requête HTTP grâce au
    mécanisme multi-idbank de l'API : les identifiants sont joints par '+'.
    L'API retourne un SDMX-XML contenant un élément <Series> par idbank,
    chacun suivi de ses <Obs> (observations mensuelles).

    Paramètres de filtre temporel :
        startPeriod : inclus  (ex: "2020-01")
        endPeriod   : inclus  (ex: "2025-12") — si vide, toutes les données récentes

    Args:
        idbanks (dict) : mapping idbank → libellé catégorie
        token   (str | None) : Bearer token OAuth2, ou None pour accès public

    Returns:
        str : réponse XML brute de l'API INSEE

    Raises:
        requests.HTTPError : si l'API retourne un code d'erreur HTTP
    """
    log.info("=" * 60)
    log.info("ETAPE 1 — EXTRACT : appel API INSEE BDM")
    log.info(f"Séries demandées : {len(idbanks)} idbanks")
    log.info(f"Période          : {START_PERIOD} → {END_PERIOD or 'aujourd\'hui'}")

    idbanks_str = "+".join(idbanks.keys())
    url = f"{BDM_DATA_URL}/{idbanks_str}"

    params: dict[str, str] = {"startPeriod": START_PERIOD}
    if END_PERIOD:
        params["endPeriod"] = END_PERIOD

    headers: dict[str, str] = {"Accept": "application/xml"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    log.info(f"GET {url}")
    r = requests.get(url, params=params, headers=headers, timeout=60)
    r.raise_for_status()

    log.info(f"Réponse : HTTP {r.status_code} — {len(r.content):,} octets reçus")
    return r.text


# =============================================================================
# ÉTAPE 2 — TRANSFORM
# =============================================================================
def transform(xml_brut: str, idbanks: dict[str, str]) -> pd.DataFrame:
    """
    Parse le SDMX-XML INSEE et construit un DataFrame normalisé.

    Stratégie de parsing :
        Le SDMX-XML 2.1 utilise un namespace dynamique basé sur le dataflow
        (ex: urn:sdmx:...Dataflow=FR1:SERIES_BDM(1.0):ObsLevelDim:TIME_PERIOD).
        On extrait le nom local de chaque balise (après '}') pour s'abstraire
        des namespaces changeants entre deux appels.

    Nettoyage :
        - Ignorer les observations sans OBS_VALUE
        - Ignorer OBS_STATUS = "M" (manquant) ou "L" (confidentiel)
        - Convertir TIME_PERIOD "YYYY-MM" en DATE "YYYY-MM-01"
        - Catégorie courte extraite du dictionnaire IDBANKS_IPC

    Args:
        xml_brut (str) : réponse XML brute de extract_bdm()
        idbanks  (dict): mapping idbank → libellé court catégorie

    Returns:
        pd.DataFrame : colonnes date_obs, valeur, categorie, sous_categorie,
                       idbank, source
    """
    log.info("=" * 60)
    log.info("ETAPE 2 — TRANSFORM : parsing SDMX-XML INSEE")

    root = ET.fromstring(xml_brut)

    rows: list[dict] = []
    nb_series = 0
    nb_obs_ok = 0
    nb_ignores = 0
    series_attrs: dict = {}

    for elem in root.iter():
        # Nom local sans namespace (ex : "{urn:sdmx:...}Series" → "Series")
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        if local == "Series":
            series_attrs = dict(elem.attrib)
            nb_series += 1

        elif local == "Obs" and series_attrs:
            obs_status  = elem.attrib.get("OBS_STATUS", "A")
            obs_value   = elem.attrib.get("OBS_VALUE")
            time_period = elem.attrib.get("TIME_PERIOD")

            # Statuts exclus : M = manquant, L = confidentiel
            if obs_status in ("M", "L") or not obs_value or not time_period:
                nb_ignores += 1
                continue

            idbank = series_attrs.get("IDBANK", "")
            title  = series_attrs.get("TITLE_FR", "")

            categorie = idbanks.get(idbank, _short_label(title))

            try:
                date_obs = datetime.strptime(time_period + "-01", "%Y-%m-%d").date()
            except ValueError:
                nb_ignores += 1
                continue

            rows.append({
                "date_obs":       date_obs,
                "valeur":         float(obs_value),
                "categorie":      categorie,
                "sous_categorie": title,
                "idbank":         idbank,
                "source":         "INSEE",
            })
            nb_obs_ok += 1

    log.info(f"Séries parsées       : {nb_series}")
    log.info(f"Observations valides : {nb_obs_ok}")
    log.info(f"Ignorées             : {nb_ignores}")

    if not rows:
        log.warning("Aucune observation extraite du XML")
        return pd.DataFrame(columns=["date_obs", "valeur", "categorie",
                                     "sous_categorie", "idbank", "source"])

    df = pd.DataFrame(rows)
    df = df.sort_values(["idbank", "date_obs"]).reset_index(drop=True)

    log.info(f"Aperçu :\n{df.head(5).to_string()}")
    log.info(f"Plage de dates : {df['date_obs'].min()} → {df['date_obs'].max()}")
    return df


def _short_label(title_fr: str) -> str:
    """
    Extrait un libellé court depuis le TITLE_FR INSEE si l'idbank n'est pas
    dans IDBANKS_IPC. Supprime le préfixe commun et le suffixe "Séries arrêtées".

    Exemple :
        "IPC - Base 2015 - ... - France - Nomenclature Coicop : 01 - Alimentation…"
        → "01 - Alimentation…"
    """
    if not title_fr:
        return "inconnu"
    if "Nomenclature Coicop : " in title_fr:
        return (title_fr.split("Nomenclature Coicop : ")[-1]
                .replace(" - Séries arrêtées", "").strip())
    parts = title_fr.split(" - France - ")
    if len(parts) > 1:
        return parts[-1].replace(" - Séries arrêtées", "").strip()
    return title_fr[:100]


# =============================================================================
# ÉTAPE 3 — LOAD
# =============================================================================
def load_to_postgres(df_clean: pd.DataFrame, engine) -> None:
    """
    Insère le DataFrame nettoyé dans la table insee_ipc de PostgreSQL.

    Args:
        df_clean (pd.DataFrame) : données issues de transform()
        engine   (Engine)       : connexion SQLAlchemy à PostgreSQL
    """
    log.info("=" * 60)
    log.info(f"ETAPE 3 — LOAD : insertion de {len(df_clean)} lignes dans insee_ipc")

    df_clean.to_sql(
        name="insee_ipc",
        con=engine,
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=500,
    )

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM insee_ipc")).scalar()
        log.info(f"Vérification PostgreSQL : {count} lignes dans insee_ipc")


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================
def main() -> None:
    log.info("=" * 60)
    log.info("DEBUT COLLECTE API INSEE BDM — IPC France (C1, issue #8)")
    log.info("=" * 60)

    try:
        # --- OAuth2 (optionnel — repli public si absent) ---
        token = get_oauth2_token()

        # --- EXTRACT ---
        xml_brut = extract_bdm(IDBANKS_IPC, token=token)

        raw_path = RAW_DIR / "insee_ipc_raw.xml"
        raw_path.write_text(xml_brut, encoding="utf-8")
        log.info(f"XML brut sauvegardé : {raw_path}")

        # --- TRANSFORM ---
        df_clean = transform(xml_brut, IDBANKS_IPC)

        if df_clean.empty:
            log.error("Aucune donnée transformée — vérifier les idbanks ou la plage de dates")
            return

        processed_path = PROCESSED_DIR / "insee_ipc_clean.csv"
        df_clean.to_csv(processed_path, index=False, encoding="utf-8")
        log.info(f"CSV nettoyé sauvegardé : {processed_path}")

        # --- LOAD ---
        log.info("Connexion à PostgreSQL (Docker port 5437)...")
        engine = create_engine(DB_URL)
        load_to_postgres(df_clean, engine)

        log.info("=" * 60)
        log.info("COLLECTE INSEE API TERMINÉE AVEC SUCCÈS")
        log.info(f"  Raw      : data/raw/api_insee/insee_ipc_raw.xml")
        log.info(f"  Processed: data/processed/api_insee/insee_ipc_clean.csv")
        log.info(f"  Base     : table insee_ipc dans PostgreSQL")
        log.info(f"  Lignes   : {len(df_clean)}")
        log.info("=" * 60)

    except Exception as exc:
        log.error(f"Erreur inattendue : {exc}")
        raise


if __name__ == "__main__":
    main()
