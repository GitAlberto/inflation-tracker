"""
=============================================================================
C17 — Page 2 : Analyse par Catégorie — inflation-tracker
=============================================================================
Deep-dive sur une catégorie IPC : statistiques, variation YoY,
heatmap mensuelle et comparaison avec l'indice général.

Issue GitHub : #19 (C17)
=============================================================================
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_client import get_categories, get_health, get_inflation, get_sources
from app.theme import inject_theme

st.set_page_config(page_title="Analyse par Catégorie", page_icon="🔍", layout="wide")
inject_theme()

st.title("🔍 Analyse par Catégorie IPC")
st.caption("Évolution détaillée, saisonnalité et comparaison avec l'indice général France")

# =============================================================================
# Filtres sidebar
# =============================================================================

with st.sidebar:
    st.header("Filtres")

    # Vérification de la connexion à l'API avant toute requête DB
    if get_health() is None:
        st.error("API data indisponible.\nDémarrez : uvicorn api.data.main:app --port 8001")
        st.stop()

    # Sélection de la source — DATAGOUV par défaut (remonte à 1996)
    sources = get_sources() or ["DATAGOUV", "INSEE", "ECB", "EUROSTAT"]
    # DATAGOUV en premier car c'est la source avec le plus d'historique France
    sources_sorted = sorted(sources, key=lambda s: (s != "DATAGOUV", s))
    source = st.selectbox("Source de données", sources_sorted, index=0)

    # Chargement des catégories pour la source sélectionnée
    cats_raw = get_categories(source=source)
    if cats_raw is None:
        st.error("Impossible de récupérer les catégories (timeout ou erreur DB).")
        st.stop()
    if not cats_raw:
        st.warning(f"Aucune catégorie disponible pour la source {source}.")
        st.stop()

    # Après normalisation dans aggregate_clean.py, toutes les sources
    # stockent le format "XX - Label" → pas de traitement spécifique par source
    categorie = st.selectbox(
        "Catégorie IPC",
        cats_raw,
        index=1 if len(cats_raw) > 1 else 0,
    )
    # Les 2 premiers caractères = code COICOP (ex: "01" dans "01 - Alimentation...")
    categorie_code = categorie[:2]

    # Période d'analyse — début à 2000 par défaut (couverture large sans remonter à 1996)
    annee_debut = st.slider("Année de début", 1996, 2025, 2000)
    annee_fin   = st.slider("Année de fin",   1996, 2025, 2025)

# =============================================================================
# Chargement des données
# =============================================================================

@st.cache_data(ttl=300)
def _load(source, cat_code, y_debut, y_fin):
    """Charge la série IPC France pour une source, une catégorie et une période."""
    result = get_inflation(
        pays="FR",
        source=source,
        categorie=cat_code,            # code COICOP filtré (ex: "01")
        date_debut=f"{y_debut}-01-01",
        date_fin=f"{y_fin}-12-31",
        limit=1000,
    )
    if not result or not result["data"]:
        return pd.DataFrame()
    df = pd.DataFrame(result["data"])
    df["date_obs"] = pd.to_datetime(df["date_obs"])
    df["valeur"]   = df["valeur"].astype(float)
    df["annee"]    = df["date_obs"].dt.year
    df["mois"]     = df["date_obs"].dt.month
    df["mois_nom"] = df["date_obs"].dt.strftime("%b")
    return df.sort_values("date_obs")


@st.cache_data(ttl=300)
def _load_ensemble(source, y_debut, y_fin):
    """Charge l'indice général (code 00) pour la même source — ligne de référence."""
    result = get_inflation(
        pays="FR", source=source, categorie="00",
        date_debut=f"{y_debut}-01-01", date_fin=f"{y_fin}-12-31", limit=1000,
    )
    if not result or not result["data"]:
        return pd.DataFrame()
    df = pd.DataFrame(result["data"])
    df["date_obs"] = pd.to_datetime(df["date_obs"])
    df["valeur"]   = df["valeur"].astype(float)
    return df.sort_values("date_obs")


df     = _load(source, categorie_code, annee_debut, annee_fin)
df_ens = _load_ensemble(source, annee_debut, annee_fin)

if df.empty:
    st.warning(f"Aucune donnée disponible pour {source} · {categorie} · {annee_debut}–{annee_fin}.")
    st.stop()

# =============================================================================
# KPIs rapides
# =============================================================================

st.subheader(f"📌 {categorie}  ·  {source}")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Valeur actuelle", f"{df['valeur'].iloc[-1]:.2f}", help="Dernière valeur disponible")
with col2:
    variation = df['valeur'].iloc[-1] - df['valeur'].iloc[0]
    st.metric("Variation totale", f"{variation:+.2f} pts", delta_color="inverse")
with col3:
    idx_max = df['valeur'].idxmax()
    st.metric("Maximum (période)", f"{df['valeur'].max():.2f}", f"en {df.loc[idx_max, 'date_obs'].strftime('%Y-%m')}")
with col4:
    st.metric("Écart-type", f"{df['valeur'].std():.2f}", help="Volatilité de l'indice")

st.divider()

# =============================================================================
# Graphique 1 — Catégorie vs Ensemble
# =============================================================================

st.subheader("Évolution : catégorie vs indice général")

fig_cmp = go.Figure()

fig_cmp.add_trace(go.Scatter(
    x=df["date_obs"], y=df["valeur"],
    name=categorie[:40],
    line=dict(color="#e74c3c", width=2.5),
    mode="lines",
))

if not df_ens.empty:
    fig_cmp.add_trace(go.Scatter(
        x=df_ens["date_obs"], y=df_ens["valeur"],
        name="Indice général (référence)",
        line=dict(color="#1a3c5e", width=1.5, dash="dot"),
        mode="lines",
    ))

fig_cmp.update_layout(
    height=400,
    yaxis_title="Indice IPC",
    hovermode="x unified",
    plot_bgcolor="white",
    xaxis=dict(gridcolor="#f0f0f0"),
    yaxis=dict(gridcolor="#f0f0f0"),
    legend=dict(orientation="h", y=-0.25),
)
st.plotly_chart(fig_cmp, use_container_width=True)

# =============================================================================
# Graphique 2 — Variation Year-over-Year (YoY)
# =============================================================================

st.subheader("Variation annuelle (Year-over-Year)")

df_yoy = df.copy().set_index("date_obs")
df_yoy["yoy"] = df_yoy["valeur"].diff(12)   # IPC(mois M, année N) − IPC(mois M, année N−1)
df_yoy = df_yoy.dropna(subset=["yoy"]).reset_index()

fig_yoy = go.Figure()
fig_yoy.add_trace(go.Bar(
    x=df_yoy["date_obs"],
    y=df_yoy["yoy"],
    marker_color=["#27ae60" if v < 0 else "#e74c3c" for v in df_yoy["yoy"]],
    name="Variation YoY (pts IPC)",
    hovertemplate="Date : %{x|%Y-%m}<br>Variation : %{y:+.2f} pts<extra></extra>",
))
fig_yoy.add_hline(y=0, line_color="black", line_width=1)
fig_yoy.update_layout(
    height=320,
    yaxis_title="Variation (pts IPC)",
    plot_bgcolor="white",
    xaxis=dict(gridcolor="#f0f0f0"),
    yaxis=dict(gridcolor="#f0f0f0"),
    showlegend=False,
)
st.plotly_chart(fig_yoy, use_container_width=True)

# =============================================================================
# Graphique 3 — Heatmap saisonnalité (mois × année)
# =============================================================================

st.subheader("Heatmap saisonnalité — IPC par mois et par année")

if len(df["annee"].unique()) > 1:
    pivot = df.pivot_table(values="valeur", index="mois", columns="annee")
    mois_labels = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]

    fig_heat = px.imshow(
        pivot,
        labels=dict(x="Année", y="Mois", color="IPC"),
        y=[mois_labels[m-1] for m in pivot.index],
        color_continuous_scale="RdYlGn_r",
        aspect="auto",
        title="",
    )
    fig_heat.update_layout(height=350)
    st.plotly_chart(fig_heat, use_container_width=True)
    st.caption("Rouge = IPC élevé | Vert = IPC bas | Lecture : repérer les mois à forte inflation récurrente")
