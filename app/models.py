from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
import enum
from datetime import datetime

# =======================================================
# ENUMS
# =======================================================

class CategoriaProducto(enum.Enum):
    comida = "comida"
    bebestible_general = "bebestible_general"
    bebestible_alcohol = "bebestible_alcohol"

class RolUsuario(enum.Enum):
    mesero = "mesero"
    cocina = "cocina"
    bar = "bar"
    admin = "admin"

class EstadoMesa(enum.Enum):
    libre = "libre"
    ocupada = "ocupada"
    pendiente_pago = "pendiente_pago"

class EstadoPedido(enum.Enum):
    nuevo = "nuevo"
    en_preparacion = "en_preparacion"
    listo_para_servir = "listo_para_servir"
    servido = "servido"
    cerrado = "cerrado"

class EstadoItem(enum.Enum):
    pendiente = "pendiente"
    en_preparacion = "en_preparacion"
    listo = "listo"

# =======================================================
# MODELOS
# =======================================================

class Producto(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True, unique=True)
    precio = Column(Float)
    categoria = Column(Enum(CategoriaProducto))
    disponible = Column(Boolean, default=True)


class Usuario(Base):
    """Modelo para Meseros, Cocineros y Bartman."""
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True, unique=True)
    pin = Column(String, unique=True) # PIN único para identificación (usado en login/búsqueda)
    password_hash = Column(String) # <<< CRÍTICO: Aquí se guarda el hash del PIN
    rol = Column(Enum(RolUsuario))
    pedidos = relationship("Pedido", back_populates="mesero")


class Mesa(Base):
    """Modelo para las mesas del restaurante."""
    __tablename__ = "mesas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True)
    estado = Column(Enum(EstadoMesa), default=EstadoMesa.libre)
    pedido_actual = relationship("Pedido", back_populates="mesa", uselist=False)


class Pedido(Base):
    """Modelo para la orden principal de la mesa."""
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    mesa_id = Column(Integer, ForeignKey("mesas.id"))
    mesero_id = Column(Integer, ForeignKey("usuarios.id"))
    estado = Column(Enum(EstadoPedido), default=EstadoPedido.nuevo)
    total = Column(Float, default=0.0)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    mesa = relationship("Mesa", back_populates="pedido_actual")
    mesero = relationship("Usuario", back_populates="pedidos")
    items = relationship("ItemPedido", back_populates="pedido")


class ItemPedido(Base):
    """Modelo para cada producto dentro de un pedido."""
    __tablename__ = "items_pedido"
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"))
    cantidad = Column(Integer)
    estado = Column(Enum(EstadoItem), default=EstadoItem.pendiente)
    destino = Column(String)

    pedido = relationship("Pedido", back_populates="items")
    producto = relationship("Producto")
