"""Separación del dataset en conjunto de entrenamiento y de test.

Lógica independiente de la interfaz gráfica: la GUI solo lee los valores que
escribe el usuario, llama a estas funciones y muestra el resultado o el error.
"""

import math
from fractions import Fraction

import numpy as np

PORCENTAJE_TEST_DEFECTO = 20
SEMILLA_DEFECTO = 42
FILAS_MINIMAS = 5


class ErrorSeparacion(Exception):
    """Parámetros o dataset no válidos para separar en entrenamiento y test."""


def interpretar_porcentaje(valor):
    """Convierte el porcentaje de test escrito por el usuario en un número.

    Admite números y textos como "20", "12.5" o "12,5".

    Raises:
        ErrorSeparacion: Si no es un número entre 1 y 99 (ambos incluidos).
    """
    if isinstance(valor, bool):
        valor = None
    if isinstance(valor, str):
        valor = valor.strip().replace(",", ".")
    try:
        porcentaje = float(valor)
    except (TypeError, ValueError):
        raise ErrorSeparacion(
            "El porcentaje de test debe ser un número entre 1 y 99.") from None
    if math.isnan(porcentaje) or not 1 <= porcentaje <= 99:
        raise ErrorSeparacion(
            "El porcentaje de test debe ser un número entre 1 y 99.")
    return porcentaje


def interpretar_semilla(valor):
    """Convierte la semilla escrita por el usuario en un entero no negativo.

    Admite enteros y textos como "42". No admite decimales ("4.5").

    Raises:
        ErrorSeparacion: Si no es un número entero mayor o igual que 0.
    """
    mensaje = "La semilla debe ser un número entero (0 o mayor)."
    if isinstance(valor, bool):
        raise ErrorSeparacion(mensaje)
    if isinstance(valor, float):
        if not valor.is_integer():
            raise ErrorSeparacion(mensaje)
        valor = int(valor)
    if isinstance(valor, str):
        valor = valor.strip()
    try:
        semilla = int(valor)
    except (TypeError, ValueError):
        raise ErrorSeparacion(mensaje) from None
    if semilla < 0:
        raise ErrorSeparacion(mensaje)
    return semilla


def calcular_tamanos(num_filas, porcentaje_test):
    """Devuelve (filas_entrenamiento, filas_test) para un dataset y porcentaje.

    El número de filas de test se redondea hacia arriba, como hace
    'train_test_split' de scikit-learn: 20 % de 101 filas -> 21 de test.
    La cuenta se hace con fracciones exactas para que los errores de los
    decimales en coma flotante no sumen una fila de más (por ejemplo, 64.4 %
    de 250 filas son 161 de test exactas, no 162).

    Raises:
        ErrorSeparacion: Si hay menos de 5 filas o algún conjunto queda vacío.
    """
    if num_filas < FILAS_MINIMAS:
        raise ErrorSeparacion(
            "El dataset tiene " + str(num_filas) + " filas; se necesitan al menos "
            + str(FILAS_MINIMAS) + " para separarlo en entrenamiento y test.")
    porcentaje_exacto = Fraction(repr(float(porcentaje_test)))
    filas_test = math.ceil(num_filas * porcentaje_exacto / 100)
    filas_entrenamiento = num_filas - filas_test
    if filas_test == 0 or filas_entrenamiento == 0:
        if filas_test == 0:
            vacio = "test"
        else:
            vacio = "entrenamiento"
        raise ErrorSeparacion(
            "Con un " + _formatear(porcentaje_test) + " % de test y "
            + str(num_filas) + " filas, el conjunto de " + vacio
            + " quedaría vacío. Elige otro porcentaje.")
    return filas_entrenamiento, filas_test


def separar_datos(df, porcentaje_test=PORCENTAJE_TEST_DEFECTO, semilla=SEMILLA_DEFECTO):
    """Separa el dataset en entrenamiento y test de forma aleatoria y reproducible.

    Con el mismo dataset, el mismo porcentaje y la misma semilla devuelve
    siempre los mismos conjuntos. Las filas se reparten sin repetirse: cada
    fila del dataset está en uno solo de los dos conjuntos. Se conserva el
    índice original de cada fila para poder identificarla.

    Args:
        df: DataFrame con los datos cargados.
        porcentaje_test: Porcentaje de filas para test (número o texto, 1-99).
            El de entrenamiento es el complementario.
        semilla: Semilla del generador aleatorio (entero >= 0, o texto).

    Returns:
        Tupla (entrenamiento, test) con dos DataFrames nuevos.

    Raises:
        ErrorSeparacion: Si el porcentaje o la semilla no son válidos, el
            dataset tiene menos de 5 filas o algún conjunto quedaría vacío.
    """
    porcentaje = interpretar_porcentaje(porcentaje_test)
    semilla = interpretar_semilla(semilla)
    _, filas_test = calcular_tamanos(len(df), porcentaje)

    # Se barajan las posiciones (no el índice) por si el índice tiene repetidos
    orden = np.random.default_rng(semilla).permutation(len(df))
    test = df.iloc[np.sort(orden[:filas_test])].copy()
    entrenamiento = df.iloc[np.sort(orden[filas_test:])].copy()
    return entrenamiento, test


def _formatear(numero):
    """20.0 -> "20", 12.5 -> "12.5"."""
    if float(numero).is_integer():
        return str(int(numero))
    return str(numero)