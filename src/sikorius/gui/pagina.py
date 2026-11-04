"""Página principal de la interfaz gráfica de SIKORIUS."""

from nicegui import ui

from sikorius.gui.paneles.panel_dataset import PanelDataset

# Quasar pone en mayúsculas el texto de todos los botones. Con "no-caps" se
# muestran tal cual se escriben: solo la primera letra en mayúscula.
ui.button.default_props("no-caps")


def construir_pagina(sesion):
    """Coloca los paneles en la página, en el orden del flujo de trabajo.

    Cada panel se suscribe a la sesión y se actualiza solo: aquí no se
    conectan unos paneles con otros.
    """
    with ui.header().classes("items-center"):
        ui.label("SIKORIUS").classes("text-xl font-bold")

    PanelDataset(sesion)
