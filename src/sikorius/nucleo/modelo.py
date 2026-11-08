"""Modelo de regresión lineal: ajuste, métricas, fórmula y gráfico.

Todas las funciones reciben DataFrames y devuelven resultados nuevos: no
conocen la sesión ni la interfaz gráfica. Quien guarda el modelo y avisa a
la interfaz es ``Sesion.crear_modelo``.
"""

import numpy as np

from sikorius.nucleo.errores import ErrorModelo


class ModeloLineal:
    """Modelo de regresión lineal ya entrenado.

    Attributes:
        features: Nombres de las columnas de entrada, en el orden de los
            coeficientes.
        target: Nombre de la columna de salida.
        coeficientes: Un coeficiente por cada columna de entrada.
        termino_independiente: Término independiente del modelo.
        descripcion: Texto libre, opcional, sobre en qué consiste el modelo
            y con qué propósito se creó. Empieza vacío y se puede cambiar
            cuando se quiera.
    """

    def __init__(
        self,
        features,
        target,
        coeficientes,
        termino_independiente,
        descripcion="",
    ):
        self.features = tuple(features)
        self.target = target
        self.coeficientes = tuple(coeficientes)
        self.termino_independiente = termino_independiente
        self.descripcion = descripcion

    def predecir(self, df):
        """Calcula la salida que predice el modelo para cada fila.

        Args:
            df: DataFrame que contiene las columnas de entrada del modelo.

        Returns:
            Array de numpy con una predicción por fila.
        """
        entrada = df[list(self.features)].to_numpy(dtype=float)
        return entrada @ np.array(self.coeficientes) + (
            self.termino_independiente
        )


def _columna_numerica(df, columna):
    """Devuelve una columna como array de floats, o falla con ErrorModelo.

    Args:
        df: DataFrame que contiene la columna.
        columna: Nombre de la columna.

    Raises:
        ErrorModelo: Si la columna no existe, no es numérica o tiene
            valores inexistentes o infinitos.
    """
    if columna not in df.columns:
        raise ErrorModelo(f"No existe la columna '{columna}' en los datos.")
    try:
        valores = df[columna].to_numpy(dtype=float, na_value=np.nan)
    except (TypeError, ValueError):
        raise ErrorModelo(
            f"La columna '{columna}' no es numérica: la regresión lineal "
            "solo funciona con números."
        ) from None
    if np.isnan(valores).any():
        raise ErrorModelo(
            f"La columna '{columna}' tiene valores inexistentes."
        )
    if np.isinf(valores).any():
        raise ErrorModelo(f"La columna '{columna}' tiene valores infinitos.")
    return valores


def entrenar_modelo(entrenamiento, features, target):
    """Ajusta un modelo de regresión lineal por mínimos cuadrados.

    Solo usa el DataFrame que se le pasa, que debe ser el conjunto de
    entrenamiento, y no lo modifica.

    Args:
        entrenamiento: DataFrame de entrenamiento, sin valores
            inexistentes en las columnas usadas.
        features: Nombres de las columnas de entrada.
        target: Nombre de la columna de salida.

    Returns:
        El ModeloLineal entrenado.

    Raises:
        ErrorModelo: Si el entrenamiento está vacío, tiene menos filas que
            parámetros, alguna columna no existe, no es numérica o tiene
            valores inexistentes o infinitos, o el modelo no tiene una
            solución única (columnas constantes o dependientes entre sí).
    """
    features = list(features)
    if len(entrenamiento) == 0:
        raise ErrorModelo("El conjunto de entrenamiento no tiene filas.")
    columnas = [_columna_numerica(entrenamiento, c) for c in features]
    salida = _columna_numerica(entrenamiento, target)

    parametros = len(features) + 1
    if len(salida) < parametros:
        raise ErrorModelo(
            f"Hay muy pocas filas de entrenamiento ({len(salida)}): con "
            f"{len(features)} columna(s) de entrada se necesitan al menos "
            f"{parametros}."
        )
    ampliada = np.column_stack(columnas + [np.ones(len(salida))])
    try:
        solucion, _, rango, _ = np.linalg.lstsq(ampliada, salida, rcond=None)
    except np.linalg.LinAlgError:
        raise ErrorModelo(
            "No se pudo calcular el modelo con estos datos."
        ) from None
    if rango < parametros:
        raise ErrorModelo(
            "No se puede calcular un modelo único: alguna columna de "
            "entrada es constante o se puede obtener a partir de otras."
        )
    return ModeloLineal(
        features=tuple(features),
        target=target,
        coeficientes=tuple(float(c) for c in solucion[:-1]),
        termino_independiente=float(solucion[-1]),
    )


def datos_ajuste(modelo, entrenamiento, test):
    """Calcula los datos que muestra el gráfico del ajuste del modelo.

    Con una sola columna de entrada (regresión simple) el gráfico enseña
    los puntos de cada conjunto y la recta del modelo. Con varias
    (regresión múltiple) enseña el valor real de la salida frente al
    valor predicho, y la recta en la que ambos coinciden.

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
                real["entrenamiento"],
            ),
            "test": (test[columna].to_numpy(dtype=float), real["test"]),
        }
        extremos = np.array(
            [
                min(puntos["entrenamiento"][0].min(), puntos["test"][0].min()),
                max(puntos["entrenamiento"][0].max(), puntos["test"][0].max()),
            ]
        )
        recta = modelo.coeficientes[0] * extremos + (
            modelo.termino_independiente
        )
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

    Borra lo que hubiera en la figura, así que se puede llamar de nuevo
    cada vez que se crea un modelo nuevo.

    Args:
        figura: Figura de matplotlib (``matplotlib.figure.Figure``).
        datos: Diccionario devuelto por ``datos_ajuste``.
    """
    figura.clear()
    ejes = figura.subplots()
    ejes.scatter(
        *datos["entrenamiento"],
        color="tab:blue",
        marker="o",
        label="Entrenamiento",
    )
    ejes.scatter(*datos["test"], color="tab:orange", marker="s", label="Test")
    ejes.plot(
        *datos["recta"],
        color="black",
        linestyle="--",
        label=datos["etiqueta_recta"],
    )
    # Pocas marcas en cada eje: con cifras grandes, si no, se pisan.
    ejes.locator_params(nbins=5)
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
    # Cada término es (valor, texto sin signo): "3.0000 * x" o "5.0000"
    terminos = []
    for coeficiente, columna in zip(
        modelo.coeficientes, modelo.features, strict=True
    ):
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


def calcular_ecm(real, predicho):
    """Error cuadrático medio: media de (real - predicho) al cuadrado.

    Args:
        real: Valores reales de la salida.
        predicho: Valores que predice el modelo.

    Returns:
        El error cuadrático medio, como float (``nan`` si no hay valores).
    """
    real = np.asarray(real, dtype=float)
    if real.size == 0:
        return float("nan")
    errores = real - np.asarray(predicho, dtype=float)
    return float(np.mean(errores**2))


def calcular_r2(real, predicho):
    """Coeficiente de determinación R² = 1 - SS_res / SS_tot.

    Args:
        real: Valores reales de la salida.
        predicho: Valores que predice el modelo.

    Returns:
        El R² como float. Si no hay valores o todos los reales son iguales
        no se puede calcular (SS_tot es 0) y devuelve ``nan``.
    """
    real = np.asarray(real, dtype=float)
    if real.size == 0:
        return float("nan")
    predicho = np.asarray(predicho, dtype=float)
    suma_residuos = np.sum((real - predicho) ** 2)
    suma_total = np.sum((real - real.mean()) ** 2)
    if suma_total == 0:
        return float("nan")
    return float(1 - suma_residuos / suma_total)


def metricas_modelo(modelo, entrenamiento, test):
    """Calcula R² y ECM del modelo en entrenamiento y en test.

    Args:
        modelo: ModeloLineal ya entrenado.
        entrenamiento: DataFrame de entrenamiento.
        test: DataFrame de test.

    Returns:
        Diccionario ``{"entrenamiento": {"r2": ..., "ecm": ...},
        "test": {"r2": ..., "ecm": ...}}``.
    """
    metricas = {}
    for nombre, df in (("entrenamiento", entrenamiento), ("test", test)):
        real = df[modelo.target].to_numpy(dtype=float)
        predicho = modelo.predecir(df)
        metricas[nombre] = {
            "r2": calcular_r2(real, predicho),
            "ecm": calcular_ecm(real, predicho),
        }
    return metricas
