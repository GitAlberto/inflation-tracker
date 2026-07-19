# =============================================================================
# Dockerfile — API data REST (C19 — Livraison continue)
# Port : 8001
# =============================================================================
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Sous-ensemble des dépendances : on exclut prophet/pyspark (lourds, inutiles ici)
# L'image data n'a pas besoin de CmdStan ni de la JVM
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    sqlalchemy \
    psycopg2-binary \
    python-dotenv \
    pydantic

COPY . .

EXPOSE 8001

CMD ["uvicorn", "api.data.main:app", "--host", "0.0.0.0", "--port", "8001"]
