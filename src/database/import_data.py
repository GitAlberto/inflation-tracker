"""
=============================================================================
C4 — Orchestrateur d'import — toutes sources → PostgreSQL
=============================================================================
Point d'entrée unique pour alimenter toute la base de données.
Enchaîne dans l'ordre :
    1. Nettoyage des anciens fichiers data/raw/ et data/processed/
    2. Collecte des 5 sources (ECB, INSEE, CSV/DATAGOUV, OpenFoodFacts, Eurostat)
    3. Agrégation et normalisation → inflation_unified

Comportement en cas d'erreur :
    Si une source plante, l'orchestrateur continue avec les suivantes.
    Le rapport final liste les succès et les échecs — aucune source silencieuse.

Utilisation :
    # Pipeline complet (nettoyage + collecte + agrégation)
    python src/database/import_data.py

    # Sans nettoyage préalable des fichiers (garde les anciens raw/processed)
    python src/database/import_data.py --no-clean

    # Une seule source (pour déboguer ou mettre à jour indépendamment)
    python src/database/import_data.py --source ecb
    python src/database/import_data.py --source insee
    python src/database/import_data.py --source csv
    python src/database/import_data.py --source openfoodfacts
    python src/database/import_data.py --source eurostat

    # Sans relancer l'agrégation à la fin
    python src/database/import_data.py --no-aggregate

Chaque script de collecte reste également lançable seul :
    python src/collect/load_ecb_to_db.py
    python src/collect/collect_insee_api.py
    etc.

Issue GitHub : #9 (C4)
=============================================================================
"""

import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Ajout de la racine du projet au PYTHONPATH pour les imports relatifs
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# =============================================================================
# Registre des sources
# Chaque entrée définit :
#   - key        : identifiant court pour --source
#   - label      : nom affiché dans le rapport
#   - module     : chemin Python du module à importer
#   - status     : "ready" = script existant / "pending" = pas encore créé
# =============================================================================
SOURCES = [
    {
        "key":    "ecb",
        "label":  "BDD simulée ECB (HICP 6 pays × 13 COICOP, indice base 2015)",
        "module": "src.collect.load_ecb_to_db",
        "status": "ready",
    },
    {
        "key":    "insee",
        "label":  "API INSEE BDM (IPC France par catégorie)",
        "module": "src.collect.collect_insee_api",
        "status": "ready",
    },
    {
        "key":    "csv",
        "label":  "CSV data.gouv.fr (séries longues IPC)",
        "module": "src.collect.collect_csv",
        "status": "ready",
    },
    {
        "key":    "openfoodfacts",
        "label":  "Scraping Open Food Facts (prix alimentaires)",
        "module": "src.collect.scrape_openfoodfacts",
        "status": "ready",
    },
    {
        "key":    "eurostat",
        "label":  "Big Data Eurostat + PySpark (27 pays × 30 ans)",
        "module": "src.collect.collect_eurostat_spark",
        "status": "ready",
    },
]


def clean_output_files() -> None:
    """
    Supprime tous les fichiers dans data/raw/ et data/processed/.

    Conserve les dossiers et les README.md — seuls les fichiers de données
    (CSV, JSON, GZ, parquet...) sont supprimés pour repartir d'un état propre.
    On ne supprime jamais les dossiers eux-mêmes : certains scripts vérifient
    leur existence avant de créer des fichiers.
    """
    DATA_DIR = ROOT / "data"
    extensions_donnees = {".csv", ".json", ".gz", ".parquet", ".tsv", ".xml", ".zip"}

    total = 0
    for sous_dossier in ["raw", "processed"]:
        dossier = DATA_DIR / sous_dossier
        if not dossier.exists():
            continue
        # Parcours récursif — supprime uniquement les fichiers de données
        for fichier in dossier.rglob("*"):
            if fichier.is_file() and fichier.suffix.lower() in extensions_donnees:
                fichier.unlink()
                log.info(f"  Supprimé : {fichier.relative_to(ROOT)}")
                total += 1

    log.info(f"Nettoyage terminé — {total} fichier(s) supprimé(s)")


def run_aggregate() -> dict:
    """Lance aggregate_clean.py après la collecte pour normaliser inflation_unified."""
    log.info("[aggregate] Lancement de src.aggregate.aggregate_clean...")
    debut = time.time()
    try:
        import importlib
        module = importlib.import_module("src.aggregate.aggregate_clean")
        module.main()
        duree = round(time.time() - debut, 1)
        log.info(f"[aggregate] OK en {duree}s")
        return {"key": "aggregate", "label": "Agrégation → inflation_unified",
                "status": "OK", "duree": duree, "message": ""}
    except Exception as e:
        duree = round(time.time() - debut, 1)
        log.error(f"[aggregate] ERREUR après {duree}s : {e}")
        return {"key": "aggregate", "label": "Agrégation → inflation_unified",
                "status": "ERREUR", "duree": duree, "message": str(e)}


def run_source(source: dict) -> dict:
    """
    Lance le script de collecte d'une source et retourne un rapport.

    Importe dynamiquement le module de la source puis appelle sa fonction
    main(). Si le module n'existe pas encore (status=pending), retourne un
    rapport SKIP propre sans faire planter l'orchestrateur.

    Args:
        source (dict): entrée du registre SOURCES

    Returns:
        dict: rapport avec clés status ("OK" | "ERREUR" | "SKIP"), durée, message
    """
    key   = source["key"]
    label = source["label"]

    # --- Source non encore implémentée ---
    if source["status"] == "pending":
        log.warning(f"[{key}] SKIP — script non encore créé (Phase 2)")
        return {"key": key, "label": label, "status": "SKIP", "duree": 0,
                "message": "script non implémenté (Phase 2)"}

    # --- Import dynamique du module ---
    log.info(f"[{key}] Lancement de {source['module']}...")
    debut = time.time()

    try:
        import importlib
        module = importlib.import_module(source["module"])

        # Chaque script de collecte expose une fonction main()
        if not hasattr(module, "main"):
            raise AttributeError(f"Le module {source['module']} n'a pas de fonction main()")

        module.main()

        duree = round(time.time() - debut, 1)
        log.info(f"[{key}] OK en {duree}s")
        return {"key": key, "label": label, "status": "OK", "duree": duree, "message": ""}

    except Exception as e:
        duree = round(time.time() - debut, 1)
        # On log l'erreur mais on NE lève PAS l'exception → l'orchestrateur continue
        log.error(f"[{key}] ERREUR après {duree}s : {e}")
        return {"key": key, "label": label, "status": "ERREUR", "duree": duree,
                "message": str(e)}


def print_rapport(rapports: list[dict], debut_global: float) -> None:
    """
    Affiche le rapport final de l'orchestrateur.

    Args:
        rapports       : liste des rapports par source
        debut_global   : timestamp de début pour calcul durée totale
    """
    duree_totale = round(time.time() - debut_global, 1)

    log.info("")
    log.info("=" * 60)
    log.info("RAPPORT IMPORT — inflation-tracker")
    log.info(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"Durée totale : {duree_totale}s")
    log.info("=" * 60)

    icones = {"OK": "✅", "ERREUR": "❌", "SKIP": "⏭️ "}
    for r in rapports:
        icone = icones.get(r["status"], "?")
        ligne = f"  {icone} [{r['key']:15}] {r['status']:6} ({r['duree']}s) — {r['label']}"
        if r["message"]:
            ligne += f"\n               └─ {r['message']}"
        log.info(ligne)

    nb_ok     = sum(1 for r in rapports if r["status"] == "OK")
    nb_erreur = sum(1 for r in rapports if r["status"] == "ERREUR")
    nb_skip   = sum(1 for r in rapports if r["status"] == "SKIP")

    log.info("=" * 60)
    log.info(f"  {nb_ok} OK   {nb_erreur} ERREUR   {nb_skip} SKIP")
    log.info("=" * 60)

    if nb_erreur > 0:
        log.warning("Des sources ont échoué — vérifier les logs ci-dessus.")


def main(
    sources_selectionnees: list[str] | None = None,
    do_clean: bool = True,
    do_aggregate: bool = True,
) -> None:
    """
    Orchestre le pipeline complet : nettoyage → collecte → agrégation.

    Args:
        sources_selectionnees : clés des sources à lancer (None = toutes).
        do_clean              : supprime data/raw/ et data/processed/ avant collecte.
        do_aggregate          : lance aggregate_clean.py après la collecte.
    """
    debut_global = time.time()

    # Filtre les sources demandées
    if sources_selectionnees:
        sources_a_lancer = [s for s in SOURCES if s["key"] in sources_selectionnees]
        cles_inconnues   = set(sources_selectionnees) - {s["key"] for s in SOURCES}
        if cles_inconnues:
            log.error(f"Sources inconnues : {cles_inconnues}")
            log.info(f"Sources disponibles : {[s['key'] for s in SOURCES]}")
            sys.exit(1)
    else:
        sources_a_lancer = SOURCES

    log.info("=" * 60)
    log.info("DEBUT PIPELINE — inflation-tracker (C4, issue #9)")
    log.info(f"Sources   : {[s['key'] for s in sources_a_lancer]}")
    log.info(f"Nettoyage : {'OUI' if do_clean else 'NON (--no-clean)'}")
    log.info(f"Agrégation: {'OUI' if do_aggregate else 'NON (--no-aggregate)'}")
    log.info("=" * 60)

    # --- Étape 0 : nettoyage des anciens fichiers output ---
    if do_clean:
        log.info("ÉTAPE 0 — Nettoyage data/raw/ et data/processed/")
        clean_output_files()
        log.info("")

    # --- Étapes 1-N : collecte des sources ---
    rapports = []
    for source in sources_a_lancer:
        rapport = run_source(source)
        rapports.append(rapport)
        log.info("")

    # --- Étape finale : agrégation et normalisation → inflation_unified ---
    if do_aggregate:
        log.info("ÉTAPE FINALE — Agrégation et normalisation → inflation_unified")
        rapport_agg = run_aggregate()
        rapports.append(rapport_agg)
        log.info("")

    print_rapport(rapports, debut_global)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline complet inflation-tracker : nettoyage → collecte → agrégation"
    )
    parser.add_argument(
        "--source",
        nargs="+",
        choices=[s["key"] for s in SOURCES],
        help="Source(s) à importer. Sans argument = toutes les sources.",
        metavar="SOURCE",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Ne pas supprimer data/raw/ et data/processed/ avant la collecte.",
    )
    parser.add_argument(
        "--no-aggregate",
        action="store_true",
        help="Ne pas lancer aggregate_clean.py après la collecte.",
    )
    args = parser.parse_args()

    main(
        sources_selectionnees=args.source,
        do_clean=not args.no_clean,
        do_aggregate=not args.no_aggregate,
    )
