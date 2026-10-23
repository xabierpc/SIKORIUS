"""Estado compartido de la aplicación.

Guarda el dataset cargado y su ruta para que lo usen los pasos siguientes
(selección de columnas, separación en entrenamiento y test, preprocesado y
creación del modelo). La lectura de archivos la hace siempre el módulo de
importación; aquí solo se guarda el resultado.
"""

from pathlib import Path

from sikorius.importador import importar_datos


class EstadoApp:
    """Datos cargados en la aplicación (una sola instancia, app local)."""

    def __init__(self):
        self.datos = None
        self.ruta = None
        self.seleccion = None

    def hay_datos(self):
        """Indica si ya se ha cargado algún dataset."""
        return self.datos is not None

    def guardar_seleccion(self, features, target, tipo_regresion):
        """Guarda la selección de columnas ya validada.

        Args:
            features: Lista con los nombres de las columnas de entrada.
            target: Nombre de la columna de salida.
            tipo_regresion: "simple" o "multiple".
        """
        self.seleccion = {
            "features": list(features),
            "target": target,
            "tipo_regresion": tipo_regresion,
        }

    def borrar_seleccion(self):
        """Olvida la selección de columnas (p. ej. al cambiar de dataset)."""
        self.seleccion = None

    def cargar(self, ruta_archivo):
        """Importa el archivo y, si todo va bien, sustituye los datos actuales.

        Args:
            ruta_archivo: Ruta del archivo (str o Path).

        Returns:
            DataFrame con los datos importados.

        Raises:
            ErrorImportacion: Si el módulo de importación no puede leer el
            archivo. En ese caso los datos y la ruta anteriores se conservan.
        """
        df = importar_datos(ruta_archivo)
        self.datos = df
        self.ruta = str(Path(ruta_archivo).resolve())
        self.seleccion = None  # las columnas del dataset anterior ya no valen
        return df


# Instancia única que comparte toda la aplicación
estado = EstadoApp()