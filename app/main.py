# main.py (VERSIÓN FINAL CON WEBSOCKETS)
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles
from typing import List
from .websocket_manager import manager
import json
from sqlalchemy import text

from . import models, schemas, crud 
from .database import SessionLocal, engine 

from sqlalchemy.orm import relationship

from datetime import timedelta
from . import auth
from .auth import oauth2_scheme 
from fastapi.security import OAuth2PasswordRequestForm 

# Esta línea es la magia que crea las tablas al inicio (ya la tenemos)
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de App de Restaurante",
    description="El backend para gestionar pedidos, mesas y menú.",
    version="0.1.0"
)

# ----------------------------------------------------------------
# FUNCIÓN DE DEPENDENCIA (Inyección de Dependencias de FastAPI)
# ----------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# ----------------------------------------------------------------
# CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS
# ----------------------------------------------------------------
# Monta la carpeta 'static' para que los archivos sean accesibles en /static
app.mount("/static", StaticFiles(directory="static"), name="static")
# ----------------------------------------------------------------
# FUNCIÓN DE SEGURIDAD (Obtiene el usuario logueado)
# ----------------------------------------------------------------
def get_current_user(db: Session = Depends(get_db), token: str = Depends(auth.oauth2_scheme)):
    # Decodificar el token para obtener el ID y rol
    token_data = auth.decode_access_token(token) 
    
    # Buscar el usuario en la base de datos
    user = db.query(models.Usuario).filter(models.Usuario.id == token_data['user_id']).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# Define un "endpoint" o "ruta"
@app.get("/")
def leer_raiz():
    return {"mensaje": "¡Bienvenido al backend del restaurante!"}


# ----------------------------------------------------------------
# ENDPOINTS DE AUTENTICACIÓN
# ----------------------------------------------------------------

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    # 1. Buscar usuario y verificar PIN
    user = db.query(models.Usuario).filter(models.Usuario.nombre == form_data.username).first()
    
    if not user or not auth.verify_password(form_data.password, user.pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o PIN incorrecto",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Generar el token
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.id, "role": user.rol.value},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user_role": user.rol.value}


# ----------------------------------------------------------------
# ENDPOINTS PARA PRODUCTOS (EL MENÚ)
# ----------------------------------------------------------------

@app.post("/productos/", response_model=schemas.Producto)
def crear_producto(
    producto: schemas.ProductoCreate, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user) 
):
    """Permite al administrador agregar un nuevo ítem al menú."""
    if current_user.rol.value not in ['admin']:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado. Solo Admin.")

    try:
        return crud.create_producto(db=db, producto=producto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno al crear el producto.")


@app.get("/productos/", response_model=List[schemas.Producto])
def leer_productos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Devuelve la lista completa de productos del menú."""
    productos = crud.get_productos(db, skip=skip, limit=limit)
    return productos


# ----------------------------------------------------------------
# ENDPOINTS PARA LA TOMA DE PEDIDOS
# ----------------------------------------------------------------

@app.post("/pedidos/", response_model=schemas.Pedido)
def tomar_pedido(
    pedido: schemas.PedidoCreate, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user) 
):
    """La Mesera toma un pedido."""
    if current_user.rol.value != 'mesero':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo los meseros pueden tomar pedidos.")
    
    if pedido.mesero_id != current_user.id:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes tomar pedidos a nombre de otro mesero.")

    try:
        return crud.create_pedido(db=db, pedido=pedido)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno al procesar el pedido.")


# ----------------------------------------------------------------
# ENDPOINTS PARA VISTAS DE TAREAS (COCINA/BAR)
# ----------------------------------------------------------------

@app.get("/tareas/cocina/", response_model=List[schemas.TareaItem])
def obtener_tareas_cocina(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user) 
):
    """Devuelve todos los ítems de comida pendientes para la Cocina."""
    if current_user.rol.value not in ['cocina', 'admin']:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a Cocina.")

    return crud.get_tareas_pendientes(db, destino='cocina')


@app.get("/tareas/bar/", response_model=List[schemas.TareaItem])
def obtener_tareas_bar(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user) 
):
    """Devuelve todos los ítems de bebida pendientes para el Bar."""
    if current_user.rol.value not in ['bar', 'admin']:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a Bar.")
         
    return crud.get_tareas_pendientes(db, destino='bar')

# 🚨 CORREGIDO: AÑADIR 'async' y 'await'
@app.put("/item-pedido/{item_id}/listo", response_model=schemas.ItemPedido)
async def marcar_item_como_listo( # 🚨 AÑADIDO 'async'
    item_id: int, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user) 
):
    """El Cocinero/Bartman marca un ítem como LISTO (dispara notificación WS)."""
    if current_user.rol.value not in ['cocina', 'bar', 'admin']:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo personal de producción puede usar este endpoint.")

    try:
        # 🚨 AÑADIDO 'await'
        return await crud.marcar_item_listo(db, item_id=item_id) 
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno al actualizar el ítem.")


# ----------------------------------------------------------------
# ENDPOINTS PARA AVANCE DEL PEDIDO (MESERA)
# ----------------------------------------------------------------

@app.put("/pedidos/{pedido_id}/servido", response_model=schemas.Pedido)
def pedido_servido(
    pedido_id: int, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user) 
):
    """La mesera marca el pedido como Servido (entregado al cliente)."""
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
    """Cierra el pedido y libera la mesa (Simula el pago)."""
    if current_user.rol.value not in ['mesero', 'admin']:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo meseros pueden cerrar pedidos.")

    try:
        return crud.cerrar_pedido(db, pedido_id)
    except HTTPException as e:
        raise e

# ----------------------------------------------------------------
# ENDPOINT DE WEBSOCKETS (MESERAS)
# ----------------------------------------------------------------

@app.websocket("/ws/notifications/")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint que usan las tablets de las Meseras para escuchar 
    cuando un pedido está listo.
    """
    await manager.connect(websocket)
    try:
        # Loop que mantiene la conexión abierta
        while True:
            # Necesario para detectar la desconexión
            data = await websocket.receive_text() 
            # Respuesta opcional (PONG)
            await websocket.send_text(json.dumps({"type": "PONG", "message": f"Server received: {data}"}))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Error en el WebSocket: {e}")
        manager.disconnect(websocket)
# ----------------------------------------------------------------
# ENDPOINT DE SALUD Y MONITOREO
# ----------------------------------------------------------------

@app.get("/health")
def check_health(db: Session = Depends(get_db)):
    """
    Verifica la salud de la API y la conexión a la base de datos.
    """
    try:
        # Intenta ejecutar una consulta simple para verificar la conexión a DB
        db.execute(text("SELECT 1"))
        db.commit()
        
        return {
            "status": "ok",
            "database_connection": "successful",
            "api_version": app.version
        }
    except Exception as e:
        # Si la consulta falla, algo está mal con la base de datos
        raise HTTPException(status_code=503, detail={
            "status": "error",
            "database_connection": "failed",
            "detail": str(e)
        })