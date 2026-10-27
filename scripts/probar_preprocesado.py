"""Página de prueba local del botón "Aplicar preprocesado" (tarea #110).

Solo sirve para probar tu parte mientras no estén los controles reales de
la tarea #109 (estrategia y valor constante). NO se sube al repositorio.

Para arrancarla, desde la raíz del proyecto:
    uv run python probar_preprocesado.py
"""

import numpy as np
import pandas as pd
from nicegui import ui

from sikorius.estado import estado
from sikorius.gui.boton_preprocesado import crear_boton_preprocesado
from sikorius.preprocesado import columnas_seleccionadas, modelo_disponible
from sikorius.separacion import separar_datos

ESTRATEGIAS = {
    "eliminar": "Eliminar filas",
    "media": "Media",
    "mediana": "Mediana",
    "constante": "Valor constante",
}


def preparar_estado():
    """Carga un dataset con huecos y lo separa, como haría la aplicación."""
    datos = pd.DataFrame({
        "x1": [1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, np.nan, 9.0, 10.0],
        "x2": [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, np.nan, 6.0, 5.0, 3.0],
        "y": [2.0, 4.0, 6.0, np.nan, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0],
    })
    estado.datos = datos
    estado.guardar_seleccion(["x1", "x2"], "y", "multiple")
    entrenamiento, test = separar_datos(datos, 30, 42)
    estado.guardar_separacion(entrenamiento, test, 30, 42)


def nulos(df, columnas):
    return {c: int(df[c].isna().sum()) for c in columnas}


@ui.page("/")
def pagina():
    preparar_estado()
    with ui.card().classes("w-full max-w-xl mx-auto"):
        ui.label("Prueba de preprocesado (#110)").classes("text-xl font-bold")
        info = ui.label().classes("whitespace-pre-line")

        estrategia = ui.radio(ESTRATEGIAS, value="eliminar").props("inline")
        constante = ui.number("Valor constante")
        constante.disable()
        estrategia.on_value_change(
            lambda e: constante.enable() if e.value == "constante"
            else constante.disable())

        boton_modelo = ui.button(
            "Crear modelo (simulado)",
            on_click=lambda: ui.notify("Modelo creado (simulado)"))

        def refrescar():
            columnas = columnas_seleccionadas(estado)
            if estado.preprocesado is not None:
                tr = estado.preprocesado["entrenamiento"]
                te = estado.preprocesado["test"]
            else:
                tr, te = estado.entrenamiento, estado.test
            info.set_text(f"Entrenamiento: {nulos(tr, columnas)}\n"
                          f"Test: {nulos(te, columnas)}")
            if modelo_disponible(estado):
                boton_modelo.enable()
            else:
                boton_modelo.disable()

        crear_boton_preprocesado(
            obtener_estrategia=lambda: estrategia.value,
            obtener_constante=lambda: constante.value,
            al_aplicar=refrescar,
        )
        refrescar()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Prueba de preprocesado")