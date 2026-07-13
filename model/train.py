"""
=============================================================================
C8 — Entraînement Prophet — inflation-tracker
=============================================================================
Entraîne un modèle Prophet par catégorie INSEE sur les données IPC France.

Stratégie d'évaluation :
    1. Split train (2020-2024) / eval (2025) → métriques honnêtes sur données inconnues
    2. Réentraînement sur données complètes (2020-2025) → modèle de production

Sortie :
    model/prophet_{slug}.pkl  — modèle sérialisé par catégorie (non versionné)
    model/metrics.json        — métriques MAE/RMSE/MAPE par catégorie (versionné)

Issue GitHub : #14 (C8)
=============================================================================
"""

import os
import json
import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd
import joblib                                           # sérialisation des modèles Prophet
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL as SAUrl
from prophet import Prophet                             # modèle retenu après benchmark C7
from sklearn.metrics import mean_absolute_error, mean_squared_error

# =============================================================================
# Configuration
# =============================================================================

# Racine du projet = deux niveaux au-dessus de model/
ROOT     = Path(__file__).parent.parent
ENV_PATH = ROOT / ".env"
MODEL_DIR = Path(__file__).parent   # dossier model/ pour les .pkl et metrics.json

load_dotenv(dotenv_path=ENV_PATH, override=True)

# Suppression des variables PostgreSQL système (évite la surcharge du .env)
for _v in ["PGPASSWORD", "PGUSER", "PGHOST", "PGPORT", "PGDATABASE", "PGPASSFILE"]:
    os.environ.pop(_v, None)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Hyperparamètres Prophet — identiques au benchmark C7 pour cohérence
PROPHET_PARAMS = {
    "yearly_seasonality":     True,    # saisonnalité annuelle IPC (énergie hiver, alim été)
    "weekly_seasonality":     False,   # désactivé : données mensuelles uniquement
    "daily_seasonality":      False,   # désactivé : même raison
    "changepoint_prior_scale": 0.05,  # régularisation faible : évite surapprentissage sur ~60 pts
    "seasonality_mode":       "additive",  # additif : cohérent avec la nature de l'IPC base 100
}

# Date de séparation train / eval (même split que le benchmark C7)
EVAL_START = "2025-01-01"


# =============================================================================
# Connexion base de données
# =============================================================================

def get_engine():
    """Crée le moteur SQLAlchemy depuis les variables .env."""
    url = SAUrl.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "inflation_tracker"),
    )
    return create_engine(url)


# =============================================================================
# Chargement des données
# =============================================================================

def load_series(engine) -> dict[str, pd.DataFrame]:
    """
    Charge toutes les séries IPC INSEE depuis inflation_unified.

    Retourne un dict {categorie: DataFrame[date_obs, valeur]}
    trié par date pour chaque catégorie.
    """
    log.info("Chargement des séries INSEE depuis inflation_unified...")

    # Sélection des 13 catégories IPC France (source=INSEE uniquement)
    with engine.connect() as conn:
        df = pd.read_sql(
            text("""
                SELECT date_obs, categorie, valeur
                FROM inflation_unified
                WHERE source = 'INSEE'
                  AND pays   = 'FR'
                ORDER BY categorie, date_obs
            """),
            conn,
            parse_dates=["date_obs"],   # conversion automatique string → datetime
        )

    # Conversion NUMERIC PostgreSQL → float numpy (nécessaire pour Prophet)
    df["valeur"] = df["valeur"].astype(float)

    # Découpage en dict par catégorie pour traitement individuel
    series = {}
    for cat, grp in df.groupby("categorie"):
        series[cat] = grp[["date_obs", "valeur"]].reset_index(drop=True)

    log.info(f"{len(series)} catégories chargées : {list(series.keys())}")
    return series


# =============================================================================
# Utilitaires
# =============================================================================

def slugify(name: str) -> str:
    """Convertit un nom de catégorie en slug valide pour nom de fichier.

    Exemple : '00 - Ensemble' → '00_ensemble'
    """
    slug = name.lower()                         # tout en minuscules
    slug = re.sub(r"[^a-z0-9]+", "_", slug)    # remplace les caractères spéciaux par _
    slug = slug.strip("_")                      # supprime les _ en début/fin
    return slug


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Calcule MAE, RMSE et MAPE entre valeurs réelles et prédites."""
    mae  = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    # MAPE = moyenne des erreurs relatives en % (évite division par zéro)
    mape = float((np.abs((y_true - y_pred) / np.where(y_true != 0, y_true, 1)) * 100).mean())
    return {"MAE": round(mae, 4), "RMSE": round(rmse, 4), "MAPE_pct": round(mape, 2)}


# =============================================================================
# Entraînement
# =============================================================================

def train_one(df_cat: pd.DataFrame, categorie: str) -> tuple[Prophet, dict]:
    """
    Entraîne Prophet sur une catégorie IPC et retourne le modèle + métriques.

    Étapes :
        1. Split train / eval sur EVAL_START
        2. Entraînement sur train → évaluation sur eval (métriques honnêtes)
        3. Réentraînement sur données complètes (production)
        4. Retour du modèle de production et des métriques d'évaluation

    Args:
        df_cat     : DataFrame[date_obs, valeur] pour cette catégorie
        categorie  : nom de la catégorie (pour les logs)

    Returns:
        (modèle Prophet entraîné sur données complètes, dict de métriques)
    """
    # --- 1. Préparation du format Prophet (colonnes 'ds' et 'y' obligatoires) ---
    df_prophet = df_cat.rename(columns={"date_obs": "ds", "valeur": "y"})

    # --- 2. Split train / eval ---
    train = df_prophet[df_prophet["ds"] < EVAL_START].copy()   # 2020-2024 (60 pts)
    eval_ = df_prophet[df_prophet["ds"] >= EVAL_START].copy()  # 2025 (12 pts)

    # --- 3. Entraînement sur train pour calcul des métriques ---
    model_eval = Prophet(**PROPHET_PARAMS)
    model_eval.fit(train)   # ajustement bayésien sur les 60 points d'entraînement

    # Prédiction sur la période d'évaluation (12 mois 2025)
    future_eval = model_eval.make_future_dataframe(periods=len(eval_), freq="MS")
    forecast_eval = model_eval.predict(future_eval)

    # Extraction des prédictions sur la période de test uniquement
    preds_eval = forecast_eval[forecast_eval["ds"] >= EVAL_START]["yhat"].values

    # Calcul des métriques sur les valeurs réelles vs prédites
    metrics = compute_metrics(eval_["y"].values, preds_eval)
    metrics["n_train"] = len(train)   # nb points d'entraînement (info utile pour le jury)
    metrics["n_eval"]  = len(eval_)   # nb points d'évaluation

    log.info(f"  [{categorie}] eval → MAE={metrics['MAE']} RMSE={metrics['RMSE']} MAPE={metrics['MAPE_pct']}%")

    # --- 4. Réentraînement sur données complètes (2020-2025) pour production ---
    model_prod = Prophet(**PROPHET_PARAMS)
    model_prod.fit(df_prophet)   # toutes les données disponibles pour de meilleures prédictions

    return model_prod, metrics


# =============================================================================
# Boucle principale
# =============================================================================

def main() -> None:
    """Entraîne Prophet sur les 13 catégories INSEE et sauvegarde modèles + métriques."""
    log.info("=" * 60)
    log.info("DEBUT ENTRAINEMENT C8 — Prophet × 13 catégories INSEE")
    log.info("=" * 60)

    # Connexion PostgreSQL et chargement des 13 séries
    engine = get_engine()
    series = load_series(engine)

    all_metrics = {}   # accumulateur : {categorie: {MAE, RMSE, MAPE, ...}}

    for categorie, df_cat in series.items():
        log.info(f"Entraînement : {categorie} ({len(df_cat)} points)")

        # Entraînement et calcul des métriques pour cette catégorie
        model, metrics = train_one(df_cat, categorie)

        # Sauvegarde du modèle sérialisé avec joblib (non versionné dans Git)
        slug       = slugify(categorie)                              # nom de fichier sûr
        model_path = MODEL_DIR / f"prophet_{slug}.pkl"
        joblib.dump(model, model_path)                               # sérialisation binaire
        log.info(f"  Modèle sauvegardé → {model_path.name}")

        # Stockage des métriques avec le nom de catégorie comme clé
        all_metrics[categorie] = metrics

    # --- Sauvegarde du fichier de métriques (versionné dans Git) ---
    metrics_path = MODEL_DIR / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2, ensure_ascii=False)

    log.info("=" * 60)
    log.info(f"ENTRAINEMENT TERMINE — {len(all_metrics)} modèles sauvegardés")
    log.info(f"Métriques exportées → {metrics_path}")
    log.info("=" * 60)

    # Résumé des métriques dans les logs pour vérification rapide
    for cat, m in all_metrics.items():
        log.info(f"  {cat[:35]:35} MAE={m['MAE']:6.4f}  MAPE={m['MAPE_pct']:5.2f}%")


if __name__ == "__main__":
    main()
