# =============================================================================
# Dockerfile — API modèle Prophet (C19 — Livraison continue)
# Port : 8002
# =============================================================================
# python:3.12-slim = image officielle allégée (~130Mo vs ~1Go pour la full)
FROM python:3.12-slim

WORKDIR /app

# Dépendances API modèle uniquement — sans pyspark/jupyter/statsmodels (inutiles en prod)
# prophet installe cmdstanpy comme dépendance — CmdStan binaire NOT requis pour l'inférence
RUN pip install --no-cache-dir \
    fastapi==0.115.5 \
    uvicorn[standard]==0.32.1 \
    pydantic==2.10.1 \
    python-dotenv==1.0.1 \
    prometheus-client==0.21.1 \
    prophet==1.1.6 \
    numpy==1.26.4 \
    pandas==2.2.3 \
    joblib==1.4.2

# Copie du code source complet
COPY . .

EXPOSE 8002

# host 0.0.0.0 requis pour que le port soit accessible depuis l'extérieur du container
CMD ["uvicorn", "api.model.main:app", "--host", "0.0.0.0", "--port", "8002"]
