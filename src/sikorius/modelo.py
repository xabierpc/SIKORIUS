import numpy as np

from sikorius.preprocesado import modelo_disponible


class ErrorModelo(Exception):
    """Error producido al crear el modelo."""


class ModeloLineal:
    """Modelo de regresión lineal ya entrenado.

    Attributes:
        features: Nombres de las columnas de entrada.
        target: Nombre de la columna de salida.
        coeficientes: Un coeficiente por cada columna de entrada.
        termino_independiente: Término independiente del modelo.
    """

    def __init__(self, features, target, coeficientes,
                 termino_independiente):
        self.features = tuple(features)
        self.target = target
        self.coeficientes = tuple(coeficientes)
        self.termino_independiente = termino_independiente

    def predecir(self, df):
        """Calcula la salida que predice el modelo para cada fila.

        Args:
            df: DataFrame que contiene las columnas de entrada del modelo.

        Returns:
            Array de numpy con una predicción por fila.
        """
        resultado = []
        for fila in df[list(self.features)].to_numpy(dtype=float):
            suma = self.termino_independiente
            for valor, coef in zip(fila, self.coeficientes):
                suma += valor * coef
            resultado.append(suma)
        return np.array(resultado)


def entrenar_modelo(entrenamiento, features, target):
    """Ajusta un modelo de regresión lineal por mínimos cuadrados.

    Usa el DataFrame que se le pasa, que es el conjunto de
    entrenamiento, y no lo modifica.

    Args:
        entrenamiento: DataFrame de entrenamiento.
        features: Nombres de las columnas de entrada.
        target: Nombre de la columna de salida.

    Returns:
        El ModeloLineal entrenado.
    """
    features = list(features)
    entrada = entrenamiento[features].to_numpy(dtype=float)
    salida = entrenamiento[target].to_numpy(dtype=float)
    ampliada = np.column_stack([entrada, np.ones(len(entrada))])
    solucion = np.linalg.lstsq(ampliada, salida, rcond=None)[0]
    return ModeloLineal(
        features=tuple(features),
        target=target,
        coeficientes=tuple(float(c) for c in solucion[:-1]),
        termino_independiente=float(solucion[-1]),
    )


def _entrenamiento_vigente(estado):
    """Entrenamiento preprocesado, si lo hay, o el original."""
    if estado.preprocesado is not None:
        return estado.preprocesado["entrenamiento"]
    return estado.entrenamiento


def crear_modelo(estado):
    """Crea el modelo con la selección y el entrenamiento del estado.

    Args:
        estado: Estado de la aplicación.

    Returns:
        El ModeloLineal creado.

    Raises:
        ErrorModelo: Si falta la selección de columnas, la separación en
            entrenamiento y test, o quedan valores inexistentes en las
            columnas seleccionadas de alguno de los dos conjuntos.
    """
    if not modelo_disponible(estado):
        raise ErrorModelo(
            "No se puede crear el modelo: confirma la selección de "
            "columnas, separa los datos y trata los valores inexistentes."
        )
    seleccion = estado.seleccion
    modelo = entrenar_modelo(
        _entrenamiento_vigente(estado),
        seleccion["features"],
        seleccion["target"],
    )
    estado.modelo = modelo
    return modelo