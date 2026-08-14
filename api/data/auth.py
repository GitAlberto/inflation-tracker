"""
=============================================================================
C10 — Authentification API data — X-API-Key (deux niveaux)
=============================================================================
Deux niveaux d'accès contrôlés par le header HTTP X-API-Key :

  verify_user_key  → accepte API_KEY (admin) OU API_KEY_USER
                     Routes publiques : consultation données, prédictions
  verify_admin_key → accepte uniquement API_KEY (admin)
                     Routes sensibles : stats agrégées, export complet

Variables .env :
    API_KEY       = clé administrateur (accès complet)
    API_KEY_USER  = clé utilisateur (accès lecture publique)

Issue GitHub : #11 (C5) #22 (C10)
=============================================================================
"""

import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

# Header HTTP attendu : X-API-Key: <valeur>
# auto_error=True : FastAPI rejette automatiquement les requêtes sans header
# et marque la sécurité comme obligatoire dans Swagger (cadenas fermé par défaut)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def verify_admin_key(key: str | None = Security(_api_key_header)) -> str:
    """Admin uniquement — API_KEY requis. Routes sensibles (stats, exports)."""
    expected_admin = os.getenv("API_KEY")
    if not expected_admin or not key or key != expected_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès administrateur requis. Clé admin dans X-API-Key.",
        )
    return key


def verify_user_key(key: str | None = Security(_api_key_header)) -> str:
    """User ou admin — API_KEY ou API_KEY_USER acceptés. Routes publiques."""
    expected_admin = os.getenv("API_KEY")
    expected_user  = os.getenv("API_KEY_USER")
    valid = {k for k in [expected_admin, expected_user] if k}
    if not key or key not in valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé API manquante ou invalide. Fournir le header X-API-Key.",
        )
    return key


# Alias rétrocompatibilité — les tests existants utilisent verify_key (= admin)
verify_key = verify_admin_key
