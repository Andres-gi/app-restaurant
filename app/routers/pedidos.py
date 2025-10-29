from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Importaciones de la aplicación
from app import schemas, models
from app.database import get_db
from app.crud import create_pedido, marcar_pedido_servido, cerrar_pedido
from app.main import get_current_user 

router = APIRouter(
    prefix="/api/v1/pedidos",
    tags=["Pedidos (Meseros)"],
    # Se añade la dependencia de seguridad a nivel de router
    dependencies=[Depends(get_current_user)] 
)

# --- FUNCIÓN DE VERIFICACIÓN DE ROL ---
def check_mesero(current_user: models.Usuario):
    """Verifica si el usuario actual tiene el rol de mesero."""
    if current_user.rol.value != models.RolUsuario.mesero.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los meseros pueden realizar esta acción."
        )


# =======================================================
# RUTAS PRINCIPALES DEL FLUJO DE PEDIDOS
# =======================================================

@router.post("/", response_model=schemas.Pedido, status_code=status.HTTP_201_CREATED)
def create_new_pedido(
    pedido: schemas.PedidoCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Crea un nuevo pedido, asocia ítems y marca la mesa como OCUPADA.
    Requiere rol 'mesero'.
    """
    check_mesero(current_user)

    # El mesero autenticado es quien está creando el pedido
    if pedido.mesero_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Solo puedes crear pedidos para tu propio ID de mesero."
        )

    # El CRUD se encargará de verificar la mesa y los productos
    return create_pedido(db, pedido=pedido)


@router.put("/{pedido_id}/servir", response_model=schemas.Pedido)
def mark_pedido_servido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Marca un pedido como SERVIDO (entregado al cliente). 
    Solo puede hacerse si el pedido está 'listo_para_servir'. Requiere rol 'mesero'.
    """
    check_mesero(current_user)

    # El CRUD contiene la lógica de validación de estado
    return marcar_pedido_servido(db, pedido_id=pedido_id)


@router.put("/{pedido_id}/cerrar", response_model=schemas.Pedido)
def close_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Cierra un pedido, lo marca como 'cerrado' y libera la mesa. 
    Requiere rol 'mesero' o 'admin'.
    """
    if current_user.rol.value not in [models.RolUsuario.mesero.value, models.RolUsuario.admin.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo meseros o administradores pueden cerrar pedidos."
        )

    # El CRUD contiene la lógica de validación de estado y liberación de mesa
    return cerrar_pedido(db, pedido_id=pedido_id)
