"""Diálogo para elegir dónde se guarda el modelo (historia #21).

Funciona como el explorador de la carga de datasets: el servidor de NiceGUI
corre en el propio equipo, así que la ruta elegida es una ruta real del
disco. El usuario navega por las carpetas, escribe el nombre del archivo y
pulsa "Guardar". La extensión ``.json`` se añade sola si no la escribe y,
si el archivo ya existe, se le pregunta antes de sobrescribirlo.

El diálogo solo elige la ruta: guardar el modelo es cosa de la sesión.
"""

from pathlib import Path

from nicegui import ui

from sikorius.gui.avisos import notificar_error
from sikorius.gui.componentes.confirmacion import confirmar
from sikorius.gui.componentes.explorador_archivos import (
    listar_carpeta,
    nombre_unidad,
    unidades_disponibles,
)
from sikorius.nucleo.persistencia import EXTENSION, ruta_con_extension

# Caracteres que Windows no admite en un nombre de archivo. Se rechazan en
# todos los sistemas para que los modelos se puedan copiar a cualquiera.
CARACTERES_PROHIBIDOS = '<>:"/\\|?*'


def es_modelo(ruta):
    """Archivos que se muestran en el diálogo: los de modelo (.json)."""
    return Path(ruta).suffix.lower() == EXTENSION


def motivo_nombre_no_valido(nombre):
    """Explica por qué un nombre de archivo no vale.

    Args:
        nombre: Lo que el usuario ha escrito en el campo del nombre.

    Returns:
        El texto del problema, o None si el nombre es válido.
    """
    if nombre is None:
        nombre = ""
    nombre = nombre.strip()
    if nombre == "":
        return "Escribe un nombre para el archivo."
    if nombre in (".", ".."):
        return "'" + nombre + "' no es un nombre de archivo válido."
    for caracter in CARACTERES_PROHIBIDOS:
        if caracter in nombre:
            return (
                "El nombre del archivo no puede contener ninguno de "
                "estos caracteres: " + " ".join(CARACTERES_PROHIBIDOS)
            )
    return None


def ruta_destino(carpeta, nombre):
    """Ruta completa del archivo, con la extensión añadida si falta.

    Se quitan los espacios del principio y del final del nombre. No
    comprueba el nombre: antes hay que llamar a
    ``motivo_nombre_no_valido``.

    Args:
        carpeta: Carpeta elegida en el diálogo.
        nombre: Nombre del archivo escrito por el usuario.

    Returns:
        La ruta como ``Path``, terminada en ``.json``.
    """
    return ruta_con_extension(Path(carpeta) / nombre.strip())


def carpeta_valida(carpeta):
    """La carpeta resuelta si existe; si no, la carpeta personal."""
    if carpeta is None:
        return Path.home()
    carpeta = Path(carpeta).resolve()
    if carpeta.is_dir():
        return carpeta
    return Path.home()


class DialogoGuardado:
    """Explorador de carpetas con un campo para el nombre del archivo.

    Attributes:
        carpeta: Carpeta que se está mostrando, como ``Path``.
        nombre: Campo de texto con el nombre del archivo.
        resultado: Ruta elegida (``Path``) o None mientras no se elija.
    """

    def __init__(
        self, carpeta_inicial, nombre_inicial, aviso=None, preguntar=None
    ):
        """Crea el diálogo (sin abrirlo) y muestra la carpeta inicial.

        Args:
            carpeta_inicial: Carpeta que se muestra al abrir. Si no
                existe, se empieza en la carpeta personal.
            nombre_inicial: Nombre que aparece ya escrito.
            aviso: Texto opcional que se muestra en naranja encima de la
                lista (por ejemplo, que el modelo no tiene descripción).
                No impide guardar.
            preguntar: Función asíncrona ``(titulo, mensaje,
                texto_aceptar) -> bool`` que pide confirmación antes de
                sobrescribir. Por defecto, ``confirmar``.
        """
        if preguntar is None:
            preguntar = confirmar
        self._preguntar = preguntar
        self.resultado = None
        self.carpeta = None

        with (
            ui.dialog() as self.dialogo,
            ui.card().classes("w-[650px] max-w-full"),
        ):
            ui.label("Guardar modelo").classes("text-lg font-semibold")
            ui.label("Formato: JSON (" + EXTENSION + ")").classes(
                "text-sm text-gray-500"
            )
            self.aviso = ui.label("").classes(
                "text-sm text-orange-800 bg-orange-50 p-2 rounded w-full"
            )
            if aviso:
                self.aviso.set_text(aviso)
            else:
                self.aviso.set_visibility(False)

            with ui.row().classes("w-full items-center no-wrap"):
                ui.button(
                    icon="home", on_click=lambda: self.mostrar(Path.home())
                ).props("flat round dense").tooltip("Carpeta personal")
                for unidad in unidades_disponibles():
                    ui.button(
                        nombre_unidad(unidad), on_click=self._ir_a(unidad)
                    ).props("flat dense no-caps").tooltip(
                        "Unidad " + nombre_unidad(unidad)
                    )
                self.etiqueta_carpeta = ui.label().classes("text-sm break-all")
            with ui.scroll_area().classes("w-full h-64 border rounded"):
                self.lista = (
                    ui.list().classes("w-full").props("dense separator")
                )

            # Enter en el campo equivale a pulsar "Guardar"
            self.nombre = ui.input(
                label="Nombre del archivo", value=nombre_inicial
            ).classes("w-full")
            self.nombre.on("keydown.enter", self.aceptar)

            with ui.row().classes("w-full justify-end"):
                ui.button("Cancelar", on_click=self.cancelar).props("flat")
                self.boton_guardar = ui.button(
                    "Guardar", icon="save", on_click=self.aceptar
                )

        self.mostrar(carpeta_valida(carpeta_inicial))

    # --- Navegación ---

    def _ir_a(self, carpeta):
        # Cada botón necesita su propia función: una lambda escrita en el
        # bucle de las unidades se quedaría con la última para todos
        return lambda: self.mostrar(carpeta)

    def _al_pulsar(self, ruta):
        return lambda: self._abrir(ruta)

    def _abrir(self, ruta):
        """Una carpeta se abre; un archivo pone su nombre en el campo."""
        if ruta.is_dir():
            self.mostrar(ruta)
        else:
            self.nombre.set_value(ruta.name)

    def _anadir_entrada(self, ruta, icono, texto):
        with ui.item(on_click=self._al_pulsar(ruta)):
            with ui.item_section().props("avatar"):
                ui.icon(icono)
            with ui.item_section():
                ui.item_label(texto)

    def mostrar(self, carpeta):
        """Lista las subcarpetas y los modelos (.json) de carpeta.

        Si no se puede abrir, avisa y se queda en la carpeta anterior.
        """
        carpeta = Path(carpeta)
        try:
            entradas = listar_carpeta(carpeta, es_modelo)
        except PermissionError:
            notificar_error("Sin permiso para abrir " + str(carpeta))
            return
        except OSError as error:
            notificar_error(
                "No se puede abrir " + str(carpeta) + ": " + str(error)
            )
            return

        self.carpeta = carpeta
        self.etiqueta_carpeta.set_text(str(carpeta))
        self.lista.clear()
        with self.lista:
            if carpeta.parent != carpeta:
                self._anadir_entrada(carpeta.parent, "arrow_upward", "..")
            for ruta in entradas:
                if ruta.is_dir():
                    self._anadir_entrada(ruta, "folder", ruta.name)
                else:
                    self._anadir_entrada(ruta, "description", ruta.name)
            if len(entradas) == 0:
                with ui.item():
                    ui.item_label("No hay carpetas ni modelos").classes(
                        "text-gray-500"
                    )

    # --- Botones ---

    def cancelar(self):
        """Cierra sin elegir nada."""
        self.resultado = None
        self.dialogo.submit(None)

    async def aceptar(self):
        """Comprueba el nombre y, si todo va bien, cierra con la ruta.

        Si el nombre no vale, o el archivo existe y el usuario no quiere
        sobrescribirlo, el diálogo sigue abierto para elegir otro.
        """
        motivo = motivo_nombre_no_valido(self.nombre.value)
        if motivo is not None:
            notificar_error(motivo)
            return
        ruta = ruta_destino(self.carpeta, self.nombre.value)
        if ruta.is_dir():
            notificar_error(
                "Ya hay una carpeta llamada '" + ruta.name + "'. "
                "Elige otro nombre."
            )
            return
        if ruta.exists():
            sobrescribir = await self._preguntar(
                "El archivo ya existe",
                "Ya hay un archivo llamado '"
                + ruta.name
                + "' en "
                + str(ruta.parent)
                + ". ¿Quieres sustituirlo?",
                "Sobrescribir",
            )
            if not sobrescribir:
                return
        self.resultado = ruta
        self.dialogo.submit(ruta)

    async def elegir(self):
        """Abre el diálogo y espera a que el usuario termine.

        Returns:
            La ruta elegida (``Path``) o None si cierra el diálogo sin
            elegir (botón Cancelar, Escape o clic fuera).
        """
        respuesta = await self.dialogo
        self.dialogo.delete()
        if respuesta is None:
            return None
        return self.resultado


async def elegir_ruta_guardado(carpeta_inicial, nombre_inicial, aviso=None):
    """Abre el diálogo de guardado y devuelve la ruta elegida o None."""
    dialogo = DialogoGuardado(carpeta_inicial, nombre_inicial, aviso)
    return await dialogo.elegir()
