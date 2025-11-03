# app/routers/tareas.py
"""
Router de tareas. Se eliminó el uso de await sobre funciones sincrónicas en crud.
Se agregaron validaciones para 'destino'.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import schemas, models
from app.database import get_db
from app.crud import get_tareas_pendientes, marcar_item_listo
from app.main import get_current_user

router = APIRouter(
    prefix="/api/v1/tareas",
    tags=["Tareas (Cocina/Bar)"],
    dependencies=[Depends(get_current_user)]
)

def check_produccion(current_user: models.Usuario):
    if current_user.rol.value not in [models.RolUsuario.cocina.value, models.RolUsuario.bar.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo personal de Cocina o Bar puede acceder a esta ruta."
        )

@router.get("/pendientes/{destino}", response_model=List[schemas.TareaItem])
def read_tareas_pendientes(
    destino: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    check_produccion(current_user)
    if current_user.rol.value != destino and current_user.rol.value != models.RolUsuario.admin.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tu rol '{current_user.rol.value}' no te permite ver tareas de '{destino}'."
        )
    return get_tareas_pendientes(db, destino=destino)

@router.put("/listo/{item_id}", response_model=schemas.ItemPedido)
def mark_item_as_ready(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    check_produccion(current_user)
    db_item = marcar_item_listo(db, item_id=item_id)

    if db_item.destino != current_user.rol.value and current_user.rol.value != models.RolUsuario.admin.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No tienes permiso para marcar este ítem, pertenece a '{db_item.destino}'."
        )
    return db_item
