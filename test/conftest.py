"""Utilidades compartidas por test_entrada.py y test_salida.py.

Cargan el archivo ``src/sikorius/datos_entrada_salida.py`` con
``importlib`` (se mantiene así desde que el archivo tenía guiones en el
nombre). Se usan los elementos reales de NiceGUI sin arrancar el
servidor.

pytest carga este archivo solo; los fixtures (``datos``, ``pagina``,
``pagina_con_datos``) están disponibles en los dos archivos de tests.
"""

import asyncio
import importlib.util
import inspect
import sqlite3
from pathlib import Path

import pandas as pd
import pytest
from nicegui import ui

RUTA_MODULO = (Path(__file__).resolve().parent.parent
               / "src" / "sikorius" / "datos_entrada_salida.py")


def _cargar_modulo():
    spec = importlib.util.spec_from_file_location(
        "datos_entrada_y_salida", RUTA_MODULO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


modulo = _cargar_modulo()

COLUMNAS = ["superficie", "habitaciones", "barrio", "precio"]


@pytest.fixture
def datos():
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
    return [e for e in selector._event_listeners.values()
            if e.type in ("popup-show", "popupShow")]


def desplegar(selector):
    """Simula que el usuario despliega el selector (llama a al_abrir)."""
    manejador = oyentes_al_desplegar(selector)[-1].handler
    if inspect.signature(manejador).parameters:
        manejador(None)
    else:
        manejador()


class Pagina:
    """Construye la página y guarda lo necesario para manejarla."""

    def __init__(self, monkeypatch):
        self.avisos = []
        self.botones = {}
        self.subida = None
        self.radio = None
        self.selects = []

        reales = {n: getattr(ui, n) for n in ("button", "upload", "radio",
                                               "select")}

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
        monkeypatch.setattr(ui, "notify",
                            lambda m, **kw: self.avisos.append((m, kw)))
        monkeypatch.setattr(ui.upload, "reset", lambda self_: None,
                            raising=False)
        modulo.pagina_principal()

    # Los selectores se recrean: el vigente es el último de cada etiqueta
    def _ultimo(self, prefijo):
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
