from __future__ import annotations

from typing import Optional

from .base import db


class Proveedor(db.Model):
    """Proveedor que surte productos al catálogo."""

    __tablename__ = "Proveedor"

    id_proveedor: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nom_prov: str = db.Column(db.String(60), nullable=False)
    tel_prov: Optional[str] = db.Column(db.String(15), nullable=True)

    # 1:M -> Un Proveedor surte muchos ítems del Catálogo
    items = db.relationship("Catalogo", back_populates="proveedor", lazy=True)

    def __init__(self, nom_prov: str, tel_prov: Optional[str] = None) -> None:
        self.nom_prov = nom_prov
        self.tel_prov = tel_prov

    def __repr__(self) -> str:
        return f"<Proveedor {self.id_proveedor}: {self.nom_prov}>"
