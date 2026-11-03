from __future__ import annotations

from .base import db


class Historial(db.Model):
    """Movimiento de inventario (Entrada, Salida, Merma, Ajuste)."""

    __tablename__ = "Historial"

    id_movimiento: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_item: int = db.Column(
        db.Integer, db.ForeignKey("Catalogo.id_item"), nullable=False
    )
    id_usuario: int = db.Column(
        db.Integer, db.ForeignKey("Usuario.id_usuario"), nullable=False
    )
    tipo_mov: str = db.Column(db.String(60), nullable=False)
    cant_mov: int = db.Column(db.Integer, nullable=False)
    fecha_mov: str = db.Column(db.String(20), nullable=False)

    # N:1
    item = db.relationship("Catalogo", back_populates="movimientos")
    usuario = db.relationship("Usuario", back_populates="movimientos")

    def __init__(
        self,
        id_item: int,
        id_usuario: int,
        tipo_mov: str,
        cant_mov: int,
        fecha_mov: str,
    ) -> None:
        self.id_item = id_item
        self.id_usuario = id_usuario
        self.tipo_mov = tipo_mov
        self.cant_mov = cant_mov
        self.fecha_mov = fecha_mov

    def __repr__(self) -> str:
        return f"<Historial {self.id_movimiento}: {self.tipo_mov} x{self.cant_mov}>"
