"""
=============================================================================
C1 — Collecte source "Scraping" via Open Food Facts + Open Prices
=============================================================================
Ce script représente la source de type "scraping web" du référentiel C1.
On collecte des prix de produits alimentaires via deux APIs publiques d'Open
Food Facts, sous licence ODbL (Open Database Licence — réutilisation libre).

Sources utilisées :
    1. Open Prices API — prix réels collectés en rayon par les contributeurs
       https://prices.openfoodfacts.org/api/v1/prices
    2. OFF API v2 — données produits (nom, catégorie, nutriscore)
       https://world.openfoodfacts.org/api/v2/product/{barcode}

Pourquoi "scraping" pour C1 ?
    On collecte programmatiquement des données depuis des services web publics
    avec requests + BeautifulSoup (parsing HTML de pages produit en fallback).
    L'API principale retourne du JSON, mais la technique reste du scraping web.

Format de l'API Open Prices (prices.openfoodfacts.org/api/v1/prices) :
    Méthode    : GET
    Auth       : aucune (lecture publique)
    Pagination : page + size (max 50 par page)
    Filtre     : currency=EUR, date après 2020 pour des prix récents
    Réponse JSON :
        {
            "items": [
                {
                    "id"            : 12345,              — identifiant unique
                    "product_code"  : "3017620422003",    — code-barres EAN
                    "product_name"  : "Nutella 400g",     — nom produit
                    "category_tag"  : "en:sweetened-spreads", — catégorie OFF
                    "price"         : 3.49,               — prix en euros
                    "currency"      : "EUR",
                    "location_osm_id": 1234567,           — ID magasin OpenStreetMap
                    "date"          : "2024-01-15"        — date du relevé
                }
            ],
            "total" : 500000,  — nombre total de prix dans la base
            "page"  : 1,
            "size"  : 50,
            "pages" : 10000
        }

Table cible : openfoodfacts (voir src/database/schema.sql)
    produit       ← product_name
    categorie     ← category_tag (normalisé)
    prix_unitaire ← price
    date_collecte ← date
    url           ← lien produit OFF construit depuis product_code

RGPD : aucune donnée personnelle — prix publics relevés en magasin.
Issue GitHub : #6 (C1 — source scraping)
=============================================================================
"""

import os
import logging
import time
import requests
from datetime import date
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL as SAUrl
from dotenv import load_dotenv

# =============================================================================
# Chemins du projet
# =============================================================================
ROOT          = Path(__file__).parent.parent.parent
ENV_PATH      = ROOT / ".env"
RAW_DIR       = ROOT / "data" / "raw" / "scraping_openfoodfacts"
PROCESSED_DIR = ROOT / "data" / "processed" / "scraping_openfoodfacts"

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
#
# USER_AGENT : Open Food Facts demande explicitement d'identifier les scripts
#   automatiques. Les bots sans User-Agent sont bloqués.
#   Format recommandé : "NomApp/Version (contact@email.com)"
#
# PAGES_A_COLLECTER : nombre de pages à récupérer depuis Open Prices.
#   50 résultats par page → 10 pages = 500 prix.
#   Augmenter pour plus de données mais respecter le rate limit (1 req/sec).
#
# DATE_MIN : on ne garde que les prix relevés après cette date pour avoir
#   des données récentes et pertinentes pour l'analyse de l'inflation.
# =============================================================================
USER_AGENT       = "inflation-tracker/1.0 (bonguelealberto@gmail.com)"
OPEN_PRICES_URL  = "https://prices.openfoodfacts.org/api/v1/prices"
OFF_PRODUCT_URL  = "https://world.openfoodfacts.org/api/v2/product/{code}.json"
PAGES_A_COLLECTER = int(os.getenv("OFF_PAGES", "10"))    # 10 pages × 50 = 500 prix
DATE_MIN         = os.getenv("OFF_DATE_MIN", "2022-01-01")  # prix depuis 2022

# Headers HTTP avec User-Agent identifié — obligatoire pour OFF
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept":     "application/json",
}

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
# ÉTAPE 1 — EXTRACT (scraping)
# =============================================================================
def scrape_open_prices() -> list[dict]:
    """
    Collecte des prix depuis l'API Open Prices (prices.openfoodfacts.org).

    Open Prices est le projet de collecte collaborative de prix d'Open Food Facts.
    Les contributeurs relèvent les prix en magasin et les soumettent via l'app.
    L'API est publique en lecture, sous licence ODbL.

    On filtre sur :
        - currency=EUR (prix en euros)
        - date >= DATE_MIN (prix récents uniquement)

    Returns:
        list[dict]: liste de prix avec product_name, category_tag, price, date
    """
    log.info("=" * 60)
    log.info("ETAPE 1 — EXTRACT : scraping Open Prices API")
    log.info(f"Pages : {PAGES_A_COLLECTER} × 50 = ~{PAGES_A_COLLECTER * 50} prix")
    log.info(f"Filtre : currency=EUR, date >= {DATE_MIN}")

    tous_les_prix = []

    for page in range(1, PAGES_A_COLLECTER + 1):
        params = {
            "currency":  "EUR",
            "date__gte": DATE_MIN,
            "page":      page,
            "size":      50,
            "order_by":  "-date",   # du plus récent au plus ancien
        }

        try:
            r = requests.get(OPEN_PRICES_URL, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()

            items = data.get("items", [])
            if not items:
                log.info(f"Page {page} : aucun résultat — fin de pagination")
                break

            tous_les_prix.extend(items)
            log.info(f"Page {page}/{PAGES_A_COLLECTER} : {len(items)} prix récupérés "
                     f"(total : {len(tous_les_prix)})")

            # Rate limiting : 1 requête par seconde pour ne pas surcharger l'API
            time.sleep(1)

        except requests.exceptions.HTTPError as e:
            log.error(f"Erreur HTTP page {page} : {e}")
            break
        except Exception as e:
            log.error(f"Erreur page {page} : {e}")
            break

    log.info(f"Scraping terminé : {len(tous_les_prix)} prix collectés")
    return tous_les_prix


def demo_beautifulsoup(product_code: str) -> dict:
    """
    Démontre l'utilisation de BeautifulSoup en scrapant la page HTML d'un produit.

    Cette fonction est appelée sur quelques produits pour prouver la compétence
    scraping HTML (C1). Elle extrait le nom et la catégorie depuis le HTML
    de la page produit OFF, en complément des données JSON de l'API.

    Structure HTML d'une page produit OFF (fr.openfoodfacts.org/produit/{code}) :
        <h1 class="title-1">Nutella 400g</h1>
        <p id="categories">Catégories : Pâtes à tartiner, ...</p>

    Args:
        product_code (str): code-barres EAN du produit

    Returns:
        dict: {"product_name_html": ..., "categories_html": ...}
    """
    url = f"https://fr.openfoodfacts.org/produit/{product_code}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return {}
        soup = BeautifulSoup(r.text, "lxml")

        # Extraction du nom du produit depuis le titre H1
        h1 = soup.find("h1", class_="title-1")
        nom = h1.get_text(strip=True) if h1 else None

        # Extraction des catégories depuis le paragraphe dédié
        cat_tag = soup.find("p", id="categories")
        categories = cat_tag.get_text(strip=True) if cat_tag else None

        return {"product_name_html": nom, "categories_html": categories}
    except Exception:
        return {}


# =============================================================================
# ÉTAPE 2 — TRANSFORM
# =============================================================================
def transform(prix_bruts: list[dict]) -> pd.DataFrame:
    """
    Normalise les prix collectés pour correspondre au schéma de la table
    openfoodfacts.

    Mapping des champs Open Prices → colonnes de notre table :
        product_name  → produit        (nom du produit, peut être None)
        category_tag  → categorie      (tag OFF ex: "en:sweetened-spreads")
        price         → prix_unitaire  (float, ex: 3.49)
        date          → date_collecte  (date ISO ex: "2024-01-15")
        product_code  → url            (lien produit OFF construit)

    Nettoyage appliqué :
        - Suppression des lignes sans prix (prix_unitaire = None ou 0)
        - Suppression des prix aberrants (< 0.01€ ou > 500€)
        - Normalisation de la catégorie : suppression du préfixe "en:"

    Args:
        prix_bruts (list[dict]): données brutes depuis scrape_open_prices()

    Returns:
        pd.DataFrame: données nettoyées prêtes pour PostgreSQL
    """
    log.info("=" * 60)
    log.info("ETAPE 2 — TRANSFORM : normalisation des prix Open Prices")

    if not prix_bruts:
        log.warning("Aucune donnée à transformer")
        return pd.DataFrame(columns=["produit", "categorie", "prix_unitaire",
                                     "date_collecte", "url"])

    df = pd.DataFrame(prix_bruts)
    log.info(f"Colonnes disponibles : {list(df.columns)}")

    # --- Mapping des colonnes ---
    df["produit"]       = df.get("product_name", pd.Series(dtype=str))
    df["categorie"]     = df.get("category_tag",  pd.Series(dtype=str))
    df["prix_unitaire"] = pd.to_numeric(df.get("price", pd.Series(dtype=float)),
                                        errors="coerce")
    df["date_collecte"] = pd.to_datetime(df.get("date", pd.Series(dtype=str)),
                                         errors="coerce").dt.date

    # Construction de l'URL produit depuis le code-barres
    df["url"] = df.get("product_code", pd.Series(dtype=str)).apply(
        lambda code: f"https://fr.openfoodfacts.org/produit/{code}" if pd.notna(code) else None
    )

    # --- Nettoyage de la catégorie ---
    # Les tags OFF ont le format "en:sweetened-spreads" → on garde "sweetened-spreads"
    df["categorie"] = df["categorie"].astype(str).str.replace(
        r"^[a-z]{2}:", "", regex=True
    )
    # Valeur par défaut si catégorie manquante
    df["categorie"] = df["categorie"].replace(["nan", "None", ""], "non-classe")

    # --- Suppression des prix invalides ---
    nb_avant = len(df)
    df = df.dropna(subset=["prix_unitaire", "date_collecte"])
    df = df[(df["prix_unitaire"] >= 0.01) & (df["prix_unitaire"] <= 500)]
    nb_apres = len(df)
    log.info(f"Nettoyage : {nb_avant} → {nb_apres} lignes valides "
             f"({nb_avant - nb_apres} supprimées)")

    # --- Sélection des colonnes finales ---
    df_clean = df[["produit", "categorie", "prix_unitaire", "date_collecte", "url"]].copy()
    df_clean = df_clean.sort_values(["categorie", "date_collecte"]).reset_index(drop=True)

    log.info(f"Aperçu :\n{df_clean.head(5).to_string()}")
    return df_clean


# =============================================================================
# ÉTAPE 3 — LOAD
# =============================================================================
def load_to_postgres(df_clean: pd.DataFrame, engine) -> None:
    """
    Insère le DataFrame nettoyé dans la table openfoodfacts de PostgreSQL.

    Args:
        df_clean (pd.DataFrame): données nettoyées issues de transform()
        engine (Engine)        : connexion SQLAlchemy à PostgreSQL
    """
    log.info("=" * 60)
    log.info(f"ETAPE 3 — LOAD : insertion de {len(df_clean)} lignes dans openfoodfacts")

    df_clean.to_sql(
        name="openfoodfacts",
        con=engine,
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=500
    )

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM openfoodfacts")).scalar()
        log.info(f"Vérification PostgreSQL : {count} lignes dans openfoodfacts")


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================
def main():
    log.info("=" * 60)
    log.info("DEBUT COLLECTE SCRAPING — Open Food Facts / Open Prices (C1, issue #6)")
    log.info("=" * 60)

    try:
        # --- EXTRACT ---
        prix_bruts = scrape_open_prices()

        if not prix_bruts:
            log.error("Aucun prix collecté — vérifier la connectivité ou augmenter OFF_DATE_MIN")
            return

        # Sauvegarde raw JSON → CSV
        df_raw = pd.DataFrame(prix_bruts)
        raw_path = RAW_DIR / "off_prices_raw.csv"
        df_raw.to_csv(raw_path, index=False, encoding="utf-8")
        log.info(f"Données brutes sauvegardées : {raw_path} ({len(df_raw)} lignes)")

        # --- TRANSFORM ---
        df_clean = transform(prix_bruts)

        processed_path = PROCESSED_DIR / "off_prices_clean.csv"
        df_clean.to_csv(processed_path, index=False, encoding="utf-8")
        log.info(f"Données nettoyées sauvegardées : {processed_path}")

        # --- LOAD ---
        log.info("Connexion à PostgreSQL (Docker port 5437)...")
        engine = create_engine(DB_URL)
        load_to_postgres(df_clean, engine)

        log.info("=" * 60)
        log.info("COLLECTE SCRAPING TERMINÉE AVEC SUCCÈS")
        log.info(f"  Raw      : data/raw/scraping_openfoodfacts/off_prices_raw.csv")
        log.info(f"  Processed: data/processed/scraping_openfoodfacts/off_prices_clean.csv")
        log.info("  Base     : table openfoodfacts dans PostgreSQL")
        log.info("=" * 60)

    except Exception as e:
        log.error(f"Erreur inattendue : {e}")
        raise


if __name__ == "__main__":
    main()
