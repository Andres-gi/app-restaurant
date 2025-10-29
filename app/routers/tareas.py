from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Importaciones de la aplicación
from app import schemas, models
from app.database import get_db
from app.crud import get_tareas_pendientes, marcar_item_listo
from app.main import get_current_user 

router = APIRouter(
    prefix="/api/v1/tareas",
    tags=["Tareas (Cocina/Bar)"],
    # Se añade la dependencia de seguridad a nivel de router
    dependencies=[Depends(get_current_user)] 
)

# --- FUNCIÓN DE VERIFICACIÓN DE ROL ---
def check_produccion(current_user: models.Usuario):
    """Verifica si el usuario actual tiene rol de cocina o bar."""
    if current_user.rol.value not in [models.RolUsuario.cocina.value, models.RolUsuario.bar.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo personal de Cocina o Bar puede acceder a esta ruta."
        )

# =======================================================
# RUTAS DE TAREAS PENDIENTES
# =======================================================

@router.get("/pendientes/{destino}", response_model=List[schemas.TareaItem])
def read_tareas_pendientes(
    destino: str, # 'cocina' o 'bar'
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Obtiene las tareas pendientes o en preparación para un destino ('cocina' o 'bar').
    El rol del usuario debe coincidir con el destino o ser 'admin'.
    """
    check_produccion(current_user) # Verifica que sea Cocina o Bar

    # Validación extra: si el usuario es 'cocina', solo puede ver tareas de 'cocina'.
    if current_user.rol.value != destino and current_user.rol.value != models.RolUsuario.admin.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tu rol '{current_user.rol.value}' no te permite ver tareas de '{destino}'."
        )

    return get_tareas_pendientes(db, destino=destino)


@router.put("/listo/{item_id}", response_model=schemas.ItemPedido)
async def mark_item_as_ready(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Marca un ítem de pedido como 'listo'. Si es el último ítem, notifica a las meseras vía WebSocket.
    Requiere rol 'cocina' o 'bar'.
    """
    check_produccion(current_user) # Verifica que sea Cocina o Bar

    # El CRUD se encarga de la lógica de estado y la notificación por WebSockets
    db_item = await marcar_item_listo(db, item_id=item_id)

    # Validación: el item debe pertenecer al área de trabajo del usuario
    if db_item.destino != current_user.rol.value and current_user.rol.value != models.RolUsuario.admin.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No tienes permiso para marcar este ítem, pertenece a '{db_item.destino}'."
        )

    return db_item
