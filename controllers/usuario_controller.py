"""Autenticación y consulta de usuarios."""
from __future__ import annotations

import re
from hmac import compare_digest
from typing import List, Mapping, Optional, Tuple

from models import Usuario, db

from .base_controller import BaseController, ReglaNegocioError

ROL_ESTILISTA: str = "Estilista"
ROL_ADMIN: str = "Administrador"
ROLES: Tuple[str, ...] = (ROL_ADMIN, ROL_ESTILISTA)
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UsuarioController(BaseController):
    """Lógica de acceso y listados de usuarios."""

    def autenticar(self, correo_us: str, contra_us: str) -> Optional[Usuario]:
        """Devuelve el Usuario si las credenciales son válidas; None en caso contrario.

        Prototipo: `contra_us` se almacena tal cual (VARCHAR(60)); se compara en tiempo constante.
        """
        correo = (correo_us or "").strip().lower()
        if not correo or not contra_us:
            return None
        usuario = db.session.scalar(
            db.select(Usuario).where(db.func.lower(Usuario.correo_us) == correo)
        )
        if usuario is None:
            return None
        coincide = compare_digest(
            usuario.contra_us.encode("utf-8"), contra_us.encode("utf-8")
        )
        return usuario if coincide else None

    def registrar_usuario(self, datos: Mapping[str, str]) -> Usuario:
        """Valida y da de alta un Usuario (Administrador o Estilista)."""
        nom_us = " ".join((datos.get("nom_us") or "").split())
        rol_us = (datos.get("rol_us") or "").strip()
        tel_us = (datos.get("tel_us") or "").strip() or None
        correo_us = (datos.get("correo_us") or "").strip().lower()
        contra_us = datos.get("contra_us") or ""

        if not nom_us:
            raise ReglaNegocioError("El nombre del usuario es obligatorio.")
        if len(nom_us) > 60:
            raise ReglaNegocioError("El nombre del usuario no puede exceder 60 caracteres.")
        if rol_us not in ROLES:
            raise ReglaNegocioError("Selecciona un rol válido (Administrador o Estilista).")
        if tel_us is not None and (
            len(tel_us) > 15 or not tel_us.replace("+", "").replace("-", "").replace(" ", "").isdigit()
        ):
            raise ReglaNegocioError("El teléfono debe contener solo dígitos (máximo 15 caracteres).")
        if not PATRON_CORREO.match(correo_us) or len(correo_us) > 60:
            raise ReglaNegocioError("Ingresa un correo electrónico válido (máximo 60 caracteres).")
        if len(contra_us) < 6 or len(contra_us) > 60:
            raise ReglaNegocioError("La contraseña debe tener entre 6 y 60 caracteres.")
        if db.session.scalar(
            db.select(Usuario).where(db.func.lower(Usuario.correo_us) == correo_us)
        ) is not None:
            raise ReglaNegocioError("Ya existe un usuario con ese correo electrónico.")

        usuario = Usuario(nom_us, rol_us, correo_us, contra_us, tel_us)
        with self.transaccion():
            db.session.add(usuario)
        return usuario

    def listar_para_venta(self, id_usuario_sesion: Optional[int] = None) -> List[Usuario]:
        """Estilistas disponibles para atender una venta (más el usuario en sesión)."""
        consulta = db.select(Usuario).where(
            (Usuario.rol_us == ROL_ESTILISTA) | (Usuario.id_usuario == id_usuario_sesion)
        ).order_by(Usuario.nom_us)
        return list(db.session.scalars(consulta))
