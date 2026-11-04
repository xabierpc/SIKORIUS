"""Pruebas del panel de selección de columnas, sin servidor (#11).

Incluyen los casos de confirmación que antes se probaban contra la demo de
selección de columnas (test_entrada.py y test_salida.py), ahora contra el
panel real que usa la aplicación.

    uv run pytest tests/gui/test_panel_columnas.py -v
"""

import inspect

import pandas as pd
import pytest
from nicegui import ui

from sikorius.gui.paneles.panel_columnas import PanelColumnas
from sikorius.nucleo.importador import importar_datos
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


def abrir_target(panel):
    """Simula que el usuario abre el desplegable del target."""
    oyentes = [
        e
        for e in panel.target.selector._event_listeners.values()
        if e.type in ("popup-show", "popupShow")
    ]
    manejador = oyentes[-1].handler
    if inspect.signature(manejador).parameters:
        manejador(None)
    else:
        manejador()


@pytest.fixture
def casas():
    """Dataset pequeño con tres columnas numéricas y una de texto (barrio)."""
    return pd.DataFrame(
        {
            "superficie": [60.0, 95.0, 110.0],
            "habitaciones": [2, 3, 4],
            "barrio": ["Elviña", "Os Mallos", "Riazor"],
            "precio": [121000, 189500, 265000],
        }
    )


@pytest.fixture
def panel_casas(sesion, casas):
    sesion.cargar_dataset(casas, "casas.csv")
    return PanelColumnas(sesion)


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


# --- Confirmar: casos de la antigua demo ---


def test_confirmar_sin_dataset(sesion, avisos):
    panel = PanelColumnas(sesion)
    panel.confirmar()
    assert avisos == [("Carga primero un dataset.", "negative")]
    assert sesion.seleccion is None


@pytest.mark.parametrize(
    "features, target, mensaje",
    [
        ([], None, "features) y la columna de salida (target)"),
        ([], "precio", "al menos una columna de entrada"),
        (["superficie"], None, "la columna de salida"),
    ],
)
def test_confirmar_falta_algo(panel_casas, avisos, features, target, mensaje):
    elegir(panel_casas, features, target)
    panel_casas.confirmar()
    texto, tipo = avisos[-1]
    assert texto.startswith("Falta seleccionar")
    assert mensaje in texto
    assert tipo == "negative"
    assert panel_casas.sesion.seleccion is None


def test_confirmar_una_sola_entrada_es_regresion_simple(panel_casas, avisos):
    elegir(panel_casas, ["superficie"], "precio")
    panel_casas.confirmar()
    assert avisos[-1] == (
        "Selección confirmada. Entrada: superficie | Salida: precio",
        "positive",
    )
    assert panel_casas.sesion.seleccion.tipo_regresion == "simple"


def test_confirmar_varias_entradas_es_regresion_multiple(panel_casas, avisos):
    panel_casas.features.selector.set_value(["superficie", "habitaciones"])
    abrir_target(panel_casas)
    panel_casas.target.selector.set_value("precio")
    panel_casas.confirmar()
    assert avisos[-1] == (
        "Selección confirmada. Entrada: superficie, habitaciones | "
        "Salida: precio",
        "positive",
    )
    assert panel_casas.sesion.seleccion.tipo_regresion == "multiple"


def test_confirmar_target_no_numerico(panel_casas, avisos):
    elegir(panel_casas, ["superficie"], "barrio")
    panel_casas.confirmar()
    texto, tipo = avisos[-1]
    assert "no son numéricas" in texto and "barrio" in texto
    assert tipo == "negative"
    assert panel_casas.sesion.seleccion is None


def test_al_abrir_target_se_excluyen_las_features(panel_casas):
    panel_casas.features.selector.set_value(["superficie", "habitaciones"])
    abrir_target(panel_casas)
    assert panel_casas.target.selector.options == ["barrio", "precio"]


def test_target_elegido_y_luego_como_feature_se_rechaza(panel_casas, avisos):
    """Si se elige el target antes que las features, nada impide elegir la
    misma columna como feature; la validación lo tiene que parar."""
    panel_casas.target.selector.set_value("precio")
    panel_casas.features.selector.set_value(["precio", "superficie"])
    panel_casas.confirmar()
    texto, tipo = avisos[-1]
    assert "no puede ser entrada y salida a la vez" in texto
    assert tipo == "negative"
    assert panel_casas.sesion.seleccion is None


def test_al_reabrir_target_se_quita_si_ya_es_feature(panel_casas):
    panel_casas.target.selector.set_value("precio")
    panel_casas.features.selector.set_value(["precio"])
    abrir_target(panel_casas)
    assert panel_casas.target.obtener_seleccion() is None


def test_confirmar_excel_con_cabeceras_numericas(sesion, tmp_path, avisos):
    """Las cabeceras 2023 y 2024 de un Excel llegan como números."""
    ruta = tmp_path / "anios.xlsx"
    pd.DataFrame({2023: [1.0, 2.0], 2024: [3.0, 4.0]}).to_excel(
        ruta, index=False
    )
    sesion.cargar_dataset(importar_datos(ruta), ruta)
    panel = PanelColumnas(sesion)
    elegir(panel, ["2023"], "2024")
    panel.confirmar()
    assert avisos[-1][1] == "positive"
    assert sesion.columnas_modelo() == [2023, 2024]


def test_dataset_nuevo_muestra_sus_columnas_y_hay_que_elegir_otra_vez(
    panel_casas, avisos
):
    elegir(panel_casas, ["superficie"], "precio")
    panel_casas.sesion.cargar_dataset(
        pd.DataFrame({"x": [1, 3], "y": [2, 4]}), "otro.csv"
    )
    assert panel_casas.features.selector.options == ["x", "y"]
    assert panel_casas.features.obtener_seleccion() == []
    assert panel_casas.target.obtener_seleccion() is None
    panel_casas.confirmar()
    assert "Falta seleccionar" in avisos[-1][0]


def test_confirmar_con_seleccion_del_dataset_anterior_falla(
    panel_casas, avisos
):
    """Aunque el valor viejo siguiera en el selector, la validación usa el
    dataset nuevo y avisa de que la columna no existe."""
    panel_casas.sesion.cargar_dataset(
        pd.DataFrame({"x": [1, 3], "y": [2, 4]}), "otro.csv"
    )
    panel_casas.features.selector.options.append("superficie")
    elegir(panel_casas, ["superficie"], "y")
    panel_casas.confirmar()
    texto, tipo = avisos[-1]
    assert "no existen" in texto and "superficie" in texto
    assert tipo == "negative"
    assert panel_casas.sesion.seleccion is None
