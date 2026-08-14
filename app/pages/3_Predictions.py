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


@st.cache_data(ttl=300)
def _load_predictions(categorie, horizon):
    """Prédictions pour le graphique principal — mis en cache 5 min.

    Caché pour éviter un re-appel API parasite à chaque interaction simulateur
    qui déclenche un rerun complet de la page.
    """
    return predict_categorie(categorie, horizon=horizon)


def _load_predictions_sim(categorie, horizon):
    """Prédictions pour le simulateur budgétaire — sans cache.

    Chaque appel génère une vraie requête HTTP vers l'API modèle,
    correctement comptabilisée dans Prometheus (inflation_predictions_total).
    """
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
# Tableau détaillé des prédictions — juste après les KPIs
# =============================================================================

with st.expander("📋 Tableau des prédictions (valeurs numériques)"):
    df_display = df_pred.copy()
    df_display["date_pred"]  = df_display["date_pred"].dt.strftime("%Y-%m")
    df_display["yhat"]       = df_display["yhat"].round(2)
    df_display["yhat_lower"] = df_display["yhat_lower"].round(2)
    df_display["yhat_upper"] = df_display["yhat_upper"].round(2)
    df_display.columns       = ["Date", "IPC prédit", "IC bas (80%)", "IC haut (80%)"]
    st.dataframe(df_display, use_container_width=True, hide_index=True)

# =============================================================================
# Simulateur budgétaire — conversion IPC → €
# =============================================================================

def _simuler_budget(
    montant: float,
    indice_actuel: float,
    indice_predit: float,
    indice_lower: float,
    indice_upper: float,
) -> dict:
    """Convertit les indices IPC en variation budgétaire en euros.

    Formule : montant × (indice_prédit / indice_actuel).
    La base de référence (2015 ou 2025) s'annule dans le ratio — seule
    la variation relative compte. Les deux indices doivent venir de la
    même source pour que la base soit identique.
    """
    ratio = indice_predit / indice_actuel
    futur = round(montant * ratio)
    return {
        "futur": futur,
        "min":   round(montant * (indice_lower / indice_actuel)),
        "max":   round(montant * (indice_upper / indice_actuel)),
        "delta": futur - round(montant),
    }


st.divider()
st.subheader("💶 Simulateur budgétaire")
st.caption(
    "Estimez l'impact concret de l'inflation sur votre budget mensuel "
    "selon les prédictions Prophet."
)

# --- 3 inputs sur une seule ligne ---
SIM_HORIZONS = [3, 6, 12, 18, 24, 36]

col_in1, col_in2, col_in3 = st.columns(3)

with col_in1:
    montant = st.number_input(
        "Montant actuel (€/mois)",
        min_value=1,
        max_value=10_000,
        value=300,
        step=10,
        key="sim_montant",
    )

with col_in2:
    sim_categorie = st.selectbox(
        "Catégorie IPC",
        cats,
        index=cats.index(categorie) if categorie in cats else 0,
        key="sim_categorie",
    )

with col_in3:
    sim_horizon = st.selectbox(
        "Budget dans X mois",
        options=SIM_HORIZONS,
        index=SIM_HORIZONS.index(12),
        key="sim_horizon",
        format_func=lambda x: f"{x} mois",
    )

# --- Chargement des données pour la catégorie du simulateur (cached) ---
df_hist_sim = _load_historique(sim_categorie)
pred_sim    = _load_predictions_sim(sim_categorie, horizon=sim_horizon)

if pred_sim is None or df_hist_sim.empty:
    st.warning("Données indisponibles pour la catégorie sélectionnée.")
else:
    df_pred_sim = pd.DataFrame(pred_sim["predictions"])
    df_pred_sim["date_pred"] = pd.to_datetime(df_pred_sim["date_pred"])

    indice_actuel = float(df_hist_sim["valeur"].iloc[-1])
    indice_predit = float(df_pred_sim["yhat"].iloc[-1])
    indice_lower  = float(df_pred_sim["yhat_lower"].iloc[-1])
    indice_upper  = float(df_pred_sim["yhat_upper"].iloc[-1])
    date_ref      = df_hist_sim["date_obs"].iloc[-1].strftime("%Y-%m")

    sim = _simuler_budget(montant, indice_actuel, indice_predit, indice_lower, indice_upper)
    # pct calculé sur le ratio IPC exact — pas sur les budgets arrondis
    # (arrondir 79.28 → 79 € sur un budget de 80 € fausserait le % de 0.3 pts)
    pct = (indice_predit / indice_actuel - 1) * 100
    delta_ipc = indice_predit - indice_actuel

    # 5 KPIs : IPC actuel → IPC prédit → Budget actuel → Variation % → Budget dans X mois
    col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
    with col_s1:
        st.metric(
            f"IPC actuel ({date_ref})",
            f"{indice_actuel:.2f} pts",
            help="Dernière valeur réelle connue (INSEE, base 100 = 2015)",
        )
    with col_s2:
        st.metric(
            f"IPC prédit ({sim_horizon} mois)",
            f"{indice_predit:.2f} pts",
            delta=f"{delta_ipc:+.2f} pts",
            delta_color="inverse",
            help="Valeur centrale Prophet à l'horizon choisi",
        )
    with col_s3:
        st.metric("Budget actuel", f"{round(montant)} €")
    with col_s4:
        st.metric(
            "Variation estimée",
            f"{pct:+.1f} %",
            delta_color="inverse",
        )
    with col_s5:
        st.metric(
            f"Budget dans {sim_horizon} mois",
            f"{sim['futur']} €",
            delta=f"{sim['delta']:+d} €/mois",
            delta_color="inverse",
        )

    st.caption(
        f"Fourchette IC 80 % : entre **{sim['min']} €** et **{sim['max']} €**"
    )

    # Variables stockées pour la section explicative ci-dessous
    _ipc_ref      = indice_actuel
    _ipc_label    = sim_categorie
    _delta_ipc    = delta_ipc
    _sim_horizon  = sim_horizon

# =============================================================================
# Impact concret selon votre budget — basé sur la prédiction en cours
# =============================================================================

st.divider()
try:
    pct_predit = _delta_ipc / _ipc_ref * 100
    with st.expander("💡 Qu'est-ce que ça représente concrètement ?"):
        st.markdown(
            f"Prophet prédit **{_delta_ipc:+.2f} pts IPC** sur *{_ipc_label}* "
            f"dans **{_sim_horizon} mois**, soit une hausse de **{pct_predit:.1f} %**."
        )
        hausse_mois  = round(montant * (_delta_ipc / _ipc_ref))
        hausse_total = hausse_mois * _sim_horizon
        mot          = "hausse" if hausse_mois >= 0 else "baisse"
        abs_mois     = abs(hausse_mois)
        abs_total    = abs(hausse_total)

        st.markdown(
            f"Pour votre budget de **{round(montant)} €/mois**, "
            f"cette prédiction représente une **{mot} de {abs_mois} €/mois**, "
            f"soit **{abs_total} € sur les {_sim_horizon} mois**."
        )
        ipc_fin      = _ipc_ref + _delta_ipc
        budget_futur = round(montant * ipc_fin / _ipc_ref)
        st.caption(
            f"Calcul : budget futur = {round(montant)} € × ({ipc_fin:.2f} / {_ipc_ref:.2f}) "
            f"= {budget_futur} € → "
            f"{mot} = {budget_futur} − {round(montant)} "
            f"= {hausse_mois:+d} €/mois"
        )
except NameError:
    pass  # données simulateur non disponibles — section masquée
