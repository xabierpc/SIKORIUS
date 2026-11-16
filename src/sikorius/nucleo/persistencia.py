"""Guardado y carga de un modelo de regresión lineal en un archivo JSON.

Sigue el formato elegido en la investigación de persistencia (historia
#20, ``docs/investigacion-persistencia.md``, apartado 6). El archivo
guarda el modelo, su fórmula, las métricas y la descripción, pero nunca
los datos con los que se entrenó ni los gráficos.

No conoce la sesión ni la interfaz gráfica: para guardar recibe el modelo,
sus métricas y la ruta, y escribe el archivo; para cargar (historia #24)
recibe la ruta y devuelve el modelo y sus métricas.
"""

import json
import math
import numbers
import os
import tempfile
from pathlib import Path

from sikorius.nucleo.errores import ErrorPersistencia
from sikorius.nucleo.modelo import ModeloLineal, formula_texto

FORMATO = "sikorius-modelo"
VERSION_FORMATO = 1
EXTENSION = ".json"

CONJUNTOS = ("entrenamiento", "test")
NOMBRES_METRICAS = ("r2", "ecm")


def ruta_con_extension(ruta):
    """Añade la extensión ``.json`` si la ruta no la tiene.

    La extensión se compara sin distinguir mayúsculas: "modelo.JSON" se
    deja igual. Si la ruta tiene otra extensión, se añade detrás:
    "modelo.v2" pasa a ser "modelo.v2.json".

    Args:
        ruta: Ruta del archivo, como texto o ``Path``.

    Returns:
        La ruta como ``Path``, terminada en ``.json``.
    """
    ruta = Path(ruta)
    if ruta.suffix.lower() == EXTENSION:
        return ruta
    return ruta.with_name(ruta.name + EXTENSION)


def modelo_a_diccionario(modelo, metricas):
    """Convierte el modelo y su información en el diccionario del archivo.

    Args:
        modelo: ModeloLineal ya entrenado (o cargado).
        metricas: Diccionario con la forma que devuelve
            ``metricas_modelo``: ``{"entrenamiento": {"r2": ..., "ecm":
            ...}, "test": {"r2": ..., "ecm": ...}}``.

    Returns:
        Diccionario con la estructura documentada en la historia #20, que
        solo contiene textos, números, ``None``, listas y diccionarios.

    Raises:
        ErrorPersistencia: Si las métricas no tienen la forma esperada, o
            el modelo tiene coeficientes que no son números finitos o no
            tiene un coeficiente por columna de entrada.
    """
    coeficientes = list(modelo.coeficientes)
    features = list(modelo.features)
    if len(coeficientes) != len(features):
        raise ErrorPersistencia(
            "El modelo no tiene un coeficiente por cada columna de entrada."
        )
    for valor in coeficientes + [modelo.termino_independiente]:
        if not _es_numero_finito(valor):
            raise ErrorPersistencia(
                "El modelo tiene un coeficiente que no es un número finito."
            )

    descripcion = modelo.descripcion
    if descripcion is None:
        descripcion = ""

    return {
        "formato": FORMATO,
        "version_formato": VERSION_FORMATO,
        "descripcion": str(descripcion),
        "formula": formula_texto(modelo),
        "modelo": {
            "features": features,
            "target": modelo.target,
            "coeficientes": [float(c) for c in coeficientes],
            "termino_independiente": float(modelo.termino_independiente),
        },
        "metricas": _metricas_a_diccionario(metricas),
    }


def guardar_modelo(modelo, metricas, ruta):
    """Guarda el modelo y su información en un archivo JSON.

    Escribe exactamente en la ruta indicada, sin añadir la extensión (para
    eso está ``ruta_con_extension``). Si el archivo ya existe lo
    sobrescribe: preguntar antes es cosa de la interfaz.

    Primero escribe un archivo temporal en la misma carpeta y, solo si
    todo ha ido bien, lo pone en el lugar del definitivo. Así, si falla
    a mitad, un archivo anterior con ese nombre queda intacto y no se deja
    un archivo a medias.

    Args:
        modelo: ModeloLineal ya entrenado (o cargado), con su descripción.
        metricas: Métricas de entrenamiento y test, con la forma que
            devuelve ``metricas_modelo``.
        ruta: Ruta del archivo, como texto o ``Path``. Admite espacios,
            tildes y la letra ñ.

    Returns:
        La ruta absoluta del archivo guardado, como ``Path``.

    Raises:
        ErrorPersistencia: Si el modelo o las métricas no son válidos, o
            no se puede escribir el archivo (la carpeta no existe, no hay
            permisos, no queda espacio...). En ese caso no se crea ni se
            modifica ningún archivo.
    """
    # Se convierte a texto antes de tocar el disco: si falla, no se crea
    # nada. allow_nan=False asegura que nunca se escribe un NaN.
    datos = modelo_a_diccionario(modelo, metricas)
    try:
        texto = json.dumps(
            datos, indent=2, ensure_ascii=False, allow_nan=False
        )
    except (TypeError, ValueError):
        raise ErrorPersistencia(
            "El modelo tiene datos que no se pueden guardar en el archivo."
        ) from None

    ruta = Path(ruta).absolute()
    if ruta.is_dir():
        raise ErrorPersistencia(
            "No se puede guardar el modelo: '%s' es una carpeta." % ruta
        )
    try:
        _escribir_reemplazando(ruta, texto + "\n")
    except OSError as error:
        mensaje = _mensaje_error_escritura(ruta, error)
        raise ErrorPersistencia(mensaje) from None
    return ruta


def cargar_modelo(ruta):
    """Lee un modelo guardado con ``guardar_modelo``.

    Comprueba todo el archivo antes de crear el modelo: si falta algo o
    tiene un valor que no corresponde, no se devuelve un modelo a medias.
    La fórmula del archivo no se lee, porque se calcula a partir de los
    coeficientes y las columnas.

    Args:
        ruta: Ruta del archivo, como texto o ``Path``. Admite espacios,
            tildes y la letra ñ.

    Returns:
        Tupla ``(modelo, metricas)``: el ModeloLineal con su descripción
        (vacía si se guardó sin ella) y las métricas con la forma que
        devuelve ``metricas_modelo``. Las métricas que se guardaron como
        ``null`` (no calculables) vuelven a ser NaN.

    Raises:
        ErrorPersistencia: Si no se puede leer el archivo, está dañado, no
            tiene el formato de SIKORIUS o le falta parte del modelo.
    """
    ruta = Path(ruta).absolute()
    datos = _leer_json(ruta)
    if not isinstance(datos, dict) or datos.get("formato") != FORMATO:
        raise ErrorPersistencia(
            "'%s' no es un archivo de modelo de SIKORIUS." % ruta.name
        )
    version = datos.get("version_formato")
    if not _es_numero(version) or version != VERSION_FORMATO:
        raise ErrorPersistencia(
            "El archivo '%s' tiene una versión del formato que esta "
            "aplicación no sabe leer." % ruta.name
        )

    contenido = _apartado(datos, "modelo", dict, ruta)
    features = _apartado(contenido, "features", list, ruta)
    target = _apartado(contenido, "target", str, ruta)
    coeficientes = _apartado(contenido, "coeficientes", list, ruta)
    independiente = _apartado(contenido, "termino_independiente", None, ruta)
    descripcion = _apartado(datos, "descripcion", str, ruta)

    if len(features) == 0 or not all(
        isinstance(f, str) and f != "" for f in features
    ):
        raise _archivo_danado(ruta, "las columnas de entrada no son válidas")
    if len(set(features)) != len(features):
        raise _archivo_danado(ruta, "hay columnas de entrada repetidas")
    if target == "" or target in features:
        raise _archivo_danado(ruta, "la columna de salida no es válida")
    if len(coeficientes) != len(features):
        raise _archivo_danado(
            ruta, "no hay un coeficiente por cada columna de entrada"
        )
    for valor in coeficientes + [independiente]:
        if not _es_numero_finito(valor):
            raise _archivo_danado(
                ruta, "algún coeficiente no es un número válido"
            )

    modelo = ModeloLineal(
        features=tuple(features),
        target=target,
        coeficientes=tuple(float(c) for c in coeficientes),
        termino_independiente=float(independiente),
        descripcion=descripcion,
    )
    metricas = _metricas_desde_diccionario(
        _apartado(datos, "metricas", dict, ruta), ruta
    )
    return modelo, metricas


def _leer_json(ruta):
    """Contenido JSON del archivo, o ErrorPersistencia con un mensaje claro.

    NaN e Infinity no son JSON válido (``guardar_modelo`` nunca los
    escribe), así que también se rechazan.
    """
    if ruta.is_dir():
        raise ErrorPersistencia(
            "No se puede cargar el modelo: '%s' es una carpeta." % ruta
        )
    try:
        texto = ruta.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ErrorPersistencia(
            "No se puede cargar el modelo: no existe el archivo '%s'." % ruta
        ) from None
    except PermissionError:
        raise ErrorPersistencia(
            "No se puede cargar el modelo: no tienes permiso para leer "
            "'%s'." % ruta
        ) from None
    except UnicodeDecodeError:
        raise _archivo_danado(ruta, "no es un archivo de texto") from None
    except OSError as error:
        detalle = error.strerror
        if not detalle:
            detalle = str(error)
        raise ErrorPersistencia(
            "No se pudo leer el modelo de '%s': %s." % (ruta, detalle)
        ) from None
    try:
        return json.loads(texto, parse_constant=_rechazar_constante)
    except ValueError:
        raise _archivo_danado(ruta, "no es un JSON válido") from None


def _rechazar_constante(nombre):
    raise ValueError("Constante no admitida: " + nombre)


def _archivo_danado(ruta, motivo):
    """Error de un archivo que no se puede usar, con el motivo."""
    return ErrorPersistencia(
        "El archivo '%s' está dañado o incompleto: %s." % (ruta.name, motivo)
    )


def _apartado(datos, clave, tipo, ruta):
    """datos[clave], comprobando que existe y, si se indica, su tipo."""
    if clave not in datos:
        raise _archivo_danado(ruta, "falta '%s'" % clave)
    valor = datos[clave]
    if tipo is not None and not isinstance(valor, tipo):
        raise _archivo_danado(ruta, "'%s' no tiene el tipo esperado" % clave)
    return valor


def _metricas_desde_diccionario(metricas, ruta):
    """Métricas del archivo con la forma de ``metricas_modelo``.

    ``null`` pasa a NaN, que es como se representa una métrica que no se
    pudo calcular.
    """
    resultado = {}
    for conjunto in CONJUNTOS:
        valores = metricas.get(conjunto)
        if not isinstance(valores, dict):
            raise _archivo_danado(
                ruta, "faltan las métricas del conjunto de %s" % conjunto
            )
        resultado[conjunto] = {}
        for nombre in NOMBRES_METRICAS:
            if nombre not in valores:
                raise _archivo_danado(
                    ruta,
                    "falta la métrica %s del conjunto de %s"
                    % (nombre, conjunto),
                )
            valor = valores[nombre]
            if valor is None:
                resultado[conjunto][nombre] = math.nan
            elif _es_numero_finito(valor):
                resultado[conjunto][nombre] = float(valor)
            else:
                raise _archivo_danado(
                    ruta,
                    "la métrica %s del conjunto de %s no es un número"
                    % (nombre, conjunto),
                )
    return resultado


def _metricas_a_diccionario(metricas):
    """Copia R² y ECM de cada conjunto; NaN e infinito pasan a ``None``."""
    if not isinstance(metricas, dict):
        raise ErrorPersistencia("Faltan las métricas del modelo.")
    resultado = {}
    for conjunto in CONJUNTOS:
        valores = metricas.get(conjunto)
        if not isinstance(valores, dict):
            raise ErrorPersistencia(
                "Faltan las métricas del conjunto de %s." % conjunto
            )
        resultado[conjunto] = {}
        for nombre in NOMBRES_METRICAS:
            if nombre not in valores:
                raise ErrorPersistencia(
                    "Falta la métrica %s del conjunto de %s."
                    % (nombre, conjunto)
                )
            resultado[conjunto][nombre] = _metrica_a_json(valores[nombre])
    return resultado


def _metrica_a_json(valor):
    """NaN o infinito no son JSON válido: se guardan como ``None``."""
    if valor is None:
        return None
    if not _es_numero(valor):
        raise ErrorPersistencia("Una métrica del modelo no es un número.")
    numero = float(valor)
    if not math.isfinite(numero):
        return None
    return numero


def _es_numero(valor):
    """True si valor es un número real: int, float o los de numpy.

    Se rechazan los bool (True no es una métrica ni un coeficiente) y los
    textos, aunque parezcan números ("2"): float("2") funcionaría, pero
    el modelo tendría un coeficiente que no es un número.
    """
    if isinstance(valor, bool):
        return False
    return isinstance(valor, numbers.Real)


def _es_numero_finito(valor):
    """True si valor es un número real (no bool) finito."""
    if not _es_numero(valor):
        return False
    return math.isfinite(float(valor))


def _escribir_reemplazando(ruta, texto):
    """Escribe en un temporal de la misma carpeta y lo mueve a ruta."""
    descriptor, temporal = tempfile.mkstemp(
        prefix="." + ruta.name + ".", suffix=".tmp", dir=ruta.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            archivo.write(texto)
            archivo.flush()
            os.fsync(archivo.fileno())
        os.chmod(temporal, _permisos_archivo(ruta))
        os.replace(temporal, ruta)
    except BaseException:
        try:
            os.remove(temporal)
        except OSError:
            pass
        raise


def _permisos_archivo(ruta):
    """Permisos del archivo guardado.

    mkstemp crea el temporal solo legible por su dueño (0600). Si se
    sobrescribe un archivo se conservan sus permisos; si es nuevo, se usan
    los de cualquier archivo nuevo (0666 menos la umask).
    """
    if ruta.exists():
        return ruta.stat().st_mode & 0o777
    umask = os.umask(0)
    os.umask(umask)
    return 0o666 & ~umask


def _mensaje_error_escritura(ruta, error):
    """Mensaje claro para el usuario según el tipo de error del sistema."""
    if isinstance(error, FileNotFoundError):
        return "No se puede guardar el modelo: no existe la carpeta '%s'." % (
            ruta.parent
        )
    if isinstance(error, PermissionError):
        return (
            "No se puede guardar el modelo: no tienes permiso para escribir "
            "en '%s'." % ruta.parent
        )
    if isinstance(error, NotADirectoryError):
        return (
            "No se puede guardar el modelo: '%s' no es una carpeta válida."
            % ruta.parent
        )
    detalle = error.strerror
    if not detalle:
        detalle = str(error)
    return "No se pudo guardar el modelo en '%s': %s." % (ruta, detalle)
