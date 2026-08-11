"""
=============================================================================
C12 — Tests unitaires du pipeline d'agrégation (src/aggregate/aggregate_clean.py)
=============================================================================
Vérifie la structure des constantes SQL sans accès à la base de données :
    - Liste SOURCES : 4 sources ECB / INSEE / DATAGOUV / EUROSTAT
    - CTE COICOP : 13 codes attendus (00-12), y compris 12 absent du dataset INSEE
    - base_ref : chaque source a la bonne base (2015 ou 2025)
    - Idempotence : ON CONFLICT DO NOTHING dans chaque INSERT
    - Table cible : toutes les requêtes ciblent inflation_unified

Lancement :
    pytest tests/test_aggregate.py -v

Issue GitHub : #18 (C12)
=============================================================================
"""

import re

import pytest

from aggregate.aggregate_clean import (
    _COICOP_CTE,
    SOURCES,
    SQL_ECB,
    SQL_INSEE,
    SQL_DATAGOUV,
    SQL_EUROSTAT,
)

# Labels attendus dans SOURCES (dans l'ordre défini dans le module)
_EXPECTED_LABELS = {"ECB", "INSEE", "DATAGOUV", "EUROSTAT"}

# Les 13 codes COICOP de niveau 1 définis dans la CTE (00-12)
_EXPECTED_CODES = {str(i).zfill(2) for i in range(13)}   # {'00', '01', ..., '12'}


# =============================================================================
# SOURCES — liste des 4 sources
# =============================================================================

def test_sources_contient_4_elements():
    """SOURCES doit lister exactement 4 sources (ECB, INSEE, DATAGOUV, EUROSTAT)."""
    assert len(SOURCES) == 4


def test_sources_labels_corrects():
    """Les 4 labels de SOURCES doivent être ECB, INSEE, DATAGOUV et EUROSTAT."""
    labels = {label for label, _ in SOURCES}
    assert labels == _EXPECTED_LABELS


def test_sources_chaque_element_est_un_tuple_label_sql():
    """Chaque élément de SOURCES doit être un tuple (str, str) — label + SQL."""
    for item in SOURCES:
        assert isinstance(item, tuple) and len(item) == 2
        label, sql = item
        assert isinstance(label, str) and len(label) > 0
        assert isinstance(sql, str) and len(sql) > 100   # SQL non vide


# =============================================================================
# CTE COICOP — référentiel des 13 codes
# =============================================================================

def test_coicop_cte_contient_13_codes():
    """La CTE coicop_ref doit définir 13 codes : 00 (Ensemble) à 12 (Biens divers)."""
    for code in _EXPECTED_CODES:
        assert f"'{code}'" in _COICOP_CTE, f"Code COICOP '{code}' absent de _COICOP_CTE"


def test_coicop_cte_contient_00_ensemble():
    """'00 - Ensemble' doit être présent — c'est l'indice agrégé de référence."""
    assert "00 - Ensemble" in _COICOP_CTE


def test_coicop_cte_contient_code_12():
    """Le code 12 doit être dans la CTE même s'il est absent du dataset INSEE API.

    La catégorie 12 (Biens et services divers) est définie dans la nomenclature COICOP
    mais l'INSEE ne la publie pas via son API BDM — elle est absente d'insee_ipc.
    """
    assert "'12'" in _COICOP_CTE
    assert "12 - Biens et services divers" in _COICOP_CTE


def test_coicop_cte_labels_uniques():
    """Chaque code COICOP ne doit apparaître qu'une seule fois dans la CTE."""
    for code in _EXPECTED_CODES:
        occurrences = _COICOP_CTE.count(f"('{code}'")
        assert occurrences == 1, f"Code '{code}' apparaît {occurrences} fois dans la CTE"


# =============================================================================
# base_ref — cohérence par source
# =============================================================================

def test_sql_ecb_base_ref_2015():
    """ECB HICP est en base 2015=100 — base_ref doit être '2015'."""
    assert "'2015'" in SQL_ECB
    assert "'2025'" not in SQL_ECB


def test_sql_insee_base_ref_2015():
    """INSEE IPC base 2015=100 — base_ref doit être '2015'."""
    assert "'2015'" in SQL_INSEE
    assert "'2025'" not in SQL_INSEE


def test_sql_eurostat_base_ref_2015():
    """EUROSTAT HICP (unit=I15) base 2015=100 — base_ref doit être '2015'."""
    assert "'2015'" in SQL_EUROSTAT
    assert "'2025'" not in SQL_EUROSTAT


def test_sql_datagouv_base_ref_2025():
    """DATAGOUV est en base 2025 depuis le rebasage INSEE 2025 — base_ref doit être '2025'."""
    assert "'2025'" in SQL_DATAGOUV
    assert "'2015'" not in SQL_DATAGOUV


# =============================================================================
# Idempotence — ON CONFLICT DO NOTHING
# =============================================================================

def test_sql_ecb_on_conflict_do_nothing():
    """SQL_ECB doit être idempotent (relançable sans doublons)."""
    assert "ON CONFLICT" in SQL_ECB
    assert "DO NOTHING" in SQL_ECB


def test_sql_insee_on_conflict_do_nothing():
    """SQL_INSEE doit être idempotent."""
    assert "ON CONFLICT" in SQL_INSEE
    assert "DO NOTHING" in SQL_INSEE


def test_sql_datagouv_on_conflict_do_nothing():
    """SQL_DATAGOUV doit être idempotent."""
    assert "ON CONFLICT" in SQL_DATAGOUV
    assert "DO NOTHING" in SQL_DATAGOUV


def test_sql_eurostat_on_conflict_do_nothing():
    """SQL_EUROSTAT doit être idempotent."""
    assert "ON CONFLICT" in SQL_EUROSTAT
    assert "DO NOTHING" in SQL_EUROSTAT


# =============================================================================
# Table cible — toutes les requêtes pointent vers inflation_unified
# =============================================================================

@pytest.mark.parametrize("label,sql", SOURCES)
def test_sql_insere_dans_inflation_unified(label, sql):
    """Chaque SQL doit insérer dans inflation_unified (table de destination unique)."""
    assert "INSERT INTO inflation_unified" in sql, (
        f"[{label}] 'INSERT INTO inflation_unified' absent du SQL"
    )


# =============================================================================
# Filtres de niveau COICOP — niveau 1 seulement
# =============================================================================

def test_sql_ecb_filtre_niveau1_coicop():
    """ECB : seul le niveau 1 (4 derniers chiffres = '0000') doit être inséré.

    Ex: '010000' → alimentation (niveau 1) ; '011000' → exclu (niveau 2).
    """
    assert "RIGHT(e.coicop, 4) = '0000'" in SQL_ECB


def test_sql_eurostat_filtre_cp_deux_chiffres():
    """EUROSTAT : filtre CP + exactement 2 chiffres (ex: 'CP01', pas 'CP0111')."""
    assert "^CP[0-9]" in SQL_EUROSTAT


def test_sql_datagouv_filtre_deux_chiffres_exact():
    """DATAGOUV : catégorie = exactement 2 chiffres (ex: '01', pas '01.1')."""
    assert "^[0-9]" in SQL_DATAGOUV
