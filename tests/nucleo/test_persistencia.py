"""Tests del guardado del modelo en archivo JSON (#21, tarea #138).

uv run pytest tests/nucleo/test_persistencia.py -v
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

from sikorius.nucleo.errores import ErrorPersistencia, ErrorSikorius
from sikorius.nucleo.modelo import (
    ModeloLineal,
    entrenar_modelo,
    formula_texto,
    metricas_modelo,
)
from sikorius.nucleo.persistencia import (
    EXTENSION,
    FORMATO,
    VERSION_FORMATO,
    guardar_modelo,
    modelo_a_diccionario,
    ruta_con_extension,
)

# =============================================================================
# Utilidades
# =============================================================================

# Valores que no aparecen en ningún otro sitio del modelo: si alguno
# acaba en el archivo, es que se han guardado los datos.
VALORES_DATASET = (101.25, 202.5, 303.75, 404.125, 505.0625, 606.03125)


def datos_entrenamiento():
    """y = 2*x1 - 3*x2 + 5 con un poco de ruido determinista."""
    rng = np.random.default_rng(0)
    x1 = rng.uniform(0, 10, 30)
    x2 = rng.uniform(0, 10, 30)
    ruido = rng.normal(0, 0.5, 30)
    return pd.DataFrame({"x1": x1, "x2": x2, "y": 2 * x1 - 3 * x2 + 5 + ruido})


def datos_test():
    """Test con valores reconocibles para buscarlos en el archivo."""
    return pd.DataFrame(
        {
            "x1": [VALORES_DATASET[0], VALORES_DATASET[1]],
            "x2": [VALORES_DATASET[2], VALORES_DATASET[3]],
            "y": [VALORES_DATASET[4], VALORES_DATASET[5]],
        }
    )


@pytest.fixture
def entrenado():
    """(modelo, métricas, entrenamiento, test) con descripción."""
    entrenamiento = datos_entrenamiento()
    test = datos_test()
    modelo = entrenar_modelo(entrenamiento, ["x1", "x2"], "y")
    modelo.descripcion = "Predice y a partir de x1 y x2."
    metricas = metricas_modelo(modelo, entrenamiento, test)
    return modelo, metricas, entrenamiento, test


def leer_json(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)


def metricas_fijas():
    return {
        "entrenamiento": {"r2": 0.9, "ecm": 1.5},
        "test": {"r2": 0.8, "ecm": 2.5},
    }


# =============================================================================
# Información guardada
# =============================================================================


def test_guarda_toda_la_informacion(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    ruta = guardar_modelo(modelo, metricas, tmp_path / "modelo.json")
    datos = leer_json(ruta)

    assert datos["formato"] == FORMATO
    assert datos["version_formato"] == VERSION_FORMATO
    assert datos["descripcion"] == "Predice y a partir de x1 y x2."
    assert datos["formula"] == formula_texto(modelo)
    assert datos["modelo"] == {
        "features": ["x1", "x2"],
        "target": "y",
        "coeficientes": list(modelo.coeficientes),
        "termino_independiente": modelo.termino_independiente,
    }
    assert datos["metricas"] == metricas


def test_estructura_exacta_de_la_historia_20(entrenado, tmp_path):
    """Sin campos de más ni de menos respecto al formato documentado."""
    modelo, metricas, _, _ = entrenado
    datos = leer_json(guardar_modelo(modelo, metricas, tmp_path / "m.json"))
    assert set(datos) == {
        "formato",
        "version_formato",
        "descripcion",
        "formula",
        "modelo",
        "metricas",
    }
    assert set(datos["modelo"]) == {
        "features",
        "target",
        "coeficientes",
        "termino_independiente",
    }
    assert set(datos["metricas"]) == {"entrenamiento", "test"}
    for conjunto in ("entrenamiento", "test"):
        assert set(datos["metricas"][conjunto]) == {"r2", "ecm"}


def test_coeficientes_sin_perdida_de_precision(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    datos = leer_json(guardar_modelo(modelo, metricas, tmp_path / "m.json"))
    assert tuple(datos["modelo"]["coeficientes"]) == modelo.coeficientes
    assert (
        datos["modelo"]["termino_independiente"]
        == modelo.termino_independiente
    )


def test_con_lo_guardado_se_predice_igual(entrenado, tmp_path):
    """El archivo basta para predecir sin el dataset original."""
    modelo, metricas, _, test = entrenado
    datos = leer_json(guardar_modelo(modelo, metricas, tmp_path / "m.json"))
    reconstruido = ModeloLineal(**datos["modelo"])
    assert np.array_equal(reconstruido.predecir(test), modelo.predecir(test))


def test_descripcion_vacia(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    modelo.descripcion = ""
    datos = leer_json(guardar_modelo(modelo, metricas, tmp_path / "m.json"))
    assert datos["descripcion"] == ""


def test_descripcion_none_se_guarda_vacia(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    modelo.descripcion = None
    datos = leer_json(guardar_modelo(modelo, metricas, tmp_path / "m.json"))
    assert datos["descripcion"] == ""


def test_descripcion_con_tildes_saltos_y_comillas(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    modelo.descripcion = 'Año 2026: "pequeño" modelo.\nSegunda línea, ñ.'
    ruta = guardar_modelo(modelo, metricas, tmp_path / "m.json")
    assert leer_json(ruta)["descripcion"] == modelo.descripcion
    # ensure_ascii=False: las tildes se ven tal cual en el archivo
    assert "pequeño" in ruta.read_text(encoding="utf-8")


def test_regresion_simple(tmp_path):
    entrenamiento = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [3.0, 5.0, 7.0]})
    modelo = entrenar_modelo(entrenamiento, ["x"], "y")
    metricas = metricas_modelo(modelo, entrenamiento, entrenamiento)
    datos = leer_json(guardar_modelo(modelo, metricas, tmp_path / "m.json"))
    assert datos["modelo"]["features"] == ["x"]
    assert datos["formula"] == "y = 2.0000 * x + 1.0000"


def test_columnas_con_nombres_raros(tmp_path):
    entrenamiento = pd.DataFrame(
        {"tamaño (m²)": [1.0, 2.0, 3.0], "precio €": [3.0, 5.0, 7.0]}
    )
    modelo = entrenar_modelo(entrenamiento, ["tamaño (m²)"], "precio €")
    metricas = metricas_modelo(modelo, entrenamiento, entrenamiento)
    datos = leer_json(guardar_modelo(modelo, metricas, tmp_path / "m.json"))
    assert datos["modelo"]["features"] == ["tamaño (m²)"]
    assert datos["modelo"]["target"] == "precio €"


@pytest.mark.parametrize(
    "valor", [float("nan"), float("inf"), float("-inf"), np.nan]
)
def test_metricas_no_finitas_se_guardan_como_null(entrenado, tmp_path, valor):
    """R² vale NaN si el test tiene la salida constante, por ejemplo."""
    modelo, _, _, _ = entrenado
    metricas = metricas_fijas()
    metricas["test"]["r2"] = valor
    ruta = guardar_modelo(modelo, metricas, tmp_path / "m.json")
    texto = ruta.read_text(encoding="utf-8")
    assert "NaN" not in texto
    assert "Infinity" not in texto
    assert leer_json(ruta)["metricas"]["test"]["r2"] is None


def test_metrica_none_se_guarda_como_null(entrenado, tmp_path):
    modelo, _, _, _ = entrenado
    metricas = metricas_fijas()
    metricas["entrenamiento"]["ecm"] = None
    datos = leer_json(guardar_modelo(modelo, metricas, tmp_path / "m.json"))
    assert datos["metricas"]["entrenamiento"]["ecm"] is None


def test_metricas_de_numpy_se_guardan_como_float(entrenado, tmp_path):
    modelo, _, _, _ = entrenado
    metricas = {
        "entrenamiento": {"r2": np.float64(0.5), "ecm": np.float32(2.0)},
        "test": {"r2": np.float64(0.25), "ecm": np.int64(3)},
    }
    datos = leer_json(guardar_modelo(modelo, metricas, tmp_path / "m.json"))
    assert datos["metricas"] == {
        "entrenamiento": {"r2": 0.5, "ecm": 2.0},
        "test": {"r2": 0.25, "ecm": 3.0},
    }


def test_ignora_metricas_de_mas(entrenado, tmp_path):
    modelo, _, _, _ = entrenado
    metricas = metricas_fijas()
    metricas["test"]["otra"] = 7.0
    metricas["validacion"] = {"r2": 1.0, "ecm": 0.0}
    datos = leer_json(guardar_modelo(modelo, metricas, tmp_path / "m.json"))
    assert datos["metricas"] == metricas_fijas()


# =============================================================================
# Información no guardada
# =============================================================================


def test_no_guarda_los_datos(entrenado, tmp_path):
    modelo, metricas, entrenamiento, test = entrenado
    ruta = guardar_modelo(modelo, metricas, tmp_path / "m.json")
    texto = ruta.read_text(encoding="utf-8")
    for valor in VALORES_DATASET:
        assert repr(valor) not in texto
    for valor in entrenamiento.to_numpy().ravel():
        assert repr(float(valor)) not in texto
    # Ningún campo puede contener tantos números como filas hay
    for valor in _valores_hoja(leer_json(ruta)):
        assert not isinstance(valor, list) or len(valor) <= 2


def _valores_hoja(datos):
    """Recorre todos los valores (y listas) del JSON."""
    if isinstance(datos, dict):
        for valor in datos.values():
            yield from _valores_hoja(valor)
    else:
        yield datos


def test_no_guarda_graficos(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    ruta = guardar_modelo(modelo, metricas, tmp_path / "m.json")
    texto = ruta.read_text(encoding="utf-8").lower()
    for palabra in ("png", "svg", "base64", "grafico", "figura", "recta"):
        assert palabra not in texto


def test_archivo_pequeno(entrenado, tmp_path):
    """Con 30 filas de entrenamiento el archivo no crece con los datos."""
    modelo, metricas, _, _ = entrenado
    ruta = guardar_modelo(modelo, metricas, tmp_path / "m.json")
    assert ruta.stat().st_size < 1000


def test_no_modifica_modelo_ni_metricas(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    antes = (
        modelo.features,
        modelo.target,
        modelo.coeficientes,
        modelo.termino_independiente,
        modelo.descripcion,
    )
    metricas_antes = json.dumps(metricas)
    guardar_modelo(modelo, metricas, tmp_path / "m.json")
    despues = (
        modelo.features,
        modelo.target,
        modelo.coeficientes,
        modelo.termino_independiente,
        modelo.descripcion,
    )
    assert despues == antes
    assert json.dumps(metricas) == metricas_antes


# =============================================================================
# Rutas
# =============================================================================


@pytest.mark.parametrize(
    "carpeta",
    ["con espacios", "canción", "año ñoño", "Mis modelos/sub carpeta"],
)
def test_rutas_con_espacios_tildes_y_enie(entrenado, tmp_path, carpeta):
    modelo, metricas, _, _ = entrenado
    destino = tmp_path / carpeta
    destino.mkdir(parents=True)
    ruta = guardar_modelo(modelo, metricas, destino / "Mi módelo ñ.json")
    assert ruta.exists()
    assert leer_json(ruta)["modelo"]["target"] == "y"


def test_acepta_ruta_como_texto(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    ruta = guardar_modelo(modelo, metricas, str(tmp_path / "m.json"))
    assert ruta == tmp_path / "m.json"
    assert ruta.exists()


def test_devuelve_ruta_absoluta(entrenado, tmp_path, monkeypatch):
    modelo, metricas, _, _ = entrenado
    monkeypatch.chdir(tmp_path)
    ruta = guardar_modelo(modelo, metricas, "relativo.json")
    assert ruta.is_absolute()
    assert ruta == tmp_path / "relativo.json"


def test_no_anade_extension_por_su_cuenta(entrenado, tmp_path):
    """Añadirla es cosa de ruta_con_extension, que usa el diálogo."""
    modelo, metricas, _, _ = entrenado
    ruta = guardar_modelo(modelo, metricas, tmp_path / "sin_extension")
    assert ruta.name == "sin_extension"
    assert leer_json(ruta)["formato"] == FORMATO


def test_sobrescribe_archivo_existente(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    ruta = tmp_path / "m.json"
    ruta.write_text("contenido viejo", encoding="utf-8")
    guardar_modelo(modelo, metricas, ruta)
    assert leer_json(ruta)["formato"] == FORMATO


def test_no_deja_temporales(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    guardar_modelo(modelo, metricas, tmp_path / "m.json")
    guardar_modelo(modelo, metricas, tmp_path / "m.json")
    assert [p.name for p in tmp_path.iterdir()] == ["m.json"]


@pytest.mark.skipif(sys.platform == "win32", reason="permisos POSIX")
def test_archivo_nuevo_con_permisos_normales(entrenado, tmp_path):
    """El temporal nace con 0600; el archivo final no debe quedarse así."""
    modelo, metricas, _, _ = entrenado
    umask = os.umask(0o022)
    try:
        ruta = guardar_modelo(modelo, metricas, tmp_path / "m.json")
    finally:
        os.umask(umask)
    assert ruta.stat().st_mode & 0o777 == 0o644


@pytest.mark.skipif(sys.platform == "win32", reason="permisos POSIX")
def test_sobrescribir_conserva_permisos(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    ruta = tmp_path / "m.json"
    ruta.write_text("{}", encoding="utf-8")
    ruta.chmod(0o640)
    guardar_modelo(modelo, metricas, ruta)
    assert ruta.stat().st_mode & 0o777 == 0o640


# =============================================================================
# ruta_con_extension
# =============================================================================


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("modelo", "modelo.json"),
        ("modelo.json", "modelo.json"),
        ("modelo.JSON", "modelo.JSON"),
        ("modelo.Json", "modelo.Json"),
        ("modelo.v2", "modelo.v2.json"),
        ("modelo.txt", "modelo.txt.json"),
        ("mi modelo ñ", "mi modelo ñ.json"),
        (".json", ".json.json"),
    ],
)
def test_ruta_con_extension(tmp_path, entrada, esperado):
    assert ruta_con_extension(tmp_path / entrada) == tmp_path / esperado


def test_ruta_con_extension_conserva_carpeta():
    resultado = ruta_con_extension("carpeta con espacios/canción/modelo")
    assert resultado.parent.name == "canción"
    assert resultado.name == "modelo" + EXTENSION


def test_ruta_con_extension_acepta_texto():
    assert ruta_con_extension("a/b") == ruta_con_extension(
        ruta_con_extension("a/b")
    )


# =============================================================================
# Errores
# =============================================================================


def test_error_es_de_sikorius():
    """La GUI muestra tal cual el mensaje de los ErrorSikorius."""
    assert issubclass(ErrorPersistencia, ErrorSikorius)


def test_carpeta_inexistente(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    ruta = tmp_path / "no_existe" / "m.json"
    with pytest.raises(ErrorPersistencia, match="no existe la carpeta"):
        guardar_modelo(modelo, metricas, ruta)
    assert not ruta.parent.exists()


def test_ruta_es_una_carpeta(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    with pytest.raises(ErrorPersistencia, match="es una carpeta"):
        guardar_modelo(modelo, metricas, tmp_path)


def test_padre_es_un_archivo(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    archivo = tmp_path / "archivo.txt"
    archivo.write_text("hola", encoding="utf-8")
    with pytest.raises(ErrorPersistencia):
        guardar_modelo(modelo, metricas, archivo / "m.json")


@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0,
    reason="root ignora los permisos de las carpetas",
)
def test_sin_permisos(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    carpeta = tmp_path / "bloqueada"
    carpeta.mkdir()
    carpeta.chmod(0o500)
    try:
        with pytest.raises(ErrorPersistencia, match="permiso"):
            guardar_modelo(modelo, metricas, carpeta / "m.json")
    finally:
        carpeta.chmod(0o700)
    assert list(carpeta.iterdir()) == []


def test_otro_error_del_sistema(entrenado, tmp_path, monkeypatch):
    """Por ejemplo, disco lleno: mensaje claro y nada a medias."""
    modelo, metricas, _, _ = entrenado

    def disco_lleno(*args, **kwargs):
        raise OSError(28, "No queda espacio en el dispositivo")

    monkeypatch.setattr(os, "fsync", disco_lleno)
    with pytest.raises(ErrorPersistencia, match="No queda espacio"):
        guardar_modelo(modelo, metricas, tmp_path / "m.json")
    assert list(tmp_path.iterdir()) == []


def test_error_no_estropea_archivo_existente(entrenado, tmp_path, monkeypatch):
    modelo, metricas, _, _ = entrenado
    ruta = tmp_path / "m.json"
    ruta.write_text('{"anterior": true}', encoding="utf-8")

    def falla(*args, **kwargs):
        raise OSError(5, "Error de entrada/salida")

    monkeypatch.setattr(os, "replace", falla)
    with pytest.raises(ErrorPersistencia):
        guardar_modelo(modelo, metricas, ruta)
    assert leer_json(ruta) == {"anterior": True}
    assert [p.name for p in tmp_path.iterdir()] == ["m.json"]


def test_tras_un_error_se_puede_reintentar(entrenado, tmp_path):
    modelo, metricas, _, _ = entrenado
    with pytest.raises(ErrorPersistencia):
        guardar_modelo(modelo, metricas, tmp_path / "no" / "m.json")
    ruta = guardar_modelo(modelo, metricas, tmp_path / "m.json")
    assert ruta.exists()


@pytest.mark.parametrize(
    "metricas",
    [
        None,
        {},
        {"entrenamiento": {"r2": 1.0, "ecm": 0.0}},
        {"entrenamiento": {"r2": 1.0}, "test": {"r2": 1.0, "ecm": 0.0}},
        {"entrenamiento": "mal", "test": {"r2": 1.0, "ecm": 0.0}},
        {"entrenamiento": {"r2": "x", "ecm": 0}, "test": {"r2": 1, "ecm": 0}},
        {"entrenamiento": {"r2": "1", "ecm": 0}, "test": {"r2": 1, "ecm": 0}},
        {"entrenamiento": {"r2": True, "ecm": 0}, "test": {"r2": 1, "ecm": 0}},
    ],
)
def test_metricas_no_validas(entrenado, tmp_path, metricas):
    modelo, _, _, _ = entrenado
    with pytest.raises(ErrorPersistencia):
        guardar_modelo(modelo, metricas, tmp_path / "m.json")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("coeficientes", "independiente"),
    [
        ((float("nan"), 1.0), 0.0),
        ((1.0, float("inf")), 0.0),
        ((1.0, 2.0), float("nan")),
        ((1.0, "2"), 0.0),
        ((1.0, True), 0.0),
        ((1.0,), 0.0),
    ],
)
def test_modelo_no_valido(tmp_path, coeficientes, independiente):
    modelo = ModeloLineal(("a", "b"), "y", coeficientes, independiente)
    with pytest.raises(ErrorPersistencia):
        guardar_modelo(modelo, metricas_fijas(), tmp_path / "m.json")
    assert list(tmp_path.iterdir()) == []


# =============================================================================
# modelo_a_diccionario
# =============================================================================


def test_diccionario_es_json_valido(entrenado):
    modelo, metricas, _, _ = entrenado
    datos = modelo_a_diccionario(modelo, metricas)
    texto = json.dumps(datos, allow_nan=False)
    assert json.loads(texto) == datos


def test_diccionario_usa_listas_y_floats(entrenado):
    modelo, metricas, _, _ = entrenado
    datos = modelo_a_diccionario(modelo, metricas)
    assert isinstance(datos["modelo"]["features"], list)
    assert isinstance(datos["modelo"]["coeficientes"], list)
    for valor in datos["modelo"]["coeficientes"]:
        assert type(valor) is float
    assert type(datos["modelo"]["termino_independiente"]) is float
