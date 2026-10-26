"""Pruebas de caja blanca del módulo de importación.

Cada función del módulo se prueba por separado y cada test indica entre
corchetes la rama del código que recorre, por ejemplo [I1] o [S4]. El mapa
completo de ramas está al principio de cada sección.

Los tests marcados con ``xfail(strict=True)`` documentan FALLOS REALES del
código actual: hoy fallan a propósito. Cuando se corrija el fallo, el test
pasará y pytest avisará con XPASS(strict); en ese momento hay que quitar el
marcador ``xfail``.

Ejecución con cobertura de ramas:
    uv run --with pytest-cov pytest --cov=sikorius.importador --cov-branch \
        --cov-report=term-missing
"""

import ast
import csv
import hashlib
import random
import sqlite3
import warnings
from pathlib import Path

import pandas as pd
import pytest

import sikorius.importador as importador
from sikorius.importador import (
    ErrorImportacion,
    _convertir_numericas,
    _leer_csv,
    _leer_excel,
    _leer_sqlite,
    _leer_texto,
    importar_datos,
)


# --- Utilidades ---------------------------------------------------------------

@pytest.fixture
def datos():
    return pd.DataFrame({
        "barrio": ["Elviña", "Os Mallos", "Riazor"],
        "superficie": [60.25, 95.0, 110.0],
        "precio": [121000, 189500, 265000],
    })


def escribir(ruta, contenido):
    """Escribe texto (UTF-8) o bytes en la ruta y la devuelve."""
    if isinstance(contenido, str):
        contenido = contenido.encode("utf-8")
    ruta.write_bytes(contenido)
    return ruta


def crear_sqlite(ruta, sentencias):
    """Crea una base de datos SQLite ejecutando las sentencias dadas."""
    conexion = sqlite3.connect(ruta)
    for sentencia in sentencias:
        conexion.execute(sentencia)
    conexion.commit()
    conexion.close()
    return ruta


class Espia:
    """Sustituye a una función y guarda los argumentos con que se llama."""

    def __init__(self, devolver=None, lanzar=None):
        self.llamadas = []
        self.devolver = devolver
        self.lanzar = lanzar

    def __call__(self, *args, **kwargs):
        self.llamadas.append((args, kwargs))
        if self.lanzar is not None:
            raise self.lanzar
        return self.devolver


DF_UNO = pd.DataFrame({"a": [1]})


# =============================================================================
# importar_datos
#   [I1] la ruta no es un archivo            -> ErrorImportacion "no existe"
#   [I2] extensión .csv                      -> _leer_csv
#   [I3] extensión .xlsx / .xls              -> _leer_excel
#   [I4] extensión .sqlite / .db             -> _leer_sqlite
#   [I5] cualquier otra extensión            -> ErrorImportacion "no soportada"
#   [I6] el lector devuelve un df vacío      -> ErrorImportacion "no contiene"
#   [I7] el lector devuelve datos            -> _convertir_numericas
# =============================================================================

@pytest.fixture
def espias_lectores(monkeypatch):
    """Sustituye los tres lectores por espías que devuelven DF_UNO."""
    espias = {
        "_leer_csv": Espia(DF_UNO.copy()),
        "_leer_excel": Espia(DF_UNO.copy()),
        "_leer_sqlite": Espia(DF_UNO.copy()),
    }
    for nombre, espia in espias.items():
        monkeypatch.setattr(importador, nombre, espia)
    return espias


def test_I1_ruta_inexistente(tmp_path, espias_lectores):
    with pytest.raises(ErrorImportacion, match="no existe"):
        importar_datos(tmp_path / "nada.csv")
    assert all(not e.llamadas for e in espias_lectores.values())


def test_I1_carpeta_con_extension_valida(tmp_path, espias_lectores):
    (tmp_path / "carpeta.csv").mkdir()
    with pytest.raises(ErrorImportacion):
        importar_datos(tmp_path / "carpeta.csv")
    assert all(not e.llamadas for e in espias_lectores.values())


def test_I1_enlace_simbolico_roto(tmp_path):
    enlace = tmp_path / "roto.csv"
    try:
        enlace.symlink_to(tmp_path / "destino_que_no_existe.csv")
    except OSError:
        # Windows solo deja crearlos como administrador o en modo desarrollador
        pytest.skip("El sistema no permite crear enlaces simbólicos")
    with pytest.raises(ErrorImportacion, match="no existe"):
        importar_datos(enlace)


def test_I1_cadena_vacia(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ErrorImportacion, match="no existe"):
        importar_datos("")


@pytest.mark.parametrize("nombre, lector", [
    ("a.csv", "_leer_csv"), ("a.CSV", "_leer_csv"), ("a.CsV", "_leer_csv"),
    ("a.xlsx", "_leer_excel"), ("a.XLSX", "_leer_excel"),
    ("a.xls", "_leer_excel"), ("a.Xls", "_leer_excel"),
    ("a.sqlite", "_leer_sqlite"), ("a.SQLITE", "_leer_sqlite"),
    ("a.db", "_leer_sqlite"), ("a.DB", "_leer_sqlite"),
    ("a.b.c.csv", "_leer_csv"), ("datos.xlsx.db", "_leer_sqlite"),
])
def test_I2_I3_I4_despacho_por_extension(tmp_path, espias_lectores, nombre,
                                         lector):
    ruta = escribir(tmp_path / nombre, "x")
    importar_datos(ruta)
    for nombre_espia, espia in espias_lectores.items():
        esperadas = 1 if nombre_espia == lector else 0
        assert len(espia.llamadas) == esperadas
    # el lector recibe un Path, no la cadena original
    (argumento,), _ = espias_lectores[lector].llamadas[0]
    assert isinstance(argumento, Path)


@pytest.mark.parametrize("nombre", [
    "a.txt", "a.json", "a.xlsm", "a.tsv", "a.csv.bak", "a.csv ", "a.",
    "sin_extension", ".csv", "a.sqlite3",
])
def test_I5_extension_no_soportada(tmp_path, espias_lectores, nombre):
    ruta = escribir(tmp_path / nombre, "a,b\n1,2\n")
    with pytest.raises(ErrorImportacion, match="no soportada"):
        importar_datos(ruta)
    assert all(not e.llamadas for e in espias_lectores.values())


@pytest.mark.parametrize("vacio", [
    pd.DataFrame(),                       # sin filas ni columnas
    pd.DataFrame(columns=["a", "b"]),     # columnas pero sin filas
    pd.DataFrame(index=[0, 1]),           # filas pero sin columnas
])
def test_I6_lector_devuelve_vacio(tmp_path, monkeypatch, vacio):
    monkeypatch.setattr(importador, "_leer_csv", Espia(vacio))
    espia_conv = Espia(DF_UNO)
    monkeypatch.setattr(importador, "_convertir_numericas", espia_conv)
    with pytest.raises(ErrorImportacion, match="no contiene datos"):
        importar_datos(escribir(tmp_path / "a.csv", "x"))
    assert not espia_conv.llamadas


def test_I7_devuelve_resultado_de_convertir(tmp_path, monkeypatch):
    leido = pd.DataFrame({"a": ["1"]})
    convertido = pd.DataFrame({"a": [1]})
    monkeypatch.setattr(importador, "_leer_csv", Espia(leido))
    espia_conv = Espia(convertido)
    monkeypatch.setattr(importador, "_convertir_numericas", espia_conv)
    assert importar_datos(escribir(tmp_path / "a.csv", "x")) is convertido
    assert espia_conv.llamadas[0][0][0] is leido


def test_I_acepta_objeto_pathlike(tmp_path, datos):
    ruta = tmp_path / "a.csv"
    datos.to_csv(ruta, index=False)

    class RutaPropia:
        def __fspath__(self):
            return str(ruta)

    assert len(importar_datos(RutaPropia())) == 3


@pytest.mark.parametrize("carpeta, archivo", [
    ("con espacios", "mis datos.csv"),
    ("año 2026", "señal.csv"),
    ("canción ÁÉÍÓÚ ü", "ñandú.csv"),
    ("中文", "データ.csv"),
])
def test_I_rutas_con_caracteres_especiales(tmp_path, datos, carpeta, archivo):
    (tmp_path / carpeta).mkdir()
    ruta = tmp_path / carpeta / archivo
    datos.to_csv(ruta, index=False)
    assert len(importar_datos(ruta)) == 3
    assert len(importar_datos(str(ruta))) == 3


def test_I_ruta_relativa_con_puntos(tmp_path, datos, monkeypatch):
    (tmp_path / "a" / "b").mkdir(parents=True)
    datos.to_csv(tmp_path / "a" / "datos.csv", index=False)
    monkeypatch.chdir(tmp_path / "a" / "b")
    assert len(importar_datos("../datos.csv")) == 3
    assert len(importar_datos("./../b/../datos.csv")) == 3


@pytest.mark.parametrize("argumento", [None, b"datos.csv", 123, 1.5, []])
def test_I_tipo_de_argumento_invalido(argumento):
    with pytest.raises(ErrorImportacion):
        importar_datos(argumento)


# =============================================================================
# _convertir_numericas
#   [C1] la columna ya es numérica           -> no se toca
#   [C2] texto convertible                   -> pasa a número
#   [C3] texto no convertible (ValueError)   -> se deja igual
#   [C4] valores no escalares (TypeError)    -> se deja igual
#   [C5] DataFrame sin columnas              -> el bucle no se ejecuta
# =============================================================================

def test_C1_columnas_numericas_no_se_tocan(monkeypatch):
    df = pd.DataFrame({"i": [1, 2], "f": [1.5, 2.5], "b": [True, False],
                       "t": ["1", "2"]})
    real = pd.to_numeric
    llamadas = []

    def espia(serie, *a, **k):
        llamadas.append(serie.name)
        return real(serie, *a, **k)

    monkeypatch.setattr(pd, "to_numeric", espia)
    _convertir_numericas(df)
    assert llamadas == ["t"]
    assert df["b"].dtype == bool


@pytest.mark.parametrize("valores, esperado", [
    (["1", "2", "3"], [1, 2, 3]),
    (["1.5", "-2", "3e2"], [1.5, -2.0, 300.0]),
    ([" 7 ", "8"], [7, 8]),
    (["1", None], [1.0, None]),
    (["", "1"], [None, 1.0]),          # la cadena vacía cuenta como hueco
])
def test_C2_texto_numerico_se_convierte(valores, esperado):
    df = _convertir_numericas(pd.DataFrame({"x": valores}))
    assert pd.api.types.is_numeric_dtype(df["x"])
    obtenido = [None if pd.isna(v) else v for v in df["x"]]
    assert obtenido == esperado


@pytest.mark.parametrize("valores", [
    ["1", "a"], ["1,5", "2,5"], ["1.2.3"], ["Elviña"],
    ["True", "False"], ["1 000"], ["12€"],
])
def test_C3_texto_no_numerico_se_mantiene(valores):
    df = _convertir_numericas(pd.DataFrame({"x": valores}))
    assert df["x"].tolist() == valores


def test_C4_valores_no_escalares_no_rompen():
    df = pd.DataFrame({"x": [[1], [2]], "y": [{"a": 1}, {"b": 2}]})
    resultado = _convertir_numericas(df)
    assert resultado["x"].tolist() == [[1], [2]]


def test_C4_columnas_duplicadas_no_rompen():
    df = pd.DataFrame([["1", "2"]], columns=["x", "x"])
    assert _convertir_numericas(df).shape == (1, 2)


def test_C5_sin_columnas():
    df = pd.DataFrame(index=[0, 1])
    assert _convertir_numericas(df) is df


def test_C_modifica_y_devuelve_el_mismo_objeto():
    df = pd.DataFrame({"x": ["1"]})
    assert _convertir_numericas(df) is df


def test_C_bytes_de_sqlite_no_rompen():
    df = pd.DataFrame({"b": [b"\x00\x01", b"\xff"]})
    assert _convertir_numericas(df)["b"].tolist() == [b"\x00\x01", b"\xff"]


def test_C_fechas_no_se_convierten_en_enteros():
    df = pd.DataFrame({"f": pd.to_datetime(["2024-01-01", "2024-06-30"])})
    assert pd.api.types.is_datetime64_any_dtype(_convertir_numericas(df)["f"])


def test_C_duraciones_no_se_convierten_en_enteros():
    df = pd.DataFrame({"t": pd.to_timedelta([1, 2], unit="h")})
    assert pd.api.types.is_timedelta64_dtype(_convertir_numericas(df)["t"])


def test_C_LIMITACION_ceros_a_la_izquierda_se_pierden():
    """Códigos postales o DNI tipo '01001' pasan a 1001. Es lo que pide el
    criterio (todo lo numérico es número), pero conviene saberlo."""
    df = _convertir_numericas(pd.DataFrame({"cp": ["01001", "15001"]}))
    assert df["cp"].tolist() == [1001, 15001]


# =============================================================================
# _leer_texto
#   [T1] contiene byte nulo                  -> ErrorImportacion
#   [T2] UTF-8 válido                        -> texto
#   [T3] UTF-8 con BOM                       -> texto sin BOM
#   [T4] no es UTF-8                         -> se decodifica como cp1252
# =============================================================================

@pytest.mark.parametrize("contenido", [
    b"\x00", b"a,b\n1,\x002\n", b"a,b\n1,2\n\x00",
    "x,y\n1,2\n".encode("utf-16"),          # UTF-16 siempre lleva nulos
    b"PK\x03\x04\x00\x00",                   # cabecera ZIP (xlsx)
    b"SQLite format 3\x00",                  # cabecera SQLite
])
def test_T1_bytes_nulos(tmp_path, contenido):
    with pytest.raises(ErrorImportacion, match="dañado"):
        _leer_texto(escribir(tmp_path / "a.csv", contenido))


def test_T2_utf8(tmp_path):
    ruta = escribir(tmp_path / "a.csv", "señal,ü\n1,2\n")
    assert _leer_texto(ruta) == "señal,ü\n1,2\n"


def test_T3_utf8_con_bom(tmp_path):
    ruta = escribir(tmp_path / "a.csv", b"\xef\xbb\xbfa,b\n1,2\n")
    assert _leer_texto(ruta) == "a,b\n1,2\n"


def test_T4_cp1252(tmp_path):
    ruta = escribir(tmp_path / "a.csv", "Elviña,€\n".encode("cp1252"))
    assert _leer_texto(ruta) == "Elviña,€\n"


def test_T4_LIMITACION_bytes_indefinidos_se_sustituyen(tmp_path):
    """0x81 no existe en cp1252: se cambia por '�' sin avisar."""
    ruta = escribir(tmp_path / "a.csv", b"a\n\x81\n")
    assert _leer_texto(ruta) == "a\n�\n"


def test_T_archivo_vacio(tmp_path):
    assert _leer_texto(escribir(tmp_path / "a.csv", b"")) == ""


# =============================================================================
# _leer_csv
#   [L1] texto vacío o solo espacios         -> ErrorImportacion
#   [L2] el Sniffer detecta ','              -> decimal '.'
#   [L3] el Sniffer detecta ';'              -> decimal ','
#   [L4] el Sniffer detecta tabulador        -> decimal '.'
#   [L5] el Sniffer falla (csv.Error)        -> separador ',' por defecto
#   [L6] pandas lanza EmptyDataError         -> ErrorImportacion
#   [L7] pandas lanza ParserError            -> ErrorImportacion
# =============================================================================

@pytest.mark.parametrize("contenido", [
    "", " ", "\n\n\n", "\t \r\n", "\r", "\x0c", b"\xef\xbb\xbf",
])
def test_L1_sin_contenido(tmp_path, contenido):
    with pytest.raises(ErrorImportacion, match="no contiene datos"):
        _leer_csv(escribir(tmp_path / "a.csv", contenido))


@pytest.fixture
def espia_read_csv(monkeypatch):
    """Deja que pandas lea de verdad, pero apunta sep y decimal."""
    real = pd.read_csv
    llamadas = []

    def espia(*args, **kwargs):
        llamadas.append(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", espia)
    return llamadas


def test_L2_coma(tmp_path, espia_read_csv):
    df = _leer_csv(escribir(tmp_path / "a.csv", "a,b\n1.5,2\n3.5,4\n"))
    assert espia_read_csv[0]["sep"] == ","
    assert espia_read_csv[0]["decimal"] == "."
    assert df["a"].tolist() == [1.5, 3.5]


def test_L3_punto_y_coma(tmp_path, espia_read_csv):
    df = _leer_csv(escribir(tmp_path / "a.csv", "a;b\n1,5;2\n3,5;4\n"))
    assert espia_read_csv[0]["sep"] == ";"
    assert espia_read_csv[0]["decimal"] == ","
    assert df["a"].tolist() == [1.5, 3.5]


def test_L4_tabulador(tmp_path, espia_read_csv):
    df = _leer_csv(escribir(tmp_path / "a.csv", "a\tb\n1.5\t2\n3.5\t4\n"))
    assert espia_read_csv[0]["sep"] == "\t"
    assert espia_read_csv[0]["decimal"] == "."
    assert df["a"].tolist() == [1.5, 3.5]


def test_L5_sniffer_falla_natural(tmp_path, espia_read_csv):
    """Con una sola columna el Sniffer no encuentra separador."""
    df = _leer_csv(escribir(tmp_path / "a.csv", "precio\n10\n20\n"))
    assert espia_read_csv[0]["sep"] == ","
    assert df["precio"].tolist() == [10, 20]


def test_L5_sniffer_falla_forzado(tmp_path, monkeypatch, espia_read_csv):
    def falla(*args, **kwargs):
        raise csv.Error("forzado")

    monkeypatch.setattr(csv.Sniffer, "sniff", falla)
    _leer_csv(escribir(tmp_path / "a.csv", "a;b\n1;2\n"))
    assert espia_read_csv[0]["sep"] == ","


def test_L5_sniffer_solo_mira_los_primeros_5000(tmp_path, monkeypatch):
    muestras = []
    real = csv.Sniffer.sniff

    def espia(self, muestra, *args, **kwargs):
        muestras.append(muestra)
        return real(self, muestra, *args, **kwargs)

    monkeypatch.setattr(csv.Sniffer, "sniff", espia)
    filas = "".join(f"{i};{i}\n" for i in range(5000))
    df = _leer_csv(escribir(tmp_path / "a.csv", "a;b\n" + filas))
    assert len(muestras[0]) == 5000
    assert len(df) == 5000   # la muestra corta una línea y aun así funciona


def test_L6_empty_data_error_natural(tmp_path):
    """Dos BOM: utf-8-sig quita uno y strip() no quita el otro, pero pandas
    no ve nada que leer."""
    ruta = escribir(tmp_path / "a.csv", b"\xef\xbb\xbf\xef\xbb\xbf")
    with pytest.raises(ErrorImportacion, match="no contiene datos") as info:
        _leer_csv(ruta)
    assert isinstance(info.value.__cause__, pd.errors.EmptyDataError)


def test_L6_empty_data_error_forzado(tmp_path, monkeypatch):
    monkeypatch.setattr(pd, "read_csv",
                        Espia(lanzar=pd.errors.EmptyDataError("forzado")))
    with pytest.raises(ErrorImportacion, match="no contiene datos"):
        _leer_csv(escribir(tmp_path / "a.csv", "a,b\n1,2\n"))


@pytest.mark.parametrize("contenido", [
    "a,b\n1,2\n3,4,5\n",            # una fila con un campo de más
    'a,b\n"1,2\n3,4\n',             # comillas sin cerrar
])
def test_L7_parser_error(tmp_path, contenido):
    with pytest.raises(ErrorImportacion, match="dañado") as info:
        _leer_csv(escribir(tmp_path / "a.csv", contenido))
    assert isinstance(info.value.__cause__, pd.errors.ParserError)


@pytest.mark.parametrize("contenido", [
    "a;b\n1;2\n3;4;5;6\n",          # una fila con campos de más
    "a;b;c\n1;2;3\n4;5\n6;7;8\n",   # una fila con un campo de menos
])
def test_L5_sniffer_falla_con_punto_y_coma(tmp_path, contenido):
    try:
        df = _leer_csv(escribir(tmp_path / "a.csv", contenido))
    except ErrorImportacion:
        return                      # dar error también sería correcto
    assert ";" not in "".join(df.columns)


def test_L_texto_con_separador_del_otro_tipo(tmp_path):
    """Comas dentro del texto de un CSV con ';' y viceversa."""
    df = _leer_csv(escribir(tmp_path / "a.csv",
                            "nombre;precio\nGarcía, Ana;1,5\nLópez, Luis;2,5\n"))
    assert df.columns.tolist() == ["nombre", "precio"]
    assert df["precio"].tolist() == [1.5, 2.5]
    df = _leer_csv(escribir(tmp_path / "b.csv",
                            "texto,valor\nhola; adiós,1\nqué; tal,2\n"))
    assert df.columns.tolist() == ["texto", "valor"]


def test_L_campos_entre_comillas(tmp_path):
    df = _leer_csv(escribir(tmp_path / "a.csv",
                            'n,v\n"Pérez, J.",1\n"dice ""hola""",2\n'))
    assert df["n"].tolist() == ['Pérez, J.', 'dice "hola"']


@pytest.mark.parametrize("fin_de_linea", ["\n", "\r\n", "\r"])
def test_L_finales_de_linea(tmp_path, fin_de_linea):
    texto = fin_de_linea.join(["a,b", "1,2", "3,4"]) + fin_de_linea
    assert _leer_csv(escribir(tmp_path / "a.csv", texto)).shape == (2, 2)


def test_L_fila_con_un_campo_de_mas_no_desplaza_datos(tmp_path):
    ruta = escribir(tmp_path / "a.csv", "a,b\n1,2,3\n")
    try:
        df = _leer_csv(ruta)
    except ErrorImportacion:
        return
    assert df["a"].tolist() == [1]


def test_L_campo_de_mas_con_indice_desde_cero(tmp_path):
    """pandas 3 compacta el índice 0, 1... en un RangeIndex, así que no
    basta con mirar el tipo del índice para detectar el desplazamiento."""
    ruta = escribir(tmp_path / "a.csv", "id,v\n0,a,x\n1,b,y\n")
    with pytest.raises(ErrorImportacion, match="más campos"):
        _leer_csv(ruta)


def test_L_indice_implicito_con_csv_error(monkeypatch):
    """Si el módulo csv no puede leer las filas, se deja decidir a pandas."""
    def falla(*args, **kwargs):
        raise csv.Error("forzado")

    monkeypatch.setattr(csv, "reader", falla)
    assert importador._indice_implicito("a,b\n1,2,3\n", ",") is False


def test_L_separador_al_final_de_cada_linea(tmp_path):
    df = _leer_csv(escribir(tmp_path / "a.csv", "id,v\n0,a,\n1,b,\n"))
    assert df["id"].tolist() == [0, 1]
    assert df["v"].tolist() == ["a", "b"]


def test_L_una_columna_con_coma_decimal(tmp_path):
    ruta = escribir(tmp_path / "a.csv", "precio\n1,5\n2,5\n")
    try:
        df = importar_datos(ruta)
    except ErrorImportacion:
        return
    assert df["precio"].tolist() == [1.5, 2.5]


def test_L_filas_sin_valores(tmp_path):
    with pytest.raises(ErrorImportacion, match="no contiene datos"):
        importar_datos(escribir(tmp_path / "a.csv", "a,b\n,\n,\n"))


def test_L_sin_permiso_de_lectura(tmp_path, monkeypatch):
    ruta = escribir(tmp_path / "a.csv", "a,b\n1,2\n")

    def sin_permiso(self):
        raise PermissionError("Permiso denegado")

    monkeypatch.setattr(Path, "read_bytes", sin_permiso)
    with pytest.raises(ErrorImportacion):
        importar_datos(ruta)


# =============================================================================
# _leer_excel
#   [E1] lectura correcta
#   [E2] falta la librería (ImportError)     -> "Falta la librería"
#   [E3] cualquier otro error                -> "dañado"
# =============================================================================

def test_E1_xlsx(tmp_path, datos):
    ruta = tmp_path / "a.xlsx"
    datos.to_excel(ruta, index=False)
    pd.testing.assert_frame_equal(_leer_excel(ruta), datos)


def test_E1_solo_lee_la_primera_hoja(tmp_path):
    ruta = tmp_path / "a.xlsx"
    with pd.ExcelWriter(ruta) as escritor:
        pd.DataFrame({"h1": [1]}).to_excel(
            escritor, sheet_name="uno", index=False)
        pd.DataFrame({"h2": [2]}).to_excel(
            escritor, sheet_name="dos", index=False)
    assert _leer_excel(ruta).columns.tolist() == ["h1"]


def test_E1_LIMITACION_primera_hoja_vacia(tmp_path):
    """Si la primera hoja está vacía, se informa de que no hay datos aunque
    otras hojas sí los tengan."""
    ruta = tmp_path / "a.xlsx"
    with pd.ExcelWriter(ruta) as escritor:
        pd.DataFrame().to_excel(escritor, sheet_name="vacia", index=False)
        pd.DataFrame({"a": [1]}).to_excel(
            escritor, sheet_name="datos", index=False)
    with pytest.raises(ErrorImportacion, match="no contiene datos"):
        importar_datos(ruta)


def test_E2_falta_libreria(tmp_path, monkeypatch):
    monkeypatch.setattr(pd, "read_excel",
                        Espia(lanzar=ImportError("Missing optional xlrd")))
    with pytest.raises(ErrorImportacion, match="Falta la librería") as info:
        _leer_excel(escribir(tmp_path / "a.xls", b"x"))
    assert ".xls" in str(info.value)
    assert isinstance(info.value.__cause__, ImportError)


def test_E2_las_librerias_estan_instaladas():
    import openpyxl  # noqa: F401
    import xlrd      # noqa: F401


@pytest.mark.parametrize("nombre, contenido", [
    ("a.xlsx", "texto plano"),
    ("a.xls", "texto plano"),
    ("a.xlsx", b""),
    ("a.xlsx", b"PK\x03\x04" + b"\x00" * 50),     # ZIP truncado
    ("a.xls", b"\xd0\xcf\x11\xe0" + b"\x00" * 50),  # OLE truncado
    ("a.xlsx", b"SQLite format 3\x00" + b"\x00" * 84),
])
def test_E3_contenido_invalido(tmp_path, nombre, contenido):
    with pytest.raises(ErrorImportacion, match="dañado") as info:
        _leer_excel(escribir(tmp_path / nombre, contenido))
    assert info.value.__cause__ is not None


def test_E3_xlsx_truncado(tmp_path, datos):
    ruta = tmp_path / "a.xlsx"
    datos.to_excel(ruta, index=False)
    ruta.write_bytes(ruta.read_bytes()[:300])
    with pytest.raises(ErrorImportacion, match="dañado"):
        _leer_excel(ruta)


def test_E_LIMITACION_xlsx_renombrado_a_xls_se_acepta(tmp_path, datos):
    """pandas mira el contenido, no la extensión. Es razonable, pero el
    criterio dice 'el formato se determina por la extensión'."""
    ruta = tmp_path / "a.xls"
    datos.to_excel(tmp_path / "a.xlsx", index=False)
    (tmp_path / "a.xlsx").rename(ruta)
    assert len(_leer_excel(ruta)) == 3


def test_E_fechas_de_excel(tmp_path):
    ruta = tmp_path / "a.xlsx"
    pd.DataFrame({"fecha": pd.to_datetime(["2024-01-01"]),
                  "v": [1]}).to_excel(ruta, index=False)
    df = importar_datos(ruta)
    assert pd.api.types.is_datetime64_any_dtype(df["fecha"])


# =============================================================================
# _leer_sqlite
#   [S1] ninguna tabla                       -> ErrorImportacion
#   [S2] más de una tabla                    -> ErrorImportacion
#   [S3] una tabla                           -> sus datos
#   [S4] no es una base de datos             -> sqlite3.DatabaseError
#   [S5] la tabla no se puede leer           -> pd.errors.DatabaseError
#   [S6] la conexión se cierra en todos los caminos (finally)
# =============================================================================

@pytest.mark.parametrize("sentencias", [
    [],
    ["CREATE VIEW v AS SELECT 1 AS a"],          # solo una vista
    ["CREATE TABLE t(a)", "DROP TABLE t"],
])
def test_S1_sin_tablas(tmp_path, sentencias):
    ruta = crear_sqlite(tmp_path / "a.db", sentencias)
    with pytest.raises(ErrorImportacion, match="ninguna tabla"):
        _leer_sqlite(ruta)


def test_S1_archivo_de_cero_bytes(tmp_path):
    """SQLite considera un archivo vacío como una base de datos vacía."""
    with pytest.raises(ErrorImportacion, match="ninguna tabla"):
        _leer_sqlite(escribir(tmp_path / "a.db", b""))


@pytest.mark.parametrize("n", [2, 3, 10])
def test_S2_varias_tablas(tmp_path, n):
    ruta = crear_sqlite(tmp_path / "a.db",
                        [f"CREATE TABLE t{i}(a)" for i in range(n)])
    with pytest.raises(ErrorImportacion, match="más de una tabla"):
        _leer_sqlite(ruta)


def test_S2_LIMITACION_tabla_virtual_fts5(tmp_path):
    """Una tabla FTS5 crea tablas internas: cuenta como 'más de una'."""
    ruta = crear_sqlite(tmp_path / "a.db",
                        ["CREATE VIRTUAL TABLE t USING fts5(a)",
                         "INSERT INTO t VALUES ('x')"])
    with pytest.raises(ErrorImportacion, match="más de una tabla"):
        _leer_sqlite(ruta)


@pytest.mark.parametrize("nombre_sql", [
    "t", '"año fiscal"', '"mi""tabla"', '"select"', '"sqlite1datos"',
    '"sqliteVentas"', '"%_raro_%"', '"tabla; DROP TABLE x"',
])
def test_S3_nombres_de_tabla_raros(tmp_path, nombre_sql):
    ruta = crear_sqlite(tmp_path / "a.db", [
        f"CREATE TABLE {nombre_sql} (a INTEGER)",
        f"INSERT INTO {nombre_sql} VALUES (7)",
    ])
    assert _leer_sqlite(ruta)["a"].tolist() == [7]


def test_S3_ignora_tablas_internas_vistas_e_indices(tmp_path):
    ruta = crear_sqlite(tmp_path / "a.db", [
        # sqlite_sequence
        "CREATE TABLE t(id INTEGER PRIMARY KEY AUTOINCREMENT, a)",
        "INSERT INTO t(a) VALUES (1)",
        "CREATE INDEX i ON t(a)",
        "CREATE VIEW v AS SELECT * FROM t",
        "CREATE TRIGGER tr AFTER INSERT ON t BEGIN SELECT 1; END",
        "ANALYZE",                                                  # sqlite_stat1
    ])
    assert _leer_sqlite(ruta).columns.tolist() == ["id", "a"]


def test_S3_tipos_de_columna(tmp_path):
    ruta = crear_sqlite(tmp_path / "a.db", [
        "CREATE TABLE t(i INTEGER, r REAL, t TEXT, b BLOB, n)",
        "INSERT INTO t VALUES (1, 1.5, 'x', x'00ff', NULL)",
    ])
    fila = _leer_sqlite(ruta).iloc[0]
    assert fila["i"] == 1 and fila["r"] == 1.5 and fila["t"] == "x"
    assert fila["b"] == b"\x00\xff" and pd.isna(fila["n"])


def test_S3_numeros_guardados_como_texto(tmp_path):
    ruta = crear_sqlite(tmp_path / "a.db", [
        "CREATE TABLE t(a TEXT)", "INSERT INTO t VALUES ('1.5'), ('2')"])
    assert importar_datos(ruta)["a"].tolist() == [1.5, 2.0]


def test_S3_no_modifica_el_archivo(tmp_path):
    ruta = crear_sqlite(tmp_path / "a.db",
                        ["CREATE TABLE t(a)", "INSERT INTO t VALUES (1)"])
    antes = hashlib.sha256(ruta.read_bytes()).hexdigest()
    _leer_sqlite(ruta)
    assert hashlib.sha256(ruta.read_bytes()).hexdigest() == antes
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.db"]


@pytest.mark.parametrize("contenido", [
    "esto no es una base de datos" * 10,
    b"\xff" * 4096,
    b"SQLite format 3\x00" + b"\xff" * 84,    # cabecera buena, resto basura
    "a,b\n1,2\n",
])
def test_S4_no_es_base_de_datos(tmp_path, contenido):
    with pytest.raises(ErrorImportacion, match="dañado") as info:
        _leer_sqlite(escribir(tmp_path / "a.db", contenido))
    assert isinstance(info.value.__cause__, sqlite3.DatabaseError)


def test_S4_xlsx_renombrado_a_db(tmp_path, datos):
    ruta = tmp_path / "a.db"
    datos.to_excel(tmp_path / "a.xlsx", index=False)
    (tmp_path / "a.xlsx").rename(ruta)
    with pytest.raises(ErrorImportacion, match="dañado"):
        _leer_sqlite(ruta)


def test_S5_pagina_de_datos_corrupta(tmp_path):
    """La tabla aparece en sqlite_master (página 1) pero sus datos están en
    páginas dañadas: falla al hacer el SELECT, dentro de pandas."""
    ruta = crear_sqlite(tmp_path / "a.db", ["CREATE TABLE t(a TEXT)"] + [
        f"INSERT INTO t VALUES ('{'x' * 500}')" for _ in range(50)])
    contenido = bytearray(ruta.read_bytes())
    tam_pagina = int.from_bytes(contenido[16:18], "big")
    contenido[tam_pagina:2 * tam_pagina] = b"\x55" * tam_pagina
    ruta.write_bytes(bytes(contenido))
    with pytest.raises(ErrorImportacion, match="No se pudo leer") as info:
        _leer_sqlite(ruta)
    assert isinstance(info.value.__cause__, pd.errors.DatabaseError)


@pytest.mark.parametrize("caso", ["ok", "sin_tablas", "varias", "no_es_db",
                                  "falla_lectura"])
def test_S6_la_conexion_siempre_se_cierra(tmp_path, monkeypatch, caso):
    ruta = tmp_path / "a.db"
    if caso in ("ok", "falla_lectura"):
        crear_sqlite(ruta, ["CREATE TABLE t(a)", "INSERT INTO t VALUES (1)"])
    elif caso == "sin_tablas":
        crear_sqlite(ruta, [])
    elif caso == "varias":
        crear_sqlite(ruta, ["CREATE TABLE t1(a)", "CREATE TABLE t2(a)"])
    else:
        escribir(ruta, "basura" * 100)
    if caso == "falla_lectura":
        monkeypatch.setattr(pd, "read_sql_query",
                            Espia(lanzar=pd.errors.DatabaseError("forzado")))

    creadas = conexiones_de(monkeypatch)
    try:
        _leer_sqlite(ruta)
    except ErrorImportacion:
        pass
    assert len(creadas) == 1 and creadas[0].cerrada


def conexiones_de(monkeypatch):
    # Se instala aquí, después de crear los archivos de prueba, para que
    # crear_sqlite use el sqlite3.connect normal.
    creadas = []
    conectar_real = sqlite3.connect

    class ConexionEspia(sqlite3.Connection):
        cerrada = False

        def close(self):
            self.cerrada = True
            super().close()

    def conectar(*args, **kwargs):
        conexion = conectar_real(*args, factory=ConexionEspia, **kwargs)
        creadas.append(conexion)
        return conexion

    monkeypatch.setattr(sqlite3, "connect", conectar)
    return creadas


def test_S_error_propio_no_se_reetiqueta_como_danado(tmp_path):
    """El ErrorImportacion de 'ninguna tabla' se lanza dentro del try: no
    debe acabar convertido en 'dañado' por el except de fuera."""
    ruta = crear_sqlite(tmp_path / "a.db", [])
    with pytest.raises(ErrorImportacion) as info:
        _leer_sqlite(ruta)
    assert "dañado" not in str(info.value)
    assert info.value.__cause__ is None


# =============================================================================
# Contrato general del módulo
# =============================================================================

EXTENSIONES = [".csv", ".xlsx", ".xls", ".sqlite", ".db"]


def _basura(semilla, sin_nulos):
    aleatorio = random.Random(semilla)
    minimo = 1 if sin_nulos else 0
    longitud = aleatorio.choice([1, 2, 10, 100, 1000, 5000])
    return bytes(aleatorio.randint(minimo, 255) for _ in range(longitud))


@pytest.mark.parametrize("extension", EXTENSIONES)
@pytest.mark.parametrize("semilla", range(40))
def test_fuzz_solo_escapa_error_importacion(tmp_path, extension, semilla):
    """Contenido aleatorio: el resultado tiene que ser un DataFrame no vacío
    o un ErrorImportacion. Cualquier otra excepción es un fallo."""
    for sin_nulos in (False, True):
        ruta = escribir(tmp_path / f"f{int(sin_nulos)}{extension}",
                        _basura(semilla, sin_nulos))
        try:
            df = importar_datos(ruta)
        except ErrorImportacion:
            continue
        assert isinstance(df, pd.DataFrame) and not df.empty


@pytest.mark.parametrize("semilla", range(30))
def test_fuzz_csv_de_texto_aleatorio(tmp_path, semilla):
    """Texto hecho con los caracteres que más líos dan a un lector CSV."""
    aleatorio = random.Random(semilla)
    alfabeto = ',;\t"\'\n\r 0123456789.-eE ñáü€#\\'
    texto = "".join(aleatorio.choice(alfabeto) for _ in range(400))
    ruta = escribir(tmp_path / "a.csv", texto)
    try:
        df = importar_datos(ruta)
    except ErrorImportacion:
        return
    assert isinstance(df, pd.DataFrame) and not df.empty


def test_no_escribe_por_consola_ni_avisa(tmp_path, datos, capsys):
    rutas = []
    for extension in [".csv", ".xlsx", ".sqlite"]:
        ruta = tmp_path / f"a{extension}"
        if extension == ".csv":
            datos.to_csv(ruta, index=False)
        elif extension == ".xlsx":
            datos.to_excel(ruta, index=False)
        else:
            conexion = sqlite3.connect(ruta)
            datos.to_sql("t", conexion, index=False)
            conexion.close()
        rutas.append(ruta)
    rutas += [tmp_path / "no_existe.csv", escribir(tmp_path / "x.txt", "")]
    with warnings.catch_warnings():
        warnings.simplefilter("error")       # un aviso de pandas -> fallo
        for ruta in rutas:
            try:
                importar_datos(ruta)
            except ErrorImportacion:
                pass
    salida = capsys.readouterr()
    assert salida.out == "" and salida.err == ""


def test_solo_importa_librerias_permitidas():
    arbol = ast.parse(Path(importador.__file__).read_text(encoding="utf-8"))
    modulos = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos |= {a.name.split(".")[0] for a in nodo.names}
        elif isinstance(nodo, ast.ImportFrom):
            modulos.add(nodo.module.split(".")[0])
    assert modulos <= {"csv", "sqlite3", "io", "pathlib", "pandas"}


def test_no_hay_print_ni_input():
    arbol = ast.parse(Path(importador.__file__).read_text(encoding="utf-8"))
    llamadas = {n.func.id for n in ast.walk(arbol)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert not llamadas & {"print", "input", "breakpoint", "exit"}


def test_docstring_de_la_funcion_publica():
    doc = importar_datos.__doc__
    for seccion in ("Args", "Returns", "Raises"):
        assert seccion in doc


def test_los_errores_envueltos_conservan_la_causa(tmp_path):
    casos = [escribir(tmp_path / "a.xlsx", "x"),
             escribir(tmp_path / "a.db", "x" * 200),
             escribir(tmp_path / "a.csv", 'a,b\n"1\n2,3,4\n')]
    for ruta in casos:
        with pytest.raises(ErrorImportacion) as info:
            importar_datos(ruta)
        assert info.value.__cause__ is not None, ruta.name