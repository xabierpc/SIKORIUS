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
        # Separación en entrenamiento y test (historia de separación)
        self.entrenamiento = None
        self.test = None
        self.separacion = None  # parámetros usados: porcentaje_test y semilla
        # Pasos posteriores, que dependen de la separación
        self.preprocesado = None
        self.modelo = None

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
        self.borrar_separacion()  # con otras columnas hay que volver a separar

    def borrar_seleccion(self):
        """Olvida la selección de columnas (p. ej. al cambiar de dataset)."""
        self.seleccion = None
        self.borrar_separacion()

    def hay_seleccion(self):
        """Indica si hay una selección de columnas confirmada."""
        return self.seleccion is not None

    def hay_separacion(self):
        """Indica si ya se ha separado el dataset en entrenamiento y test.

        El preprocesado y la creación del modelo solo deben permitirse
        cuando esto devuelve True.
        """
        return self.entrenamiento is not None and self.test is not None

    def guardar_separacion(self, entrenamiento, test, porcentaje_test, semilla):
        """Guarda los conjuntos de entrenamiento y test.

        Descarta el preprocesado y el modelo creados con una separación
        anterior, porque ya no corresponden a estos conjuntos.
        """
        self.entrenamiento = entrenamiento
        self.test = test
        self.separacion = {"porcentaje_test": porcentaje_test, "semilla": semilla}
        self.preprocesado = None
        self.modelo = None

    def borrar_separacion(self):
        """Olvida la separación y todo lo que se hizo a partir de ella."""
        self.entrenamiento = None
        self.test = None
        self.separacion = None
        self.preprocesado = None
        self.modelo = None

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
        self.borrar_seleccion()  # las columnas del dataset anterior ya no valen
        return df


# Instancia única que comparte toda la aplicación
estado = EstadoApp()