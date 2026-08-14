"""
C5 — Routes /api/inflation — exposition de inflation_unified
Issue GitHub : #11
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.data.auth import verify_user_key
from api.data.database import get_db
from api.data.schemas import InflationResponse, InflationPoint

# dependencies=[Security(verify_key)] protège toutes les routes de ce router (C5)
router = APIRouter(prefix="/inflation", tags=["inflation"], dependencies=[Security(verify_user_key)])


@router.get("", response_model=InflationResponse)
def get_inflation(
    source: Optional[str] = Query(None, description="Source : ECB | INSEE | DATAGOUV | EUROSTAT"),
    categorie: Optional[str] = Query(None, description="Code ou libellé catégorie COICOP (recherche partielle)"),
    date_debut: Optional[date] = Query(None, description="Date de début (YYYY-MM-DD)"),
    date_fin: Optional[date] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre de résultats (max 1000)"),
    offset: int = Query(0, ge=0, description="Décalage pour la pagination"),
    db: Session = Depends(get_db),
):
    """
    Retourne les points d'inflation filtrés depuis inflation_unified.
    Périmètre France uniquement — ~15 700 lignes en base.
    """
    filters, params = _build_filters(source, categorie, date_debut, date_fin)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    total = db.execute(
        text(f"SELECT COUNT(*) FROM inflation_unified {where}"), params
    ).scalar()

    rows = db.execute(
        text(f"""
            SELECT date_obs, pays, categorie, valeur, source, base_ref
            FROM inflation_unified {where}
            ORDER BY date_obs DESC
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": limit, "offset": offset},
    ).fetchall()

    return InflationResponse(
        total=total,
        limit=limit,
        offset=offset,
        data=[
            InflationPoint(
                date_obs=r.date_obs,
                pays=r.pays,
                categorie=r.categorie,
                valeur=r.valeur,
                source=r.source,
                base_ref=r.base_ref,
            )
            for r in rows
        ],
    )


@router.get("/tendance")
def get_tendance(
    source: str = Query(..., description="Source : ECB | INSEE | DATAGOUV | EUROSTAT"),
    categorie: Optional[str] = Query(None, description="Catégorie COICOP (recherche partielle)"),
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Moyenne mensuelle de l'inflation par source — périmètre France uniquement.
    Endpoint principal pour les graphiques Streamlit.
    """
    filters = ["source = :source"]
    params: dict = {"source": source.upper()}

    if categorie:
        filters.append("categorie ILIKE :categorie")
        params["categorie"] = f"%{categorie}%"
    if date_debut:
        filters.append("date_obs >= :date_debut")
        params["date_debut"] = date_debut
    if date_fin:
        filters.append("date_obs <= :date_fin")
        params["date_fin"] = date_fin

    where = "WHERE " + " AND ".join(filters)
    rows = db.execute(
        text(f"""
            SELECT date_obs AS mois,
                   ROUND(AVG(valeur), 4)          AS valeur_moy,
                   COUNT(DISTINCT categorie)       AS nb_categories
            FROM inflation_unified
            {where}
            GROUP BY date_obs
            ORDER BY mois
        """),
        params,
    ).fetchall()

    return {
        "pays": "FR",
        "source": source.upper(),
        "nb_points": len(rows),
        "data": [
            {
                "mois": str(r.mois),
                "valeur_moy": float(r.valeur_moy),
                "nb_categories": r.nb_categories,
            }
            for r in rows
        ],
    }



@router.get("/sources")
def get_sources(db: Session = Depends(get_db)):
    """Liste des sources disponibles."""
    rows = db.execute(
        text("SELECT DISTINCT source FROM inflation_unified ORDER BY source")
    ).fetchall()
    return {"sources": [r.source for r in rows]}


@router.get("/date-range")
def get_date_range(
    source: str = Query(..., description="Source : ECB | INSEE | DATAGOUV | EUROSTAT"),
    db: Session = Depends(get_db),
):
    """Retourne la première et dernière date disponible pour une source."""
    row = db.execute(
        text("""
            SELECT MIN(date_obs) AS date_min, MAX(date_obs) AS date_max
            FROM inflation_unified
            WHERE source = :source
        """),
        {"source": source.upper()},
    ).fetchone()

    if not row or not row.date_min:
        raise HTTPException(status_code=404, detail=f"Aucune donnée pour source={source.upper()}")

    return {
        "source":    source.upper(),
        "date_min":  str(row.date_min),
        "date_max":  str(row.date_max),
        "annee_min": row.date_min.year,
        "annee_max": row.date_max.year,
    }


@router.get("/categories")
def get_categories(
    source: Optional[str] = Query(None, description="Filtrer par source"),
    db: Session = Depends(get_db),
):
    """Liste des catégories COICOP disponibles, optionnellement filtrées par source."""
    if source:
        rows = db.execute(
            text("""
                SELECT DISTINCT categorie
                FROM inflation_unified
                WHERE source = :source
                ORDER BY categorie
            """),
            {"source": source.upper()},
        ).fetchall()
    else:
        rows = db.execute(
            text("SELECT DISTINCT categorie FROM inflation_unified ORDER BY categorie")
        ).fetchall()
    return {"categories": [r.categorie for r in rows]}


@router.get("/top-categories")
def get_top_categories(
    source: str = Query("EUROSTAT", description="Source : ECB | INSEE | DATAGOUV | EUROSTAT"),
    date_debut: Optional[date] = Query(None, description="Date de début (YYYY-MM-DD)"),
    date_fin: Optional[date] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    limit: int = Query(5, ge=1, le=13, description="Nombre de catégories (max 13)"),
    db: Session = Depends(get_db),
):
    """
    Top N catégories les plus inflationnistes sur une période.
    Classées par valeur moyenne décroissante.
    """
    params: dict = {"source": source.upper(), "limit": limit}
    date_filter = ""
    if date_debut:
        date_filter += " AND date_obs >= :date_debut"
        params["date_debut"] = date_debut
    if date_fin:
        date_filter += " AND date_obs <= :date_fin"
        params["date_fin"] = date_fin

    rows = db.execute(
        text(f"""
            SELECT categorie,
                   ROUND(AVG(valeur), 2) AS inflation_moy,
                   ROUND(MAX(valeur), 2) AS pic,
                   COUNT(*)              AS nb_observations
            FROM inflation_unified
            WHERE source = :source {date_filter}
            GROUP BY categorie
            ORDER BY inflation_moy DESC
            LIMIT :limit
        """),
        params,
    ).fetchall()

    return {
        "source": source.upper(),
        "nb_categories": len(rows),
        "data": [
            {
                "rang": i + 1,
                "categorie": r.categorie,
                "inflation_moy": float(r.inflation_moy),
                "pic": float(r.pic),
                "nb_observations": r.nb_observations,
            }
            for i, r in enumerate(rows)
        ],
    }


@router.get("/comparaison-sources")
def get_comparaison_sources(
    categorie: str = Query(..., description="Catégorie COICOP (recherche partielle, ex: alimentation)"),
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Compare les 4 sources sur la même catégorie et la même période.
    Démontre la valeur de la normalisation : INSEE, DATAGOUV, ECB et EUROSTAT
    côte à côte sur des données comparables.
    """
    params: dict = {"categorie": f"%{categorie}%"}
    date_filter = ""
    if date_debut:
        date_filter += " AND date_obs >= :date_debut"
        params["date_debut"] = date_debut
    if date_fin:
        date_filter += " AND date_obs <= :date_fin"
        params["date_fin"] = date_fin

    rows = db.execute(
        text(f"""
            SELECT source,
                   base_ref,
                   ROUND(AVG(valeur), 2)  AS valeur_moy,
                   ROUND(MIN(valeur), 2)  AS valeur_min,
                   ROUND(MAX(valeur), 2)  AS valeur_max,
                   COUNT(*)               AS nb_observations,
                   MIN(date_obs)          AS date_debut,
                   MAX(date_obs)          AS date_fin
            FROM inflation_unified
            WHERE categorie ILIKE :categorie {date_filter}
            GROUP BY source, base_ref
            ORDER BY source
        """),
        params,
    ).fetchall()

    return {
        "categorie_filtre": categorie,
        "nb_sources": len(rows),
        "data": [
            {
                "source":          r.source,
                "base_ref":        r.base_ref,
                "valeur_moy":      float(r.valeur_moy),
                "valeur_min":      float(r.valeur_min),
                "valeur_max":      float(r.valeur_max),
                "nb_observations": r.nb_observations,
                "date_debut":      str(r.date_debut),
                "date_fin":        str(r.date_fin),
            }
            for r in rows
        ],
    }


@router.get("/resume")
def get_resume(db: Session = Depends(get_db)):
    """
    KPIs globaux du projet : volume total, couverture temporelle par source,
    dernière valeur IPC connue (INSEE, catégorie Ensemble).
    Endpoint de synthèse — idéal pour un widget de tableau de bord.
    """
    sources_rows = db.execute(
        text("""
            SELECT source, base_ref,
                   COUNT(*)       AS nb_obs,
                   MIN(date_obs)  AS date_min,
                   MAX(date_obs)  AS date_max
            FROM inflation_unified
            GROUP BY source, base_ref
            ORDER BY source
        """)
    ).fetchall()

    derniere = db.execute(
        text("""
            SELECT valeur, date_obs
            FROM inflation_unified
            WHERE source = 'INSEE'
              AND categorie ILIKE '%ensemble%'
              AND categorie NOT ILIKE '%hors%'
            ORDER BY date_obs DESC
            LIMIT 1
        """)
    ).fetchone()

    total = db.execute(text("SELECT COUNT(*) FROM inflation_unified")).scalar()

    return {
        "total_observations": total,
        "nb_sources": len(sources_rows),
        "derniere_valeur_ipc": {
            "valeur":    float(derniere.valeur) if derniere else None,
            "date_obs":  str(derniere.date_obs) if derniere else None,
            "source":    "INSEE",
            "categorie": "00 - Ensemble",
        },
        "sources": [
            {
                "source":          r.source,
                "base_ref":        r.base_ref,
                "nb_observations": r.nb_obs,
                "date_debut":      str(r.date_min),
                "date_fin":        str(r.date_max),
            }
            for r in sources_rows
        ],
    }


def _build_filters(source, categorie, date_debut, date_fin):
    filters, params = [], {}
    if source:
        filters.append("source = :source")
        params["source"] = source.upper()
    if categorie:
        filters.append("categorie ILIKE :categorie")
        params["categorie"] = f"%{categorie}%"
    if date_debut:
        filters.append("date_obs >= :date_debut")
        params["date_debut"] = date_debut
    if date_fin:
        filters.append("date_obs <= :date_fin")
        params["date_fin"] = date_fin
    return filters, params
