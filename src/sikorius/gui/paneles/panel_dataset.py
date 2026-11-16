"""Carga del dataset: pantalla de inicio con el logo y tabla con los datos.

Mientras no hay dataset se ve la pantalla de inicio (el logo, que se
escribe solo, y el botón de subir el archivo). En cuanto se carga uno, la
pantalla de inicio desaparece y ocupa su lugar la tabla con los datos.
"""

from pathlib import Path

from nicegui import ui

from sikorius.dominio.errores import ErrorImportacion
from sikorius.gui.avisos import notificar_error, notificar_exito
from sikorius.gui.componentes.explorador_archivos import seleccionar_archivo
from sikorius.gui.componentes.tabla_datos import TablaDatos
from sikorius.gui.paneles.base import Panel
from sikorius.gui.tema import CARPETA_RECURSOS, colores_columnas

# El logo es un SVG con su animación dentro (ver recursos/logo.svg). Se
# incrusta como HTML y no con ui.image porque una imagen no deja que el CSS
# anime sus piezas.
RUTA_LOGO = CARPETA_RECURSOS / "logo.svg"

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


def colores_elegidos(sesion):
    """{columna: color} de las columnas de la selección confirmada.

    Cada columna lleva el mismo color que su "chip" en el panel de columnas.
    Si todavía no hay selección, el diccionario está vacío.
    """
    seleccion = sesion.seleccion
    if sesion.dataset is None or seleccion is None:
        return {}
    todos = colores_columnas(sesion.dataset.datos.columns)
    elegidas = list(seleccion.features) + [seleccion.target]
    return {c: todos[c] for c in elegidas if c in todos}


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
        # Colores que lleva ahora la tabla (para no tocarla si no cambian)
        self._coloreado = {}
        super().__init__(sesion)

    def actualizar(self):
        dataset = self.sesion.dataset
        self.inicio.set_visibility(dataset is None)
        self.contenido.set_visibility(dataset is not None)
        if dataset is None:
            self.etiqueta_ruta.set_text("Ningún archivo cargado")
            self.etiqueta_resumen.set_text("")
            return
        if dataset is not self._mostrado:
            self._mostrar_dataset(dataset)
        # Las columnas elegidas se tiñen; al cambiar la selección (o al
        # cargar otro dataset, que la borra) se actualizan los colores
        colores = colores_elegidos(self.sesion)
        if colores != self._coloreado:
            self._coloreado = colores
            self.tabla.colorear(colores)

    def _mostrar_dataset(self, dataset):
        """Pone el dataset en la tabla (solo cuando es uno nuevo: enviar
        todas las filas al navegador en cada aviso haría la página lenta)."""
        self._mostrado = dataset
        self._coloreado = {}
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
            self.sesion.importar_dataset(ruta)
        except ErrorImportacion as error:
            notificar_error(error)
            return
        notificar_exito("Dataset cargado correctamente")
