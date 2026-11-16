"""Panel para hacer predicciones con el modelo actual (historia #22).

Aparece en cuanto hay un modelo, tanto si se ha creado en la aplicación
como si se ha cargado de un archivo. Tiene un campo por cada columna de
entrada del modelo, el botón "Realizar predicción" y el resultado.

Interpretar los valores y calcular la predicción es cosa de
``sikorius.dominio.prediccion`` (a través de ``Sesion.predecir``); aquí
solo se leen los campos y se muestra el resultado.
"""

from nicegui import ui

from sikorius.dominio.errores import ErrorPrediccion
from sikorius.dominio.prediccion import texto_prediccion
from sikorius.gui.avisos import notificar_error
from sikorius.gui.paneles.base import Panel


class PanelPrediccion(Panel):
    """Campos de entrada del modelo, botón de predecir y resultado.

    Mientras no hay modelo el panel no se ve.
    """

    def __init__(self, sesion):
        self.tarjeta = ui.card().classes("w-full")
        with self.tarjeta:
            # Sin tilde: la fuente de los títulos (Forque) no la tiene
            ui.label("Prediccion").classes("text-lg font-semibold")
            ui.label(
                "Escribe un valor para cada variable de entrada. Puedes usar "
                "punto o coma para los decimales."
            ).classes("text-sm opacity-70")
            self.contenedor_campos = ui.row().classes("w-full gap-4")
            with ui.row().classes("items-center gap-4"):
                self.boton = ui.button(
                    "Realizar predicción",
                    icon="calculate",
                    on_click=self.predecir,
                )
                # Fuente normal, no la de los títulos: el nombre de la
                # columna es del usuario y puede tener tildes o la ñ
                self.resultado = ui.label("").classes(
                    "text-xl font-medium text-secondary"
                )
        # {columna: ui.input}, en el orden de las columnas del modelo
        self.campos = {}
        # Modelo para el que están hechos los campos. La sesión avisa
        # también por cambios que no son del modelo (por ejemplo, al
        # guardarlo), y en esos casos no hay que borrar lo escrito.
        self._modelo_campos = None
        super().__init__(sesion)

    def actualizar(self):
        """Muestra el panel si hay modelo y rehace los campos si cambia."""
        mod = self.sesion.modelo
        self.tarjeta.set_visibility(mod is not None)
        if mod is None:
            self._modelo_campos = None
            self._crear_campos(())
            self._borrar_resultado()
        elif mod is not self._modelo_campos:
            self._modelo_campos = mod
            self._crear_campos(mod.features)
            self._borrar_resultado()

    def _crear_campos(self, features):
        """Un campo de texto por columna de entrada, con su nombre.

        Son de texto, y no numéricos, para aceptar también la coma decimal
        ("3,5"). Con Intro se hace la predicción.
        """
        self.contenedor_campos.clear()
        self.campos = {}
        with self.contenedor_campos:
            for columna in features:
                self.campos[columna] = (
                    ui.input(label=str(columna))
                    .on("keydown.enter", self.predecir)
                    .classes("w-48")
                )

    def _borrar_resultado(self):
        self.resultado.set_text("")
        self.resultado.set_visibility(False)

    def valores(self):
        """Lo escrito en cada campo: ``{columna: texto}``."""
        return {columna: campo.value for columna, campo in self.campos.items()}

    def predecir(self):
        """Calcula la predicción con lo escrito y la muestra.

        Si falta algún valor o alguno no es un número, avisa de cuál y
        borra el resultado anterior. Los campos se quedan como estaban
        para que se puedan corregir.
        """
        mod = self.sesion.modelo
        try:
            valor = self.sesion.predecir(self.valores())
        except ErrorPrediccion as error:
            self._borrar_resultado()
            notificar_error(error)
            return
        self.resultado.set_text(texto_prediccion(mod, valor))
        self.resultado.set_visibility(True)
