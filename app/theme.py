"""
Thème — inflation-tracker (C17)

Palette :
    #8d57f6  violet          — accent principal
    #449864  vert            — positif / succès
    #e99842  orange          — avertissement / secondaire
    #000000  noir            — texte
    #ffffff  blanc           — fond principal
    #F0EAFE  lavande pâle    — fond sidebar / secondaire

Appel : inject_theme() juste après set_page_config() dans chaque page.
"""

import streamlit as st

_CSS = """
<style>
/* ================================================================
   VARIABLES CSS RACINE — écrase le thème natif Streamlit
================================================================ */
:root {
    --primary-color: #8d57f6;
    --background-color: #ffffff;
    --secondary-background-color: #F0EAFE;
    --text-color: #000000;
}

/* ================================================================
   NAVIGATION DES PAGES
================================================================ */
[data-testid="stSidebarNav"] {
    background-color: #F0EAFE !important;
    padding-top: 0.5rem !important;
}

[data-testid="stSidebarNav"] a,
[data-testid="stSidebarNavLink"],
[data-testid="stSidebarNavLink"] span {
    color: #4a3580 !important;
    font-size: 0.85rem !important;
    font-weight: 400 !important;
    text-decoration: none !important;
}

[data-testid="stSidebarNavLink"][aria-current="page"],
[data-testid="stSidebarNavLink"][aria-current="page"] span {
    color: #8d57f6 !important;
    font-weight: 600 !important;
}

[data-testid="stSidebarNavLink"]:hover span {
    color: #a97af9 !important;
}

/* ================================================================
   SIDEBAR
================================================================ */
section[data-testid="stSidebar"] {
    background-color: #F0EAFE !important;
    border-right: 1px solid rgba(141, 87, 246, 0.15) !important;
}

section[data-testid="stSidebar"] h1 {
    color: #000000 !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
}

section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #8d57f6 !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.10em !important;
    margin-top: 1.1rem !important;
    margin-bottom: 0.4rem !important;
}

section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] li,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #2a1a60 !important;
    font-size: 0.82rem !important;
    line-height: 1.5 !important;
}

section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: #8878b8 !important;
    font-size: 0.70rem !important;
}

section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
section[data-testid="stSidebar"] label {
    color: #5e40a8 !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}

section[data-testid="stSidebar"] [data-baseweb="select"] > div:first-child {
    background-color: #e3d8fd !important;
    border-color: rgba(141, 87, 246, 0.30) !important;
    color: #000000 !important;
}

section[data-testid="stSidebar"] [data-baseweb="select"] span {
    color: #000000 !important;
}

section[data-testid="stSidebar"] [data-baseweb="tag"] {
    background-color: rgba(141, 87, 246, 0.15) !important;
    border: 1px solid rgba(141, 87, 246, 0.35) !important;
}
section[data-testid="stSidebar"] [data-baseweb="tag"] span {
    color: #4a3580 !important;
}

section[data-testid="stSidebar"] [data-testid="stAlert"] {
    background-color: transparent !important;
    border: none !important;
    padding: 2px 0 !important;
    font-size: 0.78rem !important;
}

section[data-testid="stSidebar"] hr {
    border-top: 1px solid rgba(141, 87, 246, 0.15) !important;
    margin: 0.6rem 0 !important;
}

/* ================================================================
   SLIDER — violet principal
================================================================ */
div[data-testid="stSlider"] > div > div > div > div {
    background-color: #8d57f6 !important;
}
div[data-testid="stSlider"] span[role="slider"] {
    background-color: #8d57f6 !important;
    border-color: #8d57f6 !important;
    box-shadow: 0 0 0 4px rgba(141, 87, 246, 0.18) !important;
}

/* ================================================================
   CONTENU PRINCIPAL
================================================================ */
.main h1 {
    color: #000000 !important;
    font-weight: 800 !important;
    font-size: 1.55rem !important;
    letter-spacing: -0.025em !important;
    border-bottom: 2px solid #8d57f6 !important;
    padding-bottom: 0.35em !important;
    margin-bottom: 0.25em !important;
}

.main h2 {
    color: #000000 !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    border-bottom: 1px solid #e3d8fd !important;
    padding-bottom: 4px !important;
    margin-top: 1.6rem !important;
}

.main h3 {
    color: #000000 !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
}

[data-testid="stCaptionContainer"] p {
    color: #8878b8 !important;
    font-size: 0.76rem !important;
}

.main p {
    color: #111111 !important;
    line-height: 1.6 !important;
}

/* ================================================================
   MÉTRIQUES — bordure gauche violette
================================================================ */
div[data-testid="metric-container"] {
    background-color: #ffffff !important;
    border: 1px solid #e3d8fd !important;
    border-left: 3px solid #8d57f6 !important;
    border-radius: 3px !important;
    padding: 10px 16px !important;
    box-shadow: 0 1px 4px rgba(141, 87, 246, 0.07) !important;
}

div[data-testid="metric-container"] > label {
    color: #8878b8 !important;
    font-size: 0.66rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
}

[data-testid="stMetricValue"] > div {
    color: #8d57f6 !important;
    font-weight: 700 !important;
    font-variant-numeric: tabular-nums !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    font-variant-numeric: tabular-nums !important;
}

/* ================================================================
   TABLEAUX
================================================================ */
.stDataFrame {
    border: 1px solid #e3d8fd !important;
    border-radius: 3px !important;
    font-variant-numeric: tabular-nums !important;
    overflow: hidden !important;
}

.stDataFrame thead th {
    background-color: #F0EAFE !important;
    color: #5e40a8 !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

/* ================================================================
   EXPANDERS
================================================================ */
[data-testid="stExpander"] {
    border: 1px solid #e3d8fd !important;
    border-radius: 3px !important;
    background-color: #ffffff !important;
}

[data-testid="stExpander"] summary {
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: #000000 !important;
    padding: 10px 12px !important;
}

/* ================================================================
   DIVIDERS
================================================================ */
hr {
    border: none !important;
    border-top: 1px solid #e3d8fd !important;
    margin: 0.8rem 0 !important;
}

/* ================================================================
   FOND PRINCIPAL
================================================================ */
.main {
    background-color: #ffffff !important;
}

.main .block-container {
    padding-top: 1.4rem !important;
    padding-bottom: 2rem !important;
}

/* ================================================================
   ALERTES
================================================================ */
[data-testid="stAlert"] {
    border-radius: 3px !important;
    font-size: 0.82rem !important;
}

/* ================================================================
   TABS
================================================================ */
[data-testid="stTabs"] [role="tab"] {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

/* ================================================================
   LABELS WIDGETS — contenu principal
================================================================ */
.main [data-testid="stWidgetLabel"] p {
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    color: #5e40a8 !important;
}
</style>
"""


def inject_theme() -> None:
    """Injecte le thème — appeler juste après set_page_config()."""
    st.markdown(_CSS, unsafe_allow_html=True)
