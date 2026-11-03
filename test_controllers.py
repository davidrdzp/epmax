"""Verifica los 5 requerimientos complementarios con los datos de epmax.db."""
import os

os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"
os.environ["DISABLE_SQLALCHEMY_CEXT_RUNTIME"] = "1"

from datetime import date

from app import app
from controllers import EPMAXServices
from models import Catalogo, Usuario, Venta, db


def titulo(texto: str) -> None:
    print(f"\n{'=' * 70}\n{texto}\n{'=' * 70}")


def main() -> None:
    servicios = EPMAXServices()

    titulo("a) Catálogo agrupado por categoría")
    for categoria, items in servicios.catalogo.agrupar_por_categoria().items():
        print(f"[{categoria}]")
        if not items:
            print("   (sin ítems)")
        for i in items:
            print(f"   #{i.id_item} {i.nom_item:<28} {i.tipo_item:<9} ${i.precio_v:>8.2f}")

    titulo("b) Productividad por usuario")
    for usuario in db.session.scalars(db.select(Usuario)):
        p = servicios.ventas.productividad_usuario(usuario.id_usuario)
        print(f"{p.nom_us} ({p.rol_us}) -> transacciones={p.total_transacciones} "
              f"piezas={p.total_piezas} ingreso=${p.ingreso_total:.2f}")
        for d in p.detalle:
            print(f"   Folio {d.id_venta} | {d.fecha_v} | {d.cliente} | {d.item} "
                  f"x{d.cant_v} @ ${d.precio_v:.2f} = ${d.subtotal:.2f}")

    titulo("c) Trazabilidad de inventario")
    for item in db.session.scalars(db.select(Catalogo)):
        movimientos = servicios.inventario.trazabilidad_item(item.id_item)
        print(f"#{item.id_item} {item.nom_item}: {len(movimientos)} movimiento(s)")
        for m in movimientos:
            print(f"   Mov {m.id_movimiento} | {m.fecha_mov} | {m.tipo_mov:<8} "
                  f"| {m.cant_mov:>4} | {m.usuario}")

    titulo("d) Alertas preventivas (hoy, umbral 30 días)")
    alertas = servicios.inventario.alertas_preventivas()
    print("Stock bajo:")
    for a in alertas.stock_bajo:
        print(f"   #{a.id_item} {a.nom_item}: stock={a.stock} <= mínimo={a.stock_min}")
    print("Próximos a caducar / vencidos:", alertas.proximos_a_caducar or "ninguno")

    ref = date(2027, 6, 15)
    print(f"\nSimulación con fecha de referencia {ref}:")
    for a in servicios.inventario.alertas_preventivas(fecha_referencia=ref).proximos_a_caducar:
        print(f"   #{a.id_item} {a.nom_item}: {a.fecha_caduc} ({a.estado}, {a.dias_restantes} días)")

    titulo("e) Devoluciones por folio de venta")
    for venta in db.session.scalars(db.select(Venta)):
        devs = servicios.ventas.devoluciones_por_venta(venta.id_venta)
        print(f"Folio {venta.id_venta}: {len(devs)} devolución(es)")
        for d in devs:
            print(f"   Dev {d.id_devolucion} | {d.fecha_dev} | piezas={d.cant_dev} "
                  f"| autorizó={d.autorizado_por} | destino={d.destino}")

    titulo("Validación de errores")
    for nombre, llamada in (
        ("usuario inexistente", lambda: servicios.ventas.productividad_usuario(999)),
        ("ítem inexistente", lambda: servicios.inventario.trazabilidad_item(999)),
        ("venta inexistente", lambda: servicios.ventas.devoluciones_por_venta(999)),
    ):
        try:
            llamada()
            print(f"FALLO: {nombre} no lanzó error")
        except ValueError as e:
            print(f"OK ({nombre}): {e}")

    print("\nTodas las pruebas se ejecutaron sin errores.")


if __name__ == "__main__":
    with app.app_context():
        main()
