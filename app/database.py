# database.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Cargar variables de entorno del archivo .env
load_dotenv()

# 1. URL de Conexión
# Leer la URL desde la variable de entorno, que se define en el shell
# o en un archivo .env. Esto es más seguro y flexible.
SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("La variable de entorno DATABASE_URL no está configurada.")

# 2. El "Motor" (Engine) de SQLAlchemy
# Es el punto de entrada principal a la base de datos.
# 'pool_pre_ping=True' ayuda a evitar desconexiones de PostgreSQL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True
)


# 3. La Fábrica de Sesiones (SessionLocal)
# Cada instancia de SessionLocal será una sesión de base de datos.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 4. La Base Declarativa (Base)
# Crearemos nuestras tablas (Modelos) heredando de esta clase.
Base = declarative_base()
 