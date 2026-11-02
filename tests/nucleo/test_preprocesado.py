"""Pruebas del preprocesado de los datos antes de crear el modelo (#110, #111).

    uv run pytest tests/nucleo/test_preprocesado.py -v

Bloques:
    - Constantes y jerarquía de errores.
    - normalizar_espacios_vacios: celdas vacías o con espacios pasan a NaN.
    - detectar_nulos / quedan_nulos / detectar_nulos_conjuntos / hay_nulos.
    - interpretar_constante: números válidos ("2,5", " 3 "...) y errores.
    - aplicar_preprocesado: las cuatro estrategias, resumen y errores.
    - texto_resumen: mensaje que se muestra al usuario.
"""

import numpy as np
import pandas as pd
import pytest

from sikorius.nucleo.preprocesado import (
    CONSTANTE,
    ELIMINAR,
    ESTRATEGIAS,
    MEDIA,
    MEDIANA,
    AvisoPreprocesado,
    ColumnasNoEncontradasError,
    ErrorPreprocesado,
    aplicar_preprocesado,
    detectar_nulos,
    detectar_nulos_conjuntos,
    hay_nulos,
    interpretar_constante,
    normalizar_espacios_vacios,
    quedan_nulos,
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


# =============================================================================
# Constantes y errores
# =============================================================================


def test_estrategias_disponibles():
    assert ESTRATEGIAS == ("eliminar", "media", "mediana", "constante")
    assert (ELIMINAR, MEDIA, MEDIANA, CONSTANTE) == ESTRATEGIAS


def test_jerarquia_de_errores():
    """La GUI captura ErrorPreprocesado: los demás errores deben heredar
    de él."""
    assert issubclass(AvisoPreprocesado, ErrorPreprocesado)
    assert issubclass(ColumnasNoEncontradasError, ErrorPreprocesado)
    assert issubclass(ColumnasNoEncontradasError, ValueError)


# =============================================================================
# normalizar_espacios_vacios
# =============================================================================


@pytest.mark.parametrize("vacio", ["", " ", "   ", "\t", "\n", " \t "])
def test_normalizar_celdas_vacias_pasan_a_nan(vacio):
    df = pd.DataFrame({"a": [1.0, vacio, 3.0]})
    resultado = normalizar_espacios_vacios(df, ["a"])
    assert pd.isna(resultado.at[1, "a"])
    assert resultado.at[0, "a"] == 1.0
    assert resultado.at[2, "a"] == 3.0


def test_normalizar_no_toca_textos_con_contenido():
    df = pd.DataFrame({"a": ["0", " x ", "nan"]})
    resultado = normalizar_espacios_vacios(df, ["a"])
    assert resultado["a"].tolist() == ["0", " x ", "nan"]


def test_normalizar_solo_columnas_indicadas():
    df = pd.DataFrame({"a": [""], "b": [""]})
    resultado = normalizar_espacios_vacios(df, ["a"])
    assert pd.isna(resultado.at[0, "a"])
    assert resultado.at[0, "b"] == ""


def test_normalizar_no_modifica_el_original():
    df = crear_train()
    copia = df.copy()
    normalizar_espacios_vacios(df, COLUMNAS)
    pd.testing.assert_frame_equal(df, copia)


def test_normalizar_columna_inexistente():
    with pytest.raises(ColumnasNoEncontradasError, match="no_existe"):
        normalizar_espacios_vacios(crear_train(), ["x", "no_existe"])


# =============================================================================
# detectar_nulos y relacionadas
# =============================================================================


def test_detectar_cuenta_nan_none_y_vacios():
    df = pd.DataFrame(
        {
            "nan": [np.nan, 1.0, np.nan],
            "none": [None, "a", "b"],
            "vacios": ["", "  ", "c"],
            "llena": [1, 2, 3],
        }
    )
    assert detectar_nulos(df, list(df.columns)) == {
        "nan": 2,
        "none": 1,
        "vacios": 2,
        "llena": 0,
    }


def test_detectar_solo_columnas_indicadas():
    assert detectar_nulos(crear_train(), ["x"]) == {"x": 1}


def test_detectar_dataframe_sin_filas():
    df = pd.DataFrame({"x": pd.Series([], dtype=float)})
    assert detectar_nulos(df, ["x"]) == {"x": 0}


def test_detectar_cabecera_no_texto():
    df = pd.DataFrame({2020: [1.0, np.nan]})
    assert detectar_nulos(df, [2020]) == {2020: 1}


def test_detectar_columnas_inexistentes_las_nombra_todas():
    with pytest.raises(ColumnasNoEncontradasError) as error:
        detectar_nulos(crear_train(), ["a", "x", "b"])
    assert "a, b" in str(error.value)


@pytest.mark.parametrize(
    "columnas, esperado",
    [
        (["x"], True),
        (["y"], True),
        (["x", "y"], True),
        (("x", "y"), True),
        ([], False),
    ],
)
def test_quedan_nulos(columnas, esperado):
    assert quedan_nulos(crear_train(), columnas) is esperado


def test_quedan_nulos_sin_valores_inexistentes():
    df = pd.DataFrame({"x": [1.0, 2.0], "y": ["a", "b"]})
    assert quedan_nulos(df, ["x", "y"]) is False


def test_detectar_conjuntos_por_separado():
    deteccion = detectar_nulos_conjuntos(
        crear_train(), crear_test(), ("x", "y")
    )
    assert deteccion == {
        "train": {"x": 1, "y": 1},
        "test": {"x": 1, "y": 0},
    }


@pytest.mark.parametrize(
    "deteccion, esperado",
    [
        ({"train": {"x": 0}, "test": {"x": 0}}, False),
        ({"train": {"x": 1}, "test": {"x": 0}}, True),
        ({"train": {"x": 0}, "test": {"x": 0, "y": 3}}, True),
        ({"train": {}, "test": {}}, False),
    ],
)
def test_hay_nulos(deteccion, esperado):
    assert hay_nulos(deteccion) is esperado


# =============================================================================
# interpretar_constante
# =============================================================================


@pytest.mark.parametrize(
    "valor, esperado",
    [
        (0, 0.0),
        (3, 3.0),
        (-1, -1.0),
        (2.5, 2.5),
        ("3", 3.0),
        ("2.5", 2.5),
        ("2,5", 2.5),
        ("  4  ", 4.0),
        ("-0,75", -0.75),
        ("1e3", 1000.0),
        (np.int64(7), 7.0),
        (np.float64(1.5), 1.5),
    ],
)
def test_constante_valida(valor, esperado):
    resultado = interpretar_constante(valor)
    assert resultado == esperado
    assert isinstance(resultado, float)


@pytest.mark.parametrize(
    "valor",
    [
        None,
        True,
        False,
        "",
        "   ",
        "abc",
        "2,5,1",
        "3 €",
        "nan",
        "inf",
        "-inf",
        float("nan"),
        float("inf"),
        [1],
        {},
    ],
)
def test_constante_no_valida(valor):
    with pytest.raises(ErrorPreprocesado, match="debe ser un número"):
        interpretar_constante(valor)


# =============================================================================
# aplicar_preprocesado · eliminar
# =============================================================================


def test_eliminar_quita_filas_con_nulos_en_columnas_seleccionadas():
    train, test, resumen = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, ELIMINAR
    )
    assert train.index.tolist() == [10, 13]  # 11 (NaN) y 12 ("  ") fuera
    assert test.index.tolist() == [21]
    assert resumen == {
        "train": {"filas_eliminadas": 2, "valores_rellenados": 0},
        "test": {"filas_eliminadas": 1, "valores_rellenados": 0},
    }


def test_eliminar_ignora_nulos_de_columnas_no_seleccionadas():
    """La fila 10 tiene NaN en 'otra', pero 'otra' no está seleccionada."""
    train, _, _ = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, ELIMINAR
    )
    assert 10 in train.index
    assert pd.isna(train.at[10, "otra"])


def test_eliminar_sin_nulos_no_cambia_nada():
    train = pd.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0]})
    test = pd.DataFrame({"x": [5.0], "y": [6.0]})
    train_p, test_p, resumen = aplicar_preprocesado(
        train, test, COLUMNAS, ELIMINAR
    )
    pd.testing.assert_frame_equal(train_p, train)
    pd.testing.assert_frame_equal(test_p, test)
    assert resumen["train"]["filas_eliminadas"] == 0
    assert resumen["test"]["filas_eliminadas"] == 0


@pytest.mark.parametrize(
    "vacio, conjunto",
    [
        ("train", "entrenamiento"),
        ("test", "test"),
    ],
)
def test_eliminar_dejaria_un_conjunto_vacio(vacio, conjunto):
    lleno = pd.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0]})
    sin_datos = pd.DataFrame({"x": [np.nan, 1.0], "y": [1.0, ""]})
    train = sin_datos if vacio == "train" else lleno
    test = sin_datos if vacio == "test" else lleno
    with pytest.raises(AvisoPreprocesado) as error:
        aplicar_preprocesado(train, test, COLUMNAS, ELIMINAR)
    assert "conjunto de " + conjunto in str(error.value)


def test_eliminar_dejaria_los_dos_vacios():
    sin_datos = pd.DataFrame({"x": [np.nan], "y": [1.0]})
    with pytest.raises(AvisoPreprocesado, match="entrenamiento y el de test"):
        aplicar_preprocesado(sin_datos, sin_datos, COLUMNAS, ELIMINAR)


# =============================================================================
# aplicar_preprocesado · media, mediana y constante
# =============================================================================


def test_media_se_calcula_solo_con_entrenamiento():
    """El test se rellena con la media de train (x = 3), no con la suya, para
    no filtrar información del conjunto de test al modelo."""
    train, test, _ = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, MEDIA
    )
    media_x = (1.0 + 3.0 + 5.0) / 3
    media_y = (10.0 + 20.0 + 40.0) / 3
    assert train.at[11, "x"] == media_x
    assert train.at[12, "y"] == media_y
    assert test.at[20, "x"] == media_x
    assert test.at[21, "x"] == 100.0  # los valores reales se conservan


def test_mediana_se_calcula_solo_con_entrenamiento():
    train = pd.DataFrame({"x": [1.0, 2.0, 100.0, np.nan], "y": [1.0] * 4})
    test = pd.DataFrame({"x": [np.nan, 50.0], "y": [1.0, 1.0]})
    train_p, test_p, _ = aplicar_preprocesado(train, test, COLUMNAS, MEDIANA)
    assert train_p.at[3, "x"] == 2.0
    assert test_p.at[0, "x"] == 2.0


@pytest.mark.parametrize(
    "constante, esperado",
    [
        (0, 0.0),
        (-3, -3.0),
        ("2,5", 2.5),
        (" 7 ", 7.0),
    ],
)
def test_constante_rellena_con_el_valor(constante, esperado):
    train, test, _ = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, CONSTANTE, constante
    )
    assert train.at[11, "x"] == esperado
    assert train.at[12, "y"] == esperado
    assert test.at[20, "x"] == esperado


@pytest.mark.parametrize("estrategia", [MEDIA, MEDIANA, CONSTANTE])
def test_rellenar_resumen_y_sin_nulos(estrategia):
    train, test, resumen = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, estrategia, 0
    )
    assert resumen == {
        "train": {"filas_eliminadas": 0, "valores_rellenados": 2},
        "test": {"filas_eliminadas": 0, "valores_rellenados": 1},
    }
    assert not quedan_nulos(train, COLUMNAS)
    assert not quedan_nulos(test, COLUMNAS)
    assert len(train) == 4 and len(test) == 2  # no se quita ninguna fila


@pytest.mark.parametrize("estrategia", [MEDIA, MEDIANA, CONSTANTE])
def test_rellenar_no_toca_columnas_no_seleccionadas(estrategia):
    train, test, _ = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, estrategia, 0
    )
    assert pd.isna(train.at[10, "otra"])
    assert test["otra"].isna().all()


@pytest.mark.parametrize("estrategia", [MEDIA, MEDIANA])
def test_rellenar_columna_sin_valores_en_entrenamiento(estrategia):
    train = pd.DataFrame({"x": [np.nan, np.nan], "y": [1.0, 2.0]})
    test = pd.DataFrame({"x": [5.0], "y": [3.0]})
    with pytest.raises(ErrorPreprocesado) as error:
        aplicar_preprocesado(train, test, COLUMNAS, estrategia)
    texto = str(error.value)
    assert "No se puede calcular la " + estrategia + " de x" in texto
    assert not isinstance(error.value, AvisoPreprocesado)


@pytest.mark.parametrize("constante", [None, "", "abc", float("nan")])
def test_constante_no_numerica(constante):
    with pytest.raises(ErrorPreprocesado, match="debe ser un número"):
        aplicar_preprocesado(
            crear_train(), crear_test(), COLUMNAS, CONSTANTE, constante
        )


# =============================================================================
# aplicar_preprocesado · comunes
# =============================================================================


@pytest.mark.parametrize("estrategia", ["", "borrar", "Media", None, "MEDIA"])
def test_estrategia_no_valida(estrategia):
    with pytest.raises(ErrorPreprocesado, match="Estrategia no válida"):
        aplicar_preprocesado(crear_train(), crear_test(), COLUMNAS, estrategia)


@pytest.mark.parametrize("estrategia", ESTRATEGIAS)
def test_no_modifica_los_conjuntos_originales(estrategia):
    train, test = crear_train(), crear_test()
    copia_train, copia_test = train.copy(), test.copy()
    aplicar_preprocesado(train, test, COLUMNAS, estrategia, 1)
    pd.testing.assert_frame_equal(train, copia_train)
    pd.testing.assert_frame_equal(test, copia_test)


@pytest.mark.parametrize("estrategia", ESTRATEGIAS)
def test_columna_inexistente(estrategia):
    with pytest.raises(ColumnasNoEncontradasError):
        aplicar_preprocesado(
            crear_train(), crear_test(), ["x", "z"], estrategia, 1
        )


@pytest.mark.parametrize("estrategia", ESTRATEGIAS)
def test_acepta_columnas_como_tupla(estrategia):
    train, _, _ = aplicar_preprocesado(
        crear_train(), crear_test(), ("x", "y"), estrategia, 1
    )
    assert not quedan_nulos(train, COLUMNAS)


def test_conserva_columnas_e_indice():
    train, test, _ = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, MEDIA
    )
    assert list(train.columns) == ["x", "y", "otra"]
    assert train.index.tolist() == [10, 11, 12, 13]
    assert test.index.tolist() == [20, 21]


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


def test_texto_resumen_con_resultado_real():
    _, _, resumen = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, MEDIA
    )
    texto = texto_resumen(resumen)
    assert "Entrenamiento: 0 filas eliminadas, 2 valores rellenados" in texto
    assert "Test: 0 filas eliminadas, 1 valores rellenados" in texto
