"""Pruebas del catálogo de cambios del asistente.

uv run pytest tests/dominio/test_transformaciones.py -v
"""

import numpy as np
import pandas as pd
import pytest

from sikorius.dominio.errores import ErrorTransformacion
from sikorius.dominio.transformaciones import (
    Operacion,
    aplicar_operacion,
    aplicar_operaciones,
)


def op(tipo, columna=None, operador=None, valor=None, nombre_nuevo=None):
    return Operacion(
        tipo=tipo,
        columna=columna,
        operador=operador,
        valor=valor,
        nombre_nuevo=nombre_nuevo,
    )


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "precio": [100.0, 200.0, 600.0, np.nan, 200.0],
            "ciudad": ["Coruña", "Lugo", "Coruña", "Vigo", "Lugo"],
            "m2": ["50", "70,5", "x", "40", "70,5"],
        }
    )


def test_no_modifica_el_original(df):
    copia = df.copy()
    aplicar_operacion(df, op("eliminar_columna", "precio"))
    pd.testing.assert_frame_equal(df, copia)


def test_eliminar_columna(df):
    datos, texto = aplicar_operacion(df, op("eliminar_columna", "ciudad"))
    assert list(datos.columns) == ["precio", "m2"]
    assert "ciudad" in texto


def test_eliminar_la_unica_columna_falla():
    with pytest.raises(ErrorTransformacion):
        aplicar_operacion(
            pd.DataFrame({"a": [1]}), op("eliminar_columna", "a")
        )


def test_columna_inexistente(df):
    with pytest.raises(ErrorTransformacion, match="No existe"):
        aplicar_operacion(df, op("eliminar_columna", "nada"))


def test_columna_que_no_es_texto():
    df = pd.DataFrame({2020: [1.0, 2.0], "y": [3.0, 4.0]})
    datos, _ = aplicar_operacion(df, op("eliminar_columna", "2020"))
    assert list(datos.columns) == ["y"]


def test_renombrar(df):
    datos, _ = aplicar_operacion(
        df, op("renombrar_columna", "m2", nombre_nuevo="superficie")
    )
    assert "superficie" in datos.columns


def test_renombrar_a_un_nombre_que_ya_existe(df):
    with pytest.raises(ErrorTransformacion, match="Ya hay"):
        aplicar_operacion(
            df, op("renombrar_columna", "m2", nombre_nuevo="precio")
        )


def test_renombrar_sin_nombre(df):
    with pytest.raises(ErrorTransformacion):
        aplicar_operacion(df, op("renombrar_columna", "m2", nombre_nuevo=""))


def test_eliminar_nulos_de_una_columna(df):
    datos, texto = aplicar_operacion(
        df, op("eliminar_filas_con_nulos", "precio")
    )
    assert len(datos) == 4
    assert "se elimina 1 fila" in texto


def test_eliminar_nulos_de_todas():
    df = pd.DataFrame({"a": [1.0, None, 3.0], "b": ["x", "y", " "]})
    datos, _ = aplicar_operacion(df, op("eliminar_filas_con_nulos"))
    assert len(datos) == 1


def test_filtrar_numerico(df):
    datos, texto = aplicar_operacion(
        df, op("filtrar_filas", "precio", "<=", "500")
    )
    assert datos["precio"].tolist() == [100.0, 200.0, 200.0]
    assert "se eliminan 2 filas" in texto


def test_filtrar_numeros_guardados_como_texto(df):
    datos, _ = aplicar_operacion(df, op("filtrar_filas", "m2", ">", "60"))
    assert datos["m2"].tolist() == ["70,5", "70,5"]


@pytest.mark.parametrize(
    "operador, esperado",
    [("<", 1), ("<=", 3), (">", 1), (">=", 3), ("==", 2), ("!=", 2)],
)
def test_todos_los_operadores(df, operador, esperado):
    datos, _ = aplicar_operacion(
        df, op("filtrar_filas", "precio", operador, "200")
    )
    assert len(datos) == esperado


def test_filtrar_texto(df):
    datos, _ = aplicar_operacion(
        df, op("filtrar_filas", "ciudad", "==", "Coruña")
    )
    assert len(datos) == 2


def test_filtrar_texto_con_menor_que_falla(df):
    with pytest.raises(ErrorTransformacion, match="no es numérica"):
        aplicar_operacion(df, op("filtrar_filas", "ciudad", "<", "Lugo"))


def test_filtrar_sin_operador_o_valor(df):
    with pytest.raises(ErrorTransformacion):
        aplicar_operacion(df, op("filtrar_filas", "precio", None, "1"))
    with pytest.raises(ErrorTransformacion):
        aplicar_operacion(df, op("filtrar_filas", "precio", "<", " "))


def test_eliminar_duplicados(df):
    datos, _ = aplicar_operacion(df, op("eliminar_duplicados"))
    assert len(datos) == 4
    datos, _ = aplicar_operacion(df, op("eliminar_duplicados", "ciudad"))
    assert len(datos) == 3


def test_quitar_atipicos():
    df = pd.DataFrame({"x": [10.0, 11.0, 12.0, 11.0, 10.0, 1000.0, None]})
    datos, texto = aplicar_operacion(df, op("quitar_atipicos", "x"))
    assert 1000.0 not in datos["x"].tolist()
    assert len(datos) == 6  # el nulo se queda
    assert "rango intercuartílico" in texto


def test_quitar_atipicos_sin_numeros(df):
    with pytest.raises(ErrorTransformacion):
        aplicar_operacion(df, op("quitar_atipicos", "ciudad"))


def test_convertir_a_numero(df):
    datos, texto = aplicar_operacion(df, op("convertir_a_numero", "m2"))
    assert datos["m2"].tolist()[:2] == [50.0, 70.5]
    assert np.isnan(datos["m2"].iloc[2])
    assert "1 valores" in texto


def test_varias_operaciones_en_orden(df):
    datos, textos = aplicar_operaciones(
        df,
        [
            op("eliminar_filas_con_nulos", "precio"),
            op("filtrar_filas", "precio", "<", "500"),
            op("eliminar_columna", "m2"),
        ],
    )
    assert len(textos) == 3
    assert list(datos.index) == [0, 1, 2]
    assert list(datos.columns) == ["precio", "ciudad"]


def test_si_una_falla_dice_cual(df):
    with pytest.raises(ErrorTransformacion, match="Cambio 2"):
        aplicar_operaciones(
            df,
            [op("eliminar_duplicados"), op("eliminar_columna", "nada")],
        )


def test_no_se_puede_quedar_sin_filas(df):
    with pytest.raises(ErrorTransformacion, match="sin filas"):
        aplicar_operaciones(df, [op("filtrar_filas", "precio", ">", "1e9")])
