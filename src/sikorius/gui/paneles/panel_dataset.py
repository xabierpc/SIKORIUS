"""Pestaña "Datos": la tabla con el dataset cargado.

La pantalla de inicio (logo y botones de subir un dataset o cargar un
modelo) es otra pestaña, ver ``panel_inicio``. Esta solo tiene sentido con
un dataset: sin él, la pestaña no se ve (``Sesion.etapas_disponibles``).
"""

from nicegui import ui

from sikorius.gui.componentes import carga_dataset
from sikorius.gui.componentes.tabla_datos import TablaDatos
from sikorius.gui.paneles.base import Panel
from sikorius.gui.tema import colores_columnas

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


def texto_resumen(datos):
    """Texto como "20640 filas y 10 columnas"."""
    return (
        str(len(datos)) + " filas y " + str(len(datos.columns)) + " columnas"
    )


class PanelDataset(Panel):
    """Ruta y tamaño del dataset, la tabla y el botón de cargar otro.

    Para cargar un modelo guardado se vuelve a la pestaña "Inicio".
    """

    def __init__(self, sesion):
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
        """Carga otro dataset (ver ``componentes.carga_dataset``)."""
        await carga_dataset.cargar_dataset(self.sesion)
