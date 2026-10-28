"""
Elimina las filas con valores inexistentes o los rellena (media, mediana o
valor constante) en los conjuntos de entrenamiento y test, y guarda el
resultado en el estado de la aplicación. También detecta los valores
inexistentes de las columnas seleccionadas.

Toda la lógica es independiente de la interfaz gráfica.
"""

import math

import numpy as np
import pandas as pd
 
ELIMINAR = "eliminar"
MEDIA = "media"
MEDIANA = "mediana"
CONSTANTE = "constante"
ESTRATEGIAS = (ELIMINAR, MEDIA, MEDIANA, CONSTANTE)
 
 
class ErrorPreprocesado(Exception):
    """Error producido al aplicar el preprocesado."""
 
 
class ColumnasNoEncontradasError(ValueError):
    """Se lanza cuando alguna columna seleccionada no existe en el DataFrame."""


def _comprobar_columnas(df, columnas):
    faltan = [c for c in columnas if c not in df.columns]
    if faltan:
        raise ColumnasNoEncontradasError(
            "Columnas no encontradas: " + ", ".join(map(str, faltan)))


def normalizar_espacios_vacios(df: pd.DataFrame, columnas: list) -> pd.DataFrame:
    """Convierte en NaN las celdas vacías o con solo espacios.

    Args:
        df: DataFrame a revisar (no se modifica).
        columnas: Lista de nombres de columnas.

    Returns:
        Copia del DataFrame con esas celdas como NaN.

    Raises:
        ColumnasNoEncontradasError: Si alguna columna no existe.
    """
    _comprobar_columnas(df, columnas)
    copia = df.copy()
    for columna in columnas:
        for indice in copia.index:
            valor = copia.at[indice, columna]
            if isinstance(valor, str) and valor.strip() == "":
                copia.at[indice, columna] = np.nan
    return copia


def detectar_nulos(df: pd.DataFrame, columnas: list) -> dict:
    """Cuenta los valores inexistentes (NaN o celdas vacías) de cada columna.

    Args:
        df: DataFrame a revisar.
        columnas: Lista de nombres de columnas.

    Returns:
        Diccionario {columna: número de valores inexistentes}.

    Raises:
        ColumnasNoEncontradasError: Si alguna columna no existe.
    """
    _comprobar_columnas(df, columnas)
    num_nulos = {}
    for i in columnas:
        contador = 0
        for j in df[i]:
            if (isinstance(j, str) and j.strip() == "") or pd.isna(j):
                contador += 1
        num_nulos[i] = contador
    return num_nulos


def quedan_nulos(df, columnas):
    """Indica si queda algún valor inexistente en las columnas indicadas.

    Args:
        df: DataFrame a revisar.
        columnas: Lista de nombres de columnas.

    Returns:
        True si hay al menos un valor inexistente, False en caso contrario.
    """
    return any(n > 0 for n in detectar_nulos(df, list(columnas)).values())


def detectar_nulos_conjuntos(train, test, columnas):
    """Detecta los valores inexistentes de train y test por separado.

    Args:
        train: DataFrame de entrenamiento.
        test: DataFrame de test.
        columnas: Columnas seleccionadas (entrada y salida).

    Returns:
        Diccionario {"train": {columna: n}, "test": {columna: n}}.
    """
    columnas = list(columnas)
    return {
        "train": detectar_nulos(train, columnas),
        "test": detectar_nulos(test, columnas),
    }


def hay_nulos(deteccion):
    """Indica si la detección encontró algún valor inexistente.

    Args:
        deteccion: Diccionario devuelto por ``detectar_nulos_conjuntos``.

    Returns:
        True si hay al menos un valor inexistente en train o en test.
    """
    return any(n > 0 for conjunto in deteccion.values() for n in conjunto.values())


def detectar_en_estado(estado):
    """Detecta los valores inexistentes de los conjuntos guardados en el estado.

    Si ya se aplicó un preprocesado, revisa los conjuntos preprocesados.

    Args:
        estado: Estado de la aplicación.

    Returns:
        El diccionario de ``detectar_nulos_conjuntos``, o None si aún no hay
        selección de columnas o separación en entrenamiento y test.
    """
    if not estado.hay_seleccion() or not estado.hay_separacion():
        return None
    if estado.preprocesado is not None:
        train = estado.preprocesado["entrenamiento"]
        test = estado.preprocesado["test"]
    else:
        train, test = estado.entrenamiento, estado.test
    return detectar_nulos_conjuntos(train, test, columnas_seleccionadas(estado))


def interpretar_constante(valor):
    """Convierte el valor constante escrito por el usuario en un número.

    Admite números y textos como "3", "2.5" o "2,5".

    Raises:
        ErrorPreprocesado: Si no es un número válido.
    """
    mensaje = "El valor constante debe ser un número."
    if valor is None or isinstance(valor, bool):
        raise ErrorPreprocesado(mensaje)
    if isinstance(valor, str):
        valor = valor.strip().replace(",", ".")
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorPreprocesado(mensaje) from None
    if math.isnan(numero) or math.isinf(numero):
        raise ErrorPreprocesado(mensaje)
    return numero


def columnas_seleccionadas(estado):
    """Devuelve las columnas de entrada seguidas de la de salida.
 
    Args:
        estado: Estado de la aplicación, con la selección ya confirmada.
 
    Returns:
        Lista con las features y, al final, el target.
    """
    seleccion = estado.seleccion
    return list(seleccion["features"]) + [seleccion["target"]]
 
 
def _resumen(filas_eliminadas, valores_rellenados):
    return {
        "filas_eliminadas": filas_eliminadas,
        "valores_rellenados": valores_rellenados,
    }
 
 
def aplicar_preprocesado(train, test, columnas, estrategia, constante=None):
    """Trata los valores inexistentes de los conjuntos de train y test.
 
    Args:
        train: DataFrame de entrenamiento.
        test: DataFrame de test.
        columnas: Columnas seleccionadas (entrada y salida).
        estrategia: "eliminar", "media", "mediana" o "constante".
        constante: Número con el que rellenar (solo para "constante").
 
    Returns:
        Tupla (train_proc, test_proc, resumen). El resumen es un diccionario
        {"train": {...}, "test": {...}} con "filas_eliminadas" y
        "valores_rellenados" de cada conjunto.
 
    Raises:
        ErrorPreprocesado: Si la estrategia no es válida o, con
            "constante", el valor no es numérico.
    """
    columnas = list(columnas)
    if estrategia not in ESTRATEGIAS:
        raise ErrorPreprocesado(f"Estrategia no válida: {estrategia}")
 
    # Las celdas vacías pasan a NaN para tratarlas igual que el resto
    train = normalizar_espacios_vacios(train, columnas)
    test = normalizar_espacios_vacios(test, columnas)
    train_proc = train.copy()
    test_proc = test.copy()
 
    if estrategia == ELIMINAR:
        train_proc = train_proc.dropna(subset=columnas)
        test_proc = test_proc.dropna(subset=columnas)
        resumen = {
            "train": _resumen(len(train) - len(train_proc), 0),
            "test": _resumen(len(test) - len(test_proc), 0),
        }
        return train_proc, test_proc, resumen
 
    if estrategia == CONSTANTE:
        constante = interpretar_constante(constante)
        valores = {c: constante for c in columnas}
    elif estrategia == MEDIA:
        valores = train[columnas].mean().to_dict()
    else:
        valores = train[columnas].median().to_dict()
 
    train_proc = train_proc.fillna(valores)
    test_proc = test_proc.fillna(valores)
    resumen = {
        "train": _resumen(0, _nulos(train, columnas)
                          - _nulos(train_proc, columnas)),
        "test": _resumen(0, _nulos(test, columnas)
                         - _nulos(test_proc, columnas)),
    }
    return train_proc, test_proc, resumen
 
 
def _nulos(df, columnas):
    """Número total de valores inexistentes en las columnas indicadas."""
    return sum(detectar_nulos(df, columnas).values())
 
 
def aplicar_al_estado(estado, estrategia, constante=None):
    """Preprocesa los conjuntos guardados en el estado y guarda el resultado.
 
    Args:
        estado: Estado de la aplicación.
        estrategia: "eliminar", "media", "mediana" o "constante".
        constante: Número con el que rellenar (solo para "constante").
 
    Returns:
        El resumen del preprocesado (ver ``aplicar_preprocesado``).
 
    Raises:
        ErrorPreprocesado: Si no hay selección confirmada ni separación en
            entrenamiento y test, o si la estrategia no es válida. En ese
            caso el estado no se modifica.
    """
    if not estado.hay_seleccion():
        raise ErrorPreprocesado("Confirma primero la selección de columnas.")
    if not estado.hay_separacion():
        raise ErrorPreprocesado("Separa primero en entrenamiento y test.")
    entrenamiento, test, resumen = aplicar_preprocesado(
        estado.entrenamiento,
        estado.test,
        columnas_seleccionadas(estado),
        estrategia,
        constante,
    )
    estado.preprocesado = {
        "entrenamiento": entrenamiento,
        "test": test,
        "estrategia": estrategia,
        "resumen": resumen,
    }
    return resumen
 
 
def modelo_disponible(estado):
    """Indica si se puede crear el modelo con los datos del estado.

    Args:
        estado: Estado de la aplicación.
 
    Returns:
        True si se puede crear el modelo, False en caso contrario.
    """
    if not estado.hay_seleccion() or not estado.hay_separacion():
        return False
    columnas = columnas_seleccionadas(estado)
    if estado.preprocesado is not None:
        entrenamiento = estado.preprocesado["entrenamiento"]
        test = estado.preprocesado["test"]
    else:
        entrenamiento, test = estado.entrenamiento, estado.test
    return not (
        quedan_nulos(entrenamiento, columnas) or quedan_nulos(test, columnas)
    )
 
 
def texto_resumen(resumen):
    """Redacta el mensaje de éxito a partir del resumen del preprocesado.
 
    Args:
        resumen: Diccionario devuelto por ``aplicar_preprocesado``.
 
    Returns:
        Texto con filas eliminadas y valores rellenados de cada conjunto.
    """
    partes = []
    for clave, nombre in (("train", "Entrenamiento"), ("test", "Test")):
        datos = resumen[clave]
        partes.append(
            f"{nombre}: {datos['filas_eliminadas']} filas eliminadas, "
            f"{datos['valores_rellenados']} valores rellenados"
        )
    return "Preprocesado aplicado. " + " | ".join(partes) + "."