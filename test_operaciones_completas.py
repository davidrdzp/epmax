"""Prueba de flujo completo: categoría, proveedor, estilista, venta y devolución.

Usa el cliente de pruebas de Flask sobre una copia temporal de epmax.db; la base real
se restaura al terminar, por lo que no modifica los datos existentes.
"""
import os

os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"
os.environ["DISABLE_SQLALCHEMY_CEXT_RUNTIME"] = "1"

import re
import shutil
import sys
import tempfile
from pathlib import Path

from app import BASE_DIR, app, db
from models import Catalogo, Categoria, Devolucion, Historial, Proveedor, Usuario, Venta

errores: list[str] = []


def verificar(condicion: bool, descripcion: str) -> None:
    print(("  OK    " if condicion else "  FALLO ") + descripcion)
    if not condicion:
        errores.append(descripcion)


def main() -> None:
    admin = app.test_client()
    admin.post("/login", data={"correo_us": "admin@epmax.com", "contra_us": "admin123"})

    # ------------------------------------------------------------ categoría y proveedor
    print("Categorías y proveedores")
    r = admin.post("/categorias/nueva", data={"nom_cat": "Tratamientos"}, follow_redirects=True)
    verificar("Categoría «Tratamientos» registrada" in r.get_data(as_text=True), "alta de categoría confirma en pantalla")
    with app.app_context():
        categoria = Categoria.query.filter_by(nom_cat="Tratamientos").one()
        id_categoria = categoria.id_categoria
    r = admin.post("/categorias/nueva", data={"nom_cat": "tratamientos"}, follow_redirects=True)
    verificar("Ya existe la categoría" in r.get_data(as_text=True), "categoría duplicada rechazada")
    r = admin.post("/categorias/nueva", data={"nom_cat": "  "}, follow_redirects=True)
    verificar("obligatorio" in r.get_data(as_text=True), "categoría vacía rechazada")

    r = admin.post("/proveedores/nuevo", data={"nom_prov": "Cosmética Premium", "tel_prov": "5553334444"}, follow_redirects=True)
    verificar("Proveedor «Cosmética Premium» registrado" in r.get_data(as_text=True), "alta de proveedor confirma en pantalla")
    with app.app_context():
        proveedor = Proveedor.query.filter_by(nom_prov="Cosmética Premium").one()
        id_proveedor = proveedor.id_proveedor
        verificar(proveedor.tel_prov == "5553334444", "teléfono del proveedor guardado")
    r = admin.post("/proveedores/nuevo", data={"nom_prov": "Malo", "tel_prov": "abc"}, follow_redirects=True)
    verificar("solo dígitos" in r.get_data(as_text=True), "teléfono de proveedor inválido rechazado")

    html = admin.get("/catalogo").get_data(as_text=True)
    verificar(f'<option value="{id_categoria}">Tratamientos</option>' in html, "nueva categoría disponible en el selector de ítems")
    verificar(f'<option value="{id_proveedor}">Cosmética Premium</option>' in html, "nuevo proveedor disponible en el selector de ítems")

    # Ítem físico con la nueva categoría y proveedor
    admin.post("/catalogo", data=dict(
        nom_item="Ampolleta Reparadora", tipo_item="Producto", precio_v="150", precio_c="80",
        stock="10", stock_min="2", stock_max="40", fecha_caduc="2028-05-01",
        id_categoria=str(id_categoria), id_proveedor=str(id_proveedor),
    ))
    admin.post("/catalogo", data=dict(
        nom_item="Alaciado Keratina", tipo_item="Servicio", precio_v="900", precio_c="0",
        id_categoria=str(id_categoria), id_proveedor=str(id_proveedor),
    ))
    with app.app_context():
        producto = Catalogo.query.filter_by(nom_item="Ampolleta Reparadora").one()
        servicio = Catalogo.query.filter_by(nom_item="Alaciado Keratina").one()
        id_producto, id_servicio = producto.id_item, servicio.id_item
        verificar(producto.id_categoria == id_categoria and producto.id_proveedor == id_proveedor,
                  "ítem creado con la nueva categoría y proveedor")

    # ------------------------------------------------------------ usuarios
    print("Nuevo estilista")
    datos_us = dict(nom_us="Lucía Estilista", rol_us="Estilista", tel_us="5556667777",
                    correo_us="lucia@epmax.com", contra_us="lucia123")
    r = admin.post("/usuarios/nuevo", data=datos_us, follow_redirects=True)
    verificar("Estilista «Lucía Estilista» registrado" in r.get_data(as_text=True), "alta de estilista confirma en pantalla")
    with app.app_context():
        lucia = Usuario.query.filter_by(correo_us="lucia@epmax.com").one()
        id_lucia = lucia.id_usuario
        verificar(lucia.rol_us == "Estilista" and lucia.tel_us == "5556667777", "datos del estilista guardados")
    r = admin.post("/usuarios/nuevo", data={**datos_us, "nom_us": "Otra"}, follow_redirects=True)
    verificar("Ya existe un usuario con ese correo" in r.get_data(as_text=True), "correo duplicado rechazado")
    r = admin.post("/usuarios/nuevo", data={**datos_us, "correo_us": "x@y.com", "rol_us": "Gerente"}, follow_redirects=True)
    verificar("rol válido" in r.get_data(as_text=True), "rol inválido rechazado")
    r = admin.post("/usuarios/nuevo", data={**datos_us, "correo_us": "x@y.com", "contra_us": "123"}, follow_redirects=True)
    verificar("entre 6 y 60" in r.get_data(as_text=True), "contraseña corta rechazada")

    html = admin.get("/pos").get_data(as_text=True)
    verificar(f'<option value="{id_lucia}"' in html and "Lucía Estilista" in html, "nuevo estilista aparece en el POS")
    html = admin.get("/usuarios").get_data(as_text=True)
    productividad = html.split("Productividad de Estilistas")[1]
    verificar("Lucía Estilista" in productividad, "nuevo estilista aparece en Productividad del módulo Personal")

    nueva = app.test_client()
    r = nueva.post("/login", data={"correo_us": "lucia@epmax.com", "contra_us": "lucia123"})
    verificar(r.status_code == 302 and "/dashboard" in r.headers["Location"], "el nuevo estilista puede iniciar sesión")
    r = nueva.post("/usuarios/nuevo", data={**datos_us, "correo_us": "otro@epmax.com"}, follow_redirects=True)
    verificar("Solo un Administrador" in r.get_data(as_text=True), "un estilista no puede registrar usuarios")
    with app.app_context():
        verificar(Usuario.query.filter_by(correo_us="otro@epmax.com").count() == 0, "no se creó el usuario solicitado por un estilista")

    # ------------------------------------------------------------ venta
    print("Venta asignada al nuevo estilista")
    with app.app_context():
        stock_inicial = db.session.get(Catalogo, id_producto).stock
    r = admin.post("/pos/procesar_venta", data={
        "id_cliente": "1", "id_usuario": str(id_lucia), "fecha_v": "",
        "id_item": [str(id_producto), str(id_servicio)], "cant_v": ["3", "1"],
    }, follow_redirects=True)
    verificar("Folios generados" in r.get_data(as_text=True), "venta registrada con dos folios")
    with app.app_context():
        ventas = Venta.query.filter_by(id_usuario=id_lucia).order_by(Venta.id_venta).all()
        verificar(len(ventas) == 2, "las ventas quedan a nombre del nuevo estilista")
        folio_producto = next(v.id_venta for v in ventas if v.id_item == id_producto)
        folio_servicio = next(v.id_venta for v in ventas if v.id_item == id_servicio)
        verificar(db.session.get(Catalogo, id_producto).stock == stock_inicial - 3, "stock descontado por la venta")

    html = admin.get("/usuarios").get_data(as_text=True)
    productividad = html.split("Productividad de Estilistas")[1]
    verificar("Lucía Estilista" in productividad and "$1,350.00" in productividad, "productividad refleja $450 + $900")

    print("Historial de ventas")
    html = admin.get("/ventas/historial").get_data(as_text=True)
    tabla = html.split("Historial de Ventas Registradas")[1]
    verificar(f"#{folio_producto}" in tabla and "Ampolleta Reparadora" in tabla and "Alaciado Keratina" in tabla, "historial lista las ventas nuevas")
    verificar("$450.00" in tabla and "$900.00" in tabla, "historial muestra importe = cant_v * precio_v")
    verificar(tabla.count("Servicio</span>") >= 1 and tabla.count("Producto</span>") >= 1, "historial muestra badges Servicio/Producto")
    verificar('id="filtroVentas"' in tabla and 'id="filtroEstilista"' in tabla, "historial incluye filtros por folio y estilista")
    folios = [int(n) for n in re.findall(r'data-folio="(\d+)"', tabla)]
    verificar(folios == sorted(folios, reverse=True) and len(folios) >= 3, "historial ordenado de más reciente a más antiguo")
    html_nueva = nueva.get("/ventas/historial").get_data(as_text=True)
    verificar("Ampolleta Reparadora" in html_nueva.split("Historial de Ventas Registradas")[1], "el estilista ve sus propias ventas en el historial")
    verificar('id="filtroEstilista"' not in html_nueva, "el estilista no ve el filtro por estilista")

    # ------------------------------------------------------------ devoluciones
    print("Devoluciones")
    html = admin.get(f"/devoluciones?id_venta={folio_producto}").get_data(as_text=True)
    verificar("Procesar nueva devolución" in html and 'name="cant_dev"' in html and 'name="destino"' in html,
              "el folio muestra el formulario de devolución")
    verificar("Lucía Estilista" in html and "Ampolleta Reparadora" in html and "$450.00" in html, "detalle de venta (estilista, ítem, total)")

    with app.app_context():
        hist_antes = Historial.query.count()
    r = admin.post("/devoluciones/procesar", data={"id_venta": str(folio_producto), "cant_dev": "5", "destino": "Stock"}, follow_redirects=True)
    verificar("No se pueden devolver 5 piezas" in r.get_data(as_text=True), "devolución mayor a lo vendido rechazada")
    r = admin.post("/devoluciones/procesar", data={"id_venta": str(folio_producto), "cant_dev": "1", "destino": "Otro"}, follow_redirects=True)
    verificar("«Stock» o «Merma»" in r.get_data(as_text=True), "destino inválido rechazado")
    with app.app_context():
        verificar(Historial.query.count() == hist_antes and Devolucion.query.filter_by(id_venta=folio_producto).count() == 0,
                  "rechazos no modifican la base de datos")

    r = admin.post("/devoluciones/procesar", data={"id_venta": str(folio_producto), "cant_dev": "2", "destino": "Stock"}, follow_redirects=True)
    verificar("Devolución #" in r.get_data(as_text=True) and "registrada" in r.get_data(as_text=True), "devolución a Stock confirma en pantalla")
    with app.app_context():
        dev = Devolucion.query.filter_by(id_venta=folio_producto).one()
        verificar(dev.cant_dev == 2 and dev.destino == "Stock" and dev.id_usuario == 1, "Devoluciones guarda cantidad, destino y usuario en sesión")
        verificar(db.session.get(Catalogo, id_producto).stock == stock_inicial - 3 + 2, "la devolución a Stock suma al inventario")
        mov = Historial.query.order_by(Historial.id_movimiento.desc()).first()
        verificar(mov.tipo_mov == "Devolución - Entrada a Stock" and mov.cant_mov == 2 and mov.id_item == id_producto,
                  "Historial registra 'Devolución - Entrada a Stock'")

    # Solo queda 1 pieza disponible: 3 vendidas - 2 devueltas
    r = admin.post("/devoluciones/procesar", data={"id_venta": str(folio_producto), "cant_dev": "2", "destino": "Merma"}, follow_redirects=True)
    verificar("1 disponible" in r.get_data(as_text=True), "no se supera lo vendido menos lo ya devuelto")
    with app.app_context():
        stock_antes_merma = db.session.get(Catalogo, id_producto).stock
    admin.post("/devoluciones/procesar", data={"id_venta": str(folio_producto), "cant_dev": "1", "destino": "Merma"})
    with app.app_context():
        verificar(db.session.get(Catalogo, id_producto).stock == stock_antes_merma, "la Merma no suma al stock")
        mov = Historial.query.order_by(Historial.id_movimiento.desc()).first()
        verificar(mov.tipo_mov == "Devolución - Merma" and mov.cant_mov == 1, "Historial registra 'Devolución - Merma'")
    html = admin.get(f"/devoluciones?id_venta={folio_producto}").get_data(as_text=True)
    verificar("Procesar nueva devolución" not in html and "ya fueron devueltas" in html, "folio totalmente devuelto oculta el formulario")
    verificar("Merma</span>" in html and "Stock</span>" in html, "las devoluciones previas se listan en el folio")

    with app.app_context():
        hist_antes = Historial.query.count()
    admin.post("/devoluciones/procesar", data={"id_venta": str(folio_servicio), "cant_dev": "1", "destino": "Stock"})
    with app.app_context():
        verificar(Devolucion.query.filter_by(id_venta=folio_servicio).count() == 1, "devolución de servicio registrada")
        verificar(Historial.query.count() == hist_antes, "devolución de servicio no genera movimientos de Historial")

    r = admin.post("/devoluciones/procesar", data={"id_venta": "99999", "cant_dev": "1", "destino": "Stock"}, follow_redirects=True)
    verificar("No existe una venta" in r.get_data(as_text=True), "folio inexistente rechazado")
    anonimo = app.test_client()
    r = anonimo.post("/devoluciones/procesar", data={"id_venta": "1", "cant_dev": "1", "destino": "Stock"})
    verificar(r.status_code == 302 and "/login" in r.headers["Location"], "devoluciones requieren sesión")


if __name__ == "__main__":
    original = BASE_DIR / "epmax.db"
    respaldo = Path(tempfile.gettempdir()) / "epmax_respaldo_operaciones.db"
    shutil.copy2(original, respaldo)
    try:
        main()
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
        shutil.copy2(respaldo, original)
        print("\nepmax.db restaurada a su estado original.")
    if errores:
        print(f"\n{len(errores)} verificación(es) fallida(s)")
        sys.exit(1)
    print("\nTodas las verificaciones pasaron.")
