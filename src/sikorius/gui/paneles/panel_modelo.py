"""Panel para crear y evaluar el modelo de regresión lineal."""

import math
from pathlib import Path

from nicegui import ui

from sikorius.gui.avisos import notificar_error, notificar_exito
from sikorius.gui.componentes import dialogo_guardado
from sikorius.gui.paneles.base import Panel
from sikorius.nucleo import modelo
from sikorius.nucleo.errores import ErrorModelo, ErrorPersistencia
from sikorius.nucleo.persistencia import EXTENSION
from sikorius.nucleo.texto import formatear_numero

DECIMALES_METRICAS = 4

AVISO_SIN_DESCRIPCION = (
    "El modelo no tiene descripción. Puedes guardarlo igualmente, pero "
    "después será más difícil saber para qué se creó."
)


def texto_metrica(nombre, valor):
    """Ejemplo: "R²: 0.9816". Si no se puede calcular, "R²: no calculable"."""
    if math.isnan(valor):
        return f"{nombre}: no calculable"
    return f"{nombre}: {formatear_numero(valor, DECIMALES_METRICAS)}"


def destino_inicial(sesion):
    """Carpeta y nombre que propone el diálogo de guardado.

    - Si el modelo ya se guardó, el mismo archivo (para volver a
      guardarlo hay que confirmar que se sobrescribe).
    - Si no, la carpeta del dataset y "modelo_<nombre del dataset>.json".
    - Sin dataset, la carpeta personal y "modelo.json".

    Returns:
        Tupla (carpeta como ``Path``, nombre del archivo).
    """
    if sesion.ruta_modelo is not None:
        ruta = Path(sesion.ruta_modelo)
        return ruta.parent, ruta.name
    if sesion.dataset is not None:
        ruta = Path(sesion.dataset.ruta)
        return ruta.parent, "modelo_" + ruta.stem + EXTENSION
    return Path.home(), "modelo" + EXTENSION


def aviso_antes_de_guardar(mod):
    """Aviso del diálogo de guardado si falta la descripción, o None."""
    descripcion = mod.descripcion
    if descripcion is None or descripcion.strip() == "":
        return AVISO_SIN_DESCRIPCION
    return None


class PanelModelo(Panel):
    """Botón de creación, fórmula, métricas y gráfico de ajuste."""

    def __init__(self, sesion):
        with ui.card().classes("w-full"):
            ui.label("Modelo").classes("text-lg font-semibold")
            self.aviso = ui.label("").classes("text-sm text-gray-500")
            with ui.row().classes("items-center gap-2"):
                self.boton = ui.button("Crear modelo", on_click=self.crear)
                self.boton_guardar = ui.button(
                    "Guardar modelo", icon="save", on_click=self.guardar
                ).props("outline")

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

        # Modelo que se ve ahora. La sesión avisa también por cambios que
        # no son del modelo (por ejemplo, al guardarlo), y redibujar el
        # gráfico en cada aviso sería lento y no cambiaría nada.
        self._mostrado = None
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
            if self.sesion.modelo is not self._mostrado:
                self._mostrar_resultados()
                self._mostrado = self.sesion.modelo
            self.resultados.set_visibility(True)
            self.boton_guardar.enable()
        else:
            self._mostrado = None
            self.resultados.set_visibility(False)
            self.boton_guardar.disable()

    def _mostrar_resultados(self):
        """Escribe la fórmula y las métricas y dibuja el gráfico."""
        mod = self.sesion.modelo
        entrenamiento, test = self.sesion.conjuntos_actuales()

        self.formula.set_text(modelo.formula_texto(mod))

        metricas = self.sesion.metricas_modelo()
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

    async def guardar(self):
        """Pide la ruta con el diálogo y guarda el modelo en ella.

        Si el usuario cierra el diálogo no pasa nada. Si el guardado falla
        se muestra el error y se puede volver a intentar.
        """
        mod = self.sesion.modelo
        if mod is None:
            notificar_error("Crea primero el modelo para poder guardarlo.")
            return
        carpeta, nombre = destino_inicial(self.sesion)
        ruta = await dialogo_guardado.elegir_ruta_guardado(
            carpeta, nombre, aviso_antes_de_guardar(mod)
        )
        if ruta is None:
            return  # el usuario cerró el diálogo: no se guarda nada
        try:
            guardada = self.sesion.guardar_modelo(ruta)
        except ErrorPersistencia as error:
            notificar_error(error)
            return
        notificar_exito("Modelo guardado en " + str(guardada))
