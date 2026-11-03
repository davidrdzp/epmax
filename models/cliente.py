from __future__ import annotations

from typing import Optional

from .base import db


class Cliente(db.Model):
    """Cliente del estudio."""

    __tablename__ = "Cliente"

    id_cliente: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nom_cl: str = db.Column(db.String(60), nullable=False)
    tel_cl: Optional[str] = db.Column(db.String(15), nullable=True)
    gen_cl: Optional[str] = db.Column(db.String(15), nullable=True)

    # 1:M -> Un Cliente registra muchas Ventas
    ventas = db.relationship("Venta", back_populates="cliente", lazy=True)

    def __init__(
        self,
        nom_cl: str,
        tel_cl: Optional[str] = None,
        gen_cl: Optional[str] = None,
    ) -> None:
        self.nom_cl = nom_cl
        self.tel_cl = tel_cl
        self.gen_cl = gen_cl

    def __repr__(self) -> str:
        return f"<Cliente {self.id_cliente}: {self.nom_cl}>"
