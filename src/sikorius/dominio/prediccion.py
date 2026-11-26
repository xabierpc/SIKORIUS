"""Predicciones con un modelo de regresión lineal creado o cargado (#22).

No conoce la sesión ni la interfaz gráfica: recibe el modelo y los valores
que ha escrito el usuario, y devuelve el valor predicho. Funciona igual con
un modelo recién creado que con uno cargado de un archivo, porque los dos
son un ``ModeloLineal``.
"""

import math
import numbers

import pandas as pd

from sikorius.dominio.errores import ErrorPrediccion
from sikorius.dominio.modelo import DECIMALES_FORMULA


def interpretar_valores(features, valores):
    """Convierte en números los valores escritos para cada entrada.

    Admite números y textos como "3", "3.5" o "3,5". Se ignoran los
    espacios del principio y del final.

    Args:
        features: Nombres de las columnas de entrada del modelo.
        valores: Diccionario ``{columna: valor}``. Las claves que no son
            columnas de entrada se ignoran.

    Returns:
        Diccionario ``{columna: float}`` con una entrada por columna, en el
        orden de ``features``.

    Raises:
        ErrorPrediccion: Si falta algún valor (no está, es None o es un
            texto vacío) o alguno no es un número finito. El mensaje dice
            qué columnas fallan.
    """
    if valores is None:
        valores = {}
    faltan = []
    no_validos = []
    numeros = {}
    for columna in features:
        valor = valores.get(columna)
        if isinstance(valor, str):
            valor = valor.strip()
        if valor is None or valor == "":
            faltan.append(str(columna))
            continue
        numero = _a_numero(valor)
        if numero is None:
            no_validos.append(str(columna))
        else:
            numeros[columna] = numero

    if faltan:
        raise ErrorPrediccion("Falta el valor de: " + ", ".join(faltan) + ".")
    if no_validos:
        raise ErrorPrediccion(
            "El valor de " + ", ".join(no_validos) + " no es un número válido."
        )
    return numeros


def predecir(modelo, valores):
    """Calcula la salida que predice el modelo para unos valores de entrada.

    Args:
        modelo: ModeloLineal creado en la aplicación o cargado de un
            archivo.
        valores: Diccionario ``{columna: valor}`` con un valor por cada
            columna de entrada del modelo, como número o como texto
            ("3.5" o "3,5").

    Returns:
        El valor predicho, como float, sin redondear.

    Raises:
        ErrorPrediccion: Si no hay modelo, falta algún valor o alguno no
            es un número.
    """
    if modelo is None:
        raise ErrorPrediccion(
            "Crea o carga primero un modelo para hacer predicciones."
        )
    numeros = interpretar_valores(modelo.features, valores)
    # Se usa el mismo cálculo que en las métricas y el gráfico
    fila = pd.DataFrame([numeros], columns=list(modelo.features))
    return float(modelo.predecir(fila)[0])


def texto_prediccion(modelo, valor, decimales=DECIMALES_FORMULA):
    """Escribe el resultado como ``<salida> = <valor_predicho>``.

    El valor se redondea con los mismos decimales que la fórmula del
    modelo, por ejemplo "precio = 1520.3750".

    Args:
        modelo: ModeloLineal con el que se hizo la predicción.
        valor: Valor predicho que devuelve ``predecir``.
        decimales: Decimales con los que se muestra el valor.

    Returns:
        El texto del resultado.
    """
    redondeado = round(float(valor), decimales)
    if redondeado == 0:
        redondeado = 0.0  # Evita que se muestre "-0.0000"
    return f"{modelo.target} = {redondeado:.{decimales}f}"


def _a_numero(valor):
    """Valor como float finito, o None si no es un número válido."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, str):
        valor = valor.replace(",", ".")
    elif not isinstance(valor, numbers.Real):
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numero):
        return None
    return numero
