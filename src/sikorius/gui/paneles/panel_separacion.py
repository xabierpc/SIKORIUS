"""Separación del dataset en entrenamiento y test.

El panel solo recoge el porcentaje de test y la semilla, llama a
``sikorius.nucleo.separacion.separar_datos`` y guarda el resultado en la
sesión. Toda la lógica de la separación está fuera de la GUI.
"""

from nicegui import ui

from sikorius.gui.avisos import notificar_error, notificar_exito
from sikorius.gui.paneles.base import Panel
from sikorius.nucleo.separacion import (
    PORCENTAJE_TEST_DEFECTO,
    SEMILLA_DEFECTO,
    ErrorSeparacion,
    interpretar_porcentaje,
    interpretar_semilla,
    separar_datos,
)
from sikorius.nucleo.texto import formatear_numero


def texto_resultado(separacion):
    """Texto como "Entrenamiento: 80 filas | Test: 20 filas"."""
    return (
        "Entrenamiento: "
        + str(len(separacion.entrenamiento))
        + " filas | Test: "
        + str(len(separacion.test))
        + " filas"
    )


class PanelSeparacion(Panel):
    """Porcentaje de test + semilla + botón "Separar datos" + resultado.

    Solo está disponible cuando hay una selección de columnas confirmada en
    la sesión.
    """

    def __init__(self, sesion):
        with ui.card().classes("w-full"):
            ui.label("Entrenamiento y test").classes("text-lg font-semibold")
            self.aviso = ui.label("").classes("text-sm text-gray-500")

            # Todo en una sola fila para ocupar poco alto: los campos a la
            # izquierda, los porcentajes y el resultado en medio y el botón
            # pegado a la derecha (ui.space empuja el botón hasta el borde).
            with ui.row().classes("w-full items-center gap-4"):
                self.entrada_porcentaje = (
                    ui.input(
                        "Porcentaje de test (%)",
                        value=str(PORCENTAJE_TEST_DEFECTO),
                        on_change=self._mostrar_entrenamiento,
                    )
                    .props("dense")
                    .classes("w-44")
                )
                self.entrada_semilla = (
                    ui.input("Semilla", value=str(SEMILLA_DEFECTO))
                    .props("dense")
                    .classes("w-44")
                )
                with ui.column().classes("gap-0"):
                    self.etiqueta_entrenamiento = ui.label("").classes(
                        "text-sm"
                    )
                    self.etiqueta_resultado = ui.label("").classes("text-sm")
                ui.space()
                self.boton_separar = ui.button(
                    "Separar datos", icon="call_split", on_click=self.separar
                )

        # Separación cuyos valores se ven ahora en los campos. Solo se
        # escriben al cambiar la separación: si se escribieran en cada aviso
        # de la sesión, se perdería lo que el usuario estuviera tecleando.
        self._separacion = None
        self._mostrar_entrenamiento()
        super().__init__(sesion)

    def _mostrar_entrenamiento(self, _evento=None):
        """Muestra el porcentaje de entrenamiento (complementario del de
        test)."""
        try:
            porcentaje = interpretar_porcentaje(self.entrada_porcentaje.value)
        except ErrorSeparacion:
            self.etiqueta_entrenamiento.set_text("Entrenamiento: -")
            return
        self.etiqueta_entrenamiento.set_text(
            "Entrenamiento: " + formatear_numero(100 - porcentaje, 2) + " %"
        )

    def _mostrar_valores_usados(self, separacion):
        """Pone en los campos el porcentaje y la semilla con los que se
        separó (por ejemplo, al recargar la página)."""
        self.entrada_porcentaje.set_value(
            formatear_numero(separacion.porcentaje_test)
        )
        self.entrada_semilla.set_value(str(separacion.semilla))

    def actualizar(self):
        """Habilita el panel solo si hay selección confirmada y muestra el
        resultado de la separación actual, si la hay."""
        if self.sesion.seleccion is None:
            self.aviso.set_text(
                "Confirma primero la selección de columnas para poder "
                "separar los datos."
            )
            self.aviso.set_visibility(True)
            self.entrada_porcentaje.disable()
            self.entrada_semilla.disable()
            self.boton_separar.disable()
        else:
            self.aviso.set_text("")
            # Oculto no deja hueco en la tarjeta
            self.aviso.set_visibility(False)
            self.entrada_porcentaje.enable()
            self.entrada_semilla.enable()
            self.boton_separar.enable()

        separacion = self.sesion.separacion
        if separacion is None:
            self.etiqueta_resultado.set_text("")
        else:
            self.etiqueta_resultado.set_text(texto_resultado(separacion))
            if separacion is not self._separacion:
                self._mostrar_valores_usados(separacion)
        self._separacion = separacion

    def separar(self):
        """Separa el dataset con los valores del formulario y guarda el
        resultado en la sesión."""
        if self.sesion.seleccion is None:
            notificar_error("Confirma primero la selección de columnas.")
            return
        try:
            porcentaje = interpretar_porcentaje(self.entrada_porcentaje.value)
            semilla = interpretar_semilla(self.entrada_semilla.value)
            entrenamiento, test = separar_datos(
                self.sesion.dataset.datos, porcentaje, semilla
            )
        except ErrorSeparacion as error:
            notificar_error(error)
            return
        self.sesion.guardar_separacion(
            entrenamiento, test, porcentaje, semilla
        )
        notificar_exito(
            "Datos separados correctamente. "
            + texto_resultado(self.sesion.separacion)
        )
