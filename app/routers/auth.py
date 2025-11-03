# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database import get_db
from app.models import Usuario
from app.auth import verify_password, create_access_token

router = APIRouter(prefix="/token", tags=["Autenticación"])

@router.post("/", summary="Genera token de acceso con usuario y PIN")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Valida nombre y PIN (bcrypt hash) y devuelve un token JWT.
    """
    user = db.query(Usuario).filter(Usuario.nombre == form_data.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar PIN con bcrypt
    if not verify_password(form_data.password, user.pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="PIN incorrecto",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Crear token JWT
    access_token_expires = timedelta(minutes=120)
    access_token = create_access_token(
        data={"user_id": user.id, "role": user.rol.value},
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}
