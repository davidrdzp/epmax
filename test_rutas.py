"""Prueba de navegación y rutas con el cliente de pruebas de Flask.

Usa una copia temporal de epmax.db, por lo que no modifica los datos reales.
"""
import os

os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"
os.environ["DISABLE_SQLALCHEMY_CEXT_RUNTIME"] = "1"

import shutil
import sys
import tempfile
from pathlib import Path

from app import BASE_DIR, app, db
from models import Catalogo, Cliente, Historial, Venta

errores: list[str] = []

# Módulos del menú lateral (el Administrador ve todos; "/usuarios" es solo para Administrador).
RUTAS_PROTEGIDAS = ("/dashboard", "/pos", "/catalogo", "/proveedores", "/categorias",
                    "/usuarios", "/devoluciones", "/ventas/historial")
ENLACES_MENU = RUTAS_PROTEGIDAS


def verificar(condicion: bool, descripcion: str) -> None:
    print(("  OK   " if condicion else "  FALLO") + f" {descripcion}")
    if not condicion:
        errores.append(descripcion)


def main() -> None:
    c = app.test_client()

    print("Rutas protegidas sin sesión")
    for ruta in RUTAS_PROTEGIDAS:
        r = c.get(ruta)
        verificar(r.status_code == 302 and "/login" in r.headers["Location"], f"{ruta} redirige a /login")

    print("Login")
    verificar(c.get("/login").status_code == 200, "GET /login 200")
    r = c.post("/login", data={"correo_us": "admin@epmax.com", "contra_us": "mala"})
    verificar(r.status_code == 401 and "incorrectos" in r.get_data(as_text=True), "credenciales inválidas muestran error")
    r = c.post("/login", data={"correo_us": "admin@epmax.com", "contra_us": "admin123"})
    verificar(r.status_code == 302 and "/dashboard" in r.headers["Location"], "login válido redirige al dashboard")

    print("Páginas (Administrador)")
    for ruta in RUTAS_PROTEGIDAS:
        r = c.get(ruta)
        html = r.get_data(as_text=True)
        verificar(r.status_code == 200, f"GET {ruta} 200")
        for destino in ENLACES_MENU + ("/logout",):
            verificar(f'href="{destino}"' in html, f"{ruta}: enlace a {destino}")
        verificar(".html\"" not in html.replace("<!DOCTYPE html>", ""), f"{ruta}: sin enlaces *.html estáticos")

    html = c.get("/dashboard").get_data(as_text=True)
    verificar("Mascarilla Hidratante" in html, "dashboard lista stock bajo real")
    verificar("Productividad de Estilistas" not in html and "Devoluciones por Folio" not in html
              and "Historial de Ventas Registradas" not in html, "dashboard solo contiene resumen y alertas")
    html = c.get("/usuarios").get_data(as_text=True)
    verificar("Productividad de Estilistas" in html and "Coco Estilista" in html and 'name="correo_us"' in html,
              "/usuarios muestra productividad y alta de usuarios (admin)")
    html = c.get("/devoluciones?id_venta=1").get_data(as_text=True)
    verificar("Stock" in html and "Administrador EPMAX" in html, "folio 1 muestra su devolución")
    verificar("No existe una venta" in c.get("/devoluciones?id_venta=999").get_data(as_text=True), "folio inexistente informa error")
    html = c.get("/ventas/historial").get_data(as_text=True)
    verificar("Historial de Ventas Registradas" in html and 'data-folio="1"' in html, "/ventas/historial lista los folios")
    html = c.get("/proveedores").get_data(as_text=True)
    verificar('name="nom_prov"' in html and "Proveedores registrados" in html, "/proveedores muestra tabla y alta")
    html = c.get("/categorias").get_data(as_text=True)
    verificar('name="nom_cat"' in html and "Categorías registradas" in html, "/categorias muestra tabla y alta")
    html = c.get("/catalogo").get_data(as_text=True)
    verificar('name="nom_cat"' not in html and 'name="nom_prov"' not in html, "/catalogo ya no contiene altas de categoría ni proveedor")

    print("Redirecciones de formularios POST")
    for ruta, datos, destino in (
        ("/categorias/nueva", {"nom_cat": ""}, "/categorias"),
        ("/proveedores/nuevo", {"nom_prov": ""}, "/proveedores"),
        ("/usuarios/nuevo", {"nom_us": ""}, "/usuarios"),
        ("/devoluciones/procesar", {"id_venta": "999"}, "/devoluciones"),
    ):
        r = c.post(ruta, data=datos)
        verificar(r.status_code == 302 and r.headers["Location"].split("#")[0].split("?")[0] == destino,
                  f"POST {ruta} redirige a {destino}")

    html = c.get("/catalogo").get_data(as_text=True)
    verificar("Cuidado Capilar" in html and "Shampoo Reparador 500ml" in html, "catálogo agrupado por categoría")
    html = c.get("/catalogo?tipo_item=Servicio").get_data(as_text=True)
    verificar("Corte de Cabello" in html and "Shampoo" not in html.split("<tbody>")[1], "filtro por tipo")
    html = c.get("/catalogo?id_categoria=2").get_data(as_text=True)
    verificar("Tinte Rubio" in html and "Mascarilla" not in html.split("<tbody>")[1], "filtro por categoría")

    print("Alta de ítems")
    with app.app_context():
        n_hist = Historial.query.count()
    datos = dict(nom_item="Spray Fijador", tipo_item="Producto", precio_v="90", precio_c="50",
                 stock="12", stock_min="3", stock_max="30", fecha_caduc="2028-01-01",
                 id_categoria="1", id_proveedor="1")
    c.post("/catalogo", data=datos)
    with app.app_context():
        item = Catalogo.query.filter_by(nom_item="Spray Fijador").one()
        verificar(Historial.query.count() == n_hist + 1, "ítem físico genera Entrada en Historial")
        mov = Historial.query.order_by(Historial.id_movimiento.desc()).first()
        verificar(mov.tipo_mov == "Entrada" and mov.cant_mov == 12 and mov.id_item == item.id_item, "Entrada con cantidad correcta")
        id_spray = item.id_item
    c.post("/catalogo", data={**datos, "nom_item": "Facial", "tipo_item": "Servicio"})
    with app.app_context():
        servicio = Catalogo.query.filter_by(nom_item="Facial").one()
        verificar(servicio.stock == 0 and Historial.query.filter_by(id_item=servicio.id_item).count() == 0, "servicio sin stock ni Historial")
    r = c.post("/catalogo", data={**datos, "nom_item": "Malo", "precio_v": "-5"}, follow_redirects=True)
    verificar("mayor o igual a 0" in r.get_data(as_text=True), "precio negativo rechazado")
    r = c.post("/catalogo", data={**datos, "nom_item": "Malo2", "id_categoria": "99"}, follow_redirects=True)
    verificar("categoría seleccionada no existe" in r.get_data(as_text=True), "categoría inexistente rechazada")

    print("Clientes")
    c.post("/clientes/nuevo", data={"nom_cl": "Ana Prueba", "tel_cl": "5551112222", "gen_cl": "Femenino"})
    with app.app_context():
        verificar(Cliente.query.filter_by(nom_cl="Ana Prueba").count() == 1, "cliente registrado")
    r = c.post("/clientes/nuevo", data={"nom_cl": ""}, follow_redirects=True)
    verificar("obligatorio" in r.get_data(as_text=True), "cliente sin nombre rechazado")

    print("Venta (POS)")
    html = c.get("/pos").get_data(as_text=True)
    verificar("María López" in html and "Spray Fijador" in html and "Coco Estilista" in html, "POS lista clientes, ítems y estilistas")
    with app.app_context():
        stock_antes = db.session.get(Catalogo, id_spray).stock
        ventas_antes = Venta.query.count()
        hist_antes = Historial.query.count()
    r = c.post("/pos/procesar_venta", data={"id_cliente": "1", "id_usuario": "2", "fecha_v": "",
                                            "id_item": ["1", "4"], "cant_v": ["2", "1"]}, follow_redirects=True)
    html = r.get_data(as_text=True)
    verificar("Folios generados" in html, "venta con 2 ítems genera folios")
    with app.app_context():
        verificar(Venta.query.count() == ventas_antes + 2, "2 filas en Ventas")
        verificar(db.session.get(Catalogo, 1).stock == 18, "stock del producto descontado (20-2)")
        verificar(Historial.query.count() == hist_antes + 1, "solo el producto físico genera Salida")
        salida = Historial.query.order_by(Historial.id_movimiento.desc()).first()
        verificar(salida.tipo_mov == "Salida" and salida.id_usuario == 2, "Salida vinculada al estilista responsable")
    r = c.post("/pos/procesar_venta", data={"id_cliente": "1", "id_usuario": "2",
                                            "id_item": ["1"], "cant_v": ["999"]}, follow_redirects=True)
    verificar("Stock insuficiente" in r.get_data(as_text=True), "venta sin stock rechazada")
    r = c.post("/pos/procesar_venta", data={"id_cliente": "1", "id_usuario": "2",
                                            "id_item": ["2", "2"], "cant_v": ["2", "2"]}, follow_redirects=True)
    verificar("Stock insuficiente" in r.get_data(as_text=True), "líneas repetidas se suman para validar stock")
    with app.app_context():
        verificar(db.session.get(Catalogo, 2).stock == 3, "rechazo no modifica stock (atomicidad)")
    r = c.post("/pos/procesar_venta", data={"id_cliente": "1", "id_usuario": "2"}, follow_redirects=True)
    verificar("al menos un ítem" in r.get_data(as_text=True), "venta vacía rechazada")

    print("Estilista (no admin)")
    c2 = app.test_client()
    c2.post("/login", data={"correo_us": "estilista@epmax.com", "contra_us": "estilista123"})
    html = c2.get("/dashboard").get_data(as_text=True)
    verificar('href="/usuarios"' not in html, "estilista no ve «Personal» en el menú")
    r = c2.get("/usuarios")
    verificar(r.status_code == 302 and "/dashboard" in r.headers["Location"], "estilista no puede abrir /usuarios")
    r = c2.get("/usuarios", follow_redirects=True)
    verificar("Solo un Administrador" in r.get_data(as_text=True) and "Productividad de Estilistas" not in r.get_data(as_text=True),
              "estilista no ve productividad global")
    for ruta in ("/proveedores", "/categorias", "/devoluciones", "/ventas/historial"):
        verificar(c2.get(ruta).status_code == 200, f"estilista accede a {ruta}")

    print("Logout")
    r = c.get("/logout")
    verificar(r.status_code == 302 and "/login" in r.headers["Location"], "logout redirige a /login")
    verificar(c.get("/dashboard").status_code == 302, "sesión cerrada: dashboard protegido")


if __name__ == "__main__":
    original = BASE_DIR / "epmax.db"
    respaldo = Path(tempfile.gettempdir()) / "epmax_respaldo.db"
    shutil.copy2(original, respaldo)
    try:
        with app.app_context():
            pass
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
