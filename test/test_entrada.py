"""Pruebas de la ENTRADA del modelo (columnas de entrada o features).

Prueba la parte de entrada de ``src/sikorius/datos_entrada_salida.py``:

- La estructura del archivo.
- ``SelectorFeatures``: elección de las columnas de entrada (simple o
  múltiple según el tipo de regresión).
- ``importar_archivo_subido``: guarda el archivo subido y lo importa.
- En ``pagina_principal``: subir el dataset, el tipo de regresión y la
  confirmación de las features.

Las utilidades (fixtures ``datos``, ``pagina`` y ``pagina_con_datos`` y los
falsos de ``ui.upload``) están al principio de este archivo. Antes estaban
en ``conftest.py`` y se compartían con test_salida.py; ahora cada archivo
lleva las suyas para no depender de conftest.

Los tests marcados con ``xfail(strict=True)`` documentan FALLOS REALES del
código actual: hoy fallan a propósito. Cuando se corrija el fallo, pytest
avisará con XPASS(strict) y habrá que quitar el marcador.

Ejecución:
    uv run pytest test/test_entrada.py -v
"""

import ast
import asyncio
import builtins
import inspect
import sqlite3
from pathlib import Path

import pandas as pd
import pytest
from nicegui import ui

import sikorius.datos_entrada_salida as modulo
from sikorius.importador import ErrorImportacion

# =============================================================================
# Utilidades (antes estaban en conftest.py; ahora cada archivo lleva las suyas)
# =============================================================================

RUTA_MODULO = Path(modulo.__file__)

COLUMNAS = ["superficie", "habitaciones", "barrio", "precio"]


@pytest.fixture
def datos():
    """Dataset pequeño con tres columnas numéricas y una de texto (barrio)."""
    return pd.DataFrame({
        "superficie": [60.0, 95.0, 110.0],
        "habitaciones": [2, 3, 4],
        "barrio": ["Elviña", "Os Mallos", "Riazor"],
        "precio": [121000, 189500, 265000],
    })


class ArchivoSubido:
    """Imita al archivo que entrega ui.upload en el evento."""

    def __init__(self, nombre, contenido=b"", fallo=None):
        self.name = nombre
        self.contenido = contenido
        self.fallo = fallo
        self.guardado_en = None

    async def save(self, ruta):
        self.guardado_en = Path(ruta)
        if self.fallo is not None:
            raise self.fallo
        Path(ruta).write_bytes(self.contenido)


class EventoSubida:
    """Imita al evento de ui.upload: solo hace falta el archivo."""

    def __init__(self, archivo):
        self.file = archivo


def bytes_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def bytes_xlsx(df, tmp_path):
    ruta = tmp_path / "origen.xlsx"
    df.to_excel(ruta, index=False)
    return ruta.read_bytes()


def bytes_sqlite(df, tmp_path):
    ruta = tmp_path / "origen.db"
    conexion = sqlite3.connect(ruta)
    df.to_sql("t", conexion, index=False)
    conexion.close()
    return ruta.read_bytes()


def ejecutar(corrutina):
    return asyncio.run(corrutina)


def oyentes_al_desplegar(selector):
    """Manejadores del evento de abrir el desplegable de un ui.select."""
    return [e for e in selector._event_listeners.values()
            if e.type in ("popup-show", "popupShow")]


def desplegar(selector):
    """Simula que el usuario abre el desplegable (lanza el último manejador)."""
    manejador = oyentes_al_desplegar(selector)[-1].handler
    if inspect.signature(manejador).parameters:
        manejador(None)
    else:
        manejador()


class Pagina:
    """Construye la página y guarda lo necesario para manejarla.

    Sustituye ui.button, ui.upload, ui.radio, ui.select y ui.notify por
    versiones que crean el elemento real pero se quedan con una referencia,
    para poder pulsar botones, subir archivos y leer los avisos sin servidor.
    """

    def __init__(self, monkeypatch):
        self.avisos = []
        self.botones = {}
        self.subida = None
        self.radio = None
        self.selects = []
        reales = {n: getattr(ui, n) for n in ("button", "upload", "radio", "select")}

        def button(texto, on_click=None, **kw):
            self.botones[texto] = on_click
            return reales["button"](texto, on_click=on_click, **kw)

        def upload(*a, on_upload=None, **kw):
            self.al_subir = on_upload
            self.subida = reales["upload"](*a, on_upload=on_upload, **kw)
            return self.subida

        def radio(*a, **kw):
            self.radio = reales["radio"](*a, **kw)
            return self.radio

        def select(*a, **kw):
            elemento = reales["select"](*a, **kw)
            self.selects.append(elemento)
            return elemento

        monkeypatch.setattr(ui, "button", button)
        monkeypatch.setattr(ui, "upload", upload)
        monkeypatch.setattr(ui, "radio", radio)
        monkeypatch.setattr(ui, "select", select)
        monkeypatch.setattr(ui, "notify", lambda m, **kw: self.avisos.append((m, kw)))
        monkeypatch.setattr(ui.upload, "reset", lambda self: None, raising=False)
        modulo.pagina_principal()

    def _ultimo(self, prefijo):
        """Último ui.select creado cuya etiqueta empieza por el prefijo."""
        return [s for s in self.selects
                if str(s.props.get("label", "")).startswith(prefijo)][-1]

    @property
    def features(self):
        return self._ultimo("Feature")

    @property
    def target(self):
        return self._ultimo("Target")

    def subir(self, nombre, contenido):
        self.avisos.clear()
        ejecutar(self.al_subir(EventoSubida(ArchivoSubido(nombre, contenido))))

    def abrir_target(self):
        desplegar(self.target)

    def confirmar(self):
        """Pulsa «Confirmar selección» y devuelve el único aviso mostrado."""
        self.avisos.clear()
        self.botones["Confirmar selección"]()
        assert len(self.avisos) == 1
        return self.avisos[0]


@pytest.fixture
def pagina(monkeypatch):
    return Pagina(monkeypatch)


@pytest.fixture
def pagina_con_datos(pagina, datos):
    pagina.subir("datos.csv", bytes_csv(datos))
    return pagina


SelectorFeatures = modulo.SelectorFeatures
SelectorTarget = modulo.SelectorTarget
importar_archivo_subido = modulo.importar_archivo_subido


# =============================================================================
# Estructura del archivo
# =============================================================================

def test_el_archivo_existe():
    assert RUTA_MODULO.is_file()


def test_el_archivo_compila():
    compile(RUTA_MODULO.read_text(encoding="utf-8"), str(RUTA_MODULO), "exec")


@pytest.mark.parametrize("nombre", [
    "SelectorFeatures", "SelectorTarget", "importar_archivo_subido",
    "pagina_principal", "EXTENSIONES_ADMITIDAS",
])
def test_existen_clases_y_funciones(nombre):
    assert hasattr(modulo, nombre)


def test_metodos_publicos():
    for metodo in ["cambiar_tipo_regresion", "cargar_columnas",
                   "obtener_seleccion"]:
        assert callable(getattr(SelectorFeatures, metodo, None)), metodo
        assert getattr(SelectorFeatures, metodo).__doc__, metodo


def test_constantes_de_tipo_de_regresion():
    assert SelectorFeatures.SIMPLE == "simple"
    assert SelectorFeatures.MULTIPLE == "multiple"


def test_importar_archivo_subido_es_asincrona():
    assert inspect.iscoroutinefunction(importar_archivo_subido)


def test_extensiones_admitidas_coinciden_con_el_importador(tmp_path):
    """Lo que deja subir el navegador lo tiene que aceptar el importador."""
    extensiones = modulo.EXTENSIONES_ADMITIDAS.split(",")
    assert extensiones == [".csv", ".xlsx", ".xls", ".sqlite", ".db"]
    for extension in extensiones:
        ruta = tmp_path / ("a" + extension)
        ruta.write_bytes(b"")
        with pytest.raises(ErrorImportacion) as info:
            modulo.importar_datos(ruta)
        assert "no soportada" not in str(info.value)


def test_usa_el_importador_y_la_validacion_del_proyecto():
    assert modulo.importar_datos.__module__ == "sikorius.importador"
    assert modulo.validar_seleccion.__module__ == "sikorius.validacion"


def test_no_lee_archivos_por_su_cuenta():
    codigo = RUTA_MODULO.read_text(encoding="utf-8")
    for prohibido in ("read_csv", "read_excel", "read_sql", "sqlite3", "print("):
        assert prohibido not in codigo, prohibido


def test_el_codigo_de_la_pagina_no_usa_variables_sin_definir():
    """Comprobación estática: toda variable usada dentro de la página está
    definida (ayuda a detectar errores de nombres al editar)."""
    arbol = ast.parse(RUTA_MODULO.read_text(encoding="utf-8"))
    pagina = next(n for n in arbol.body if isinstance(n, ast.FunctionDef)
                  and n.name == "pagina_principal")
    definidas = set(dir(modulo)) | set(dir(builtins)) | {
        n.id for n in ast.walk(pagina)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    definidas |= {n.name for n in ast.walk(pagina)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    definidas |= {a.arg for n in ast.walk(pagina) if isinstance(n, ast.arguments)
                  for a in n.args}
    definidas |= {n.name for n in ast.walk(pagina)
                  if isinstance(n, ast.ExceptHandler) and n.name}
    usadas = {n.id for n in ast.walk(pagina)
              if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    assert usadas <= definidas, usadas - definidas


# =============================================================================
# SelectorFeatures
# =============================================================================

def test_features_por_defecto_es_multiple_y_vacio():
    selector = SelectorFeatures()
    assert selector.tipo_regresion == SelectorFeatures.MULTIPLE
    assert selector.columnas == []
    assert selector.selector.props["multiple"] is True
    assert selector.selector.value == []
    assert selector.obtener_seleccion() == []


def test_features_vacio_esta_deshabilitado():
    assert not SelectorFeatures().selector.enabled


def test_features_multiple_usa_chips_y_etiqueta():
    selector = SelectorFeatures(SelectorFeatures.MULTIPLE)
    assert selector.selector.props.get("use-chips") is True
    assert selector.selector.props["label"] == "Features (selección múltiple)"


def test_features_simple():
    selector = SelectorFeatures(SelectorFeatures.SIMPLE)
    assert not selector.selector.props.get("multiple")
    assert not selector.selector.props.get("use-chips")
    assert selector.selector.value is None
    assert selector.selector.props["label"] == "Feature (selección simple)"
    assert selector.obtener_seleccion() == []


def test_features_se_puede_borrar_la_seleccion():
    assert SelectorFeatures().selector.props["clearable"] is True


def test_features_cargar_columnas(datos):
    selector = SelectorFeatures()
    selector.cargar_columnas(datos)
    assert selector.columnas == COLUMNAS
    assert selector.selector.options == COLUMNAS
    assert selector.selector.enabled


def test_features_cargar_dataset_sin_columnas_deshabilita(datos):
    selector = SelectorFeatures()
    selector.cargar_columnas(datos)
    selector.cargar_columnas(pd.DataFrame())
    assert selector.columnas == []
    assert not selector.selector.enabled


def test_features_nombres_de_columna_que_no_son_texto():
    selector = SelectorFeatures()
    selector.cargar_columnas(pd.DataFrame([[1, 2, 3]], columns=[2024, 1.5, "x"]))
    assert selector.columnas == ["2024", "1.5", "x"]


def test_features_cargar_no_modifica_el_dataframe(datos):
    copia = datos.copy()
    SelectorFeatures().cargar_columnas(datos)
    pd.testing.assert_frame_equal(datos, copia)


def test_features_seleccion_multiple(datos):
    selector = SelectorFeatures()
    selector.cargar_columnas(datos)
    selector.selector.set_value(["superficie", "habitaciones"])
    assert selector.obtener_seleccion() == ["superficie", "habitaciones"]


def test_features_seleccion_simple_devuelve_lista(datos):
    selector = SelectorFeatures(SelectorFeatures.SIMPLE)
    selector.cargar_columnas(datos)
    selector.selector.set_value("superficie")
    assert selector.obtener_seleccion() == ["superficie"]


def test_features_obtener_seleccion_devuelve_una_copia(datos):
    selector = SelectorFeatures()
    selector.cargar_columnas(datos)
    selector.selector.set_value(["superficie"])
    selector.obtener_seleccion().append("precio")
    assert selector.obtener_seleccion() == ["superficie"]


def test_features_borrar_la_seleccion(datos):
    selector = SelectorFeatures(SelectorFeatures.SIMPLE)
    selector.cargar_columnas(datos)
    selector.selector.set_value("superficie")
    selector.selector.set_value(None)
    assert selector.obtener_seleccion() == []


def test_features_cargar_otro_dataset_limpia_la_seleccion(datos):
    selector = SelectorFeatures()
    selector.cargar_columnas(datos)
    selector.selector.set_value(["superficie"])
    selector.cargar_columnas(pd.DataFrame({"x": [1], "y": [2]}))
    assert selector.selector.options == ["x", "y"]
    assert selector.obtener_seleccion() == []


def test_features_cargar_el_mismo_dataset_tambien_limpia(datos):
    selector = SelectorFeatures()
    selector.cargar_columnas(datos)
    selector.selector.set_value(["superficie"])
    selector.cargar_columnas(datos)
    assert selector.obtener_seleccion() == []


@pytest.mark.parametrize("de, a", [
    (SelectorFeatures.MULTIPLE, SelectorFeatures.SIMPLE),
    (SelectorFeatures.SIMPLE, SelectorFeatures.MULTIPLE),
])
def test_features_cambiar_tipo_limpia_y_conserva_columnas(datos, de, a):
    selector = SelectorFeatures(de)
    selector.cargar_columnas(datos)
    selector.selector.set_value(
        ["superficie"] if de == SelectorFeatures.MULTIPLE else "superficie")
    selector.cambiar_tipo_regresion(a)
    assert selector.tipo_regresion == a
    assert selector.selector.props.get("multiple", False) == (
        a == SelectorFeatures.MULTIPLE)
    assert selector.selector.options == COLUMNAS
    assert selector.selector.enabled
    assert selector.obtener_seleccion() == []


def test_features_cambiar_tipo_no_deja_selectores_viejos(datos):
    selector = SelectorFeatures()
    selector.cargar_columnas(datos)
    for _ in range(5):
        selector.cambiar_tipo_regresion(SelectorFeatures.SIMPLE)
        selector.cambiar_tipo_regresion(SelectorFeatures.MULTIPLE)
    hijos = list(selector.contenedor.default_slot.children)
    assert hijos == [selector.selector]


@pytest.mark.parametrize("tipo", ["", "Simple", "MULTIPLE", "lineal", None, 1])
def test_features_cambiar_a_tipo_no_valido(datos, tipo):
    selector = SelectorFeatures()
    selector.cargar_columnas(datos)
    selector.selector.set_value(["superficie"])
    with pytest.raises(ValueError, match="no válido"):
        selector.cambiar_tipo_regresion(tipo)
    # el error no cambia nada
    assert selector.tipo_regresion == SelectorFeatures.MULTIPLE
    assert selector.obtener_seleccion() == ["superficie"]


@pytest.mark.parametrize("tipo", ["raro", "Multiple", None])
def test_features_constructor_con_tipo_no_valido(tipo):
    with pytest.raises(ValueError):
        SelectorFeatures(tipo)


@pytest.mark.xfail(strict=True, reason=(
    "FALLO E2 (limitación conocida): columnas que solo se distinguen por el "
    "tipo del nombre (1 y '1') salen repetidas en el selector y no se "
    "pueden elegir por separado, porque todo se pasa a texto."))
def test_features_columnas_que_solo_difieren_en_el_tipo():
    selector = SelectorFeatures()
    selector.cargar_columnas(pd.DataFrame([[1, 2]], columns=[1, "1"]))
    assert len(set(selector.selector.options)) == 2


# =============================================================================
# importar_archivo_subido
# =============================================================================

@pytest.mark.parametrize("extension", [".csv", ".xlsx", ".sqlite", ".db"])
def test_subir_cada_formato(tmp_path, datos, extension):
    if extension == ".csv":
        contenido = bytes_csv(datos)
    elif extension == ".xlsx":
        contenido = bytes_xlsx(datos, tmp_path)
    else:
        contenido = bytes_sqlite(datos, tmp_path)
    archivo = ArchivoSubido("datos" + extension, contenido)
    df = ejecutar(importar_archivo_subido(archivo))
    assert df.columns.tolist() == COLUMNAS
    assert len(df) == 3


def test_subir_conserva_el_nombre_y_borra_el_temporal(datos):
    archivo = ArchivoSubido("mis datos.csv", bytes_csv(datos))
    ejecutar(importar_archivo_subido(archivo))
    assert archivo.guardado_en.name == "mis datos.csv"
    assert not archivo.guardado_en.exists()
    assert not archivo.guardado_en.parent.exists()


def test_subir_con_extension_en_mayusculas(datos):
    archivo = ArchivoSubido("DATOS.CSV", bytes_csv(datos))
    assert len(ejecutar(importar_archivo_subido(archivo))) == 3


@pytest.mark.parametrize("nombre", [
    "../../fuera.csv", "carpeta/sub/datos.csv", "C:/Windows/datos.csv",
    "..\\..\\fuera.csv",
])
def test_subir_nombre_con_ruta_no_sale_de_la_carpeta_temporal(datos, nombre):
    archivo = ArchivoSubido(nombre, bytes_csv(datos))
    ejecutar(importar_archivo_subido(archivo))
    assert archivo.guardado_en.name.endswith(".csv")
    assert ".." not in archivo.guardado_en.parts
    assert archivo.guardado_en.parent.name.startswith("tmp")


@pytest.mark.parametrize("nombre, contenido, mensaje", [
    ("vacio.csv", b"", "no contiene datos"),
    ("datos.txt", b"a,b\n1,2\n", "no soportada"),
    ("sin_extension", b"a,b\n1,2\n", "no soportada"),
    ("roto.xlsx", b"esto no es un excel", "dañado"),
    ("roto.db", b"basura" * 100, "dañado"),
    ("binario.csv", b"\x00\x01", "dañado"),
])
def test_subir_archivo_no_valido(nombre, contenido, mensaje):
    archivo = ArchivoSubido(nombre, contenido)
    with pytest.raises(ErrorImportacion, match=mensaje):
        ejecutar(importar_archivo_subido(archivo))
    assert not archivo.guardado_en.exists()


def test_subir_sqlite_sin_tablas(tmp_path):
    ruta = tmp_path / "v.db"
    sqlite3.connect(ruta).close()
    archivo = ArchivoSubido("v.db", ruta.read_bytes())
    with pytest.raises(ErrorImportacion, match="ninguna tabla"):
        ejecutar(importar_archivo_subido(archivo))


def test_subir_error_al_guardar_se_propaga():
    archivo = ArchivoSubido("a.csv", fallo=OSError("disco lleno"))
    with pytest.raises(OSError, match="disco lleno"):
        ejecutar(importar_archivo_subido(archivo))


# =============================================================================
# pagina_principal: subida del dataset y columnas de entrada
# =============================================================================

def test_pagina_elementos(pagina):
    assert "Confirmar selección" in pagina.botones
    assert pagina.radio.value == SelectorFeatures.MULTIPLE
    assert set(pagina.radio.options) == {"simple", "multiple"}
    assert pagina.subida.props["accept"] == modulo.EXTENSIONES_ADMITIDAS
    assert pagina.subida.props["auto-upload"] is True
    assert not pagina.features.enabled and not pagina.target.enabled


def test_subir_dataset_rellena_los_dos_selectores(pagina_con_datos):
    pagina = pagina_con_datos
    assert pagina.features.options == COLUMNAS
    assert pagina.target.options == COLUMNAS
    ((mensaje, kw),) = pagina.avisos
    assert mensaje == "Dataset cargado: 3 filas, 4 columnas"
    assert kw["type"] == "positive"


@pytest.mark.parametrize("nombre, contenido, mensaje", [
    ("vacio.csv", b"", "no contiene datos"),
    ("datos.txt", b"a\n1\n", "no soportada"),
    ("roto.xlsx", b"texto", "dañado"),
])
def test_subir_dataset_erroneo_avisa_y_conserva_lo_anterior(
        pagina_con_datos, nombre, contenido, mensaje):
    pagina = pagina_con_datos
    pagina.features.set_value(["superficie"])
    pagina.subir(nombre, contenido)
    ((texto, kw),) = pagina.avisos
    assert mensaje in texto and kw["type"] == "negative"
    assert pagina.features.options == COLUMNAS
    assert pagina.features.value == ["superficie"]


def test_subir_con_error_inesperado_avisa(pagina):
    pagina.avisos.clear()
    archivo = ArchivoSubido("a.csv", fallo=OSError("disco lleno"))
    ejecutar(pagina.al_subir(EventoSubida(archivo)))
    ((texto, kw),) = pagina.avisos
    assert texto.startswith("Error inesperado al importar")
    assert "disco lleno" in texto and kw["type"] == "negative"


def test_confirmar_sin_dataset(pagina):
    texto, kw = pagina.confirmar()
    assert texto == "Carga primero un dataset."
    assert kw["type"] == "negative"


def test_confirmar_sin_features(pagina_con_datos):
    pagina_con_datos.target.set_value("precio")
    texto, _ = pagina_con_datos.confirmar()
    assert "Falta seleccionar al menos una columna de entrada" in texto


def test_confirmar_seleccion_correcta_simple(pagina_con_datos):
    pagina = pagina_con_datos
    pagina.radio.set_value(SelectorFeatures.SIMPLE)
    pagina.features.set_value("superficie")
    pagina.target.set_value("precio")
    texto, kw = pagina.confirmar()
    assert kw["type"] == "positive"
    assert "Entrada: superficie | Salida: precio" in texto


def test_cambiar_tipo_limpia_las_features(pagina_con_datos):
    pagina = pagina_con_datos
    pagina.features.set_value(["superficie"])
    pagina.radio.set_value(SelectorFeatures.SIMPLE)
    assert pagina.features.value is None
    assert not pagina.features.props.get("multiple")
    pagina.radio.set_value(SelectorFeatures.MULTIPLE)
    assert pagina.features.value == []


def test_cambiar_tipo_reconstruye_el_selector_una_sola_vez(pagina_con_datos):
    pagina = pagina_con_datos
    antes = len(pagina.selects)
    pagina.radio.set_value(SelectorFeatures.SIMPLE)
    assert len(pagina.selects) - antes == 1
