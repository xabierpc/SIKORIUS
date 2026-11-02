import numpy as np

from sikorius.preprocesado import modelo_disponible


class ErrorModelo(Exception):
    """Error producido al crear el modelo."""


class ModeloLineal:
    """Modelo de regresión lineal ya entrenado.

    Attributes:
        features: Nombres de las columnas de entrada, en el orden de los
            coeficientes.
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
        entrada = df[list(self.features)].to_numpy(dtype=float)
        return entrada @ np.array(self.coeficientes) + (
            self.termino_independiente)


def entrenar_modelo(entrenamiento, features, target):
    """Ajusta un modelo de regresión lineal por mínimos cuadrados.

    Args:
        entrenamiento: DataFrame de entrenamiento, sin valores
            inexistentes en las columnas usadas.
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


def conjuntos_vigentes(estado):
    """Devuelve los conjuntos de entrenamiento y test que se están usando.

    Args:
        estado: Estado de la aplicación, con la separación hecha.

    Returns:
        Tupla (entrenamiento, test) de DataFrames.
    """
    if estado.preprocesado is not None:
        return (estado.preprocesado["entrenamiento"],
                estado.preprocesado["test"])
    return estado.entrenamiento, estado.test


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
    entrenamiento, _ = conjuntos_vigentes(estado)
    modelo = entrenar_modelo(
        entrenamiento, seleccion["features"], seleccion["target"]
    )
    estado.modelo = modelo
    return modelo


def datos_ajuste(modelo, entrenamiento, test):
    """Calcula los datos que muestra el gráfico del ajuste del modelo.

    Args:
        modelo: ModeloLineal ya entrenado.
        entrenamiento: DataFrame de entrenamiento.
        test: DataFrame de test.

    Returns:
        Diccionario con las claves "tipo" ("simple" o "multiple"),
        "etiqueta_x", "etiqueta_y", "etiqueta_recta", y "entrenamiento",
        "test" y "recta", que son tuplas (valores_x, valores_y).
    """
    real = {
        "entrenamiento": entrenamiento[modelo.target].to_numpy(dtype=float),
        "test": test[modelo.target].to_numpy(dtype=float),
    }
    if len(modelo.features) == 1:
        columna = modelo.features[0]
        puntos = {
            "entrenamiento": (
                entrenamiento[columna].to_numpy(dtype=float),
                real["entrenamiento"]),
            "test": (test[columna].to_numpy(dtype=float), real["test"]),
        }
        extremos = np.array([
            min(puntos["entrenamiento"][0].min(), puntos["test"][0].min()),
            max(puntos["entrenamiento"][0].max(), puntos["test"][0].max()),
        ])
        recta = modelo.coeficientes[0] * extremos + (
            modelo.termino_independiente)
        return {
            "tipo": "simple",
            "etiqueta_x": columna,
            "etiqueta_y": modelo.target,
            "etiqueta_recta": "Recta del modelo",
            "entrenamiento": puntos["entrenamiento"],
            "test": puntos["test"],
            "recta": (extremos, recta),
        }

    predicho = {
        "entrenamiento": modelo.predecir(entrenamiento),
        "test": modelo.predecir(test),
    }
    todos = np.concatenate(list(real.values()) + list(predicho.values()))
    extremos = np.array([todos.min(), todos.max()])
    return {
        "tipo": "multiple",
        "etiqueta_x": "Valor predicho",
        "etiqueta_y": "Valor real",
        "etiqueta_recta": "Real = predicho",
        "entrenamiento": (predicho["entrenamiento"], real["entrenamiento"]),
        "test": (predicho["test"], real["test"]),
        "recta": (extremos, extremos),
    }


def dibujar_ajuste(figura, datos):
    """Dibuja el gráfico del ajuste en una figura de matplotlib.

    Args:
        figura: Figura de matplotlib (``matplotlib.figure.Figure``).
        datos: Diccionario devuelto por ``datos_ajuste``.
    """
    figura.clear()
    ejes = figura.subplots()
    ejes.scatter(*datos["entrenamiento"], color="tab:blue", marker="o",
                 label="Entrenamiento")
    ejes.scatter(*datos["test"], color="tab:orange", marker="s",
                 label="Test")
    ejes.plot(*datos["recta"], color="black", linestyle="--",
              label=datos["etiqueta_recta"])
    ejes.set_xlabel(datos["etiqueta_x"])
    ejes.set_ylabel(datos["etiqueta_y"])
    ejes.legend()
    figura.tight_layout()


DECIMALES_FORMULA = 4
 
 
def formula_texto(modelo, decimales=DECIMALES_FORMULA):
    """Escribe la fórmula del modelo con los nombres de las columnas.
 
    Args:
        modelo: ModeloLineal ya entrenado.
        decimales: Decimales con los que se muestran los números.
 
    Returns:
        El texto de la fórmula.
    """
    terminos = []
    for coeficiente, columna in zip(modelo.coeficientes, modelo.features):
        numero = _numero_sin_signo(coeficiente, decimales)
        terminos.append((coeficiente, f"{numero} * {columna}"))
    independiente = modelo.termino_independiente
    terminos.append(
        (independiente, _numero_sin_signo(independiente, decimales))
    )
 
    texto = f"{modelo.target} ="
    for posicion, (valor, cuerpo) in enumerate(terminos):
        negativo = round(valor, decimales) < 0
        if posicion == 0:
            texto += f" -{cuerpo}" if negativo else f" {cuerpo}"
        else:
            texto += f" - {cuerpo}" if negativo else f" + {cuerpo}"
    return texto
 
 
def _numero_sin_signo(valor, decimales):
    """Valor absoluto redondeado, con siempre los mismos decimales."""
    return f"{abs(round(valor, decimales)):.{decimales}f}"