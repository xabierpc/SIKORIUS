"""Pruebas del panel del modelo de la GUI, sin servidor (#121).

uv run pytest tests/gui/test_panel_modelo.py -v
"""

import inspect
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from nicegui import ui

from sikorius.gui.paneles.panel_modelo import PanelModelo, texto_metrica
from sikorius.sesion import Sesion

# =============================================================================
# Utilidades
# =============================================================================


def datos_lineales(n=20):
    """y = 2*x1 - 3*x2 + 5, sin ruido (un coeficiente es negativo)."""
    x1 = np.arange(n, dtype=float)
    x2 = (np.arange(n, dtype=float) * 7) % 11
    return pd.DataFrame({"x1": x1, "x2": x2, "y": 2 * x1 - 3 * x2 + 5})


def crear_sesion(df=None, features=("x1", "x2"), separar=True):
    """Sesión nueva con selección y, si se pide, separación 15 + 5 filas."""
    df = datos_lineales() if df is None else df
    sesion = Sesion()
    sesion.cargar_dataset(df, "datos.csv")
    sesion.guardar_seleccion(list(features), "y")
    if separar:
        sesion.guardar_separacion(df.iloc[:15], df.iloc[15:], 20, 42)
    return sesion


@pytest.fixture
def sesion_lista():
    """Se puede crear el modelo: hay separación y no hay nulos."""
    return crear_sesion()


@pytest.fixture
def sesion_con_nulos():
    df = datos_lineales()
    df.loc[3, "x1"] = np.nan
    return crear_sesion(df)


@pytest.fixture
def avisos(monkeypatch):
    """Recoge los ui.notify (mensaje, tipo) en lugar de mostrarlos."""
    lista = []

    def anotar(mensaje, **kw):
        lista.append((mensaje, kw.get("type")))

    monkeypatch.setattr(ui, "notify", anotar)
    return lista


# =============================================================================
# texto_metrica
# =============================================================================


@pytest.mark.parametrize(
    "nombre, valor, esperado",
    [
        ("R²", 0.98164, "R²: 0.9816"),
        ("ECM", 238494173.71153, "ECM: 238494173.7115"),
        ("R²", 1.0, "R²: 1"),
        ("R²", -0.5, "R²: -0.5"),
        ("R²", float("nan"), "R²: no calculable"),
    ],
)
def test_texto_metrica(nombre, valor, esperado):
    assert texto_metrica(nombre, valor) == esperado


# =============================================================================
# Estado inicial: cuándo se puede crear
# =============================================================================


def test_sin_seleccion_explica_que_falta():
    panel = PanelModelo(Sesion())
    assert "selección" in panel.aviso.text
    assert panel.aviso.visible
    assert not panel.boton.enabled
    assert not panel.resultados.visible


def test_sin_separacion_explica_que_falta():
    panel = PanelModelo(crear_sesion(separar=False))
    assert "Separa primero" in panel.aviso.text
    assert not panel.boton.enabled
    assert not panel.resultados.visible


def test_con_nulos_pide_preprocesar(sesion_con_nulos):
    panel = PanelModelo(sesion_con_nulos)
    assert "preprocesado" in panel.aviso.text
    assert not panel.boton.enabled


def test_se_puede_crear_cuando_esta_todo_listo(sesion_lista, avisos):
    panel = PanelModelo(sesion_lista)
    assert panel.boton.text == "Crear modelo"
    assert panel.boton.enabled
    assert not panel.aviso.visible
    assert not panel.resultados.visible
    assert sesion_lista.modelo is None  # no se crea hasta pulsar
    assert avisos == []


def test_con_nulos_tratados_se_habilita(sesion_con_nulos):
    panel = PanelModelo(sesion_con_nulos)
    sesion_con_nulos.aplicar_preprocesado("media")
    assert panel.boton.enabled


# =============================================================================
# Crear el modelo
# =============================================================================


def test_crear_muestra_exito_y_resultados(sesion_lista, avisos):
    panel = PanelModelo(sesion_lista)

    panel.crear()

    assert avisos == [("Modelo creado correctamente.", "positive")]
    assert sesion_lista.modelo is not None
    assert panel.resultados.visible


def test_muestra_la_formula_con_el_signo_correcto(sesion_lista):
    panel = PanelModelo(sesion_lista)
    panel.crear()
    assert panel.formula.text == "y = 2.0000 * x1 - 3.0000 * x2 + 5.0000"
    assert "+ -" not in panel.formula.text


def test_muestra_las_metricas_de_cada_conjunto(sesion_lista):
    panel = PanelModelo(sesion_lista)
    panel.crear()
    for clave in ("entrenamiento", "test"):
        r2, ecm = panel.metricas[clave]
        assert r2.text == "R²: 1"  # ajuste perfecto: los datos no tienen ruido
        assert ecm.text == "ECM: 0"


def test_las_metricas_distinguen_entrenamiento_y_test():
    df = datos_lineales()
    df.loc[15:, "y"] += 2  # el test tiene un error constante de 2
    panel = PanelModelo(crear_sesion(df))
    panel.crear()
    assert panel.metricas["entrenamiento"][1].text == "ECM: 0"
    assert panel.metricas["test"][1].text == "ECM: 4"


def test_r2_no_calculable_se_avisa_en_pantalla():
    df = datos_lineales().assign(y=7.0)  # salida constante
    panel = PanelModelo(crear_sesion(df))
    panel.crear()
    assert panel.metricas["entrenamiento"][0].text == "R²: no calculable"
    assert panel.metricas["test"][0].text == "R²: no calculable"


def test_grafico_regresion_multiple(sesion_lista):
    panel = PanelModelo(sesion_lista)
    panel.crear()
    ejes = panel.grafico.fig.axes[0]
    assert ejes.get_xlabel() == "Valor predicho"
    assert ejes.get_ylabel() == "Valor real"
    textos = [t.get_text() for t in ejes.get_legend().get_texts()]
    assert textos == ["Entrenamiento", "Test", "Real = predicho"]


def test_grafico_regresion_simple():
    panel = PanelModelo(crear_sesion(features=("x1",)))
    panel.crear()
    ejes = panel.grafico.fig.axes[0]
    assert ejes.get_xlabel() == "x1"
    assert ejes.get_ylabel() == "y"
    textos = [t.get_text() for t in ejes.get_legend().get_texts()]
    assert textos == ["Entrenamiento", "Test", "Recta del modelo"]


def test_crear_otra_vez_sustituye_al_modelo(sesion_lista, avisos):
    panel = PanelModelo(sesion_lista)
    panel.crear()
    primero = sesion_lista.modelo

    panel.crear()

    assert sesion_lista.modelo is not primero
    assert [tipo for _, tipo in avisos] == ["positive", "positive"]
    assert len(panel.grafico.fig.axes) == 1  # se redibuja, no se apila


def test_error_al_crear_avisa_y_no_cambia_nada(sesion_lista, avisos):
    constante = sesion_lista.separacion.entrenamiento.assign(x1=1.0)
    sesion_lista.separacion = replace(
        sesion_lista.separacion, entrenamiento=constante
    )
    panel = PanelModelo(sesion_lista)

    panel.crear()

    mensaje, tipo = avisos[-1]
    assert tipo == "negative"
    assert "modelo único" in mensaje
    assert sesion_lista.modelo is None
    assert not panel.resultados.visible
    assert panel.boton.enabled  # se puede volver a intentar


def test_columna_de_texto_avisa_con_su_nombre(avisos):
    df = datos_lineales().assign(texto="a")
    panel = PanelModelo(crear_sesion(df, features=("x1", "texto")))

    panel.crear()

    mensaje, tipo = avisos[-1]
    assert tipo == "negative"
    assert "'texto' no es numérica" in mensaje


def test_sin_separacion_avisa_al_pulsar(avisos):
    panel = PanelModelo(crear_sesion(separar=False))
    panel.crear()
    mensaje, tipo = avisos[-1]
    assert tipo == "negative"
    assert "Separa primero" in mensaje


# =============================================================================
# Camino completo
# =============================================================================


def test_camino_completo_con_valores_inexistentes(sesion_separada, avisos):
    """El flujo entero: separado con un NaN, se trata y se crea el modelo."""
    panel = PanelModelo(sesion_separada)
    assert not panel.boton.enabled  # el NaN de x1 está en train o en test
    assert "preprocesado" in panel.aviso.text

    sesion_separada.aplicar_preprocesado("media")
    assert panel.boton.enabled

    panel.crear()

    assert avisos[-1] == ("Modelo creado correctamente.", "positive")
    assert sesion_separada.modelo.features == ("x1", "x2")
    assert panel.resultados.visible
    assert panel.formula.text.startswith("y = ")
    assert "R²" in panel.metricas["test"][0].text


# =============================================================================
# Se actualiza solo con la sesión
# =============================================================================


def test_se_habilita_solo_al_separar():
    sesion = crear_sesion(separar=False)
    panel = PanelModelo(sesion)
    assert not panel.boton.enabled

    df = datos_lineales()
    sesion.guardar_separacion(df.iloc[:15], df.iloc[15:], 20, 42)

    assert panel.boton.enabled


def test_volver_a_separar_oculta_el_modelo(sesion_lista):
    panel = PanelModelo(sesion_lista)
    panel.crear()
    df = datos_lineales()

    sesion_lista.guardar_separacion(df.iloc[:10], df.iloc[10:], 50, 1)

    assert sesion_lista.modelo is None
    assert not panel.resultados.visible
    assert panel.boton.enabled


def test_aplicar_preprocesado_oculta_el_modelo(sesion_lista):
    panel = PanelModelo(sesion_lista)
    panel.crear()

    sesion_lista.aplicar_preprocesado("media")

    assert sesion_lista.modelo is None
    assert not panel.resultados.visible


def test_dataset_nuevo_oculta_el_modelo(sesion_lista):
    panel = PanelModelo(sesion_lista)
    panel.crear()

    sesion_lista.cargar_dataset(datos_lineales(), "otro.csv")

    assert not panel.resultados.visible
    assert "selección" in panel.aviso.text


def test_al_recargar_la_pagina_se_ve_el_modelo(sesion_lista):
    sesion_lista.crear_modelo()

    panel = PanelModelo(sesion_lista)

    assert panel.resultados.visible
    assert panel.formula.text == "y = 2.0000 * x1 - 3.0000 * x2 + 5.0000"


def test_no_contiene_logica_del_modelo():
    import sikorius.gui.paneles.panel_modelo as panel

    codigo = inspect.getsource(panel)
    for llamada in ("formula_texto(", "metricas_modelo(", "datos_ajuste("):
        assert llamada in codigo
    for prohibido in ("lstsq", "polyfit", "numpy", "np.", "mean("):
        assert prohibido not in codigo


# =============================================================================
# Descripción del modelo
# =============================================================================


def test_sin_modelo_no_se_puede_describir(sesion_lista):
    panel = PanelModelo(sesion_lista)
    assert not panel.resultados.visible  # el campo está dentro de resultados


def test_con_modelo_aparece_el_campo_opcional(sesion_lista):
    panel = PanelModelo(sesion_lista)
    panel.crear()
    assert panel.resultados.visible
    assert isinstance(panel.descripcion, ui.textarea)
    assert panel.descripcion.props["label"] == "Descripción (opcional)"
    assert panel.descripcion.value == ""


def test_lo_escrito_se_guarda_en_el_modelo(sesion_lista):
    panel = PanelModelo(sesion_lista)
    panel.crear()

    panel.descripcion.set_value("Precio de las casas")

    assert sesion_lista.modelo.descripcion == "Precio de las casas"


def test_cada_cambio_queda_reflejado(sesion_lista):
    panel = PanelModelo(sesion_lista)
    panel.crear()
    for texto in ("P", "Pr", "Pre", "Pre\nsio"):
        panel.descripcion.set_value(texto)
        assert sesion_lista.modelo.descripcion == texto


def test_se_puede_borrar_la_descripcion(sesion_lista):
    panel = PanelModelo(sesion_lista)
    panel.crear()
    panel.descripcion.set_value("algo")
    panel.descripcion.set_value("")
    assert sesion_lista.modelo.descripcion == ""


def test_crear_otro_modelo_vacia_el_campo(sesion_lista):
    panel = PanelModelo(sesion_lista)
    panel.crear()
    panel.descripcion.set_value("descripción del primero")
    primero = sesion_lista.modelo

    panel.crear()

    assert sesion_lista.modelo is not primero
    assert panel.descripcion.value == ""
    assert sesion_lista.modelo.descripcion == ""
    assert primero.descripcion == "descripción del primero"


def test_el_modelo_nuevo_no_hereda_la_descripcion_tras_preprocesar(
    sesion_lista,
):
    panel = PanelModelo(sesion_lista)
    panel.crear()
    panel.descripcion.set_value("texto")

    sesion_lista.aplicar_preprocesado("media")  # borra el modelo
    assert not panel.resultados.visible
    panel.crear()

    assert panel.descripcion.value == ""


def test_al_recargar_la_pagina_se_ve_la_descripcion(sesion_lista):
    sesion_lista.crear_modelo()
    sesion_lista.guardar_descripcion("Descripción guardada")

    panel = PanelModelo(sesion_lista)

    assert panel.descripcion.value == "Descripción guardada"


def test_otros_avisos_no_pisan_lo_que_se_escribe(sesion_lista):
    panel = PanelModelo(sesion_lista)
    panel.crear()
    panel.descripcion.set_value("lo que escribo")

    panel.actualizar()  # la sesión avisa por otro motivo

    assert panel.descripcion.value == "lo que escribo"
    assert sesion_lista.modelo.descripcion == "lo que escribo"