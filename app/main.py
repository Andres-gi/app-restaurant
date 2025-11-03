# app/main.py
"""
Aplicación FastAPI principal. Rutas principales, WebSocket y health-check.
Se corrigieron: sintaxis errónea en marcar_item_como_listo, uso consistente de token decoding,
y pequeños ajustes para evitar await sobre funciones sync.
"""

from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles
from typing import List
from .websocket_manager import manager
import json
from sqlalchemy import text
from . import models, schemas, crud
from .database import engine, get_db
from . import auth

# Si necesitas crear tablas automáticamente en dev:
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de App de Restaurante",
    description="El backend para gestionar pedidos, mesas y menú.",
    version="0.1.0"
)

# incluye routers en archivos separados (asegúrate de importarlos en package)
from .routers import auth as auth_router
app.include_router(auth_router.router)

app.mount("/static", StaticFiles(directory="static"), name="static")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(auth.oauth2_scheme)):
    """
    Valida token y retorna instancia de Usuario desde DB.
    decode_access_token devuelve {'user_id': int, 'role': str}
    """
    token_data = auth.decode_access_token(token)
    user = db.query(models.Usuario).filter(models.Usuario.id == token_data['user_id']).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@app.get("/")
def leer_raiz():
    return {"mensaje": "¡Bienvenido al backend del restaurante!"}

@app.post("/productos/", response_model=schemas.Producto)
def crear_producto(
    producto: schemas.ProductoCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.value not in ['admin']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado. Solo Admin.")

    try:
        return crud.create_producto(db=db, producto=producto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno al crear el producto.")

@app.get("/productos/", response_model=List[schemas.Producto])
def leer_productos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    productos = crud.get_productos(db, skip=skip, limit=limit)
    return productos

@app.post("/pedidos/", response_model=schemas.Pedido)
def tomar_pedido(
    pedido: schemas.PedidoCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.value != 'mesero':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo los meseros pueden tomar pedidos.")
    if pedido.mesero_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes tomar pedidos a nombre de otro mesero.")
    try:
        return crud.create_pedido(db=db, pedido=pedido)
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno al procesar el pedido.")

@app.get("/tareas/cocina/", response_model=List[schemas.TareaItem])
def obtener_tareas_cocina(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.value not in ['cocina', 'admin']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a Cocina.")
    return crud.get_tareas_pendientes(db, destino='cocina')

@app.get("/tareas/bar/", response_model=List[schemas.TareaItem])
def obtener_tareas_bar(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.value not in ['bar', 'admin']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a Bar.")
    return crud.get_tareas_pendientes(db, destino='bar')

@app.put("/item-pedido/{item_id}/listo", response_model=schemas.ItemPedido)
def marcar_item_como_listo(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Validación de rol
    if current_user.rol.value not in ['cocina', 'bar', 'admin']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo personal de producción puede usar este endpoint.")
    try:
        return crud.marcar_item_listo(db, item_id=item_id)
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno al actualizar el ítem.")

@app.put("/pedidos/{pedido_id}/servido", response_model=schemas.Pedido)
def pedido_servido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.value not in ['mesero', 'admin']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo meseros pueden servir pedidos.")
    try:
        return crud.marcar_pedido_servido(db, pedido_id)
    except HTTPException as e:
        raise e

@app.put("/pedidos/{pedido_id}/cerrado", response_model=schemas.Pedido)
def pedido_cerrado(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.value not in ['mesero', 'admin']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo meseros pueden cerrar pedidos.")
    try:
        return crud.cerrar_pedido(db, pedido_id)
    except HTTPException as e:
        raise e

@app.websocket("/ws/notifications/")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"type": "PONG", "message": f"Server received: {data}"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Error en el WebSocket: {e}")
        manager.disconnect(websocket)

@app.get("/health")
def check_health(db: Session = Depends(get_db)):
    try:
        # simple select para verificar conexión
        db.execute(text("SELECT 1"))
        # no es estrictamente necesario commit en SELECT, pero lo dejamos
        db.commit()
        return {
            "status": "ok",
            "database_connection": "successful",
            "api_version": app.version
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail={
            "status": "error",
            "database_connection": "failed",
            "detail": str(e)
        })
