"""Pruebas del estado antiguo (EstadoApp). Archivo temporal.

Se borra en la ronda 3 junto con sikorius/estado.py, cuando test_sesion.py
cubra las mismas reglas.

    uv run pytest tests/test_estado.py -v
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sikorius.estado import EstadoApp
from sikorius.nucleo.preprocesado import (
    CONSTANTE,
    ELIMINAR,
    ESTRATEGIAS,
    MEDIA,
    AvisoPreprocesado,
    ErrorPreprocesado,
    aplicar_al_estado,
    columnas_seleccionadas,
    detectar_en_estado,
    hay_nulos,
    modelo_disponible,
)
from sikorius.nucleo.separacion import (
    separar_datos,
)

# =============================================================================
# Utilidades
# =============================================================================


def crear_df(num_filas):
    """Dataset con una columna 'id' única por fila, una feature y un target."""
    return pd.DataFrame(
        {
            "id": list(range(num_filas)),
            "x": np.arange(num_filas, dtype=float) * 1.5,
            "y": np.arange(num_filas, dtype=float) * 3.0 + 1.0,
        }
    )


@pytest.fixture
def estado_con_seleccion():
    """Estado nuevo (no la instancia compartida) con datos y selección."""
    estado = EstadoApp()
    estado.datos = crear_df(100)
    estado.guardar_seleccion(["x"], "y", "simple")
    return estado


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


# =============================================================================
# Utilidades
# =============================================================================


def crear_csv(ruta, texto):
    """Escribe un CSV en UTF-8 (creando las carpetas) y devuelve su ruta."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def crear_sqlite(ruta, sentencias):
    """Crea una base de datos SQLite con las sentencias dadas."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    for sentencia in sentencias:
        conexion.execute(sentencia)
    conexion.commit()
    conexion.close()
    return ruta


def nombres(rutas):
    """Lista con los nombres de una lista de Path."""
    resultado = []
    for ruta in rutas:
        resultado.append(ruta.name)
    return resultado


@pytest.fixture
def carpeta_rara(tmp_path):
    """Carpeta con espacios, tildes y ñ en el nombre."""
    carpeta = tmp_path / "Mis datos ñandú" / "acción y canción"
    carpeta.mkdir(parents=True)
    return carpeta


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


def test_repetir_separacion_descarta_preprocesado_y_modelo(
    estado_con_seleccion,
):
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


def test_cargar_nuevo_dataset_obliga_a_repetir_separacion(
    estado_con_seleccion, tmp_path
):
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
# columnas_seleccionadas
# =============================================================================


def test_columnas_features_y_target_al_final():
    estado = EstadoApp()
    estado.datos = pd.DataFrame({"a": [1], "b": [2], "c": [3], "d": [4]})
    estado.guardar_seleccion(["c", "a"], "b", "multiple")
    assert columnas_seleccionadas(estado) == ["c", "a", "b"]


def test_columnas_cabeceras_no_texto_usan_la_columna_real():
    """El selector guarda "2020" como texto; el DataFrame tiene el entero
    2020."""
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
    estado.seleccion = {
        "features": ["a"],
        "target": "b",
        "tipo_regresion": "simple",
    }
    assert columnas_seleccionadas(estado) == ["a", "b"]


# =============================================================================
# Estado: detectar_en_estado, aplicar_al_estado y modelo_disponible
# =============================================================================


def test_detectar_en_estado_sin_seleccion_ni_separacion():
    estado = EstadoApp()
    estado.datos = crear_train()
    assert detectar_en_estado(estado) is None
    estado.guardar_seleccion(["x"], "y", "simple")
    assert detectar_en_estado(estado) is None  # falta la separación


def test_detectar_en_estado_con_separacion(estado_con_nulos):
    assert detectar_en_estado(estado_con_nulos) == {
        "train": {"x": 1, "y": 1},
        "test": {"x": 1, "y": 0},
    }


def test_detectar_en_estado_revisa_los_conjuntos_preprocesados(
    estado_con_nulos,
):
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
    assert set(estado.preprocesado) == {
        "entrenamiento",
        "test",
        "estrategia",
        "resumen",
    }
    assert estado.preprocesado["estrategia"] == CONSTANTE
    assert estado.preprocesado["resumen"] == resumen
    assert estado.preprocesado["entrenamiento"].at[11, "x"] == 0.0
    # Los conjuntos de la separación se conservan sin preprocesar
    assert estado.entrenamiento is train_original
    assert estado.test is test_original
    assert pd.isna(estado.entrenamiento.at[11, "x"])


def test_aplicar_al_estado_parte_siempre_de_la_separacion(estado_con_nulos):
    """Aplicar dos veces no encadena: la segunda parte de los datos
    separados."""
    aplicar_al_estado(estado_con_nulos, CONSTANTE, 0)
    resumen = aplicar_al_estado(estado_con_nulos, ELIMINAR)
    assert resumen["train"]["filas_eliminadas"] == 2
    assert estado_con_nulos.preprocesado["estrategia"] == ELIMINAR
    assert len(estado_con_nulos.preprocesado["entrenamiento"]) == 2


@pytest.mark.parametrize(
    "estrategia, constante",
    [
        (CONSTANTE, "abc"),
        ("otra", None),
    ],
)
def test_aplicar_al_estado_error_conserva_lo_anterior(
    estado_con_nulos, estrategia, constante
):
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
# Tarea 1 · estado.py
# =============================================================================


def test_tarea1_estado_inicial_vacio():
    from sikorius.estado import EstadoApp

    estado = EstadoApp()

    assert estado.datos is None
    assert estado.ruta is None
    assert estado.hay_datos() is False


def test_tarea1_existe_instancia_compartida():
    from sikorius.estado import EstadoApp, estado

    assert isinstance(estado, EstadoApp)


def test_tarea1_cargar_csv_devuelve_y_guarda_datos(tmp_path):
    from sikorius.estado import EstadoApp

    archivo = crear_csv(
        tmp_path / "pisos.csv", "superficie,precio\n60.5,121000\n95,189500\n"
    )
    estado = EstadoApp()

    df = estado.cargar(archivo)

    assert isinstance(df, pd.DataFrame)
    assert estado.datos is df
    assert estado.hay_datos() is True
    assert list(df.columns) == ["superficie", "precio"]
    assert len(df) == 2


def test_tarea1_ruta_guardada_es_str_absoluto(tmp_path):
    from sikorius.estado import EstadoApp

    archivo = crear_csv(tmp_path / "datos.csv", "x\n1\n")
    estado = EstadoApp()

    estado.cargar(archivo)

    assert isinstance(estado.ruta, str)
    assert Path(estado.ruta).is_absolute()
    assert estado.ruta == str(archivo.resolve())


def test_tarea1_ruta_relativa_se_guarda_absoluta(tmp_path, monkeypatch):
    from sikorius.estado import EstadoApp

    crear_csv(tmp_path / "datos.csv", "x\n1\n")
    monkeypatch.chdir(tmp_path)
    estado = EstadoApp()

    estado.cargar("datos.csv")

    assert estado.ruta == str((tmp_path / "datos.csv").resolve())


def test_tarea1_funciona_con_espacios_tildes_y_enie(carpeta_rara):
    from sikorius.estado import EstadoApp

    archivo = crear_csv(
        carpeta_rara / "pisos ñ á.csv",
        "barrio,precio\nElviña,121000\nRiazor,265000\n",
    )
    estado = EstadoApp()

    df = estado.cargar(str(archivo))

    assert list(df["barrio"]) == ["Elviña", "Riazor"]
    assert estado.ruta == str(archivo.resolve())


def test_tarea1_funciona_desde_cualquier_carpeta(tmp_path, monkeypatch):
    from sikorius.estado import EstadoApp

    archivo = crear_csv(tmp_path / "datos" / "pisos.csv", "x\n1\n")
    otra = tmp_path / "otra carpeta"
    otra.mkdir()
    monkeypatch.chdir(otra)
    estado = EstadoApp()

    estado.cargar(archivo)

    assert estado.ruta == str(archivo.resolve())


def test_tarea1_cargar_sqlite(carpeta_rara):
    from sikorius.estado import EstadoApp

    archivo = crear_sqlite(
        carpeta_rara / "base ñ.db",
        [
            "CREATE TABLE pisos (superficie REAL, precio INTEGER)",
            "INSERT INTO pisos VALUES (60.5, 121000)",
        ],
    )
    estado = EstadoApp()

    df = estado.cargar(archivo)

    assert list(df.columns) == ["superficie", "precio"]


def test_tarea1_nuevo_archivo_sustituye_al_anterior(tmp_path):
    from sikorius.estado import EstadoApp

    primero = crear_csv(tmp_path / "uno.csv", "a\n1\n")
    segundo = crear_csv(tmp_path / "dos.csv", "b,c\n2,3\n4,5\n")
    estado = EstadoApp()

    estado.cargar(primero)
    estado.cargar(segundo)

    assert list(estado.datos.columns) == ["b", "c"]
    assert estado.ruta == str(segundo.resolve())


def test_tarea1_usa_el_modulo_de_importacion(tmp_path, monkeypatch):
    """La lectura no se reimplementa: estado.cargar llama a importar_datos."""
    import sikorius.estado as modulo_estado
    from sikorius.estado import EstadoApp

    llamadas = []
    falso = pd.DataFrame({"a": [1]})

    def importar_falso(ruta):
        llamadas.append(ruta)
        return falso

    monkeypatch.setattr(modulo_estado, "importar_datos", importar_falso)
    archivo = crear_csv(tmp_path / "datos.csv", "x\n1\n")
    estado = EstadoApp()

    df = estado.cargar(archivo)

    assert len(llamadas) == 1
    assert df is falso


@pytest.mark.parametrize("contenido", ["", "solo,cabecera\n"])
def test_tarea1_error_conserva_estado_anterior(tmp_path, contenido):
    from sikorius.estado import EstadoApp
    from sikorius.nucleo.importador import ErrorImportacion

    bueno = crear_csv(tmp_path / "bueno.csv", "a\n1\n")
    malo = crear_csv(tmp_path / "malo.csv", contenido)
    estado = EstadoApp()
    df_bueno = estado.cargar(bueno)

    with pytest.raises(ErrorImportacion):
        estado.cargar(malo)

    assert estado.datos is df_bueno
    assert estado.ruta == str(bueno.resolve())


def test_tarea1_error_sin_datos_previos(tmp_path):
    from sikorius.estado import EstadoApp
    from sikorius.nucleo.importador import ErrorImportacion

    estado = EstadoApp()

    with pytest.raises(ErrorImportacion):
        estado.cargar(tmp_path / "no_existe.csv")

    assert estado.hay_datos() is False
    assert estado.ruta is None


def test_tarea1_error_trae_mensaje_del_importador(tmp_path):
    """El mensaje que verá el usuario es el del módulo de importación."""
    from sikorius.estado import EstadoApp
    from sikorius.nucleo.importador import ErrorImportacion

    archivo = crear_sqlite(
        tmp_path / "dos_tablas.db",
        [
            "CREATE TABLE a (x INTEGER)",
            "CREATE TABLE b (y INTEGER)",
        ],
    )
    estado = EstadoApp()

    with pytest.raises(ErrorImportacion, match="más de una tabla"):
        estado.cargar(archivo)
