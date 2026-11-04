"""Formatos de archivo que admite SIKORIUS."""

from pathlib import Path

EXTENSIONES_CSV = (".csv",)
EXTENSIONES_EXCEL = (".xlsx", ".xls")
EXTENSIONES_SQLITE = (".sqlite", ".db")
EXTENSIONES_ADMITIDAS = (
    EXTENSIONES_CSV + EXTENSIONES_EXCEL + EXTENSIONES_SQLITE
)


def extension(ruta):
    """Extensión del archivo en minúsculas, con el punto."""
    return Path(ruta).suffix.lower()


def es_admitido(ruta):
    """Indica si el archivo tiene una extensión que se puede importar."""
    return extension(ruta) in EXTENSIONES_ADMITIDAS
