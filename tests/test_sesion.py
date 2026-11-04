"""Tests de la sesión: cascada de pasos, avisos y preprocesado.

Recogen también las reglas que antes probaba tests/test_estado.py con el
estado antiguo (EstadoApp). La lectura de archivos ya no es de la sesión:
la prueban tests/nucleo/test_importador.py y tests/gui/test_panel_dataset.py.

    uv run pytest tests/test_sesion.py -v
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sikorius.nucleo.errores import AvisoPreprocesado, ErrorPreprocesado
from sikorius.nucleo.preprocesado import ESTRATEGIAS

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


def preparar(sesion, train, test, features=("x",), target="y"):
    """Carga train + test como dataset, selecciona y separa con ellos."""
    sesion.cargar_dataset(pd.concat([train, test]), "datos.csv")
    sesion.guardar_seleccion(list(features), target)
    sesion.guardar_separacion(train, test, 20, 42)
    return sesion


@pytest.fixture
def sesion_con_nulos(sesion):
    return preparar(sesion, crear_train(), crear_test())


@pytest.fixture
def sesion_sin_nulos(sesion):
    train = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    test = pd.DataFrame({"x": [4.0], "y": [8.0]})
    return preparar(sesion, train, test)


# =============================================================================
# Cascada: cambiar un paso borra los posteriores
# =============================================================================


def test_sesion_nueva_vacia(sesion):
    assert sesion.dataset is None
    assert sesion.seleccion is None
    assert sesion.separacion is None
    assert sesion.preprocesado is None
    assert sesion.modelo is None


def test_cargar_dataset_borra_los_pasos_posteriores(sesion_separada):
    sesion_separada.cargar_dataset(pd.DataFrame({"a": [1, 2]}), "otro.csv")
    assert sesion_separada.seleccion is None
    assert sesion_separada.separacion is None
    assert sesion_separada.preprocesado is None


def test_nuevo_dataset_sustituye_al_anterior(sesion, datos):
    sesion.cargar_dataset(datos, "uno.csv")
    otro = pd.DataFrame({"a": [1, 2]})
    sesion.cargar_dataset(otro, "dos.csv")
    assert sesion.dataset.datos is otro
    assert sesion.dataset.ruta.endswith("dos.csv")


def test_la_ruta_se_guarda_como_texto_absoluto(
    sesion, datos, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    sesion.cargar_dataset(datos, "datos.csv")
    assert isinstance(sesion.dataset.ruta, str)
    assert Path(sesion.dataset.ruta) == tmp_path / "datos.csv"


def test_nueva_seleccion_conserva_el_dataset(sesion_separada):
    datos = sesion_separada.dataset.datos
    sesion_separada.guardar_seleccion(["x1"], "y")
    assert sesion_separada.dataset.datos is datos
    assert sesion_separada.separacion is None


def test_guardar_separacion(sesion_con_seleccion):
    entrenamiento = pd.DataFrame({"x1": [1.0], "x2": [2.0], "y": [3.0]})
    test = pd.DataFrame({"x1": [4.0], "x2": [5.0], "y": [6.0]})
    sesion_con_seleccion.guardar_separacion(entrenamiento, test, 25, 7)
    separacion = sesion_con_seleccion.separacion
    assert separacion.entrenamiento is entrenamiento
    assert separacion.test is test
    assert separacion.porcentaje_test == 25
    assert separacion.semilla == 7


def test_repetir_separacion_descarta_el_preprocesado(sesion_separada):
    sesion_separada.aplicar_preprocesado("media")
    entrenamiento = sesion_separada.separacion.entrenamiento
    test = sesion_separada.separacion.test
    sesion_separada.guardar_separacion(entrenamiento, test, 20, 42)
    assert sesion_separada.preprocesado is None
    assert sesion_separada.modelo is None


def test_tipo_de_regresion_segun_numero_de_entradas(sesion_con_seleccion):
    assert sesion_con_seleccion.seleccion.tipo_regresion == "multiple"
    sesion_con_seleccion.guardar_seleccion(["x1"], "y")
    assert sesion_con_seleccion.seleccion.tipo_regresion == "simple"


# =============================================================================
# Avisos a la interfaz
# =============================================================================


def test_avisa_en_cada_cambio_hasta_cancelar(sesion, datos):
    avisos = []
    cancelar = sesion.al_cambiar(lambda: avisos.append("cambio"))
    sesion.cargar_dataset(datos, "datos.csv")
    cancelar()
    sesion.cargar_dataset(datos, "datos.csv")
    assert len(avisos) == 1


# =============================================================================
# columnas_modelo
# =============================================================================


def test_columnas_entradas_y_salida_al_final(sesion, datos):
    sesion.cargar_dataset(datos, "datos.csv")
    sesion.guardar_seleccion(["x2", "x1"], "y")
    assert sesion.columnas_modelo() == ["x2", "x1", "y"]


def test_columnas_cabeceras_no_texto_usan_la_columna_real(sesion):
    sesion.cargar_dataset(
        pd.DataFrame({2020: [1.0, 2.0], "y": [3.0, 4.0]}), "datos.xlsx"
    )
    sesion.guardar_seleccion(["2020"], "y")
    assert sesion.columnas_modelo() == [2020, "y"]


# =============================================================================
# detectar_nulos
# =============================================================================


def test_detectar_sin_seleccion_ni_separacion(sesion, datos):
    assert sesion.detectar_nulos() is None
    sesion.cargar_dataset(datos, "datos.csv")
    sesion.guardar_seleccion(["x1"], "y")
    assert sesion.detectar_nulos() is None


def test_detectar_con_separacion(sesion_con_nulos):
    assert sesion_con_nulos.detectar_nulos() == {
        "train": {"x": 1, "y": 1},
        "test": {"x": 1, "y": 0},
    }


def test_detectar_revisa_los_conjuntos_preprocesados(sesion_con_nulos):
    sesion_con_nulos.aplicar_preprocesado("media")
    assert sesion_con_nulos.detectar_nulos() == {
        "train": {"x": 0, "y": 0},
        "test": {"x": 0, "y": 0},
    }


# =============================================================================
# aplicar_preprocesado
# =============================================================================


def test_aplicar_sin_seleccion(sesion, datos):
    sesion.cargar_dataset(datos, "datos.csv")
    with pytest.raises(ErrorPreprocesado, match="selección"):
        sesion.aplicar_preprocesado("media")


def test_aplicar_sin_separacion(sesion_con_seleccion):
    with pytest.raises(ErrorPreprocesado, match="Separa"):
        sesion_con_seleccion.aplicar_preprocesado("media")
    assert sesion_con_seleccion.preprocesado is None


def test_aplicar_guarda_el_resultado(sesion_con_nulos):
    resumen = sesion_con_nulos.aplicar_preprocesado("eliminar")
    preprocesado = sesion_con_nulos.preprocesado
    assert preprocesado.estrategia == "eliminar"
    assert preprocesado.resumen == resumen
    assert preprocesado.entrenamiento.index.tolist() == [10, 13]
    assert preprocesado.test.index.tolist() == [21]
    # La separación original no cambia
    assert len(sesion_con_nulos.separacion.entrenamiento) == 4


def test_aplicar_parte_siempre_de_la_separacion(sesion_con_nulos):
    sesion_con_nulos.aplicar_preprocesado("media")
    resumen = sesion_con_nulos.aplicar_preprocesado("eliminar")
    # Si partiera de los datos ya rellenados no eliminaría ninguna fila
    assert resumen["train"]["filas_eliminadas"] == 2
    assert sesion_con_nulos.preprocesado.estrategia == "eliminar"


def test_aplicar_error_conserva_lo_anterior(sesion_con_nulos):
    sesion_con_nulos.aplicar_preprocesado("media")
    anterior = sesion_con_nulos.preprocesado
    avisos = []
    sesion_con_nulos.al_cambiar(lambda: avisos.append("cambio"))
    with pytest.raises(ErrorPreprocesado):
        sesion_con_nulos.aplicar_preprocesado("constante", "abc")
    assert sesion_con_nulos.preprocesado is anterior
    assert avisos == []


def test_aplicar_aviso_no_aplica_nada(sesion):
    train = pd.DataFrame({"x": [np.nan, 2.0], "y": [1.0, np.nan]})
    test = pd.DataFrame({"x": [1.0], "y": [2.0]})
    preparar(sesion, train, test)
    with pytest.raises(AvisoPreprocesado):
        sesion.aplicar_preprocesado("eliminar")
    assert sesion.preprocesado is None


def test_aplicar_con_cabeceras_no_texto(sesion):
    train = pd.DataFrame({2020: [1.0, np.nan, 3.0], "y": [1.0, 2.0, 3.0]})
    test = pd.DataFrame({2020: [4.0], "y": [4.0]})
    preparar(sesion, train, test, features=("2020",))
    sesion.aplicar_preprocesado("media")
    assert sesion.preprocesado.entrenamiento[2020].tolist() == [1.0, 2.0, 3.0]
    assert sesion.puede_crear_modelo()


# =============================================================================
# puede_crear_modelo
# =============================================================================


def test_modelo_no_disponible_sin_separacion(sesion, sesion_con_seleccion):
    assert not sesion.puede_crear_modelo()
    assert not sesion_con_seleccion.puede_crear_modelo()


def test_modelo_no_disponible_con_nulos(sesion_con_nulos):
    assert not sesion_con_nulos.puede_crear_modelo()


def test_modelo_disponible_sin_nulos_sin_preprocesar(sesion_sin_nulos):
    assert sesion_sin_nulos.preprocesado is None
    assert sesion_sin_nulos.puede_crear_modelo()


@pytest.mark.parametrize("estrategia", ESTRATEGIAS)
def test_modelo_disponible_tras_preprocesar(sesion_con_nulos, estrategia):
    sesion_con_nulos.aplicar_preprocesado(estrategia, constante=0)
    assert sesion_con_nulos.puede_crear_modelo()


def test_modelo_disponible_ignora_columnas_no_seleccionadas(sesion):
    """'otra' tiene nulos, pero no se usa en el modelo."""
    train = crear_train()[["x", "otra"]].assign(y=[1.0, 2.0, 3.0, 4.0])
    test = crear_test()[["x", "otra"]].assign(y=[5.0, 6.0])
    train["x"] = train["x"].fillna(0.0)
    test["x"] = test["x"].fillna(0.0)
    preparar(sesion, train, test)
    assert sesion.puede_crear_modelo()
