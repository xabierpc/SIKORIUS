"""Pruebas de la SALIDA del modelo (columna de salida o target).

Prueba la parte de salida de ``src/sikorius/datos-entrada-y-salida.py``:

- ``SelectorTarget``: elección de la columna de salida, sin poder repetir
  una columna de entrada.
- En ``pagina_principal``: la elección del target y la confirmación de la
  selección (que usa ``validacion.validar_seleccion``).

Las utilidades compartidas con test_entrada.py están en ``conftest.py``.

Los tests marcados con ``xfail(strict=True)`` documentan FALLOS REALES del
código actual: hoy fallan a propósito. Cuando se corrija el fallo, pytest
avisará con XPASS(strict) y habrá que quitar el marcador.

Ejecución:
    uv run pytest test/test_salida.py -v
"""

import ast
import builtins
import inspect
import sqlite3

import pandas as pd
import pytest

from conftest import (
    COLUMNAS, RUTA_MODULO, ArchivoSubido, EventoSubida, bytes_csv,
    bytes_sqlite, bytes_xlsx, desplegar, ejecutar, modulo,
    oyentes_al_desplegar,
)
from sikorius.importador import ErrorImportacion

SelectorFeatures = modulo.SelectorFeatures
SelectorTarget = modulo.SelectorTarget
importar_archivo_subido = modulo.importar_archivo_subido


# =============================================================================
# Estructura de SelectorTarget
# =============================================================================

def test_metodos_publicos():
    for metodo in ["cargar_columnas", "excluir", "obtener_seleccion"]:
        assert callable(getattr(SelectorTarget, metodo, None)), metodo
        assert getattr(SelectorTarget, metodo).__doc__, metodo


def test_docstring_de_selector_target_no_esta_copiado():
    """El docstring de SelectorTarget habla de la columna de salida."""
    assert "salida" in SelectorTarget.__doc__.lower()


def test_docstring_de_selector_target_empieza_bien():
    assert "entrada (features)" not in SelectorTarget.__doc__.split("\n\n")[0]


# =============================================================================
# SelectorTarget
# =============================================================================

def test_target_empieza_vacio_y_deshabilitado():
    target = SelectorTarget()
    assert target.columnas == [] and target.excluidas == []
    assert target.selector.value is None
    assert target.obtener_seleccion() is None
    assert not target.selector.enabled


def test_target_es_seleccion_simple():
    target = SelectorTarget()
    assert not target.selector.props.get("multiple")
    assert target.selector.props["label"] == "Target (columna de salida)"
    assert target.selector.props["clearable"] is True


def test_target_cargar_columnas(datos):
    target = SelectorTarget()
    target.cargar_columnas(datos)
    assert target.selector.options == COLUMNAS
    assert target.selector.enabled


def test_target_seleccion(datos):
    target = SelectorTarget()
    target.cargar_columnas(datos)
    target.selector.set_value("precio")
    assert target.obtener_seleccion() == "precio"


def test_target_cargar_otro_dataset_limpia_seleccion_y_exclusiones(datos):
    target = SelectorTarget()
    target.cargar_columnas(datos)
    target.excluir(["superficie"])
    target.selector.set_value("precio")
    target.cargar_columnas(pd.DataFrame({"superficie": [1], "z": [2]}))
    assert target.excluidas == []
    assert target.selector.options == ["superficie", "z"]
    assert target.obtener_seleccion() is None


def test_target_cargar_dataset_sin_columnas_deshabilita(datos):
    target = SelectorTarget()
    target.cargar_columnas(datos)
    target.cargar_columnas(pd.DataFrame())
    assert not target.selector.enabled


def test_target_excluir_quita_opciones(datos):
    target = SelectorTarget()
    target.cargar_columnas(datos)
    target.excluir(["superficie", "habitaciones"])
    assert target.selector.options == ["barrio", "precio"]
    assert target.columnas == COLUMNAS     # las columnas no se pierden


def test_target_excluir_la_columna_elegida_la_deselecciona(datos):
    target = SelectorTarget()
    target.cargar_columnas(datos)
    target.selector.set_value("superficie")
    target.excluir(["superficie"])
    assert target.obtener_seleccion() is None
    assert "superficie" not in target.selector.options


def test_target_excluir_otra_columna_conserva_la_seleccion(datos):
    target = SelectorTarget()
    target.cargar_columnas(datos)
    target.selector.set_value("precio")
    target.excluir(["superficie"])
    assert target.obtener_seleccion() == "precio"


def test_target_excluir_no_acumula(datos):
    """Cada llamada sustituye las exclusiones anteriores."""
    target = SelectorTarget()
    target.cargar_columnas(datos)
    target.excluir(["superficie"])
    target.excluir(["habitaciones"])
    assert target.selector.options == ["superficie", "barrio", "precio"]
    target.excluir([])
    assert target.selector.options == COLUMNAS


def test_target_excluir_todas(datos):
    target = SelectorTarget()
    target.cargar_columnas(datos)
    target.excluir(COLUMNAS)
    assert target.selector.options == []


def test_target_excluir_columnas_inexistentes(datos):
    target = SelectorTarget()
    target.cargar_columnas(datos)
    target.excluir(["no_existe"])
    assert target.selector.options == COLUMNAS


def test_target_excluir_antes_de_cargar():
    target = SelectorTarget()
    target.excluir(["a"])
    assert target.selector.options == []


@pytest.mark.parametrize("columnas", [("superficie",), {"superficie"},
                                      iter(["superficie"])])
def test_target_excluir_acepta_cualquier_iterable(datos, columnas):
    target = SelectorTarget()
    target.cargar_columnas(datos)
    target.excluir(columnas)
    assert "superficie" not in target.selector.options


def test_target_excluir_no_guarda_la_lista_del_que_llama(datos):
    target = SelectorTarget()
    target.cargar_columnas(datos)
    features = ["superficie"]
    target.excluir(features)
    features.append("precio")
    assert target.excluidas == ["superficie"]


def test_target_sin_al_abrir_no_registra_evento():
    con = len(oyentes_al_desplegar(SelectorTarget(al_abrir=lambda: None).selector))
    sin = len(oyentes_al_desplegar(SelectorTarget().selector))
    assert con == sin + 1


def test_target_al_abrir_se_llama_al_desplegar(datos):
    llamadas = []
    target = SelectorTarget(al_abrir=lambda: llamadas.append(1))
    target.cargar_columnas(datos)   # se reconstruye el selector
    desplegar(target.selector)
    assert llamadas == [1]


# =============================================================================
# pagina_principal: columna de salida y confirmación
# =============================================================================

def test_confirmar_sin_elegir_nada(pagina_con_datos):
    texto, kw = pagina_con_datos.confirmar()
    assert "Falta seleccionar" in texto
    assert "features" in texto and "target" in texto
    assert kw["type"] == "negative"


def test_confirmar_sin_target(pagina_con_datos):
    pagina_con_datos.features.set_value(["superficie"])
    texto, _ = pagina_con_datos.confirmar()
    assert "Falta seleccionar la columna de salida" in texto


def test_confirmar_seleccion_correcta_multiple(pagina_con_datos):
    pagina = pagina_con_datos
    pagina.features.set_value(["superficie", "habitaciones"])
    pagina.abrir_target()
    pagina.target.set_value("precio")
    texto, kw = pagina.confirmar()
    assert kw["type"] == "positive"
    assert texto == ("Selección confirmada. Entrada: superficie, "
                     "habitaciones | Salida: precio")


def test_al_abrir_target_se_excluyen_las_features(pagina_con_datos):
    pagina = pagina_con_datos
    pagina.features.set_value(["superficie", "habitaciones"])
    pagina.abrir_target()
    assert pagina.target.options == ["barrio", "precio"]


def test_target_elegido_y_luego_como_feature_se_rechaza(pagina_con_datos):
    """Si se elige el target antes que las features, nada impide elegir la
    misma columna como feature; la validación lo tiene que parar."""
    pagina = pagina_con_datos
    pagina.target.set_value("precio")
    pagina.features.set_value(["precio", "superficie"])
    texto, kw = pagina.confirmar()
    assert "no puede ser entrada y salida a la vez" in texto
    assert kw["type"] == "negative"


def test_al_reabrir_target_se_quita_si_ya_es_feature(pagina_con_datos):
    pagina = pagina_con_datos
    pagina.target.set_value("precio")
    pagina.features.set_value(["precio"])
    pagina.abrir_target()
    assert pagina.target.value is None


@pytest.mark.parametrize("features, target", [
    (["barrio"], "precio"),
    (["superficie"], "barrio"),
])
def test_confirmar_columna_no_numerica(pagina_con_datos, features, target):
    pagina = pagina_con_datos
    pagina.features.set_value(features)
    pagina.target.set_value(target)
    texto, kw = pagina.confirmar()
    assert "no son numéricas" in texto and "barrio" in texto
    assert kw["type"] == "negative"


def test_confirmar_con_nombres_de_columna_numericos(pagina, tmp_path):
    df = pd.DataFrame({2023: [1.0, 2.0], 2024: [3.0, 4.0]})
    pagina.subir("anios.xlsx", bytes_xlsx(df, tmp_path))
    pagina.features.set_value(["2023"])
    pagina.target.set_value("2024")
    _, kw = pagina.confirmar()
    assert kw["type"] == "positive"


def test_cargar_otro_dataset_limpia_las_dos_selecciones(pagina_con_datos):
    pagina = pagina_con_datos
    pagina.features.set_value(["superficie"])
    pagina.target.set_value("precio")
    pagina.subir("otro.csv", b"x,y\n1,2\n3,4\n")
    assert pagina.features.options == ["x", "y"]
    assert pagina.features.value == []
    assert pagina.target.value is None
    texto, _ = pagina.confirmar()
    assert "Falta seleccionar" in texto


def test_confirmar_con_seleccion_del_dataset_anterior_falla(pagina_con_datos):
    """Aunque el valor viejo siguiera en el selector, la validación usa el
    dataset nuevo y avisa de que la columna no existe."""
    pagina = pagina_con_datos
    pagina.subir("otro.csv", b"x,y\n1,2\n3,4\n")
    pagina.features.options.append("superficie")
    pagina.features.set_value(["superficie"])
    pagina.target.set_value("y")
    texto, _ = pagina.confirmar()
    assert "no existen" in texto and "superficie" in texto
