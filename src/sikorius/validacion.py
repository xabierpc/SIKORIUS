import pandas as pd


class ErrorSeleccion(Exception):
    """Selección de columnas no válida para un modelo de regresión lineal."""


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

    # El selector trabaja con nombres en texto: se asocian a las columnas reales
    reales = {str(c): c for c in df.columns}

    inexistentes = [c for c in list(features) + [target] if c not in reales]
    if inexistentes:
        raise ErrorSeleccion("Columnas que no existen en el dataset: " + ", ".join(inexistentes))

    if target in features:
        raise ErrorSeleccion("La columna '" + target + "' no puede ser entrada y salida a la vez.")

    no_numericas = [
        c for c in list(features) + [target]
        if not pd.api.types.is_numeric_dtype(df[reales[c]])
    ]
    if no_numericas:
        raise ErrorSeleccion(
            "Estas columnas no son numéricas y no se pueden usar en una regresión lineal: "
            + ", ".join(no_numericas)
        )