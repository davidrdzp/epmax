import os

# Debe definirse antes de importar sqlalchemy (evita cargar extensiones C bloqueadas).
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"
os.environ["DISABLE_SQLALCHEMY_CEXT_RUNTIME"] = "1"

from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Union, cast

from flask import Flask, flash, redirect, render_template, request, session, url_for
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.wrappers import Response

from controllers import EPMAXServices
from controllers.usuario_controller import ROL_ADMIN, ROLES
from models import db

BASE_DIR: Path = Path(__file__).resolve().parent

RespuestaVista = Union[str, Response]
F = TypeVar("F", bound=Callable[..., Any])


@event.listens_for(Engine, "connect")
def activar_llaves_foraneas(dbapi_connection, connection_record) -> None:
    """SQLite no valida llaves foráneas por defecto; se activan en cada conexión."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_app() -> Flask:
    """Fábrica de la aplicación Flask."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR / 'epmax.db'}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Clave para firmar la sesión; en producción definir EPMAX_SECRET_KEY.
    app.secret_key = os.environ.get("EPMAX_SECRET_KEY", "epmax-dev-key")

    db.init_app(app)
    return app


app: Flask = create_app()
services: EPMAXServices = EPMAXServices()


# ---------------------------------------------------------------------- sesión
def login_required(vista: F) -> F:
    """Redirige a /login si no hay un usuario en sesión."""

    @wraps(vista)
    def envoltura(*args: Any, **kwargs: Any) -> Any:
        if "id_usuario" not in session:
            flash("Inicia sesión para continuar.", "warning")
            return redirect(url_for("login"))
        return vista(*args, **kwargs)

    return cast(F, envoltura)


def es_administrador() -> bool:
    return session.get("rol_us") == ROL_ADMIN


def admin_required(mensaje: str) -> Callable[[F], F]:
    """Exige sesión iniciada y rol Administrador; si no, avisa con `mensaje` y vuelve al dashboard."""

    def decorador(vista: F) -> F:
        @wraps(vista)
        def envoltura(*args: Any, **kwargs: Any) -> Any:
            if not es_administrador():
                flash(mensaje, "error")
                return redirect(url_for("dashboard"))
            return vista(*args, **kwargs)

        return login_required(cast(F, envoltura))

    return decorador


@app.context_processor
def inyectar_rol() -> dict[str, Any]:
    """Variables disponibles en todas las plantillas (el menú lateral oculta «Personal» a no administradores)."""
    return {"es_admin": es_administrador()}


# ---------------------------------------------------------------------- rutas: acceso
@app.route("/")
def index() -> Response:
    destino = "dashboard" if "id_usuario" in session else "login"
    return redirect(url_for(destino))


@app.route("/login", methods=["GET", "POST"])
def login() -> RespuestaVista:
    if request.method == "GET":
        if "id_usuario" in session:
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    correo_us = request.form.get("correo_us", "")
    usuario = services.usuarios.autenticar(correo_us, request.form.get("contra_us", ""))
    if usuario is None:
        return (
            render_template(
                "login.html",
                error="Correo o contraseña incorrectos.",
                correo_us=correo_us,
            ),
            401,
        )

    session.clear()
    session["id_usuario"] = usuario.id_usuario
    session["nom_us"] = usuario.nom_us
    session["rol_us"] = usuario.rol_us
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout() -> Response:
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------- rutas: dashboard
@app.route("/dashboard")
@login_required
def dashboard() -> RespuestaVista:
    """Solo tarjetas de resumen y alertas preventivas (stock mínimo / caducidad)."""
    alertas = services.inventario.alertas_preventivas()
    resumen = services.ventas.resumen_ventas(None if es_administrador() else session["id_usuario"])
    return render_template(
        "dashboard.html",
        stock_bajo=alertas.stock_bajo,
        proximos_a_caducar=alertas.proximos_a_caducar,
        resumen=resumen,
    )


# ---------------------------------------------------------------------- rutas: catálogo
@app.route("/catalogo", methods=["GET", "POST"])
@login_required
def catalogo() -> RespuestaVista:
    """Consulta del catálogo (agrupado por categoría) y alta de ítems."""
    if request.method == "POST":
        try:
            item = services.catalogo.registrar_item(request.form, session["id_usuario"])
            flash(f"Ítem «{item.nom_item}» registrado con ID {item.id_item}.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("catalogo") + "#formulario")

    filtro_cat = request.args.get("id_categoria", "").strip()
    id_categoria = int(filtro_cat) if filtro_cat.isdigit() else None
    tipo_item = request.args.get("tipo_item", "").strip() or None
    texto = request.args.get("q", "").strip()

    # El texto de búsqueda se aplica en el navegador (filtrado dinámico en catalogo.html),
    # por lo que aquí solo se filtra por categoría y tipo.
    agrupado = services.catalogo.agrupar_por_categoria(id_categoria, tipo_item)
    items = [i for lista in agrupado.values() for i in lista]
    return render_template(
        "catalogo.html",
        agrupado=agrupado,
        total_items=len(items),
        estados={i.id_item: services.catalogo.estado_item(i) for i in items},
        categorias=services.catalogo.listar_categorias(),
        proveedores=services.catalogo.listar_proveedores(),
        tipos=("Producto", "Servicio", "Insumo"),
        filtro_categoria=id_categoria,
        filtro_tipo=tipo_item,
        filtro_texto=texto,
    )


# ---------------------------------------------------------------------- rutas: proveedores
@app.route("/proveedores", methods=["GET"])
@login_required
def proveedores() -> RespuestaVista:
    return render_template("proveedores.html", proveedores=services.catalogo.listar_proveedores())


@app.route("/proveedores/nuevo", methods=["POST"])
@login_required
def nuevo_proveedor() -> Response:
    try:
        proveedor = services.catalogo.registrar_proveedor(request.form)
        flash(f"Proveedor «{proveedor.nom_prov}» registrado con ID {proveedor.id_proveedor}.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("proveedores") + "#nuevo-proveedor")


# ---------------------------------------------------------------------- rutas: categorías
@app.route("/categorias", methods=["GET"])
@login_required
def categorias() -> RespuestaVista:
    return render_template("categorias.html", categorias=services.catalogo.listar_categorias())


@app.route("/categorias/nueva", methods=["POST"])
@login_required
def nueva_categoria() -> Response:
    try:
        categoria = services.catalogo.registrar_categoria(request.form)
        flash(f"Categoría «{categoria.nom_cat}» registrada con ID {categoria.id_categoria}.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("categorias") + "#nueva-categoria")


# ---------------------------------------------------------------------- rutas: personal (solo Administrador)
@app.route("/usuarios", methods=["GET"])
@admin_required("Solo un Administrador puede acceder al módulo de Personal.")
def usuarios() -> RespuestaVista:
    return render_template(
        "usuarios.html",
        roles=ROLES,
        productividad=services.ventas.productividad_estilistas(),
    )


@app.route("/usuarios/nuevo", methods=["POST"])
@admin_required("Solo un Administrador puede registrar usuarios.")
def nuevo_usuario() -> Response:
    try:
        usuario = services.usuarios.registrar_usuario(request.form)
        flash(f"{usuario.rol_us} «{usuario.nom_us}» registrado con ID {usuario.id_usuario}.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("usuarios") + "#usuarios")


# ---------------------------------------------------------------------- rutas: devoluciones
@app.route("/devoluciones", methods=["GET"])
@login_required
def devoluciones() -> RespuestaVista:
    """Buscador de folios y formulario de devolución."""
    folio_txt = request.args.get("id_venta", "").strip()
    consulta_folio = None
    error_folio: Optional[str] = None
    if folio_txt:
        if not folio_txt.isdigit() or int(folio_txt) < 1:
            error_folio = "El folio debe ser un número entero positivo."
        else:
            try:
                consulta_folio = services.ventas.consultar_folio(int(folio_txt))
            except ValueError:
                error_folio = f"No existe una venta con el folio {folio_txt}."
    return render_template(
        "devoluciones.html",
        folio_txt=folio_txt,
        consulta_folio=consulta_folio,
        error_folio=error_folio,
    )


@app.route("/devoluciones/procesar", methods=["POST"])
@login_required
def procesar_devolucion() -> Response:
    id_venta = request.form.get("id_venta", "").strip()
    try:
        devolucion = services.ventas.registrar_devolucion(
            id_venta=id_venta,
            id_usuario=session["id_usuario"],
            cant_dev=request.form.get("cant_dev", ""),
            destino=request.form.get("destino", ""),
        )
        flash(
            f"Devolución #{devolucion.id_devolucion} registrada: {devolucion.cant_dev} pieza(s) "
            f"del folio #{devolucion.id_venta} con destino «{devolucion.destino}».",
            "success",
        )
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("devoluciones", id_venta=id_venta) + "#devoluciones")


# ---------------------------------------------------------------------- rutas: historial de ventas
@app.route("/ventas/historial", methods=["GET"])
@login_required
def historial_ventas() -> RespuestaVista:
    """Auditoría de folios: el Administrador ve todo el estudio; el Estilista solo lo suyo."""
    admin = es_administrador()
    historial = services.ventas.historial_ventas(None if admin else session["id_usuario"])
    return render_template(
        "historial.html",
        historial_ventas=historial,
        atendidos_por=sorted({v.estilista for v in historial}),
    )


# ---------------------------------------------------------------------- rutas: POS
@app.route("/pos", methods=["GET"])
@login_required
def pos() -> RespuestaVista:
    return render_template(
        "pos.html",
        clientes=services.clientes.listar(),
        usuarios=services.usuarios.listar_para_venta(session["id_usuario"]),
        catalogo_agrupado=services.catalogo.agrupar_por_categoria(),
        hoy=services.ventas.hoy().isoformat(),
        generos=("Femenino", "Masculino", "Otro"),
    )


@app.route("/pos/procesar_venta", methods=["POST"])
@login_required
def procesar_venta() -> Response:
    try:
        ventas = services.ventas.registrar_venta(
            id_cliente=request.form.get("id_cliente", ""),
            id_usuario=request.form.get("id_usuario", ""),
            ids_item=request.form.getlist("id_item"),
            cantidades=request.form.getlist("cant_v"),
            fecha_v=request.form.get("fecha_v"),
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("pos"))

    folios = ", ".join(f"#{v.id_venta}" for v in ventas)
    etiqueta = "Folio generado" if len(ventas) == 1 else "Folios generados"
    flash(f"Venta registrada correctamente. {etiqueta}: {folios}.", "success")
    avisados: set[int] = set()
    for venta in ventas:
        item = venta.item
        if item.id_item in avisados:
            continue
        avisados.add(item.id_item)
        if item.tipo_item != "Servicio" and (item.stock or 0) <= (item.stock_min or 0):
            flash(
                f"Aviso: «{item.nom_item}» quedó con stock {item.stock} (mínimo {item.stock_min}).",
                "warning",
            )
    return redirect(url_for("pos"))


@app.route("/clientes/nuevo", methods=["POST"])
@login_required
def nuevo_cliente() -> Response:
    try:
        cliente = services.clientes.registrar_cliente(request.form)
        flash(f"Cliente «{cliente.nom_cl}» registrado.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("pos"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print(f"Base de datos lista en: {BASE_DIR / 'epmax.db'}")
    app.run(debug=True)
