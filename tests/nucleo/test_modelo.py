"""Tests de la lógica del modelo de regresión lineal (#121).

uv run pytest tests/nucleo/test_modelo.py -v
"""

import inspect
import json
import warnings

import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure

from sikorius.nucleo.errores import ErrorModelo
from sikorius.nucleo.modelo import (
    ModeloLineal,
    calcular_ecm,
    calcular_r2,
    datos_ajuste,
    dibujar_ajuste,
    entrenar_modelo,
    formula_texto,
    metricas_modelo,
)

# =============================================================================
# Utilidades
# =============================================================================


def datos_lineales(n=20, semilla=0):
    """y = 2*x1 - 3*x2 + 5, sin ruido (un coeficiente es negativo)."""
    rng = np.random.default_rng(semilla)
    x1 = rng.uniform(0, 10, n)
    x2 = rng.uniform(0, 10, n)
    return pd.DataFrame({"x1": x1, "x2": x2, "y": 2 * x1 - 3 * x2 + 5})


# =============================================================================
# Entrenamiento
# =============================================================================


def test_regresion_simple_recupera_recta():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [3.0, 5.0, 7.0, 9.0]})
    modelo = entrenar_modelo(df, ["x"], "y")
    assert modelo.coeficientes == pytest.approx((2.0,))
    assert modelo.termino_independiente == pytest.approx(1.0)
    assert modelo.features == ("x",)
    assert modelo.target == "y"


def test_regresion_multiple_con_coeficiente_negativo():
    modelo = entrenar_modelo(datos_lineales(), ["x1", "x2"], "y")
    assert modelo.coeficientes == pytest.approx((2.0, -3.0))
    assert modelo.termino_independiente == pytest.approx(5.0)


def test_predecir():
    df = datos_lineales()
    modelo = entrenar_modelo(df, ["x1", "x2"], "y")
    assert modelo.predecir(df) == pytest.approx(df["y"].to_numpy())


def test_entrenar_no_modifica_el_entrenamiento():
    df = datos_lineales()
    antes = df.copy()
    entrenar_modelo(df, ["x1", "x2"], "y")
    pd.testing.assert_frame_equal(df, antes)


# =============================================================================
# Gráfico del ajuste
# =============================================================================


def datos_simples():
    entrenamiento = pd.DataFrame(
        {"x": [1.0, 2.0, 3.0, 4.0], "y": [3.0, 5.0, 7.0, 9.0]}
    )
    test = pd.DataFrame({"x": [0.0, 10.0], "y": [1.5, 20.0]})
    return entrenamiento, test


def test_datos_ajuste_regresion_simple():
    entrenamiento, test = datos_simples()
    modelo = entrenar_modelo(entrenamiento, ["x"], "y")
    datos = datos_ajuste(modelo, entrenamiento, test)
    assert datos["tipo"] == "simple"
    assert datos["etiqueta_x"] == "x"
    assert datos["etiqueta_y"] == "y"
    assert datos["entrenamiento"][0].tolist() == [1.0, 2.0, 3.0, 4.0]
    assert datos["test"][1].tolist() == [1.5, 20.0]
    extremos, recta = datos["recta"]
    # la recta cubre también los puntos de test (de x = 0 a x = 10)
    assert extremos.tolist() == [0.0, 10.0]
    assert recta == pytest.approx([1.0, 21.0])


def test_datos_ajuste_regresion_multiple():
    df = datos_lineales()
    modelo = entrenar_modelo(df.iloc[:15], ["x1", "x2"], "y")
    datos = datos_ajuste(modelo, df.iloc[:15], df.iloc[15:])
    assert datos["tipo"] == "multiple"
    assert datos["etiqueta_x"] == "Valor predicho"
    assert datos["etiqueta_y"] == "Valor real"
    predicho, real = datos["test"]
    assert predicho == pytest.approx(modelo.predecir(df.iloc[15:]))
    assert real.tolist() == df.iloc[15:]["y"].tolist()
    predicho, real = datos["entrenamiento"]
    assert predicho == pytest.approx(modelo.predecir(df.iloc[:15]))
    assert real.tolist() == df.iloc[:15]["y"].tolist()
    extremos, diagonal = datos["recta"]
    assert extremos.tolist() == diagonal.tolist()  # real = predicho
    todos = np.concatenate(
        [
            datos["entrenamiento"][0],
            datos["entrenamiento"][1],
            datos["test"][0],
            datos["test"][1],
        ]
    )
    assert extremos[0] == pytest.approx(todos.min())
    assert extremos[1] == pytest.approx(todos.max())


def test_dibujar_ajuste_simple_etiquetas_y_leyenda():
    entrenamiento, test = datos_simples()
    modelo = entrenar_modelo(entrenamiento, ["x"], "y")
    figura = Figure()
    dibujar_ajuste(figura, datos_ajuste(modelo, entrenamiento, test))
    ejes = figura.axes[0]
    assert ejes.get_xlabel() == "x"
    assert ejes.get_ylabel() == "y"
    textos = [t.get_text() for t in ejes.get_legend().get_texts()]
    assert textos == ["Entrenamiento", "Test", "Recta del modelo"]


def test_dibujar_ajuste_multiple_etiquetas_y_leyenda():
    df = datos_lineales()
    modelo = entrenar_modelo(df.iloc[:15], ["x1", "x2"], "y")
    figura = Figure()
    dibujar_ajuste(figura, datos_ajuste(modelo, df.iloc[:15], df.iloc[15:]))
    ejes = figura.axes[0]
    assert ejes.get_xlabel() == "Valor predicho"
    assert ejes.get_ylabel() == "Valor real"
    textos = [t.get_text() for t in ejes.get_legend().get_texts()]
    assert textos == ["Entrenamiento", "Test", "Real = predicho"]


def test_dibujar_ajuste_usa_pocas_marcas_en_los_ejes():
    df = datos_lineales() * 100000  # cifras grandes: marcas largas
    modelo = entrenar_modelo(df.iloc[:15], ["x1", "x2"], "y")
    figura = Figure()
    dibujar_ajuste(figura, datos_ajuste(modelo, df.iloc[:15], df.iloc[15:]))
    ejes = figura.axes[0]
    assert len(ejes.get_xticks()) <= 7
    assert len(ejes.get_yticks()) <= 7


def test_dibujar_ajuste_dos_veces_sustituye_el_grafico():
    entrenamiento, test = datos_simples()
    modelo = entrenar_modelo(entrenamiento, ["x"], "y")
    datos = datos_ajuste(modelo, entrenamiento, test)
    figura = Figure()
    dibujar_ajuste(figura, datos)
    dibujar_ajuste(figura, datos)
    assert len(figura.axes) == 1


# =============================================================================
# Fórmula del modelo
# =============================================================================


def test_formula_regresion_simple():
    modelo = ModeloLineal(("x",), "y", (2.0,), 1.0)
    assert formula_texto(modelo) == "y = 2.0000 * x + 1.0000"


def test_formula_coeficiente_negativo_resta():
    modelo = ModeloLineal(("x1", "x2"), "y", (2.0, -3.0), 5.0)
    formula = formula_texto(modelo)
    assert formula == "y = 2.0000 * x1 - 3.0000 * x2 + 5.0000"
    assert "+ -" not in formula


def test_formula_termino_independiente_negativo_resta():
    modelo = ModeloLineal(("x1", "x2"), "y", (2.0, 3.0), -5.0)
    assert formula_texto(modelo) == "y = 2.0000 * x1 + 3.0000 * x2 - 5.0000"


def test_formula_primer_coeficiente_negativo_lleva_el_signo_delante():
    modelo = ModeloLineal(("x1", "x2"), "y", (-2.0, 3.0), 5.0)
    assert formula_texto(modelo) == "y = -2.0000 * x1 + 3.0000 * x2 + 5.0000"


def test_formula_redondea_a_un_numero_fijo_de_decimales():
    modelo = ModeloLineal(("x",), "y", (1.23456789,), 0.5)
    assert formula_texto(modelo) == "y = 1.2346 * x + 0.5000"
    assert formula_texto(modelo, decimales=2) == "y = 1.23 * x + 0.50"


def test_formula_negativo_que_redondea_a_cero_no_muestra_menos_cero():
    modelo = ModeloLineal(("x",), "y", (-0.00001,), 3.0)
    formula = formula_texto(modelo)
    assert formula == "y = 0.0000 * x + 3.0000"
    assert "-0.0000" not in formula


def test_formula_usa_los_nombres_reales_de_las_columnas():
    df = datos_lineales()
    modelo = entrenar_modelo(df, ["x1", "x2"], "y")
    assert formula_texto(modelo) == "y = 2.0000 * x1 - 3.0000 * x2 + 5.0000"


# =============================================================================
# Métricas del modelo
# =============================================================================


def test_ecm_calculo_a_mano():
    # errores: 1, -1, 2 -> (1 + 1 + 4) / 3 = 2
    assert calcular_ecm([1, 2, 3], [0, 3, 1]) == pytest.approx(2.0)


def test_r2_calculo_a_mano():
    real = [1.0, 2.0, 3.0]
    predicho = [1.0, 2.0, 4.0]
    # SS_res = 1, SS_tot = 2 -> 1 - 1/2
    assert calcular_r2(real, predicho) == pytest.approx(0.5)


def test_r2_ajuste_perfecto_es_uno_y_ecm_cero():
    real = [1.0, 2.0, 3.0]
    assert calcular_r2(real, real) == pytest.approx(1.0)
    assert calcular_ecm(real, real) == pytest.approx(0.0)


def test_r2_con_salida_constante_no_se_puede_calcular():
    assert np.isnan(calcular_r2([5.0, 5.0, 5.0], [5.0, 4.0, 6.0]))


def test_r2_puede_ser_negativo():
    assert calcular_r2([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) < 0


def test_metricas_modelo_entrenamiento_y_test():
    df = datos_lineales()
    entrenamiento, test = df.iloc[:15], df.iloc[15:].copy()
    modelo = entrenar_modelo(entrenamiento, ["x1", "x2"], "y")
    test["y"] = test["y"] + 2  # el test tiene error constante de 2
    metricas = metricas_modelo(modelo, entrenamiento, test)
    assert set(metricas) == {"entrenamiento", "test"}
    assert metricas["entrenamiento"]["r2"] == pytest.approx(1.0)
    assert metricas["entrenamiento"]["ecm"] == pytest.approx(0.0, abs=1e-12)
    assert metricas["test"]["ecm"] == pytest.approx(4.0)
    assert metricas["test"]["r2"] < 1.0


def test_metricas_no_modifican_los_datos():
    df = datos_lineales()
    antes = df.copy()
    modelo = entrenar_modelo(df.iloc[:15], ["x1", "x2"], "y")
    metricas_modelo(modelo, df.iloc[:15], df.iloc[15:])
    pd.testing.assert_frame_equal(df, antes)


# =============================================================================
# Manejo de errores
# =============================================================================


def test_columna_de_texto_en_la_entrada_da_error_con_su_nombre():
    df = datos_lineales().assign(texto="a")
    with pytest.raises(ErrorModelo, match="'texto' no es numérica"):
        entrenar_modelo(df, ["x1", "texto"], "y")


def test_columna_de_texto_en_la_salida_da_error():
    df = datos_lineales().assign(texto="a")
    with pytest.raises(ErrorModelo, match="'texto' no es numérica"):
        entrenar_modelo(df, ["x1"], "texto")


def test_columna_inexistente_da_error():
    with pytest.raises(ErrorModelo, match="No existe la columna 'zzz'"):
        entrenar_modelo(datos_lineales(), ["zzz"], "y")


def test_valores_inexistentes_dan_error_al_entrenar():
    df = datos_lineales()
    df.loc[df.index[2], "x1"] = np.nan
    with pytest.raises(ErrorModelo, match="inexistentes"):
        entrenar_modelo(df, ["x1", "x2"], "y")


def test_valores_infinitos_dan_error():
    df = datos_lineales()
    df.loc[df.index[2], "x1"] = np.inf
    with pytest.raises(ErrorModelo, match="infinitos"):
        entrenar_modelo(df, ["x1", "x2"], "y")


def test_entrenamiento_vacio_da_error():
    with pytest.raises(ErrorModelo, match="no tiene filas"):
        entrenar_modelo(datos_lineales().iloc[:0], ["x1"], "y")


def test_menos_filas_que_parametros_da_error():
    df = datos_lineales().iloc[:2]  # 2 entradas + término = 3 parámetros
    with pytest.raises(ErrorModelo, match="muy pocas filas"):
        entrenar_modelo(df, ["x1", "x2"], "y")


def test_columna_de_entrada_constante_da_error():
    df = datos_lineales().assign(c=3.0)
    with pytest.raises(ErrorModelo, match="modelo único"):
        entrenar_modelo(df, ["x1", "c"], "y")


def test_columnas_dependientes_dan_error():
    df = datos_lineales()
    df["doble"] = 2 * df["x1"]
    with pytest.raises(ErrorModelo, match="modelo único"):
        entrenar_modelo(df, ["x1", "doble"], "y")


def test_metricas_con_conjunto_vacio_dan_nan_sin_avisos():
    df = datos_lineales()
    modelo = entrenar_modelo(df.iloc[:15], ["x1", "x2"], "y")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        metricas = metricas_modelo(modelo, df.iloc[:15], df.iloc[:0])
    assert np.isnan(metricas["test"]["ecm"])
    assert np.isnan(metricas["test"]["r2"])
    assert metricas["entrenamiento"]["r2"] == pytest.approx(1.0)


# =============================================================================
# Descripción del modelo
# =============================================================================


def test_un_modelo_entrenado_tiene_la_descripcion_vacia():
    modelo = entrenar_modelo(datos_lineales(), ["x1", "x2"], "y")
    assert modelo.descripcion == ""


def test_la_descripcion_es_opcional_al_crear_el_modelo():
    modelo = ModeloLineal(("x",), "y", (2.0,), 1.0)
    assert modelo.descripcion == ""


def test_la_descripcion_se_guarda_en_el_modelo():
    modelo = ModeloLineal(("x",), "y", (2.0,), 1.0, "Precio de casas")
    assert modelo.descripcion == "Precio de casas"


def test_la_descripcion_se_puede_cambiar_despues():
    modelo = entrenar_modelo(datos_lineales(), ["x1", "x2"], "y")
    modelo.descripcion = "Primera versión"
    modelo.descripcion = "Segunda versión\ncon dos líneas"
    assert modelo.descripcion == "Segunda versión\ncon dos líneas"


def test_la_descripcion_no_cambia_el_resto_del_modelo():
    modelo = entrenar_modelo(datos_lineales(), ["x1", "x2"], "y")
    formula = formula_texto(modelo)
    coeficientes = modelo.coeficientes
    modelo.descripcion = "Un texto cualquiera"
    assert formula_texto(modelo) == formula
    assert modelo.coeficientes == coeficientes


# =============================================================================
# Estructura de persistencia (investigación #20)
# =============================================================================


def bloque_modelo(modelo):
    """El bloque "modelo" del archivo JSON de la investigación."""
    return {
        "features": list(modelo.features),
        "target": modelo.target,
        "coeficientes": list(modelo.coeficientes),
        "termino_independiente": modelo.termino_independiente,
    }


def test_el_constructor_acepta_los_campos_del_bloque_json():
    parametros = set(inspect.signature(ModeloLineal).parameters)
    campos = {"features", "target", "coeficientes", "termino_independiente"}
    assert campos <= parametros
    assert "descripcion" not in campos  # la descripción va fuera del bloque


def test_el_modelo_se_reconstruye_desde_el_bloque_json():
    df = datos_lineales()
    original = entrenar_modelo(df, ["x1", "x2"], "y")
    texto = json.dumps(bloque_modelo(original), allow_nan=False)

    reconstruido = ModeloLineal(**json.loads(texto))

    assert reconstruido.features == original.features
    assert reconstruido.coeficientes == original.coeficientes
    assert reconstruido.predecir(df).tolist() == original.predecir(df).tolist()
    assert reconstruido.descripcion == ""


def test_los_numeros_del_modelo_son_float_normales():
    modelo = entrenar_modelo(datos_lineales(), ["x1", "x2"], "y")
    assert all(type(c) is float for c in modelo.coeficientes)
    assert type(modelo.termino_independiente) is float


def test_las_metricas_tienen_la_estructura_del_archivo():
    df = datos_lineales()
    modelo = entrenar_modelo(df.iloc[:15], ["x1", "x2"], "y")
    metricas = metricas_modelo(modelo, df.iloc[:15], df.iloc[15:])
    assert set(metricas) == {"entrenamiento", "test"}
    for conjunto in metricas.values():
        assert set(conjunto) == {"r2", "ecm"}
    json.dumps(metricas, allow_nan=False)  # son números JSON válidos


def test_la_formula_es_un_texto():
    modelo = entrenar_modelo(datos_lineales(), ["x1", "x2"], "y")
    assert isinstance(formula_texto(modelo), str)
