"""Pruebas del panel de selección de columnas, sin servidor (#11).

uv run pytest tests/gui/test_panel_columnas.py -v
"""

import pandas as pd
import pytest
from nicegui import ui

from sikorius.gui.paneles.panel_columnas import PanelColumnas
from sikorius.nucleo.separacion import separar_datos


@pytest.fixture
def avisos(monkeypatch):
    """Recoge los ui.notify (mensaje, tipo) en lugar de mostrarlos."""
    lista = []

    def anotar(mensaje, **kw):
        lista.append((mensaje, kw.get("type")))

    monkeypatch.setattr(ui, "notify", anotar)
    return lista


def elegir(panel, features, target):
    """Marca en los selectores lo que elegiría el usuario."""
    panel.features.selector.set_value(features)
    panel.target.selector.set_value(target)


# --- Estado inicial ---


def test_sin_dataset(sesion):
    panel = PanelColumnas(sesion)
    assert not panel.boton_confirmar.enabled
    assert not panel.features.selector.enabled
    assert panel.etiqueta_seleccion.text == ""


def test_al_cargar_muestra_las_columnas(sesion, datos):
    panel = PanelColumnas(sesion)
    sesion.cargar_dataset(datos, "datos.csv")
    assert panel.boton_confirmar.enabled
    assert panel.features.columnas == ["x1", "x2", "y"]
    assert panel.target.columnas == ["x1", "x2", "y"]


# --- Confirmar ---


def test_confirmar_guarda_en_la_sesion(sesion, datos, avisos):
    sesion.cargar_dataset(datos, "datos.csv")
    panel = PanelColumnas(sesion)
    elegir(panel, ["x1", "x2"], "y")

    panel.confirmar()

    assert sesion.seleccion.features == ("x1", "x2")
    assert sesion.seleccion.target == "y"
    assert panel.etiqueta_seleccion.text == "Entrada: x1, x2 | Salida: y"
    assert avisos[-1][1] == "positive"


def test_confirmar_incompleto_no_cambia_la_sesion(sesion, datos, avisos):
    sesion.cargar_dataset(datos, "datos.csv")
    panel = PanelColumnas(sesion)
    elegir(panel, ["x1"], None)

    panel.confirmar()

    assert sesion.seleccion is None
    assert avisos[-1][1] == "negative"
    assert "Falta seleccionar" in avisos[-1][0]


def test_confirmar_columna_no_numerica(sesion, avisos):
    datos = pd.DataFrame({"x": [1, 2], "barrio": ["a", "b"], "y": [3, 4]})
    sesion.cargar_dataset(datos, "datos.csv")
    panel = PanelColumnas(sesion)
    elegir(panel, ["barrio"], "y")

    panel.confirmar()

    assert sesion.seleccion is None
    assert "no son numéricas" in avisos[-1][0]


def test_confirmar_cabecera_numerica(sesion, avisos):
    """Una columna llamada 2020 (número) se elige como "2020" (texto)."""
    datos = pd.DataFrame({2020: [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    sesion.cargar_dataset(datos, "datos.xlsx")
    panel = PanelColumnas(sesion)
    elegir(panel, ["2020"], "y")

    panel.confirmar()

    assert sesion.seleccion.features == ("2020",)
    assert sesion.columnas_modelo() == [2020, "y"]


# --- La selección no se pierde ---


def test_al_recargar_la_pagina_se_ve_la_seleccion(
    sesion_con_seleccion,
):
    panel = PanelColumnas(sesion_con_seleccion)
    assert panel.features.obtener_seleccion() == ["x1", "x2"]
    assert panel.target.obtener_seleccion() == "y"
    assert panel.etiqueta_seleccion.text == "Entrada: x1, x2 | Salida: y"


def test_al_recargar_el_target_sigue_sin_las_features(
    sesion_con_seleccion,
):
    panel = PanelColumnas(sesion_con_seleccion)
    assert panel.target.selector.options == ["y"]


def test_separar_no_recrea_los_selectores(sesion_con_seleccion):
    panel = PanelColumnas(sesion_con_seleccion)
    selector = panel.features.selector

    entrenamiento, test = separar_datos(
        sesion_con_seleccion.dataset.datos, 20, 42
    )
    sesion_con_seleccion.guardar_separacion(entrenamiento, test, 20, 42)

    assert panel.features.selector is selector
    assert panel.features.obtener_seleccion() == ["x1", "x2"]


def test_lo_elegido_sin_confirmar_no_se_pierde(sesion_con_seleccion):
    """Si otro paso avisa a la sesión, no se borra lo que se está eligiendo."""
    panel = PanelColumnas(sesion_con_seleccion)
    elegir(panel, ["x1"], None)

    entrenamiento, test = separar_datos(
        sesion_con_seleccion.dataset.datos, 20, 42
    )
    sesion_con_seleccion.guardar_separacion(entrenamiento, test, 20, 42)

    assert panel.features.obtener_seleccion() == ["x1"]


def test_dataset_nuevo_limpia_la_seleccion(sesion_con_seleccion, datos):
    panel = PanelColumnas(sesion_con_seleccion)

    sesion_con_seleccion.cargar_dataset(datos, "otro.csv")

    assert panel.features.obtener_seleccion() == []
    assert panel.target.obtener_seleccion() is None
    assert panel.etiqueta_seleccion.text == ""
