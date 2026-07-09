from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class InflationPoint(BaseModel):
    date_obs: date
    pays: str
    categorie: str
    valeur: Decimal
    source: str

    model_config = {"from_attributes": True}


class InflationResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: list[InflationPoint]


class PrixAlimentaire(BaseModel):
    produit: Optional[str]
    categorie: str
    prix_unitaire: Optional[Decimal]
    date_collecte: date
    url: Optional[str]

    model_config = {"from_attributes": True}


class PrixResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: list[PrixAlimentaire]
