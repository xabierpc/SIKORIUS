"""Crea los archivos de prueba de la sección 2.2 del plan (F-1 a F-14).

Son los mismos archivos que el plan explica cómo crear a mano. Aquí se
crean con código para que todas las ejecuciones partan exactamente de los
mismos datos. Se guardan en ``data/pruebas/``, que no se sube al
repositorio.
"""

import os
import shutil
import sqlite3
from pathlib import Path

CARPETA_ESPECIAL = "carpeta ñandú á"
CARPETA_SOLO_LECTURA = "solo_lectura"

ARCHIVOS_TEXTO = {
    "vacio.csv": "",
    "solo_cabecera.csv": "a,b\n",
    "falso.xlsx": "esto no es un excel\n",
    "falso.db": "esto no es una base de datos\n",
    "notas.txt": "hola\n",
    "cuatro_filas.csv": "x,y\n1,2\n2,4\n3,6\n4,8\n",
    "cinco_filas.csv": "x,y\n1,2\n2,4\n3,6\n4,8\n5,10\n",
    "lineal.csv": (
        "x1,x2,y\n"
        "1,0,7\n"
        "2,1,6\n"
        "3,0,11\n"
        "4,2,7\n"
        "5,1,12\n"
        "6,3,8\n"
        "7,0,19\n"
        "8,2,15\n"
        "9,1,20\n"
        "10,4,13\n"
        "11,2,21\n"
        "12,3,20\n"
    ),
    "nulos_total.csv": "x,y\n,1\n,2\n,3\n,4\n,5\n,6\n,7\n,8\n,9\n,10\n",
    "modelo_roto.json": "{ esto no es json\n",
    "modelo_incompleto.json": '{"descripcion": "falta todo lo demás"}\n',
}

# Archivos que crean los propios casos (modelos guardados): se borran al
# preparar los datos para que cada ejecución empiece igual
GENERADOS = (
    "modelo_lineal.json",
    "sin_descripcion.json",
    "reintento.json",
    "flujo_completo.json",
    "prohibido.json",
)


def preparar(carpeta_data, dataset_csv=None):
    """Crea (o vuelve a crear) todos los archivos de prueba.

    Args:
        carpeta_data: Carpeta ``data/`` del proyecto.
        dataset_csv: Ruta del dataset de ejemplo en CSV (D-1). Si existe,
            se copia dentro de la carpeta con caracteres especiales (F-11).

    Returns:
        La carpeta ``data/pruebas/``.
    """
    carpeta = Path(carpeta_data) / "pruebas"
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, contenido in ARCHIVOS_TEXTO.items():
        (carpeta / nombre).write_text(contenido, encoding="utf-8")

    _crear_sqlite(carpeta / "dos_tablas.db", dos_tablas=True)
    _crear_sqlite(carpeta / "sin_tablas.db", dos_tablas=False)

    for nombre in GENERADOS:
        ruta = carpeta / nombre
        if ruta.exists():
            ruta.unlink()

    especial = carpeta / CARPETA_ESPECIAL
    if especial.exists():
        shutil.rmtree(especial)
    especial.mkdir()
    if dataset_csv is not None and Path(dataset_csv).is_file():
        shutil.copy(dataset_csv, especial / Path(dataset_csv).name)

    solo_lectura = carpeta / CARPETA_SOLO_LECTURA
    if solo_lectura.exists():
        os.chmod(solo_lectura, 0o755)
        shutil.rmtree(solo_lectura)
    solo_lectura.mkdir()
    # Sin permiso de escritura (CP-64). En Windows no tiene efecto.
    os.chmod(solo_lectura, 0o555)
    return carpeta


def _crear_sqlite(ruta, dos_tablas):
    if ruta.exists():
        ruta.unlink()
    conexion = sqlite3.connect(ruta)
    try:
        if dos_tablas:
            conexion.execute("create table a (x real)")
            conexion.execute("create table b (y real)")
            conexion.execute("insert into a values (1)")
            conexion.execute("insert into b values (2)")
        else:
            conexion.execute("create table t (x real)")
            conexion.execute("drop table t")
        conexion.commit()
    finally:
        conexion.close()
