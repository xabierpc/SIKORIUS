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

from sikorius.aplicacion import EXTENSION, ruta_con_extension
from sikorius.gui.avisos import notificar_error
from sikorius.gui.componentes.confirmacion import confirmar
from sikorius.gui.componentes.explorador_archivos import NavegadorCarpetas

# Caracteres que Windows no admite en un nombre de archivo. Se rechazan en
# todos los sistemas para que los modelos se puedan copiar a cualquiera.
CARACTERES_PROHIBIDOS = '<>:"/\\|?*'

# Nombres que Windows reserva para dispositivos, con o sin extensión
# ("con.json" tampoco vale). Por lo mismo, se rechazan en todos los sistemas.
NOMBRES_RESERVADOS = frozenset(
    ["CON", "PRN", "AUX", "NUL"]
    + ["COM%d" % i for i in range(1, 10)]
    + ["LPT%d" % i for i in range(1, 10)]
)

# Longitud máxima de un nombre de archivo en casi todos los sistemas
# (en bytes, con la extensión incluida).
LONGITUD_MAXIMA = 255


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
    if any(ord(caracter) < 32 for caracter in nombre):
        return "El nombre del archivo no puede contener tabuladores ni saltos."
    if nombre.endswith("."):
        # Windows quita el punto final y guardaría otro archivo
        return "El nombre del archivo no puede terminar en punto."
    if nombre.split(".")[0].strip().upper() in NOMBRES_RESERVADOS:
        return (
            "'" + nombre + "' es un nombre reservado del sistema. "
            "Elige otro nombre."
        )
    nombre_final = ruta_con_extension(nombre).name
    if len(nombre_final.encode("utf-8")) > LONGITUD_MAXIMA:
        return "El nombre del archivo es demasiado largo."
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
            aviso: Texto opcional que se muestra en amarillo encima de la
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
        # Mientras se comprueba el nombre (y se pregunta si sobrescribir),
        # otro Enter o clic en "Guardar" no hace nada: así no se abren dos
        # preguntas a la vez.
        self._comprobando = False

        with (
            ui.dialog() as self.dialogo,
            ui.card().classes("w-[650px] max-w-full"),
        ):
            ui.label("Guardar modelo").classes("text-lg font-semibold")
            ui.label("Formato: JSON (" + EXTENSION + ")").classes(
                "text-sm text-secondary"
            )
            self.aviso = ui.label("").classes(
                "text-sm text-dark bg-warning p-2 rounded w-full"
            )
            if aviso:
                self.aviso.set_text(aviso)
            else:
                self.aviso.set_visibility(False)

            self.navegador = NavegadorCarpetas(
                es_modelo,
                lambda ruta: self.nombre.set_value(ruta.name),
                "No hay carpetas ni modelos",
                al_cambiar_carpeta=self._actualizar_destino,
                alto="h-64",
            )

            # Enter en el campo equivale a pulsar "Guardar"
            self.nombre = ui.input(
                label="Nombre del archivo",
                value=nombre_inicial,
                on_change=lambda _: self._actualizar_destino(),
            ).classes("w-full")
            self.nombre.on("keydown.enter", self.aceptar)
            # Ruta completa con la que se guardará, extensión incluida
            self.destino = ui.label("").classes(
                "text-sm text-secondary break-all"
            )

            with ui.row().classes("w-full justify-end"):
                ui.button("Cancelar", on_click=self.cancelar).props("flat")
                self.boton_guardar = ui.button(
                    "Guardar", icon="save", on_click=self.aceptar
                )

        self.mostrar(carpeta_valida(carpeta_inicial))

    # --- Navegación (la hace NavegadorCarpetas) ---

    @property
    def carpeta(self):
        """Carpeta que se está mostrando, como ``Path``."""
        return self.navegador.carpeta

    @property
    def etiqueta_carpeta(self):
        return self.navegador.etiqueta_carpeta

    @property
    def lista(self):
        return self.navegador.lista

    def mostrar(self, carpeta):
        """Lista las subcarpetas y los modelos (.json) de carpeta.

        Si no se puede abrir, avisa y se queda en la carpeta anterior.
        """
        self.navegador.mostrar(carpeta)

    def texto_destino(self):
        """Dónde se guardará con el nombre escrito, o por qué no se puede."""
        motivo = motivo_nombre_no_valido(self.nombre.value)
        if motivo is not None:
            return motivo
        return "Se guardará como: " + str(
            ruta_destino(self.carpeta, self.nombre.value)
        )

    def _actualizar_destino(self):
        # Hasta que se muestra la primera carpeta no hay nada que enseñar
        if self.carpeta is not None:
            self.destino.set_text(self.texto_destino())

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
        if self._comprobando:
            return
        self._comprobando = True
        try:
            ruta = await self._comprobar_ruta()
        finally:
            self._comprobando = False
        if ruta is None:
            return
        self.resultado = ruta
        self.dialogo.submit(ruta)

    async def _comprobar_ruta(self):
        """La ruta elegida si se puede usar, o None (tras avisar)."""
        motivo = motivo_nombre_no_valido(self.nombre.value)
        if motivo is not None:
            notificar_error(motivo)
            return None
        ruta = ruta_destino(self.carpeta, self.nombre.value)
        if ruta.is_dir():
            notificar_error(
                "Ya hay una carpeta llamada '" + ruta.name + "'. "
                "Elige otro nombre."
            )
            return None
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
                return None
        return ruta

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
