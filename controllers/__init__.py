
from .base_controller import ReglaNegocioError
from .catalogo_controller import CatalogoController
from .cliente_controller import ClienteController
from .inventario_controller import InventarioController
from .usuario_controller import UsuarioController
from .ventas_controller import VentasController


class EPMAXServices:

    def __init__(self) -> None:
        self.catalogo: CatalogoController = CatalogoController()
        self.ventas: VentasController = VentasController()
        self.inventario: InventarioController = InventarioController()
        self.clientes: ClienteController = ClienteController()
        self.usuarios: UsuarioController = UsuarioController()


__all__ = [
    "CatalogoController",
    "ClienteController",
    "InventarioController",
    "UsuarioController",
    "VentasController",
    "EPMAXServices",
    "ReglaNegocioError",
]
