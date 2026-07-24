"""
C5 — Routes /api/prix-alimentaires — exposition de openfoodfacts
Issue GitHub : #11
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.data.auth import verify_key
from api.data.database import get_db
from api.data.schemas import PrixResponse, PrixAlimentaire

# dependencies=[Security(verify_key)] protège toutes les routes de ce router (C5)
router = APIRouter(prefix="/prix-alimentaires", tags=["prix-alimentaires"], dependencies=[Security(verify_key)])


@router.get("", response_model=PrixResponse)
def get_prix(
    categorie: Optional[str] = Query(None, description="Catégorie alimentaire (recherche partielle)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Prix de produits alimentaires collectés via Open Food Facts."""
    filters, params = [], {}
    if categorie:
        filters.append("categorie ILIKE :categorie")
        params["categorie"] = f"%{categorie}%"

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    total = db.execute(
        text(f"SELECT COUNT(*) FROM openfoodfacts {where}"), params
    ).scalar()

    rows = db.execute(
        text(f"""
            SELECT produit, categorie, prix_unitaire, date_collecte, url
            FROM openfoodfacts {where}
            ORDER BY date_collecte DESC
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": limit, "offset": offset},
    ).fetchall()

    return PrixResponse(
        total=total,
        limit=limit,
        offset=offset,
        data=[
            PrixAlimentaire(
                produit=r.produit,
                categorie=r.categorie,
                prix_unitaire=r.prix_unitaire,
                date_collecte=r.date_collecte,
                url=r.url,
            )
            for r in rows
        ],
    )


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """Liste des catégories alimentaires disponibles."""
    rows = db.execute(
        text("SELECT DISTINCT categorie FROM openfoodfacts ORDER BY categorie")
    ).fetchall()
    return {"categories": [r.categorie for r in rows]}


@router.get("/stats")
def get_stats(
    categorie: Optional[str] = Query(None, description="Filtrer par catégorie"),
    db: Session = Depends(get_db),
):
    """Prix moyen, min et max par catégorie alimentaire."""
    if categorie:
        rows = db.execute(
            text("""
                SELECT categorie,
                       ROUND(AVG(prix_unitaire), 2) AS prix_moy,
                       MIN(prix_unitaire)            AS prix_min,
                       MAX(prix_unitaire)            AS prix_max,
                       COUNT(*)                      AS nb_produits
                FROM openfoodfacts
                WHERE categorie ILIKE :categorie
                  AND prix_unitaire IS NOT NULL
                GROUP BY categorie
                ORDER BY categorie
            """),
            {"categorie": f"%{categorie}%"},
        ).fetchall()
    else:
        rows = db.execute(
            text("""
                SELECT categorie,
                       ROUND(AVG(prix_unitaire), 2) AS prix_moy,
                       MIN(prix_unitaire)            AS prix_min,
                       MAX(prix_unitaire)            AS prix_max,
                       COUNT(*)                      AS nb_produits
                FROM openfoodfacts
                WHERE prix_unitaire IS NOT NULL
                GROUP BY categorie
                ORDER BY categorie
            """)
        ).fetchall()

    return {
        "data": [
            {
                "categorie": r.categorie,
                "prix_moy": float(r.prix_moy) if r.prix_moy else None,
                "prix_min": float(r.prix_min) if r.prix_min else None,
                "prix_max": float(r.prix_max) if r.prix_max else None,
                "nb_produits": r.nb_produits,
            }
            for r in rows
        ]
    }
