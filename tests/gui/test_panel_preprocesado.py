"""Pruebas del panel de preprocesado de la GUI, sin servidor (#26).

uv run pytest tests/gui/test_panel_preprocesado.py -v
"""

import inspect

import numpy as np
import pandas as pd
import pytest
from nicegui import ui

from sikorius.gui.paneles.panel_preprocesado import (
    PanelPreprocesado,
    texto_resumen,
)
from sikorius.nucleo.preprocesado import (
    CONSTANTE,
    ELIMINAR,
    ESTRATEGIAS,
    MEDIA,
    MEDIANA,
)
from sikorius.sesion import Sesion

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


def crear_sesion(train=None, test=None, separar=True):
    """Sesión nueva con selección x -> y y, si se pide, separación."""
    train = crear_train() if train is None else train
    test = crear_test() if test is None else test
    sesion = Sesion()
    sesion.cargar_dataset(pd.concat([train, test]), "datos.csv")
    sesion.guardar_seleccion(["x"], "y")
    if separar:
        sesion.guardar_separacion(train, test, 20, 42)
    return sesion


@pytest.fixture
def sesion_con_nulos():
    return crear_sesion()


@pytest.fixture
def sesion_sin_nulos():
    train = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    test = pd.DataFrame({"x": [4.0], "y": [8.0]})
    return crear_sesion(train, test)


@pytest.fixture
def avisos(monkeypatch):
    """Recoge los ui.notify (mensaje, tipo) en lugar de mostrarlos."""
    lista = []

    def anotar(mensaje, **kw):
        lista.append((mensaje, kw.get("type")))

    monkeypatch.setattr(ui, "notify", anotar)
    return lista


# =============================================================================
# texto_resumen
# =============================================================================


def test_texto_resumen():
    resumen = {
        "train": {"filas_eliminadas": 3, "valores_rellenados": 0},
        "test": {"filas_eliminadas": 1, "valores_rellenados": 0},
    }
    assert texto_resumen(resumen) == (
        "Preprocesado aplicado. "
        "Entrenamiento: 3 filas eliminadas, 0 valores rellenados | "
        "Test: 1 filas eliminadas, 0 valores rellenados."
    )


def test_texto_resumen_sin_f_strings():
    codigo = inspect.getsource(texto_resumen)
    assert 'f"' not in codigo
    assert "f'" not in codigo


# =============================================================================
# Estado inicial
# =============================================================================


def test_sin_separacion_oculta_tabla_y_controles():
    panel = PanelPreprocesado(crear_sesion(separar=False))
    assert "Separa primero" in panel.aviso.text
    assert panel.tabla.rows == []
    assert not panel.tabla.visible
    assert not panel.controles.visible
    assert panel.aplicado.text == ""


def test_muestra_nulos_por_conjunto(sesion_con_nulos):
    panel = PanelPreprocesado(sesion_con_nulos)
    assert panel.tabla.visible
    assert panel.tabla.rows == [
        {"columna": "x", "train": 1, "test": 1},
        {"columna": "y", "train": 1, "test": 0},
    ]
    assert "Entrenamiento: 2 | Test: 1" in panel.aviso.text
    assert "text-orange-700" in panel.aviso.classes
    assert panel.controles.visible


def test_sin_nulos_oculta_controles(sesion_sin_nulos):
    panel = PanelPreprocesado(sesion_sin_nulos)
    assert panel.tabla.rows == [
        {"columna": "x", "train": 0, "test": 0},
        {"columna": "y", "train": 0, "test": 0},
    ]
    assert "No hay valores inexistentes" in panel.aviso.text
    assert "text-green-700" in panel.aviso.classes
    assert not panel.controles.visible


def test_cabecera_numerica_en_la_tabla():
    train = pd.DataFrame({2020: [1.0, np.nan, 3.0], "y": [1.0, 2.0, 3.0]})
    test = pd.DataFrame({2020: [4.0], "y": [4.0]})
    sesion = Sesion()
    sesion.cargar_dataset(pd.concat([train, test]), "datos.xlsx")
    sesion.guardar_seleccion(["2020"], "y")
    sesion.guardar_separacion(train, test, 20, 42)

    panel = PanelPreprocesado(sesion)

    assert panel.tabla.rows[0] == {"columna": "2020", "train": 1, "test": 0}


def test_estrategia_por_defecto(sesion_con_nulos):
    panel = PanelPreprocesado(sesion_con_nulos)
    assert panel.boton.text == "Aplicar preprocesado"
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
def test_constante_solo_con_esa_estrategia(
    sesion_con_nulos, estrategia, habilitado
):
    panel = PanelPreprocesado(sesion_con_nulos)
    panel.estrategia.set_value(estrategia)
    assert panel.constante.enabled is habilitado


# =============================================================================
# Aplicar
# =============================================================================


def test_no_aplica_nada_hasta_pulsar(sesion_con_nulos, avisos):
    PanelPreprocesado(sesion_con_nulos)
    assert sesion_con_nulos.preprocesado is None
    assert avisos == []


def test_aplicar_correcto(sesion_con_nulos, avisos):
    panel = PanelPreprocesado(sesion_con_nulos)
    panel.estrategia.set_value(MEDIA)

    panel.aplicar()

    mensaje, tipo = avisos[-2]
    assert tipo == "positive"
    assert mensaje == texto_resumen(sesion_con_nulos.preprocesado.resumen)
    assert sesion_con_nulos.preprocesado.estrategia == MEDIA
    assert sesion_con_nulos.puede_crear_modelo()


def test_aplicar_lee_los_controles_al_pulsar(sesion_con_nulos):
    panel = PanelPreprocesado(sesion_con_nulos)
    panel.estrategia.set_value(CONSTANTE)
    panel.constante.set_value(9)

    panel.aplicar()

    preprocesado = sesion_con_nulos.preprocesado
    assert preprocesado.estrategia == CONSTANTE
    assert preprocesado.test.at[20, "x"] == 9.0


def test_error_constante_no_cambia_nada(sesion_con_nulos, avisos):
    panel = PanelPreprocesado(sesion_con_nulos)
    panel.estrategia.set_value(CONSTANTE)  # sin escribir el valor

    panel.aplicar()

    mensaje, tipo = avisos[-1]
    assert tipo == "negative"
    assert "debe ser un número" in mensaje
    assert sesion_con_nulos.preprocesado is None
    assert panel.controles.visible


def test_sin_separacion_avisa(avisos):
    panel = PanelPreprocesado(crear_sesion(separar=False))
    panel.aplicar()
    mensaje, tipo = avisos[-1]
    assert tipo == "negative"
    assert "Separa primero" in mensaje


def test_aviso_si_queda_un_conjunto_vacio(avisos):
    train = pd.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0]})
    test = pd.DataFrame({"x": [np.nan], "y": [1.0]})
    sesion = crear_sesion(train, test)
    panel = PanelPreprocesado(sesion)

    panel.aplicar()

    mensaje, tipo = avisos[-1]
    assert tipo == "warning"  # aviso, no error
    assert "vacío" in mensaje
    assert sesion.preprocesado is None


def test_se_puede_reintentar_tras_un_error(sesion_con_nulos, avisos):
    panel = PanelPreprocesado(sesion_con_nulos)
    panel.estrategia.set_value(CONSTANTE)
    panel.aplicar()
    assert avisos[-1][1] == "negative"
    assert panel.boton.enabled

    panel.constante.set_value(1)
    panel.aplicar()

    assert avisos[-1][1] == "positive"
    assert sesion_con_nulos.preprocesado is not None


# =============================================================================
# Después de aplicar: se puede cambiar de estrategia
# =============================================================================


def test_tras_aplicar_se_siguen_viendo_los_nulos_originales(sesion_con_nulos):
    panel = PanelPreprocesado(sesion_con_nulos)
    panel.estrategia.set_value(MEDIANA)

    panel.aplicar()

    assert panel.tabla.rows == [
        {"columna": "x", "train": 1, "test": 1},
        {"columna": "y", "train": 1, "test": 0},
    ]
    assert "sin preprocesar" not in panel.aviso.text
    assert panel.controles.visible


def test_tras_aplicar_muestra_la_estrategia(sesion_con_nulos):
    panel = PanelPreprocesado(sesion_con_nulos)
    panel.estrategia.set_value(MEDIA)

    panel.aplicar()

    assert panel.aplicado.text == (
        "Aplicado: Rellenar con la media (de entrenamiento)"
    )


def test_se_puede_cambiar_de_estrategia(sesion_con_nulos):
    panel = PanelPreprocesado(sesion_con_nulos)
    panel.estrategia.set_value(MEDIA)
    panel.aplicar()

    panel.estrategia.set_value(ELIMINAR)
    panel.aplicar()

    preprocesado = sesion_con_nulos.preprocesado
    assert preprocesado.estrategia == ELIMINAR
    # Se aplica sobre los datos sin preprocesar, no sobre los ya rellenados
    assert preprocesado.resumen["train"]["filas_eliminadas"] == 2
    assert panel.aplicado.text == (
        "Aplicado: Eliminar filas con valores inexistentes"
    )


def test_error_al_cambiar_conserva_lo_aplicado(sesion_con_nulos, avisos):
    panel = PanelPreprocesado(sesion_con_nulos)
    panel.estrategia.set_value(MEDIA)
    panel.aplicar()
    anterior = sesion_con_nulos.preprocesado

    panel.estrategia.set_value(CONSTANTE)
    panel.constante.set_value(None)
    panel.aplicar()

    assert avisos[-1][1] == "negative"
    assert sesion_con_nulos.preprocesado is anterior


# =============================================================================
# Se actualiza solo con la sesión
# =============================================================================


def test_se_actualiza_solo_al_separar():
    sesion = crear_sesion(separar=False)
    panel = PanelPreprocesado(sesion)
    assert not panel.tabla.visible

    sesion.guardar_separacion(crear_train(), crear_test(), 20, 42)

    assert panel.tabla.visible
    assert panel.controles.visible


def test_volver_a_separar_borra_lo_aplicado(sesion_con_nulos):
    panel = PanelPreprocesado(sesion_con_nulos)
    panel.aplicar()
    assert panel.aplicado.text != ""

    sesion_con_nulos.guardar_separacion(crear_train(), crear_test(), 20, 1)

    assert panel.aplicado.text == ""


def test_dataset_nuevo_oculta_el_panel(sesion_con_nulos):
    panel = PanelPreprocesado(sesion_con_nulos)

    sesion_con_nulos.cargar_dataset(crear_train(), "otro.csv")

    assert "Separa primero" in panel.aviso.text
    assert not panel.tabla.visible
    assert not panel.controles.visible


def test_al_recargar_la_pagina_marca_lo_aplicado(sesion_con_nulos):
    sesion_con_nulos.aplicar_preprocesado(MEDIANA)

    panel = PanelPreprocesado(sesion_con_nulos)

    assert panel.estrategia.value == MEDIANA
    assert panel.aplicado.text == (
        "Aplicado: Rellenar con la mediana (de entrenamiento)"
    )


def test_otros_avisos_no_cambian_la_estrategia_elegida(sesion_con_nulos):
    panel = PanelPreprocesado(sesion_con_nulos)
    panel.aplicar()  # eliminar
    panel.estrategia.set_value(MEDIA)  # elige otra, sin aplicar

    panel.actualizar()  # la sesión avisa por otro motivo

    assert panel.estrategia.value == MEDIA


def test_no_contiene_logica_de_preprocesado():
    import sikorius.gui.paneles.panel_preprocesado as panel

    codigo = inspect.getsource(panel)
    assert "detectar_nulos_conjuntos(" in codigo
    for prohibido in ("fillna", "dropna", "isna", "mean(", "median("):
        assert prohibido not in codigo
