"""Explorador de archivos hecho con NiceGUI.

Solo muestra carpetas y archivos con las extensiones que admite el módulo de
importación. Como el servidor de NiceGUI corre en el propio equipo, la ruta
que devuelve es la ruta real del archivo en el disco. En Windows muestra
además un botón por cada unidad de disco (C:, D:...) para poder cambiar de
una a otra.
"""

import os
import string
from pathlib import Path

from nicegui import ui

from sikorius.aplicacion import EXTENSIONES_ADMITIDAS, es_admitido
from sikorius.gui.avisos import notificar_error


def _es_windows():
    """Indica si la aplicación se está ejecutando en Windows."""
    return os.name == "nt"


def carpeta_valida(carpeta):
    """La carpeta resuelta si existe; si no, la carpeta personal.

    La usan el explorador de datasets y el diálogo de guardado: si la
    carpeta de la última vez ya no existe (o no se indicó ninguna), se
    abre la carpeta personal en vez de fallar.
    """
    if carpeta is None:
        return Path.home()
    carpeta = Path(carpeta).resolve()
    if carpeta.is_dir():
        return carpeta
    return Path.home()


def unidades_disponibles():
    """Devuelve las unidades de disco de Windows que existen (C:\\, D:\\...).

    En Linux y macOS devuelve una lista vacía: todo cuelga de "/" y se llega
    a cualquier carpeta subiendo con "..".
    """
    if not _es_windows():
        return []
    unidades = []
    for letra in string.ascii_uppercase:
        raiz = Path(letra + ":\\")
        if raiz.exists():
            unidades.append(raiz)
    return unidades


def nombre_unidad(unidad):
    """Texto del botón de una unidad: "C:\\" -> "C:"."""
    return str(unidad)[:2]


def _clave_orden(ruta):
    # Primero las carpetas y después los archivos, por orden alfabético
    return (not ruta.is_dir(), ruta.name.lower())


def listar_carpeta(carpeta, admitido=es_admitido):
    """Devuelve las subcarpetas y los archivos compatibles de una carpeta.

    Se omiten los archivos y carpetas ocultos (los que empiezan por punto).

    Args:
        carpeta: Carpeta que se lista.
        admitido: Función que recibe la ruta de un archivo y dice si se
            muestra. Por defecto, los datasets que se pueden importar.

    Raises:
        PermissionError: Si no hay permiso para leer la carpeta.
    """
    entradas = []
    for ruta in Path(carpeta).iterdir():
        if ruta.name.startswith("."):
            continue
        try:
            if ruta.is_dir() or ruta.is_file() and admitido(ruta):
                entradas.append(ruta)
        except OSError:
            pass  # enlaces rotos o archivos inaccesibles: no se muestran
    entradas.sort(key=_clave_orden)
    return entradas


class NavegadorCarpetas:
    """Lista de carpetas y archivos para moverse por el disco.

    Lo usan el explorador de datasets y el diálogo de guardado del modelo.
    Arriba lleva el botón de la carpeta personal, un botón por unidad de
    disco (en Windows) y la carpeta actual; debajo, la lista con ".." para
    subir. Una carpeta se abre al pulsarla; un archivo se le pasa a
    ``al_elegir_archivo``.

    Attributes:
        carpeta: Carpeta que se está mostrando (``Path``), o None antes de
            mostrar la primera.
        etiqueta_carpeta: Etiqueta con la ruta de la carpeta actual.
        lista: Lista de NiceGUI con las entradas.
    """

    def __init__(
        self,
        admitido,
        al_elegir_archivo,
        texto_vacio,
        al_cambiar_carpeta=None,
        alto="h-80",
    ):
        """Crea los controles en el contenedor actual, sin mostrar nada.

        Args:
            admitido: Función que recibe la ruta de un archivo y dice si se
                muestra.
            al_elegir_archivo: Función que recibe el ``Path`` del archivo
                pulsado.
            texto_vacio: Texto que se ve si no hay nada que mostrar.
            al_cambiar_carpeta: Función opcional, sin argumentos, que se
                llama cada vez que se muestra otra carpeta.
            alto: Clase de Tailwind con la altura de la lista.
        """
        self._admitido = admitido
        self._al_elegir_archivo = al_elegir_archivo
        self._texto_vacio = texto_vacio
        self._al_cambiar_carpeta = al_cambiar_carpeta
        self.carpeta = None

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
        with ui.scroll_area().classes("w-full " + alto + " border rounded"):
            self.lista = ui.list().classes("w-full").props("dense separator")

    def _ir_a(self, carpeta):
        # Cada botón necesita su propia función: una lambda escrita en el
        # bucle de las unidades se quedaría con la última para todos
        return lambda: self.mostrar(carpeta)

    def _al_pulsar(self, ruta):
        return lambda: self._abrir(ruta)

    def _abrir(self, ruta):
        if ruta.is_dir():
            self.mostrar(ruta)
        else:
            self._al_elegir_archivo(ruta)

    def _anadir_entrada(self, ruta, icono, texto):
        with ui.item(on_click=self._al_pulsar(ruta)):
            with ui.item_section().props("avatar"):
                ui.icon(icono)
            with ui.item_section():
                ui.item_label(texto)

    def mostrar(self, carpeta):
        """Lista la carpeta. Si no se puede abrir, avisa y se queda en la
        anterior.

        Returns:
            True si se ha mostrado la carpeta.
        """
        carpeta = Path(carpeta)
        try:
            entradas = listar_carpeta(carpeta, self._admitido)
        except PermissionError:
            notificar_error("Sin permiso para abrir " + str(carpeta))
            return False
        except OSError as error:
            notificar_error(
                "No se puede abrir " + str(carpeta) + ": " + str(error)
            )
            return False

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
                    ui.item_label(self._texto_vacio).classes("text-secondary")
        if self._al_cambiar_carpeta is not None:
            self._al_cambiar_carpeta()
        return True


async def seleccionar_archivo(
    carpeta_inicial,
    titulo="Selecciona un dataset",
    tipos=None,
    admitido=es_admitido,
):
    """Abre el explorador y espera a que el usuario elija un archivo.

    Por defecto muestra los datasets que se pueden importar. Cambiando
    ``titulo``, ``tipos`` y ``admitido`` sirve para elegir otros archivos
    (por ejemplo, un modelo guardado).

    Args:
        carpeta_inicial: Carpeta que se muestra al abrir el explorador.
        titulo: Texto de la cabecera del explorador.
        tipos: Extensiones que se muestran, para el texto "Tipos
            admitidos". Por defecto, las del módulo de importación.
        admitido: Función que recibe la ruta de un archivo y dice si se
            muestra. Por defecto, los datasets que se pueden importar.

    Returns:
        Ruta absoluta (str) del archivo elegido, o None si el usuario cierra
        el explorador sin elegir nada (botón Cancelar, Escape o clic fuera).
    """
    if tipos is None:
        tipos = EXTENSIONES_ADMITIDAS
    tipos = ", ".join(tipos)

    with ui.dialog() as dialogo, ui.card().classes("w-[650px] max-w-full"):
        ui.label(titulo).classes("text-lg font-semibold")
        ui.label("Tipos admitidos: " + tipos).classes("text-sm text-secondary")
        navegador = NavegadorCarpetas(
            admitido,
            lambda ruta: dialogo.submit(str(ruta.resolve())),
            "No hay carpetas ni archivos compatibles",
        )
        with ui.row().classes("w-full justify-end"):
            ui.button("Cancelar", on_click=lambda: dialogo.submit(None)).props(
                "flat"
            )

    navegador.mostrar(carpeta_valida(carpeta_inicial))

    ruta = await dialogo
    dialogo.delete()
    return ruta
