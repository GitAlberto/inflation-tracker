"""
=============================================================================
C8 — Prédictions Prophet — inflation-tracker
=============================================================================
Charge un modèle Prophet sauvegardé et génère des prédictions sur N mois.

Utilisation :
    # Prédictions 12 mois pour la catégorie ensemble
    python model/predict.py --categorie "00 - Ensemble" --horizon 12

    # Prédictions pour toutes les catégories
    python model/predict.py --all --horizon 12

Prérequis :
    Avoir exécuté model/train.py au préalable (génère les .pkl)

Issue GitHub : #14 (C8)
=============================================================================
"""

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd
import joblib                   # chargement des modèles Prophet sérialisés
from prophet import Prophet     # nécessaire pour désérialiser les .pkl

# Racine du projet = deux niveaux au-dessus de model/
ROOT      = Path(__file__).parent.parent
MODEL_DIR = Path(__file__).parent   # dossier contenant les .pkl et metrics.json


# =============================================================================
# Utilitaires
# =============================================================================

def slugify(name: str) -> str:
    """Convertit un nom de catégorie en slug pour retrouver le .pkl correspondant.

    Doit être identique à la fonction dans train.py.
    Exemple : '00 - Ensemble' → '00_ensemble'
    """
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)   # remplace les caractères spéciaux par _
    slug = slug.strip("_")                     # supprime les _ en début/fin
    return slug


def load_model(categorie: str) -> Prophet:
    """Charge le modèle Prophet sérialisé pour une catégorie donnée.

    Args:
        categorie : nom exact de la catégorie (ex: '00 - Ensemble')

    Returns:
        Modèle Prophet chargé depuis le .pkl correspondant

    Raises:
        FileNotFoundError : si le .pkl n'existe pas (train.py non exécuté)
    """
    slug       = slugify(categorie)                        # conversion en nom de fichier
    model_path = MODEL_DIR / f"prophet_{slug}.pkl"

    if not model_path.exists():
        raise FileNotFoundError(
            f"Modèle introuvable : {model_path}\n"
            f"→ Exécutez d'abord : python model/train.py"
        )

    model = joblib.load(model_path)   # désérialisation du modèle Prophet
    return model


def list_available() -> list[str]:
    """Retourne la liste des catégories disponibles depuis metrics.json."""
    metrics_path = MODEL_DIR / "metrics.json"

    if not metrics_path.exists():
        return []   # metrics.json absent = train.py non exécuté

    with open(metrics_path, encoding="utf-8") as f:
        metrics = json.load(f)

    return list(metrics.keys())   # les clés sont les noms de catégories


# =============================================================================
# Prédiction
# =============================================================================

def predict_one(categorie: str, horizon: int = 12) -> pd.DataFrame:
    """
    Génère les prédictions Prophet pour une catégorie sur N mois.

    Args:
        categorie : nom de la catégorie IPC (ex: '00 - Ensemble')
        horizon   : nombre de mois à prédire à partir de la dernière date connue

    Returns:
        DataFrame avec colonnes :
            ds           : date du premier jour du mois prédit
            yhat         : valeur IPC prédite (indice base 100 = 2015)
            yhat_lower   : borne basse intervalle de confiance 80%
            yhat_upper   : borne haute intervalle de confiance 80%
    """
    # Chargement du modèle Prophet depuis le .pkl
    model = load_model(categorie)

    # Réduction des échantillons Monte-Carlo pour les intervalles de confiance
    # Par défaut Prophet utilise 1000 échantillons → fragmentation mémoire sous Windows
    # 200 échantillons suffisent pour des IC robustes sur données mensuelles (12-36 pts)
    model.uncertainty_samples = 200

    # Création du DataFrame de dates futures : horizon mois supplémentaires
    # freq='MS' = Month Start : premier jour de chaque mois (cohérent avec les données INSEE)
    future = model.make_future_dataframe(periods=horizon, freq="MS")

    # Génération des prédictions sur tout l'historique + les dates futures
    forecast = model.predict(future)

    # Extraction uniquement des N dernières lignes (les prédictions futures)
    predictions = forecast.tail(horizon)[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    predictions = predictions.reset_index(drop=True)

    # Renommage pour clarté : 'ds' → 'date_pred'
    predictions = predictions.rename(columns={"ds": "date_pred"})

    return predictions


def predict_all(horizon: int = 12) -> dict[str, pd.DataFrame]:
    """
    Génère les prédictions pour toutes les catégories disponibles.

    Args:
        horizon : nombre de mois à prédire

    Returns:
        Dict {categorie: DataFrame de prédictions}
    """
    categories = list_available()   # liste depuis metrics.json

    if not categories:
        print("Aucun modèle disponible. Exécutez d'abord : python model/train.py")
        return {}

    results = {}
    for cat in categories:
        print(f"Prédiction : {cat}...")
        results[cat] = predict_one(cat, horizon)   # prédiction individuelle

    return results


# =============================================================================
# Affichage
# =============================================================================

def print_predictions(categorie: str, df: pd.DataFrame) -> None:
    """Affiche les prédictions dans le terminal de façon lisible."""
    print(f"\n{'='*60}")
    print(f"Prédictions Prophet — {categorie}")
    print(f"Horizon : {len(df)} mois")
    print(f"{'='*60}")
    print(f"{'Date':12} {'IPC prédit':>12} {'IC bas':>10} {'IC haut':>10}")
    print("-" * 50)

    for _, row in df.iterrows():
        # Formatage de chaque ligne : date, valeur centrale, bornes IC
        date = row["date_pred"].strftime("%Y-%m")
        print(f"{date:12} {row['yhat']:>12.2f} {row['yhat_lower']:>10.2f} {row['yhat_upper']:>10.2f}")

    # Résumé : variation totale sur la période prédite
    variation = df["yhat"].iloc[-1] - df["yhat"].iloc[0]
    print("-" * 50)
    print(f"Variation sur {len(df)} mois : {variation:+.2f} pts")


# =============================================================================
# Point d'entrée CLI
# =============================================================================

def main() -> None:
    """Interface en ligne de commande pour générer des prédictions."""
    parser = argparse.ArgumentParser(
        description="Génère des prédictions Prophet pour l'IPC France (C8)"
    )

    # Argument obligatoire : catégorie ou toutes
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--categorie", type=str,
        help='Catégorie IPC (ex: "00 - Ensemble")'
    )
    group.add_argument(
        "--all", action="store_true",
        help="Prédictions pour toutes les catégories disponibles"
    )

    # Horizon de prédiction (défaut : 12 mois)
    parser.add_argument(
        "--horizon", type=int, default=12,
        help="Nombre de mois à prédire (défaut : 12)"
    )

    args = parser.parse_args()

    if args.all:
        # Prédictions pour toutes les catégories
        results = predict_all(horizon=args.horizon)
        for cat, df in results.items():
            print_predictions(cat, df)
    else:
        # Prédiction pour une catégorie spécifique
        df = predict_one(args.categorie, horizon=args.horizon)
        print_predictions(args.categorie, df)


if __name__ == "__main__":
    main()
