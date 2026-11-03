"""Utilidades compartidas por los controladores."""
from __future__ import annotations

import math
from contextlib import contextmanager
from datetime import date, datetime
from typing import Iterator, Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError

from models import db

FORMATOS_FECHA: tuple[str, ...] = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
)

TIPOS_ITEM: Tuple[str, ...] = ("Producto", "Servicio", "Insumo")
TIPOS_FISICOS: Tuple[str, ...] = ("Producto", "Insumo")


class ReglaNegocioError(ValueError):
    """Error de validación o regla de negocio con un mensaje apto para mostrarse al usuario."""


class BaseController:
 

    @staticmethod
    def parsear_fecha(texto: Optional[str]) -> Optional[datetime]:
       
        if not texto:
            return None
        for formato in FORMATOS_FECHA:
            try:
                return datetime.strptime(texto.strip(), formato)
            except ValueError:
                continue
        return None

    @staticmethod
    def hoy() -> date:
        return date.today()

    @staticmethod
    def ahora_texto() -> str:
    
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def a_entero(
        texto: Optional[str],
        campo: str,
        minimo: Optional[int] = None,
        defecto: Optional[int] = None,
    ) -> int:
       
        limpio = (texto or "").strip()
        if not limpio:
            if defecto is not None:
                return defecto
            raise ReglaNegocioError(f"El campo «{campo}» es obligatorio.")
        try:
            valor = int(limpio)
        except ValueError as exc:
            raise ReglaNegocioError(f"El campo «{campo}» debe ser un número entero.") from exc
        if minimo is not None and valor < minimo:
            raise ReglaNegocioError(f"El campo «{campo}» debe ser mayor o igual a {minimo}.")
        return valor

    @staticmethod
    def a_decimal(texto: Optional[str], campo: str, minimo: float = 0.0) -> float:
       
        limpio = (texto or "").strip()
        if not limpio:
            raise ReglaNegocioError(f"El campo «{campo}» es obligatorio.")
        try:
            valor = float(limpio)
        except ValueError as exc:
            raise ReglaNegocioError(f"El campo «{campo}» debe ser un número.") from exc
        if not math.isfinite(valor) or valor < minimo:
            raise ReglaNegocioError(f"El campo «{campo}» debe ser mayor o igual a {minimo:g}.")
        return valor

    @contextmanager
    def transaccion(self) -> Iterator[None]:
        """Confirma al salir sin error; ante cualquier fallo hace rollback."""
        try:
            yield
            db.session.commit()
        except ReglaNegocioError:
            db.session.rollback()
            raise
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise ReglaNegocioError("No se pudo guardar el registro en la base de datos.") from exc
        except Exception:
            db.session.rollback()
            raise
