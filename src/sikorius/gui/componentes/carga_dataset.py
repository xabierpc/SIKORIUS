"""Carga de un dataset desde la interfaz.

Junta lo que pasa al pulsar "Subir dataset" (en el inicio) o "Cargar otro"
(en la pestaña "Datos"): preguntar si hay un modelo cargado con cambios sin
guardar, elegir el archivo y avisar de cómo ha ido. Leer el archivo y
cambiar el estado es cosa de la sesión: aquí no se abre ningún archivo.
"""

from pathlib import Path

from sikorius.dominio.errores import ErrorImportacion
from sikorius.gui.avisos import notificar_error, notificar_exito
from sikorius.gui.componentes import carga_modelo
from sikorius.gui.componentes.explorador_archivos import seleccionar_archivo


def carpeta_inicial(sesion):
    """Carpeta del último archivo cargado o, si no hay, la carpeta personal."""
    if sesion.dataset is not None:
        return Path(sesion.dataset.ruta).parent
    return Path.home()


async def cargar_dataset(sesion):
    """Abre el explorador e importa el archivo elegido.

    Si hay un modelo cargado con cambios sin guardar, antes pregunta,
    porque el dataset nuevo lo sustituye. Si el usuario no confirma o
    cierra el explorador, no cambia nada. Si el archivo no vale, se muestra
    el motivo y se conserva el dataset anterior.

    Returns:
        True si se ha cargado un dataset.
    """
    if sesion.modelo_cargado:
        seguir = await carga_modelo.aceptar_perder_cambios(
            sesion, "cargas un dataset"
        )
        if not seguir:
            return False
    ruta = await seleccionar_archivo(carpeta_inicial(sesion))
    if ruta is None:
        return False  # el usuario cerró el explorador: todo sigue igual
    try:
        sesion.importar_dataset(ruta)
    except ErrorImportacion as error:
        notificar_error(error)
        return False
    notificar_exito("Dataset cargado correctamente")
    return True
