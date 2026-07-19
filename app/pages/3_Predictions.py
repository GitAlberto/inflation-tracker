"""
=============================================================================
C17 — Page 3 : Prédictions Prophet — inflation-tracker
=============================================================================
Prédictions IPC 1-36 mois par catégorie avec intervalle de confiance 80%.
Combine historique réel (API data) et prédictions (API modèle).

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

from app.api_client import get_categories, get_metrics_categorie, predict_categorie
from app.data_client import get_inflation
from app.theme import inject_theme

st.set_page_config(page_title="Prédictions Prophet", page_icon="🔮", layout="wide")
inject_theme()

st.title("🔮 Prédictions Prophet — IPC France")
st.caption("Modèle Prophet Meta entraîné sur données INSEE 2020-2025 · Évaluation honnête split train/test 2025")

# =============================================================================
# Sidebar — paramètres de prédiction
# =============================================================================

with st.sidebar:
    st.header("Paramètres")

    # Liste des catégories disponibles (depuis l'API modèle)
    cats = get_categories()
    if not cats:
        st.error("API modèle indisponible.\nDémarrez : uvicorn api.model.main:app --port 8002")
        st.stop()

    categorie = st.selectbox("Catégorie IPC", cats, index=0)

    horizon = st.slider(
        "Horizon de prédiction (mois)", min_value=1, max_value=36, value=12,
        help="Nombre de mois à prédire à partir de décembre 2025"
    )

    st.divider()

    # Métriques du modèle pour la catégorie sélectionnée
    m = get_metrics_categorie(categorie)
    if m:
        st.subheader("Métriques eval 2025")
        st.metric("MAE",  f"{m['MAE']:.4f} pts IPC")
        st.metric("RMSE", f"{m['RMSE']:.4f} pts IPC")
        st.metric("MAPE", f"{m['MAPE_pct']:.2f} %")
        st.caption(f"Entraîné sur {m['n_train']} pts · Évalué sur {m['n_eval']} pts")

# =============================================================================
# Chargement des données
# =============================================================================

@st.cache_data(ttl=300)
def _load_historique(categorie):
    """Charge l'historique IPC INSEE pour la catégorie sélectionnée."""
    result = get_inflation(
        pays="FR", source="INSEE",
        categorie=categorie[:2],     # code 2 chiffres
        limit=1000,
    )
    if not result or not result["data"]:
        return pd.DataFrame()
    df = pd.DataFrame(result["data"])
    df["date_obs"] = pd.to_datetime(df["date_obs"])
    df["valeur"]   = df["valeur"].astype(float)
    return df.sort_values("date_obs")


@st.cache_data(ttl=60)   # cache 1 minute — les prédictions sont lentes (chargement .pkl)
def _load_predictions(categorie, horizon):
    """Appelle l'API modèle pour obtenir les prédictions Prophet."""
    return predict_categorie(categorie, horizon=horizon)


# Affichage d'un spinner pendant le chargement des prédictions
with st.spinner(f"Génération des prédictions Prophet pour '{categorie}'..."):
    df_hist = _load_historique(categorie)
    pred    = _load_predictions(categorie, horizon)

if pred is None:
    st.error("L'API modèle n'a pas pu générer de prédictions. Vérifiez qu'elle est démarrée.")
    st.stop()

# Conversion des prédictions en DataFrame
df_pred = pd.DataFrame(pred["predictions"])
df_pred["date_pred"] = pd.to_datetime(df_pred["date_pred"])

# =============================================================================
# Graphique principal — historique + prédictions + IC
# =============================================================================

fig = go.Figure()

# Courbe historique réelle
if not df_hist.empty:
    fig.add_trace(go.Scatter(
        x=df_hist["date_obs"],
        y=df_hist["valeur"],
        name="Historique réel (INSEE)",
        mode="lines",
        line=dict(color="#1a3c5e", width=2.5),
        hovertemplate="Date : %{x|%Y-%m}<br>IPC réel : %{y:.2f}<extra></extra>",
    ))

# Intervalle de confiance 80% (area fill entre lower et upper)
fig.add_trace(go.Scatter(
    x=pd.concat([df_pred["date_pred"], df_pred["date_pred"].iloc[::-1]]),
    y=pd.concat([df_pred["yhat_upper"], df_pred["yhat_lower"].iloc[::-1]]),
    fill="toself",
    fillcolor="rgba(39, 174, 96, 0.15)",   # vert semi-transparent
    line=dict(color="rgba(255,255,255,0)"),  # bordure invisible
    name="Intervalle de confiance 80%",
    hoverinfo="skip",                        # pas de tooltip sur la zone
))

# Courbe des prédictions centrales
fig.add_trace(go.Scatter(
    x=df_pred["date_pred"],
    y=df_pred["yhat"],
    name=f"Prédiction Prophet ({horizon} mois)",
    mode="lines+markers",
    line=dict(color="#27ae60", width=2.5),
    marker=dict(size=5),
    hovertemplate=(
        "Date : %{x|%Y-%m}<br>"
        "IPC prédit : %{y:.2f}<br>"
        "<extra></extra>"
    ),
))

# Ligne verticale séparant historique et prédictions.
# add_vline ET add_shape(xref="x", yref="paper") déclenchent tous deux
# _process_multiple_axis_spanning_shapes → sum([Timestamp]) → TypeError pandas 2.x.
# Solution : go.Scatter en coordonnées data (xref="x", yref="y") — aucune logique
# d'axis-spanning, 100% compatible pandas 2.x.
if not df_hist.empty:
    last_date = pd.Timestamp(df_hist["date_obs"].max())
    last_date_str = last_date.strftime("%Y-%m-%d")
    all_vals = pd.concat([
        df_hist["valeur"],
        df_pred["yhat"], df_pred["yhat_lower"], df_pred["yhat_upper"],
    ])
    y_min = float(all_vals.min()) - 1
    y_max = float(all_vals.max()) + 1
    fig.add_trace(go.Scatter(
        x=[last_date_str, last_date_str],
        y=[y_min, y_max],
        mode="lines",
        line=dict(dash="dot", color="grey", width=1.5),
        showlegend=False,
        hoverinfo="skip",
    ))
    fig.add_annotation(
        x=last_date_str,
        y=y_max,
        xref="x", yref="y",
        text=f"Début prédiction<br>{last_date.strftime('%Y-%m')}",
        showarrow=False,
        xanchor="right",
        yanchor="top",
        font=dict(size=11, color="grey"),
    )

fig.update_layout(
    title=dict(
        text=f"Prophet — IPC France · {categorie} · Prédiction {horizon} mois",
        font=dict(size=15),
    ),
    xaxis_title="Date",
    yaxis_title="Indice IPC (base 100 = 2015)",
    hovermode="x unified",
    height=520,
    plot_bgcolor="white",
    xaxis=dict(gridcolor="#f0f0f0"),
    yaxis=dict(gridcolor="#f0f0f0"),
    legend=dict(orientation="h", y=-0.2),
)

st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# Résumé de la prédiction
# =============================================================================

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        "IPC prédit (1er mois)",
        f"{df_pred['yhat'].iloc[0]:.2f}",
        help=f"IC 80% : [{df_pred['yhat_lower'].iloc[0]:.2f} – {df_pred['yhat_upper'].iloc[0]:.2f}]",
    )
with col2:
    st.metric(
        f"IPC prédit (mois {horizon})",
        f"{df_pred['yhat'].iloc[-1]:.2f}",
        help=f"IC 80% : [{df_pred['yhat_lower'].iloc[-1]:.2f} – {df_pred['yhat_upper'].iloc[-1]:.2f}]",
    )
with col3:
    variation = pred["variation_totale"]
    st.metric(
        "Variation prédite",
        f"{variation:+.2f} pts IPC",
        delta_color="inverse",   # hausse = rouge pour le consommateur
    )

# =============================================================================
# Tableau détaillé des prédictions
# =============================================================================

with st.expander("📋 Tableau des prédictions (valeurs numériques)"):
    df_display = df_pred.copy()
    df_display["date_pred"]  = df_display["date_pred"].dt.strftime("%Y-%m")
    df_display["yhat"]       = df_display["yhat"].round(2)
    df_display["yhat_lower"] = df_display["yhat_lower"].round(2)
    df_display["yhat_upper"] = df_display["yhat_upper"].round(2)
    df_display.columns      = ["Date", "IPC prédit", "IC bas (80%)", "IC haut (80%)"]
    st.dataframe(df_display, use_container_width=True, hide_index=True)
