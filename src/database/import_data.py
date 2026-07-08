"""
=============================================================================
C4 — Orchestrateur d'import — toutes sources → PostgreSQL
=============================================================================
Ce script est le point d'entrée unique pour alimenter toute la base de données.
Il enchaîne les 5 scripts de collecte dans l'ordre et produit un rapport final.

Comportement en cas d'erreur :
    Si une source plante, l'orchestrateur continue avec les suivantes.
    Le rapport final liste les succès et les échecs — aucune source silencieuse.

Utilisation :
    # Toutes les sources
    python src/database/import_data.py

    # Une seule source (pour déboguer ou mettre à jour indépendamment)
    python src/database/import_data.py --source ecb
    python src/database/import_data.py --source insee
    python src/database/import_data.py --source csv
    python src/database/import_data.py --source openfoodfacts
    python src/database/import_data.py --source eurostat

    # Plusieurs sources
    python src/database/import_data.py --source ecb insee

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
        "label":  "BDD simulée ECB (HICP 6 pays × 12 COICOP)",
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


def main(sources_selectionnees: list[str] | None = None) -> None:
    """
    Orchestre l'import de toutes les sources (ou d'un sous-ensemble).

    Args:
        sources_selectionnees: liste de clés de sources à lancer.
                               Si None → toutes les sources sont lancées.
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
    log.info("DEBUT IMPORT — inflation-tracker (C4, issue #9)")
    log.info(f"Sources : {[s['key'] for s in sources_a_lancer]}")
    log.info("=" * 60)

    rapports = []
    for source in sources_a_lancer:
        rapport = run_source(source)
        rapports.append(rapport)
        log.info("")   # ligne vide entre chaque source pour lisibilité

    print_rapport(rapports, debut_global)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Orchestrateur d'import inflation-tracker — C4"
    )
    parser.add_argument(
        "--source",
        nargs="+",   # accepte une ou plusieurs valeurs : --source ecb insee
        choices=[s["key"] for s in SOURCES],
        help="Source(s) à importer. Sans argument = toutes les sources.",
        metavar="SOURCE"
    )
    args = parser.parse_args()

    main(sources_selectionnees=args.source)
