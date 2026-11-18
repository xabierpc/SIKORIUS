"""Asistente con LLM: un chat en un panel lateral.

Se abre con el botón flotante de abajo a la derecha. Explica el dataset y
el modelo, y propone cambios al dataset que el usuario ve antes de
aplicarlos y que se pueden deshacer.

Hablar con la LLM y probar los cambios es cosa de
``aplicacion.asistente.Asistente``; aquí solo se pinta el chat.
"""

from nicegui import ui

from sikorius.aplicacion.asistente import MENSAJE_SIN_CLAVE
from sikorius.dominio.errores import ErrorAsistente
from sikorius.gui.avisos import notificar_error, notificar_exito
from sikorius.gui.componentes.confirmacion import confirmar
from sikorius.gui.paneles.base import Panel

# Peticiones de ejemplo que se ofrecen con el chat vacío
SUGERENCIAS = (
    "Explícame el dataset",
    "Explícame el modelo",
    "Quita las filas duplicadas",
    "¿Qué columnas tienen valores inexistentes?",
)

AVISO_PASOS = (
    "Al cambiar el dataset se borran la selección de columnas, la "
    "separación, el preprocesado y el modelo."
)


class PanelAsistente(Panel):
    """Botón flotante y panel lateral con el chat del asistente."""

    def __init__(self, sesion, asistente, etapa_actual=None):
        """
        Args:
            sesion: La ``Sesion`` de la aplicación.
            asistente: El ``Asistente`` (uno para toda la aplicación, como
                la sesión, para que la conversación siga al recargar).
            etapa_actual: Función sin argumentos que devuelve el nombre de
                la pestaña abierta, para dárselo de contexto a la LLM.
        """
        self.asistente = asistente
        self.etapa_actual = etapa_actual
        self.ocupado = False

        self.cajon = (
            ui.right_drawer(value=False)
            .props("width=420 bordered")
            .classes("column no-wrap gap-3 p-4")
        )
        with self.cajon:
            with ui.row().classes("w-full items-center no-wrap"):
                ui.icon("auto_awesome", color="secondary").classes("text-xl")
                ui.label("Asistente").classes("text-lg font-semibold")
                ui.space()
                self.boton_deshacer = (
                    ui.button(icon="undo", on_click=self.deshacer)
                    .props("flat round")
                    .tooltip("Deshacer el último cambio del asistente")
                )
                self.boton_borrar = (
                    ui.button(icon="delete_sweep", on_click=self.borrar)
                    .props("flat round")
                    .tooltip("Empezar una conversación nueva")
                )
                ui.button(icon="close", on_click=self.cajon.hide).props(
                    "flat round"
                )

            self.aviso_sin_clave = ui.label(MENSAJE_SIN_CLAVE).classes(
                "text-sm text-warning"
            )

            self.desplazable = ui.scroll_area().classes("w-full grow")
            with self.desplazable:
                self.chat = ui.column().classes("w-full gap-2")
                self.cargando = ui.row().classes("items-center gap-2")
                with self.cargando:
                    ui.spinner("dots", size="lg", color="secondary")
                    ui.label("Pensando...").classes("text-sm opacity-70")

            self.sugerencias = ui.row().classes("w-full gap-2")
            with self.sugerencias:
                for texto in SUGERENCIAS:
                    ui.chip(
                        texto,
                        on_click=lambda t=texto: self.enviar(t),
                    ).props("outline clickable color=secondary")

            self.tarjeta_propuesta = ui.card().classes(
                "w-full bg-transparent border border-primary"
            )

            with ui.row().classes("w-full items-center no-wrap gap-2"):
                self.entrada = (
                    ui.input(placeholder="Pídele algo al asistente...")
                    .props("outlined dense autogrow")
                    .classes("grow")
                    .on("keydown.enter", self.enviar)
                )
                self.boton_enviar = ui.button(
                    icon="send", on_click=self.enviar
                ).props("round")

        with ui.page_sticky(position="bottom-right", x_offset=24, y_offset=24):
            self.boton_abrir = (
                ui.button(icon="auto_awesome", on_click=self.cajon.toggle)
                .props("fab color=primary")
                .tooltip("Asistente")
            )
        super().__init__(sesion)

    # --- Pintar ---

    def actualizar(self):
        """Pinta el estado del asistente (se llama al cambiar la sesión)."""
        disponible = self.asistente.disponible
        self.aviso_sin_clave.set_visibility(not disponible)
        self.entrada.set_enabled(disponible and not self.ocupado)
        self.boton_enviar.set_enabled(disponible and not self.ocupado)
        self.boton_deshacer.set_enabled(
            self.asistente.puede_deshacer() and not self.ocupado
        )
        self.boton_borrar.set_enabled(
            bool(self.asistente.mensajes) and not self.ocupado
        )
        self.cargando.set_visibility(self.ocupado)
        self.sugerencias.set_visibility(
            disponible and not self.asistente.mensajes and not self.ocupado
        )
        self._pintar_chat()
        self._pintar_propuesta()

    def _pintar_chat(self):
        self.chat.clear()
        with self.chat:
            for mensaje in self.asistente.mensajes:
                if mensaje.rol == "usuario":
                    # Texto tal cual: lo ha escrito el usuario
                    ui.chat_message(mensaje.texto, name="Tú", sent=True).props(
                        "bg-color=primary text-color=white"
                    )
                else:
                    with ui.chat_message(name="Asistente").props(
                        "bg-color=grey-9 text-color=grey-2"
                    ):
                        ui.markdown(mensaje.texto)
        self.desplazable.scroll_to(percent=1.0)

    def _pintar_propuesta(self):
        propuesta = self.asistente.propuesta
        self.tarjeta_propuesta.clear()
        self.tarjeta_propuesta.set_visibility(propuesta is not None)
        if propuesta is None:
            return
        with self.tarjeta_propuesta:
            ui.label("Cambios propuestos").classes("font-medium")
            with ui.column().classes("gap-1"):
                for descripcion in propuesta.descripciones:
                    with ui.row().classes("no-wrap items-start gap-2"):
                        ui.icon("chevron_right", color="secondary")
                        ui.label(descripcion).classes("text-sm")
            ui.label(
                "Filas: "
                + str(propuesta.filas_antes)
                + " → "
                + str(propuesta.filas_despues)
            ).classes("text-sm opacity-70")
            if self.sesion.seleccion is not None:
                ui.label(AVISO_PASOS).classes("text-sm text-warning")
            with ui.row().classes("w-full justify-end"):
                ui.button("Descartar", on_click=self.descartar).props("flat")
                ui.button("Aplicar", icon="check", on_click=self.aplicar)

    # --- Acciones ---

    async def enviar(self, texto=None):
        """Manda lo escrito (o una sugerencia) y pinta la respuesta."""
        if not isinstance(texto, str):
            texto = self.entrada.value
        if self.ocupado or not (texto or "").strip():
            return
        self.entrada.set_value("")
        self.ocupado = True
        self.actualizar()
        etapa = None
        if self.etapa_actual is not None:
            etapa = self.etapa_actual()
        try:
            await self.asistente.enviar(texto, etapa=etapa)
        except ErrorAsistente as error:
            notificar_error(error)
        finally:
            self.ocupado = False
            self.actualizar()

    async def _seguir_si_hay_modelo_sin_guardar(self):
        """Pregunta antes de perder un modelo que no está guardado."""
        if not self.sesion.hay_cambios_sin_guardar():
            return True
        return await confirmar(
            "Modelo sin guardar",
            "El modelo actual tiene cambios sin guardar y se perderá al "
            "cambiar el dataset. ¿Quieres continuar?",
            "Continuar",
        )

    async def aplicar(self):
        """Aplica los cambios propuestos al dataset."""
        if not await self._seguir_si_hay_modelo_sin_guardar():
            return
        # El botón "Aplicar" está dentro de la tarjeta de la propuesta, que
        # se vacía al aplicar: los avisos se cuelgan del panel lateral
        with self.cajon:
            try:
                self.asistente.confirmar()
            except ErrorAsistente as error:
                notificar_error(error)
            else:
                notificar_exito("Cambios aplicados al dataset.")
        # La sesión ya avisa a todos los paneles; esto cubre el caso de
        # que la propuesta se descarte sin cambiar la sesión
        self.actualizar()

    def descartar(self):
        self.asistente.descartar()
        self.actualizar()

    async def deshacer(self):
        """Vuelve al dataset de antes del último cambio del asistente."""
        if not await self._seguir_si_hay_modelo_sin_guardar():
            return
        try:
            self.asistente.deshacer()
        except ErrorAsistente as error:
            notificar_error(error)
        else:
            notificar_exito("Cambio deshecho.")
        self.actualizar()

    def borrar(self):
        self.asistente.borrar_conversacion()
        self.actualizar()
