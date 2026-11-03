from __future__ import annotations

from .base import db


class Categoria(db.Model):
    """Categoría que agrupa ítems del catálogo."""

    __tablename__ = "Categoria"

    id_categoria: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nom_cat: str = db.Column(db.String(60), nullable=False)

    # 1:M -> Una Categoría agrupa muchos ítems del Catálogo
    items = db.relationship("Catalogo", back_populates="categoria", lazy=True)

    def __init__(self, nom_cat: str) -> None:
        self.nom_cat = nom_cat

    def __repr__(self) -> str:
        return f"<Categoria {self.id_categoria}: {self.nom_cat}>"
