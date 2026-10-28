"""Preprocesado de los datos antes de crear el modelo (historia #26).

El panel muestra los valores inexistentes detectados en las columnas
seleccionadas (por separado en entrenamiento y test), deja elegir la
estrategia de tratamiento y la aplica con el botón "Aplicar preprocesado".

Toda la detección y el tratamiento están en ``sikorius.preprocesado``;
aquí solo se leen los controles y se muestra el resultado.
"""

from nicegui import ui

from sikorius.gui.boton_preprocesado import crear_boton_preprocesado
from sikorius.preprocesado import (
    CONSTANTE, ELIMINAR, MEDIA, MEDIANA, columnas_seleccionadas,
    detectar_en_estado, hay_nulos,
)

OPCIONES_ESTRATEGIA = {
    ELIMINAR: "Eliminar filas con valores inexistentes",
    MEDIA: "Rellenar con la media (de entrenamiento)",
    MEDIANA: "Rellenar con la mediana (de entrenamiento)",
    CONSTANTE: "Rellenar con un valor constante",
}


class PanelPreprocesado:
    """Detección de valores inexistentes + estrategia + botón de aplicar.

    Solo está disponible cuando hay selección de columnas y separación en
    entrenamiento y test. Hay que llamar a ``actualizar`` cada vez que
    cambien la selección o la separación, para volver a detectar.
    """

    def __init__(self, estado, al_aplicar=None):
        self.estado = estado
        self.al_aplicar = al_aplicar

        self.aviso = ui.label("").classes("text-sm")
        self.tabla = ui.table(
            columns=[
                {"name": "columna", "label": "Columna", "field": "columna",
                 "align": "left"},
                {"name": "train", "label": "Entrenamiento", "field": "train"},
                {"name": "test", "label": "Test", "field": "test"},
            ],
            rows=[],
            row_key="columna",
        ).classes("w-full")

        self.controles = ui.column().classes("w-full")
        with self.controles:
            ui.label("Estrategia de tratamiento").classes("font-medium")
            self.estrategia = ui.radio(OPCIONES_ESTRATEGIA, value=ELIMINAR)
            self.constante = ui.number("Valor constante").classes("w-48")
            self.boton = crear_boton_preprocesado(
                obtener_estrategia=lambda: self.estrategia.value,
                obtener_constante=lambda: self.constante.value,
                al_aplicar=self._tras_aplicar,
            )

        self.estrategia.on_value_change(self._actualizar_constante)
        self._actualizar_constante()
        self.actualizar()

    def _actualizar_constante(self, _evento=None):
        """El campo del valor constante solo se habilita con esa opción."""
        if self.estrategia.value == CONSTANTE:
            self.constante.enable()
        else:
            self.constante.disable()

    def _tras_aplicar(self):
        self.actualizar()
        if self.al_aplicar is not None:
            self.al_aplicar()

    def actualizar(self):
        """Vuelve a detectar los valores inexistentes y muestra el resultado."""
        deteccion = detectar_en_estado(self.estado)

        if deteccion is None:
            self.aviso.set_text(
                "Separa primero los datos en entrenamiento y test para "
                "detectar los valores inexistentes.")
            self.aviso.classes(replace="text-sm text-gray-500")
            self.tabla.rows = []
            self.tabla.update()
            self.tabla.set_visibility(False)
            self.controles.set_visibility(False)
            return

        columnas = columnas_seleccionadas(self.estado)
        self.tabla.rows = [
            {"columna": c, "train": deteccion["train"][c],
             "test": deteccion["test"][c]}
            for c in columnas
        ]
        self.tabla.update()
        self.tabla.set_visibility(True)

        if hay_nulos(deteccion):
            total_train = sum(deteccion["train"].values())
            total_test = sum(deteccion["test"].values())
            self.aviso.set_text(
                "Se han detectado valores inexistentes. Entrenamiento: "
                + str(total_train) + " | Test: " + str(total_test)
                + ". Elige cómo tratarlos.")
            self.aviso.classes(replace="text-sm text-orange-700")
            self.controles.set_visibility(True)
        else:
            self.aviso.set_text(
                "No hay valores inexistentes en las columnas seleccionadas. "
                "Puedes continuar sin preprocesar.")
            self.aviso.classes(replace="text-sm text-green-700")
            self.controles.set_visibility(False)
