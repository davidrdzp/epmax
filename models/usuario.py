from __future__ import annotations

from typing import List, Optional

from .base import db


class Usuario(db.Model):
    """Usuario del sistema (Administrador, Estilista, etc.)."""

    __tablename__ = "Usuario"

    id_usuario: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nom_us: str = db.Column(db.String(60), nullable=False)
    rol_us: str = db.Column(db.String(30), nullable=False)
    tel_us: Optional[str] = db.Column(db.String(15), nullable=True)
    correo_us: str = db.Column(db.String(60), unique=True, nullable=False)
    contra_us: str = db.Column(db.String(60), nullable=False)

    # 1:M -> Un Usuario procesa muchas Ventas, Devoluciones y movimientos de Historial
    ventas = db.relationship("Venta", back_populates="usuario", lazy=True)
    devoluciones = db.relationship("Devolucion", back_populates="usuario", lazy=True)
    movimientos = db.relationship("Historial", back_populates="usuario", lazy=True)

    def __init__(
        self,
        nom_us: str,
        rol_us: str,
        correo_us: str,
        contra_us: str,
        tel_us: Optional[str] = None,
    ) -> None:
        self.nom_us = nom_us
        self.rol_us = rol_us
        self.correo_us = correo_us
        self.contra_us = contra_us
        self.tel_us = tel_us

    def __repr__(self) -> str:
        return f"<Usuario {self.id_usuario}: {self.nom_us} ({self.rol_us})>"
