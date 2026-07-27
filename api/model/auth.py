"""
=============================================================================
C10 — Authentification API modèle — X-API-Key (deux niveaux)
=============================================================================
Deux niveaux d'accès contrôlés par le header HTTP X-API-Key :

  verify_user_key  → accepte API_KEY (admin) OU API_KEY_USER
                     Routes publiques : /predict/{categorie}, /categories
  verify_admin_key → accepte uniquement API_KEY (admin)
                     Routes sensibles : /metrics, /predict (toutes catégories)

Variables .env :
    API_KEY       = clé administrateur (accès complet)
    API_KEY_USER  = clé utilisateur (accès lecture publique)

Issue GitHub : #15 (C9) #22 (C10)
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


def verify_admin_key(key: str | None = Security(_api_key_header)) -> str:
    """Admin uniquement — API_KEY requis. Routes sensibles (métriques, export)."""
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
