from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

# Importaciones de la aplicación
from app.database import get_db
from app.schemas import Token # Importamos el esquema de respuesta del Token
from app.auth import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.crud import get_user_by_pin # <<< CRUCIAL: Búsqueda por PIN

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Autenticación"],
)

# Endpoint para el login
@router.post("/token", response_model=Token)
async def login_for_access_token(
    # Usamos OAuth2PasswordRequestForm.
    # El campo 'username' se usa para el PIN de identificación.
    # El campo 'password' se usa para el PIN de verificación.
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    Autentica al usuario usando el PIN.

    NOTA: Utiliza 'username' para el PIN de identificación y 'password' para el PIN
    de verificación debido a la estructura de OAuth2PasswordRequestForm.
    """

    pin_id = form_data.username  # PIN de identificación (debe ser único)
    pin_password = form_data.password # PIN de contraseña (para hasheo)

    # 1. Buscar usuario por PIN de identificación
    user = get_user_by_pin(db, pin=pin_id)

    if not user:
        # El PIN de identificación no existe
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Verificar el PIN de contraseña contra el hash almacenado
    # Verificamos el PIN ingresado contra el hash guardado en user.password_hash
    if not verify_password(pin_password, user.password_hash): 
        # La verificación del PIN falló
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Generar el Token JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Payload: 'sub' (ID) y 'role' para control de acceso
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.rol.value}, # Convertimos el Enum a string
        expires_delta=access_token_expires
    )

    # 4. Retornar el token y la información del usuario
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "user_role": user.rol.value # Retornamos el valor string del Enum
    }
