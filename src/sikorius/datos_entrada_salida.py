"""Demo independiente de la selección de columnas (historia #11).

Los selectores están en ``sikorius.gui.selector_columnas`` y son los mismos
que usa la aplicación principal (``sikorius.gui.app``). Esta demo carga el
dataset con ``ui.upload`` en vez de con el explorador de archivos.

Para arrancarla: uv run python -m sikorius.datos_entrada_salida
"""

import tempfile
from pathlib import Path

from nicegui import ui

from sikorius.gui.selector_columnas import SelectorFeatures, SelectorTarget
from sikorius.importador import ErrorImportacion, importar_datos
from sikorius.validacion import ErrorSeleccion, validar_seleccion

EXTENSIONES_ADMITIDAS = ".csv,.xlsx,.xls,.sqlite,.db"


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

        estado = {"df": None, "seleccion": None}

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
            target.cargar_columnas(df)
            estado["df"] = df
            estado["seleccion"] = None
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
        target = SelectorTarget(al_abrir=lambda: target.excluir(selector.obtener_seleccion()))

        def confirmar():
            if estado["df"] is None:
                ui.notify("Carga primero un dataset.", type="negative")
                return
            features = selector.obtener_seleccion()
            objetivo = target.obtener_seleccion()
            try:
                validar_seleccion(estado["df"], features, objetivo)
            except ErrorSeleccion as error:
                ui.notify(str(error), type="negative", multi_line=True)
                return
            estado["seleccion"] = {"features": features, "target": objetivo}
            ui.notify(
                "Selección confirmada. Entrada: " + ", ".join(features) + " | Salida: " + objetivo,
                type="positive",
                multi_line=True,
            )

        ui.button("Confirmar selección", on_click=confirmar)

        def al_cambiar_tipo(evento):
            selector.cambiar_tipo_regresion(evento.value)
            estado["seleccion"] = None

        tipo.on_value_change(al_cambiar_tipo)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Selector de features")