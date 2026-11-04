"""Pruebas de los selectores de columnas, sin servidor (#11).

Prueban el componente directamente, sin pasar por el panel. Los tests de
los selectores que antes estaban en test_entrada.py y test_salida.py (que
probaban la demo de selección de columnas) están ahora aquí.

    uv run pytest tests/gui/test_selectores.py -v
"""

import inspect

import pandas as pd
import pytest

from sikorius.gui.componentes.selectores import (
    SelectorFeatures,
    SelectorTarget,
)

COLUMNAS = ["superficie", "habitaciones", "barrio", "precio"]


def datos():
    return pd.DataFrame(
        {"x1": [1, 2], "x2": [3, 4], 2020: [5, 6], "y": [7, 8]}
    )


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


def oyentes_al_desplegar(selector):
    """Manejadores del evento de abrir el desplegable de un ui.select."""
    return [
        e
        for e in selector._event_listeners.values()
        if e.type in ("popup-show", "popupShow")
    ]


def desplegar(selector):
    """Simula que el usuario abre el desplegable (lanza el último
    manejador)."""
    manejador = oyentes_al_desplegar(selector)[-1].handler
    if inspect.signature(manejador).parameters:
        manejador(None)
    else:
        manejador()


# =============================================================================
# SelectorFeatures
# =============================================================================


def test_features_sin_dataset_esta_deshabilitado():
    selector = SelectorFeatures()
    assert not selector.selector.enabled
    assert selector.obtener_seleccion() == []


def test_features_por_defecto_es_multiple_y_vacio():
    selector = SelectorFeatures()
    assert selector.columnas == []
    assert selector.selector.props["multiple"] is True
    assert selector.selector.value == []
    assert selector.obtener_seleccion() == []


def test_features_multiple_usa_chips_y_etiqueta():
    selector = SelectorFeatures()
    assert selector.selector.props.get("use-chips") is True
    assert selector.selector.props["label"] == "Features (selección múltiple)"


def test_features_no_tiene_modo_simple():
    """El tipo de regresión lo decide la sesión, no el selector."""
    assert not hasattr(SelectorFeatures, "SIMPLE")
    assert not hasattr(SelectorFeatures, "cambiar_tipo_regresion")
    with pytest.raises(TypeError):
        SelectorFeatures("simple")


def test_features_se_puede_borrar_la_seleccion():
    assert SelectorFeatures().selector.props["clearable"] is True


def test_features_muestra_las_columnas_como_texto():
    selector = SelectorFeatures()
    selector.cargar_columnas(datos())
    assert selector.selector.enabled
    assert selector.columnas == ["x1", "x2", "2020", "y"]


def test_features_cargar_columnas(casas):
    selector = SelectorFeatures()
    selector.cargar_columnas(casas)
    assert selector.columnas == COLUMNAS
    assert selector.selector.options == COLUMNAS
    assert selector.selector.enabled


def test_features_cargar_dataset_sin_columnas_deshabilita(casas):
    selector = SelectorFeatures()
    selector.cargar_columnas(casas)
    selector.cargar_columnas(pd.DataFrame())
    assert selector.columnas == []
    assert not selector.selector.enabled


def test_features_nombres_de_columna_que_no_son_texto():
    selector = SelectorFeatures()
    selector.cargar_columnas(
        pd.DataFrame([[1, 2, 3]], columns=[2024, 1.5, "x"])
    )
    assert selector.columnas == ["2024", "1.5", "x"]


def test_features_cargar_no_modifica_el_dataframe(casas):
    copia = casas.copy()
    SelectorFeatures().cargar_columnas(casas)
    pd.testing.assert_frame_equal(casas, copia)


def test_features_devuelve_siempre_una_lista():
    selector = SelectorFeatures()
    selector.cargar_columnas(datos())
    selector.selector.set_value(["x1", "2020"])
    assert selector.obtener_seleccion() == ["x1", "2020"]


def test_features_obtener_seleccion_devuelve_una_copia(casas):
    selector = SelectorFeatures()
    selector.cargar_columnas(casas)
    selector.selector.set_value(["superficie"])
    selector.obtener_seleccion().append("precio")
    assert selector.obtener_seleccion() == ["superficie"]


def test_features_borrar_la_seleccion(casas):
    selector = SelectorFeatures()
    selector.cargar_columnas(casas)
    selector.selector.set_value(["superficie"])
    selector.selector.set_value(None)  # la X de "clearable" deja None
    assert selector.obtener_seleccion() == []


def test_features_una_sola_columna_tambien_es_lista(casas):
    selector = SelectorFeatures()
    selector.cargar_columnas(casas)
    selector.selector.set_value(["superficie"])
    assert selector.obtener_seleccion() == ["superficie"]


def test_features_dataset_nuevo_limpia_la_seleccion():
    selector = SelectorFeatures()
    selector.cargar_columnas(datos())
    selector.selector.set_value(["x1"])
    selector.cargar_columnas(pd.DataFrame({"a": [1], "b": [2]}))
    assert selector.obtener_seleccion() == []
    assert selector.columnas == ["a", "b"]


def test_features_cargar_el_mismo_dataset_tambien_limpia(casas):
    selector = SelectorFeatures()
    selector.cargar_columnas(casas)
    selector.selector.set_value(["superficie"])
    selector.cargar_columnas(casas)
    assert selector.obtener_seleccion() == []


def test_features_recargar_no_deja_selectores_viejos(casas):
    selector = SelectorFeatures()
    for _ in range(5):
        selector.cargar_columnas(casas)
    hijos = list(selector.contenedor.default_slot.children)
    assert hijos == [selector.selector]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "FALLO E2 (limitación conocida): columnas que solo se distinguen "
        "por el "
        "tipo del nombre (1 y '1') salen repetidas en el selector y no se "
        "pueden elegir por separado, porque todo se pasa a texto."
    ),
)
def test_features_columnas_que_solo_difieren_en_el_tipo():
    selector = SelectorFeatures()
    selector.cargar_columnas(pd.DataFrame([[1, 2]], columns=[1, "1"]))
    assert len(set(selector.selector.options)) == 2


# =============================================================================
# SelectorTarget
# =============================================================================


def test_target_metodos_publicos_documentados():
    for metodo in ["cargar_columnas", "excluir", "obtener_seleccion"]:
        assert callable(getattr(SelectorTarget, metodo, None)), metodo
        assert getattr(SelectorTarget, metodo).__doc__, metodo


def test_target_docstring_habla_de_la_salida():
    primer_parrafo = SelectorTarget.__doc__.split("\n\n")[0]
    assert "salida" in SelectorTarget.__doc__.lower()
    assert "entrada (features)" not in primer_parrafo


def test_target_sin_dataset_esta_deshabilitado():
    selector = SelectorTarget()
    assert not selector.selector.enabled
    assert selector.obtener_seleccion() is None


def test_target_empieza_vacio():
    target = SelectorTarget()
    assert target.columnas == [] and target.excluidas == []
    assert target.selector.value is None


def test_target_es_seleccion_simple():
    target = SelectorTarget()
    assert not target.selector.props.get("multiple")
    assert target.selector.props["label"] == "Target (columna de salida)"
    assert target.selector.props["clearable"] is True


def test_target_cargar_columnas(casas):
    target = SelectorTarget()
    target.cargar_columnas(casas)
    assert target.selector.options == COLUMNAS
    assert target.selector.enabled


def test_target_seleccion(casas):
    target = SelectorTarget()
    target.cargar_columnas(casas)
    target.selector.set_value("precio")
    assert target.obtener_seleccion() == "precio"


def test_target_dataset_nuevo_quita_las_exclusiones():
    selector = SelectorTarget()
    selector.cargar_columnas(datos())
    selector.excluir(["x1"])
    selector.cargar_columnas(datos())
    assert selector.selector.options == ["x1", "x2", "2020", "y"]


def test_target_cargar_otro_dataset_limpia_seleccion_y_exclusiones(casas):
    target = SelectorTarget()
    target.cargar_columnas(casas)
    target.excluir(["superficie"])
    target.selector.set_value("precio")
    target.cargar_columnas(pd.DataFrame({"superficie": [1], "z": [2]}))
    assert target.excluidas == []
    assert target.selector.options == ["superficie", "z"]
    assert target.obtener_seleccion() is None


def test_target_cargar_dataset_sin_columnas_deshabilita(casas):
    target = SelectorTarget()
    target.cargar_columnas(casas)
    target.cargar_columnas(pd.DataFrame())
    assert not target.selector.enabled


def test_target_excluye_las_features():
    selector = SelectorTarget()
    selector.cargar_columnas(datos())
    selector.excluir(["x1", "x2"])
    assert selector.selector.options == ["2020", "y"]
    # las columnas no se pierden: solo se ocultan
    assert selector.columnas == ["x1", "x2", "2020", "y"]


def test_target_excluido_se_deselecciona():
    selector = SelectorTarget()
    selector.cargar_columnas(datos())
    selector.selector.set_value("x1")
    selector.excluir(["x1"])
    assert selector.obtener_seleccion() is None


def test_target_excluir_otra_columna_conserva_la_seleccion(casas):
    target = SelectorTarget()
    target.cargar_columnas(casas)
    target.selector.set_value("precio")
    target.excluir(["superficie"])
    assert target.obtener_seleccion() == "precio"


def test_target_excluir_no_acumula(casas):
    """Cada llamada sustituye las exclusiones anteriores."""
    target = SelectorTarget()
    target.cargar_columnas(casas)
    target.excluir(["superficie"])
    target.excluir(["habitaciones"])
    assert target.selector.options == ["superficie", "barrio", "precio"]
    target.excluir([])
    assert target.selector.options == COLUMNAS


def test_target_excluir_todas(casas):
    target = SelectorTarget()
    target.cargar_columnas(casas)
    target.excluir(COLUMNAS)
    assert target.selector.options == []


def test_target_excluir_columnas_inexistentes(casas):
    target = SelectorTarget()
    target.cargar_columnas(casas)
    target.excluir(["no_existe"])
    assert target.selector.options == COLUMNAS


def test_target_excluir_antes_de_cargar():
    target = SelectorTarget()
    target.excluir(["a"])
    assert target.selector.options == []


@pytest.mark.parametrize(
    "columnas", [("superficie",), {"superficie"}, iter(["superficie"])]
)
def test_target_excluir_acepta_cualquier_iterable(casas, columnas):
    target = SelectorTarget()
    target.cargar_columnas(casas)
    target.excluir(columnas)
    assert "superficie" not in target.selector.options


def test_target_excluir_no_guarda_la_lista_del_que_llama(casas):
    target = SelectorTarget()
    target.cargar_columnas(casas)
    features = ["superficie"]
    target.excluir(features)
    features.append("precio")
    assert target.excluidas == ["superficie"]


def test_target_sin_al_abrir_no_registra_evento():
    con = len(
        oyentes_al_desplegar(SelectorTarget(al_abrir=lambda: None).selector)
    )
    sin = len(oyentes_al_desplegar(SelectorTarget().selector))
    assert con == sin + 1


def test_target_al_abrir_se_llama_al_desplegar(casas):
    llamadas = []
    target = SelectorTarget(al_abrir=lambda: llamadas.append(1))
    target.cargar_columnas(casas)  # se reconstruye el selector
    desplegar(target.selector)
    assert llamadas == [1]
