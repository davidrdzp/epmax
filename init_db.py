"""Puebla epmax.db con datos de prueba para verificar llaves foráneas y relaciones."""
import os

# Debe definirse antes de importar sqlalchemy (evita cargar extensiones C bloqueadas).
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"
os.environ["DISABLE_SQLALCHEMY_CEXT_RUNTIME"] = "1"

from datetime import datetime

from app import app
from models import (
    Catalogo,
    Categoria,
    Cliente,
    Devolucion,
    Historial,
    Proveedor,
    Usuario,
    Venta,
    db,
)


def poblar() -> None:
    ahora: str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Nota: contraseñas en texto plano solo para el prototipo (aplicar hash en la Fase de login).
    admin = Usuario("Administrador EPMAX", "Administrador", "admin@epmax.com", "admin123", "5551234567")
    estilista = Usuario("Coco Estilista", "Estilista", "estilista@epmax.com", "estilista123", "5557654321")

    clientes = [
        Cliente("María López", "5550001111", "Femenino"),
        Cliente("Carlos Ruiz", "5550002222", "Masculino"),
    ]
    proveedores = [
        Proveedor("Distribuidora Belleza MX", "5559990001"),
        Proveedor("Insumos Profesionales SA", "5559990002"),
    ]
    categorias = [
        Categoria("Cuidado Capilar"),
        Categoria("Coloración"),
        Categoria("Servicios"),
    ]

    db.session.add_all([admin, estilista, *clientes, *proveedores, *categorias])
    db.session.flush()  # Genera los IDs para usarlos como llaves foráneas

    catalogo = [
        Catalogo(categorias[0].id_categoria, proveedores[0].id_proveedor,
                 "Shampoo Reparador 500ml", "Producto", 180.0, 110.0, 20, 5, 50, "2027-12-31"),
        Catalogo(categorias[0].id_categoria, proveedores[0].id_proveedor,
                 "Mascarilla Hidratante", "Producto", 250.0, 150.0, 3, 5, 30, "2027-06-30"),
        Catalogo(categorias[1].id_categoria, proveedores[1].id_proveedor,
                 "Tinte Rubio Ceniza", "Insumo", 120.0, 70.0, 15, 4, 40, "2028-01-15"),
        Catalogo(categorias[2].id_categoria, proveedores[1].id_proveedor,
                 "Corte de Cabello", "Servicio", 200.0, 0.0, 0, 0, 0, None),
    ]
    db.session.add_all(catalogo)
    db.session.flush()

    venta = Venta(clientes[0].id_cliente, estilista.id_usuario, catalogo[0].id_item, ahora, 2)
    db.session.add(venta)
    db.session.flush()

    db.session.add_all([
        Devolucion(venta.id_venta, admin.id_usuario, 1, ahora, "Stock"),
        Historial(catalogo[0].id_item, admin.id_usuario, "Entrada", 20, ahora),
        Historial(catalogo[0].id_item, estilista.id_usuario, "Salida", 2, ahora),
    ])
    db.session.commit()


def verificar() -> None:
    estilista = Usuario.query.filter_by(rol_us="Estilista").first()
    item = Catalogo.query.first()
    venta = Venta.query.first()
    print("Ventas del estilista :", estilista.ventas)
    print("Categoría del ítem   :", item.categoria, "| Proveedor:", item.proveedor)
    print("Historial del ítem   :", item.movimientos)
    print("Devoluciones venta   :", venta.devoluciones)
    print("Ventas del cliente   :", venta.cliente.ventas)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if Usuario.query.first() is not None:
            print("La base de datos ya contiene datos; no se vuelve a poblar.")
        else:
            poblar()
            print("Datos de prueba insertados correctamente.")
        verificar()
