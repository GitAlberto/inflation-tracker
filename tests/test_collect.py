"""
=============================================================================
C12 — Tests unitaires collecteur CSV (source data.gouv.fr/INSEE)
=============================================================================
Teste la fonction transform() de src/collect/collect_csv.py — pure
transformation pandas, sans réseau ni base de données.

Couvre :
    - Filtres sur FREQ, UNIT_MEASURE, IND_TYPE, GEO, PRODUCT_GROUP
    - Conversion date_obs (premier du mois)
    - Typage numérique de la colonne valeur
    - Nettoyage des lignes NaN
    - Colonnes de sortie attendues

Lancement :
    pytest tests/test_collect.py -v

Issue GitHub : #18 (C12)
=============================================================================
"""

import pandas as pd
import pytest

from collect.collect_csv import transform


# =============================================================================
# Données de test
# =============================================================================

def _row(**overrides) -> dict:
    """Retourne un dict représentant une ligne valide du CSV INSEE brut.

    Toutes les valeurs par défaut passent les 6 filtres de transform() :
    FREQ='M', UNIT_MEASURE='IX', IND_TYPE='IX', GEO='F', PRODUCT_GROUP='_Z',
    BASE_PER='2015'.
    """
    base = {
        "IDX_TYPE":        "CPI",
        "IND_TYPE":        "IX",
        "PRODUCT_GROUP":   "_Z",
        "COICOP_2018":     "01",
        "OBS_STATUS":      "A",
        "SEASONAL_ADJUST": "N",
        "GEO":             "F",
        "GEO_OBJECT":      "FRANCE",
        "TPH_CPI":         "_T",
        "UNIT_MEASURE":    "IX",
        "FREQ":            "M",
        "DECIMALS":        2,
        "CONF_STATUS":     "F",
        "BASE_PER":        "2015",
        "TIME_PERIOD":     "2024-01",
        "OBS_VALUE":       119.17,
    }
    base.update(overrides)
    return base


def _df(*rows) -> pd.DataFrame:
    """Construit un DataFrame à partir d'un ou plusieurs dicts de lignes."""
    return pd.DataFrame(list(rows))


# =============================================================================
# Colonnes de sortie
# =============================================================================

def test_transform_colonnes_sortie():
    """transform() doit retourner exactement les colonnes attendues par datagouv_ipc."""
    df_clean = transform(_df(_row()))
    expected = {"date_obs", "valeur", "categorie", "source"}
    assert expected.issubset(df_clean.columns)


def test_transform_source_datagouv():
    """La colonne source doit valoir 'data.gouv.fr' (traçabilité de la source)."""
    df_clean = transform(_df(_row()))
    assert (df_clean["source"] == "data.gouv.fr").all()


def test_transform_renomme_coicop_en_categorie():
    """COICOP_2018 doit être renommé en 'categorie' dans la sortie."""
    df_clean = transform(_df(_row(COICOP_2018="01")))
    assert "categorie" in df_clean.columns
    assert "COICOP_2018" not in df_clean.columns


# =============================================================================
# Filtre 1 — Fréquence mensuelle (FREQ='M')
# =============================================================================

def test_transform_filtre_freq_mensuelle_garde_m():
    """Une ligne FREQ='M' doit passer le filtre fréquence."""
    df_clean = transform(_df(_row(FREQ="M")))
    assert len(df_clean) == 1


def test_transform_filtre_freq_exclut_annuel():
    """FREQ='A' (annuel) et FREQ='Q' (trimestriel) doivent être exclus."""
    df_clean = transform(_df(
        _row(FREQ="M"),
        _row(FREQ="A"),
        _row(FREQ="Q"),
    ))
    assert len(df_clean) == 1


def test_transform_fallback_si_aucun_m():
    """Si aucune fréquence 'M' n'est présente, transform() conserve toutes les lignes
    (fallback défensif — cf. collect_csv.py ligne 284).
    """
    df_clean = transform(_df(_row(FREQ="A"), _row(FREQ="Q")))
    assert len(df_clean) == 2   # pas de filtre fréquence appliqué


# =============================================================================
# Filtre 2 — Unité = indice (UNIT_MEASURE='IX')
# =============================================================================

def test_transform_filtre_unite_indice():
    """UNIT_MEASURE='RCH_A' (taux annuel) et 'RCH_M' (taux mensuel) doivent être exclus."""
    df_clean = transform(_df(
        _row(UNIT_MEASURE="IX"),
        _row(UNIT_MEASURE="RCH_A"),
        _row(UNIT_MEASURE="RCH_M"),
    ))
    assert len(df_clean) == 1


# =============================================================================
# Filtre 3 — IND_TYPE='IX' (pas les variations YoY)
# =============================================================================

def test_transform_filtre_ind_type_yoy():
    """IND_TYPE='YOY' (variation année-sur-année) doit être exclu même si UNIT_MEASURE='IX'."""
    df_clean = transform(_df(
        _row(IND_TYPE="IX"),
        _row(IND_TYPE="YOY"),
    ))
    assert len(df_clean) == 1


# =============================================================================
# Filtre 4 — France nationale (GEO='F')
# =============================================================================

def test_transform_filtre_geo_france():
    """Les DOM/COM (GEO='971', '972', '973'...) doivent être exclus."""
    df_clean = transform(_df(
        _row(GEO="F"),
        _row(GEO="971"),    # Guadeloupe
        _row(GEO="972"),    # Martinique
        _row(GEO="973"),    # Guyane
    ))
    assert len(df_clean) == 1


# =============================================================================
# Filtre 5 — Agrégat COICOP pur (PRODUCT_GROUP='_Z')
# =============================================================================

def test_transform_filtre_product_group():
    """Les sous-groupes produit (ex: '4005', '4037') doivent être exclus."""
    df_clean = transform(_df(
        _row(PRODUCT_GROUP="_Z"),
        _row(PRODUCT_GROUP="4005"),
        _row(PRODUCT_GROUP="4037"),
    ))
    assert len(df_clean) == 1


# =============================================================================
# Conversion de la date
# =============================================================================

def test_transform_date_premier_du_mois():
    """TIME_PERIOD='2024-01' doit produire date_obs = 2024-01-01 (premier du mois)."""
    df_clean = transform(_df(_row(TIME_PERIOD="2024-01")))
    assert len(df_clean) == 1
    date = df_clean["date_obs"].iloc[0]
    assert str(date)[:10] == "2024-01-01"


def test_transform_date_type_datetime():
    """date_obs doit être de type datetime (parsé par pandas, pas une chaîne)."""
    df_clean = transform(_df(_row(TIME_PERIOD="2023-06")))
    assert pd.api.types.is_datetime64_any_dtype(df_clean["date_obs"])


# =============================================================================
# Conversion de la valeur
# =============================================================================

def test_transform_valeur_numerique():
    """valeur doit être numérique (float) — pas une chaîne de caractères."""
    df_clean = transform(_df(_row(OBS_VALUE=119.17)))
    assert pd.api.types.is_numeric_dtype(df_clean["valeur"])
    assert df_clean["valeur"].iloc[0] == pytest.approx(119.17)


# =============================================================================
# Nettoyage des NaN
# =============================================================================

def test_transform_supprime_lignes_nan_valeur():
    """Une ligne avec OBS_VALUE=None doit être supprimée du résultat."""
    df_clean = transform(_df(
        _row(OBS_VALUE=119.17),
        _row(OBS_VALUE=None),
    ))
    assert len(df_clean) == 1
    assert df_clean["valeur"].notna().all()


def test_transform_supprime_lignes_nan_categorie():
    """Une ligne avec COICOP_2018=None doit être supprimée (catégorie obligatoire)."""
    df_clean = transform(_df(
        _row(COICOP_2018="01"),
        _row(COICOP_2018=None),
    ))
    assert len(df_clean) == 1


# =============================================================================
# Comportement multi-catégories
# =============================================================================

def test_transform_plusieurs_categories():
    """Plusieurs catégories COICOP valides doivent toutes passer."""
    df_clean = transform(_df(
        _row(COICOP_2018="00", TIME_PERIOD="2024-01"),
        _row(COICOP_2018="01", TIME_PERIOD="2024-01"),
        _row(COICOP_2018="07", TIME_PERIOD="2024-01"),
    ))
    assert len(df_clean) == 3
