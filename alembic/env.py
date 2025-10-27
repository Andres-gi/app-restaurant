from logging.config import fileConfig

# Importaciones clave para la configuración de la BD
from sqlalchemy import create_engine
from sqlalchemy import pool

from alembic import context

# 🚨 Importaciones de FastAPI/App
import os
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv() 

# Importar la Base de los modelos de nuestra aplicación
from app.database import Base # <-- ¡IMPORTACIÓN CRÍTICA!

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 🚨 DEFINICIÓN DEL TARGET METADATA
# Conectamos todos nuestros modelos a Alembic
target_metadata = Base.metadata

def get_url():
    """Obtiene la URL de conexión a la BD desde las variables de entorno."""
    # Lee la URL de la variable de entorno DATABASE_URL (definida en el shell o en .env)
    # Esto es más robusto que depender de la interpolación de alembic.ini
    return os.environ.get("DATABASE_URL")

def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo 'offline'."""

    url = get_url()

    # Si no se encuentra la URL, intenta leer el fallback de alembic.ini
    if not url:
         url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones en modo 'online'."""
    
    url = get_url()
    
    if not url:
        # Fallback si no hay variable de entorno
        url = config.get_main_option("sqlalchemy.url")
        
    # Crear el motor de SQLAlchemy usando la URL obtenida
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
