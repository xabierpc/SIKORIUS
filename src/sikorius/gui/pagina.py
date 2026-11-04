"""Página principal de la interfaz gráfica de SIKORIUS."""

from nicegui import ui

from sikorius.gui.paneles.panel_columnas import PanelColumnas
from sikorius.gui.paneles.panel_dataset import PanelDataset
from sikorius.gui.paneles.panel_preprocesado import PanelPreprocesado
from sikorius.gui.paneles.panel_separacion import PanelSeparacion
from sikorius.gui.tema import aplicar_tema

# Quasar pone en mayúsculas el texto de todos los botones. Con "no-caps" se
# muestran tal cual se escriben: solo la primera letra en mayúscula.
ui.button.default_props("no-caps")


def construir_pagina(sesion):
    """Coloca los paneles en la página, en el orden del flujo de trabajo.

    Cada panel se suscribe a la sesión y se actualiza solo: aquí no se
    conectan unos paneles con otros.
    """
    aplicar_tema()
    with ui.header().classes("items-center"):
        ui.label("SIKORIUS").classes("text-xl font-bold")

    # El dataset ocupa dos tercios y las columnas y la separación el tercio
    # de la derecha, así se eligen viendo los datos. "basis-0" hace que el
    # reparto (2:1) no dependa del contenido y "min-w-0" deja que la tabla
    # encoja y saque su propio scroll horizontal.
    with ui.row().classes("w-full items-start no-wrap gap-4"):
        with ui.column().classes("basis-0 grow-[2] min-w-0"):
            PanelDataset(sesion)
        with ui.column().classes("basis-0 grow min-w-0"):
            PanelColumnas(sesion)
            PanelSeparacion(sesion)
    PanelPreprocesado(sesion)
