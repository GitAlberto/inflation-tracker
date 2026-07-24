"""
=============================================================================
C17 — Page 1 : Analyse Historique — inflation-tracker
=============================================================================
Graphique IPC multi-sources, multi-pays avec filtres interactifs.

Issue GitHub : #19 (C17)
=============================================================================
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Ajout de la racine au sys.path pour les imports app.*
ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_client import get_categories, get_inflation, get_sources
from app.theme import inject_theme

st.set_page_config(page_title="Analyse Historique", page_icon="📊", layout="wide")
inject_theme()

st.title("📊 Analyse Historique de l'Inflation")
st.caption("Données IPC — INSEE, BCE, Eurostat, data.gouv — France et zone euro")

# =============================================================================
# Filtres sidebar
# =============================================================================

with st.sidebar:
    st.header("Filtres")

    # Périmètre fixé à la France — toutes les sources sont filtrées geo=FR à la collecte
    pays = "FR"

    # Sélection de la source
    sources = get_sources() or ["INSEE", "ECB", "EUROSTAT", "DATAGOUV"]
    source = st.selectbox("Source de données", sources, index=0)

    # Sélection des catégories (multi-sélection)
    cats = get_categories(source=source) or []
    if cats:
        categories = st.multiselect(
            "Catégories (max 5)",
            cats,
            default=cats[:1],          # catégorie principale par défaut
            max_selections=5,          # limite pour la lisibilité du graphique
        )
    else:
        categories = []
        st.warning("Aucune catégorie disponible pour cette source.")

    # Plage d'années — slider range double poignée
    st.subheader("Période")
    annee_debut, annee_fin = st.slider(
        "Années",
        min_value=1996,
        max_value=2025,
        value=(1996, 2025),
    )
    date_debut = f"{annee_debut}-01-01"
    date_fin   = f"{annee_fin}-12-31"

# =============================================================================
# Chargement des données
# =============================================================================

@st.cache_data(ttl=300)   # cache 5 minutes pour éviter les appels répétés
def _load_serie(pays, source, categorie, date_debut, date_fin):
    """Charge une série IPC depuis l'API data pour une catégorie donnée."""
    result = get_inflation(
        pays=pays,
        source=source,
        categorie=categorie,
        date_debut=str(date_debut),
        date_fin=str(date_fin),
        limit=1000,
    )
    if not result or not result["data"]:
        return pd.DataFrame()

    df = pd.DataFrame(result["data"])
    df["date_obs"] = pd.to_datetime(df["date_obs"])   # string → datetime
    df["valeur"]   = df["valeur"].astype(float)        # NUMERIC → float
    return df.sort_values("date_obs")                  # tri chronologique


# =============================================================================
# Graphique principal — courbes IPC par catégorie
# =============================================================================

if not categories:
    st.info("Sélectionnez au moins une catégorie dans le panneau de gauche.")
else:
    fig = go.Figure()

    # Palette de couleurs pour distinguer les catégories
    colors = ["#1a3c5e", "#27ae60", "#e74c3c", "#f39c12", "#8e44ad"]

    all_data = []
    for i, cat in enumerate(categories):
        df = _load_serie(pays, source, cat, date_debut, date_fin)
        if df.empty:
            st.warning(f"Aucune donnée pour : {cat}")
            continue

        all_data.append(df)
        color = colors[i % len(colors)]

        # Courbe principale de la catégorie
        fig.add_trace(go.Scatter(
            x=df["date_obs"],
            y=df["valeur"],
            name=cat[:45],                  # nom tronqué pour la légende
            mode="lines",
            line=dict(color=color, width=2),
            hovertemplate=(
                f"<b>{cat[:30]}</b><br>"
                "Date : %{x|%Y-%m}<br>"
                "IPC : %{y:.2f}<br>"
                "<extra></extra>"
            ),
        ))

    # Mise en forme du graphique
    fig.update_layout(
        title=dict(
            text=f"IPC {pays} — {source} — {annee_debut} → {annee_fin}",
            font=dict(size=16),
        ),
        xaxis_title="Date",
        yaxis_title="Indice IPC (base 100 = 2015)",
        hovermode="x unified",      # tooltip groupé sur l'axe X
        legend=dict(
            orientation="h",        # légende horizontale sous le graphique
            yanchor="top",
            y=-0.2,
            xanchor="left",
            x=0,
        ),
        height=520,
        plot_bgcolor="white",
        xaxis=dict(gridcolor="#f0f0f0"),
        yaxis=dict(gridcolor="#f0f0f0"),
    )

    st.plotly_chart(fig, use_container_width=True)   # graphique pleine largeur

    # =============================================================================
    # Tableau des statistiques descriptives
    # =============================================================================

    if all_data:
        st.subheader("Statistiques descriptives")

        stats_rows = []
        for i, (cat, df) in enumerate(zip(categories, all_data)):
            if df.empty:
                continue
            stats_rows.append({
                "Catégorie": cat[:50],
                "Min": f"{df['valeur'].min():.2f}",
                "Max": f"{df['valeur'].max():.2f}",
                "Moyenne": f"{df['valeur'].mean():.2f}",
                "Écart-type": f"{df['valeur'].std():.2f}",
                "Variation totale": f"{df['valeur'].iloc[-1] - df['valeur'].iloc[0]:+.2f} pts",
                "N points": len(df),
            })

        if stats_rows:
            st.dataframe(
                pd.DataFrame(stats_rows),
                use_container_width=True,
                hide_index=True,
            )
