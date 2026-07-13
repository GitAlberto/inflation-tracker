"""
=============================================================================
C8 — Évaluation et visualisation — inflation-tracker
=============================================================================
Charge metrics.json et génère les preuves visuelles pour la compétence C8 :
    - Tableau des métriques par catégorie
    - Graphique prédiction 12 mois vs historique (catégorie '00 - Ensemble')
    - Décomposition Prophet (tendance + saisonnalité)

Utilisation :
    python model/evaluate.py

Prérequis :
    Avoir exécuté model/train.py au préalable

Issue GitHub : #14 (C8)
=============================================================================
"""

import json
import os
from pathlib import Path

import joblib                           # chargement du modèle .pkl
import matplotlib.dates as mdates      # formatage des dates sur l'axe X
import matplotlib.pyplot as plt        # graphiques
import pandas as pd
from dotenv import load_dotenv
from prophet import Prophet             # nécessaire pour la désérialisation joblib
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL as SAUrl

# Chemins du projet
ROOT       = Path(__file__).parent.parent   # racine du projet
MODEL_DIR  = Path(__file__).parent          # dossier model/
PREUVES    = ROOT / "preuves" / "technique" # dossier de sortie pour les preuves RNCP

load_dotenv(ROOT / ".env", override=True)

# Suppression des variables PostgreSQL système
for _v in ["PGPASSWORD", "PGUSER", "PGHOST", "PGPORT", "PGDATABASE", "PGPASSFILE"]:
    os.environ.pop(_v, None)

# Catégorie principale pour les graphiques de preuve
CATEGORIE_PRINCIPALE = "00 - Ensemble"


# =============================================================================
# Chargement
# =============================================================================

def load_metrics() -> dict:
    """Charge le fichier metrics.json généré par train.py."""
    metrics_path = MODEL_DIR / "metrics.json"

    if not metrics_path.exists():
        raise FileNotFoundError(
            "metrics.json introuvable — exécutez d'abord : python model/train.py"
        )

    with open(metrics_path, encoding="utf-8") as f:
        return json.load(f)   # dict {categorie: {MAE, RMSE, MAPE_pct, ...}}


def load_historical(categorie: str) -> pd.DataFrame:
    """Charge l'historique IPC depuis PostgreSQL pour une catégorie donnée."""
    db_url = SAUrl.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "inflation_tracker"),
    )
    engine = create_engine(db_url)

    with engine.connect() as conn:
        df = pd.read_sql(
            text("""
                SELECT date_obs, valeur
                FROM inflation_unified
                WHERE source    = 'INSEE'
                  AND pays      = 'FR'
                  AND categorie = :cat
                ORDER BY date_obs
            """),
            conn,
            params={"cat": categorie},
            parse_dates=["date_obs"],   # conversion automatique string → datetime
        )

    df["valeur"] = df["valeur"].astype(float)   # NUMERIC → float pour matplotlib
    return df


# =============================================================================
# Affichage du tableau de métriques
# =============================================================================

def print_metrics_table(metrics: dict) -> None:
    """Affiche le tableau des métriques par catégorie dans le terminal."""
    print("\n" + "=" * 70)
    print("MÉTRIQUES C8 — Prophet IPC France × 13 catégories (eval 2025)")
    print("=" * 70)
    print(f"{'Catégorie':40} {'MAE':>8} {'RMSE':>8} {'MAPE%':>7}")
    print("-" * 70)

    # Tri par MAE croissant pour mettre en avant les meilleures performances
    sorted_metrics = sorted(metrics.items(), key=lambda x: x[1]["MAE"])

    for cat, m in sorted_metrics:
        print(f"{cat[:40]:40} {m['MAE']:>8.4f} {m['RMSE']:>8.4f} {m['MAPE_pct']:>6.2f}%")

    # Calcul des moyennes pour résumé global
    maes  = [m["MAE"]      for m in metrics.values()]
    mapes = [m["MAPE_pct"] for m in metrics.values()]

    print("-" * 70)
    print(f"{'Moyenne (13 catégories)':40} {sum(maes)/len(maes):>8.4f}            {sum(mapes)/len(mapes):>6.2f}%")
    print("=" * 70)


# =============================================================================
# Graphique 1 — Prédictions 12 mois vs historique
# =============================================================================

def plot_predictions(metrics: dict) -> None:
    """
    Génère le graphique principal de prédiction Prophet pour C8.

    Affiche :
        - L'historique complet (2020-2025)
        - Les prédictions sur 12 mois futurs (2026)
        - L'intervalle de confiance 80%
        - Un encadré avec les métriques d'évaluation
    """
    # Chargement du modèle de production (entraîné sur données complètes 2020-2025)
    import re
    slug = CATEGORIE_PRINCIPALE.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    model_path = MODEL_DIR / f"prophet_{slug}.pkl"

    if not model_path.exists():
        print(f"Modèle {model_path.name} introuvable — exécutez train.py")
        return

    model = joblib.load(model_path)   # chargement du modèle Prophet sérialisé

    # Chargement de l'historique depuis PostgreSQL
    hist = load_historical(CATEGORIE_PRINCIPALE)

    # Génération des prédictions : 12 mois futurs après décembre 2025
    future   = model.make_future_dataframe(periods=12, freq="MS")
    forecast = model.predict(future)

    # Séparation historique connu / prédictions futures
    last_date    = hist["date_obs"].max()           # dernière date connue
    fc_future    = forecast[forecast["ds"] > last_date]   # seulement le futur
    fc_historical = forecast[forecast["ds"] <= last_date] # overlay sur l'historique

    # --- Construction du graphique ---
    fig, ax = plt.subplots(figsize=(16, 7))

    # Courbe historique réelle (trait plein bleu marine)
    ax.plot(hist["date_obs"], hist["valeur"],
            color="#1a3c5e", linewidth=2.5, label="Historique réel 2020-2025", zorder=3)

    # Overlay Prophet sur l'historique (lissage bayésien)
    ax.plot(fc_historical["ds"], fc_historical["yhat"],
            color="#7fb3d3", linewidth=1.2, linestyle="--",
            label="Ajustement Prophet (historique)", alpha=0.7)

    # Prédictions futures 12 mois (trait vert épais)
    ax.plot(fc_future["ds"], fc_future["yhat"],
            color="#27ae60", linewidth=2.5, marker="o", markersize=5,
            label="Prédiction Prophet 2026 (12 mois)", zorder=3)

    # Intervalle de confiance 80% sur la période future
    ax.fill_between(
        fc_future["ds"],
        fc_future["yhat_lower"],   # borne basse IC 80%
        fc_future["yhat_upper"],   # borne haute IC 80%
        alpha=0.2, color="#27ae60",
        label="Intervalle de confiance 80%"
    )

    # Ligne verticale séparant historique et prédictions
    ax.axvline(last_date, color="grey", linestyle=":", linewidth=1.5,
               label=f"Début prédiction ({last_date.strftime('%Y-%m')})")

    # Encadré de métriques (depuis metrics.json) en haut à droite
    m = metrics.get(CATEGORIE_PRINCIPALE, {})
    if m:
        stats_text = (
            f"Métriques eval 2025\n"
            f"MAE  = {m.get('MAE', 'N/A'):.4f}\n"
            f"RMSE = {m.get('RMSE', 'N/A'):.4f}\n"
            f"MAPE = {m.get('MAPE_pct', 'N/A'):.2f}%"
        )
        # Boîte de texte positionnée en bas à droite du graphique
        ax.text(0.98, 0.05, stats_text, transform=ax.transAxes,
                fontsize=10, verticalalignment="bottom", horizontalalignment="right",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.8))

    # Mise en forme
    ax.set_title(
        f"Prophet — IPC France '{CATEGORIE_PRINCIPALE}' — Prédiction 12 mois (2026)",
        fontsize=13, fontweight="bold"
    )
    ax.set_ylabel("Indice IPC (base 100 = 2015)")   # unité sur l'axe Y
    ax.legend(loc="upper left", fontsize=9)           # légende en haut à gauche
    ax.grid(alpha=0.3)                                 # grille légère
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))  # format YYYY-MM
    plt.xticks(rotation=30)                            # rotation pour lisibilité

    plt.tight_layout()

    # Sauvegarde pour le dossier de preuves RNCP
    out_path = PREUVES / "C8_predictions_prophet.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\nGraphique sauvegardé → {out_path}")
    plt.show()


# =============================================================================
# Graphique 2 — Décomposition Prophet (tendance + saisonnalité)
# =============================================================================

def plot_decomposition() -> None:
    """
    Génère la décomposition Prophet pour C8 : tendance + saisonnalité annuelle.

    Complément du graphique de prédiction — montre comment Prophet décompose
    la série en composantes interprétables (utile pour l'oral RNCP).
    """
    import re
    slug = CATEGORIE_PRINCIPALE.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    model_path = MODEL_DIR / f"prophet_{slug}.pkl"

    if not model_path.exists():
        print("Modèle introuvable pour la décomposition.")
        return

    model    = joblib.load(model_path)   # chargement du modèle
    future   = model.make_future_dataframe(periods=12, freq="MS")
    forecast = model.predict(future)     # prédiction nécessaire pour les composantes

    # Graphique natif Prophet : une ligne par composante (tendance, saisonnalité)
    fig = prophet_decomposition_plot(model, forecast)
    fig.set_size_inches(14, 8)
    plt.suptitle(
        f"Décomposition Prophet — IPC France '{CATEGORIE_PRINCIPALE}'",
        fontsize=13, fontweight="bold", y=1.01
    )
    plt.tight_layout()

    out_path = PREUVES / "C8_decomposition_prophet.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"Décomposition sauvegardée → {out_path}")
    plt.show()


def prophet_decomposition_plot(model, forecast):
    """Appel de la méthode de décomposition native Prophet."""
    return model.plot_components(forecast)


# =============================================================================
# Point d'entrée
# =============================================================================

def main() -> None:
    """Lance l'évaluation complète : métriques + graphiques de preuve C8."""
    print("=" * 60)
    print("EVALUATION C8 — Prophet IPC France (inflation-tracker)")
    print("=" * 60)

    # Chargement des métriques depuis metrics.json
    metrics = load_metrics()

    # Affichage du tableau de performance
    print_metrics_table(metrics)

    # Génération du graphique de prédiction 12 mois
    plot_predictions(metrics)

    # Génération de la décomposition tendance + saisonnalité
    plot_decomposition()


if __name__ == "__main__":
    main()
