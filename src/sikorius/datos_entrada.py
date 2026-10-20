import tempfile
from pathlib import Path

from nicegui import ui

from importador import ErrorImportacion, importar_datos

EXTENSIONES_ADMITIDAS = ".csv,.xlsx,.xls,.sqlite,.db"


class SelectorFeatures:
    """
    Selector dinámico de columnas de entrada (features).

    - Regresión simple   -> selección simple (una sola columna).
    - Regresión múltiple -> selección múltiple.
    - Al cargar un dataset nuevo muestra sus columnas y limpia la selección anterior.
    """

    SIMPLE = "simple"
    MULTIPLE = "multiple"

    def __init__(self, tipo_regresion="multiple"):
        self.columnas = []
        self.tipo_regresion = tipo_regresion
        self.selector = None
        self.contenedor = ui.column().classes("w-full")
        self._construir_selector()

    def _construir_selector(self):
        """(Re)crea el ui.select según el tipo de regresión, sin selección previa."""
        self.contenedor.clear()

        if self.tipo_regresion == self.MULTIPLE:
            es_multiple = True
            etiqueta = "Features (selección múltiple)"
            valor_inicial = []
        else:
            es_multiple = False
            etiqueta = "Feature (selección simple)"
            valor_inicial = None

        with self.contenedor:
            self.selector = ui.select(
                options=self.columnas,
                label=etiqueta,
                multiple=es_multiple,
                value=valor_inicial,
                clearable=True,
            ).classes("w-full")

            if es_multiple:
                self.selector.props("use-chips")

            if len(self.columnas) == 0:
                self.selector.disable()
            else:
                self.selector.enable()

    def cambiar_tipo_regresion(self, tipo_regresion):
        """Cambia entre selección simple y múltiple; limpia la selección."""
        if tipo_regresion != self.SIMPLE and tipo_regresion != self.MULTIPLE:
            raise ValueError("Tipo de regresión no válido: " + str(tipo_regresion))
        self.tipo_regresion = tipo_regresion
        self._construir_selector()

    def cargar_columnas(self, df):
        """Muestra las columnas de un dataset nuevo y limpia la selección anterior."""
        self.columnas = []
        for columna in df.columns:
            self.columnas.append(str(columna))
        self._construir_selector()

    def obtener_seleccion(self):
        """Devuelve siempre una lista de features (vacía si no hay selección)."""
        valor = self.selector.value
        if valor is None:
            return []
        if isinstance(valor, list):
            return list(valor)
        return [valor]


async def importar_archivo_subido(archivo):
    """
    Guarda el archivo subido en una carpeta temporal (conservando su nombre,
    para que importar_datos detecte el formato por la extensión) y lo importa.
    Lanza ErrorImportacion si el archivo no se puede leer.
    """
    with tempfile.TemporaryDirectory() as carpeta:
        nombre = Path(archivo.name).name
        ruta = Path(carpeta) / nombre
        await archivo.save(ruta)
        return importar_datos(ruta)


# --- Demo mínima: carga de datos + tipo de regresión -----------------------
@ui.page("/")
def pagina_principal():
    with ui.card().classes("w-full max-w-xl mx-auto"):
        ui.label("Selector de features").classes("text-xl font-bold")

        tipo = ui.radio(
            {SelectorFeatures.SIMPLE: "Regresión simple", SelectorFeatures.MULTIPLE: "Regresión múltiple"},
            value=SelectorFeatures.MULTIPLE,
        ).props("inline")

        async def al_subir(evento):
            try:
                df = await importar_archivo_subido(evento.file)
            except ErrorImportacion as error:
                ui.notify(str(error), type="negative")
                return
            except Exception as error:
                ui.notify("Error inesperado al importar: " + str(error), type="negative")
                return
            selector.cargar_columnas(df)
            ui.notify(
                "Dataset cargado: " + str(len(df)) + " filas, " + str(len(df.columns)) + " columnas",
                type="positive",
            )
            subida.reset()

        subida = ui.upload(
            label="Cargar datos (CSV, Excel o SQLite)",
            on_upload=al_subir,
            auto_upload=True,
        ).props("accept=" + EXTENSIONES_ADMITIDAS).classes("w-full")

        selector = SelectorFeatures(tipo_regresion=tipo.value)
        tipo.on_value_change(lambda evento: selector.cambiar_tipo_regresion(evento.value))


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Selector de features")