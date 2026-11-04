"""Pruebas del panel de separación de la GUI, sin servidor (#41).

uv run pytest tests/gui/test_panel_separacion.py -v
"""

import numpy as np
import pandas as pd
import pytest
from nicegui import ui

from sikorius.gui.paneles.panel_separacion import PanelSeparacion
from sikorius.nucleo.separacion import separar_datos
from sikorius.sesion import Sesion

# =============================================================================
# Utilidades
# =============================================================================


def crear_df(num_filas):
    """Dataset con una columna 'id' única por fila, una feature y un target."""
    return pd.DataFrame(
        {
            "id": list(range(num_filas)),
            "x": np.arange(num_filas, dtype=float) * 1.5,
            "y": np.arange(num_filas, dtype=float) * 3.0 + 1.0,
        }
    )


def ids(df):
    """Conjunto con los valores de la columna 'id'."""
    return set(df["id"].tolist())


def crear_sesion(num_filas, con_seleccion=True):
    """Sesión nueva con un dataset de num_filas filas y, si se pide, con la
    selección x -> y confirmada."""
    sesion = Sesion()
    sesion.cargar_dataset(crear_df(num_filas), "datos.csv")
    if con_seleccion:
        sesion.guardar_seleccion(["x"], "y")
    return sesion


@pytest.fixture
def sesion_100():
    return crear_sesion(100)


@pytest.fixture
def avisos(monkeypatch):
    """Recoge los ui.notify (mensaje, tipo) en lugar de mostrarlos."""
    lista = []

    def anotar(mensaje, **kw):
        lista.append((mensaje, kw.get("type")))

    monkeypatch.setattr(ui, "notify", anotar)
    return lista


# =============================================================================
# Estado inicial y habilitado
# =============================================================================


def test_panel_valores_por_defecto(sesion_100):
    panel = PanelSeparacion(sesion_100)
    assert panel.entrada_porcentaje.value == "20"
    assert panel.entrada_semilla.value == "42"
    assert panel.etiqueta_entrenamiento.text == "Entrenamiento: 80 %"
    assert panel.etiqueta_resultado.text == ""


def test_panel_deshabilitado_sin_seleccion(avisos):
    sesion = crear_sesion(50, con_seleccion=False)
    panel = PanelSeparacion(sesion)
    assert not panel.boton_separar.enabled
    assert not panel.entrada_porcentaje.enabled
    assert not panel.entrada_semilla.enabled
    assert "Confirma primero" in panel.aviso.text
    panel.separar()
    assert avisos[-1][1] == "negative"
    assert sesion.separacion is None


def test_panel_se_habilita_solo_al_confirmar_seleccion():
    sesion = crear_sesion(50, con_seleccion=False)
    panel = PanelSeparacion(sesion)
    sesion.guardar_seleccion(["x"], "y")
    assert panel.boton_separar.enabled
    assert panel.entrada_porcentaje.enabled
    assert panel.entrada_semilla.enabled
    assert panel.aviso.text == ""


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("20", "Entrenamiento: 80 %"),
        ("1", "Entrenamiento: 99 %"),
        ("99", "Entrenamiento: 1 %"),
        ("12.5", "Entrenamiento: 87.5 %"),
        ("12,5", "Entrenamiento: 87.5 %"),
        ("33.33", "Entrenamiento: 66.67 %"),
        ("0", "Entrenamiento: -"),
        ("100", "Entrenamiento: -"),
        ("abc", "Entrenamiento: -"),
        ("", "Entrenamiento: -"),
    ],
)
def test_panel_entrenamiento_es_el_complementario(sesion_100, texto, esperado):
    panel = PanelSeparacion(sesion_100)
    panel.entrada_porcentaje.set_value(texto)
    assert panel.etiqueta_entrenamiento.text == esperado


# =============================================================================
# Separar
# =============================================================================


def test_panel_separar_correcto(sesion_100, avisos):
    panel = PanelSeparacion(sesion_100)
    panel.separar()
    separacion = sesion_100.separacion
    assert len(separacion.entrenamiento) == 80
    assert len(separacion.test) == 20
    assert separacion.porcentaje_test == 20.0
    assert separacion.semilla == 42
    mensaje, tipo = avisos[-1]
    assert tipo == "positive"
    assert "correctamente" in mensaje
    assert "80 filas" in mensaje
    assert "20 filas" in mensaje
    assert (
        panel.etiqueta_resultado.text
        == "Entrenamiento: 80 filas | Test: 20 filas"
    )


def test_panel_separar_con_otros_valores(sesion_100):
    panel = PanelSeparacion(sesion_100)
    panel.entrada_porcentaje.set_value("35")
    panel.entrada_semilla.set_value("7")
    panel.separar()
    separacion = sesion_100.separacion
    assert len(separacion.test) == 35
    assert len(separacion.entrenamiento) == 65
    esperado = separar_datos(sesion_100.dataset.datos, 35, 7)[1]
    pd.testing.assert_frame_equal(separacion.test, esperado)


@pytest.mark.parametrize("porcentaje", ["0", "100", "abc", "", "-5", "150"])
def test_panel_porcentaje_no_valido(sesion_100, avisos, porcentaje):
    panel = PanelSeparacion(sesion_100)
    panel.entrada_porcentaje.set_value(porcentaje)
    panel.separar()
    mensaje, tipo = avisos[-1]
    assert tipo == "negative"
    assert "entre 1 y 99" in mensaje
    assert sesion_100.separacion is None


@pytest.mark.parametrize("semilla", ["4.5", "abc", "", "-1"])
def test_panel_semilla_no_valida(sesion_100, avisos, semilla):
    panel = PanelSeparacion(sesion_100)
    panel.entrada_semilla.set_value(semilla)
    panel.separar()
    mensaje, tipo = avisos[-1]
    assert tipo == "negative"
    assert "entero" in mensaje
    assert sesion_100.separacion is None


def test_panel_dataset_con_pocas_filas(avisos):
    sesion = crear_sesion(4)
    panel = PanelSeparacion(sesion)
    panel.separar()
    mensaje, tipo = avisos[-1]
    assert tipo == "negative"
    assert "al menos 5" in mensaje
    assert sesion.separacion is None


def test_panel_conjunto_vacio(avisos):
    sesion = crear_sesion(5)
    panel = PanelSeparacion(sesion)
    panel.entrada_porcentaje.set_value("99")
    panel.separar()
    mensaje, tipo = avisos[-1]
    assert tipo == "negative"
    assert "vacío" in mensaje


def test_panel_error_conserva_separacion_anterior(sesion_100, avisos):
    panel = PanelSeparacion(sesion_100)
    panel.separar()
    anterior = sesion_100.separacion
    panel.entrada_porcentaje.set_value("100")
    panel.separar()
    assert sesion_100.separacion is anterior


def test_panel_repetir_separacion_descarta_preprocesado(sesion_100):
    panel = PanelSeparacion(sesion_100)
    panel.separar()
    sesion_100.preprocesado = "preprocesado anterior"
    sesion_100.modelo = "modelo anterior"
    panel.entrada_semilla.set_value("1")
    panel.separar()
    assert sesion_100.preprocesado is None
    assert sesion_100.modelo is None
    assert sesion_100.separacion.semilla == 1


def test_panel_misma_entrada_misma_separacion(sesion_100):
    panel = PanelSeparacion(sesion_100)
    panel.separar()
    primera = ids(sesion_100.separacion.test)
    panel.separar()
    assert ids(sesion_100.separacion.test) == primera


# =============================================================================
# Se actualiza solo con la sesión
# =============================================================================


def test_panel_cambio_de_seleccion_borra_resultado(sesion_100):
    panel = PanelSeparacion(sesion_100)
    panel.separar()
    assert panel.etiqueta_resultado.text != ""
    sesion_100.cargar_dataset(crear_df(100), "otro.csv")
    assert panel.etiqueta_resultado.text == ""
    assert not panel.boton_separar.enabled


def test_al_recargar_la_pagina_muestra_los_valores_usados(sesion_100):
    entrenamiento, test = separar_datos(sesion_100.dataset.datos, 35, 7)
    sesion_100.guardar_separacion(entrenamiento, test, 35.0, 7)

    panel = PanelSeparacion(sesion_100)

    assert panel.entrada_porcentaje.value == "35"
    assert panel.entrada_semilla.value == "7"
    assert panel.etiqueta_entrenamiento.text == "Entrenamiento: 65 %"
    assert (
        panel.etiqueta_resultado.text
        == "Entrenamiento: 65 filas | Test: 35 filas"
    )


def test_al_recargar_muestra_porcentaje_con_decimales(sesion_100):
    entrenamiento, test = separar_datos(sesion_100.dataset.datos, 12.5, 3)
    sesion_100.guardar_separacion(entrenamiento, test, 12.5, 3)

    panel = PanelSeparacion(sesion_100)

    assert panel.entrada_porcentaje.value == "12.5"
    assert panel.etiqueta_entrenamiento.text == "Entrenamiento: 87.5 %"


def test_otros_pasos_no_borran_lo_que_se_esta_escribiendo(
    sesion_separada,
):
    """Si otro panel cambia la sesión sin tocar la separación, los campos
    se quedan con lo que el usuario estaba escribiendo."""
    panel = PanelSeparacion(sesion_separada)
    panel.entrada_porcentaje.set_value("30")

    sesion_separada.aplicar_preprocesado("eliminar")

    assert panel.entrada_porcentaje.value == "30"


def test_panel_no_contiene_logica_de_separacion():
    """La GUI llama a separar_datos; no baraja filas por su cuenta."""
    import inspect

    import sikorius.gui.paneles.panel_separacion as panel

    codigo = inspect.getsource(panel)
    assert "separar_datos(" in codigo
    assert "permutation" not in codigo
    assert "sample(" not in codigo
