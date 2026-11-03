"""Requerimientos c) trazabilidad de inventario y d) alertas preventivas."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional

from models import Catalogo, db

from .base_controller import TIPOS_FISICOS, BaseController


@dataclass
class MovimientoInventario:
    id_movimiento: int
    fecha_mov: str
    tipo_mov: str
    cant_mov: int
    usuario: str


@dataclass
class AlertaStock:
    id_item: int
    nom_item: str
    tipo_item: str
    stock: int
    stock_min: int


@dataclass
class AlertaCaducidad:
    id_item: int
    nom_item: str
    tipo_item: str
    fecha_caduc: str
    dias_restantes: int
    estado: str  # "Vencido" o "Por vencer"


@dataclass
class AlertasPreventivas:
    stock_bajo: List[AlertaStock] = field(default_factory=list)
    proximos_a_caducar: List[AlertaCaducidad] = field(default_factory=list)


class InventarioController(BaseController):
    """Consultas de inventario."""

    def trazabilidad_item(self, id_item: int) -> List[MovimientoInventario]:
        """Movimientos del Historial de un ítem en orden cronológico."""
        item = db.session.get(Catalogo, id_item)
        if item is None:
            raise ValueError(f"No existe el ítem con id_item={id_item}")

        movimientos = sorted(
            item.movimientos,
            key=lambda m: (self.parsear_fecha(m.fecha_mov) or datetime.min, m.id_movimiento),
        )
        return [
            MovimientoInventario(
                id_movimiento=m.id_movimiento,
                fecha_mov=m.fecha_mov,
                tipo_mov=m.tipo_mov,
                cant_mov=m.cant_mov,
                usuario=m.usuario.nom_us,
            )
            for m in movimientos
        ]

    def alertas_preventivas(
        self,
        dias_umbral: int = 30,
        fecha_referencia: Optional[date] = None,
    ) -> AlertasPreventivas:
        """Detecta stock bajo (`stock <= stock_min`) y caducidad vencida o próxima.

        Solo evalúa ítems de tipo Producto o Insumo. `fecha_referencia` (por defecto hoy)
        permite probar la lógica con otra fecha.
        """
        referencia: date = fecha_referencia or self.hoy()
        alertas = AlertasPreventivas()

        consulta = (
            db.select(Catalogo)
            .where(Catalogo.tipo_item.in_(TIPOS_FISICOS))
            .order_by(Catalogo.nom_item)
        )
        for item in db.session.scalars(consulta):
            stock: int = item.stock or 0
            stock_min: int = item.stock_min or 0
            if stock <= stock_min:
                alertas.stock_bajo.append(
                    AlertaStock(item.id_item, item.nom_item, item.tipo_item, stock, stock_min)
                )

            caducidad = self.parsear_fecha(item.fecha_caduc)
            if caducidad is None:
                continue
            dias: int = (caducidad.date() - referencia).days
            if dias <= dias_umbral:
                alertas.proximos_a_caducar.append(
                    AlertaCaducidad(
                        id_item=item.id_item,
                        nom_item=item.nom_item,
                        tipo_item=item.tipo_item,
                        fecha_caduc=item.fecha_caduc or "",
                        dias_restantes=dias,
                        estado="Vencido" if dias < 0 else "Por vencer",
                    )
                )
        alertas.proximos_a_caducar.sort(key=lambda a: a.dias_restantes)
        return alertas
