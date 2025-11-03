# app/crud.py
"""
Implementación mínima de operaciones CRUD necesarias para las rutas del proyecto.
Esta versión usa SQLAlchemy ORM y espera que los modelos en app.models estén definidos.
Incluye validaciones básicas y raise de HTTPException en casos esperados.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from . import models, schemas
from typing import List

# Productos
def get_productos(db: Session, skip: int = 0, limit: int = 100) -> List[models.Producto]:
    return db.query(models.Producto).offset(skip).limit(limit).all()

def create_producto(db: Session, producto: schemas.ProductoCreate) -> models.Producto:
    # Validaciones básicas
    if producto.precio < 0:
        raise ValueError("El precio no puede ser negativo.")
    # Validar categoría si se desea (se acepta como string con valores del enum)
    existing = db.query(models.Producto).filter(models.Producto.nombre == producto.nombre).first()
    if existing:
        raise ValueError("Ya existe un producto con ese nombre.")
    db_producto = models.Producto(
        nombre=producto.nombre,
        precio=producto.precio,
        categoria=producto.categoria,  # SQLAlchemy Enum aceptará la string si coincide
        disponible=producto.disponible if producto.disponible is not None else True
    )
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto

# Usuarios / Autenticación
def get_user_by_name(db: Session, username: str):
    """Retorna el usuario por nombre (nombre en la tabla usuarios)."""
    return db.query(models.Usuario).filter(models.Usuario.nombre == username).first()

# Pedidos y items
def create_pedido(db: Session, pedido: schemas.PedidoCreate) -> models.Pedido:
    # Validar mesa y mesero
    mesa = db.query(models.Mesa).filter(models.Mesa.id == pedido.mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=400, detail="Mesa no encontrada.")
    mesero = db.query(models.Usuario).filter(models.Usuario.id == pedido.mesero_id).first()
    if not mesero:
        raise HTTPException(status_code=400, detail="Mesero no encontrado.")

    db_pedido = models.Pedido(
        mesa_id=pedido.mesa_id,
        mesero_id=pedido.mesero_id,
        estado=models.EstadoPedido.nuevo,
        total=0.0
    )
    db.add(db_pedido)
    db.commit()
    db.refresh(db_pedido)

    total = 0.0
    items_created = []
    for item in pedido.items:
        producto = db.query(models.Producto).filter(models.Producto.id == item.producto_id).first()
        if not producto:
            # Rollback parcial y error
            db.delete(db_pedido)
            db.commit()
            raise HTTPException(status_code=400, detail=f"Producto con id {item.producto_id} no encontrado.")
        db_item = models.ItemPedido(
            pedido_id=db_pedido.id,
            producto_id=item.producto_id,
            cantidad=item.cantidad,
            estado=models.EstadoItem.pendiente,
            destino=models.DestinoItem.cocina if producto.categoria == "comida" else models.DestinoItem.bar
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        items_created.append(db_item)
        total += (producto.precio or 0.0) * item.cantidad

    # Actualizar total
    db_pedido.total = total
    db.commit()
    db.refresh(db_pedido)
    return db_pedido

def get_tareas_pendientes(db: Session, destino: str):
    """Devuelve ítems pendientes por destino ('cocina' o 'bar')."""
    if destino not in [d.value for d in models.DestinoItem]:
        raise HTTPException(status_code=400, detail="Destino inválido.")
    return db.query(models.ItemPedido).filter(
        models.ItemPedido.destino == destino,
        models.ItemPedido.estado == models.EstadoItem.pendiente
    ).all()

def marcar_item_listo(db: Session, item_id: int) -> models.ItemPedido:
    item = db.query(models.ItemPedido).filter(models.ItemPedido.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ítem no encontrado.")
    # sólo si está en preparación o pendiente
    item.estado = models.EstadoItem.listo
    db.commit()
    db.refresh(item)
    return item

def marcar_pedido_servido(db: Session, pedido_id: int) -> models.Pedido:
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    pedido.estado = models.EstadoPedido.servido
    db.commit()
    db.refresh(pedido)
    return pedido

def cerrar_pedido(db: Session, pedido_id: int) -> models.Pedido:
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    pedido.estado = models.EstadoPedido.cerrado
    db.commit()
    db.refresh(pedido)
    return pedido
