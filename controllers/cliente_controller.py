"""Alta y consulta de clientes."""
from __future__ import annotations

from typing import List, Mapping

from models import Cliente, db

from .base_controller import BaseController, ReglaNegocioError

GENEROS: tuple[str, ...] = ("Femenino", "Masculino", "Otro")


class ClienteController(BaseController):
    def listar(self) -> List[Cliente]:
        return list(db.session.scalars(db.select(Cliente).order_by(Cliente.nom_cl)))

    def registrar_cliente(self, datos: Mapping[str, str]) -> Cliente:
        """Valida y guarda un nuevo Cliente (nom_cl, tel_cl, gen_cl)."""
        nom_cl = (datos.get("nom_cl") or "").strip()
        tel_cl = (datos.get("tel_cl") or "").strip() or None
        gen_cl = (datos.get("gen_cl") or "").strip() or None

        if not nom_cl:
            raise ReglaNegocioError("El nombre del cliente es obligatorio.")
        if len(nom_cl) > 60:
            raise ReglaNegocioError("El nombre del cliente no puede exceder 60 caracteres.")
        if tel_cl is not None and (len(tel_cl) > 15 or not tel_cl.replace("+", "").replace("-", "").replace(" ", "").isdigit()):
            raise ReglaNegocioError("El teléfono debe contener solo dígitos (máximo 15 caracteres).")
        if gen_cl is not None and gen_cl not in GENEROS:
            raise ReglaNegocioError("Género no válido.")

        cliente = Cliente(nom_cl=nom_cl, tel_cl=tel_cl, gen_cl=gen_cl)
        with self.transaccion():
            db.session.add(cliente)
        return cliente
