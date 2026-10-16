import pandas as pd
import sqlite3
from pathlib import Path

class ErrorImportacion(Exception):
    """Error producido al importar un archivo de datos"""

def importar_datos(ruta_archivo) -> pd.DataFrame:
    """Importa un CSV, Excel o SQLite y devuelve sus datos.

    El formato se determina a partir de la extensión del archivo. En SQLite
    la base de datos debe contener una única tabla que se detecta de forma
    automática. En CSV y Excel la primera fila se tomará como encabezado.

    Args:
        ruta_archivo: Ruta del archivo que se importa
    
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
        raise ErrorImportacion("El archivo no contiene datos")

    return df


def _leer_csv(ruta) -> pd.DataFrame:
    try:
        return pd.read_csv(ruta)
    except pd.errors.EmptyDataError as e:
        raise ErrorImportacion("El archivo no contiene datos") from e
    except (pd.errors.ParserError, UnicodeDecodeError) as e:
        raise ErrorImportacion("El archivo está dañado o no es CSV válido") from e


def _leer_excel(ruta) -> pd.DataFrame:
    try:
        return pd.read_excel(ruta)
    except Exception as e:
        raise ErrorImportacion("El archivo está dañado o no es un excel válido") from e

def _leer_sqlite(ruta) -> pd.DataFrame:
    try:
        conexion=sqlite3.connect(ruta)
        try:
            tablas = conexion.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()

            if len(tablas) == 0:
                raise ErrorImportacion("La base de datos no contiene ninguna tabla")
            if len(tablas) > 1:
                raise ErrorImportacion("La base de datos contiene más de una tabla")

            nombre = tablas[0][0].replace('"', '""')
            return pd.read_sql_query(f'SELECT * FROM "{nombre}"', conexion)
        finally:
            conexion.close()
    except sqlite3.DatabaseError as e:
        raise ErrorImportacion("El archivo está dañado o no es una base de datos válida") from e
    except pd.errors.DatabaseError as e:
        raise ErrorImportacion("No se pudo leer la tabla de la base de datos") from e