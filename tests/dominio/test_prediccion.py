"""Tests de las predicciones con un modelo creado o cargado (#22).

    uv run pytest tests/dominio/test_prediccion.py -v

Bloques:
    - interpretar_valores: punto y coma decimal, valores que faltan y
      valores no numéricos.
    - predecir: coincide con el valor calculado a mano con la fórmula, y
      da lo mismo con el modelo creado que con el guardado y cargado.
    - texto_prediccion: formato "<salida> = <valor>" con los decimales de
      la fórmula.
"""

import numpy as np
import pandas as pd
import pytest

from sikorius.datos.persistencia import cargar_modelo, guardar_modelo
from sikorius.dominio.errores import ErrorPrediccion, ErrorSikorius
from sikorius.dominio.modelo import (
    DECIMALES_FORMULA,
    ModeloLineal,
    entrenar_modelo,
    metricas_modelo,
)
from sikorius.dominio.prediccion import (
    interpretar_valores,
    predecir,
    texto_prediccion,
)

# =============================================================================
# Utilidades
# =============================================================================


def datos_simples():
    """y = 2*x + 1, sin ruido."""
    return pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [3.0, 5.0, 7.0, 9.0]})


def datos_multiples(n=20, semilla=0):
    """precio = 1.5*metros - 4*antiguedad + 10, con un poco de ruido."""
    rng = np.random.default_rng(semilla)
    metros = rng.uniform(40, 150, n)
    antiguedad = rng.uniform(0, 50, n)
    ruido = rng.normal(0, 0.5, n)
    precio = 1.5 * metros - 4 * antiguedad + 10 + ruido
    return pd.DataFrame(
        {"metros": metros, "antiguedad": antiguedad, "precio": precio}
    )


def a_mano(modelo, valores):
    """Valor de la fórmula: suma de coeficiente * valor + independiente."""
    total = modelo.termino_independiente
    for coeficiente, columna in zip(
        modelo.coeficientes, modelo.features, strict=True
    ):
        total += coeficiente * valores[columna]
    return total


def guardar_y_cargar(modelo, df, ruta):
    """Guarda el modelo (#21) y lo vuelve a cargar del archivo (#24)."""
    guardar_modelo(modelo, metricas_modelo(modelo, df, df), ruta)
    cargado, _ = cargar_modelo(ruta)
    return cargado


# =============================================================================
# interpretar_valores
# =============================================================================


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("3.5", 3.5),
        ("3,5", 3.5),
        ("  3,5 ", 3.5),
        ("-2", -2.0),
        ("0", 0.0),
        ("1e3", 1000.0),
        (7, 7.0),
        (2.25, 2.25),
        (np.float64(1.5), 1.5),
    ],
)
def test_interpretar_valores_validos(texto, esperado):
    assert interpretar_valores(["x"], {"x": texto}) == {"x": esperado}


def test_interpretar_valores_respeta_el_orden_e_ignora_otras_claves():
    numeros = interpretar_valores(
        ["b", "a"], {"a": "1", "b": "2", "otra": "abc"}
    )
    assert list(numeros) == ["b", "a"]
    assert numeros == {"a": 1.0, "b": 2.0}


@pytest.mark.parametrize("vacio", [None, "", "   "])
def test_falta_un_valor(vacio):
    with pytest.raises(ErrorPrediccion, match="Falta el valor de: x2"):
        interpretar_valores(["x1", "x2"], {"x1": "1", "x2": vacio})


def test_faltan_varios_valores_los_dice_todos():
    with pytest.raises(ErrorPrediccion) as error:
        interpretar_valores(["x1", "x2", "x3"], {"x2": "5"})
    assert str(error.value) == "Falta el valor de: x1, x3."


def test_sin_valores():
    with pytest.raises(ErrorPrediccion, match="x1, x2"):
        interpretar_valores(["x1", "x2"], None)


@pytest.mark.parametrize(
    "malo", ["abc", "3,5,1", "1.000,5", "nan", "inf", True, [1], float("nan")]
)
def test_valor_no_numerico(malo):
    with pytest.raises(ErrorPrediccion) as error:
        interpretar_valores(["x1", "x2"], {"x1": "1", "x2": malo})
    assert str(error.value) == "El valor de x2 no es un número válido."


def test_varios_no_numericos_los_dice_todos():
    with pytest.raises(ErrorPrediccion, match="El valor de x1, x3 no"):
        interpretar_valores(
            ["x1", "x2", "x3"], {"x1": "a", "x2": "2", "x3": "b"}
        )


def test_primero_avisa_de_los_que_faltan():
    with pytest.raises(ErrorPrediccion, match="Falta el valor de: x2"):
        interpretar_valores(["x1", "x2"], {"x1": "abc"})


def test_columnas_que_no_son_texto():
    """Las cabeceras numéricas (por ejemplo, 2020) también valen."""
    assert interpretar_valores([2020], {2020: "4,5"}) == {2020: 4.5}
    with pytest.raises(ErrorPrediccion, match="Falta el valor de: 2020"):
        interpretar_valores([2020], {})


def test_el_error_lo_muestra_la_gui():
    """La GUI captura ErrorSikorius y muestra su mensaje."""
    assert issubclass(ErrorPrediccion, ErrorSikorius)


# =============================================================================
# predecir
# =============================================================================


def test_prediccion_simple_a_mano():
    modelo = entrenar_modelo(datos_simples(), ["x"], "y")
    # y = 2*x + 1 -> con x = 10, y = 21
    assert predecir(modelo, {"x": "10"}) == pytest.approx(21.0)
    assert predecir(modelo, {"x": "2,5"}) == pytest.approx(6.0)


def test_prediccion_multiple_a_mano():
    modelo = entrenar_modelo(
        datos_multiples(), ["metros", "antiguedad"], "precio"
    )
    valores = {"metros": 80.0, "antiguedad": 12.5}
    esperado = a_mano(modelo, valores)

    texto = {"metros": "80", "antiguedad": "12,5"}
    assert predecir(modelo, texto) == pytest.approx(esperado)
    # Y está cerca de la fórmula con la que se generaron los datos
    assert esperado == pytest.approx(1.5 * 80 - 4 * 12.5 + 10, abs=1)


def test_prediccion_con_modelo_conocido():
    """Coeficientes puestos a mano: no depende del entrenamiento."""
    modelo = ModeloLineal(("a", "b"), "z", (2.0, -0.5), 3.0)
    # z = 2*4 - 0.5*6 + 3 = 8
    assert predecir(modelo, {"a": "4", "b": "6"}) == pytest.approx(8.0)


def test_prediccion_devuelve_float():
    modelo = entrenar_modelo(datos_simples(), ["x"], "y")
    assert type(predecir(modelo, {"x": 1})) is float


def test_mismo_resultado_con_modelo_creado_y_cargado(tmp_path):
    df = datos_multiples()
    creado = entrenar_modelo(df, ["metros", "antiguedad"], "precio")
    cargado = guardar_y_cargar(creado, df, tmp_path / "modelo ñandú.json")

    valores = {"metros": "95,5", "antiguedad": "3"}
    assert predecir(cargado, valores) == predecir(creado, valores)


def test_sin_modelo():
    with pytest.raises(ErrorPrediccion, match="Crea o carga primero"):
        predecir(None, {"x": "1"})


def test_tras_un_error_se_puede_volver_a_predecir():
    modelo = entrenar_modelo(datos_simples(), ["x"], "y")
    with pytest.raises(ErrorPrediccion):
        predecir(modelo, {"x": "abc"})
    assert predecir(modelo, {"x": "1"}) == pytest.approx(3.0)


def test_predecir_no_cambia_el_modelo():
    modelo = entrenar_modelo(datos_simples(), ["x"], "y")
    antes = (
        modelo.features,
        modelo.coeficientes,
        modelo.termino_independiente,
    )
    predecir(modelo, {"x": "5"})
    assert antes == (
        modelo.features,
        modelo.coeficientes,
        modelo.termino_independiente,
    )


# =============================================================================
# texto_prediccion
# =============================================================================


def test_texto_con_nombre_de_la_salida_y_decimales_de_la_formula():
    modelo = ModeloLineal(("x",), "precio", (1.0,), 0.0)
    assert texto_prediccion(modelo, 1520.375) == "precio = 1520.3750"
    assert texto_prediccion(modelo, 2.123456) == "precio = 2.1235"
    assert texto_prediccion(modelo, -3) == "precio = -3.0000"


def test_texto_usa_los_decimales_de_la_formula():
    modelo = ModeloLineal(("x",), "y", (1.0,), 0.0)
    decimales = texto_prediccion(modelo, 1 / 3).split(".")[-1]
    assert len(decimales) == DECIMALES_FORMULA


def test_texto_sin_menos_cero():
    modelo = ModeloLineal(("x",), "y", (1.0,), 0.0)
    assert texto_prediccion(modelo, -0.00001) == "y = 0.0000"


def test_texto_de_una_prediccion_completa():
    modelo = entrenar_modelo(datos_simples(), ["x"], "y")
    valor = predecir(modelo, {"x": "3,5"})
    assert texto_prediccion(modelo, valor) == "y = 8.0000"
