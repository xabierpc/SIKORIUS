"""Carga del dataset: botón, ruta del archivo y tabla con los datos."""

from pathlib import Path

from nicegui import ui

from sikorius.gui.avisos import notificar_error, notificar_exito
from sikorius.gui.componentes.explorador_archivos import seleccionar_archivo
from sikorius.gui.componentes.tabla_datos import TablaDatos
from sikorius.gui.paneles.base import Panel
from sikorius.nucleo.errores import ErrorImportacion
from sikorius.nucleo.importador import importar_datos


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
    """Dos tarjetas: la carga del archivo y la tabla con sus datos."""

    def __init__(self, sesion):
        with ui.card().classes("w-full"):
            ui.label("Dataset").classes("text-lg font-semibold")
            with ui.row().classes("w-full items-center no-wrap"):
                self.boton_cargar = ui.button(
                    "Cargar dataset", icon="folder_open", on_click=self.cargar
                )
                with ui.column().classes("gap-0 min-w-0"):
                    ui.label("Ruta:").classes("text-sm text-secondary")
                    self.etiqueta_ruta = ui.label("").classes(
                        "font-mono break-all"
                    )

        with ui.card().classes("w-full"):
            ui.label("Datos").classes("text-lg font-semibold")
            self.tabla = TablaDatos()
            self.etiqueta_resumen = ui.label("").classes(
                "text-sm text-secondary"
            )

        # Dataset que se ve ahora en la tabla. La sesión avisa en cada paso
        # (columnas, separación...), y volver a enviar todas las filas al
        # navegador en cada aviso haría la página muy lenta.
        self._mostrado = None
        super().__init__(sesion)

    def actualizar(self):
        dataset = self.sesion.dataset
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
