"""Pruebas del preprocesado de los datos antes de crear el modelo (#110, #111).

    uv run pytest test/test_preprocesado.py -v

Bloques:
    - Constantes y jerarquía de errores.
    - normalizar_espacios_vacios: celdas vacías o con espacios pasan a NaN.
    - detectar_nulos / quedan_nulos / detectar_nulos_conjuntos / hay_nulos.
    - interpretar_constante: números válidos ("2,5", " 3 "...) y errores.
    - columnas_seleccionadas: orden features + target y cabeceras no texto.
    - aplicar_preprocesado: las cuatro estrategias, resumen y errores.
    - Estado: detectar_en_estado, aplicar_al_estado, modelo_disponible.
    - texto_resumen: mensaje que se muestra al usuario.
    - crear_boton_preprocesado: el botón de la GUI, sin servidor.
    - PanelPreprocesado: el panel de la GUI, sin servidor.
"""

import inspect

import numpy as np
import pandas as pd
import pytest
from nicegui import ui

import sikorius.gui.boton_preprocesado as modulo_boton
from sikorius.estado import EstadoApp
from sikorius.preprocesado import (
    CONSTANTE, ELIMINAR, ESTRATEGIAS, MEDIA, MEDIANA, AvisoPreprocesado,
    ColumnasNoEncontradasError, ErrorPreprocesado, aplicar_al_estado,
    aplicar_preprocesado, columnas_seleccionadas, detectar_en_estado,
    detectar_nulos, detectar_nulos_conjuntos, hay_nulos, interpretar_constante,
    modelo_disponible, normalizar_espacios_vacios, quedan_nulos, texto_resumen,
)


# =============================================================================
# Utilidades
# =============================================================================

def crear_train():
    """Entrenamiento con un NaN en 'x', una celda en blanco en 'y' y un NaN
    en 'otra', que no se selecciona nunca."""
    return pd.DataFrame({
        "x": [1.0, np.nan, 3.0, 5.0],
        "y": [10.0, 20.0, "  ", 40.0],
        "otra": [np.nan, 1.0, 2.0, 3.0],
    }, index=[10, 11, 12, 13])


def crear_test():
    """Test con un NaN en 'x' y ninguno en 'y'."""
    return pd.DataFrame({
        "x": [np.nan, 100.0],
        "y": [1.0, 2.0],
        "otra": [np.nan, np.nan],
    }, index=[20, 21])


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
# Constantes y errores
# =============================================================================

def test_estrategias_disponibles():
    assert ESTRATEGIAS == ("eliminar", "media", "mediana", "constante")
    assert (ELIMINAR, MEDIA, MEDIANA, CONSTANTE) == ESTRATEGIAS


def test_jerarquia_de_errores():
    """La GUI captura ErrorPreprocesado: los demás errores deben heredar de él."""
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
    df = pd.DataFrame({
        "nan": [np.nan, 1.0, np.nan],
        "none": [None, "a", "b"],
        "vacios": ["", "  ", "c"],
        "llena": [1, 2, 3],
    })
    assert detectar_nulos(df, list(df.columns)) == {
        "nan": 2, "none": 1, "vacios": 2, "llena": 0,
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


@pytest.mark.parametrize("columnas, esperado", [
    (["x"], True), (["y"], True), (["x", "y"], True),
    (("x", "y"), True), ([], False),
])
def test_quedan_nulos(columnas, esperado):
    assert quedan_nulos(crear_train(), columnas) is esperado


def test_quedan_nulos_sin_valores_inexistentes():
    df = pd.DataFrame({"x": [1.0, 2.0], "y": ["a", "b"]})
    assert quedan_nulos(df, ["x", "y"]) is False


def test_detectar_conjuntos_por_separado():
    deteccion = detectar_nulos_conjuntos(crear_train(), crear_test(),
                                         ("x", "y"))
    assert deteccion == {
        "train": {"x": 1, "y": 1},
        "test": {"x": 1, "y": 0},
    }


@pytest.mark.parametrize("deteccion, esperado", [
    ({"train": {"x": 0}, "test": {"x": 0}}, False),
    ({"train": {"x": 1}, "test": {"x": 0}}, True),
    ({"train": {"x": 0}, "test": {"x": 0, "y": 3}}, True),
    ({"train": {}, "test": {}}, False),
])
def test_hay_nulos(deteccion, esperado):
    assert hay_nulos(deteccion) is esperado


# =============================================================================
# interpretar_constante
# =============================================================================

@pytest.mark.parametrize("valor, esperado", [
    (0, 0.0), (3, 3.0), (-1, -1.0), (2.5, 2.5), ("3", 3.0), ("2.5", 2.5),
    ("2,5", 2.5), ("  4  ", 4.0), ("-0,75", -0.75), ("1e3", 1000.0),
    (np.int64(7), 7.0), (np.float64(1.5), 1.5),
])
def test_constante_valida(valor, esperado):
    resultado = interpretar_constante(valor)
    assert resultado == esperado
    assert isinstance(resultado, float)


@pytest.mark.parametrize("valor", [
    None, True, False, "", "   ", "abc", "2,5,1", "3 €", "nan", "inf",
    "-inf", float("nan"), float("inf"), [1], {},
])
def test_constante_no_valida(valor):
    with pytest.raises(ErrorPreprocesado, match="debe ser un número"):
        interpretar_constante(valor)


# =============================================================================
# columnas_seleccionadas
# =============================================================================

def test_columnas_features_y_target_al_final():
    estado = EstadoApp()
    estado.datos = pd.DataFrame({"a": [1], "b": [2], "c": [3], "d": [4]})
    estado.guardar_seleccion(["c", "a"], "b", "multiple")
    assert columnas_seleccionadas(estado) == ["c", "a", "b"]


def test_columnas_cabeceras_no_texto_usan_la_columna_real():
    """El selector guarda "2020" como texto; el DataFrame tiene el entero 2020."""
    estado = EstadoApp()
    estado.datos = pd.DataFrame({2020: [1.0], "precio": [2.0]})
    estado.guardar_seleccion(["2020"], "precio", "simple")
    assert columnas_seleccionadas(estado) == [2020, "precio"]


def test_columnas_usa_entrenamiento_si_hay_separacion():
    estado = crear_estado()
    estado.datos = None
    assert columnas_seleccionadas(estado) == ["x", "y"]


def test_columnas_sin_datos_devuelve_los_nombres():
    estado = EstadoApp()
    estado.seleccion = {"features": ["a"], "target": "b",
                        "tipo_regresion": "simple"}
    assert columnas_seleccionadas(estado) == ["a", "b"]


# =============================================================================
# aplicar_preprocesado · eliminar
# =============================================================================

def test_eliminar_quita_filas_con_nulos_en_columnas_seleccionadas():
    train, test, resumen = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, ELIMINAR)
    assert train.index.tolist() == [10, 13]    # 11 (NaN) y 12 ("  ") fuera
    assert test.index.tolist() == [21]
    assert resumen == {
        "train": {"filas_eliminadas": 2, "valores_rellenados": 0},
        "test": {"filas_eliminadas": 1, "valores_rellenados": 0},
    }


def test_eliminar_ignora_nulos_de_columnas_no_seleccionadas():
    """La fila 10 tiene NaN en 'otra', pero 'otra' no está seleccionada."""
    train, _, _ = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, ELIMINAR)
    assert 10 in train.index
    assert pd.isna(train.at[10, "otra"])


def test_eliminar_sin_nulos_no_cambia_nada():
    train = pd.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0]})
    test = pd.DataFrame({"x": [5.0], "y": [6.0]})
    train_p, test_p, resumen = aplicar_preprocesado(train, test, COLUMNAS,
                                                    ELIMINAR)
    pd.testing.assert_frame_equal(train_p, train)
    pd.testing.assert_frame_equal(test_p, test)
    assert resumen["train"]["filas_eliminadas"] == 0
    assert resumen["test"]["filas_eliminadas"] == 0


@pytest.mark.parametrize("vacio, conjunto", [
    ("train", "entrenamiento"), ("test", "test"),
])
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
    with pytest.raises(AvisoPreprocesado,
                       match="entrenamiento y el de test"):
        aplicar_preprocesado(sin_datos, sin_datos, COLUMNAS, ELIMINAR)


# =============================================================================
# aplicar_preprocesado · media, mediana y constante
# =============================================================================

def test_media_se_calcula_solo_con_entrenamiento():
    """El test se rellena con la media de train (x = 3), no con la suya, para
    no filtrar información del conjunto de test al modelo."""
    train, test, _ = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, MEDIA)
    media_x = (1.0 + 3.0 + 5.0) / 3
    media_y = (10.0 + 20.0 + 40.0) / 3
    assert train.at[11, "x"] == media_x
    assert train.at[12, "y"] == media_y
    assert test.at[20, "x"] == media_x
    assert test.at[21, "x"] == 100.0           # los valores reales se conservan


def test_mediana_se_calcula_solo_con_entrenamiento():
    train = pd.DataFrame({"x": [1.0, 2.0, 100.0, np.nan], "y": [1.0] * 4})
    test = pd.DataFrame({"x": [np.nan, 50.0], "y": [1.0, 1.0]})
    train_p, test_p, _ = aplicar_preprocesado(train, test, COLUMNAS, MEDIANA)
    assert train_p.at[3, "x"] == 2.0
    assert test_p.at[0, "x"] == 2.0


@pytest.mark.parametrize("constante, esperado", [
    (0, 0.0), (-3, -3.0), ("2,5", 2.5), (" 7 ", 7.0),
])
def test_constante_rellena_con_el_valor(constante, esperado):
    train, test, _ = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, CONSTANTE, constante)
    assert train.at[11, "x"] == esperado
    assert train.at[12, "y"] == esperado
    assert test.at[20, "x"] == esperado


@pytest.mark.parametrize("estrategia", [MEDIA, MEDIANA, CONSTANTE])
def test_rellenar_resumen_y_sin_nulos(estrategia):
    train, test, resumen = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, estrategia, 0)
    assert resumen == {
        "train": {"filas_eliminadas": 0, "valores_rellenados": 2},
        "test": {"filas_eliminadas": 0, "valores_rellenados": 1},
    }
    assert not quedan_nulos(train, COLUMNAS)
    assert not quedan_nulos(test, COLUMNAS)
    assert len(train) == 4 and len(test) == 2   # no se quita ninguna fila


@pytest.mark.parametrize("estrategia", [MEDIA, MEDIANA, CONSTANTE])
def test_rellenar_no_toca_columnas_no_seleccionadas(estrategia):
    train, test, _ = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, estrategia, 0)
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
        aplicar_preprocesado(crear_train(), crear_test(), COLUMNAS,
                             CONSTANTE, constante)


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
        aplicar_preprocesado(crear_train(), crear_test(), ["x", "z"],
                             estrategia, 1)


@pytest.mark.parametrize("estrategia", ESTRATEGIAS)
def test_acepta_columnas_como_tupla(estrategia):
    train, _, _ = aplicar_preprocesado(crear_train(), crear_test(),
                                       ("x", "y"), estrategia, 1)
    assert not quedan_nulos(train, COLUMNAS)


def test_conserva_columnas_e_indice():
    train, test, _ = aplicar_preprocesado(
        crear_train(), crear_test(), COLUMNAS, MEDIA)
    assert list(train.columns) == ["x", "y", "otra"]
    assert train.index.tolist() == [10, 11, 12, 13]
    assert test.index.tolist() == [20, 21]


# =============================================================================
# Estado: detectar_en_estado, aplicar_al_estado y modelo_disponible
# =============================================================================

def test_detectar_en_estado_sin_seleccion_ni_separacion():
    estado = EstadoApp()
    estado.datos = crear_train()
    assert detectar_en_estado(estado) is None
    estado.guardar_seleccion(["x"], "y", "simple")
    assert detectar_en_estado(estado) is None    # falta la separación


def test_detectar_en_estado_con_separacion(estado_con_nulos):
    assert detectar_en_estado(estado_con_nulos) == {
        "train": {"x": 1, "y": 1},
        "test": {"x": 1, "y": 0},
    }


def test_detectar_en_estado_revisa_los_conjuntos_preprocesados(estado_con_nulos):
    aplicar_al_estado(estado_con_nulos, MEDIA)
    deteccion = detectar_en_estado(estado_con_nulos)
    assert not hay_nulos(deteccion)


def test_aplicar_al_estado_sin_seleccion():
    estado = EstadoApp()
    estado.datos = crear_train()
    with pytest.raises(ErrorPreprocesado, match="selección de columnas"):
        aplicar_al_estado(estado, MEDIA)
    assert estado.preprocesado is None


def test_aplicar_al_estado_sin_separacion():
    estado = EstadoApp()
    estado.datos = crear_train()
    estado.guardar_seleccion(["x"], "y", "simple")
    with pytest.raises(ErrorPreprocesado, match="entrenamiento y test"):
        aplicar_al_estado(estado, MEDIA)
    assert estado.preprocesado is None


def test_aplicar_al_estado_guarda_el_resultado(estado_con_nulos):
    estado = estado_con_nulos
    train_original, test_original = estado.entrenamiento, estado.test
    resumen = aplicar_al_estado(estado, CONSTANTE, "0")
    assert set(estado.preprocesado) == {"entrenamiento", "test", "estrategia",
                                        "resumen"}
    assert estado.preprocesado["estrategia"] == CONSTANTE
    assert estado.preprocesado["resumen"] == resumen
    assert estado.preprocesado["entrenamiento"].at[11, "x"] == 0.0
    # Los conjuntos de la separación se conservan sin preprocesar
    assert estado.entrenamiento is train_original
    assert estado.test is test_original
    assert pd.isna(estado.entrenamiento.at[11, "x"])


def test_aplicar_al_estado_parte_siempre_de_la_separacion(estado_con_nulos):
    """Aplicar dos veces no encadena: la segunda parte de los datos separados."""
    aplicar_al_estado(estado_con_nulos, CONSTANTE, 0)
    resumen = aplicar_al_estado(estado_con_nulos, ELIMINAR)
    assert resumen["train"]["filas_eliminadas"] == 2
    assert estado_con_nulos.preprocesado["estrategia"] == ELIMINAR
    assert len(estado_con_nulos.preprocesado["entrenamiento"]) == 2


@pytest.mark.parametrize("estrategia, constante", [
    (CONSTANTE, "abc"), ("otra", None),
])
def test_aplicar_al_estado_error_conserva_lo_anterior(estado_con_nulos,
                                                      estrategia, constante):
    aplicar_al_estado(estado_con_nulos, MEDIA)
    anterior = estado_con_nulos.preprocesado
    with pytest.raises(ErrorPreprocesado):
        aplicar_al_estado(estado_con_nulos, estrategia, constante)
    assert estado_con_nulos.preprocesado is anterior


def test_aplicar_al_estado_aviso_no_aplica_nada():
    train = pd.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0]})
    test = pd.DataFrame({"x": [np.nan], "y": [1.0]})
    estado = crear_estado(train, test)
    with pytest.raises(AvisoPreprocesado):
        aplicar_al_estado(estado, ELIMINAR)
    assert estado.preprocesado is None


def test_aplicar_al_estado_cabeceras_no_texto():
    train = pd.DataFrame({2020: [1.0, np.nan, 3.0], "y": [1.0, 2.0, 3.0]})
    test = pd.DataFrame({2020: [np.nan], "y": [4.0]})
    estado = EstadoApp()
    estado.datos = pd.concat([train, test])
    estado.guardar_seleccion(["2020"], "y", "simple")
    estado.guardar_separacion(train, test, 25, 42)
    aplicar_al_estado(estado, MEDIA)
    assert estado.preprocesado["test"].at[0, 2020] == 2.0


def test_nueva_separacion_descarta_el_preprocesado(estado_con_nulos):
    aplicar_al_estado(estado_con_nulos, MEDIA)
    estado_con_nulos.guardar_separacion(crear_train(), crear_test(), 30, 1)
    assert estado_con_nulos.preprocesado is None
    assert not modelo_disponible(estado_con_nulos)


def test_modelo_no_disponible_sin_separacion():
    estado = EstadoApp()
    assert modelo_disponible(estado) is False
    estado.datos = crear_train()
    estado.guardar_seleccion(["x"], "y", "simple")
    assert modelo_disponible(estado) is False


def test_modelo_no_disponible_con_nulos(estado_con_nulos):
    assert modelo_disponible(estado_con_nulos) is False


def test_modelo_disponible_sin_nulos_sin_preprocesar(estado_sin_nulos):
    assert estado_sin_nulos.preprocesado is None
    assert modelo_disponible(estado_sin_nulos) is True


@pytest.mark.parametrize("estrategia", ESTRATEGIAS)
def test_modelo_disponible_tras_preprocesar(estado_con_nulos, estrategia):
    aplicar_al_estado(estado_con_nulos, estrategia, 0)
    assert modelo_disponible(estado_con_nulos) is True


def test_modelo_disponible_ignora_columnas_no_seleccionadas(estado_con_nulos):
    """'otra' sigue con NaN tras preprocesar, pero no se usa en el modelo."""
    aplicar_al_estado(estado_con_nulos, MEDIA)
    assert estado_con_nulos.preprocesado["test"]["otra"].isna().all()
    assert modelo_disponible(estado_con_nulos) is True


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
    _, _, resumen = aplicar_preprocesado(crear_train(), crear_test(),
                                         COLUMNAS, MEDIA)
    texto = texto_resumen(resumen)
    assert "Entrenamiento: 0 filas eliminadas, 2 valores rellenados" in texto
    assert "Test: 0 filas eliminadas, 1 valores rellenados" in texto


# =============================================================================
# crear_boton_preprocesado (GUI sin servidor)
# =============================================================================
#
# El botón trabaja con la instancia compartida ``sikorius.estado.estado``.
# Para no ensuciarla entre tests se sustituye por un estado nuevo.

def crear_boton(estado, monkeypatch, estrategia, constante=None,
                al_aplicar=None):
    from sikorius.gui.boton_preprocesado import crear_boton_preprocesado
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
    _, botones, avisos = crear_boton(estado_con_nulos, monkeypatch, MEDIA,
                                     al_aplicar=lambda: llamadas.append(1))
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
    from sikorius.gui.boton_preprocesado import crear_boton_preprocesado
    monkeypatch.setattr(modulo_boton, "estado", estado_con_nulos)
    Avisos(monkeypatch)
    botones = Botones(monkeypatch)
    controles = {"estrategia": MEDIA, "constante": None}
    crear_boton_preprocesado(lambda: controles["estrategia"],
                             lambda: controles["constante"])
    controles["estrategia"] = CONSTANTE
    controles["constante"] = "9"
    botones.pulsar()
    assert estado_con_nulos.preprocesado["estrategia"] == CONSTANTE
    assert estado_con_nulos.preprocesado["test"].at[20, "x"] == 9.0


@pytest.mark.parametrize("constante", [None, "abc", ""])
def test_boton_error_constante(estado_con_nulos, monkeypatch, constante):
    llamadas = []
    _, botones, avisos = crear_boton(estado_con_nulos, monkeypatch, CONSTANTE,
                                     constante,
                                     al_aplicar=lambda: llamadas.append(1))
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
    _, botones, avisos = crear_boton(estado, monkeypatch, ELIMINAR,
                                     al_aplicar=lambda: llamadas.append(1))
    botones.pulsar()
    mensaje, tipo = avisos.ultimo()
    assert tipo == "warning"                   # aviso, no error
    assert "vacío" in mensaje
    assert estado.preprocesado is None
    assert llamadas == []


def test_boton_se_puede_reintentar_tras_un_error(estado_con_nulos, monkeypatch):
    from sikorius.gui.boton_preprocesado import crear_boton_preprocesado
    monkeypatch.setattr(modulo_boton, "estado", estado_con_nulos)
    avisos = Avisos(monkeypatch)
    botones = Botones(monkeypatch)
    constante = {"valor": "abc"}
    boton = crear_boton_preprocesado(lambda: CONSTANTE,
                                     lambda: constante["valor"])
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
    from sikorius.gui.panel_preprocesado import PanelPreprocesado
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


@pytest.mark.parametrize("estrategia, habilitado", [
    (CONSTANTE, True), (MEDIA, False), (MEDIANA, False), (ELIMINAR, False),
])
def test_panel_constante_solo_con_esa_estrategia(estado_con_nulos, monkeypatch,
                                                 estrategia, habilitado):
    panel, _, _ = crear_panel(estado_con_nulos, monkeypatch)
    panel.estrategia.set_value(estrategia)
    assert panel.constante.enabled is habilitado


def test_panel_aplicar_actualiza_la_deteccion(estado_con_nulos, monkeypatch):
    llamadas = []
    panel, botones, avisos = crear_panel(estado_con_nulos, monkeypatch,
                                         al_aplicar=lambda: llamadas.append(1))
    panel.estrategia.set_value(MEDIANA)
    botones.pulsar()
    assert avisos.ultimo()[1] == "positive"
    assert estado_con_nulos.preprocesado["estrategia"] == MEDIANA
    # Tras aplicar ya no quedan nulos: la tabla se pone a 0 y se ocultan
    # los controles
    assert all(fila["train"] == 0 and fila["test"] == 0
               for fila in panel.tabla.rows)
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
    panel, botones, avisos = crear_panel(estado_con_nulos, monkeypatch,
                                         al_aplicar=lambda: llamadas.append(1))
    panel.estrategia.set_value(CONSTANTE)     # sin escribir el valor
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
    import sikorius.gui.panel_preprocesado as panel
    codigo = inspect.getsource(panel)
    assert "detectar_en_estado(" in codigo
    for prohibido in ("fillna", "dropna", "isna", "mean(", "median("):
        assert prohibido not in codigo
