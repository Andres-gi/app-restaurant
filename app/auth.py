# app/auth.py (ACTUALIZADO para usar .env)
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, status
import os # <-- NUEVO
from dotenv import load_dotenv # <-- NUEVO

# Cargar variables de entorno desde el archivo .env
load_dotenv() 

# --- CONFIGURACIÓN DE SEGURIDAD ---

# Obtener variables del .env o usar un valor por defecto (MALA PRÁCTICA en producción)
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-inseguro-si-falla-el-env") 
ALGORITHM = "HS256"
# Convertir la variable de entorno a entero
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)) 

# ... El resto del archivo auth.py sigue igual ...

# Contexto para el hashing de contraseñas (PIN)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema para el token OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- FUNCIONES DE HASHING ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# --- FUNCIONES DE JWT ---

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    # Asegúrate de que 'sub' esté presente antes de crear el token
    if 'sub' not in to_encode:
        # El sub es el identificador principal (aquí usamos el id del usuario)
        raise ValueError("Token data must contain 'sub' key (User ID)")
        
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la credencial",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Validar si el ID y Rol están presentes
        user_id: int = payload.get("sub")
        user_role: str = payload.get("role")
        
        if user_id is None or user_role is None:
            raise credentials_exception
        
        # Devolvemos un diccionario con las claves que get_current_user espera
        return {"user_id": user_id, "role": user_role}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token ha expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise credentials_exception