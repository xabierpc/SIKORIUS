"""Vigila la separación en capas.

    gui -> aplicacion -> datos -> dominio

Cada capa solo puede importar las capas que tiene por debajo. La GUI puede
usar tipos, constantes y funciones de formato del dominio, pero los
archivos siempre los lee y escribe a través de la sesión.

    uv run pytest tests/test_arquitectura.py -v
"""

import ast
from pathlib import Path

import pytest

import sikorius

RAIZ = Path(sikorius.__file__).parent

PROHIBIDOS = {
    "dominio": (
        "nicegui",
        "sikorius.gui",
        "sikorius.aplicacion",
        "sikorius.datos",
    ),
    "datos": ("nicegui", "sikorius.gui", "sikorius.aplicacion"),
    "aplicacion": ("nicegui", "sikorius.gui"),
    "gui": ("sikorius.datos",),
}


def _modulos_importados(archivo):
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                yield alias.name
        elif isinstance(nodo, ast.ImportFrom) and nodo.module is not None:
            yield nodo.module


@pytest.mark.parametrize("capa", sorted(PROHIBIDOS))
def test_capa_no_importa_capas_prohibidas(capa):
    for archivo in (RAIZ / capa).rglob("*.py"):
        for modulo in _modulos_importados(archivo):
            assert not modulo.startswith(PROHIBIDOS[capa]), (
                capa + "/" + archivo.name + " importa " + modulo
            )
