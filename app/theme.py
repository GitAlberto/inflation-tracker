"""
Thème financier professionnel — inflation-tracker (C17)

Palette :
    #0b1929  marine profond   — fond sidebar
    #c9a84c  or              — accent primaire (sliders, bordures actives)
    #f5f7fa  blanc bleuté    — fond principal
    #1c2e40  ardoise         — texte principal
    #8a9eb8  gris-bleu       — labels, captions

Appel : inject_theme() juste après set_page_config() dans chaque page.
"""

import streamlit as st

_CSS = """
<style>
/* ================================================================
   NAVIGATION DES PAGES (sidebar nav Streamlit multi-page)
   Les liens héritent de textColor du config.toml (#1c2e40 = ardoise
   foncée), illisible sur fond marine. On force un gris-bleu clair.
================================================================ */
[data-testid="stSidebarNav"] {
    background-color: #0b1929 !important;
    padding-top: 0.5rem !important;
}

[data-testid="stSidebarNav"] a,
[data-testid="stSidebarNavLink"],
[data-testid="stSidebarNavLink"] span {
    color: #b8cce0 !important;
    font-size: 0.85rem !important;
    font-weight: 400 !important;
    text-decoration: none !important;
}

/* Page active — or */
[data-testid="stSidebarNavLink"][aria-current="page"],
[data-testid="stSidebarNavLink"][aria-current="page"] span {
    color: #c9a84c !important;
    font-weight: 600 !important;
}

/* Hover — légèrement plus clair */
[data-testid="stSidebarNavLink"]:hover span {
    color: #e8d5a0 !important;
}

/* ================================================================
   SIDEBAR — fond marine profond
================================================================ */
section[data-testid="stSidebar"] {
    background-color: #0b1929 !important;
    border-right: 1px solid rgba(201, 168, 76, 0.25) !important;
}

/* Titre principal dans la sidebar (st.title) */
section[data-testid="stSidebar"] h1 {
    color: #e8d5a0 !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em !important;
}

/* Sous-titres sidebar (st.subheader / st.header) */
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #c9a84c !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.10em !important;
    margin-top: 1.1rem !important;
    margin-bottom: 0.4rem !important;
}

/* Paragraphes et spans — texte secondaire clair */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] li,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #b8cce0 !important;
    font-size: 0.82rem !important;
    line-height: 1.5 !important;
}

/* Caption dans la sidebar */
section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: #4d6c8a !important;
    font-size: 0.70rem !important;
    line-height: 1.55 !important;
}

/* Labels des widgets (selectbox, slider, multiselect…) */
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
section[data-testid="stSidebar"] label {
    color: #7a9ab8 !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}

/* Fond des selectbox dans la sidebar */
section[data-testid="stSidebar"] [data-baseweb="select"] > div:first-child {
    background-color: #12263d !important;
    border-color: #2a4a6e !important;
    color: #d0e0f0 !important;
}

/* Texte sélectionné dans les selectbox */
section[data-testid="stSidebar"] [data-baseweb="select"] span {
    color: #d0e0f0 !important;
}

/* Multiselect tags */
section[data-testid="stSidebar"] [data-baseweb="tag"] {
    background-color: rgba(201, 168, 76, 0.2) !important;
    border: 1px solid rgba(201, 168, 76, 0.4) !important;
}
section[data-testid="stSidebar"] [data-baseweb="tag"] span {
    color: #e8d5a0 !important;
}

/* Status — success / error dans la sidebar */
section[data-testid="stSidebar"] [data-testid="stAlert"] {
    background-color: transparent !important;
    border: none !important;
    padding: 2px 0 !important;
    font-size: 0.78rem !important;
}

/* Divider dans la sidebar */
section[data-testid="stSidebar"] hr {
    border-top: 1px solid rgba(201, 168, 76, 0.15) !important;
    margin: 0.6rem 0 !important;
}

/* Slider — piste active et poignées en gold */
div[data-testid="stSlider"] > div > div > div > div {
    background-color: #c9a84c !important;
}
div[data-testid="stSlider"] span[role="slider"] {
    background-color: #c9a84c !important;
    border-color: #c9a84c !important;
    box-shadow: 0 0 0 4px rgba(201, 168, 76, 0.18) !important;
}

/* ================================================================
   CONTENU PRINCIPAL — typographie
================================================================ */

/* Titre h1 — ligne or en bas */
.main h1 {
    color: #0b1929 !important;
    font-weight: 800 !important;
    font-size: 1.55rem !important;
    letter-spacing: -0.025em !important;
    border-bottom: 2px solid #c9a84c !important;
    padding-bottom: 0.35em !important;
    margin-bottom: 0.25em !important;
}

/* h2 — label de section en majuscules */
.main h2 {
    color: #1c2e40 !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    border-bottom: 1px solid #dde3ec !important;
    padding-bottom: 4px !important;
    margin-top: 1.6rem !important;
}

/* h3 */
.main h3 {
    color: #1c2e40 !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
}

/* Caption principal */
[data-testid="stCaptionContainer"] p {
    color: #8a9eb8 !important;
    font-size: 0.76rem !important;
    letter-spacing: 0.01em !important;
}

/* Paragraphes */
.main p {
    color: #2a3f55 !important;
    line-height: 1.6 !important;
}

/* ================================================================
   MÉTRIQUES — carte avec bordure or
================================================================ */
div[data-testid="metric-container"] {
    background-color: #ffffff !important;
    border: 1px solid #dde3ec !important;
    border-left: 3px solid #c9a84c !important;
    border-radius: 3px !important;
    padding: 10px 16px !important;
    box-shadow: 0 1px 4px rgba(11, 25, 41, 0.05) !important;
}

div[data-testid="metric-container"] > label {
    color: #6a8aaa !important;
    font-size: 0.66rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
}

[data-testid="stMetricValue"] > div {
    color: #0b1929 !important;
    font-weight: 700 !important;
    font-variant-numeric: tabular-nums !important;
    letter-spacing: -0.02em !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    font-variant-numeric: tabular-nums !important;
}

/* ================================================================
   TABLEAUX / DATAFRAMES — chiffres alignés
================================================================ */
.stDataFrame {
    border: 1px solid #dde3ec !important;
    border-radius: 3px !important;
    font-variant-numeric: tabular-nums !important;
    overflow: hidden !important;
}

.stDataFrame thead th {
    background-color: #f0f3f8 !important;
    color: #4a6a8a !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

/* ================================================================
   EXPANDERS
================================================================ */
[data-testid="stExpander"] {
    border: 1px solid #dde3ec !important;
    border-radius: 3px !important;
    background-color: #ffffff !important;
}

[data-testid="stExpander"] summary {
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: #1c2e40 !important;
    padding: 10px 12px !important;
}

/* ================================================================
   DIVIDERS
================================================================ */
hr {
    border: none !important;
    border-top: 1px solid #dde3ec !important;
    margin: 0.8rem 0 !important;
}

/* ================================================================
   FOND PRINCIPAL — blanc légèrement bleuté
================================================================ */
.main {
    background-color: #f5f7fa !important;
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
   TABS (si utilisés)
================================================================ */
[data-testid="stTabs"] [role="tab"] {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

/* ================================================================
   SÉLECTEURS / SLIDERS dans le contenu principal
================================================================ */
.main [data-testid="stWidgetLabel"] p {
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    color: #5e7a99 !important;
}
</style>
"""


def inject_theme() -> None:
    """Injecte le thème financier — appeler juste après set_page_config()."""
    st.markdown(_CSS, unsafe_allow_html=True)
