"""Arranque de la aplicación."""

from pathlib import Path

from nicegui import ui

from sikorius.aplicacion.sesion import Sesion
from sikorius.gui.pagina import construir_pagina

# Icono de la pestaña del navegador: la S del logo
RUTA_ICONO = Path(__file__).parent / "gui" / "recursos" / "favicon.svg"


def main():
    """Crea la sesión de trabajo y arranca la interfaz en el navegador.

    Hay una sola sesión para toda la aplicación, porque se usa en local: si
    se abre otra pestaña o se recarga la página, se ve el mismo trabajo.
    """
    sesion = Sesion()

    @ui.page("/")
    def pagina_principal():
        construir_pagina(sesion)

    ui.run(title="SIKORIUS", favicon=RUTA_ICONO, reload=False)
