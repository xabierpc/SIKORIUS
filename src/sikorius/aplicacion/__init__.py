"""Capa de aplicación: lo único que la GUI necesita conocer.

Además de la sesión, reexporta los datos de los formatos de archivo que la
GUI usa en los diálogos, para que no tenga que importar la capa de datos.
"""

from sikorius.datos.formatos import EXTENSIONES_ADMITIDAS, es_admitido
from sikorius.datos.persistencia import EXTENSION, ruta_con_extension

__all__ = [
    "EXTENSION",
    "EXTENSIONES_ADMITIDAS",
    "es_admitido",
    "ruta_con_extension",
]
