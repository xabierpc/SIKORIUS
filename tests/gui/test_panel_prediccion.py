"""Pruebas del panel de predicción de la GUI, sin servidor (#22).

uv run pytest tests/gui/test_panel_prediccion.py -v
"""

import numpy as np
import pandas as pd
import pytest
from nicegui import ui

from sikorius.aplicacion.sesion import Sesion
from sikorius.gui.paneles.panel_prediccion import PanelPrediccion

# =============================================================================
# Utilidades
# =============================================================================


def datos_lineales(n=20):
    """y = 2*x1 - 3*x2 + 5, sin ruido."""
    x1 = np.arange(n, dtype=float)
    x2 = (np.arange(n, dtype=float) * 7) % 11
    return pd.DataFrame({"x1": x1, "x2": x2, "y": 2 * x1 - 3 * x2 + 5})


def crear_sesion(features=("x1", "x2")):
    """Sesión con datos separados en 15 + 5 filas, lista para crear."""
    df = datos_lineales()
    sesion = Sesion()
    sesion.cargar_dataset(df, "datos.csv")
    sesion.guardar_seleccion(list(features), "y")
    sesion.guardar_separacion(df.iloc[:15], df.iloc[15:], 20, 42)
    return sesion


def escribir(panel, **valores):
    for columna, valor in valores.items():
        panel.campos[columna].set_value(valor)


@pytest.fixture
def avisos(monkeypatch):
    """Recoge los ui.notify (mensaje, tipo) en lugar de mostrarlos."""
    lista = []

    def anotar(mensaje, **kw):
        lista.append((mensaje, kw.get("type")))

    monkeypatch.setattr(ui, "notify", anotar)
    return lista


@pytest.fixture
def sesion_con_modelo():
    sesion = crear_sesion()
    sesion.crear_modelo()
    return sesion


# =============================================================================
# Disponibilidad
# =============================================================================


def test_sin_modelo_no_se_ve():
    panel = PanelPrediccion(crear_sesion())
    assert not panel.tarjeta.visible
    assert panel.campos == {}


def test_al_crear_el_modelo_aparece():
    sesion = crear_sesion()
    panel = PanelPrediccion(sesion)
    sesion.crear_modelo()
    assert panel.tarjeta.visible
    assert list(panel.campos) == ["x1", "x2"]


def test_al_cargar_un_modelo_aparece(sesion_con_modelo, tmp_path):
    ruta = sesion_con_modelo.guardar_modelo(tmp_path / "modelo ñ.json")
    sesion = Sesion()
    panel = PanelPrediccion(sesion)

    sesion.cargar_modelo(ruta)

    assert panel.tarjeta.visible
    assert list(panel.campos) == ["x1", "x2"]


def test_al_cargar_otro_dataset_desaparece(sesion_con_modelo):
    panel = PanelPrediccion(sesion_con_modelo)
    sesion_con_modelo.cargar_dataset(datos_lineales(), "otro.csv")
    assert not panel.tarjeta.visible
    assert panel.campos == {}


# =============================================================================
# Campos
# =============================================================================


def test_un_campo_por_columna_con_su_nombre(sesion_con_modelo):
    panel = PanelPrediccion(sesion_con_modelo)
    etiquetas = [campo.props["label"] for campo in panel.campos.values()]
    assert etiquetas == ["x1", "x2"]


def test_nuevo_modelo_rehace_los_campos_y_borra_el_resultado(
    sesion_con_modelo, avisos
):
    panel = PanelPrediccion(sesion_con_modelo)
    escribir(panel, x1="1", x2="2")
    panel.predecir()
    assert panel.resultado.visible

    # Otro modelo, ahora con una sola columna de entrada
    df = datos_lineales()
    sesion_con_modelo.guardar_seleccion(["x1"], "y")
    sesion_con_modelo.guardar_separacion(df.iloc[:15], df.iloc[15:], 20, 42)
    sesion_con_modelo.crear_modelo()

    assert list(panel.campos) == ["x1"]
    assert panel.campos["x1"].value == ""
    assert panel.resultado.text == ""
    assert not panel.resultado.visible


def test_guardar_el_modelo_no_borra_lo_escrito(sesion_con_modelo, tmp_path):
    panel = PanelPrediccion(sesion_con_modelo)
    escribir(panel, x1="1", x2="2")
    sesion_con_modelo.guardar_modelo(tmp_path / "modelo.json")
    assert panel.valores() == {"x1": "1", "x2": "2"}


def test_al_recargar_la_pagina_tiene_los_campos(sesion_con_modelo):
    PanelPrediccion(sesion_con_modelo)
    despues = PanelPrediccion(sesion_con_modelo)  # F5
    assert despues.tarjeta.visible
    assert list(despues.campos) == ["x1", "x2"]


# =============================================================================
# Predicción
# =============================================================================


@pytest.mark.parametrize(
    "x1, x2, esperado",
    [
        ("4", "1", "y = 10.0000"),  # 2*4 - 3*1 + 5
        ("3,5", "2.5", "y = 4.5000"),  # 7 - 7.5 + 5
        ("0", "10", "y = -25.0000"),
    ],
)
def test_predecir_muestra_salida_igual_valor(
    sesion_con_modelo, avisos, x1, x2, esperado
):
    panel = PanelPrediccion(sesion_con_modelo)
    escribir(panel, x1=x1, x2=x2)
    panel.predecir()
    assert panel.resultado.text == esperado
    assert panel.resultado.visible
    assert avisos == []


def test_mismo_resultado_con_modelo_creado_y_cargado(
    sesion_con_modelo, tmp_path, avisos
):
    creado = PanelPrediccion(sesion_con_modelo)
    escribir(creado, x1="7,25", x2="3")
    creado.predecir()

    ruta = sesion_con_modelo.guardar_modelo(tmp_path / "modelo.json")
    sesion = Sesion()
    sesion.cargar_modelo(ruta)
    cargado = PanelPrediccion(sesion)
    escribir(cargado, x1="7,25", x2="3")
    cargado.predecir()

    assert cargado.resultado.text == creado.resultado.text


# =============================================================================
# Errores
# =============================================================================


def test_falta_un_valor_avisa_de_cual(sesion_con_modelo, avisos):
    panel = PanelPrediccion(sesion_con_modelo)
    escribir(panel, x1="1")
    panel.predecir()
    assert avisos == [("Falta el valor de: x2.", "negative")]
    assert not panel.resultado.visible


def test_valor_no_numerico_avisa_de_cual(sesion_con_modelo, avisos):
    panel = PanelPrediccion(sesion_con_modelo)
    escribir(panel, x1="abc", x2="2")
    panel.predecir()
    assert avisos == [("El valor de x1 no es un número válido.", "negative")]
    assert not panel.resultado.visible


def test_tras_un_error_se_puede_corregir_y_predecir(sesion_con_modelo, avisos):
    panel = PanelPrediccion(sesion_con_modelo)
    escribir(panel, x1="4", x2="1")
    panel.predecir()
    escribir(panel, x2="uno")
    panel.predecir()
    assert not panel.resultado.visible
    assert panel.valores() == {"x1": "4", "x2": "uno"}

    escribir(panel, x2="1")
    panel.predecir()
    assert panel.resultado.text == "y = 10.0000"
