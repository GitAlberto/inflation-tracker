"""
=============================================================================
C17 — Page 4 : Métriques Modèle Prophet — inflation-tracker
=============================================================================
Vue d'ensemble de la performance du modèle Prophet par catégorie IPC.
MAE, RMSE, MAPE — tableau et graphiques interactifs.

Issue GitHub : #19 (C17)
=============================================================================
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api_client import get_health, get_metrics
from app.theme import inject_theme

st.set_page_config(page_title="Métriques Modèle", page_icon="📈", layout="wide")
inject_theme()

st.title("📈 Métriques du Modèle Prophet")
st.caption("Évaluation honnête — split train 2020-2024 / eval 2025 (12 mois held-out) · 12 catégories INSEE")

# =============================================================================
# Statut API en sidebar
# =============================================================================

with st.sidebar:
    st.header("Statut API")
    h = get_health()
    if h:
        st.success("✅ API modèle (8002) OK")
        st.caption(f"Version : {h.get('version', 'N/A')}")
    else:
        st.error("❌ API modèle indisponible")
        st.markdown("**Démarrez l'API :**")
        st.code("uvicorn api.model.main:app --port 8002", language="bash")
        st.stop()

    st.divider()
    st.subheader("À propos de l'évaluation")
    st.markdown("""
**Split temporel strict :**
- Train : Jan 2020 → Dec 2024 (60 mois)
- Eval : Jan 2025 → Dec 2025 (12 mois)

**Métriques calculées :**
- **MAE** : Erreur absolue moyenne
- **RMSE** : Racine de l'erreur quadratique moyenne
- **MAPE** : Erreur relative (%)
    """)

# =============================================================================
# Chargement des métriques
# =============================================================================

@st.cache_data(ttl=300)
def _load_metrics():
    """Charge les métriques de tous les modèles depuis l'API."""
    return get_metrics()


metriques = _load_metrics()

if not metriques:
    st.error("Impossible de charger les métriques. L'API modèle doit être opérationnelle.")
    st.stop()

# Construction du DataFrame à partir du dict retourné par l'API
rows = []
for cat, m in metriques["metrics"].items():
    rows.append({
        "Catégorie":   cat,
        "MAE":         m["MAE"],
        "RMSE":        m["RMSE"],
        "MAPE (%)":    m["MAPE_pct"],
        "N train":     m["n_train"],
        "N eval":      m["n_eval"],
    })

df_metrics = pd.DataFrame(rows).sort_values("MAE")   # tri par MAE croissant

# =============================================================================
# KPIs globaux
# =============================================================================

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(
        "MAE médiane (toutes catégories)",
        f"{df_metrics['MAE'].median():.4f} pts IPC",
        help="La moitié des catégories a une MAE inférieure à cette valeur"
    )
with col2:
    st.metric(
        "MAPE médiane",
        f"{df_metrics['MAPE (%)'].median():.2f} %",
        help="Erreur relative médiane sur la période d'évaluation 2025"
    )
with col3:
    best_cat = df_metrics.iloc[0]
    st.metric(
        "Meilleure MAE",
        f"{best_cat['MAE']:.4f}",
        delta=best_cat["Catégorie"][:30],
        delta_color="off",
    )
with col4:
    worst_cat = df_metrics.iloc[-1]
    st.metric(
        "MAE la plus élevée",
        f"{worst_cat['MAE']:.4f}",
        delta=worst_cat["Catégorie"][:30],
        delta_color="off",
    )

st.divider()

# =============================================================================
# Graphique 1 — MAE par catégorie (barres horizontales)
# =============================================================================

st.subheader("MAE par catégorie (période eval 2025)")

# Seuil rouge à 5 pts IPC — au-delà, le modèle est considéré peu fiable
SEUIL_MAE = 5.0

# Couleur des barres : vert si MAE ≤ seuil, rouge sinon
bar_colors = [
    "#27ae60" if mae <= SEUIL_MAE else "#e74c3c"
    for mae in df_metrics["MAE"]
]

fig_mae = go.Figure()
fig_mae.add_trace(go.Bar(
    x=df_metrics["MAE"],
    y=df_metrics["Catégorie"],
    orientation="h",                 # barres horizontales pour lisibilité des labels
    marker_color=bar_colors,
    hovertemplate=(
        "<b>%{y}</b><br>"
        "MAE : %{x:.4f} pts IPC<br>"
        "<extra></extra>"
    ),
))

# Ligne verticale matérialisant le seuil critique
fig_mae.add_vline(
    x=SEUIL_MAE,
    line_dash="dash",
    line_color="#e74c3c",
    annotation_text=f"Seuil alerte : {SEUIL_MAE} pts",
    annotation_position="top right",
)

fig_mae.update_layout(
    height=500,
    xaxis_title="MAE (pts IPC)",
    yaxis_title="",
    plot_bgcolor="white",
    xaxis=dict(gridcolor="#f0f0f0"),
    yaxis=dict(gridcolor="#f0f0f0"),
    showlegend=False,
)

st.plotly_chart(fig_mae, use_container_width=True)

# =============================================================================
# Graphique 2 — MAE vs RMSE par catégorie (barres groupées)
# =============================================================================

st.subheader("MAE vs RMSE par catégorie")
st.caption(
    "Quand la barre RMSE (orange) dépasse nettement la MAE (violet), "
    "le modèle fait des erreurs ponctuelles importantes — pics d'inflation difficiles à capturer."
)

df_sorted = df_metrics.sort_values("MAE", ascending=True)

fig_compare = go.Figure()

fig_compare.add_trace(go.Bar(
    name="MAE",
    y=df_sorted["Catégorie"],
    x=df_sorted["MAE"],
    orientation="h",
    marker_color="#8d57f6",
    hovertemplate="<b>%{y}</b><br>MAE : %{x:.4f} pts IPC<extra></extra>",
))

fig_compare.add_trace(go.Bar(
    name="RMSE",
    y=df_sorted["Catégorie"],
    x=df_sorted["RMSE"],
    orientation="h",
    marker_color="#e99842",
    hovertemplate="<b>%{y}</b><br>RMSE : %{x:.4f} pts IPC<extra></extra>",
))

fig_compare.update_layout(
    barmode="group",
    height=500,
    xaxis_title="Erreur (pts IPC)",
    yaxis_title="",
    plot_bgcolor="white",
    xaxis=dict(gridcolor="#f0f0f0"),
    yaxis=dict(gridcolor="#f0f0f0", automargin=True),
    legend=dict(orientation="h", y=-0.15),
    margin=dict(l=10),
)

st.plotly_chart(fig_compare, use_container_width=True)

# =============================================================================
# Tableau complet des métriques
# =============================================================================

st.subheader("Tableau complet des métriques")

# Formatage pour affichage
df_display = df_metrics.copy()
df_display["MAE"]      = df_display["MAE"].round(4)
df_display["RMSE"]     = df_display["RMSE"].round(4)
df_display["MAPE (%)"] = df_display["MAPE (%)"].round(2)

st.dataframe(
    df_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "MAE":      st.column_config.NumberColumn("MAE (pts IPC)", format="%.4f"),
        "RMSE":     st.column_config.NumberColumn("RMSE (pts IPC)", format="%.4f"),
        "MAPE (%)": st.column_config.NumberColumn("MAPE (%)", format="%.2f%%"),
        "N train":  st.column_config.NumberColumn("N train"),
        "N eval":   st.column_config.NumberColumn("N eval (2025)"),
    },
)

# Légende
st.info(
    f"**Période évaluation :** Jan 2025 → Dec 2025 "
    f"({metriques.get('eval_period', '2025')}) · "
    f"**{metriques.get('nb_categories', 13)} catégories** évaluées · "
    "Vert : MAE ≤ 5 pts IPC · Rouge : MAE > 5 pts IPC"
)
