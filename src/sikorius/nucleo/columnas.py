"""Validación de la selección de columnas para la regresión lineal.

Comprueba que se hayan elegido columnas de entrada (features) y una de salida
(target), que existan en el dataset, que la salida no sea también entrada y
que todas sean numéricas.

Lógica independiente de la interfaz gráfica: la GUI solo recoge la selección
del usuario, llama a validar_seleccion y muestra el error si lo hay.
"""

import pandas as pd

from sikorius.nucleo.errores import ErrorSeleccion


def resolver_columnas(df, nombres):
    """Asocia nombres de columna en texto con las columnas reales del dataset.

    El selector de la GUI trabaja con los nombres como texto, pero las
    cabeceras del dataset pueden no serlo (p. ej. 2020 en un Excel). Para que
    pandas encuentre la columna hay que usar la cabecera real.

    Args:
        df: DataFrame con los datos cargados.
        nombres: Lista de nombres de columna en texto.

    Returns:
        Lista con las columnas reales, en el mismo orden que ``nombres``.

    Raises:
        ErrorSeleccion: Si algún nombre no es una columna del dataset.
    """
    reales = {}
    for columna in df.columns:
        reales[str(columna)] = columna

    resueltas = []
    inexistentes = []
    for nombre in nombres:
        if nombre in reales:
            resueltas.append(reales[nombre])
        else:
            inexistentes.append(nombre)

    if inexistentes:
        raise ErrorSeleccion(
            "Columnas que no existen en el dataset: " + ", ".join(inexistentes)
        )
    return resueltas


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
    columnas = resolver_columnas(df, nombres)

    if target in features:
        raise ErrorSeleccion(
            "La columna '"
            + target
            + "' no puede ser entrada y salida a la vez."
        )

    no_numericas = []
    for nombre, columna in zip(nombres, columnas, strict=True):
        if not pd.api.types.is_numeric_dtype(df[columna]):
            no_numericas.append(nombre)
    if no_numericas:
        raise ErrorSeleccion(
            "Estas columnas no son numéricas y no se pueden usar en una "
            "regresión lineal: " + ", ".join(no_numericas)
        )
