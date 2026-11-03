"""Productividad por usuario, devoluciones por folio y registro de ventas."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from models import Catalogo, Cliente, Devolucion, Historial, Usuario, Venta, db

from .base_controller import TIPOS_FISICOS, BaseController, ReglaNegocioError
from .usuario_controller import ROL_ESTILISTA


@dataclass
class DetalleVenta:
    id_venta: int
    fecha_v: str
    cliente: str
    item: str
    cant_v: int
    precio_v: float
    subtotal: float
    estilista: str = ""
    tipo_item: str = ""
    id_usuario: int = 0


@dataclass
class ProductividadUsuario:
    id_usuario: int
    nom_us: str
    rol_us: str
    total_transacciones: int = 0
    total_piezas: int = 0
    ingreso_total: float = 0.0
    detalle: List[DetalleVenta] = field(default_factory=list)


@dataclass
class DetalleDevolucion:
    id_devolucion: int
    id_venta: int
    cant_dev: int
    fecha_dev: str
    autorizado_por: str
    destino: str


@dataclass
class ConsultaFolio:
    venta: DetalleVenta
    devoluciones: List[DetalleDevolucion]
    cant_devuelta: int = 0
    cant_disponible: int = 0   # piezas que aún pueden devolverse (vendidas - ya devueltas)


@dataclass
class ResumenVentas:
    total_ventas: int = 0
    ingreso_total: float = 0.0
    servicios_realizados: int = 0
    ventas_hoy: int = 0


DESTINOS_DEVOLUCION: Tuple[str, ...] = ("Stock", "Merma")


class VentasController(BaseController):
    """Consultas y registro de ventas y devoluciones."""

    # ------------------------------------------------------------------ consultas
    def productividad_usuario(self, id_usuario: int) -> ProductividadUsuario:
        """Resumen de productividad de un usuario/estilista a partir de sus ventas."""
        usuario = db.session.get(Usuario, id_usuario)
        if usuario is None:
            raise ValueError(f"No existe el usuario con id_usuario={id_usuario}")

        resumen = ProductividadUsuario(
            id_usuario=usuario.id_usuario, nom_us=usuario.nom_us, rol_us=usuario.rol_us
        )
        ventas: List[Venta] = sorted(
            usuario.ventas,
            key=lambda v: (self.parsear_fecha(v.fecha_v) or datetime.min, v.id_venta),
        )
        for venta in ventas:
            detalle = self._detalle(venta)
            resumen.detalle.append(detalle)
            resumen.total_piezas += venta.cant_v
            resumen.ingreso_total += detalle.subtotal
        resumen.total_transacciones = len(ventas)
        return resumen

    def productividad_estilistas(self) -> List[ProductividadUsuario]:
        """Productividad de todos los usuarios con rol Estilista, de mayor a menor ingreso."""
        estilistas = db.session.scalars(
            db.select(Usuario).where(Usuario.rol_us == ROL_ESTILISTA).order_by(Usuario.nom_us)
        )
        resultados = [self.productividad_usuario(u.id_usuario) for u in estilistas]
        return sorted(resultados, key=lambda p: p.ingreso_total, reverse=True)

    def resumen_ventas(self, id_usuario: Optional[int] = None) -> ResumenVentas:
        """Métricas globales (o de un solo usuario si se indica `id_usuario`)."""
        base = db.select(
            db.func.count(Venta.id_venta),
            db.func.coalesce(db.func.sum(Venta.cant_v * Catalogo.precio_v), 0.0),
        ).join(Catalogo, Venta.id_item == Catalogo.id_item)
        servicios = db.select(db.func.coalesce(db.func.sum(Venta.cant_v), 0)).join(
            Catalogo, Venta.id_item == Catalogo.id_item
        ).where(Catalogo.tipo_item == "Servicio")
        hoy = db.select(db.func.count(Venta.id_venta)).where(
            Venta.fecha_v.like(f"{self.hoy():%Y-%m-%d}%")
        )
        if id_usuario is not None:
            base = base.where(Venta.id_usuario == id_usuario)
            servicios = servicios.where(Venta.id_usuario == id_usuario)
            hoy = hoy.where(Venta.id_usuario == id_usuario)

        total, ingreso = db.session.execute(base).one()
        return ResumenVentas(
            total_ventas=int(total),
            ingreso_total=float(ingreso),
            servicios_realizados=int(db.session.scalar(servicios) or 0),
            ventas_hoy=int(db.session.scalar(hoy) or 0),
        )

    def devoluciones_por_venta(self, id_venta: int) -> List[DetalleDevolucion]:
        """Devoluciones vinculadas a un folio de venta, en orden cronológico."""
        venta = db.session.get(Venta, id_venta)
        if venta is None:
            raise ValueError(f"No existe la venta con folio id_venta={id_venta}")

        devoluciones: List[Devolucion] = sorted(
            venta.devoluciones,
            key=lambda d: (self.parsear_fecha(d.fecha_dev) or datetime.min, d.id_devolucion),
        )
        return [
            DetalleDevolucion(
                id_devolucion=d.id_devolucion,
                id_venta=d.id_venta,
                cant_dev=d.cant_dev,
                fecha_dev=d.fecha_dev,
                autorizado_por=d.usuario.nom_us,
                destino=d.destino,
            )
            for d in devoluciones
        ]

    def consultar_folio(self, id_venta: int) -> ConsultaFolio:
        """Datos de la venta y sus devoluciones (para el Dashboard)."""
        devoluciones = self.devoluciones_por_venta(id_venta)
        venta = db.session.get(Venta, id_venta)
        assert venta is not None
        devueltas = sum(d.cant_dev for d in devoluciones)
        return ConsultaFolio(
            venta=self._detalle(venta),
            devoluciones=devoluciones,
            cant_devuelta=devueltas,
            cant_disponible=max(venta.cant_v - devueltas, 0),
        )

    def historial_ventas(self, id_usuario: Optional[int] = None) -> List[DetalleVenta]:
        """Todas las ventas registradas, de la más reciente a la más antigua.

        Si se indica `id_usuario` solo se incluyen las ventas procesadas por ese usuario.
        """
        consulta = db.select(Venta)
        if id_usuario is not None:
            consulta = consulta.where(Venta.id_usuario == id_usuario)
        ventas = sorted(
            db.session.scalars(consulta),
            key=lambda v: (self.parsear_fecha(v.fecha_v) or datetime.min, v.id_venta),
            reverse=True,
        )
        return [self._detalle(v) for v in ventas]

    # ------------------------------------------------------------------ devoluciones
    def registrar_devolucion(
        self,
        id_venta: str,
        id_usuario: int,
        cant_dev: str,
        destino: str,
    ) -> Devolucion:
        """Registra una devolución sobre un folio de venta de forma atómica.

        1. Valida folio, destino y que `cant_dev` no supere lo vendido menos lo ya devuelto.
        2. Inserta la fila en Devoluciones a nombre del usuario que autoriza.
        3. Si el ítem es físico (Producto/Insumo): con destino 'Stock' suma al stock y registra
           'Devolución - Entrada a Stock'; con 'Merma' solo registra 'Devolución - Merma'.
           Los Servicios no afectan inventario ni Historial.
        """
        folio = self.a_entero(id_venta, "folio de venta", 1)
        cantidad = self.a_entero(cant_dev, "cantidad a devolver", 1)
        destino = (destino or "").strip()
        if destino not in DESTINOS_DEVOLUCION:
            raise ReglaNegocioError("El destino debe ser «Stock» o «Merma».")

        venta = db.session.get(Venta, folio)
        if venta is None:
            raise ReglaNegocioError(f"No existe una venta con el folio {folio}.")
        if db.session.get(Usuario, id_usuario) is None:
            raise ReglaNegocioError("El usuario que autoriza la devolución no existe.")

        ya_devueltas = sum(d.cant_dev for d in venta.devoluciones)
        disponibles = venta.cant_v - ya_devueltas
        if disponibles < 1:
            raise ReglaNegocioError(f"Todas las piezas del folio #{folio} ya fueron devueltas.")
        if cantidad > disponibles:
            raise ReglaNegocioError(
                f"No se pueden devolver {cantidad} piezas: el folio #{folio} tiene "
                f"{disponibles} disponible{'' if disponibles == 1 else 's'} para devolución "
                f"(vendidas {venta.cant_v}, ya devueltas {ya_devueltas})."
            )

        fecha_texto = self.ahora_texto()
        item = venta.item
        devolucion = Devolucion(folio, id_usuario, cantidad, fecha_texto, destino)
        with self.transaccion():
            db.session.add(devolucion)
            if item.tipo_item in TIPOS_FISICOS:
                if destino == "Stock":
                    item.stock = (item.stock or 0) + cantidad
                    tipo_mov = "Devolución - Entrada a Stock"
                else:
                    tipo_mov = "Devolución - Merma"
                db.session.add(Historial(item.id_item, id_usuario, tipo_mov, cantidad, fecha_texto))
        return devolucion

    # ------------------------------------------------------------------ registro
    def registrar_venta(
        self,
        id_cliente: str,
        id_usuario: str,
        ids_item: Sequence[str],
        cantidades: Sequence[str],
        fecha_v: Optional[str] = None,
    ) -> List[Venta]:
        """Registra una venta (una fila de Ventas por ítem) de forma atómica.

        1. Valida cliente, usuario, ítems y stock (Producto/Insumo).
        2. Inserta las filas en Ventas con la fecha indicada (o actual).
        3. Descuenta stock en Catalogo.
        4. Registra la 'Salida' en Historial a nombre del usuario responsable.
        """
        id_cl = self.a_entero(id_cliente, "cliente", 1)
        id_us = self.a_entero(id_usuario, "usuario / estilista", 1)
        if not ids_item or len(ids_item) != len(cantidades):
            raise ReglaNegocioError("Agrega al menos un ítem a la venta.")
        lineas: List[Tuple[int, int]] = [
            (self.a_entero(i, "ítem", 1), self.a_entero(c, "cantidad", 1))
            for i, c in zip(ids_item, cantidades)
        ]

        if db.session.get(Cliente, id_cl) is None:
            raise ReglaNegocioError("El cliente seleccionado no existe.")
        if db.session.get(Usuario, id_us) is None:
            raise ReglaNegocioError("El usuario / estilista seleccionado no existe.")
        fecha_texto = self._resolver_fecha(fecha_v)

        items: Dict[int, Catalogo] = {}
        solicitado: Dict[int, int] = {}
        for id_item, cant in lineas:
            if id_item not in items:
                item = db.session.get(Catalogo, id_item)
                if item is None:
                    raise ReglaNegocioError(f"El ítem #{id_item} no existe.")
                items[id_item] = item
            solicitado[id_item] = solicitado.get(id_item, 0) + cant

        for id_item, total in solicitado.items():
            item = items[id_item]
            disponible = item.stock or 0
            if item.tipo_item in TIPOS_FISICOS and disponible < total:
                raise ReglaNegocioError(
                    f"Stock insuficiente de «{item.nom_item}»: disponible {disponible}, solicitado {total}."
                )

        ventas: List[Venta] = []
        with self.transaccion():
            for id_item, cant in lineas:
                item = items[id_item]
                venta = Venta(id_cl, id_us, id_item, fecha_texto, cant)
                db.session.add(venta)
                ventas.append(venta)
                if item.tipo_item in TIPOS_FISICOS:
                    item.stock = (item.stock or 0) - cant
                    db.session.add(Historial(id_item, id_us, "Salida", cant, fecha_texto))
        return ventas

    # ------------------------------------------------------------------ privados
    def _detalle(self, venta: Venta) -> DetalleVenta:
        return DetalleVenta(
            id_venta=venta.id_venta,
            fecha_v=venta.fecha_v,
            cliente=venta.cliente.nom_cl,
            item=venta.item.nom_item,
            cant_v=venta.cant_v,
            precio_v=venta.item.precio_v,
            subtotal=venta.cant_v * venta.item.precio_v,
            estilista=venta.usuario.nom_us,
            tipo_item=venta.item.tipo_item,
            id_usuario=venta.id_usuario,
        )

    def _resolver_fecha(self, fecha_v: Optional[str]) -> str:
        """Fecha de venta: la indicada (AAAA-MM-DD, no futura) + hora actual, o ahora."""
        texto = (fecha_v or "").strip()
        if not texto:
            return self.ahora_texto()
        try:
            fecha = datetime.strptime(texto, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ReglaNegocioError("La fecha de venta no es válida.") from exc
        if fecha > self.hoy():
            raise ReglaNegocioError("La fecha de venta no puede ser futura.")
        return f"{fecha:%Y-%m-%d} {datetime.now():%H:%M}"
