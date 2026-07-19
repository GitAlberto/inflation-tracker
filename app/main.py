"""
=============================================================================
C17 — Application Streamlit — inflation-tracker
=============================================================================
Page d'accueil : KPIs, statut des APIs, présentation du projet.

Lancement :
    streamlit run app/main.py

Issue GitHub : #19 (C17)
=============================================================================
"""

import sys
from pathlib import Path

import streamlit as st

# Ajout de la racine au sys.path pour les imports app.* depuis pages/
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api_client import get_health as model_health
from app.data_client import get_health as data_health, get_inflation
from app.theme import inject_theme

# =============================================================================
# Configuration de la page
# =============================================================================

st.set_page_config(
    page_title="Inflation Tracker France",   # titre de l'onglet navigateur
    page_icon="📈",                           # icône de l'onglet
    layout="wide",                            # pleine largeur
    initial_sidebar_state="expanded",         # sidebar ouverte par défaut
)
inject_theme()

# =============================================================================
# Sidebar — navigation et statut APIs
# =============================================================================

with st.sidebar:
    st.title("📈 Inflation Tracker")
    st.caption("Projet B3 RNCP — Développeur IA")
    st.divider()

    # Statut des deux APIs
    st.subheader("Statut des services")

    # API data (port 8001)
    h_data = data_health()
    if h_data:
        st.success("✅ API data (8001)")
    else:
        st.error("❌ API data (8001)")

    # API modèle (port 8002)
    h_model = model_health()
    if h_model:
        st.success("✅ API modèle (8002)")
    else:
        st.error("❌ API modèle (8002)")

    st.divider()
    st.caption("Sources : INSEE · BCE · Eurostat\nOpenFoodFacts · data.gouv.fr")

# =============================================================================
# Contenu principal — accueil
# =============================================================================

st.title("📈 Inflation Tracker France")
st.markdown(
    "**Comprendre et prédire l'évolution des prix** — "
    "données publiques INSEE, BCE, Eurostat agrégées et modélisées par Prophet."
)
st.divider()

# =============================================================================
# KPIs — inflation France par année
# =============================================================================

st.subheader("Inflation France — points clés")

# Chargement des données INSEE pour les KPIs annuels
@st.cache_data(ttl=300)   # cache 5 minutes — évite re-fetch à chaque interaction
def _load_kpis():
    """Charge les données IPC Ensemble pour construire les KPIs."""
    result = get_inflation(
        pays="FR", source="INSEE",
        categorie="00",          # catégorie "00 - Ensemble"
        limit=1000,
    )
    if not result or not result["data"]:
        return {}

    # Conversion en dict {année: liste de valeurs} pour calculer les moyennes
    by_year: dict[int, list[float]] = {}
    for row in result["data"]:
        year = int(row["date_obs"][:4])            # extraction de l'année YYYY-MM-DD
        val  = float(row["valeur"])                # NUMERIC PostgreSQL → float
        by_year.setdefault(year, []).append(val)

    # Calcul de la valeur IPC moyenne par année (proxy de l'indice annuel)
    return {yr: round(sum(v) / len(v), 2) for yr, v in by_year.items()}

kpis = _load_kpis()

col1, col2, col3, col4 = st.columns(4)

# Fonction utilitaire pour formater la variation entre deux années
def _delta(kpis, y1, y2):
    if y1 in kpis and y2 in kpis:
        return f"{kpis[y2] - kpis[y1]:+.2f} pts IPC"
    return "N/A"

with col1:
    # IPC 2022 — pic post-COVID
    val_2022 = kpis.get(2022, "—")
    st.metric(
        label="IPC moyen 2022",
        value=f"{val_2022}" if isinstance(val_2022, float) else val_2022,
        delta="pic inflation post-COVID",
        delta_color="inverse",   # rouge car hausse = mauvais pour le consommateur
    )

with col2:
    val_2023 = kpis.get(2023, "—")
    st.metric(
        label="IPC moyen 2023",
        value=f"{val_2023}" if isinstance(val_2023, float) else val_2023,
        delta=_delta(kpis, 2022, 2023),
        delta_color="inverse",
    )

with col3:
    val_2024 = kpis.get(2024, "—")
    st.metric(
        label="IPC moyen 2024",
        value=f"{val_2024}" if isinstance(val_2024, float) else val_2024,
        delta=_delta(kpis, 2023, 2024),
        delta_color="normal",    # vert car baisse = désinflation
    )

with col4:
    val_2025 = kpis.get(2025, "—")
    st.metric(
        label="IPC moyen 2025",
        value=f"{val_2025}" if isinstance(val_2025, float) else val_2025,
        delta=_delta(kpis, 2024, 2025),
        delta_color="normal",
    )

st.divider()

# =============================================================================
# Présentation du projet
# =============================================================================

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🗂️ Le projet")
    st.markdown("""
Le kebab coûtait **3,50 €** en 2019. Il en coûte **7 €** en 2026.

**Inflation Tracker** agrège 5 sources de données publiques pour rendre
l'inflation lisible et prédire son évolution par catégorie de produit.

**Pipeline :**
- 5 sources → PostgreSQL → API REST → Modèle Prophet → Cette application
    """)

with col_b:
    st.subheader("🧭 Navigation")
    st.markdown("""
| Page | Contenu |
|---|---|
| 📊 **Analyse Historique** | Évolution IPC multi-sources, multi-pays |
| 🔍 **Analyse par Catégorie** | Deep-dive, stats, heatmap, YoY |
| 🔮 **Prédictions** | Prophet 12 mois + intervalle de confiance |
| 📈 **Métriques Modèle** | MAE par catégorie, performance Prophet |
    """)

st.divider()
st.caption("Sources : INSEE BDM · BCE HICP · Eurostat bulk · OpenFoodFacts · data.gouv.fr")
