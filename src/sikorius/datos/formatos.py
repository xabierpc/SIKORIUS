"""Formatos de archivo que admite SIKORIUS."""

from pathlib import Path

EXTENSIONES_CSV = (".csv",)
EXTENSIONES_EXCEL = (".xlsx", ".xls")
EXTENSIONES_SQLITE = (".sqlite", ".db")
EXTENSIONES_ADMITIDAS = (
    EXTENSIONES_CSV + EXTENSIONES_EXCEL + EXTENSIONES_SQLITE
)


def extension(ruta):
    """Extensión del archivo en minúsculas, con el punto.

    Args:
        ruta: Ruta del archivo, como texto o ``Path``.

    Returns:
        La extensión, por ejemplo ".csv", o "" si no tiene.
    """
    return Path(ruta).suffix.lower()


def es_admitido(ruta):
    """Indica si el archivo tiene una extensión que se puede importar.

    Args:
        ruta: Ruta del archivo, como texto o ``Path``.

    Returns:
        True si la extensión está en ``EXTENSIONES_ADMITIDAS`` (sin
        distinguir mayúsculas).
    """
    return extension(ruta) in EXTENSIONES_ADMITIDAS
