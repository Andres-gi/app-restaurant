# auth.py
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

# ----------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------

# Secreto usado para firmar los tokens (¡CAMBIAR EN PRODUCCIÓN!)
SECRET_KEY = "tu-clave-secreta-muy-larga-y-aleatoria"
ALGORITHM = "HS256"
# El token expira después de 30 minutos
ACCESS_TOKEN_EXPIRE_MINUTES = 30 

# Contexto para hashear contraseñas (usa bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Esquema de seguridad para FastAPI (usamos el PIN como "password")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# ----------------------------------------------------------------
# FUNCIONES DE PIN/PASSWORD
# ----------------------------------------------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si el PIN plano coincide con el PIN hasheado."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera el hash de un PIN/password."""
    return pwd_context.hash(password)


# ----------------------------------------------------------------
# FUNCIONES DE JWT
# ----------------------------------------------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea el token JWT con la información del usuario (ID, rol)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    """Decodifica el token y maneja la expiración o invalidez."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        user_role: str = payload.get("role")
        if user_id is None or user_role is None:
            raise JWTError
        return {"user_id": user_id, "role": user_role}
    except JWTError:
        # Se lanza si el token es inválido o expiró
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas o token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )