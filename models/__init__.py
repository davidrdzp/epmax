"""Paquete de modelos de EPMAX. Importar todo aquí garantiza que create_all() vea cada tabla."""
from .base import db
from .catalogo import Catalogo
from .categoria import Categoria
from .cliente import Cliente
from .devolucion import Devolucion
from .historial import Historial
from .proveedor import Proveedor
from .usuario import Usuario
from .venta import Venta

__all__ = [
    "db",
    "Usuario",
    "Cliente",
    "Proveedor",
    "Categoria",
    "Catalogo",
    "Venta",
    "Devolucion",
    "Historial",
]
