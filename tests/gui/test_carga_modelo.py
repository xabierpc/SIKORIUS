"""Pruebas de la carga de un modelo desde la interfaz (#24), sin servidor.

El explorador y la confirmación se sustituyen por funciones que responden
solas: aquí se prueba qué se pregunta, qué se carga y qué se avisa.

uv run pytest tests/gui/test_carga_modelo.py -v
"""

import asyncio
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from nicegui import ui

from sikorius.gui.componentes import carga_modelo
from sikorius.gui.componentes.carga_modelo import (
    aceptar_perder_cambios,
    carpeta_inicial,
    tiene_cambios_sin_guardar,
)
from sikorius.nucleo.persistencia import EXTENSION
from sikorius.sesion import Sesion

# =============================================================================
# Utilidades
# =============================================================================


def datos_lineales(n=20):
    x1 = np.arange(n, dtype=float)
    x2 = (np.arange(n, dtype=float) * 7) % 11
    return pd.DataFrame({"x1": x1, "x2": x2, "y": 2 * x1 - 3 * x2 + 5})


def sesion_con_modelo(ruta_dataset="datos.csv"):
    """Sesión con un modelo creado y sin guardar."""
    df = datos_lineales()
    sesion = Sesion()
    sesion.cargar_dataset(df, ruta_dataset)
    sesion.guardar_seleccion(["x1", "x2"], "y")
    sesion.guardar_separacion(df.iloc[:15], df.iloc[15:], 20, 42)
    sesion.crear_modelo()
    return sesion


def guardar_un_modelo(ruta, descripcion="Guardado"):
    sesion = sesion_con_modelo()
    sesion.guardar_descripcion(descripcion)
    return sesion.guardar_modelo(ruta)


@pytest.fixture
def avisos(monkeypatch):
    """Recoge los ui.notify (mensaje, tipo) en lugar de mostrarlos."""
    lista = []

    def anotar(mensaje, **kw):
        lista.append((mensaje, kw.get("type")))

    monkeypatch.setattr(ui, "notify", anotar)
    return lista


@pytest.fixture
def explorador(monkeypatch):
    """El explorador devuelve ``explorador.ruta`` sin abrirse y anota con
    qué argumentos se le llamó."""

    class Explorador:
        ruta = None
        llamadas = []

    async def falso(carpeta, **kwargs):
        Explorador.llamadas.append((carpeta, kwargs))
        return Explorador.ruta

    Explorador.llamadas = []
    monkeypatch.setattr(carga_modelo, "seleccionar_archivo", falso)
    return Explorador


@pytest.fixture
def preguntas(monkeypatch):
    """La confirmación responde ``preguntas.respuesta`` y anota los
    mensajes."""

    class Preguntas:
        respuesta = True
        mensajes = []

    async def falsa(titulo, mensaje, texto_aceptar="Aceptar"):
        Preguntas.mensajes.append(mensaje)
        return Preguntas.respuesta

    Preguntas.mensajes = []
    monkeypatch.setattr(carga_modelo, "confirmar", falsa)
    return Preguntas


def cargar(sesion):
    return asyncio.run(carga_modelo.cargar_modelo(sesion))


# =============================================================================
# Cargar
# =============================================================================


def test_desde_el_inicio_carga_sin_preguntar(
    tmp_path, explorador, preguntas, avisos
):
    explorador.ruta = str(guardar_un_modelo(tmp_path / "m.json"))
    sesion = Sesion()

    assert cargar(sesion) is True

    assert sesion.modelo_cargado
    assert sesion.modelo.descripcion == "Guardado"
    assert preguntas.mensajes == []
    assert avisos == [
        (
            "Modelo cargado de " + str((tmp_path / "m.json").resolve()),
            "positive",
        )
    ]


def test_el_explorador_filtra_por_la_extension_del_modelo(
    tmp_path, explorador, preguntas, avisos
):
    explorador.ruta = None
    cargar(Sesion())
    _, opciones = explorador.llamadas[0]
    assert opciones["tipos"] == (EXTENSION,)
    assert opciones["admitido"](tmp_path / "modelo.json")
    assert opciones["admitido"](tmp_path / "MODELO.JSON")
    assert not opciones["admitido"](tmp_path / "datos.csv")
    assert "modelo" in opciones["titulo"]


def test_cerrar_el_explorador_no_cambia_nada(explorador, preguntas, avisos):
    sesion = sesion_con_modelo()
    modelo = sesion.modelo
    explorador.ruta = None

    assert cargar(sesion) is False

    assert sesion.modelo is modelo
    assert sesion.dataset is not None
    assert avisos == []


def test_archivo_no_valido_avisa_y_conserva_el_estado(
    tmp_path, explorador, preguntas, avisos
):
    sesion = sesion_con_modelo()
    modelo = sesion.modelo
    malo = tmp_path / "malo.json"
    malo.write_text("{roto", encoding="utf-8")
    explorador.ruta = str(malo)

    assert cargar(sesion) is False

    assert sesion.modelo is modelo
    assert not sesion.modelo_cargado
    assert len(avisos) == 1
    assert avisos[0][1] == "negative"
    assert "malo.json" in avisos[0][0]


def test_tras_un_error_se_puede_cargar_otro(
    tmp_path, explorador, preguntas, avisos
):
    sesion = Sesion()
    malo = tmp_path / "malo.json"
    malo.write_text("[]", encoding="utf-8")
    explorador.ruta = str(malo)
    cargar(sesion)

    explorador.ruta = str(guardar_un_modelo(tmp_path / "bueno.json"))
    assert cargar(sesion) is True
    assert avisos[-1][1] == "positive"


@pytest.mark.parametrize("carpeta", ["con espacios", "canción ñandú"])
def test_rutas_con_espacios_tildes_y_enie(
    tmp_path, explorador, preguntas, avisos, carpeta
):
    destino = tmp_path / carpeta
    destino.mkdir()
    explorador.ruta = str(guardar_un_modelo(destino / "año.json"))
    sesion = Sesion()
    assert cargar(sesion) is True
    assert sesion.ruta_modelo == str((destino / "año.json").resolve())


# =============================================================================
# Confirmación de cambios sin guardar
# =============================================================================


def test_modelo_creado_sin_guardar_pregunta(
    tmp_path, explorador, preguntas, avisos
):
    sesion = sesion_con_modelo()
    explorador.ruta = str(guardar_un_modelo(tmp_path / "m.json"))

    cargar(sesion)

    assert len(preguntas.mensajes) == 1
    assert "cambios sin guardar" in preguntas.mensajes[0]
    assert sesion.modelo_cargado


def test_si_no_confirma_no_abre_el_explorador(
    tmp_path, explorador, preguntas, avisos
):
    sesion = sesion_con_modelo()
    modelo = sesion.modelo
    preguntas.respuesta = False

    assert cargar(sesion) is False

    assert explorador.llamadas == []
    assert sesion.modelo is modelo
    assert avisos == []


def test_modelo_guardado_sin_cambios_no_pregunta(
    tmp_path, explorador, preguntas, avisos
):
    sesion = sesion_con_modelo()
    sesion.guardar_modelo(tmp_path / "creado.json")
    explorador.ruta = str(guardar_un_modelo(tmp_path / "m.json"))

    cargar(sesion)

    assert preguntas.mensajes == []


def test_modelo_cargado_con_la_descripcion_cambiada_pregunta(
    tmp_path, explorador, preguntas, avisos
):
    ruta = guardar_un_modelo(tmp_path / "m.json")
    sesion = Sesion()
    sesion.cargar_modelo(ruta)
    sesion.guardar_descripcion("Cambiada")
    explorador.ruta = str(ruta)

    cargar(sesion)

    assert len(preguntas.mensajes) == 1
    assert sesion.modelo.descripcion == "Guardado"


def test_tiene_cambios_sin_guardar(tmp_path):
    assert not tiene_cambios_sin_guardar(Sesion())
    sesion = sesion_con_modelo()
    assert tiene_cambios_sin_guardar(sesion)
    sesion.guardar_modelo(tmp_path / "m.json")
    assert not tiene_cambios_sin_guardar(sesion)


def test_aceptar_perder_cambios_dice_que_se_va_a_hacer(preguntas):
    sesion = sesion_con_modelo()
    preguntas.respuesta = False
    respuesta = asyncio.run(aceptar_perder_cambios(sesion, "haces algo"))
    assert respuesta is False
    assert "Si haces algo, se perderán" in preguntas.mensajes[0]


# =============================================================================
# Carpeta inicial del explorador
# =============================================================================


def test_carpeta_inicial_sin_nada_es_la_personal():
    assert carpeta_inicial(Sesion()) == Path.home()


def test_carpeta_inicial_junto_al_dataset(tmp_path):
    sesion = sesion_con_modelo(tmp_path / "datos.csv")
    assert carpeta_inicial(sesion) == tmp_path.resolve()


def test_carpeta_inicial_la_del_modelo_guardado(tmp_path):
    carpeta = tmp_path / "modelos"
    carpeta.mkdir()
    sesion = sesion_con_modelo(tmp_path / "datos.csv")
    sesion.guardar_modelo(carpeta / "m.json")
    assert carpeta_inicial(sesion) == carpeta.resolve()
