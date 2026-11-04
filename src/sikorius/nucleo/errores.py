"""Errores esperados de SIKORIUS: la GUI muestra su mensaje tal cual."""


class ErrorSikorius(Exception):
    """Base de todos los errores que se explican al usuario."""


class ErrorImportacion(ErrorSikorius):
    """No se puede importar el archivo de datos."""


class ErrorSeleccion(ErrorSikorius):
    """Selección de columnas no válida para una regresión lineal."""


class ErrorSeparacion(ErrorSikorius):
    """Parámetros o dataset no válidos para separar en entrenamiento y test."""


class ErrorPreprocesado(ErrorSikorius):
    """No se puede aplicar el preprocesado."""


class ErrorModelo(ErrorSikorius):
    """No se puede crear el modelo de regresión lineal."""


class AvisoPreprocesado(ErrorPreprocesado):
    """El preprocesado se podría hacer, pero el resultado no sería válido."""


class ColumnasNoEncontradasError(ErrorPreprocesado, ValueError):
    """Alguna columna seleccionada no existe en el DataFrame."""
