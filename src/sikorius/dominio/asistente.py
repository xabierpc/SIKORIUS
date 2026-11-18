"""Lo que el asistente sabe y lo que puede contestar.

Define la forma de la respuesta de la LLM (``RespuestaAsistente``), las
instrucciones que recibe y el resumen del trabajo actual que se le manda.
Al asistente nunca se le mandan las filas del dataset: solo los nombres de
las columnas y algunas estadísticas de cada una, y el modelo si lo hay.

No sabe nada de Groq ni de la interfaz: eso es cosa de ``datos`` y
``gui``.
"""

from pydantic import BaseModel, ConfigDict

from sikorius.dominio.modelo import formula_texto
from sikorius.dominio.texto import formatear_numero
from sikorius.dominio.transformaciones import Operacion

# Columnas que se describen como mucho (datasets muy anchos)
MAX_COLUMNAS_CONTEXTO = 60


class RespuestaAsistente(BaseModel):
    """Respuesta de la LLM: un mensaje y, si hace falta, cambios.

    Attributes:
        mensaje: Lo que se le enseña al usuario, en lenguaje natural.
        operaciones: Cambios al dataset que propone, en orden. Vacía si
            solo contesta o explica algo.
    """

    model_config = ConfigDict(extra="forbid")

    mensaje: str
    operaciones: list[Operacion]


INSTRUCCIONES = """\
Eres el asistente de SIKORIUS, una aplicación para crear modelos de \
regresión lineal a partir de un dataset. Respondes siempre en español, \
breve y claro, para alguien que está aprendiendo.

Puedes hacer dos cosas:
1. Explicar: el dataset, el modelo (fórmula, coeficientes, R², ECM) o \
qué significa un resultado. En ese caso "operaciones" va vacía.
2. Proponer cambios al dataset cuando el usuario lo pida, usando SOLO \
estas operaciones (los campos que no usa una operación van a null):
- eliminar_columna: columna.
- renombrar_columna: columna, nombre_nuevo.
- eliminar_filas_con_nulos: columna, o null para filas con algún nulo.
- filtrar_filas: columna, operador (<, <=, >, >=, ==, !=) y valor en \
texto. Se QUEDAN las filas que cumplen la condición.
- eliminar_duplicados: columna, o null para filas idénticas.
- quitar_atipicos: columna numérica (regla del rango intercuartílico).
- convertir_a_numero: columna con números guardados como texto.

Reglas:
- Usa exactamente los nombres de columna del resumen.
- Si el usuario pide algo que no está en la lista, no lo inventes: dile \
qué sí puedes hacer. Rellenar nulos con la media, la mediana o una \
constante se hace en la pestaña "Preprocesado" (así se calcula solo con \
el entrenamiento), y elegir columnas en "Variables y separacion".
- Los cambios no se aplican solos: el usuario los ve antes y los \
confirma. En "mensaje" explica qué vas a cambiar y por qué.
- Si no hay dataset cargado, no propongas cambios.
- No inventes datos ni valores que no estén en el resumen.
"""


def _describir_columna(df, columna):
    serie = df[columna]
    nulos = int(serie.isna().sum())
    partes = ["- «" + str(columna) + "» (" + str(serie.dtype) + ")"]
    partes.append("nulos: " + str(nulos))
    if serie.dtype.kind in "iuf" and serie.notna().any():
        partes.append("mín: " + formatear_numero(serie.min(), 4))
        partes.append("máx: " + formatear_numero(serie.max(), 4))
        partes.append("media: " + formatear_numero(serie.mean(), 4))
    else:
        partes.append("valores distintos: " + str(serie.nunique()))
    return ", ".join(partes)


def _describir_dataset(df):
    lineas = [
        "Dataset: "
        + str(len(df))
        + " filas, "
        + str(len(df.columns))
        + " columnas, "
        + str(int(df.duplicated().sum()))
        + " filas duplicadas.",
        "Columnas:",
    ]
    for columna in list(df.columns)[:MAX_COLUMNAS_CONTEXTO]:
        lineas.append(_describir_columna(df, columna))
    if len(df.columns) > MAX_COLUMNAS_CONTEXTO:
        sobran = len(df.columns) - MAX_COLUMNAS_CONTEXTO
        lineas.append("(y " + str(sobran) + " columnas más)")
    return lineas


def _describir_metricas(metricas):
    lineas = []
    for conjunto in ("entrenamiento", "test"):
        valores = (metricas or {}).get(conjunto)
        if not valores:
            continue
        texto = []
        for nombre, etiqueta in (("r2", "R²"), ("ecm", "ECM")):
            valor = valores.get(nombre)
            if valor is None or valor != valor:  # None o NaN
                texto.append(etiqueta + " no disponible")
            else:
                texto.append(etiqueta + " = " + formatear_numero(valor, 4))
        lineas.append("- " + conjunto + ": " + ", ".join(texto))
    return lineas


def construir_contexto(
    datos=None, seleccion=None, modelo=None, metricas=None, etapa=None
):
    """Resumen en texto del trabajo actual para dárselo a la LLM.

    Args:
        datos: DataFrame del dataset cargado, o None.
        seleccion: Tupla ``(features, target)`` confirmada, o None.
        modelo: ModeloLineal actual, o None.
        metricas: Diccionario de ``metricas_modelo``, o None.
        etapa: Pestaña en la que está el usuario, o None.

    Returns:
        Texto con un apartado por cada cosa que hay.
    """
    lineas = []
    if etapa:
        lineas.append("El usuario está en la pestaña: " + etapa + ".")
    if datos is None:
        lineas.append("No hay ningún dataset cargado.")
    else:
        lineas.extend(_describir_dataset(datos))
    if seleccion is not None:
        features, target = seleccion
        lineas.append(
            "Columnas elegidas para el modelo: entrada "
            + ", ".join("«" + str(f) + "»" for f in features)
            + "; salida «"
            + str(target)
            + "»."
        )
    if modelo is None:
        lineas.append("Todavía no hay modelo.")
    else:
        lineas.append("Modelo: " + formula_texto(modelo))
        if modelo.descripcion:
            lineas.append("Descripción del modelo: " + modelo.descripcion)
        lineas.extend(_describir_metricas(metricas))
    return "\n".join(lineas)
