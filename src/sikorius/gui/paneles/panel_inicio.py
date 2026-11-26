"""Pantalla de inicio: el logo y las dos formas de empezar.

Es la primera pestaña ("Inicio") y lo primero que se ve al abrir la
aplicación. Desde aquí se sube un dataset o se carga un modelo guardado
(historia #24). Llevar al usuario a "Datos" o a "Modelo" después no es
cosa de este panel: lo hace ``pagina.Pestanas`` al ver el cambio en la
sesión.
"""

from nicegui import ui

from sikorius.gui.componentes import carga_dataset, carga_modelo
from sikorius.gui.tema import CARPETA_RECURSOS

# El logo es un SVG con su animación dentro (ver recursos/logo.svg). Se
# incrusta como HTML y no con ui.image porque una imagen no deja que el CSS
# anime sus piezas.
RUTA_LOGO = CARPETA_RECURSOS / "logo.svg"


class PanelInicio:
    """Logo, botón "Subir dataset" y botón "Cargar modelo".

    No hereda de ``Panel``: lo que muestra no depende de la sesión, así que
    no necesita suscribirse a ella.
    """

    def __init__(self, sesion):
        self.sesion = sesion
        self.contenido = ui.column().classes("w-full items-center gap-6")
        with self.contenido:
            logo = RUTA_LOGO.read_text(encoding="utf-8")
            # sanitize=False: el SVG es un archivo nuestro y lleva su <style>
            ui.html(logo, sanitize=False).classes("w-full max-w-3xl")
            with ui.row().classes("items-center justify-center gap-4"):
                self.boton_cargar = (
                    ui.button(
                        "Subir dataset",
                        icon="upload_file",
                        on_click=self.cargar,
                    )
                    .props("size=lg")
                    .classes("sk-aparecer")
                )
                self.boton_cargar_modelo = (
                    ui.button(
                        "Cargar modelo",
                        icon="file_open",
                        on_click=self.cargar_modelo,
                    )
                    .props("size=lg outline")
                    .classes("sk-aparecer")
                )
            ui.label("CSV, Excel o SQLite").classes(
                "text-sm opacity-70 sk-aparecer"
            )

    async def cargar(self):
        """Sube un dataset (ver ``componentes.carga_dataset``)."""
        await carga_dataset.cargar_dataset(self.sesion)

    async def cargar_modelo(self):
        """Recupera un modelo guardado (ver ``componentes.carga_modelo``)."""
        await carga_modelo.cargar_modelo(self.sesion)
