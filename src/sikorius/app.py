"""Arranque de la aplicación."""

from nicegui import ui

from sikorius.gui.pagina import construir_pagina
from sikorius.sesion import Sesion


def main():
    """Crea la sesión de trabajo y arranca la interfaz en el navegador.

    Hay una sola sesión para toda la aplicación, porque se usa en local: si
    se abre otra pestaña o se recarga la página, se ve el mismo trabajo.
    """
    sesion = Sesion()

    @ui.page("/")
    def pagina_principal():
        construir_pagina(sesion)

    ui.run(title="SIKORIUS", reload=False)
