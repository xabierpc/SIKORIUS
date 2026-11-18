"""Pruebas del panel del asistente, sin servidor y con una LLM falsa.

uv run pytest tests/gui/test_panel_asistente.py -v
"""

import asyncio

import pytest
from nicegui import ui

from sikorius.aplicacion.asistente import Asistente
from sikorius.dominio.asistente import RespuestaAsistente
from sikorius.dominio.errores import ErrorAsistente
from sikorius.dominio.transformaciones import Operacion
from sikorius.gui.pagina import construir_pagina
from sikorius.gui.paneles import panel_asistente
from sikorius.gui.paneles.panel_asistente import PanelAsistente

QUITAR_X2 = Operacion(
    tipo="eliminar_columna",
    columna="x2",
    operador=None,
    valor=None,
    nombre_nuevo=None,
)


class LLMFalsa:
    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.etapas = []

    async def responder(self, conversacion, contexto):
        self.etapas.append(contexto.splitlines()[0])
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


@pytest.fixture
def avisos(monkeypatch):
    lista = []

    def anotar(mensaje, **kw):
        lista.append((mensaje, kw.get("type")))

    monkeypatch.setattr(ui, "notify", anotar)
    return lista


@pytest.fixture
def con_datos(sesion, datos):
    sesion.cargar_dataset(datos, "datos.csv")
    return sesion


def crear_panel(sesion, *respuestas, etapa=None):
    asistente = Asistente(sesion, LLMFalsa(*respuestas), usar_groq=False)
    return PanelAsistente(sesion, asistente, etapa)


def test_sin_clave_avisa_y_no_deja_escribir(sesion):
    asistente = Asistente(sesion, usar_groq=False)
    panel = PanelAsistente(sesion, asistente)
    assert panel.aviso_sin_clave.visible
    assert not panel.entrada.enabled
    assert not panel.sugerencias.visible


def test_con_clave_ofrece_sugerencias(sesion):
    panel = crear_panel(sesion)
    assert not panel.aviso_sin_clave.visible
    assert panel.entrada.enabled
    assert panel.sugerencias.visible
    assert not panel.boton_deshacer.enabled
    assert not panel.tarjeta_propuesta.visible


def test_enviar_pinta_la_conversacion(con_datos, avisos):
    panel = crear_panel(
        con_datos,
        RespuestaAsistente(mensaje="Hay 10 filas", operaciones=[]),
        etapa=lambda: "Datos",
    )
    panel.entrada.set_value("¿cuántas filas?")
    asyncio.run(panel.enviar())
    assert panel.entrada.value == ""
    assert len(panel.chat.default_slot.children) == 2
    assert not panel.sugerencias.visible
    assert not panel.cargando.visible
    assert panel.asistente._cliente.etapas == [
        "El usuario está en la pestaña: Datos."
    ]
    assert avisos == []


def test_texto_vacio_no_hace_nada(sesion):
    panel = crear_panel(sesion)
    asyncio.run(panel.enviar())
    assert panel.asistente.mensajes == ()


def test_error_se_notifica(sesion, avisos):
    panel = crear_panel(sesion, ErrorAsistente("sin red"))
    asyncio.run(panel.enviar("hola"))
    assert avisos == [("sin red", "negative")]
    assert panel.entrada.enabled


def test_propuesta_aplicar_y_deshacer(con_datos, avisos):
    panel = crear_panel(
        con_datos,
        RespuestaAsistente(mensaje="Quito x2", operaciones=[QUITAR_X2]),
    )
    asyncio.run(panel.enviar("quita x2"))
    assert panel.tarjeta_propuesta.visible
    asyncio.run(panel.aplicar())
    assert list(con_datos.dataset.datos.columns) == ["x1", "y"]
    assert not panel.tarjeta_propuesta.visible
    assert panel.boton_deshacer.enabled
    asyncio.run(panel.deshacer())
    assert list(con_datos.dataset.datos.columns) == ["x1", "x2", "y"]
    assert [t for _, t in avisos] == ["positive", "positive"]


def test_descartar(con_datos):
    panel = crear_panel(
        con_datos,
        RespuestaAsistente(mensaje="Quito x2", operaciones=[QUITAR_X2]),
    )
    asyncio.run(panel.enviar("quita x2"))
    panel.descartar()
    assert not panel.tarjeta_propuesta.visible
    assert "x2" in con_datos.dataset.datos.columns


def test_modelo_sin_guardar_pide_confirmacion(sesion_separada, monkeypatch):
    sesion_separada.aplicar_preprocesado("eliminar")
    sesion_separada.crear_modelo()

    async def no(*args, **kwargs):
        return False

    monkeypatch.setattr(panel_asistente, "confirmar", no)
    panel = crear_panel(
        sesion_separada,
        RespuestaAsistente(mensaje="Quito x2", operaciones=[QUITAR_X2]),
    )
    asyncio.run(panel.enviar("quita x2"))
    asyncio.run(panel.aplicar())
    assert sesion_separada.modelo is not None  # no se ha aplicado
    assert panel.tarjeta_propuesta.visible


def test_borrar_conversacion(sesion):
    panel = crear_panel(
        sesion, RespuestaAsistente(mensaje="Hola", operaciones=[])
    )
    asyncio.run(panel.enviar("hola"))
    panel.borrar()
    assert panel.chat.default_slot.children == []
    assert panel.sugerencias.visible


def test_pagina_con_asistente(sesion_separada, monkeypatch):
    monkeypatch.setattr(ui, "notify", lambda *a, **k: None)
    asistente = Asistente(sesion_separada, usar_groq=False)
    construir_pagina(sesion_separada, asistente)
