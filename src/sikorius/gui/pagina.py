"""Página principal de la interfaz gráfica de SIKORIUS."""

from nicegui import ui

from sikorius.gui.paneles.base import Panel
from sikorius.gui.paneles.panel_columnas import PanelColumnas
from sikorius.gui.paneles.panel_dataset import PanelDataset
from sikorius.gui.paneles.panel_modelo import PanelModelo
from sikorius.gui.paneles.panel_preprocesado import PanelPreprocesado
from sikorius.gui.paneles.panel_separacion import PanelSeparacion
from sikorius.gui.tema import aplicar_tema
from sikorius.sesion import ETAPAS

# Quasar pone en mayúsculas el texto de todos los botones. Con "no-caps" se
# muestran tal cual se escriben: solo la primera letra en mayúscula.
ui.button.default_props("no-caps")


TITULOS = {
    "datos": "Datos",
    "variables": "Variables y separación",
    "preprocesado": "Preprocesado",
    "modelo": "Modelo",
}


class Pestanas(Panel):
    """Pestañas de arriba: cada etapa se abre al completar la anterior.

    Las pestañas no disponibles se ven apagadas y no se pueden pulsar. Si
    una etapa deja de estar disponible mientras el usuario la está viendo
    (por ejemplo, al cargar otro dataset estando en "Modelo"), se le lleva
    a la última etapa que sí lo está.
    """

    def __init__(self, sesion):
        with ui.header().classes("items-center"):
            ui.label("SIKORIUS").classes("text-xl font-bold")
            ui.space()
            self.tabs = ui.tabs().props("no-caps")
            self.pestanas = {}
            with self.tabs:
                for etapa in ETAPAS:
                    self.pestanas[etapa] = ui.tab(etapa, label=TITULOS[etapa])
        # El contenido se coloca después, dentro de self.paneles
        self.paneles = ui.tab_panels(self.tabs, value="datos").classes(
            "w-full bg-transparent"
        )
        super().__init__(sesion)

    def actualizar(self):
        disponibles = self.sesion.etapas_disponibles()
        for etapa, pestana in self.pestanas.items():
            if etapa in disponibles:
                pestana.enable()
            else:
                pestana.disable()
        if self.paneles.value not in disponibles:
            self.paneles.set_value(disponibles[-1])


def construir_pagina(sesion):
    """Coloca los paneles en la página, en el orden del flujo de trabajo.

    Cada panel se suscribe a la sesión y se actualiza solo: aquí no se
    conectan unos paneles con otros.
    """
    aplicar_tema()
    pestanas = Pestanas(sesion)
    with pestanas.paneles:
        with ui.tab_panel("datos"):
            PanelDataset(sesion)
        # Columnas a la izquierda y separación a la derecha. "basis-0"
        # reparte el ancho a partes iguales sin depender del contenido.
        with (
            ui.tab_panel("variables"),
            ui.row().classes("w-full items-start no-wrap gap-4"),
        ):
            with ui.column().classes("basis-0 grow min-w-0"):
                PanelColumnas(sesion)
            with ui.column().classes("basis-0 grow min-w-0"):
                PanelSeparacion(sesion)
        with ui.tab_panel("preprocesado"):
            PanelPreprocesado(sesion)
        with ui.tab_panel("modelo"):
            PanelModelo(sesion)
