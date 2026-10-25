"""Página principal de la interfaz gráfica de SIKORIUS."""

from pathlib import Path

from nicegui import ui

from sikorius.estado import estado
from sikorius.gui.selector_archivos import seleccionar_archivo
from sikorius.gui.panel_separacion import PanelSeparacion
from sikorius.gui.selector_columnas import PanelSeleccionColumnas
from sikorius.gui.tabla_datos import TablaDatos
from sikorius.importador import ErrorImportacion


def carpeta_inicial():
    """Carpeta del último archivo cargado o, si no hay, la carpeta personal."""
    if estado.ruta is not None:
        return Path(estado.ruta).parent
    return Path.home()


@ui.page("/")
def pagina_principal():
    with ui.header().classes("items-center"):
        ui.label("SIKORIUS").classes("text-xl font-bold")

    # --- Carga del dataset ---
    with ui.card().classes("w-full"):
        ui.label("Dataset").classes("text-lg font-semibold")
        with ui.row().classes("w-full items-center no-wrap"):
            boton_cargar = ui.button("Cargar dataset", icon="folder_open") \
                .props("size=lg")
            with ui.column().classes("gap-0 min-w-0"):
                ui.label("Ruta del archivo cargado:").classes("text-sm text-gray-500")
                etiqueta_ruta = ui.label("Ningún archivo cargado") \
                    .classes("font-mono break-all")
        etiqueta_resumen = ui.label("").classes("text-sm text-gray-500")

    # --- Tabla con los datos ---
    with ui.card().classes("w-full"):
        ui.label("Datos").classes("text-lg font-semibold")
        tabla = TablaDatos()

    # --- Selección de columnas de entrada y salida (historia #11) ---
    with ui.card().classes("w-full"):
        ui.label("Columnas del modelo").classes("text-lg font-semibold")
        panel_columnas = PanelSeleccionColumnas(
            estado, al_cambiar=lambda: panel_separacion.actualizar())

    # --- Separación en entrenamiento y test ---
    with ui.card().classes("w-full"):
        ui.label("Entrenamiento y test").classes("text-lg font-semibold")
        panel_separacion = PanelSeparacion(estado)

    def refrescar():
        """Muestra en pantalla los datos guardados en el estado."""
        etiqueta_ruta.set_text(estado.ruta)
        etiqueta_resumen.set_text(
            str(len(estado.datos)) + " filas y "
            + str(len(estado.datos.columns)) + " columnas")
        tabla.mostrar(estado.datos)
        panel_columnas.cargar_columnas(estado.datos)

    async def cargar_dataset():
        ruta = await seleccionar_archivo(carpeta_inicial())
        if ruta is None:
            return  # el usuario cerró el explorador: se mantiene todo igual

        try:
            estado.cargar(ruta)
        except ErrorImportacion as error:
            ui.notify(str(error), type="negative", multi_line=True,
                      close_button="Cerrar")
            return

        refrescar()
        ui.notify("Dataset cargado correctamente", type="positive")

    boton_cargar.on_click(cargar_dataset)

    # Si se recarga la página, se vuelven a mostrar los datos ya cargados
    if estado.hay_datos():
        refrescar()


def ejecutar():
    """Arranca la interfaz gráfica en el navegador."""
    ui.run(title="SIKORIUS", reload=False)


# Para arrancar la GUI: uv run python -m sikorius.gui.app
if __name__ in {"__main__", "__mp_main__"}:
    ejecutar()