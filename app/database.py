# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator # Agregado para tipado correcto

# Configuración de la URL de tu base de datos
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:Ianfelipe1%40@localhost/restaurante_db"

# Creación del motor y la sesión
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ----------------------------------------------------------------
# FUNCIÓN DE DEPENDENCIA (Agregada aquí)
# ----------------------------------------------------------------
def get_db() -> Generator:
    """Retorna una sesión de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------------------------------------------
# NOTA: Asegúrate de que tus otras configuraciones de DB estén aquí.
# ----------------------------------------------------------------
