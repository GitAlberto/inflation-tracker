"""
C5 — Routes /api/inflation — exposition de inflation_unified
Issue GitHub : #11
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.data.database import get_db
from api.data.schemas import InflationResponse, InflationPoint

router = APIRouter(prefix="/inflation", tags=["inflation"])


@router.get("", response_model=InflationResponse)
def get_inflation(
    pays: Optional[str] = Query(None, description="Code pays ISO (ex: FR, DE, AT)"),
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
    Pagination obligatoire — 3.68M lignes en base.
    """
    filters, params = _build_filters(pays, source, categorie, date_debut, date_fin)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    total = db.execute(
        text(f"SELECT COUNT(*) FROM inflation_unified {where}"), params
    ).scalar()

    rows = db.execute(
        text(f"""
            SELECT date_obs, pays, categorie, valeur, source
            FROM inflation_unified {where}
            ORDER BY date_obs DESC, pays
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
            )
            for r in rows
        ],
    )


@router.get("/tendance")
def get_tendance(
    pays: str = Query(..., description="Code pays ISO (ex: FR, DE)"),
    source: str = Query(..., description="Source : ECB | INSEE | DATAGOUV | EUROSTAT"),
    categorie: Optional[str] = Query(None, description="Catégorie COICOP (recherche partielle)"),
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Moyenne mensuelle de l'inflation par pays/source.
    Endpoint principal pour les graphiques Grafana et Streamlit.
    """
    filters = ["pays = :pays", "source = :source"]
    params: dict = {"pays": pays.upper(), "source": source.upper()}

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
        "pays": pays.upper(),
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


@router.get("/pays")
def get_pays(db: Session = Depends(get_db)):
    """Liste des codes pays disponibles dans inflation_unified."""
    rows = db.execute(
        text("SELECT DISTINCT pays FROM inflation_unified ORDER BY pays")
    ).fetchall()
    return {"pays": [r.pays for r in rows]}


@router.get("/sources")
def get_sources(db: Session = Depends(get_db)):
    """Liste des sources disponibles."""
    rows = db.execute(
        text("SELECT DISTINCT source FROM inflation_unified ORDER BY source")
    ).fetchall()
    return {"sources": [r.source for r in rows]}


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


def _build_filters(pays, source, categorie, date_debut, date_fin):
    filters, params = [], {}
    if pays:
        filters.append("pays = :pays")
        params["pays"] = pays.upper()
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
