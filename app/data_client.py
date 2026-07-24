"""
=============================================================================
C17 — Client API data — inflation-tracker
=============================================================================
Appelle l'API data REST (api/data/, port 8001) depuis l'application Streamlit.
Toutes les fonctions retournent None si l'API est indisponible.

Issue GitHub : #19 (C17)
=============================================================================
"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", override=True)

# URL de base de l'API data — configurable via .env
DATA_API_URL = os.getenv("DATA_API_URL", "http://localhost:8001")
# Clé API — lue depuis .env, envoyée dans chaque requête via header X-API-Key (C5/C10)
_API_KEY = os.getenv("API_KEY", "")
# 30s par défaut — SELECT DISTINCT sur 3.68M lignes peut dépasser 10s sans index
_TIMEOUT = int(os.getenv("DATA_API_TIMEOUT", "30"))
# Header d'authentification injecté dans toutes les requêtes protégées
_HEADERS = {"X-API-Key": _API_KEY}


def get_health() -> dict | None:
    """Vérifie que l'API data est opérationnelle."""
    try:
        r = requests.get(f"{DATA_API_URL}/health", timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def get_inflation(
    pays: str | None = None,
    source: str | None = None,
    categorie: str | None = None,
    date_debut: str | None = None,
    date_fin: str | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> dict | None:
    """
    Récupère les données IPC depuis /api/inflation avec filtres optionnels.

    Returns:
        dict {"total": N, "data": [...], "limit": N, "offset": N}
        Chaque item : {"date_obs", "pays", "source", "categorie", "valeur"}
    """
    params = {"limit": limit, "offset": offset}   # paramètres toujours présents
    if pays:       params["pays"] = pays
    if source:     params["source"] = source
    if categorie:  params["categorie"] = categorie
    if date_debut: params["date_debut"] = date_debut
    if date_fin:   params["date_fin"] = date_fin

    try:
        r = requests.get(f"{DATA_API_URL}/api/inflation", params=params, headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def get_tendance(
    pays: str = "FR",
    source: str = "INSEE",
    date_debut: str | None = None,
    date_fin: str | None = None,
) -> dict | None:
    """
    Récupère la tendance mensuelle depuis /api/inflation/tendance.

    Returns:
        dict {"nb_points": N, "pays": str, "source": str,
              "data": [{"mois": str, "valeur_moy": float, "nb_categories": int}]}
    """
    params = {"pays": pays, "source": source}
    if date_debut: params["date_debut"] = date_debut
    if date_fin:   params["date_fin"] = date_fin

    try:
        r = requests.get(f"{DATA_API_URL}/api/inflation/tendance", params=params, headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def get_pays(source: str | None = None) -> list[str] | None:
    """Retourne la liste des pays disponibles, filtrable par source."""
    params = {}
    if source:
        params["source"] = source
    try:
        r = requests.get(f"{DATA_API_URL}/api/inflation/pays", params=params, headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json().get("pays", [])
    except requests.RequestException:
        return None


def get_sources() -> list[str] | None:
    """Retourne la liste des sources de données disponibles."""
    try:
        r = requests.get(f"{DATA_API_URL}/api/inflation/sources", headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json().get("sources", [])
    except requests.RequestException:
        return None


def get_categories(source: str | None = None) -> list[str] | None:
    """Retourne la liste des catégories, filtrable par source."""
    params = {}
    if source: params["source"] = source
    try:
        r = requests.get(f"{DATA_API_URL}/api/inflation/categories", params=params, headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json().get("categories", [])
    except requests.RequestException:
        return None


def get_prix_alimentaires(categorie: str | None = None, limit: int = 500) -> dict | None:
    """Retourne les prix Open Food Facts avec filtre catégorie optionnel."""
    params = {"limit": limit}
    if categorie: params["categorie"] = categorie
    try:
        r = requests.get(f"{DATA_API_URL}/api/prix-alimentaires", params=params, headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None
