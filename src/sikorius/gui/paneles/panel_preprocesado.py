"""Preprocesado de los datos antes de crear el modelo (historia #26).

El panel muestra los valores inexistentes detectados en las columnas
seleccionadas (por separado en entrenamiento y test), deja elegir la
estrategia de tratamiento y la aplica con el botón "Aplicar preprocesado".

Toda la detección y el tratamiento están en ``sikorius.nucleo.preprocesado``;
aquí solo se leen los controles y se muestra el resultado.
"""

from nicegui import ui

from sikorius.gui.avisos import (
    notificar_aviso,
    notificar_error,
    notificar_exito,
)
from sikorius.gui.paneles.base import Panel
from sikorius.nucleo.errores import (
    AvisoPreprocesado,
    ErrorModelo,
    ErrorPreprocesado,
)
from sikorius.nucleo.preprocesado import (
    CONSTANTE,
    ELIMINAR,
    MEDIA,
    MEDIANA,
    detectar_nulos_conjuntos,
    hay_nulos,
)

OPCIONES_ESTRATEGIA = {
    ELIMINAR: "Eliminar filas con valores inexistentes",
    MEDIA: "Rellenar con la media (de entrenamiento)",
    MEDIANA: "Rellenar con la mediana (de entrenamiento)",
    CONSTANTE: "Rellenar con un valor constante",
}


def texto_resumen(resumen):
    """Mensaje de éxito a partir del resumen de ``aplicar_preprocesado``.

    Ejemplo: "Preprocesado aplicado. Entrenamiento: 0 filas eliminadas,
    2 valores rellenados | Test: 0 filas eliminadas, 1 valores rellenados."
    """
    partes = []
    for clave, nombre in (("train", "Entrenamiento"), ("test", "Test")):
        datos = resumen[clave]
        partes.append(
            nombre
            + ": "
            + str(datos["filas_eliminadas"])
            + " filas eliminadas, "
            + str(datos["valores_rellenados"])
            + " valores rellenados"
        )
    return "Preprocesado aplicado. " + " | ".join(partes) + "."


class PanelPreprocesado(Panel):
    """Detección de valores inexistentes + estrategia + botón de aplicar.

    Solo está disponible cuando hay selección de columnas y separación en
    entrenamiento y test.
    """

    def __init__(self, sesion):
        with ui.card().classes("w-full"):
            ui.label("Preprocesado").classes("text-lg font-semibold")
            self.aviso = ui.label("").classes("text-sm")
            self.tabla = ui.table(
                columns=[
                    {
                        "name": "columna",
                        "label": "Columna",
                        "field": "columna",
                        "align": "left",
                    },
                    {
                        "name": "train",
                        "label": "Entrenamiento",
                        "field": "train",
                    },
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
                self.boton = ui.button(
                    "Aplicar preprocesado", on_click=self.aplicar
                )
            self.aplicado = ui.label("").classes("text-sm text-secondary")

        self.estrategia.on_value_change(self._actualizar_constante)
        self._actualizar_constante()
        # Preprocesado cuya estrategia se ve ahora marcada. Solo se marca al
        # cambiar el preprocesado, para no deshacer lo que el usuario esté
        # eligiendo cuando la sesión avise por otro motivo.
        self._preprocesado = None
        super().__init__(sesion)

    def _actualizar_constante(self, _evento=None):
        """El campo del valor constante solo se habilita con esa opción."""
        if self.estrategia.value == CONSTANTE:
            self.constante.enable()
        else:
            self.constante.disable()

    def _detectar(self):
        """Valores inexistentes de los conjuntos SIN preprocesar, o None si
        aún no hay selección y separación.

        Se mira la separación y no el resultado del preprocesado: así, después
        de aplicar, se siguen viendo los valores que había y se puede cambiar
        de estrategia.
        """
        if self.sesion.seleccion is None or self.sesion.separacion is None:
            return None
        return detectar_nulos_conjuntos(
            self.sesion.separacion.entrenamiento,
            self.sesion.separacion.test,
            self.sesion.columnas_modelo(),
        )

    def _mostrar_tabla(self, deteccion):
        filas = []
        for columna in self.sesion.columnas_modelo():
            filas.append(
                {
                    "columna": str(columna),
                    "train": deteccion["train"][columna],
                    "test": deteccion["test"][columna],
                }
            )
        self.tabla.rows = filas
        self.tabla.update()
        self.tabla.set_visibility(True)

    def _mostrar_aplicado(self):
        """Etiqueta con la estrategia aplicada y, al recargar la página,
        esa estrategia marcada."""
        preprocesado = self.sesion.preprocesado
        if preprocesado is None:
            self.aplicado.set_text("")
        else:
            self.aplicado.set_text(
                "Aplicado: " + OPCIONES_ESTRATEGIA[preprocesado.estrategia]
            )
            if preprocesado is not self._preprocesado:
                self.estrategia.set_value(preprocesado.estrategia)
        self._preprocesado = preprocesado

    def actualizar(self):
        """Vuelve a detectar los valores inexistentes y muestra el
        resultado."""
        deteccion = self._detectar()
        if deteccion is None:
            self.aviso.set_text(
                "Separa primero los datos en entrenamiento y test para "
                "detectar los valores inexistentes."
            )
            self.aviso.classes(replace="text-sm text-secondary")
            self.tabla.rows = []
            self.tabla.update()
            self.tabla.set_visibility(False)
            self.controles.set_visibility(False)
            self._mostrar_aplicado()
            return

        self._mostrar_tabla(deteccion)
        if hay_nulos(deteccion) and self.sesion.preprocesado is not None:
            # Ya están tratados: el aviso de valores inexistentes sobra y
            # basta con la etiqueta de lo aplicado.
            self.aviso.set_text("")
            self.controles.set_visibility(True)
        elif hay_nulos(deteccion):
            total_train = sum(deteccion["train"].values())
            total_test = sum(deteccion["test"].values())
            self.aviso.set_text(
                "Se han detectado valores inexistentes. Entrenamiento: "
                + str(total_train)
                + " | Test: "
                + str(total_test)
                + ". Elige cómo tratarlos."
            )
            self.aviso.classes(replace="text-sm text-warning")
            self.controles.set_visibility(True)
        else:
            self.aviso.set_text(
                "No hay valores inexistentes en las columnas seleccionadas. "
                "Puedes continuar sin preprocesar."
            )
            self.aviso.classes(replace="text-sm text-positive")
            self.controles.set_visibility(False)
        self._mostrar_aplicado()

    def aplicar(self):
        """Aplica la estrategia elegida. Si falla, la sesión no cambia y se
        puede volver a intentar con otras opciones."""
        try:
            resumen = self.sesion.aplicar_preprocesado(
                self.estrategia.value, self.constante.value
            )
        except AvisoPreprocesado as aviso:
            notificar_aviso(aviso)
            return
        except ErrorPreprocesado as error:
            notificar_error(error)
            return
        notificar_exito(texto_resumen(resumen))
        self._crear_modelo()

    def _crear_modelo(self):
        """Crea el modelo con los datos recién preprocesados. Si falla, el
        preprocesado se conserva y se avisa del error."""
        try:
            self.sesion.crear_modelo()
        except ErrorModelo as error:
            notificar_error(error)
            return
        notificar_exito("Modelo creado correctamente.")
