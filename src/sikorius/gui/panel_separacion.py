"""Separación del dataset en entrenamiento y test.

El panel solo recoge el porcentaje de test y la semilla, llama a
``sikorius.separacion.separar_datos`` y guarda el resultado en el estado de
la aplicación. Toda la lógica de la separación está fuera de la GUI.
"""

from nicegui import ui

from sikorius.separacion import (
    PORCENTAJE_TEST_DEFECTO, SEMILLA_DEFECTO, ErrorSeparacion,
    interpretar_porcentaje, interpretar_semilla, separar_datos,
)


class PanelSeparacion:
    """Porcentaje de test + semilla + botón "Separar datos" + resultado.

    Solo está disponible cuando hay una selección de columnas confirmada en
    el estado. Hay que llamar a ``actualizar`` cada vez que cambie la
    selección o el dataset, para habilitar o deshabilitar el panel.
    """

    def __init__(self, estado):
        self.estado = estado

        self.aviso = ui.label("").classes("text-sm text-gray-500")
        with ui.row().classes("w-full items-start"):
            self.entrada_porcentaje = ui.input(
                "Porcentaje de test (%)", value=str(PORCENTAJE_TEST_DEFECTO),
                on_change=self._mostrar_entrenamiento,
            ).classes("w-48")
            self.entrada_semilla = ui.input(
                "Semilla", value=str(SEMILLA_DEFECTO)).classes("w-48")
        self.etiqueta_entrenamiento = ui.label("").classes("text-sm")
        self.boton_separar = ui.button("Separar datos", icon="call_split",
                                       on_click=self.separar)
        self.etiqueta_resultado = ui.label("").classes("text-sm")

        self._mostrar_entrenamiento()
        self.actualizar()

    def _mostrar_entrenamiento(self, _evento=None):
        """Muestra el porcentaje de entrenamiento (complementario del de test)."""
        try:
            porcentaje = interpretar_porcentaje(self.entrada_porcentaje.value)
        except ErrorSeparacion:
            self.etiqueta_entrenamiento.set_text("Entrenamiento: -")
            return
        self.etiqueta_entrenamiento.set_text(
            "Entrenamiento: " + _formatear(100 - porcentaje) + " %")

    def actualizar(self):
        """Habilita el panel solo si hay selección confirmada y muestra el
        resultado de la separación actual, si la hay."""
        if self.estado.hay_seleccion():
            self.aviso.set_text("")
            self.entrada_porcentaje.enable()
            self.entrada_semilla.enable()
            self.boton_separar.enable()
        else:
            self.aviso.set_text(
                "Confirma primero la selección de columnas para poder separar los datos.")
            self.entrada_porcentaje.disable()
            self.entrada_semilla.disable()
            self.boton_separar.disable()

        if self.estado.hay_separacion():
            self.etiqueta_resultado.set_text(
                "Entrenamiento: " + str(len(self.estado.entrenamiento))
                + " filas | Test: " + str(len(self.estado.test)) + " filas")
        else:
            self.etiqueta_resultado.set_text("")

    def separar(self):
        """Separa el dataset con los valores del formulario y guarda el resultado."""
        if not self.estado.hay_seleccion():
            ui.notify("Confirma primero la selección de columnas.", type="negative")
            return
        try:
            porcentaje = interpretar_porcentaje(self.entrada_porcentaje.value)
            semilla = interpretar_semilla(self.entrada_semilla.value)
            entrenamiento, test = separar_datos(self.estado.datos, porcentaje, semilla)
        except ErrorSeparacion as error:
            ui.notify(str(error), type="negative", multi_line=True)
            return
        self.estado.guardar_separacion(entrenamiento, test, porcentaje, semilla)
        self.actualizar()
        ui.notify(
            "Datos separados correctamente. Entrenamiento: " + str(len(entrenamiento))
            + " filas | Test: " + str(len(test)) + " filas",
            type="positive", multi_line=True)


def _formatear(numero):
    """80.0 -> "80", 87.5 -> "87.5"."""
    return str(int(numero)) if float(numero).is_integer() else str(round(numero, 2))
