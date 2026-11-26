"""Pruebas del tema oscuro de la GUI.

uv run pytest tests/gui/test_tema.py -v
"""

import re
from pathlib import Path

import pytest

import sikorius.gui
from sikorius.gui.pagina import TITULOS
from sikorius.gui.tema import CARPETA_RECURSOS, COLORES, CSS_TEMA

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


# Una etiqueta con el mismo color de texto y de fondo (text-warning bg-warning)
# no se lee. Se mira cada línea del código: si lleva text-X y bg-X con el
# mismo color del tema, falla.
TEXTO_TEMA = re.compile(
    r"\btext-(primary|secondary|accent|dark|positive|negative|warning|info)\b"
)
FONDO_TEMA = re.compile(
    r"\bbg-(primary|secondary|accent|dark|positive|negative|warning|info)\b"
)


def textos_del_mismo_color_que_su_fondo(texto):
    """Líneas de ``texto`` con text-X y bg-X del mismo color del tema."""
    repetidos = []
    for numero, linea in enumerate(texto.splitlines(), start=1):
        iguales = set(TEXTO_TEMA.findall(linea)) & set(
            FONDO_TEMA.findall(linea)
        )
        if iguales:
            repetidos.append(numero)
    return repetidos


def test_la_deteccion_de_texto_del_color_del_fondo_funciona():
    assert textos_del_mismo_color_que_su_fondo(
        '"text-sm text-warning bg-warning p-2"'
    ) == [1]
    assert (
        textos_del_mismo_color_que_su_fondo('"text-dark bg-warning p-2"') == []
    )
    assert (
        textos_del_mismo_color_que_su_fondo('"text-warning bg-white/5"') == []
    )


def test_ninguna_etiqueta_tiene_el_texto_del_color_de_su_fondo():
    carpeta = Path(sikorius.gui.__file__).parent
    encontrados = []
    for archivo in carpeta.rglob("*.py"):
        texto = archivo.read_text(encoding="utf-8")
        for numero in textos_del_mismo_color_que_su_fondo(texto):
            encontrados.append(archivo.name + ":" + str(numero))
    assert encontrados == []


# =============================================================================
# Fuente de marca
# =============================================================================


def test_la_fuente_de_marca_esta_en_recursos_con_su_licencia():
    carpeta = CARPETA_RECURSOS / "fuentes"
    assert (carpeta / "Forque.ttf").is_file()
    # La OFL obliga a repartir la licencia junto con la fuente
    assert "SIL OPEN FONT LICENSE" in (carpeta / "OFL.txt").read_text()
    assert "/recursos/fuentes/Forque.ttf" in CSS_TEMA


def test_el_logo_esta_en_recursos():
    assert (CARPETA_RECURSOS / "logo.svg").is_file()


def test_los_titulos_y_las_pestanas_usan_la_fuente_de_marca_en_mayusculas():
    for selector in (".text-lg.font-semibold", ".q-tab__label"):
        assert selector in CSS_TEMA
    assert "text-transform: uppercase" in CSS_TEMA


def test_la_fuente_no_se_pide_en_negrita():
    """Forque solo tiene un grosor: en negrita el navegador la deformaría."""
    bloque = CSS_TEMA.split("Forque', sans-serif;")[1].split("}")[0]
    assert "font-weight: 400" in bloque


# Caracteres que trae Forque entre los que usamos: letras ASCII, cifras y
# unos pocos signos. No trae tildes, Ñ, paréntesis, barras ni guiones bajos.
LETRAS_DE_FORQUE = re.compile(r"[A-Za-z0-9 .,:;!?=+\-]*")

# Etiquetas de título: ui.label("Texto").classes("text-lg font-semibold ...")
TITULO = re.compile(
    r'ui\.label\(\s*"([^"]*)"\s*\)\s*\.classes\(\s*"[^"]*'
    r"text-(?:lg font-semibold|xl font-bold)"
)


def test_los_titulos_fijos_solo_llevan_caracteres_que_trae_forque():
    carpeta = Path(sikorius.gui.__file__).parent
    fuera = []
    for archivo in carpeta.rglob("*.py"):
        for texto in TITULO.findall(archivo.read_text(encoding="utf-8")):
            if not LETRAS_DE_FORQUE.fullmatch(texto):
                fuera.append(archivo.name + ": " + texto)
    assert fuera == []


def test_los_nombres_de_las_pestanas_solo_llevan_caracteres_de_forque():
    for titulo in TITULOS.values():
        assert LETRAS_DE_FORQUE.fullmatch(titulo), titulo
