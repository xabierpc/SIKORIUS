class ErrorSikorius(Exception):
    """Error en el codigo"""


class ErrorImportacion(ErrorSikorius):
    """Error producido al importar un archivo de datos"""


class ErrorSeleccion(ErrorSikorius):
    """Selección de columnas no válida para un modelo de regresión lineal."""


class ErrorSeparacion(ErrorSikorius):
    """Parámetros o dataset no válidos para separar en entrenamiento y test."""


class ErrorPreprocesado(ErrorSikorius):
    """Error producido al aplicar el preprocesado."""


class AvisoPreprocesado(ErrorPreprocesado):
    """El preprocesado se puede hacer, pero el resultado no sería válido."""


class ColumnasNoEncontradasError(ErrorPreprocesado, ValueError):
    """Se lanza cuando alguna columna seleccionada no existe en el DataFrame.

    Hereda de ``ErrorPreprocesado`` para que la interfaz también la capture
    y muestre el mensaje en lugar de fallar.
    """
