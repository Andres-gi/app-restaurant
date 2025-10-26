# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. URL de Conexión
# Formato: "postgresql://<usuario>:<contraseña>@<host>:<puerto>/<nombre_db>"
# ¡¡ASEGÚRATE DE CAMBIAR "tu_contraseña_aqui"!!
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:Ianfelipe1%40@localhost:5432/restaurante_db"


# 2. El "Motor" (Engine) de SQLAlchemy
# Es el punto de entrada principal a la base de datos.
engine = create_engine(SQLALCHEMY_DATABASE_URL)


# 3. La Fábrica de Sesiones (SessionLocal)
# Cada instancia de SessionLocal será una sesión de base de datos.
# Estas son las sesiones que usaremos en nuestros endpoints.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 4. La Base Declarativa (Base)
# Crearemos nuestras tablas (Modelos) heredando de esta clase.
Base = declarative_base()