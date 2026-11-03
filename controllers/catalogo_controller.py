"""Requerimiento a) catálogo agrupado por categoría, y alta de ítems."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Mapping, Optional

from models import Catalogo, Categoria, Historial, Proveedor, db

from .base_controller import (
    TIPOS_FISICOS,
    TIPOS_ITEM,
    BaseController,
    ReglaNegocioError,
)


class CatalogoController(BaseController):
    """Consultas y altas del catálogo."""

    def agrupar_por_categoria(
        self,
        id_categoria: Optional[int] = None,
        tipo_item: Optional[str] = None,
        texto: Optional[str] = None,
    ) -> Dict[str, List[Catalogo]]:

        consulta = db.select(Categoria).order_by(Categoria.nom_cat)
        if id_categoria is not None:
            consulta = consulta.where(Categoria.id_categoria == id_categoria)

        busqueda = (texto or "").strip().lower()
        filtrando_items = tipo_item is not None or bool(busqueda)

        agrupado: Dict[str, List[Catalogo]] = {}
        for categoria in db.session.scalars(consulta):
            items = sorted(categoria.items, key=lambda i: i.nom_item)
            if tipo_item is not None:
                items = [i for i in items if i.tipo_item == tipo_item]
            if busqueda:
                items = [i for i in items if busqueda in i.nom_item.lower()]
            if filtrando_items and not items:
                continue
            agrupado[categoria.nom_cat] = items
        return agrupado

    def agrupar_por_id_categoria(self) -> Dict[int, List[Catalogo]]:
  
        return {
            categoria.id_categoria: list(categoria.items)
            for categoria in db.session.scalars(db.select(Categoria))
        }

    def listar_categorias(self) -> List[Categoria]:
        return list(db.session.scalars(db.select(Categoria).order_by(Categoria.nom_cat)))

    def listar_proveedores(self) -> List[Proveedor]:
        return list(db.session.scalars(db.select(Proveedor).order_by(Proveedor.nom_prov)))

    def registrar_categoria(self, datos: Mapping[str, str]) -> Categoria:

        nom_cat = " ".join((datos.get("nom_cat") or "").split())
        if not nom_cat:
            raise ReglaNegocioError("El nombre de la categoría es obligatorio.")
        if len(nom_cat) > 60:
            raise ReglaNegocioError("El nombre de la categoría no puede exceder 60 caracteres.")
        existente = db.session.scalar(
            db.select(Categoria).where(db.func.lower(Categoria.nom_cat) == nom_cat.lower())
        )
        if existente is not None:
            raise ReglaNegocioError(f"Ya existe la categoría «{existente.nom_cat}».")

        categoria = Categoria(nom_cat)
        with self.transaccion():
            db.session.add(categoria)
        return categoria

    def registrar_proveedor(self, datos: Mapping[str, str]) -> Proveedor:

        nom_prov = " ".join((datos.get("nom_prov") or "").split())
        tel_prov = (datos.get("tel_prov") or "").strip() or None
        if not nom_prov:
            raise ReglaNegocioError("El nombre del proveedor es obligatorio.")
        if len(nom_prov) > 60:
            raise ReglaNegocioError("El nombre del proveedor no puede exceder 60 caracteres.")
        if tel_prov is not None and (
            len(tel_prov) > 15 or not tel_prov.replace("+", "").replace("-", "").replace(" ", "").isdigit()
        ):
            raise ReglaNegocioError("El teléfono debe contener solo dígitos (máximo 15 caracteres).")
        existente = db.session.scalar(
            db.select(Proveedor).where(db.func.lower(Proveedor.nom_prov) == nom_prov.lower())
        )
        if existente is not None:
            raise ReglaNegocioError(f"Ya existe el proveedor «{existente.nom_prov}».")

        proveedor = Proveedor(nom_prov, tel_prov)
        with self.transaccion():
            db.session.add(proveedor)
        return proveedor

    def estado_item(self, item: Catalogo, dias_umbral: int = 30) -> str:
    
        if item.tipo_item not in TIPOS_FISICOS:
            return "Disponible"
        caducidad = self.parsear_fecha(item.fecha_caduc)
        dias: Optional[int] = None
        if caducidad is not None:
            dias = (caducidad.date() - self.hoy()).days
        if dias is not None and dias < 0:
            return "Vencido"
        if (item.stock or 0) <= (item.stock_min or 0):
            return "Stock bajo"
        if dias is not None and dias <= dias_umbral:
            return "Por vencer"
        return "Disponible"

    def registrar_item(self, datos: Mapping[str, str], id_usuario: int) -> Catalogo:
        
        nom_item = (datos.get("nom_item") or "").strip()
        tipo_item = (datos.get("tipo_item") or "").strip()
        if not nom_item:
            raise ReglaNegocioError("El nombre del ítem es obligatorio.")
        if len(nom_item) > 60:
            raise ReglaNegocioError("El nombre del ítem no puede exceder 60 caracteres.")
        if tipo_item not in TIPOS_ITEM:
            raise ReglaNegocioError("Selecciona un tipo de ítem válido.")

        id_categoria = self.a_entero(datos.get("id_categoria"), "categoría", 1)
        id_proveedor = self.a_entero(datos.get("id_proveedor"), "proveedor", 1)
        if db.session.get(Categoria, id_categoria) is None:
            raise ReglaNegocioError("La categoría seleccionada no existe.")
        if db.session.get(Proveedor, id_proveedor) is None:
            raise ReglaNegocioError("El proveedor seleccionado no existe.")

        precio_v = self.a_decimal(datos.get("precio_v"), "precio de venta")
        precio_c = self.a_decimal(datos.get("precio_c"), "precio de compra")

        es_fisico = tipo_item in TIPOS_FISICOS
        stock = stock_min = stock_max = 0
        fecha_caduc: Optional[str] = None
        if es_fisico:
            stock = self.a_entero(datos.get("stock"), "stock actual", 0, defecto=0)
            stock_min = self.a_entero(datos.get("stock_min"), "stock mínimo", 0, defecto=0)
            stock_max = self.a_entero(datos.get("stock_max"), "stock máximo", 0, defecto=0)
            if stock_max < stock_min:
                raise ReglaNegocioError("El stock máximo no puede ser menor al stock mínimo.")
            texto_fecha = (datos.get("fecha_caduc") or "").strip()
            if texto_fecha:
                try:
                    fecha_caduc = datetime.strptime(texto_fecha, "%Y-%m-%d").strftime("%Y-%m-%d")
                except ValueError as exc:
                    raise ReglaNegocioError("La fecha de caducidad no es válida.") from exc

        item = Catalogo(
            id_categoria=id_categoria,
            id_proveedor=id_proveedor,
            nom_item=nom_item,
            tipo_item=tipo_item,
            precio_v=precio_v,
            precio_c=precio_c,
            stock=stock,
            stock_min=stock_min,
            stock_max=stock_max,
            fecha_caduc=fecha_caduc,
        )
        with self.transaccion():
            db.session.add(item)
            db.session.flush()  # genera id_item para el Historial
            if es_fisico:
                db.session.add(
                    Historial(item.id_item, id_usuario, "Entrada", stock, self.ahora_texto())
                )
        return item
