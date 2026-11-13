"""Pruebas del tema oscuro de la GUI.

uv run pytest tests/gui/test_tema.py -v
"""

import re
from pathlib import Path

import pytest

import sikorius.gui
from sikorius.gui.tema import COLORES

# Clases de Tailwind con un color fijo (text-gray-500, bg-green-100...): no
# cambian con el tema. Hay que usar las del tema: text-primary, text-warning,
# opacity-70, bg-white/5...
COLOR_FIJO = re.compile(
    r"\b(?:text|bg|border)-"
    r"(?:gray|grey|slate|zinc|neutral|stone|red|orange|amber|yellow|green"
    r"|blue|sky|indigo|purple)-\d{2,3}\b"
)


def test_los_colores_de_marca_son_morado_y_azul_claro():
    assert COLORES["primary"] == "#8b5cf6"
    assert COLORES["secondary"] == "#7dd3fc"


@pytest.mark.parametrize("nombre", list(COLORES))
def test_cada_color_es_un_hexadecimal_valido(nombre):
    assert re.fullmatch(r"#[0-9a-f]{6}", COLORES[nombre])


def test_la_gui_no_usa_colores_fijos_de_tailwind():
    carpeta = Path(sikorius.gui.__file__).parent
    encontrados = []
    for archivo in carpeta.rglob("*.py"):
        lineas = archivo.read_text(encoding="utf-8").splitlines()
        for numero, linea in enumerate(lineas, start=1):
            for coincidencia in COLOR_FIJO.findall(linea):
                encontrados.append(
                    archivo.name + ":" + str(numero) + " " + coincidencia
                )
    assert encontrados == []
