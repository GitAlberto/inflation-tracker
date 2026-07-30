# =============================================================================
# Dockerfile — Application Streamlit (C17/C19 — déploiement cloud Railway)
# Port : 8501
# =============================================================================
FROM python:3.12-slim

WORKDIR /app

# Dépendances Streamlit uniquement — pas de prophet/pyspark/jupyter
RUN pip install --no-cache-dir \
    streamlit==1.40.2 \
    plotly==5.24.1 \
    requests==2.32.3 \
    python-dotenv==1.0.1 \
    pandas==2.2.3

# Copie du package app/ dans /app/app/
# sys.path ajoute /app/ au démarrage — imports "from app.xxx" fonctionnent
COPY app/ ./app/

EXPOSE 8501

# headless=true : désactive l'ouverture automatique du navigateur (inutile en container)
CMD ["streamlit", "run", "app/main.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
