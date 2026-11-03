from __future__ import annotations

from typing import Optional

from .base import db


class Catalogo(db.Model):
    """Ítem del catálogo: producto de venta, insumo o servicio."""

    __tablename__ = "Catalogo"

    id_item: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_categoria: int = db.Column(
        db.Integer, db.ForeignKey("Categoria.id_categoria"), nullable=False
    )
    id_proveedor: int = db.Column(
        db.Integer, db.ForeignKey("Proveedor.id_proveedor"), nullable=False
    )
    nom_item: str = db.Column(db.String(60), nullable=False)
    tipo_item: str = db.Column(db.String(30), nullable=False)  # Producto, Servicio, Insumo
    precio_v: float = db.Column(db.Float, nullable=False)
    precio_c: float = db.Column(db.Float, nullable=False)
    stock: int = db.Column(db.Integer, default=0)
    stock_min: int = db.Column(db.Integer, default=0)
    stock_max: int = db.Column(db.Integer, default=0)
    fecha_caduc: Optional[str] = db.Column(db.String(20), nullable=True)

    # N:1 hacia Categoria y Proveedor
    categoria = db.relationship("Categoria", back_populates="items")
    proveedor = db.relationship("Proveedor", back_populates="items")

    # 1:M -> Un ítem aparece en muchas Ventas y registros de Historial
    ventas = db.relationship("Venta", back_populates="item", lazy=True)
    movimientos = db.relationship("Historial", back_populates="item", lazy=True)

    def __init__(
        self,
        id_categoria: int,
        id_proveedor: int,
        nom_item: str,
        tipo_item: str,
        precio_v: float,
        precio_c: float,
        stock: int = 0,
        stock_min: int = 0,
        stock_max: int = 0,
        fecha_caduc: Optional[str] = None,
    ) -> None:
        self.id_categoria = id_categoria
        self.id_proveedor = id_proveedor
        self.nom_item = nom_item
        self.tipo_item = tipo_item
        self.precio_v = precio_v
        self.precio_c = precio_c
        self.stock = stock
        self.stock_min = stock_min
        self.stock_max = stock_max
        self.fecha_caduc = fecha_caduc

    def __repr__(self) -> str:
        return f"<Catalogo {self.id_item}: {self.nom_item} ({self.tipo_item})>"
