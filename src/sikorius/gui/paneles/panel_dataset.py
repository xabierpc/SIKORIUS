"""Carga del dataset: pantalla de inicio con el logo y tabla con los datos.

Mientras no hay dataset se ve la pantalla de inicio (el logo, que se
escribe solo, y el botón de subir el archivo). En cuanto se carga uno, la
pantalla de inicio desaparece y ocupa su lugar la tabla con los datos.
"""

from pathlib import Path

from nicegui import ui

from sikorius.gui.avisos import notificar_error, notificar_exito
from sikorius.gui.componentes.explorador_archivos import seleccionar_archivo
from sikorius.gui.componentes.tabla_datos import TablaDatos
from sikorius.gui.paneles.base import Panel
from sikorius.nucleo.errores import ErrorImportacion
from sikorius.nucleo.importador import importar_datos

# El logo es un SVG con su animación dentro (ver recursos/logo.svg). Se
# incrusta como HTML y no con ui.image porque una imagen no deja que el CSS
# anime sus piezas.
RUTA_LOGO = Path(__file__).parent.parent / "recursos" / "logo.svg"

# El botón aparece cuando el logo termina de escribirse (2.5 s). Hasta
# entonces ni se ve ni se puede pulsar.
CSS_INICIO = """
.sk-aparecer {
    opacity: 0;
    pointer-events: none;
    animation: sk-aparecer 0.6s ease 2.5s forwards;
}
@keyframes sk-aparecer {
    to { opacity: 1; pointer-events: auto; }
}
@media (prefers-reduced-motion: reduce) {
    .sk-aparecer { animation: none; opacity: 1; pointer-events: auto; }
}
"""


# Alto en píxeles de cada fila de la tabla (modo "dense") y de sus bordes
ALTO_FILA = 28.5
ALTO_BORDES = 3


def alto_tabla(filas):
    """Alto CSS de la tabla: el justo para sus filas, con un máximo.

    Una tabla de 10 filas no debe dejar un hueco vacío debajo; una de miles
    ocupa como mucho el 70% de la pantalla y saca su propio scroll.
    """
    justo = round((filas + 1) * ALTO_FILA) + ALTO_BORDES  # +1: cabecera
    return "min(70vh, " + str(justo) + "px)"


def carpeta_inicial(sesion):
    """Carpeta del último archivo cargado o, si no hay, la carpeta personal."""
    if sesion.dataset is not None:
        return Path(sesion.dataset.ruta).parent
    return Path.home()


def texto_resumen(datos):
    """Texto como "20640 filas y 10 columnas"."""
    return (
        str(len(datos)) + " filas y " + str(len(datos.columns)) + " columnas"
    )


class PanelDataset(Panel):
    """Pantalla de inicio (sin dataset) o tabla grande (con dataset)."""

    def __init__(self, sesion):
        ui.add_css(CSS_INICIO)

        self.inicio = ui.column().classes("w-full items-center gap-6")
        with self.inicio:
            logo = RUTA_LOGO.read_text(encoding="utf-8")
            # sanitize=False: el SVG es un archivo nuestro y lleva su <style>
            ui.html(logo, sanitize=False).classes("w-full max-w-3xl")
            self.boton_cargar = (
                ui.button(
                    "Subir dataset", icon="upload_file", on_click=self.cargar
                )
                .props("size=lg")
                .classes("sk-aparecer")
            )
            ui.label("CSV, Excel o SQLite").classes(
                "text-sm opacity-70 sk-aparecer"
            )

        self.contenido = ui.column().classes("w-full")
        with self.contenido:
            with ui.row().classes("w-full items-center no-wrap"):
                with ui.column().classes("gap-0 min-w-0"):
                    self.etiqueta_ruta = ui.label("").classes(
                        "font-mono text-sm break-all"
                    )
                    self.etiqueta_resumen = ui.label("").classes(
                        "text-sm opacity-70"
                    )
                ui.space()
                self.boton_otro = ui.button(
                    "Cargar otro", icon="folder_open", on_click=self.cargar
                ).props("outline")
            self.tabla = TablaDatos()

        # Dataset que se ve ahora en la tabla. La sesión avisa en cada paso
        # (columnas, separación...), y volver a enviar todas las filas al
        # navegador en cada aviso haría la página muy lenta.
        self._mostrado = None
        super().__init__(sesion)

    def actualizar(self):
        dataset = self.sesion.dataset
        self.inicio.set_visibility(dataset is None)
        self.contenido.set_visibility(dataset is not None)
        if dataset is None:
            self.etiqueta_ruta.set_text("Ningún archivo cargado")
            self.etiqueta_resumen.set_text("")
            return
        if dataset is self._mostrado:
            return
        self._mostrado = dataset
        self.etiqueta_ruta.set_text(dataset.ruta)
        self.etiqueta_resumen.set_text(texto_resumen(dataset.datos))
        self.tabla.mostrar(dataset.datos)
        self.tabla.tabla.style("height: " + alto_tabla(len(dataset.datos)))

    async def cargar(self):
        """Abre el explorador e importa el archivo elegido."""
        ruta = await seleccionar_archivo(carpeta_inicial(self.sesion))
        if ruta is None:
            return  # el usuario cerró el explorador: todo sigue igual
        try:
            datos = importar_datos(ruta)
        except ErrorImportacion as error:
            notificar_error(error)
            return
        self.sesion.cargar_dataset(datos, ruta)
        notificar_exito("Dataset cargado correctamente")
