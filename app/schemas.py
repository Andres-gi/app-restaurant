# app/schemas.py
"""
Pydantic schemas para validación. Se usa orm_mode=True en Config para integración con SQLAlchemy.
Se corrigieron errores de sintaxis, removed stray paren, y Token definido claramente.
"""

from pydantic import BaseModel
from typing import List, Optional

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
        orm_mode = True

class UsuarioCreate(BaseModel):
    nombre: str
    pin: str
    rol: str

class Usuario(BaseModel):
    id: int
    nombre: str
    rol: str

    class Config:
        orm_mode = True

class MesaCreate(BaseModel):
    nombre: str

class Mesa(BaseModel):
    id: int
    nombre: str
    estado: str

    class Config:
        from_attributes = True

class ItemPedidoCreate(BaseModel):
    producto_id: int
    cantidad: int

class PedidoCreate(BaseModel):
    mesa_id: int
    mesero_id: int
    items: List[ItemPedidoCreate]

class ItemPedido(BaseModel):
    id: int
    producto_id: int
    cantidad: int
    estado: str
    destino: str

    class Config:
        orm_mode = True

class Pedido(BaseModel):
    id: int
    mesa_id: int
    mesero_id: int
    estado: str
    total: float
    items: List[ItemPedido] = []

    class Config:
        orm_mode = True

class MesaSimple(BaseModel):
    nombre: str
    class Config:
        orm_mode = True

class PedidoSimple(BaseModel):
    id: int
    mesa: MesaSimple
    class Config:
        orm_mode = True

class TareaItem(BaseModel):
    id: int
    cantidad: int
    estado: str
    destino: str
    producto: Producto
    pedido: PedidoSimple

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_role: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None
