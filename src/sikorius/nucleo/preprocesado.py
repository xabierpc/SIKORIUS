"""Tratamiento de los valores inexistentes antes de crear el modelo.

Detecta los valores inexistentes (NaN, None o texto vacío) de las columnas
seleccionadas y elimina esas filas o las rellena con la media, la mediana o
un valor constante, en los conjuntos de entrenamiento y test.

Todas las funciones reciben DataFrames y devuelven resultados nuevos: no
conocen la sesión ni la interfaz gráfica.
"""

import math

import pandas as pd

from sikorius.nucleo.errores import (
    AvisoPreprocesado,
    ColumnasNoEncontradasError,
    ErrorPreprocesado,
)

ELIMINAR = "eliminar"
MEDIA = "media"
MEDIANA = "mediana"
CONSTANTE = "constante"
ESTRATEGIAS = (ELIMINAR, MEDIA, MEDIANA, CONSTANTE)


def _comprobar_columnas(df, columnas):
    faltan = [c for c in columnas if c not in df.columns]
    if faltan:
        raise ColumnasNoEncontradasError(
            "Columnas no encontradas: " + ", ".join(map(str, faltan))
        )


def _celdas_vacias(serie):
    """True en las celdas de texto vacías o con solo espacios."""
    vacias = serie.map(
        lambda valor: isinstance(valor, str) and valor.strip() == ""
    )
    return vacias.astype(bool)


def _mascara_nulos(serie):
    """True en las celdas sin valor: NaN, None o texto vacío."""
    return serie.isna() | _celdas_vacias(serie)


def normalizar_espacios_vacios(
    df: pd.DataFrame, columnas: list
) -> pd.DataFrame:
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
        copia[columna] = copia[columna].mask(_celdas_vacias(copia[columna]))
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
    for columna in columnas:
        num_nulos[columna] = int(_mascara_nulos(df[columna]).sum())
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
    return any(
        n > 0 for conjunto in deteccion.values() for n in conjunto.values()
    )


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
        ErrorPreprocesado: Si la estrategia no es válida, con "constante"
            el valor no es numérico, o con "media"/"mediana" alguna columna
            no tiene ningún valor en entrenamiento con el que calcularla.
        AvisoPreprocesado: Si eliminar las filas dejaría vacío el conjunto
            de entrenamiento o el de test.
    """
    columnas = list(columnas)
    if estrategia not in ESTRATEGIAS:
        raise ErrorPreprocesado("Estrategia no válida: " + str(estrategia))

    # Las celdas vacías pasan a NaN para tratarlas igual que el resto
    train = normalizar_espacios_vacios(train, columnas)
    test = normalizar_espacios_vacios(test, columnas)
    train_proc = train.copy()
    test_proc = test.copy()

    if estrategia == ELIMINAR:
        train_proc = train_proc.dropna(subset=columnas)
        test_proc = test_proc.dropna(subset=columnas)
        _comprobar_no_vacios(train_proc, test_proc)
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

    if estrategia in (MEDIA, MEDIANA):
        _comprobar_valores_relleno(valores, estrategia)

    train_proc = train_proc.fillna(valores)
    test_proc = test_proc.fillna(valores)
    resumen = {
        "train": _resumen(
            0, _nulos(train, columnas) - _nulos(train_proc, columnas)
        ),
        "test": _resumen(
            0, _nulos(test, columnas) - _nulos(test_proc, columnas)
        ),
    }
    return train_proc, test_proc, resumen


def _comprobar_no_vacios(train_proc, test_proc):
    """Lanza un aviso si eliminar filas deja vacío algún conjunto."""
    vacios = []
    if len(train_proc) == 0:
        vacios.append("entrenamiento")
    if len(test_proc) == 0:
        vacios.append("test")
    if vacios:
        raise AvisoPreprocesado(
            "Eliminar las filas con valores inexistentes dejaría vacío el "
            "conjunto de " + " y el de ".join(vacios) + ". No se ha aplicado "
            "el cambio: elige otra estrategia."
        )


def _comprobar_valores_relleno(valores, estrategia):
    """Lanza un error si la media/mediana de alguna columna es NaN.

    Pasa cuando la columna no tiene ningún valor en entrenamiento: rellenar
    con NaN no haría nada y quedarían valores inexistentes.
    """
    sin_valor = [str(c) for c, v in valores.items() if pd.isna(v)]
    if sin_valor:
        raise ErrorPreprocesado(
            "No se puede calcular la "
            + estrategia
            + " de "
            + ", ".join(sin_valor)
            + " porque no tiene ningún valor en el "
            "conjunto de entrenamiento. Elige otra estrategia."
        )


def _nulos(df, columnas):
    """Número total de valores inexistentes en las columnas indicadas."""
    return sum(detectar_nulos(df, columnas).values())
