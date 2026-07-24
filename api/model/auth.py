"""
=============================================================================
C9 — Authentification API modèle — X-API-Key
=============================================================================
Vérifie la clé API passée dans le header HTTP X-API-Key sur chaque requête.
La clé est stockée dans .env (variable API_KEY) — jamais en dur dans le code.

Usage dans les routes :
    from api.model.auth import verify_key
    from fastapi import Security

    @router.get("/endpoint")
    def my_endpoint(key: str = Security(verify_key)):
        ...

Issue GitHub : #15 (C9)
=============================================================================
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

# L'API modèle n'a pas de base de données → charger .env explicitement ici
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env", override=True)

# Header HTTP attendu : X-API-Key: <valeur>
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_key(key: str | None = Security(_api_key_header)) -> str:
    """
    Dépendance FastAPI — vérifie que le header X-API-Key correspond à API_KEY dans .env.
    Lève HTTP 403 si la clé est absente ou incorrecte.
    """
    expected = os.getenv("API_KEY")
    # Clé absente ou ne correspond pas → accès refusé
    if not expected or not key or key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé API manquante ou invalide. Fournir le header X-API-Key.",
        )
    return key  # retourné pour injection optionnelle dans le handler
