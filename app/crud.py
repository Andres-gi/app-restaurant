# crud.py (VERSIÓN FINAL CON WEBSOCKETS)
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from . import models, schemas
from .models import CategoriaProducto, EstadoItem, EstadoPedido, EstadoMesa
from .auth import get_password_hash
from .websocket_manager import manager
import json
from typing import List

# --- FUNCIÓN 1: OBTENER TODOS LOS PRODUCTOS (GET) ---
def get_productos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Producto).offset(skip).limit(limit).all()

# --- FUNCIÓN 2: CREAR UN PRODUCTO (POST) ---
def create_producto(db: Session, producto: schemas.ProductoCreate):
    try:
        categoria_enum = CategoriaProducto(producto.categoria)
    except ValueError:
        raise ValueError(f"Categoría '{producto.categoria}' inválida.")

    db_producto = models.Producto(
        nombre=producto.nombre,
        precio=producto.precio,
        categoria=categoria_enum,
        disponible=producto.disponible
    )

    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto

# --- FUNCIÓN 3: CREAR USUARIO (POST) ---
def create_user(db: Session, user: schemas.UsuarioCreate):
    if user.rol not in [r.value for r in models.RolUsuario]:
        raise ValueError(f"Rol inválido: {user.rol}. Debe ser uno de: {list(models.RolUsuario)}.")

    hashed_pin = get_password_hash(user.pin) 

    db_user = models.Usuario(
        nombre=user.nombre,
        pin=hashed_pin,
        rol=models.RolUsuario(user.rol)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- FUNCIÓN 4: CREAR PEDIDO (POST) ---
def create_pedido(db: Session, pedido: schemas.PedidoCreate):
    
    # Verificar y actualizar estado de la mesa
    mesa = db.query(models.Mesa).filter(models.Mesa.id == pedido.mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")
    if mesa.estado != models.EstadoMesa.libre:
        raise HTTPException(status_code=400, detail=f"Mesa {mesa.nombre} ya está ocupada o pendiente de pago.")
        
    mesa.estado = models.EstadoMesa.ocupada # Cambiar estado de la mesa

    # Crear el pedido principal
    db_pedido = models.Pedido(
        mesa_id=pedido.mesa_id,
        mesero_id=pedido.mesero_id,
        estado=models.EstadoPedido.nuevo
    )
    db.add(db_pedido)
    db.flush() # Forzar la asignación de db_pedido.id antes del commit

    total_pedido = 0.0
    items_destino = {'comida': 'cocina', 'bebestible_general': 'bar', 'bebestible_alcohol': 'bar'}
    
    # Crear los ítems de pedido
    for item in pedido.items:
        producto = db.query(models.Producto).filter(models.Producto.id == item.producto_id).first()
        if not producto or not producto.disponible:
            raise HTTPException(status_code=400, detail=f"Producto ID {item.producto_id} no disponible.")
        
        # Determinar destino (cocina o bar)
        destino = items_destino.get(producto.categoria.value, 'cocina') 
        
        db_item = models.ItemPedido(
            pedido_id=db_pedido.id,
            producto_id=item.producto_id,
            cantidad=item.cantidad,
            destino=destino,
            estado=models.EstadoItem.pendiente
        )
        db.add(db_item)
        total_pedido += producto.precio * item.cantidad
        
    db_pedido.total = total_pedido # Actualizar el total
    
    db.commit()
    db.refresh(db_pedido)
    return db_pedido

# --- FUNCIÓN 7: OBTENER TAREAS PENDIENTES (GET) ---
def get_tareas_pendientes(db: Session, destino: str) -> List[schemas.TareaItem]:
    """
    Devuelve los ItemPedido con estado 'pendiente' o 'en_preparacion'
    para un destino específico ('cocina' o 'bar').
    """
    # Filtramos por destino y estado, y usamos joinedload para cargar las relaciones
    db_items = db.query(models.ItemPedido)\
        .filter(
            models.ItemPedido.destino == destino,
            models.ItemPedido.estado.in_([EstadoItem.pendiente, EstadoItem.en_preparacion])
        )\
        .options(
            joinedload(models.ItemPedido.producto),
            joinedload(models.ItemPedido.pedido).joinedload(models.Pedido.mesa)
        )\
        .all()
    
    return [schemas.TareaItem.from_orm(item) for item in db_items]


# --- FUNCIÓN 8: MARCAR ÍTEM COMO LISTO (PUT) ---
# 🚨 ESTA ES LA FUNCIÓN CRÍTICA DE WEBSOCKETS 🚨
async def marcar_item_listo(db: Session, item_id: int): 
    """
    Marca un ItemPedido como 'listo' y comprueba si el Pedido principal está completo.
    Si está completo, notifica vía WebSockets.
    """
    db_item = db.query(models.ItemPedido).filter(models.ItemPedido.id == item_id).first()
    
    if not db_item:
        raise HTTPException(status_code=404, detail="Item de pedido no encontrado")
    if db_item.estado == models.EstadoItem.listo:
        return db_item
        
    # 1. Marcar el ítem individual como listo
    db_item.estado = models.EstadoItem.listo
    db.commit()
    db.refresh(db_item)
    
    # 2. Comprobar si el Pedido principal está ahora listo
    pedido_id = db_item.pedido_id
    
    # Contar los ítems pendientes o en preparación para este pedido
    items_pendientes_count = db.query(models.ItemPedido)\
        .filter(
            models.ItemPedido.pedido_id == pedido_id,
            models.ItemPedido.estado.in_([EstadoItem.pendiente, EstadoItem.en_preparacion])
        ).count()
        
    if items_pendientes_count == 0:
        # Todos los ítems están listos, actualizamos el Pedido principal
        db_pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
        
        # Cargar la mesa para la notificación
        mesa = db.query(models.Mesa).filter(models.Mesa.id == db_pedido.mesa_id).first()

        if db_pedido and db_pedido.estado == EstadoPedido.nuevo:
            db_pedido.estado = EstadoPedido.listo_para_servir
            db.commit()
            
            # 🚨 LÓGICA DE WEBSOCKETS: Notificación a las Meseras
            notification_message = json.dumps({
                "type": "PEDIDO_LISTO",
                "pedido_id": pedido_id,
                "mesa_nombre": mesa.nombre
            })
            await manager.broadcast(notification_message)

            print(f"!!! WEBSOCKET BROADCAST: Pedido {pedido_id} de {mesa.nombre} está listo para servir !!!")
            
    return db_item


# --- FUNCIÓN 9: MARCAR PEDIDO COMO SERVIDO (PUT) ---
def marcar_pedido_servido(db: Session, pedido_id: int):
    """
    La mesera marca el pedido como SERVIDO (Entregado al cliente).
    Solo puede pasar a SERVIDO si está 'listo_para_servir'.
    """
    db_pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    
    if not db_pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    if db_pedido.estado == models.EstadoPedido.listo_para_servir:
        db_pedido.estado = models.EstadoPedido.servido
        db.commit()
        db.refresh(db_pedido)
        return db_pedido
    else:
        raise HTTPException(status_code=400, 
            detail=f"El pedido no se puede marcar como SERVIDO. Estado actual: {db_pedido.estado.value}"
        )


# --- FUNCIÓN 10: CERRAR Y PAGAR PEDIDO (PUT) ---
def cerrar_pedido(db: Session, pedido_id: int):
    """
    Cierra el pedido, marca la mesa como LIBRE y registra el pago.
    Solo puede cerrarse si está en estado 'servido'.
    """
    db_pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    
    if not db_pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    mesa = db_pedido.mesa

    if db_pedido.estado in [models.EstadoPedido.servido, models.EstadoPedido.listo_para_servir]:
        # 1. Cerrar el pedido
        db_pedido.estado = models.EstadoPedido.cerrado
        
        # 2. Liberar la mesa
        mesa.estado = models.EstadoMesa.libre
        
        db.commit()
        db.refresh(db_pedido)
        return db_pedido
    else:
        raise HTTPException(status_code=400, 
            detail=f"El pedido no se puede cerrar. Estado actual: {db_pedido.estado.value}"
        )