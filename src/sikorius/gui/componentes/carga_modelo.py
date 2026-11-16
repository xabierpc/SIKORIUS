"""Carga de un modelo guardado desde la interfaz (historia #24).

Junta lo que pasa al pulsar "Cargar modelo": preguntar si el modelo actual
tiene cambios sin guardar, elegir el archivo y avisar de cómo ha ido.
Leer el archivo y cambiar el estado es cosa de la sesión (que usa el
núcleo): aquí no se abre ningún archivo.
"""

from pathlib import Path

from sikorius.gui.avisos import notificar_error, notificar_exito
from sikorius.gui.componentes.confirmacion import confirmar
from sikorius.gui.componentes.dialogo_guardado import es_modelo
from sikorius.gui.componentes.explorador_archivos import seleccionar_archivo
from sikorius.nucleo.errores import ErrorPersistencia
from sikorius.nucleo.persistencia import EXTENSION

TITULO_EXPLORADOR = "Selecciona un modelo"


def carpeta_inicial(sesion):
    """Carpeta que muestra el explorador al cargar un modelo.

    La del modelo actual si se guardó o se cargó de un archivo; si no, la
    del dataset; y si tampoco hay dataset, la carpeta personal.
    """
    if sesion.ruta_modelo is not None:
        return Path(sesion.ruta_modelo).parent
    if sesion.dataset is not None:
        return Path(sesion.dataset.ruta).parent
    return Path.home()


def tiene_cambios_sin_guardar(sesion):
    """True si hay un modelo con cambios que se perderían al sustituirlo.

    Es el caso de un modelo creado que no se ha guardado, o de uno
    guardado o cargado cuya descripción ha cambiado después.
    """
    return sesion.modelo is not None and sesion.modelo_sin_guardar


async def aceptar_perder_cambios(sesion, accion):
    """Pregunta antes de perder los cambios sin guardar del modelo.

    Args:
        sesion: Sesión de trabajo.
        accion: Lo que va a hacer el usuario, para el mensaje (por
            ejemplo, "cargas otro modelo").

    Returns:
        True si no hay cambios sin guardar o el usuario acepta perderlos.
    """
    if not tiene_cambios_sin_guardar(sesion):
        return True
    return await confirmar(
        "Cambios sin guardar",
        "El modelo actual tiene cambios sin guardar. Si "
        + accion
        + ", se perderán. ¿Quieres continuar?",
        "Continuar",
    )


async def cargar_modelo(sesion):
    """Pide un archivo de modelo y lo carga en la sesión.

    Si el usuario no confirma o cierra el explorador, no cambia nada y no
    se muestra ningún error. Si el archivo no vale, se muestra el motivo,
    la sesión queda como estaba y se puede probar con otro.

    Returns:
        True si se ha cargado un modelo.
    """
    if not await aceptar_perder_cambios(sesion, "cargas otro modelo"):
        return False
    ruta = await seleccionar_archivo(
        carpeta_inicial(sesion),
        titulo=TITULO_EXPLORADOR,
        tipos=(EXTENSION,),
        admitido=es_modelo,
    )
    if ruta is None:
        return False  # el usuario cerró el explorador: todo sigue igual
    try:
        sesion.cargar_modelo(ruta)
    except ErrorPersistencia as error:
        notificar_error(error)
        return False
    notificar_exito("Modelo cargado de " + str(sesion.ruta_modelo))
    return True
