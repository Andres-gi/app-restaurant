# app/routers/pedidos.py
"""
Router para pedidos. Se quitaron awaits en llamadas sync y se agregaron controles de permisos.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import schemas, models
from app.database import get_db
from app.crud import create_pedido, marcar_pedido_servido, cerrar_pedido
from app.main import get_current_user

router = APIRouter(
    prefix="/api/v1/pedidos",
    tags=["Pedidos (Meseros)"],
    dependencies=[Depends(get_current_user)]
)

def check_mesero(current_user: models.Usuario):
    if current_user.rol.value != models.RolUsuario.mesero.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los meseros pueden realizar esta acción."
        )

@router.post("/", response_model=schemas.Pedido, status_code=status.HTTP_201_CREATED)
def create_new_pedido(
    pedido: schemas.PedidoCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    check_mesero(current_user)
    if pedido.mesero_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes crear pedidos para tu propio ID de mesero."
        )
    return create_pedido(db, pedido=pedido)

@router.put("/{pedido_id}/servir", response_model=schemas.Pedido)
def mark_pedido_servido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    check_mesero(current_user)
    return marcar_pedido_servido(db, pedido_id=pedido_id)

@router.put("/{pedido_id}/cerrar", response_model=schemas.Pedido)
def close_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.value not in [models.RolUsuario.mesero.value, models.RolUsuario.admin.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo meseros o administradores pueden cerrar pedidos."
        )
    return cerrar_pedido(db, pedido_id=pedido_id)
