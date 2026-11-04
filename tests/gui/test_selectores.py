"""Pruebas de los selectores de columnas, sin servidor.

Prueban el componente directamente, sin pasar por la demo ni por el panel:
así siguen sirviendo cuando se borre ``datos_entrada_salida.py``.

uv run pytest tests/gui/test_selectores.py -v
"""

import pandas as pd

from sikorius.gui.componentes.selectores import (
    SelectorFeatures,
    SelectorTarget,
)


def datos():
    return pd.DataFrame(
        {"x1": [1, 2], "x2": [3, 4], 2020: [5, 6], "y": [7, 8]}
    )


# --- SelectorFeatures ---


def test_features_sin_dataset_esta_deshabilitado():
    selector = SelectorFeatures()
    assert not selector.selector.enabled
    assert selector.obtener_seleccion() == []


def test_features_muestra_las_columnas_como_texto():
    selector = SelectorFeatures()
    selector.cargar_columnas(datos())
    assert selector.selector.enabled
    assert selector.columnas == ["x1", "x2", "2020", "y"]


def test_features_devuelve_siempre_una_lista():
    selector = SelectorFeatures()
    selector.cargar_columnas(datos())
    selector.selector.set_value(["x1", "2020"])
    assert selector.obtener_seleccion() == ["x1", "2020"]


def test_features_dataset_nuevo_limpia_la_seleccion():
    selector = SelectorFeatures()
    selector.cargar_columnas(datos())
    selector.selector.set_value(["x1"])
    selector.cargar_columnas(pd.DataFrame({"a": [1], "b": [2]}))
    assert selector.obtener_seleccion() == []
    assert selector.columnas == ["a", "b"]


# --- SelectorTarget ---


def test_target_sin_dataset_esta_deshabilitado():
    selector = SelectorTarget()
    assert not selector.selector.enabled
    assert selector.obtener_seleccion() is None


def test_target_excluye_las_features():
    selector = SelectorTarget()
    selector.cargar_columnas(datos())
    selector.excluir(["x1", "x2"])
    assert selector.selector.options == ["2020", "y"]


def test_target_excluido_se_deselecciona():
    selector = SelectorTarget()
    selector.cargar_columnas(datos())
    selector.selector.set_value("x1")
    selector.excluir(["x1"])
    assert selector.obtener_seleccion() is None


def test_target_dataset_nuevo_quita_las_exclusiones():
    selector = SelectorTarget()
    selector.cargar_columnas(datos())
    selector.excluir(["x1"])
    selector.cargar_columnas(datos())
    assert selector.selector.options == ["x1", "x2", "2020", "y"]
