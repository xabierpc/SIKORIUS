import csv
import sqlite3
from io import StringIO
from pathlib import Path

import pandas as pd


class ErrorImportacion(Exception):
    """Error producido al importar un archivo de datos"""


def importar_datos(ruta_archivo) -> pd.DataFrame:
    """Importa un CSV, Excel o SQLite y devuelve sus datos.

    El formato se determina a partir de la extensión del archivo. En SQLite
    la base de datos debe contener una única tabla que se detecta de forma
    automática. En CSV y Excel la primera fila se tomará como encabezado.
    Las columnas cuyos valores son todos numéricos se devuelven con tipo
    numérico.

    Args:
        ruta_archivo: Ruta del archivo que se importa (str o Path)

    Returns:
        DataFrame de pandas con los datos importados

    Raises:
        ErrorImportacion: Si el archivo no existe, la extensión no es
        correcta, el archivo está dañado o no corresponde a su extensión,
        no contiene datos o, en SQLite la base de datos no tiene tablas
        o tiene más de una.
    """

    ruta = Path(ruta_archivo)

    # Comprobar que el archivo existe
    if not ruta.is_file():
        raise ErrorImportacion(f"El archivo no existe: {ruta_archivo}")

    extension = ruta.suffix.lower()

    # Lectura del archivo
    if extension == ".csv":
        df = _leer_csv(ruta)
    elif extension in [".xlsx", ".xls"]:
        df = _leer_excel(ruta)
    elif extension in [".sqlite", ".db"]:
        df = _leer_sqlite(ruta)
    else:
        raise ErrorImportacion(f"Extensión no soportada '{extension}'")

    if df.empty:
        raise ErrorImportacion(f"El archivo no contiene datos: {ruta.name}")

    return _convertir_numericas(df)


def _convertir_numericas(df) -> pd.DataFrame:
    """Convierte a número las columnas de texto cuyos valores son números."""
    for columna in df.columns:
        if not pd.api.types.is_numeric_dtype(df[columna]):
            try:
                df[columna] = pd.to_numeric(df[columna])
            except (ValueError, TypeError):
                pass  # la columna tiene texto de verdad: se deja como está
    return df


def _leer_texto(ruta) -> str:
    """Lee el archivo como texto en UTF-8 o, si falla, en Windows-1252."""
    datos = ruta.read_bytes()
    if b"\x00" in datos:
        raise ErrorImportacion(
            f"El archivo está dañado o no es CSV válido: {ruta.name}")
    try:
        return datos.decode("utf-8-sig")
    except UnicodeDecodeError:
        return datos.decode("cp1252", errors="replace")


def _leer_csv(ruta) -> pd.DataFrame:
    texto = _leer_texto(ruta)
    if not texto.strip():
        raise ErrorImportacion(f"El archivo no contiene datos: {ruta.name}")

    # Detecta el separador (',' o ';'); con ';' el decimal suele ser ','
    try:
        separador = csv.Sniffer().sniff(
            texto[:5000], delimiters=",;\t").delimiter
    except csv.Error:
        separador = ","
    decimal = "," if separador == ";" else "."

    try:
        return pd.read_csv(StringIO(texto), sep=separador, decimal=decimal)
    except pd.errors.EmptyDataError as e:
        raise ErrorImportacion(
            f"El archivo no contiene datos: {ruta.name}") from e
    except pd.errors.ParserError as e:
        raise ErrorImportacion(
            f"El archivo está dañado o no es CSV válido: {ruta.name}") from e


def _leer_excel(ruta) -> pd.DataFrame:
    try:
        return pd.read_excel(ruta)
    except ImportError as e:
        # Falta una dependencia (xlrd u openpyxl): no es culpa del archivo
        raise ErrorImportacion(
            f"Falta la librería para leer archivos {ruta.suffix}: {e}") from e
    except Exception as e:
        raise ErrorImportacion(
            f"El archivo está dañado o no es un excel válido: {ruta.name}") from e


def _leer_sqlite(ruta) -> pd.DataFrame:
    try:
        conexion = sqlite3.connect(ruta)
        try:
            # '_' es comodín en LIKE: se escapa para excluir solo 'sqlite_...'
            tablas = conexion.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite\\_%' ESCAPE '\\'").fetchall()

            if len(tablas) == 0:
                raise ErrorImportacion(
                    f"La base de datos no contiene ninguna tabla: {ruta.name}")
            if len(tablas) > 1:
                raise ErrorImportacion(
                    f"La base de datos contiene más de una tabla: {ruta.name}")

            nombre = tablas[0][0].replace('"', '""')
            return pd.read_sql_query(f'SELECT * FROM "{nombre}"', conexion)
        finally:
            conexion.close()
    except sqlite3.DatabaseError as e:
        raise ErrorImportacion(
            f"El archivo está dañado o no es una base de datos válida: {ruta.name}") from e
    except pd.errors.DatabaseError as e:
        raise ErrorImportacion(
            f"No se pudo leer la tabla de la base de datos: {ruta.name}") from e