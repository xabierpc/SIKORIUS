"""Validación de las columnas de entrada y salida del modelo.

Los selectores de la interfaz trabajan con los nombres de las columnas en
texto; aquí se traducen a las columnas reales del DataFrame, que pueden no
ser texto (por ejemplo, 2020 en la cabecera de un Excel).
"""

import pandas as pd

from sikorius.nucleo.errores import ErrorSeleccion


def resolver_columnas(df, nombres):
    """Traduce los nombres en texto del selector a las columnas reales.

    Un nombre que no corresponde a ninguna columna se devuelve tal cual.
    """
    reales = {}
    for columna in df.columns:
        reales[str(columna)] = columna
    resultado = []
    for nombre in nombres:
        resultado.append(reales.get(nombre, nombre))
    return resultado


def validar_seleccion(df, features, target):
    """Valida la selección de columnas de entrada (features) y salida (target).

    Args:
        df: DataFrame con los datos cargados.
        features: Lista de nombres de las columnas de entrada.
        target: Nombre de la columna de salida (o None si no hay).

    Raises:
        ErrorSeleccion: Si falta alguna selección, alguna columna no existe,
            el target también es feature, o alguna columna no es numérica.
    """
    faltan = []
    if not features:
        faltan.append("al menos una columna de entrada (features)")
    if target is None or target == "":
        faltan.append("la columna de salida (target)")
    if faltan:
        raise ErrorSeleccion("Falta seleccionar " + " y ".join(faltan) + ".")

    nombres = list(features) + [target]
    reales = resolver_columnas(df, nombres)

    inexistentes = []
    for nombre, real in zip(nombres, reales, strict=True):
        if real not in df.columns:
            inexistentes.append(nombre)
    if inexistentes:
        raise ErrorSeleccion(
            "Columnas que no existen en el dataset: "
            + ", ".join(inexistentes)
            + "."
        )

    if target in features:
        raise ErrorSeleccion(
            "La columna '"
            + target
            + "' no puede ser entrada y salida a la vez."
        )

    no_numericas = []
    for nombre, real in zip(nombres, reales, strict=True):
        if not pd.api.types.is_numeric_dtype(df[real]):
            no_numericas.append(nombre)
    if no_numericas:
        raise ErrorSeleccion(
            "Estas columnas no son numéricas y no se pueden usar en una "
            "regresión lineal: " + ", ".join(no_numericas)
        )
