"""Página principal de la interfaz gráfica de SIKORIUS."""

from nicegui import ui

from sikorius.aplicacion.sesion import ETAPAS
from sikorius.gui.paneles.base import Panel
from sikorius.gui.paneles.panel_columnas import PanelColumnas
from sikorius.gui.paneles.panel_dataset import PanelDataset
from sikorius.gui.paneles.panel_inicio import PanelInicio
from sikorius.gui.paneles.panel_modelo import PanelModelo
from sikorius.gui.paneles.panel_prediccion import PanelPrediccion
from sikorius.gui.paneles.panel_preprocesado import PanelPreprocesado
from sikorius.gui.paneles.panel_separacion import PanelSeparacion
from sikorius.gui.tema import aplicar_tema

# Quasar pone en mayúsculas el texto de todos los botones. Con "no-caps" se
# muestran tal cual se escriben: solo la primera letra en mayúscula.
ui.button.default_props("no-caps")


TITULOS = {
    "inicio": "Inicio",
    "datos": "Datos",
    "variables": "Variables y separacion",
    "preprocesado": "Preprocesado",
    "modelo": "Modelo",
}


class Pestanas(Panel):
    """Pestañas de arriba: cada etapa se abre al completar la anterior.

    Las pestañas no disponibles no se ven. El grupo va centrado en la
    barra, así que al abrirse una nueva todas se recolocan para seguir
    centradas (ver recursos/estilos.css). Si
    una etapa deja de estar disponible mientras el usuario la está viendo
    (por ejemplo, al cargar otro dataset estando en "Modelo"), se le lleva
    a la última etapa que sí lo está.

    "Inicio" es la pantalla de arranque y está siempre. Al subir un
    dataset se lleva al usuario a "Datos" para que lo vea. Al cargar un
    modelo de un archivo (historia #24) solo quedan "Inicio" y "Modelo", y
    se le lleva a "Modelo".
    """

    def __init__(self, sesion):
        # Sin dataset se ve la pantalla de inicio y la barra no hace falta
        self.header = ui.header().classes("items-center")
        # Tres columnas: nombre, pestañas y acciones. Las de los lados miden
        # lo mismo, así que las pestañas quedan en el centro exacto de la
        # barra aunque a la derecha se añadan botones (ver estilos.css).
        with self.header, ui.element("div").classes("sk-barra"):
            ui.label("SIKORIUS").classes("text-xl font-bold")
            self.tabs = ui.tabs().props("no-caps")
            self.pestanas = {}
            with self.tabs:
                for etapa in ETAPAS:
                    self.pestanas[etapa] = ui.tab(
                        etapa, label=TITULOS[etapa]
                    ).classes("sk-pestana")
            # Hueco de la derecha para botones como "Continuar"
            self.acciones = ui.row().classes("items-center justify-end")
        # El contenido se coloca después, dentro de self.paneles
        # "my-auto" centra verticalmente el contenido de la pestaña en el
        # espacio que queda libre (ver recursos/estilos.css)
        self.paneles = ui.tab_panels(self.tabs, value="inicio").classes(
            "w-full bg-transparent my-auto"
        )
        # Último modelo cargado de un archivo al que ya se ha llevado al
        # usuario: solo se le lleva a "Modelo" una vez por cada carga.
        self._modelo_cargado = None
        # Lo mismo con el dataset: se lleva al usuario a "Datos" una vez
        # por cada dataset nuevo, no en cada aviso de la sesión
        self._dataset = None
        super().__init__(sesion)

    def actualizar(self):
        cargado = self.sesion.modelo_cargado
        self.header.set_value(self.sesion.dataset is not None or cargado)
        disponibles = self.sesion.etapas_disponibles()
        for etapa, pestana in self.pestanas.items():
            pestana.set_visibility(etapa in disponibles)
        dataset = self.sesion.dataset
        dataset_nuevo = dataset is not None and dataset is not self._dataset
        self._dataset = dataset
        if cargado and self.sesion.modelo is not self._modelo_cargado:
            self._modelo_cargado = self.sesion.modelo
            self.paneles.set_value("modelo")
        elif dataset_nuevo:
            self.paneles.set_value("datos")
        elif self.paneles.value not in disponibles:
            self.paneles.set_value(disponibles[-1])


def construir_pagina(sesion):
    """Coloca los paneles en la página, en el orden del flujo de trabajo.

    Cada panel se suscribe a la sesión y se actualiza solo: aquí no se
    conectan unos paneles con otros.
    """
    aplicar_tema()
    pestanas = Pestanas(sesion)
    with pestanas.paneles:
        with ui.tab_panel("inicio"):
            PanelInicio(sesion)
        with ui.tab_panel("datos"):
            PanelDataset(sesion)
        # Columnas a la izquierda y separación a la derecha. "basis-0"
        # reparte el ancho a partes iguales sin depender del contenido,
        # "items-stretch" iguala la altura de las dos columnas y "*:grow"
        # hace que la tarjeta de cada panel la ocupe entera.
        with (
            ui.tab_panel("variables"),
            ui.row().classes("w-full items-stretch no-wrap gap-4"),
        ):
            with ui.column().classes("basis-0 grow min-w-0 *:grow"):
                PanelColumnas(sesion)
            with ui.column().classes("basis-0 grow min-w-0 *:grow"):
                PanelSeparacion(sesion)
        with ui.tab_panel("preprocesado"):
            PanelPreprocesado(sesion)
        with ui.tab_panel("modelo"), ui.column().classes("w-full gap-4"):
            PanelModelo(sesion)
            PanelPrediccion(sesion)
