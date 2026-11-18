"""Cambios que el asistente puede proponer sobre el dataset.

El asistente (una LLM) nunca toca los datos ni escribe código: solo elige
operaciones de este catálogo cerrado y sus parámetros. Aquí se comprueba
que tienen sentido y se aplican con pandas.

Todas las funciones reciben DataFrames y devuelven resultados nuevos: no
conocen la sesión, la interfaz gráfica ni la LLM.
"""

import math
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict

from sikorius.dominio.errores import ErrorTransformacion
from sikorius.dominio.texto import formatear_numero

ELIMINAR_COLUMNA = "eliminar_columna"
RENOMBRAR_COLUMNA = "renombrar_columna"
ELIMINAR_NULOS = "eliminar_filas_con_nulos"
FILTRAR = "filtrar_filas"
ELIMINAR_DUPLICADOS = "eliminar_duplicados"
QUITAR_ATIPICOS = "quitar_atipicos"
CONVERTIR_A_NUMERO = "convertir_a_numero"

TIPOS = (
    ELIMINAR_COLUMNA,
    RENOMBRAR_COLUMNA,
    ELIMINAR_NULOS,
    FILTRAR,
    ELIMINAR_DUPLICADOS,
    QUITAR_ATIPICOS,
    CONVERTIR_A_NUMERO,
)

OPERADORES = ("<", "<=", ">", ">=", "==", "!=")

# Factor del rango intercuartílico para considerar atípico un valor
FACTOR_IQR = 1.5


class Operacion(BaseModel):
    """Un cambio sobre el dataset, tal como lo pide la LLM.

    Todos los campos son obligatorios (los que no se usan van a None) para
    que el esquema sirva en el modo estricto de la salida estructurada.

    Attributes:
        tipo: Qué operación es (ver ``TIPOS``).
        columna: Columna a la que afecta, o None si afecta a todas
            (eliminar duplicados o filas con algún nulo).
        operador: Solo para ``filtrar_filas``: las filas que cumplen
            ``columna operador valor`` se quedan, el resto se eliminan.
        valor: Solo para ``filtrar_filas``, en texto ("500", "3,5", "Madrid").
        nombre_nuevo: Solo para ``renombrar_columna``.
    """

    model_config = ConfigDict(extra="forbid")

    tipo: Literal[
        "eliminar_columna",
        "renombrar_columna",
        "eliminar_filas_con_nulos",
        "filtrar_filas",
        "eliminar_duplicados",
        "quitar_atipicos",
        "convertir_a_numero",
    ]
    columna: str | None
    operador: Literal["<", "<=", ">", ">=", "==", "!="] | None
    valor: str | None
    nombre_nuevo: str | None


# =============================================================================
# Utilidades
# =============================================================================


def _columna_real(df, nombre):
    """Columna del DataFrame cuyo nombre en texto es nombre.

    La LLM ve los nombres en texto, pero las columnas pueden no serlo (por
    ejemplo, 2020 en la cabecera de un Excel).

    Raises:
        ErrorTransformacion: Si falta el nombre o no existe la columna.
    """
    if nombre is None or str(nombre).strip() == "":
        raise ErrorTransformacion("Falta indicar la columna.")
    for columna in df.columns:
        if str(columna) == nombre:
            return columna
    raise ErrorTransformacion("No existe la columna «" + str(nombre) + "».")


def _a_numero(texto):
    """ "3,5" -> 3.5; None si no es un número finito."""
    if texto is None:
        return None
    try:
        numero = float(str(texto).strip().replace(",", "."))
    except ValueError:
        return None
    if not math.isfinite(numero):
        return None
    return numero


def _serie_numerica(serie):
    """La columna como números; lo que no lo es queda como NaN."""
    if pd.api.types.is_bool_dtype(serie):
        return pd.Series(math.nan, index=serie.index)
    if pd.api.types.is_numeric_dtype(serie):
        return serie.astype(float)
    texto = serie.astype("string").str.strip().str.replace(",", ".")
    return pd.to_numeric(texto, errors="coerce").astype(float)


def _eliminadas(numero):
    """3 -> "se eliminan 3 filas"; 1 -> "se elimina 1 fila"."""
    if numero == 0:
        return "no se elimina ninguna fila"
    if numero == 1:
        return "se elimina 1 fila"
    return "se eliminan " + str(numero) + " filas"


# =============================================================================
# Operaciones
# =============================================================================


def _eliminar_columna(df, op):
    columna = _columna_real(df, op.columna)
    if len(df.columns) == 1:
        raise ErrorTransformacion(
            "No se puede eliminar «" + str(columna) + "»: es la única "
            "columna del dataset."
        )
    return (
        df.drop(columns=[columna]),
        "Se elimina la columna «" + str(columna) + "».",
    )


def _renombrar_columna(df, op):
    columna = _columna_real(df, op.columna)
    nuevo = (op.nombre_nuevo or "").strip()
    if nuevo == "":
        raise ErrorTransformacion("Falta el nombre nuevo de la columna.")
    otras = [str(c) for c in df.columns if c is not columna]
    if nuevo in otras:
        raise ErrorTransformacion(
            "Ya hay una columna llamada «" + nuevo + "»."
        )
    return (
        df.rename(columns={columna: nuevo}),
        "La columna «" + str(columna) + "» pasa a llamarse «" + nuevo + "».",
    )


def _mascara_nulos(serie):
    vacias = serie.map(lambda v: isinstance(v, str) and v.strip() == "")
    return serie.isna() | vacias.astype(bool)


def _eliminar_nulos(df, op):
    if op.columna is None:
        mascara = pd.Series(False, index=df.index)
        for columna in df.columns:
            mascara = mascara | _mascara_nulos(df[columna])
        donde = "en alguna columna"
    else:
        columna = _columna_real(df, op.columna)
        mascara = _mascara_nulos(df[columna])
        donde = "en «" + str(columna) + "»"
    eliminadas = int(mascara.sum())
    return (
        df[~mascara],
        "Filas con valores inexistentes "
        + donde
        + ": "
        + _eliminadas(eliminadas)
        + ".",
    )


def _comparar(serie, operador, valor):
    if operador == "<":
        return serie < valor
    if operador == "<=":
        return serie <= valor
    if operador == ">":
        return serie > valor
    if operador == ">=":
        return serie >= valor
    if operador == "==":
        return serie == valor
    return serie != valor


def _filtrar(df, op):
    columna = _columna_real(df, op.columna)
    if op.operador not in OPERADORES:
        raise ErrorTransformacion("Falta el operador para filtrar.")
    if op.valor is None or op.valor.strip() == "":
        raise ErrorTransformacion("Falta el valor con el que filtrar.")
    numero = _a_numero(op.valor)
    serie = df[columna]
    numerica = _serie_numerica(serie)
    if numero is not None and numerica.notna().any():
        cumple = _comparar(numerica, op.operador, numero)
        valor_texto = formatear_numero(numero)
    else:
        if op.operador not in ("==", "!="):
            raise ErrorTransformacion(
                "«" + str(columna) + "» no es numérica: solo se puede "
                "filtrar por igual (==) o distinto (!=)."
            )
        cumple = _comparar(
            serie.astype("string").str.strip(), op.operador, op.valor.strip()
        )
        valor_texto = "«" + op.valor.strip() + "»"
    # Las filas sin valor en la columna nunca cumplen la condición
    cumple = cumple.fillna(False).astype(bool) & ~_mascara_nulos(serie)
    eliminadas = int((~cumple).sum())
    return (
        df[cumple],
        "Se quedan las filas con "
        + str(columna)
        + " "
        + op.operador
        + " "
        + valor_texto
        + ": "
        + _eliminadas(eliminadas)
        + ".",
    )


def _eliminar_duplicados(df, op):
    if op.columna is None:
        duplicadas = df.duplicated()
        donde = "Filas repetidas"
    else:
        columna = _columna_real(df, op.columna)
        duplicadas = df.duplicated(subset=[columna])
        donde = "Filas con «" + str(columna) + "» repetido"
    eliminadas = int(duplicadas.sum())
    return (
        df[~duplicadas],
        donde + ": " + _eliminadas(eliminadas) + ".",
    )


def _quitar_atipicos(df, op):
    columna = _columna_real(df, op.columna)
    numerica = _serie_numerica(df[columna])
    if numerica.notna().sum() < 4:
        raise ErrorTransformacion(
            "«" + str(columna) + "» no tiene suficientes valores numéricos "
            "para buscar atípicos."
        )
    q1 = numerica.quantile(0.25)
    q3 = numerica.quantile(0.75)
    margen = FACTOR_IQR * (q3 - q1)
    minimo = q1 - margen
    maximo = q3 + margen
    # Los nulos no se tocan: de ellos se encarga el preprocesado
    atipicos = (numerica < minimo) | (numerica > maximo)
    eliminadas = int(atipicos.sum())
    return (
        df[~atipicos],
        "Filas con «"
        + str(columna)
        + "» fuera de ["
        + formatear_numero(minimo, 4)
        + ", "
        + formatear_numero(maximo, 4)
        + "] (regla del rango intercuartílico): "
        + _eliminadas(eliminadas)
        + ".",
    )


def _convertir_a_numero(df, op):
    columna = _columna_real(df, op.columna)
    serie = df[columna]
    numerica = _serie_numerica(serie)
    antes = int((~_mascara_nulos(serie)).sum())
    perdidos = antes - int(numerica.notna().sum())
    copia = df.copy()
    copia[columna] = numerica
    texto = "La columna «" + str(columna) + "» pasa a ser numérica"
    if perdidos > 0:
        texto = (
            texto
            + ": "
            + str(perdidos)
            + " valores que no eran números quedan como inexistentes"
        )
    return copia, texto + "."


_APLICAR = {
    ELIMINAR_COLUMNA: _eliminar_columna,
    RENOMBRAR_COLUMNA: _renombrar_columna,
    ELIMINAR_NULOS: _eliminar_nulos,
    FILTRAR: _filtrar,
    ELIMINAR_DUPLICADOS: _eliminar_duplicados,
    QUITAR_ATIPICOS: _quitar_atipicos,
    CONVERTIR_A_NUMERO: _convertir_a_numero,
}


def aplicar_operacion(df, operacion):
    """Aplica una operación y explica en una frase lo que ha cambiado.

    Returns:
        Tupla ``(datos_nuevos, descripcion)``. df no se modifica.

    Raises:
        ErrorTransformacion: Si la operación no se puede aplicar.
    """
    funcion = _APLICAR.get(operacion.tipo)
    if funcion is None:
        raise ErrorTransformacion(
            "Operación desconocida: " + str(operacion.tipo)
        )
    return funcion(df, operacion)


def aplicar_operaciones(df, operaciones):
    """Aplica las operaciones en orden sobre una copia del dataset.

    Returns:
        Tupla ``(datos_nuevos, descripciones)``, con una frase por
        operación.

    Raises:
        ErrorTransformacion: Si alguna no se puede aplicar o el dataset se
            queda sin filas. En ese caso no se aplica ninguna.
    """
    datos = df
    descripciones = []
    for numero, operacion in enumerate(operaciones, start=1):
        try:
            datos, descripcion = aplicar_operacion(datos, operacion)
        except ErrorTransformacion as error:
            raise ErrorTransformacion(
                "Cambio " + str(numero) + ": " + str(error)
            ) from error
        descripciones.append(descripcion)
    if len(datos) == 0:
        raise ErrorTransformacion(
            "Con estos cambios el dataset se quedaría sin filas."
        )
    return datos.reset_index(drop=True), descripciones
