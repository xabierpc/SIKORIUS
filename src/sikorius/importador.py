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

    # La GUI puede pasar None si se cancela el diálogo de selección
    try:
        ruta = Path(ruta_archivo)
    except TypeError as e:
        raise ErrorImportacion(
            f"Ruta de archivo no válida: {ruta_archivo!r}") from e

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

    # Un archivo cuyas filas no tienen ningún valor (',,') tampoco tiene
    # datos, aunque el DataFrame no esté vacío
    if df.dropna(how="all").empty:
        raise ErrorImportacion(f"El archivo no contiene datos: {ruta.name}")

    return _convertir_numericas(df)


def _convertir_numericas(df) -> pd.DataFrame:
    """Convierte a número las columnas de texto cuyos valores son números."""
    for columna in df.columns:
        # Solo columnas de texto: pd.to_numeric también convertiría en
        # enteros las fechas y las duraciones
        if (pd.api.types.is_object_dtype(df[columna])
                or pd.api.types.is_string_dtype(df[columna])):
            try:
                df[columna] = pd.to_numeric(df[columna])
            except (ValueError, TypeError):
                pass  # la columna tiene texto de verdad: se deja como está
    return df


def _leer_texto(ruta) -> str:
    """Lee el archivo como texto en UTF-8 o, si falla, en Windows-1252."""
    try:
        datos = ruta.read_bytes()
    except OSError as e:
        # Sin permiso de lectura o bloqueado por otro programa
        raise ErrorImportacion(
            f"No se puede leer el archivo: {ruta.name}") from e
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
        df, campos_de_mas = _leer_tabla(texto, separador, decimal)
        if separador == "," and len(df.columns) == 1:
            encabezado = str(df.columns[0])
            if "\t" in encabezado:
                # El Sniffer falla si las filas tienen distinto número de
                # campos; el encabezado delata el separador real
                df, campos_de_mas = _leer_tabla(texto, "\t", ".")
            elif ";" in encabezado or campos_de_mas:
                # Lo mismo con ';', o un CSV de una columna guardado por
                # Excel en español, donde la coma de '1,5' es decimal
                df, campos_de_mas = _leer_tabla(texto, ";", ",")
    except pd.errors.EmptyDataError as e:
        raise ErrorImportacion(
            f"El archivo no contiene datos: {ruta.name}") from e
    except pd.errors.ParserError as e:
        raise ErrorImportacion(
            f"El archivo está dañado o no es CSV válido: {ruta.name}") from e

    if campos_de_mas:
        raise ErrorImportacion(
            f"Hay filas con más campos que el encabezado: {ruta.name}")
    return df


def _leer_tabla(texto, separador, decimal) -> tuple[pd.DataFrame, bool]:
    """Lee el CSV e indica si alguna fila tiene datos de más.

    Si la primera fila de datos tiene un campo más que el encabezado,
    pandas toma la primera columna como índice y desplaza los datos sin
    avisar; la última columna leída es entonces el campo de más. Si ese
    campo está vacío (separador al final de cada línea) no se pierde nada
    y se relee con index_col=False, que no desplaza los datos.
    """
    df = pd.read_csv(StringIO(texto), sep=separador, decimal=decimal)
    if not _indice_implicito(texto, separador):
        return df, False
    if df.iloc[:, -1].notna().any():
        return df, True
    df = pd.read_csv(StringIO(texto), sep=separador, decimal=decimal,
                     index_col=False)
    return df, False


def _indice_implicito(texto, separador) -> bool:
    """Indica si la primera fila de datos tiene un campo más que el
    encabezado, que es cuando pandas usa la primera columna como índice."""
    try:
        filas = csv.reader(StringIO(texto, newline=""), delimiter=separador)
        no_vacias = (fila for fila in filas if fila)
        encabezado = next(no_vacias, [])
        primera = next(no_vacias, [])
    except csv.Error:
        return False   # pandas decidirá si el archivo es válido
    return len(primera) == len(encabezado) + 1


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