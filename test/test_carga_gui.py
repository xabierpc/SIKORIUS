"""Pruebas de la carga de datasets desde la GUI (historia #14).

Cada bloque prueba una de las tareas del plan, así que se pueden ir pasando
a medida que se termina cada una:

    uv run pytest test/test_carga_gui.py -v              # todos
    uv run pytest test/test_carga_gui.py -v -k tarea1    # solo una tarea

    Tarea 1 -> sikorius/estado.py               (EstadoApp)
    Tarea 2 -> sikorius/gui/selector_archivos.py (es_archivo_permitido,
                                                  listar_carpeta)
    Tarea 3 -> sikorius/gui/tabla_datos.py       (dataframe_a_tabla)
    Tarea 6 -> sikorius/gui/app.py               (carpeta_inicial)

Las tareas 4 y 5 (la tabla y el diálogo en pantalla) se comprueban a mano
con la lista de la tarea 8, porque necesitan el navegador.

Los imports van dentro de cada test: así, si un archivo todavía no existe,
solo fallan los tests de esa tarea y no todos.
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


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


@pytest.fixture
def estado_limpio():
    """Deja vacía la instancia compartida 'estado' antes y después del test."""
    from sikorius.estado import estado

    estado.datos = None
    estado.ruta = None
    yield estado
    estado.datos = None
    estado.ruta = None


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

    archivo = crear_csv(tmp_path / "pisos.csv",
                        "superficie,precio\n60.5,121000\n95,189500\n")
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

    archivo = crear_csv(carpeta_rara / "pisos ñ á.csv",
                        "barrio,precio\nElviña,121000\nRiazor,265000\n")
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

    archivo = crear_sqlite(carpeta_rara / "base ñ.db", [
        "CREATE TABLE pisos (superficie REAL, precio INTEGER)",
        "INSERT INTO pisos VALUES (60.5, 121000)",
    ])
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
    from sikorius.importador import ErrorImportacion

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
    from sikorius.importador import ErrorImportacion

    estado = EstadoApp()

    with pytest.raises(ErrorImportacion):
        estado.cargar(tmp_path / "no_existe.csv")

    assert estado.hay_datos() is False
    assert estado.ruta is None


def test_tarea1_error_trae_mensaje_del_importador(tmp_path):
    """El mensaje que verá el usuario es el del módulo de importación."""
    from sikorius.estado import EstadoApp
    from sikorius.importador import ErrorImportacion

    archivo = crear_sqlite(tmp_path / "dos_tablas.db", [
        "CREATE TABLE a (x INTEGER)",
        "CREATE TABLE b (y INTEGER)",
    ])
    estado = EstadoApp()

    with pytest.raises(ErrorImportacion, match="más de una tabla"):
        estado.cargar(archivo)


# =============================================================================
# Tarea 2 · selector_archivos.py: filtro y listado
# =============================================================================


@pytest.mark.parametrize("nombre", [
    "datos.csv", "datos.xlsx", "datos.xls", "datos.sqlite", "datos.db",
    "DATOS.CSV", "Datos.Xlsx", "con espacios ñ.db", "a.b.csv",
])
def test_tarea2_extensiones_permitidas(nombre):
    from sikorius.gui.selector_archivos import es_archivo_permitido

    assert es_archivo_permitido(nombre)


@pytest.mark.parametrize("nombre", [
    "datos.txt", "datos.json", "datos.csv.bak", "datos", "csv", "foto.png",
    "datos.xlsm", "datos.sqlite3",
])
def test_tarea2_extensiones_no_permitidas(nombre):
    from sikorius.gui.selector_archivos import es_archivo_permitido

    assert not es_archivo_permitido(nombre)


def test_tarea2_acepta_path_y_str():
    from sikorius.gui.selector_archivos import es_archivo_permitido

    assert es_archivo_permitido(Path("/una/carpeta/datos.csv"))
    assert es_archivo_permitido("/una/carpeta/datos.csv")


def test_tarea2_listar_solo_compatibles_y_ordenado(tmp_path):
    from sikorius.gui.selector_archivos import listar_carpeta

    crear_csv(tmp_path / "b.csv", "x\n1\n")
    (tmp_path / "a.xlsx").write_bytes(b"")
    (tmp_path / "C.db").write_bytes(b"")
    (tmp_path / "notas.txt").write_text("hola", encoding="utf-8")
    crear_csv(tmp_path / ".oculto.csv", "x\n1\n")
    (tmp_path / "zeta").mkdir()
    (tmp_path / "Año 2026").mkdir()
    (tmp_path / ".git").mkdir()

    resultado = listar_carpeta(tmp_path)

    # Primero las carpetas y luego los archivos, alfabético sin mayúsculas
    assert nombres(resultado) == ["Año 2026", "zeta", "a.xlsx", "b.csv", "C.db"]


def test_tarea2_listar_devuelve_path(tmp_path):
    from sikorius.gui.selector_archivos import listar_carpeta

    crear_csv(tmp_path / "datos.csv", "x\n1\n")

    resultado = listar_carpeta(tmp_path)

    assert len(resultado) == 1
    assert isinstance(resultado[0], Path)
    assert resultado[0] == tmp_path / "datos.csv"


def test_tarea2_listar_carpeta_vacia(tmp_path):
    from sikorius.gui.selector_archivos import listar_carpeta

    assert listar_carpeta(tmp_path) == []


def test_tarea2_listar_acepta_str(tmp_path):
    from sikorius.gui.selector_archivos import listar_carpeta

    crear_csv(tmp_path / "datos.csv", "x\n1\n")

    assert nombres(listar_carpeta(str(tmp_path))) == ["datos.csv"]


def test_tarea2_listar_ignora_enlaces_rotos(tmp_path):
    from sikorius.gui.selector_archivos import listar_carpeta

    crear_csv(tmp_path / "bueno.csv", "x\n1\n")
    try:
        (tmp_path / "roto.csv").symlink_to(tmp_path / "no_existe.csv")
    except OSError:
        pytest.skip("El sistema no permite crear enlaces simbólicos")

    assert nombres(listar_carpeta(tmp_path)) == ["bueno.csv"]


def test_tarea2_listar_carpeta_con_enie(carpeta_rara):
    from sikorius.gui.selector_archivos import listar_carpeta

    crear_csv(carpeta_rara / "pisos ñ.csv", "x\n1\n")

    assert nombres(listar_carpeta(carpeta_rara)) == ["pisos ñ.csv"]


# =============================================================================
# Tarea 3 · tabla_datos.py: dataframe_a_tabla
# =============================================================================

def campos_de(columnas):
    """Lista con el 'field' de cada columna."""
    resultado = []
    for columna in columnas:
        resultado.append(columna["field"])
    return resultado


def etiquetas_de(columnas):
    """Lista con el 'label' de cada columna."""
    resultado = []
    for columna in columnas:
        resultado.append(columna["label"])
    return resultado


def test_tarea3_devuelve_tupla_de_dos_listas():
    from sikorius.gui.tabla_datos import dataframe_a_tabla

    resultado = dataframe_a_tabla(pd.DataFrame({"a": [1]}))

    assert isinstance(resultado, tuple)
    assert len(resultado) == 2
    assert isinstance(resultado[0], list)
    assert isinstance(resultado[1], list)


def test_tarea3_encabezados_son_los_nombres_de_columna():
    from sikorius.gui.tabla_datos import dataframe_a_tabla

    df = pd.DataFrame({"superficie": [60.5, 95.0], "precio": [121000, 189500]})

    columnas, filas = dataframe_a_tabla(df)

    assert etiquetas_de(columnas) == ["superficie", "precio"]


def test_tarea3_formato_de_cada_columna():
    from sikorius.gui.tabla_datos import dataframe_a_tabla

    columnas, filas = dataframe_a_tabla(pd.DataFrame({"a": [1], "b": [2]}))

    for columna in columnas:
        assert "name" in columna
        assert "label" in columna
        assert "field" in columna
        assert columna["name"] == columna["field"]
    assert len(set(campos_de(columnas))) == 2


def test_tarea3_todas_las_filas_y_valores():
    from sikorius.gui.tabla_datos import dataframe_a_tabla

    df = pd.DataFrame({"x": list(range(500)), "y": list(range(500, 1000))})

    columnas, filas = dataframe_a_tabla(df)
    campo_x = columnas[0]["field"]
    campo_y = columnas[1]["field"]

    assert len(filas) == 500
    assert filas[0][campo_x] == 0
    assert filas[499][campo_y] == 999


def test_tarea3_todas_las_columnas():
    from sikorius.gui.tabla_datos import dataframe_a_tabla

    datos = {}
    for i in range(40):
        datos["col" + str(i)] = [i]
    df = pd.DataFrame(datos)

    columnas, filas = dataframe_a_tabla(df)

    assert len(columnas) == 40
    for columna in columnas:
        assert columna["field"] in filas[0]


def test_tarea3_nombres_con_puntos_y_no_texto():
    from sikorius.gui.tabla_datos import dataframe_a_tabla

    df = pd.DataFrame({"precio.m2": [1], 2026: [2]})

    columnas, filas = dataframe_a_tabla(df)

    for campo in campos_de(columnas):
        assert "." not in campo
    assert etiquetas_de(columnas) == ["precio.m2", "2026"]
    assert filas[0][columnas[0]["field"]] == 1
    assert filas[0][columnas[1]["field"]] == 2


def test_tarea3_columnas_con_nombre_repetido():
    from sikorius.gui.tabla_datos import dataframe_a_tabla

    df = pd.DataFrame([[1, 2]], columns=["a", "a"])

    columnas, filas = dataframe_a_tabla(df)

    assert len(set(campos_de(columnas))) == 2
    assert filas[0][columnas[0]["field"]] == 1
    assert filas[0][columnas[1]["field"]] == 2


def test_tarea3_valores_vacios_son_none():
    from sikorius.gui.tabla_datos import dataframe_a_tabla

    df = pd.DataFrame({"a": [1.0, np.nan], "b": ["x", None]})

    columnas, filas = dataframe_a_tabla(df)

    assert filas[1][columnas[0]["field"]] is None
    assert filas[1][columnas[1]["field"]] is None
    assert filas[0][columnas[0]["field"]] == 1.0


def test_tarea3_ids_de_fila_unicos_aunque_el_indice_se_repita():
    from sikorius.gui.tabla_datos import dataframe_a_tabla

    df = pd.DataFrame({"a": [5, 5, 5]}, index=[7, 7, 7])

    columnas, filas = dataframe_a_tabla(df)

    ids = set()
    for fila in filas:
        ids.add(fila["_id"])
    assert len(ids) == 3


def test_tarea3_no_modifica_el_dataframe():
    from sikorius.gui.tabla_datos import dataframe_a_tabla

    df = pd.DataFrame({"a": [1.0, np.nan]})
    copia = df.copy()

    dataframe_a_tabla(df)

    pd.testing.assert_frame_equal(df, copia)


def test_tarea3_dataframe_vacio():
    from sikorius.gui.tabla_datos import dataframe_a_tabla

    columnas, filas = dataframe_a_tabla(pd.DataFrame())

    assert columnas == []
    assert filas == []


def test_tarea3_con_datos_del_importador(carpeta_rara):
    """Lo que devuelve el importador se puede pasar tal cual a la tabla."""
    from sikorius.gui.tabla_datos import dataframe_a_tabla
    from sikorius.importador import importar_datos

    archivo = crear_csv(carpeta_rara / "pisos.csv",
                        "barrio;superficie\nElviña;60,5\nRiazor;\n")
    df = importar_datos(archivo)

    columnas, filas = dataframe_a_tabla(df)

    assert etiquetas_de(columnas) == ["barrio", "superficie"]
    assert filas[0][columnas[1]["field"]] == 60.5
    assert filas[1][columnas[1]["field"]] is None


# =============================================================================
# Tarea 6 · app.py: carpeta_inicial
# =============================================================================

def test_tarea6_sin_datos_empieza_en_carpeta_personal(estado_limpio):
    from sikorius.gui.app import carpeta_inicial

    assert Path(carpeta_inicial()) == Path.home()


def test_tarea6_no_depende_de_la_carpeta_de_ejecucion(estado_limpio, tmp_path,
                                                      monkeypatch):
    from sikorius.gui.app import carpeta_inicial

    monkeypatch.chdir(tmp_path)

    assert Path(carpeta_inicial()) != tmp_path
    assert Path(carpeta_inicial()) == Path.home()


def test_tarea6_despues_de_cargar_empieza_en_su_carpeta(estado_limpio,
                                                       carpeta_rara):
    from sikorius.gui.app import carpeta_inicial

    archivo = crear_csv(carpeta_rara / "datos.csv", "x\n1\n")
    estado_limpio.cargar(archivo)

    assert Path(carpeta_inicial()) == carpeta_rara.resolve()
