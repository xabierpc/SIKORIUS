"""Panel para crear y evaluar el modelo de regresión lineal."""

import math

from nicegui import ui

from sikorius.gui.avisos import notificar_error, notificar_exito
from sikorius.gui.paneles.base import Panel
from sikorius.nucleo import modelo
from sikorius.nucleo.errores import ErrorModelo
from sikorius.nucleo.texto import formatear_numero

DECIMALES_METRICAS = 4


def texto_metrica(nombre, valor):
    """Ejemplo: "R²: 0.9816". Si no se puede calcular, "R²: no calculable"."""
    if math.isnan(valor):
        return f"{nombre}: no calculable"
    return f"{nombre}: {formatear_numero(valor, DECIMALES_METRICAS)}"


class PanelModelo(Panel):
    """Botón de creación, fórmula, métricas y gráfico de ajuste."""

    def __init__(self, sesion):
        with ui.card().classes("w-full"):
            ui.label("Modelo").classes("text-lg font-semibold")
            self.aviso = ui.label("").classes("text-sm text-gray-500")
            self.boton = ui.button("Crear modelo", on_click=self.crear)

            self.resultados = ui.column().classes("w-full mt-4")
            with self.resultados:
                self.formula = ui.label("").classes(
                    "font-mono text-sm bg-gray-100 p-2 rounded w-full "
                    "break-words"
                )

                # Una columna por conjunto: {"entrenamiento": (R², ECM), ...}
                self.metricas = {}
                with ui.row().classes("w-full gap-8 mt-2"):
                    for clave, titulo in (
                        ("entrenamiento", "Entrenamiento"),
                        ("test", "Test"),
                    ):
                        with ui.column().classes("gap-1"):
                            ui.label(titulo).classes(
                                "font-semibold text-gray-700"
                            )
                            self.metricas[clave] = (ui.label(""), ui.label(""))

                self.descripcion = ui.textarea(
                    label="Descripción (opcional)",
                    placeholder="En qué consiste el modelo y para qué se creó",
                    on_change=self._cambiar_descripcion,
                ).classes("w-full mt-2")
                self.descripcion.props("autogrow")

                # El gráfico es un SVG que se estira hasta el ancho que le
                # den: "max-w-lg" evita que se agrande con el panel.
                self.grafico = ui.pyplot(figsize=(5, 3.6)).classes(
                    "w-full max-w-lg self-center mt-4"
                )

        super().__init__(sesion)

    def actualizar(self):
        """Habilita/deshabilita la creación y muestra el modelo."""
        motivo = self.sesion.motivo_no_crear_modelo()
        if motivo is not None:
            self.aviso.set_text(motivo)
            self.aviso.set_visibility(True)
            self.boton.disable()
        else:
            self.aviso.set_visibility(False)
            self.boton.enable()

        if self.sesion.modelo is not None:
            self._mostrar_resultados()
            self.resultados.set_visibility(True)
        else:
            self.resultados.set_visibility(False)

    def _mostrar_resultados(self):
        """Escribe la fórmula y las métricas y dibuja el gráfico."""
        mod = self.sesion.modelo
        entrenamiento, test = self.sesion.conjuntos_actuales()

        self.formula.set_text(modelo.formula_texto(mod))

        metricas = modelo.metricas_modelo(mod, entrenamiento, test)
        for clave, (r2, ecm) in self.metricas.items():
            r2.set_text(texto_metrica("R²", metricas[clave]["r2"]))
            ecm.set_text(texto_metrica("ECM", metricas[clave]["ecm"]))

        # La descripción es del modelo, no del campo: al cambiar de modelo
        # (o al recargar la página) el campo muestra la del modelo actual.
        if self.descripcion.value != mod.descripcion:
            self.descripcion.set_value(mod.descripcion)

        datos = modelo.datos_ajuste(mod, entrenamiento, test)
        with self.grafico:
            modelo.dibujar_ajuste(self.grafico.fig, datos)

    def _cambiar_descripcion(self, evento):
        """Cada cambio del campo se guarda en la descripción del modelo."""
        mod = self.sesion.modelo
        if mod is None or evento.value == mod.descripcion:
            return
        self.sesion.guardar_descripcion(evento.value)

    def crear(self):
        """Crea el modelo. Si falla, la sesión no cambia y se avisa."""
        try:
            self.sesion.crear_modelo()
        except ErrorModelo as error:
            notificar_error(error)
            return
        notificar_exito("Modelo creado correctamente.")
