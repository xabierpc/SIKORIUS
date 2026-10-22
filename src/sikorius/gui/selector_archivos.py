"""Explorador de archivos hecho con NiceGUI.

Solo muestra carpetas y archivos con las extensiones que admite el módulo de
importación. Como el servidor de NiceGUI corre en el propio equipo, la ruta
que devuelve es la ruta real del archivo en el disco.
"""

from pathlib import Path

from nicegui import ui



def es_archivo_permitido(ruta):
    """Indica si la extensión del archivo es de un tipo compatible."""
    return Path(ruta).suffix.lower() in (".csv", ".xlsx", ".xls", ".sqlite", ".db")


def _clave_orden(ruta):
    # Primero las carpetas y después los archivos, por orden alfabético
    return (not ruta.is_dir(), ruta.name.lower())


def listar_carpeta(carpeta):
    """Devuelve las subcarpetas y los archivos compatibles de una carpeta.

    Se omiten los archivos y carpetas ocultos (los que empiezan por punto).

    Raises:
        PermissionError: Si no hay permiso para leer la carpeta.
    """
    entradas = []
    for ruta in Path(carpeta).iterdir():
        if ruta.name.startswith("."):
            continue
        try:
            if ruta.is_dir():
                entradas.append(ruta)
            elif ruta.is_file() and es_archivo_permitido(ruta):
                entradas.append(ruta)
        except OSError:
            pass  # enlaces rotos o archivos inaccesibles: no se muestran
    entradas.sort(key=_clave_orden)
    return entradas


async def seleccionar_archivo(carpeta_inicial):
    """Abre el explorador y espera a que el usuario elija un archivo.

    Args:
        carpeta_inicial: Carpeta que se muestra al abrir el explorador.

    Returns:
        Ruta absoluta (str) del archivo elegido, o None si el usuario cierra
        el explorador sin elegir nada (botón Cancelar, Escape o clic fuera).
    """
    tipos = ", ".join((".csv", ".xlsx", ".xls", ".sqlite", ".db"))

    with ui.dialog() as dialogo, ui.card().classes("w-[650px] max-w-full"):
        ui.label("Selecciona un dataset").classes("text-lg font-semibold")
        ui.label("Tipos admitidos: " + tipos).classes("text-sm text-gray-500")
        with ui.row().classes("w-full items-center no-wrap"):
            ui.button(icon="home", on_click=lambda: mostrar(Path.home())) \
                .props("flat round dense").tooltip("Carpeta personal")
            etiqueta_carpeta = ui.label().classes("text-sm break-all")
        with ui.scroll_area().classes("w-full h-80 border rounded"):
            lista = ui.list().classes("w-full").props("dense separator")
        with ui.row().classes("w-full justify-end"):
            ui.button("Cancelar", on_click=lambda: dialogo.submit(None)).props("flat")

    def accion(ruta):
        return lambda: abrir(ruta)

    def abrir(ruta):
        if ruta.is_dir():
            mostrar(ruta)
        else:
            dialogo.submit(str(ruta.resolve()))

    def anadir_entrada(ruta, icono, texto):
        with ui.item(on_click=accion(ruta)):
            with ui.item_section().props("avatar"):
                ui.icon(icono)
            with ui.item_section():
                ui.item_label(texto)

    def mostrar(carpeta):
        try:
            entradas = listar_carpeta(carpeta)
        except PermissionError:
            ui.notify("Sin permiso para abrir " + str(carpeta), type="negative")
            return
        except OSError as error:
            ui.notify("No se puede abrir " + str(carpeta) + ": " + str(error),
                      type="negative")
            return

        etiqueta_carpeta.set_text(str(carpeta))
        lista.clear()
        with lista:
            if carpeta.parent != carpeta:
                anadir_entrada(carpeta.parent, "arrow_upward", "..")
            for ruta in entradas:
                if ruta.is_dir():
                    anadir_entrada(ruta, "folder", ruta.name)
                else:
                    anadir_entrada(ruta, "description", ruta.name)
            if len(entradas) == 0:
                with ui.item():
                    ui.item_label("No hay carpetas ni archivos compatibles") \
                        .classes("text-gray-500")

    inicio = Path(carpeta_inicial).resolve()
    if not inicio.is_dir():
        inicio = Path.home()
    mostrar(inicio)

    ruta = await dialogo
    dialogo.delete()
    return ruta
