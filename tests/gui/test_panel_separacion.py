"""Pruebas del panel de separación de la GUI, sin servidor (#41).

uv run pytest tests/gui/test_panel_separacion.py -v
"""

import numpy as np
import pandas as pd
import pytest
from nicegui import ui

from sikorius.estado import EstadoApp
from sikorius.nucleo.separacion import (
    separar_datos,
)

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


@pytest.fixture
def estado_con_seleccion():
    """Estado nuevo (no la instancia compartida) con datos y selección."""
    estado = EstadoApp()
    estado.datos = crear_df(100)
    estado.guardar_seleccion(["x"], "y", "simple")
    return estado


class Avisos:
    """Recoge los ui.notify en lugar de mostrarlos."""

    def __init__(self, monkeypatch):
        self.lista = []
        monkeypatch.setattr(ui, "notify", self._anotar)

    def _anotar(self, mensaje, **kw):
        self.lista.append((mensaje, kw.get("type")))

    def ultimo(self):
        assert len(self.lista) > 0
        return self.lista[-1]


# =============================================================================
# PanelSeparacion (GUI sin servidor)
# =============================================================================


def crear_panel(estado, monkeypatch, al_separar=None):
    from sikorius.gui.paneles.panel_separacion import PanelSeparacion

    avisos = Avisos(monkeypatch)
    panel = PanelSeparacion(estado, al_separar=al_separar)
    return panel, avisos


def test_panel_valores_por_defecto(estado_con_seleccion, monkeypatch):
    panel, _ = crear_panel(estado_con_seleccion, monkeypatch)
    assert panel.entrada_porcentaje.value == "20"
    assert panel.entrada_semilla.value == "42"
    assert panel.etiqueta_entrenamiento.text == "Entrenamiento: 80 %"
    assert panel.etiqueta_resultado.text == ""


def test_panel_deshabilitado_sin_seleccion(monkeypatch):
    estado = EstadoApp()
    estado.datos = crear_df(50)
    panel, avisos = crear_panel(estado, monkeypatch)
    assert not panel.boton_separar.enabled
    assert not panel.entrada_porcentaje.enabled
    assert not panel.entrada_semilla.enabled
    assert "Confirma primero" in panel.aviso.text
    panel.separar()
    assert avisos.ultimo()[1] == "negative"
    assert not estado.hay_separacion()


def test_panel_se_habilita_al_confirmar_seleccion(monkeypatch):
    estado = EstadoApp()
    estado.datos = crear_df(50)
    panel, _ = crear_panel(estado, monkeypatch)
    estado.guardar_seleccion(["x"], "y", "simple")
    panel.actualizar()
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
def test_panel_entrenamiento_es_el_complementario(
    estado_con_seleccion, monkeypatch, texto, esperado
):
    panel, _ = crear_panel(estado_con_seleccion, monkeypatch)
    panel.entrada_porcentaje.set_value(texto)
    assert panel.etiqueta_entrenamiento.text == esperado


def test_panel_separar_correcto(estado_con_seleccion, monkeypatch):
    llamadas = []
    panel, avisos = crear_panel(
        estado_con_seleccion,
        monkeypatch,
        al_separar=lambda: llamadas.append(1),
    )
    panel.separar()
    estado = estado_con_seleccion
    assert estado.hay_separacion()
    assert len(estado.entrenamiento) == 80
    assert len(estado.test) == 20
    assert estado.separacion == {"porcentaje_test": 20.0, "semilla": 42}
    mensaje, tipo = avisos.ultimo()
    assert tipo == "positive"
    assert "correctamente" in mensaje
    assert "80 filas" in mensaje
    assert "20 filas" in mensaje
    assert (
        panel.etiqueta_resultado.text
        == "Entrenamiento: 80 filas | Test: 20 filas"
    )
    assert llamadas == [1]


def test_panel_separar_con_otros_valores(estado_con_seleccion, monkeypatch):
    panel, _ = crear_panel(estado_con_seleccion, monkeypatch)
    panel.entrada_porcentaje.set_value("35")
    panel.entrada_semilla.set_value("7")
    panel.separar()
    estado = estado_con_seleccion
    assert len(estado.test) == 35
    assert len(estado.entrenamiento) == 65
    esperado = separar_datos(estado.datos, 35, 7)[1]
    pd.testing.assert_frame_equal(estado.test, esperado)


@pytest.mark.parametrize("porcentaje", ["0", "100", "abc", "", "-5", "150"])
def test_panel_porcentaje_no_valido(
    estado_con_seleccion, monkeypatch, porcentaje
):
    llamadas = []
    panel, avisos = crear_panel(
        estado_con_seleccion,
        monkeypatch,
        al_separar=lambda: llamadas.append(1),
    )
    panel.entrada_porcentaje.set_value(porcentaje)
    panel.separar()
    mensaje, tipo = avisos.ultimo()
    assert tipo == "negative"
    assert "entre 1 y 99" in mensaje
    assert not estado_con_seleccion.hay_separacion()
    assert llamadas == []


@pytest.mark.parametrize("semilla", ["4.5", "abc", "", "-1"])
def test_panel_semilla_no_valida(estado_con_seleccion, monkeypatch, semilla):
    panel, avisos = crear_panel(estado_con_seleccion, monkeypatch)
    panel.entrada_semilla.set_value(semilla)
    panel.separar()
    mensaje, tipo = avisos.ultimo()
    assert tipo == "negative"
    assert "entero" in mensaje
    assert not estado_con_seleccion.hay_separacion()


def test_panel_dataset_con_pocas_filas(monkeypatch):
    estado = EstadoApp()
    estado.datos = crear_df(4)
    estado.guardar_seleccion(["x"], "y", "simple")
    panel, avisos = crear_panel(estado, monkeypatch)
    panel.separar()
    mensaje, tipo = avisos.ultimo()
    assert tipo == "negative"
    assert "al menos 5" in mensaje
    assert not estado.hay_separacion()


def test_panel_conjunto_vacio(monkeypatch):
    estado = EstadoApp()
    estado.datos = crear_df(5)
    estado.guardar_seleccion(["x"], "y", "simple")
    panel, avisos = crear_panel(estado, monkeypatch)
    panel.entrada_porcentaje.set_value("99")
    panel.separar()
    mensaje, tipo = avisos.ultimo()
    assert tipo == "negative"
    assert "vacío" in mensaje


def test_panel_error_conserva_separacion_anterior(
    estado_con_seleccion, monkeypatch
):
    panel, _ = crear_panel(estado_con_seleccion, monkeypatch)
    panel.separar()
    test_anterior = estado_con_seleccion.test
    panel.entrada_porcentaje.set_value("100")
    panel.separar()
    assert estado_con_seleccion.test is test_anterior


def test_panel_repetir_separacion_descarta_preprocesado(
    estado_con_seleccion, monkeypatch
):
    panel, _ = crear_panel(estado_con_seleccion, monkeypatch)
    panel.separar()
    estado_con_seleccion.preprocesado = {"algo": 1}
    estado_con_seleccion.modelo = "modelo"
    panel.entrada_semilla.set_value("1")
    panel.separar()
    assert estado_con_seleccion.preprocesado is None
    assert estado_con_seleccion.modelo is None
    assert estado_con_seleccion.separacion["semilla"] == 1


def test_panel_cambio_de_seleccion_borra_resultado(
    estado_con_seleccion, monkeypatch
):
    panel, _ = crear_panel(estado_con_seleccion, monkeypatch)
    panel.separar()
    assert panel.etiqueta_resultado.text != ""
    estado_con_seleccion.borrar_seleccion()
    panel.actualizar()
    assert panel.etiqueta_resultado.text == ""
    assert not panel.boton_separar.enabled


def test_panel_misma_entrada_misma_separacion(
    estado_con_seleccion, monkeypatch
):
    panel, _ = crear_panel(estado_con_seleccion, monkeypatch)
    panel.separar()
    primera = ids(estado_con_seleccion.test)
    panel.separar()
    assert ids(estado_con_seleccion.test) == primera


def test_panel_no_contiene_logica_de_separacion():
    """La GUI llama a separar_datos; no baraja filas por su cuenta."""
    import inspect

    import sikorius.gui.paneles.panel_separacion as panel

    codigo = inspect.getsource(panel)
    assert "separar_datos(" in codigo
    assert "permutation" not in codigo
    assert "sample(" not in codigo
