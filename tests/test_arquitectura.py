"""Vigila la separación en capas.

    gui -> aplicacion -> datos -> dominio

Cada capa solo puede importar las capas que tiene por debajo. La GUI puede
usar tipos, constantes y funciones de formato del dominio, pero los
archivos siempre los lee y escribe a través de la sesión.

    uv run pytest tests/test_arquitectura.py -v
"""

import ast
import importlib
from pathlib import Path

import pytest

import sikorius

RAIZ = Path(sikorius.__file__).parent
PROTOTIPOS = RAIZ.parents[1] / "prototipos"

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


def _importaciones_de_sikorius(archivo):
    """Pares (módulo, nombre) de cada ``from sikorius... import nombre``."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if (
            isinstance(nodo, ast.ImportFrom)
            and nodo.module is not None
            and nodo.module.startswith("sikorius")
        ):
            for alias in nodo.names:
                yield nodo.module, alias.name


@pytest.mark.parametrize(
    "archivo", sorted(PROTOTIPOS.glob("*.py")), ids=lambda a: a.name
)
def test_los_prototipos_importan_cosas_que_existen(archivo):
    """Los scripts de prototipos/ no los ejecuta el CI: si se mueve un módulo,
    este test avisa de que el script se ha quedado con una ruta vieja."""
    for modulo, nombre in _importaciones_de_sikorius(archivo):
        try:
            cargado = importlib.import_module(modulo)
        except ModuleNotFoundError:
            pytest.fail(
                archivo.name + " importa " + modulo + ", que no existe"
            )
        assert hasattr(cargado, nombre), (
            archivo.name + " importa " + nombre + " de " + modulo
        )
