#!/bin/bash
# start.sh

# 1. Comando para crear las tablas de la BD si no existen
# Esto es temporal, se reemplazará por Alembic en un proyecto real.
python -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"

# 2. Iniciar el servidor web de producción
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT