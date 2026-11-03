from __future__ import annotations

from .base import db


class Venta(db.Model):
    """Venta de un ítem del catálogo a un cliente, procesada por un usuario."""

    __tablename__ = "Ventas"

    id_venta: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente: int = db.Column(
        db.Integer, db.ForeignKey("Cliente.id_cliente"), nullable=False
    )
    id_usuario: int = db.Column(
        db.Integer, db.ForeignKey("Usuario.id_usuario"), nullable=False
    )
    id_item: int = db.Column(
        db.Integer, db.ForeignKey("Catalogo.id_item"), nullable=False
    )
    fecha_v: str = db.Column(db.String(20), nullable=False)
    cant_v: int = db.Column(db.Integer, nullable=False)

    # N:1
    cliente = db.relationship("Cliente", back_populates="ventas")
    usuario = db.relationship("Usuario", back_populates="ventas")
    item = db.relationship("Catalogo", back_populates="ventas")

    # 1:M -> Una Venta puede generar muchas Devoluciones
    devoluciones = db.relationship("Devolucion", back_populates="venta", lazy=True)

    def __init__(
        self,
        id_cliente: int,
        id_usuario: int,
        id_item: int,
        fecha_v: str,
        cant_v: int,
    ) -> None:
        self.id_cliente = id_cliente
        self.id_usuario = id_usuario
        self.id_item = id_item
        self.fecha_v = fecha_v
        self.cant_v = cant_v

    def __repr__(self) -> str:
        return f"<Venta {self.id_venta}: item={self.id_item} cant={self.cant_v}>"
