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
@st.cache_data(ttl=60)   # cache 60s — ne pas bloquer sur un échec de démarrage
def _load_kpis():
    """Charge les données IPC Ensemble pour construire les KPIs.

    Lève RuntimeError si l'API est indisponible — @st.cache_data ne met PAS
    en cache les exceptions, donc le prochain rerun retente automatiquement.
    """
    result = get_inflation(source="INSEE", categorie="00", limit=1000)
    if result is None:
        raise RuntimeError("API data indisponible")
    if not result["data"]:
        return {}

    # Conversion en dict {année: liste de valeurs} pour calculer les moyennes
    by_year: dict[int, list[float]] = {}
    for row in result["data"]:
        year = int(row["date_obs"][:4])            # extraction de l'année YYYY-MM-DD
        val  = float(row["valeur"])                # NUMERIC PostgreSQL → float
        by_year.setdefault(year, []).append(val)

    # Calcul de la valeur IPC moyenne par année (proxy de l'indice annuel)
    return {yr: round(sum(v) / len(v), 2) for yr, v in by_year.items()}


try:
    kpis = _load_kpis()
except Exception:
    kpis = {}

if not kpis:
    st.info("⏳ Données KPI en cours de chargement — rechargez la page dans quelques secondes.")

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
Le kebab coûtait **5,00 €** en 2019. Il en coûte **10,00 €** en 2026.

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

# =============================================================================
# Tableau d'impact — l'inflation en euros, pour tout le monde
# =============================================================================

st.subheader("💡 L'inflation en euros — ce que ça change vraiment")

if kpis:
    years     = sorted(kpis.keys())
    ref_year  = min(y for y in years if y >= 2020)
    cur_year  = max(years)
    ipc_start = kpis.get(ref_year)
    ipc_end   = kpis.get(cur_year)

    if ipc_start and ipc_end:
        delta_total = ipc_end - ipc_start
        pct_total   = delta_total / ipc_start * 100
        st.caption(
            f"IPC Ensemble (INSEE) — {ref_year} : **{ipc_start:.1f} pts** → "
            f"{cur_year} : **{ipc_end:.1f} pts** — soit **+{delta_total:.1f} pts IPC "
            f"(+{pct_total:.1f} %)** sur la période."
        )

        import pandas as pd
        budgets = [300, 500, 800, 1_200, 2_000]
        rows = []
        for b in budgets:
            budget_now = round(b * (ipc_end / ipc_start))
            hausse     = budget_now - b
            rows.append({
                f"Budget en {ref_year}": f"{b} €/mois",
                f"Budget équivalent en {cur_year}": f"{budget_now} €/mois",
                "Hausse mensuelle": f"+{hausse} €",
                "Hausse annuelle": f"+{hausse * 12} €",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Mini tableau explicatif — détail du calcul pas à pas sur l'exemple 500 €
        st.markdown("**Comment ce calcul fonctionne — exemple avec 500 €/mois :**")
        exemple_budget = 500
        exemple_now    = round(exemple_budget * (ipc_end / ipc_start))
        exemple_hausse = exemple_now - exemple_budget
        etapes = [
            {
                "Étape": "① Hausse de l'IPC",
                "Calcul": f"IPC {cur_year} − IPC {ref_year} = {ipc_end:.1f} − {ipc_start:.1f}",
                "Résultat": f"+{delta_total:.1f} pts IPC",
            },
            {
                "Étape": "② % d'augmentation",
                "Calcul": f"({delta_total:.1f} / {ipc_start:.1f}) × 100",
                "Résultat": f"+{pct_total:.1f} %",
            },
            {
                "Étape": "③ Nouveau budget",
                "Calcul": f"500 € × ({ipc_end:.1f} / {ipc_start:.1f})",
                "Résultat": f"{exemple_now} €/mois",
            },
            {
                "Étape": "④ Hausse en €",
                "Calcul": f"{exemple_now} € − 500 €",
                "Résultat": f"+{exemple_hausse} €/mois — soit +{exemple_hausse * 12} €/an",
            },
        ]
        st.dataframe(pd.DataFrame(etapes), use_container_width=True, hide_index=True)

st.divider()
st.caption("Sources : INSEE BDM · BCE HICP · Eurostat bulk · OpenFoodFacts · data.gouv.fr")
