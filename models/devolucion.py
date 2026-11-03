from __future__ import annotations

from .base import db


class Devolucion(db.Model):
    """Devolución asociada a una Venta (folio), procesada por un usuario."""

    __tablename__ = "Devoluciones"

    id_devolucion: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_venta: int = db.Column(
        db.Integer, db.ForeignKey("Ventas.id_venta"), nullable=False
    )
    id_usuario: int = db.Column(
        db.Integer, db.ForeignKey("Usuario.id_usuario"), nullable=False
    )
    cant_dev: int = db.Column(db.Integer, nullable=False)
    fecha_dev: str = db.Column(db.String(20), nullable=False)
    destino: str = db.Column(db.String(60), nullable=False)  # Stock, Merma

    # N:1
    venta = db.relationship("Venta", back_populates="devoluciones")
    usuario = db.relationship("Usuario", back_populates="devoluciones")

    def __init__(
        self,
        id_venta: int,
        id_usuario: int,
        cant_dev: int,
        fecha_dev: str,
        destino: str,
    ) -> None:
        self.id_venta = id_venta
        self.id_usuario = id_usuario
        self.cant_dev = cant_dev
        self.fecha_dev = fecha_dev
        self.destino = destino

    def __repr__(self) -> str:
        return f"<Devolucion {self.id_devolucion}: venta={self.id_venta} destino={self.destino}>"
