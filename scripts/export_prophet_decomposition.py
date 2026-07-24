"""
Script utilitaire — export graphique décomposition Prophet
Génère l'image pour la veille C6 (section 2.4)

Lancement (depuis la racine du projet, venv activé) :
    python scripts/export_prophet_decomposition.py
"""

import sys
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")   # pas d'interface graphique — export fichier uniquement
import matplotlib.pyplot as plt

# Ajout de la racine au path pour les imports projet
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Chemin du modèle alimentation (le plus représentatif pour la veille)
MODEL_PATH = ROOT / "model" / "prophet_01_alimentation_et_boissons_non_alcoolis_es.pkl"
OUTPUT_PATH = ROOT / "docs" / "prophet_decomposition_alimentation.png"

print(f"Chargement du modèle : {MODEL_PATH.name}")
model = joblib.load(MODEL_PATH)

# Génération du forecast sur les données d'entraînement + 12 mois futurs
future = model.make_future_dataframe(periods=12, freq="MS")   # MS = Month Start
forecast = model.predict(future)

# Graphique de décomposition : tendance + saisonnalité annuelle + résidus
fig = model.plot_components(forecast)

# Titre global
fig.suptitle(
    "Décomposition Prophet — IPC Alimentation France (INSEE 2020-2025)\n"
    "Tendance · Saisonnalité annuelle",
    fontsize=11,
    fontweight="bold",
    y=1.01,
)

fig.tight_layout()
fig.savefig(OUTPUT_PATH, dpi=150, bbox_inches="tight")
print(f"Image exportée : {OUTPUT_PATH}")
