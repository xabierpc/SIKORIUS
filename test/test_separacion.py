"""Pruebas de la separación en entrenamiento y test (historia #41).

    uv run pytest test/test_separacion.py -v

Bloques:
    - interpretar_porcentaje: valores válidos, límites (0, 1, 99, 100) y errores.
    - interpretar_semilla: enteros válidos y errores.
    - calcular_tamanos: tamaños, redondeo exacto y conjuntos vacíos.
    - separar_datos: tamaños, sin filas repetidas, reproducibilidad, aleatoriedad.
    - EstadoApp: orden del flujo (selección -> separación -> preprocesado/modelo).
    - PanelSeparacion: el panel de la GUI, sin servidor.
"""

import math

import numpy as np
import pandas as pd
import pytest
from nicegui import ui

from sikorius.estado import EstadoApp
from sikorius.separacion import (
    FILAS_MINIMAS, PORCENTAJE_TEST_DEFECTO, SEMILLA_DEFECTO, ErrorSeparacion,
    calcular_tamanos, interpretar_porcentaje, interpretar_semilla,
    separar_datos,
)


# =============================================================================
# Utilidades
# =============================================================================

def crear_df(num_filas):
    """Dataset con una columna 'id' única por fila, una feature y un target."""
    return pd.DataFrame({
        "id": list(range(num_filas)),
        "x": np.arange(num_filas, dtype=float) * 1.5,
        "y": np.arange(num_filas, dtype=float) * 3.0 + 1.0,
    })


def ids(df):
    """Conjunto con los valores de la columna 'id'."""
    return set(df["id"].tolist())


def filas_test_esperadas(num_filas, porcentaje_texto):
    """Filas de test calculadas solo con enteros (sin coma flotante).

    porcentaje_texto es un texto con como mucho dos decimales, p. ej. "64.4".
    """
    partes = porcentaje_texto.split(".")
    entero = int(partes[0])
    decimales = 0
    if len(partes) == 2:
        decimales = int(partes[1].ljust(2, "0"))
    centesimas = entero * 100 + decimales      # porcentaje * 100
    numerador = num_filas * centesimas
    denominador = 10000
    resultado = numerador // denominador
    if numerador % denominador != 0:
        resultado = resultado + 1
    return resultado


@pytest.fixture
def estado_con_seleccion():
    """Estado nuevo (no la instancia compartida) con datos y selección."""
    estado = EstadoApp()
    estado.datos = crear_df(100)
    estado.guardar_seleccion(["x"], "y", "simple")
    return estado


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


# =============================================================================
# interpretar_porcentaje
# =============================================================================

def test_valores_por_defecto():
    assert PORCENTAJE_TEST_DEFECTO == 20
    assert SEMILLA_DEFECTO == 42
    assert FILAS_MINIMAS == 5


@pytest.mark.parametrize("valor, esperado", [
    (1, 1.0), (99, 99.0), ("1", 1.0), ("99", 99.0), ("20", 20.0),
    ("12.5", 12.5), ("12,5", 12.5), ("  30  ", 30.0), (50.0, 50.0),
    ("1e1", 10.0), (np.int64(25), 25.0), (np.float64(33.3), 33.3),
])
def test_porcentaje_valido(valor, esperado):
    assert interpretar_porcentaje(valor) == esperado


@pytest.mark.parametrize("valor", [
    0, 100, "0", "100", -5, "-1", 0.99, 99.01, "99.5", 1000,
    "abc", "", "   ", None, "nan", "inf", "-inf", float("nan"),
    True, False, [20], "20%", "1,2,3", "12.5.1",
])
def test_porcentaje_no_valido(valor):
    with pytest.raises(ErrorSeparacion, match="entre 1 y 99"):
        interpretar_porcentaje(valor)


# =============================================================================
# interpretar_semilla
# =============================================================================

@pytest.mark.parametrize("valor, esperado", [
    (0, 0), (42, 42), ("42", 42), (" 7 ", 7), ("+3", 3), (5.0, 5),
    (np.int64(9), 9), (2 ** 40, 2 ** 40), (str(2 ** 63), 2 ** 63),
])
def test_semilla_valida(valor, esperado):
    resultado = interpretar_semilla(valor)
    assert resultado == esperado
    assert isinstance(resultado, int)


@pytest.mark.parametrize("valor", [
    "4.5", 4.5, "4.0", "-1", -1, "", "   ", None, "abc", "1e3",
    True, False, float("nan"), float("inf"), [1],
])
def test_semilla_no_valida(valor):
    with pytest.raises(ErrorSeparacion, match="entero"):
        interpretar_semilla(valor)


# =============================================================================
# calcular_tamanos
# =============================================================================

@pytest.mark.parametrize("num_filas, porcentaje, esperado", [
    (100, 20, (80, 20)),
    (101, 20, (80, 21)),      # se redondea hacia arriba, como scikit-learn
    (5, 20, (4, 1)),
    (5, 1, (4, 1)),           # 0.05 filas -> 1 fila de test
    (100, 99, (1, 99)),
    (1000, 12.3, (877, 123)),
    (250, 64.4, (89, 161)),   # antes salía 162 por un error de coma flotante
    (375, 8.8, (342, 33)),
    (625, 1.12, (618, 7)),
])
def test_tamanos(num_filas, porcentaje, esperado):
    assert calcular_tamanos(num_filas, porcentaje) == esperado


@pytest.mark.parametrize("num_filas", [0, 1, 2, 3, 4])
def test_menos_de_cinco_filas(num_filas):
    with pytest.raises(ErrorSeparacion, match="al menos 5"):
        calcular_tamanos(num_filas, 20)


@pytest.mark.parametrize("num_filas, porcentaje", [(5, 99), (10, 99), (5, 81)])
def test_entrenamiento_quedaria_vacio(num_filas, porcentaje):
    with pytest.raises(ErrorSeparacion, match="entrenamiento quedaría vacío"):
        calcular_tamanos(num_filas, porcentaje)


def test_mensaje_conjunto_vacio_explica_porcentaje_y_filas():
    with pytest.raises(ErrorSeparacion) as error:
        calcular_tamanos(20, 99)
    texto = str(error.value)
    assert "99 %" in texto
    assert "20 filas" in texto


def test_mensaje_con_porcentaje_decimal():
    with pytest.raises(ErrorSeparacion) as error:
        calcular_tamanos(10, 95.5)
    assert "95.5 %" in str(error.value)


def test_conjuntos_nunca_vacios_y_suman_el_total():
    """Fuerza muchas combinaciones: o hay error o los dos conjuntos tienen filas."""
    for num_filas in range(5, 120):
        for porcentaje in range(1, 100):
            try:
                entrenamiento, test = calcular_tamanos(num_filas, porcentaje)
            except ErrorSeparacion:
                assert math.ceil(num_filas * porcentaje / 100) == num_filas
                continue
            assert entrenamiento >= 1
            assert test >= 1
            assert entrenamiento + test == num_filas


def test_redondeo_exacto_con_decimales():
    """Compara con una cuenta hecha solo con enteros para miles de casos."""
    fallos = []
    for num_filas in [5, 7, 13, 99, 100, 101, 250, 375, 500, 625, 750, 1000, 1999]:
        for centesimas in range(100, 9901, 7):
            texto = str(centesimas // 100) + "." + str(centesimas % 100).rjust(2, "0")
            porcentaje = interpretar_porcentaje(texto)
            esperado = filas_test_esperadas(num_filas, texto)
            if esperado >= num_filas:
                continue
            obtenido = calcular_tamanos(num_filas, porcentaje)[1]
            if obtenido != esperado:
                fallos.append((num_filas, texto, obtenido, esperado))
    assert fallos == []


# =============================================================================
# separar_datos
# =============================================================================

def test_por_defecto_80_20():
    entrenamiento, test = separar_datos(crear_df(100))
    assert len(entrenamiento) == 80
    assert len(test) == 20


@pytest.mark.parametrize("num_filas, porcentaje", [
    (5, 1), (5, 20), (10, 50), (100, 1), (100, 30), (100, 98),
    (101, 33.3), (1000, 12.3), (250, 64.4),
])
def test_tamanos_corresponden_al_porcentaje(num_filas, porcentaje):
    entrenamiento, test = separar_datos(crear_df(num_filas), porcentaje, 7)
    esperado_entrenamiento, esperado_test = calcular_tamanos(num_filas, porcentaje)
    assert len(test) == esperado_test
    assert len(entrenamiento) == esperado_entrenamiento


@pytest.mark.parametrize("semilla", [0, 1, 42, 123456])
def test_ninguna_fila_en_los_dos_conjuntos(semilla):
    df = crear_df(57)
    entrenamiento, test = separar_datos(df, 25, semilla)
    assert ids(entrenamiento) & ids(test) == set()
    assert ids(entrenamiento) | ids(test) == ids(df)
    assert set(entrenamiento.index) & set(test.index) == set()


def test_misma_semilla_misma_separacion():
    df = crear_df(200)
    a_entrenamiento, a_test = separar_datos(df, 20, 42)
    b_entrenamiento, b_test = separar_datos(df.copy(), "20", "42")
    pd.testing.assert_frame_equal(a_entrenamiento, b_entrenamiento)
    pd.testing.assert_frame_equal(a_test, b_test)


def test_misma_semilla_siempre_igual_muchas_veces():
    df = crear_df(50)
    primera = ids(separar_datos(df, 30, 5)[1])
    for _ in range(20):
        assert ids(separar_datos(df, 30, 5)[1]) == primera


def test_distinta_semilla_distinta_separacion():
    df = crear_df(200)
    distintas = set()
    for semilla in range(10):
        distintas.add(frozenset(ids(separar_datos(df, 20, semilla)[1])))
    assert len(distintas) > 1


def test_la_separacion_es_aleatoria_no_las_ultimas_filas():
    df = crear_df(100)
    test = separar_datos(df, 20, 42)[1]
    assert ids(test) != set(range(80, 100))
    assert ids(test) != set(range(0, 20))


def test_se_conservan_columnas_valores_e_indice_original():
    df = crear_df(30)
    df.index = [i * 10 for i in range(30)]
    entrenamiento, test = separar_datos(df, 20, 1)
    assert list(entrenamiento.columns) == list(df.columns)
    assert list(test.columns) == list(df.columns)
    for indice, fila in pd.concat([entrenamiento, test]).iterrows():
        pd.testing.assert_series_equal(fila, df.loc[indice], check_names=False)


def test_conjuntos_ordenados_como_el_original():
    entrenamiento, test = separar_datos(crear_df(40), 25, 3)
    assert list(entrenamiento["id"]) == sorted(entrenamiento["id"])
    assert list(test["id"]) == sorted(test["id"])


def test_indice_con_repetidos():
    df = crear_df(20)
    df.index = [0] * 20
    entrenamiento, test = separar_datos(df, 25, 9)
    assert len(test) == 5
    assert len(entrenamiento) == 15
    assert ids(entrenamiento) & ids(test) == set()


def test_no_modifica_el_dataframe_original():
    df = crear_df(30)
    copia = df.copy()
    entrenamiento, test = separar_datos(df, 20, 1)
    entrenamiento.iloc[0, 0] = -999
    test.iloc[0, 0] = -999
    pd.testing.assert_frame_equal(df, copia)


def test_admite_valores_inexistentes_en_los_datos():
    df = crear_df(20)
    df.loc[3, "x"] = np.nan
    df.loc[7, "y"] = None
    entrenamiento, test = separar_datos(df, 20, 0)
    assert len(entrenamiento) + len(test) == 20
    total = int(entrenamiento.isna().sum().sum()) + int(test.isna().sum().sum())
    assert total == 2


def test_dataset_grande():
    entrenamiento, test = separar_datos(crear_df(100000), 20, 42)
    assert len(test) == 20000
    assert len(entrenamiento) == 80000
    assert ids(entrenamiento) & ids(test) == set()


@pytest.mark.parametrize("porcentaje, semilla, texto", [
    (0, 42, "entre 1 y 99"), (100, 42, "entre 1 y 99"), ("abc", 42, "entre 1 y 99"),
    (20, "4.5", "entero"), (20, "abc", "entero"), (20, -1, "entero"),
])
def test_errores_de_parametros(porcentaje, semilla, texto):
    with pytest.raises(ErrorSeparacion, match=texto):
        separar_datos(crear_df(50), porcentaje, semilla)


@pytest.mark.parametrize("num_filas", [0, 1, 4])
def test_error_menos_de_cinco_filas(num_filas):
    with pytest.raises(ErrorSeparacion, match="al menos 5"):
        separar_datos(crear_df(num_filas), 20, 42)


def test_error_conjunto_vacio():
    with pytest.raises(ErrorSeparacion, match="vacío"):
        separar_datos(crear_df(6), 99, 42)


# =============================================================================
# EstadoApp: orden del flujo de trabajo
# =============================================================================

def test_estado_inicial_sin_separacion():
    estado = EstadoApp()
    assert not estado.hay_seleccion()
    assert not estado.hay_separacion()
    assert estado.entrenamiento is None
    assert estado.test is None
    assert estado.separacion is None
    assert estado.preprocesado is None
    assert estado.modelo is None


def test_guardar_separacion(estado_con_seleccion):
    estado = estado_con_seleccion
    entrenamiento, test = separar_datos(estado.datos, 25, 3)
    estado.guardar_separacion(entrenamiento, test, 25.0, 3)
    assert estado.hay_separacion()
    assert estado.entrenamiento is entrenamiento
    assert estado.test is test
    assert estado.separacion == {"porcentaje_test": 25.0, "semilla": 3}


def test_repetir_separacion_descarta_preprocesado_y_modelo(estado_con_seleccion):
    estado = estado_con_seleccion
    estado.guardar_separacion(*separar_datos(estado.datos, 20, 1), 20, 1)
    estado.preprocesado = {"algo": 1}
    estado.modelo = "modelo"
    estado.guardar_separacion(*separar_datos(estado.datos, 30, 2), 30, 2)
    assert estado.preprocesado is None
    assert estado.modelo is None
    assert len(estado.test) == 30


def test_cambiar_seleccion_obliga_a_repetir_separacion(estado_con_seleccion):
    estado = estado_con_seleccion
    estado.guardar_separacion(*separar_datos(estado.datos, 20, 1), 20, 1)
    estado.preprocesado = {"algo": 1}
    estado.modelo = "modelo"
    estado.guardar_seleccion(["x", "id"], "y", "multiple")
    assert estado.hay_seleccion()
    assert not estado.hay_separacion()
    assert estado.separacion is None
    assert estado.preprocesado is None
    assert estado.modelo is None


def test_borrar_seleccion_borra_separacion(estado_con_seleccion):
    estado = estado_con_seleccion
    estado.guardar_separacion(*separar_datos(estado.datos, 20, 1), 20, 1)
    estado.borrar_seleccion()
    assert not estado.hay_seleccion()
    assert not estado.hay_separacion()


def test_cargar_nuevo_dataset_obliga_a_repetir_separacion(estado_con_seleccion,
                                                         tmp_path):
    estado = estado_con_seleccion
    estado.guardar_separacion(*separar_datos(estado.datos, 20, 1), 20, 1)
    estado.modelo = "modelo"
    ruta = tmp_path / "nuevo.csv"
    crear_df(12).to_csv(ruta, index=False)
    estado.cargar(ruta)
    assert len(estado.datos) == 12
    assert not estado.hay_seleccion()
    assert not estado.hay_separacion()
    assert estado.modelo is None


def test_hay_separacion_necesita_los_dos_conjuntos():
    estado = EstadoApp()
    estado.entrenamiento = crear_df(5)
    assert not estado.hay_separacion()
    estado.test = crear_df(5)
    assert estado.hay_separacion()


# =============================================================================
# PanelSeparacion (GUI sin servidor)
# =============================================================================

def crear_panel(estado, monkeypatch, al_separar=None):
    from sikorius.gui.panel_separacion import PanelSeparacion
    avisos = Avisos(monkeypatch)
    panel = PanelSeparacion(estado, al_separar=al_separar)
    return panel, avisos


def test_panel_valores_por_defecto(estado_con_seleccion, monkeypatch):
    panel, _ = crear_panel(estado_con_seleccion, monkeypatch)
    assert panel.entrada_porcentaje.value == "20"
    assert panel.entrada_semilla.value == "42"
    assert panel.etiqueta_entrenamiento.text == "Entrenamiento: 80 %"
    assert panel.etiqueta_resultado.text == ""


def test_panel_deshabilitado_sin_seleccion(monkeypatch):
    estado = EstadoApp()
    estado.datos = crear_df(50)
    panel, avisos = crear_panel(estado, monkeypatch)
    assert not panel.boton_separar.enabled
    assert not panel.entrada_porcentaje.enabled
    assert not panel.entrada_semilla.enabled
    assert "Confirma primero" in panel.aviso.text
    panel.separar()
    assert avisos.ultimo()[1] == "negative"
    assert not estado.hay_separacion()


def test_panel_se_habilita_al_confirmar_seleccion(monkeypatch):
    estado = EstadoApp()
    estado.datos = crear_df(50)
    panel, _ = crear_panel(estado, monkeypatch)
    estado.guardar_seleccion(["x"], "y", "simple")
    panel.actualizar()
    assert panel.boton_separar.enabled
    assert panel.entrada_porcentaje.enabled
    assert panel.entrada_semilla.enabled
    assert panel.aviso.text == ""


@pytest.mark.parametrize("texto, esperado", [
    ("20", "Entrenamiento: 80 %"), ("1", "Entrenamiento: 99 %"),
    ("99", "Entrenamiento: 1 %"), ("12.5", "Entrenamiento: 87.5 %"),
    ("12,5", "Entrenamiento: 87.5 %"), ("33.33", "Entrenamiento: 66.67 %"),
    ("0", "Entrenamiento: -"), ("100", "Entrenamiento: -"),
    ("abc", "Entrenamiento: -"), ("", "Entrenamiento: -"),
])
def test_panel_entrenamiento_es_el_complementario(estado_con_seleccion,
                                                  monkeypatch, texto, esperado):
    panel, _ = crear_panel(estado_con_seleccion, monkeypatch)
    panel.entrada_porcentaje.set_value(texto)
    assert panel.etiqueta_entrenamiento.text == esperado


def test_panel_separar_correcto(estado_con_seleccion, monkeypatch):
    llamadas = []
    panel, avisos = crear_panel(estado_con_seleccion, monkeypatch,
                                al_separar=lambda: llamadas.append(1))
    panel.separar()
    estado = estado_con_seleccion
    assert estado.hay_separacion()
    assert len(estado.entrenamiento) == 80
    assert len(estado.test) == 20
    assert estado.separacion == {"porcentaje_test": 20.0, "semilla": 42}
    mensaje, tipo = avisos.ultimo()
    assert tipo == "positive"
    assert "correctamente" in mensaje
    assert "80 filas" in mensaje
    assert "20 filas" in mensaje
    assert panel.etiqueta_resultado.text == "Entrenamiento: 80 filas | Test: 20 filas"
    assert llamadas == [1]


def test_panel_separar_con_otros_valores(estado_con_seleccion, monkeypatch):
    panel, _ = crear_panel(estado_con_seleccion, monkeypatch)
    panel.entrada_porcentaje.set_value("35")
    panel.entrada_semilla.set_value("7")
    panel.separar()
    estado = estado_con_seleccion
    assert len(estado.test) == 35
    assert len(estado.entrenamiento) == 65
    esperado = separar_datos(estado.datos, 35, 7)[1]
    pd.testing.assert_frame_equal(estado.test, esperado)


@pytest.mark.parametrize("porcentaje", ["0", "100", "abc", "", "-5", "150"])
def test_panel_porcentaje_no_valido(estado_con_seleccion, monkeypatch, porcentaje):
    llamadas = []
    panel, avisos = crear_panel(estado_con_seleccion, monkeypatch,
                                al_separar=lambda: llamadas.append(1))
    panel.entrada_porcentaje.set_value(porcentaje)
    panel.separar()
    mensaje, tipo = avisos.ultimo()
    assert tipo == "negative"
    assert "entre 1 y 99" in mensaje
    assert not estado_con_seleccion.hay_separacion()
    assert llamadas == []


@pytest.mark.parametrize("semilla", ["4.5", "abc", "", "-1"])
def test_panel_semilla_no_valida(estado_con_seleccion, monkeypatch, semilla):
    panel, avisos = crear_panel(estado_con_seleccion, monkeypatch)
    panel.entrada_semilla.set_value(semilla)
    panel.separar()
    mensaje, tipo = avisos.ultimo()
    assert tipo == "negative"
    assert "entero" in mensaje
    assert not estado_con_seleccion.hay_separacion()


def test_panel_dataset_con_pocas_filas(monkeypatch):
    estado = EstadoApp()
    estado.datos = crear_df(4)
    estado.guardar_seleccion(["x"], "y", "simple")
    panel, avisos = crear_panel(estado, monkeypatch)
    panel.separar()
    mensaje, tipo = avisos.ultimo()
    assert tipo == "negative"
    assert "al menos 5" in mensaje
    assert not estado.hay_separacion()


def test_panel_conjunto_vacio(monkeypatch):
    estado = EstadoApp()
    estado.datos = crear_df(5)
    estado.guardar_seleccion(["x"], "y", "simple")
    panel, avisos = crear_panel(estado, monkeypatch)
    panel.entrada_porcentaje.set_value("99")
    panel.separar()
    mensaje, tipo = avisos.ultimo()
    assert tipo == "negative"
    assert "vacío" in mensaje


def test_panel_error_conserva_separacion_anterior(estado_con_seleccion, monkeypatch):
    panel, _ = crear_panel(estado_con_seleccion, monkeypatch)
    panel.separar()
    test_anterior = estado_con_seleccion.test
    panel.entrada_porcentaje.set_value("100")
    panel.separar()
    assert estado_con_seleccion.test is test_anterior


def test_panel_repetir_separacion_descarta_preprocesado(estado_con_seleccion,
                                                        monkeypatch):
    panel, _ = crear_panel(estado_con_seleccion, monkeypatch)
    panel.separar()
    estado_con_seleccion.preprocesado = {"algo": 1}
    estado_con_seleccion.modelo = "modelo"
    panel.entrada_semilla.set_value("1")
    panel.separar()
    assert estado_con_seleccion.preprocesado is None
    assert estado_con_seleccion.modelo is None
    assert estado_con_seleccion.separacion["semilla"] == 1


def test_panel_cambio_de_seleccion_borra_resultado(estado_con_seleccion,
                                                   monkeypatch):
    panel, _ = crear_panel(estado_con_seleccion, monkeypatch)
    panel.separar()
    assert panel.etiqueta_resultado.text != ""
    estado_con_seleccion.borrar_seleccion()
    panel.actualizar()
    assert panel.etiqueta_resultado.text == ""
    assert not panel.boton_separar.enabled


def test_panel_misma_entrada_misma_separacion(estado_con_seleccion, monkeypatch):
    panel, _ = crear_panel(estado_con_seleccion, monkeypatch)
    panel.separar()
    primera = ids(estado_con_seleccion.test)
    panel.separar()
    assert ids(estado_con_seleccion.test) == primera


def test_panel_no_contiene_logica_de_separacion():
    """La GUI llama a separar_datos; no baraja filas por su cuenta."""
    import inspect
    import sikorius.gui.panel_separacion as panel
    codigo = inspect.getsource(panel)
    assert "separar_datos(" in codigo
    assert "permutation" not in codigo
    assert "sample(" not in codigo
