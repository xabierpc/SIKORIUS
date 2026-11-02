"""Pruebas del botón y el panel de preprocesado de la GUI, sin servidor.

    uv run pytest tests/gui/test_panel_preprocesado.py -v

Bloques:
    - crear_boton_preprocesado: el botón de la GUI, sin servidor.
    - PanelPreprocesado: el panel de la GUI, sin servidor.
"""

import inspect

import numpy as np
import pandas as pd
import pytest
from nicegui import ui

import sikorius.gui.paneles.boton_preprocesado as modulo_boton
from sikorius.estado import EstadoApp
from sikorius.nucleo.preprocesado import (
    CONSTANTE,
    ELIMINAR,
    ESTRATEGIAS,
    MEDIA,
    MEDIANA,
    texto_resumen,
)

# =============================================================================
# Utilidades
# =============================================================================


def crear_train():
    """Entrenamiento con un NaN en 'x', una celda en blanco en 'y' y un NaN
    en 'otra', que no se selecciona nunca."""
    return pd.DataFrame(
        {
            "x": [1.0, np.nan, 3.0, 5.0],
            "y": [10.0, 20.0, "  ", 40.0],
            "otra": [np.nan, 1.0, 2.0, 3.0],
        },
        index=[10, 11, 12, 13],
    )


def crear_test():
    """Test con un NaN en 'x' y ninguno en 'y'."""
    return pd.DataFrame(
        {
            "x": [np.nan, 100.0],
            "y": [1.0, 2.0],
            "otra": [np.nan, np.nan],
        },
        index=[20, 21],
    )


COLUMNAS = ["x", "y"]


def crear_estado(train=None, test=None):
    """Estado nuevo (no la instancia compartida) con selección y separación."""
    train = crear_train() if train is None else train
    test = crear_test() if test is None else test
    estado = EstadoApp()
    estado.datos = pd.concat([train, test])
    estado.guardar_seleccion(["x"], "y", "simple")
    estado.guardar_separacion(train, test, 20, 42)
    return estado


@pytest.fixture
def estado_con_nulos():
    return crear_estado()


@pytest.fixture
def estado_sin_nulos():
    train = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    test = pd.DataFrame({"x": [4.0], "y": [8.0]})
    return crear_estado(train, test)


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


class Botones:
    """Guarda la función on_click de cada ui.button para poder "pulsarlo"."""

    def __init__(self, monkeypatch):
        self.al_pulsar = {}
        original = ui.button

        def boton(texto="", *args, on_click=None, **kw):
            self.al_pulsar[texto] = on_click
            return original(texto, *args, on_click=on_click, **kw)

        monkeypatch.setattr(ui, "button", boton)

    def pulsar(self, texto="Aplicar preprocesado"):
        self.al_pulsar[texto]()


# =============================================================================
# crear_boton_preprocesado (GUI sin servidor)
# =============================================================================
#
# El botón trabaja con la instancia compartida ``sikorius.estado.estado``.
# Para no ensuciarla entre tests se sustituye por un estado nuevo.


def crear_boton(
    estado, monkeypatch, estrategia, constante=None, al_aplicar=None
):
    from sikorius.gui.paneles.boton_preprocesado import (
        crear_boton_preprocesado,
    )

    monkeypatch.setattr(modulo_boton, "estado", estado)
    avisos = Avisos(monkeypatch)
    botones = Botones(monkeypatch)
    boton = crear_boton_preprocesado(
        obtener_estrategia=lambda: estrategia,
        obtener_constante=lambda: constante,
        al_aplicar=al_aplicar,
    )
    return boton, botones, avisos


def test_boton_texto(estado_con_nulos, monkeypatch):
    boton, _, _ = crear_boton(estado_con_nulos, monkeypatch, MEDIA)
    assert boton.text == "Aplicar preprocesado"


def test_boton_no_aplica_nada_hasta_pulsarlo(estado_con_nulos, monkeypatch):
    _, _, avisos = crear_boton(estado_con_nulos, monkeypatch, MEDIA)
    assert estado_con_nulos.preprocesado is None
    assert avisos.lista == []


def test_boton_aplicar_correcto(estado_con_nulos, monkeypatch):
    llamadas = []
    _, botones, avisos = crear_boton(
        estado_con_nulos,
        monkeypatch,
        MEDIA,
        al_aplicar=lambda: llamadas.append(1),
    )
    botones.pulsar()
    mensaje, tipo = avisos.ultimo()
    assert tipo == "positive"
    assert mensaje == texto_resumen(estado_con_nulos.preprocesado["resumen"])
    assert estado_con_nulos.preprocesado["estrategia"] == MEDIA
    assert llamadas == [1]


def test_boton_sin_al_aplicar(estado_con_nulos, monkeypatch):
    _, botones, avisos = crear_boton(estado_con_nulos, monkeypatch, ELIMINAR)
    botones.pulsar()
    assert avisos.ultimo()[1] == "positive"


def test_boton_lee_los_controles_al_pulsar(estado_con_nulos, monkeypatch):
    """La estrategia y la constante se leen al pulsar, no al crear el botón."""
    from sikorius.gui.paneles.boton_preprocesado import (
        crear_boton_preprocesado,
    )

    monkeypatch.setattr(modulo_boton, "estado", estado_con_nulos)
    Avisos(monkeypatch)
    botones = Botones(monkeypatch)
    controles = {"estrategia": MEDIA, "constante": None}
    crear_boton_preprocesado(
        lambda: controles["estrategia"], lambda: controles["constante"]
    )
    controles["estrategia"] = CONSTANTE
    controles["constante"] = "9"
    botones.pulsar()
    assert estado_con_nulos.preprocesado["estrategia"] == CONSTANTE
    assert estado_con_nulos.preprocesado["test"].at[20, "x"] == 9.0


@pytest.mark.parametrize("constante", [None, "abc", ""])
def test_boton_error_constante(estado_con_nulos, monkeypatch, constante):
    llamadas = []
    _, botones, avisos = crear_boton(
        estado_con_nulos,
        monkeypatch,
        CONSTANTE,
        constante,
        al_aplicar=lambda: llamadas.append(1),
    )
    botones.pulsar()
    mensaje, tipo = avisos.ultimo()
    assert tipo == "negative"
    assert "debe ser un número" in mensaje
    assert estado_con_nulos.preprocesado is None
    assert llamadas == []


def test_boton_sin_separacion(monkeypatch):
    estado = EstadoApp()
    estado.datos = crear_train()
    estado.guardar_seleccion(["x"], "y", "simple")
    _, botones, avisos = crear_boton(estado, monkeypatch, MEDIA)
    botones.pulsar()
    mensaje, tipo = avisos.ultimo()
    assert tipo == "negative"
    assert "Separa primero" in mensaje


def test_boton_aviso_conjunto_vacio(monkeypatch):
    train = pd.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0]})
    test = pd.DataFrame({"x": [np.nan], "y": [1.0]})
    estado = crear_estado(train, test)
    llamadas = []
    _, botones, avisos = crear_boton(
        estado, monkeypatch, ELIMINAR, al_aplicar=lambda: llamadas.append(1)
    )
    botones.pulsar()
    mensaje, tipo = avisos.ultimo()
    assert tipo == "warning"  # aviso, no error
    assert "vacío" in mensaje
    assert estado.preprocesado is None
    assert llamadas == []


def test_boton_se_puede_reintentar_tras_un_error(
    estado_con_nulos, monkeypatch
):
    from sikorius.gui.paneles.boton_preprocesado import (
        crear_boton_preprocesado,
    )

    monkeypatch.setattr(modulo_boton, "estado", estado_con_nulos)
    avisos = Avisos(monkeypatch)
    botones = Botones(monkeypatch)
    constante = {"valor": "abc"}
    boton = crear_boton_preprocesado(
        lambda: CONSTANTE, lambda: constante["valor"]
    )
    botones.pulsar()
    assert avisos.ultimo()[1] == "negative"
    assert boton.enabled
    constante["valor"] = "1"
    botones.pulsar()
    assert avisos.ultimo()[1] == "positive"
    assert estado_con_nulos.preprocesado is not None


def test_boton_no_contiene_logica_de_preprocesado():
    """La GUI llama a aplicar_al_estado; no trata los nulos por su cuenta."""
    codigo = inspect.getsource(modulo_boton)
    assert "aplicar_al_estado(" in codigo
    for prohibido in ("fillna", "dropna", "isna", "mean(", "median("):
        assert prohibido not in codigo


# =============================================================================
# PanelPreprocesado (GUI sin servidor)
# =============================================================================


def crear_panel(estado, monkeypatch, al_aplicar=None):
    from sikorius.gui.paneles.panel_preprocesado import PanelPreprocesado

    monkeypatch.setattr(modulo_boton, "estado", estado)
    avisos = Avisos(monkeypatch)
    botones = Botones(monkeypatch)
    panel = PanelPreprocesado(estado, al_aplicar=al_aplicar)
    return panel, botones, avisos


def test_panel_sin_separacion_oculta_tabla_y_controles(monkeypatch):
    estado = EstadoApp()
    estado.datos = crear_train()
    estado.guardar_seleccion(["x"], "y", "simple")
    panel, _, _ = crear_panel(estado, monkeypatch)
    assert "Separa primero" in panel.aviso.text
    assert panel.tabla.rows == []
    assert not panel.tabla.visible
    assert not panel.controles.visible


def test_panel_muestra_nulos_por_conjunto(estado_con_nulos, monkeypatch):
    panel, _, _ = crear_panel(estado_con_nulos, monkeypatch)
    assert panel.tabla.visible
    assert panel.tabla.rows == [
        {"columna": "x", "train": 1, "test": 1},
        {"columna": "y", "train": 1, "test": 0},
    ]
    assert "Entrenamiento: 2 | Test: 1" in panel.aviso.text
    assert "text-orange-700" in panel.aviso.classes
    assert panel.controles.visible


def test_panel_sin_nulos_oculta_controles(estado_sin_nulos, monkeypatch):
    panel, _, _ = crear_panel(estado_sin_nulos, monkeypatch)
    assert panel.tabla.visible
    assert panel.tabla.rows == [
        {"columna": "x", "train": 0, "test": 0},
        {"columna": "y", "train": 0, "test": 0},
    ]
    assert "No hay valores inexistentes" in panel.aviso.text
    assert "text-green-700" in panel.aviso.classes
    assert not panel.controles.visible


def test_panel_estrategia_por_defecto(estado_con_nulos, monkeypatch):
    panel, _, _ = crear_panel(estado_con_nulos, monkeypatch)
    assert panel.estrategia.value == ELIMINAR
    assert set(panel.estrategia.options) == set(ESTRATEGIAS)
    assert not panel.constante.enabled


@pytest.mark.parametrize(
    "estrategia, habilitado",
    [
        (CONSTANTE, True),
        (MEDIA, False),
        (MEDIANA, False),
        (ELIMINAR, False),
    ],
)
def test_panel_constante_solo_con_esa_estrategia(
    estado_con_nulos, monkeypatch, estrategia, habilitado
):
    panel, _, _ = crear_panel(estado_con_nulos, monkeypatch)
    panel.estrategia.set_value(estrategia)
    assert panel.constante.enabled is habilitado


def test_panel_aplicar_actualiza_la_deteccion(estado_con_nulos, monkeypatch):
    llamadas = []
    panel, botones, avisos = crear_panel(
        estado_con_nulos, monkeypatch, al_aplicar=lambda: llamadas.append(1)
    )
    panel.estrategia.set_value(MEDIANA)
    botones.pulsar()
    assert avisos.ultimo()[1] == "positive"
    assert estado_con_nulos.preprocesado["estrategia"] == MEDIANA
    # Tras aplicar ya no quedan nulos: la tabla se pone a 0 y se ocultan
    # los controles
    assert all(
        fila["train"] == 0 and fila["test"] == 0 for fila in panel.tabla.rows
    )
    assert not panel.controles.visible
    assert llamadas == [1]


def test_panel_aplicar_constante(estado_con_nulos, monkeypatch):
    panel, botones, _ = crear_panel(estado_con_nulos, monkeypatch)
    panel.estrategia.set_value(CONSTANTE)
    panel.constante.set_value(-1)
    botones.pulsar()
    assert estado_con_nulos.preprocesado["entrenamiento"].at[11, "x"] == -1.0


def test_panel_error_no_cambia_nada(estado_con_nulos, monkeypatch):
    llamadas = []
    panel, botones, avisos = crear_panel(
        estado_con_nulos, monkeypatch, al_aplicar=lambda: llamadas.append(1)
    )
    panel.estrategia.set_value(CONSTANTE)  # sin escribir el valor
    botones.pulsar()
    assert avisos.ultimo()[1] == "negative"
    assert estado_con_nulos.preprocesado is None
    assert panel.controles.visible
    assert llamadas == []


def test_panel_actualizar_tras_separar(monkeypatch):
    estado = EstadoApp()
    estado.datos = crear_train()
    estado.guardar_seleccion(["x"], "y", "simple")
    panel, _, _ = crear_panel(estado, monkeypatch)
    assert not panel.tabla.visible
    estado.guardar_separacion(crear_train(), crear_test(), 20, 42)
    panel.actualizar()
    assert panel.tabla.visible
    assert panel.controles.visible


def test_panel_actualizar_tras_borrar_seleccion(estado_con_nulos, monkeypatch):
    panel, _, _ = crear_panel(estado_con_nulos, monkeypatch)
    estado_con_nulos.borrar_seleccion()
    panel.actualizar()
    assert "Separa primero" in panel.aviso.text
    assert not panel.tabla.visible
    assert not panel.controles.visible


def test_panel_no_contiene_logica_de_preprocesado():
    import sikorius.gui.paneles.panel_preprocesado as panel

    codigo = inspect.getsource(panel)
    assert "detectar_en_estado(" in codigo
    for prohibido in ("fillna", "dropna", "isna", "mean(", "median("):
        assert prohibido not in codigo
