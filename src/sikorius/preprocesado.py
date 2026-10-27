"""
Elimina las filas con valores inexistentes o los rellena (media, mediana o
valor constante) en los conjuntos de entrenamiento y test, y guarda el
resultado en el estado de la aplicación.
"""
 
ELIMINAR = "eliminar"
MEDIA = "media"
MEDIANA = "mediana"
CONSTANTE = "constante"
ESTRATEGIAS = (ELIMINAR, MEDIA, MEDIANA, CONSTANTE)
 
 
class ErrorPreprocesado(Exception):
    """Error producido al aplicar el preprocesado."""
 
 
def quedan_nulos(df, columnas):
    """Indica si queda algún valor inexistente en las columnas indicadas.
 
    Args:
        df: DataFrame a revisar.
        columnas: Lista de nombres de columnas.
 
    Returns:
        True si hay al menos un valor inexistente, False en caso contrario.
    """
    return bool(df[list(columnas)].isna().any().any())
 
 
def columnas_seleccionadas(estado):
    """Devuelve las columnas de entrada seguidas de la de salida.
 
    Args:
        estado: Estado de la aplicación, con la selección ya confirmada.
 
    Returns:
        Lista con las features y, al final, el target.
    """
    seleccion = estado.seleccion
    return list(seleccion["features"]) + [seleccion["target"]]
 
 
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
        ErrorPreprocesado: Si la estrategia no es válida.
    """
    columnas = list(columnas)
    if estrategia not in ESTRATEGIAS:
        raise ErrorPreprocesado(f"Estrategia no válida: {estrategia}")
 
    train_proc = train.copy()
    test_proc = test.copy()
 
    if estrategia == ELIMINAR:
        train_proc = train_proc.dropna(subset=columnas)
        test_proc = test_proc.dropna(subset=columnas)
        resumen = {
            "train": _resumen(len(train) - len(train_proc), 0),
            "test": _resumen(len(test) - len(test_proc), 0),
        }
        return train_proc, test_proc, resumen
 
    if estrategia == CONSTANTE:
        valores = {c: constante for c in columnas}
    elif estrategia == MEDIA:
        valores = train[columnas].mean().to_dict()
    else:
        valores = train[columnas].median().to_dict()
 
    train_proc = train_proc.fillna(valores)
    test_proc = test_proc.fillna(valores)
    resumen = {
        "train": _resumen(0, _nulos(train, columnas)
                          - _nulos(train_proc, columnas)),
        "test": _resumen(0, _nulos(test, columnas)
                         - _nulos(test_proc, columnas)),
    }
    return train_proc, test_proc, resumen
 
 
def _nulos(df, columnas):
    """Número total de valores inexistentes en las columnas indicadas."""
    return int(df[columnas].isna().sum().sum())
 
 
def aplicar_al_estado(estado, estrategia, constante=None):
    """Preprocesa los conjuntos guardados en el estado y guarda el resultado.
 
    Args:
        estado: Estado de la aplicación.
        estrategia: "eliminar", "media", "mediana" o "constante".
        constante: Número con el que rellenar (solo para "constante").
 
    Returns:
        El resumen del preprocesado (ver ``aplicar_preprocesado``).
 
    Raises:
        ErrorPreprocesado: Si no hay selección confirmada ni separación en
            entrenamiento y test, o si la estrategia no es válida. En ese
            caso el estado no se modifica.
    """
    if not estado.hay_seleccion():
        raise ErrorPreprocesado("Confirma primero la selección de columnas.")
    if not estado.hay_separacion():
        raise ErrorPreprocesado("Separa primero en entrenamiento y test.")
    entrenamiento, test, resumen = aplicar_preprocesado(
        estado.entrenamiento,
        estado.test,
        columnas_seleccionadas(estado),
        estrategia,
        constante,
    )
    estado.preprocesado = {
        "entrenamiento": entrenamiento,
        "test": test,
        "estrategia": estrategia,
        "resumen": resumen,
    }
    return resumen
 
 
def modelo_disponible(estado):
    """Indica si se puede crear el modelo con los datos del estado.

    Args:
        estado: Estado de la aplicación.
 
    Returns:
        True si se puede crear el modelo, False en caso contrario.
    """
    if not estado.hay_seleccion() or not estado.hay_separacion():
        return False
    columnas = columnas_seleccionadas(estado)
    if estado.preprocesado is not None:
        entrenamiento = estado.preprocesado["entrenamiento"]
        test = estado.preprocesado["test"]
    else:
        entrenamiento, test = estado.entrenamiento, estado.test
    return not (
        quedan_nulos(entrenamiento, columnas) or quedan_nulos(test, columnas)
    )
 
 
def texto_resumen(resumen):
    """Redacta el mensaje de éxito a partir del resumen del preprocesado.
 
    Args:
        resumen: Diccionario devuelto por ``aplicar_preprocesado``.
 
    Returns:
        Texto con filas eliminadas y valores rellenados de cada conjunto.
    """
    partes = []
    for clave, nombre in (("train", "Entrenamiento"), ("test", "Test")):
        datos = resumen[clave]
        partes.append(
            f"{nombre}: {datos['filas_eliminadas']} filas eliminadas, "
            f"{datos['valores_rellenados']} valores rellenados"
        )
    return "Preprocesado aplicado. " + " | ".join(partes) + "."