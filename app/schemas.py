# schemas.py
from pydantic import BaseModel
from typing import List, Optional

# =======================================================
# 1. SCHEMAS PARA PRODUCTO (MENÚ)
# =======================================================

class ProductoCreate(BaseModel):
    nombre: str
    precio: float
    categoria: str
    disponible: Optional[bool] = True

class Producto(BaseModel):
    id: int
    nombre: str
    precio: float
    categoria: str
    disponible: bool

    class Config:
        from_attributes = True

# =======================================================
# 2. SCHEMAS PARA USUARIO (PERSONAL)
# =======================================================

class UsuarioCreate(BaseModel):
    nombre: str
    pin: str
    rol: str

class Usuario(BaseModel):
    id: int
    nombre: str
    rol: str
    
    class Config:
        from_attributes = True

# =======================================================
# 3. SCHEMAS PARA MESA
# =======================================================

class MesaCreate(BaseModel):
    nombre: str

class Mesa(BaseModel):
    id: int
    nombre: str
    estado: str
    
    class Config:
        from_attributes = True

# =======================================================
# 4. SCHEMAS PARA PEDIDOS Y SUS ÍTEMS
# =======================================================

# Ítem individual para la ENTRADA (lo que la Mesera envía)
class ItemPedidoCreate(BaseModel):
    producto_id: int
    cantidad: int


# Pedido principal para la ENTRADA (lo que la Mesera envía)
class PedidoCreate(BaseModel):
    mesa_id: int
    mesero_id: int
    items: List[ItemPedidoCreate]


# Ítem individual para la SALIDA (lo que el backend devuelve)
class ItemPedido(BaseModel):
    id: int
    producto_id: int
    cantidad: int
    estado: str
    destino: str
    
    class Config:
        from_attributes = True

# Pedido principal para la SALIDA (lo que el backend devuelve)
class Pedido(BaseModel):
    id: int
    mesa_id: int
    mesero_id: int
    estado: str
    total: float
    # Incluimos los ítems para que la respuesta de creación sea completa
    items: List[ItemPedido] = [] 
    
    class Config:
        from_attributes = True
        # schemas.py (Añadir o verificar que exista en la sección de Pedidos/Tareas)

# --- SCHEMAS PARA LAS VISTAS DE TAREAS (COCINA/BAR) ---

# Schema para la Mesa dentro de la Tarea (solo el nombre)
class MesaSimple(BaseModel):
    nombre: str
    class Config:
        from_attributes = True

# Schema para el Pedido dentro de la Tarea (solo la ID y la Mesa)
class PedidoSimple(BaseModel):
    id: int
    # Debe coincidir con el nombre de la relación en el modelo Pedido
    mesa: MesaSimple 
    class Config:
        from_attributes = True

# El Schema que se usará para mostrar cada tarea en la pantalla de Cocina/Bar
class TareaItem(BaseModel):
    id: int
    cantidad: int
    estado: str
    destino: str
    
    # Estos dos son clave: Traen los datos relacionados (JOINEDLOAD en CRUD)
    producto: Producto # Usamos el schema Producto que ya definimos
    pedido: PedidoSimple
    
    class Config:
        from_attributes = True

# --- SCHEMAS PARA AUTENTICACIÓN ---

# Necesario para el endpoint de login
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # Añadimos el rol para que el frontend sepa a qué dashboard ir
    user_role: str

    access_token: str
    token_type: str = "bearer"
    # Añadimos el rol para que el frontend sepa a qué dashboard ir
    user_role: str 

# Esquema para el token que se usa en la seguridad de FastAPI
class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None