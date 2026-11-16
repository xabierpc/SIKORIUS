"""Selección de las columnas de entrada y salida del modelo (historia #11).

El panel junta los selectores de ``sikorius.gui.componentes.selectores`` con
el botón de confirmar. Valida la selección con el núcleo y, si es correcta,
la guarda en la sesión. Los paneles siguientes se enteran solos porque
están suscritos a la sesión.
"""

from nicegui import ui

from sikorius.gui.avisos import notificar_error, notificar_exito
from sikorius.gui.componentes.selectores import (
    SelectorFeatures,
    SelectorTarget,
)
from sikorius.gui.paneles.base import Panel
from sikorius.nucleo.columnas import ErrorSeleccion, validar_seleccion


def texto_seleccion(seleccion):
    """Texto como "Entrada: x1, x2 | Salida: y"."""
    return (
        "Entrada: "
        + ", ".join(seleccion.features)
        + " | Salida: "
        + seleccion.target
    )


class PanelColumnas(Panel):
    """Features + target + botón de confirmar."""

    def __init__(self, sesion):
        with ui.card().classes("w-full"):
            ui.label("Columnas del modelo").classes("text-lg font-semibold")
            self.features = SelectorFeatures()
            self.target = SelectorTarget(al_abrir=self._excluir_features)
            self.boton_confirmar = ui.button(
                "Confirmar selección", icon="check", on_click=self.confirmar
            )
            self.etiqueta_seleccion = ui.label("").classes(
                "text-sm text-secondary"
            )

        # Dataset cuyas columnas tienen ahora los selectores. Solo se
        # recrean al cambiar de dataset: si se recrearan en cada aviso de la
        # sesión (al separar, al preprocesar...), el usuario perdería lo que
        # estuviera eligiendo.
        self._dataset = None
        super().__init__(sesion)

    def _excluir_features(self):
        """Quita del target las columnas elegidas como features."""
        self.target.excluir(self.features.obtener_seleccion())

    def _cargar_columnas(self, dataset):
        """Pone en los selectores las columnas del dataset y vuelve a marcar
        la selección confirmada, si la hay (por ejemplo, al recargar la
        página)."""
        self.features.cargar_columnas(dataset.datos)
        self.target.cargar_columnas(dataset.datos)
        seleccion = self.sesion.seleccion
        if seleccion is not None:
            self.features.selector.set_value(list(seleccion.features))
            self._excluir_features()
            self.target.selector.set_value(seleccion.target)

    def actualizar(self):
        dataset = self.sesion.dataset
        if dataset is not self._dataset:
            self._dataset = dataset
            if dataset is not None:
                self._cargar_columnas(dataset)

        if dataset is None:
            self.boton_confirmar.disable()
        else:
            self.boton_confirmar.enable()

        if self.sesion.seleccion is None:
            self.etiqueta_seleccion.set_text("")
        else:
            self.etiqueta_seleccion.set_text(
                texto_seleccion(self.sesion.seleccion)
            )

    def confirmar(self):
        """Valida la selección y, si es correcta, la guarda en la sesión."""
        if self.sesion.dataset is None:
            notificar_error("Carga primero un dataset.")
            return
        features = self.features.obtener_seleccion()
        objetivo = self.target.obtener_seleccion()
        try:
            validar_seleccion(self.sesion.dataset.datos, features, objetivo)
        except ErrorSeleccion as error:
            notificar_error(error)
            return
        self.sesion.guardar_seleccion(features, objetivo)
        notificar_exito(
            "Selección confirmada. " + texto_seleccion(self.sesion.seleccion)
        )
