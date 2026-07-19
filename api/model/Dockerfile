# =============================================================================
# Dockerfile — API modèle Prophet (C19 — Livraison continue)
# Port : 8002
# =============================================================================
# python:3.12-slim = image officielle allégée (~130Mo vs ~1Go pour la full)
FROM python:3.12-slim

WORKDIR /app

# Copie des dépendances en premier — couche Docker cachée si requirements.txt
# n'a pas changé (évite de réinstaller à chaque rebuild du code source)
COPY requirements.txt .

# --no-cache-dir évite de stocker le cache pip dans l'image finale
# prophet + cmdstanpy compilent CmdStan → peut prendre ~5 minutes à la première build
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source complet
COPY . .

EXPOSE 8002

# host 0.0.0.0 requis pour que le port soit accessible depuis l'extérieur du container
CMD ["uvicorn", "api.model.main:app", "--host", "0.0.0.0", "--port", "8002"]
