"""Vigila la separación en capas: gui -> sesion -> nucleo.

Ningún módulo de ``sikorius.nucleo`` puede importar NiceGUI, la sesión ni
la interfaz gráfica.

    uv run pytest tests/test_arquitectura.py -v
"""

import ast
from pathlib import Path

import sikorius.nucleo

PROHIBIDOS = ("nicegui", "sikorius.sesion", "sikorius.gui")


def _modulos_importados(archivo):
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                yield alias.name
        elif isinstance(nodo, ast.ImportFrom) and nodo.module is not None:
            yield nodo.module


def test_nucleo_no_depende_de_la_gui_ni_de_la_sesion():
    carpeta = Path(sikorius.nucleo.__file__).parent
    for archivo in carpeta.glob("*.py"):
        for modulo in _modulos_importados(archivo):
            assert not modulo.startswith(PROHIBIDOS), (
                archivo.name + " importa " + modulo
            )
