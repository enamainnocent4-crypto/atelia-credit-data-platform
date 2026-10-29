# Image de l'API core banking d'Atelia Crédit
FROM python:3.12-slim

# Pas de fichiers .pyc, logs affichés immédiatement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CORE_BANKING_DATA_DIR=/data/core_banking

WORKDIR /app

# Les dépendances d'abord : Docker garde cette couche en cache tant que
# requirements.txt ne change pas, ce qui accélère les reconstructions.
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/

# L'application ne tourne pas en administrateur (root) dans le conteneur
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
