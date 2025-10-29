from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Importaciones de la aplicación
from app import schemas, models
from app.database import get_db
from app.crud import get_productos, create_producto
from app.main import get_current_user # Asumo que get_current_user está en app.main

router = APIRouter(
    prefix="/api/v1/gestion",
    tags=["Gestión (Admin/Inventario)"],
    # Se añade la dependencia de seguridad a nivel de router
    dependencies=[Depends(get_current_user)] 
)

# --- FUNCIÓN DE VERIFICACIÓN DE ROL ---
def check_admin(current_user: models.Usuario):
    """Verifica si el usuario actual tiene el rol de administrador."""
    if current_user.rol.value != models.RolUsuario.admin.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden realizar esta acción."
        )

# =======================================================
# RUTAS DE PRODUCTOS (Menú)
# =======================================================

@router.get("/productos", response_model=List[schemas.Producto])
def read_productos(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    """Obtiene la lista de todos los productos (elementos del menú)."""
    # Consulta simple, sin necesidad de ser admin
    return get_productos(db)

@router.post("/productos", response_model=schemas.Producto, status_code=status.HTTP_201_CREATED)
def create_new_producto(
    producto: schemas.ProductoCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Crea un nuevo producto en el menú. Requiere rol 'admin'."""
    check_admin(current_user)

    # Comprobar si ya existe un producto con ese nombre
    existing_producto = db.query(models.Producto).filter(models.Producto.nombre == producto.nombre).first()
    if existing_producto:
        raise HTTPException(status_code=400, detail="Ya existe un producto con este nombre.")

    return create_producto(db, producto=producto)


# =======================================================
# RUTAS DE MESAS
# =======================================================

@router.get("/mesas", response_model=List[schemas.Mesa])
def read_mesas(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    """Obtiene la lista de todas las mesas y su estado."""
    # Podría ser accesible por Meseros y Admin
    return db.query(models.Mesa).all()

@router.post("/mesas", response_model=schemas.Mesa, status_code=status.HTTP_201_CREATED)
def create_new_mesa(
    mesa: schemas.MesaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Crea una nueva mesa. Requiere rol 'admin'."""
    check_admin(current_user)

    # Comprobar si ya existe una mesa con ese nombre
    existing_mesa = db.query(models.Mesa).filter(models.Mesa.nombre == mesa.nombre).first()
    if existing_mesa:
        raise HTTPException(status_code=400, detail="Ya existe una mesa con este nombre.")

    db_mesa = models.Mesa(nombre=mesa.nombre)
    db.add(db_mesa)
    db.commit()
    db.refresh(db_mesa)
    return db_mesa
