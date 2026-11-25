"""Tests del agente con un LLM y un navegador falsos.

No necesitan red, clave de Groq, Playwright ni la aplicación en marcha.
"""

from pathlib import Path

import pytest

from probador_llm import agente
from probador_llm.agente import (
    BLOQUEADO,
    CORRECTO,
    FALLIDO,
    REVISAR,
    ejecutar_caso,
    normalizar,
)
from probador_llm.cliente_groq import Llamada, Respuesta
from probador_llm.navegador import ErrorAccion
from probador_llm.plan import Caso


class NavegadorFalso:
    """Imita al Navegador: una pantalla de texto y un botón."""

    def __init__(self):
        self.mensajes = []
        self.textos_vistos = []
        self.acciones = []
        self.capturas = 0
        self.pantalla = 'PANTALLA:\n- button "Crear modelo"'

    def observar(self):
        self.textos_vistos.append(self.pantalla)
        return self.pantalla

    def capturar(self, nombre):
        self.capturas += 1

    def pulsar(self, texto):
        self.acciones.append(("pulsar", texto))
        if texto != "Crear modelo":
            raise ErrorAccion('No hay ningún elemento "' + texto + '"')
        self.mensajes.append("ÉXITO: Modelo creado correctamente.")
        self.pantalla = "PANTALLA:\n- text: y = 2.0000 · x1 − 3.0000 · x2"
        return 'Pulsado "' + texto + '".'

    def escribir(self, campo, valor):
        self.acciones.append(("escribir", campo, valor))
        return "Escrito."


class ClienteGuion:
    """LLM falso que devuelve llamadas preparadas, una lista por turno."""

    def __init__(self, turnos):
        self.turnos = list(turnos)
        self.conversaciones = []

    def responder(self, mensajes, herramientas):
        copia = []
        for mensaje in mensajes:
            copia.append(dict(mensaje))
        self.conversaciones.append(copia)
        if self.turnos:
            llamadas = self.turnos.pop(0)
        else:
            llamadas = []
        mensaje = {"role": "assistant", "content": ""}
        return Respuesta(mensaje=mensaje, llamadas=llamadas, tokens=10)


def llamada(nombre, identificador="1", **argumentos):
    return Llamada(identificador, nombre, argumentos)


def terminar(estado, evidencias, identificador="9"):
    return llamada(
        "terminar",
        identificador,
        estado=estado,
        resultado_obtenido="Se ve la fórmula.",
        evidencias=evidencias,
    )


@pytest.fixture
def caso():
    return Caso(id="CP-47", titulo="Modelo exacto", texto="#### CP-47 ...")


def ejecutar(cliente, navegador, caso, preparacion=(), turnos=10):
    return ejecutar_caso(
        cliente,
        navegador,
        lambda: None,
        caso,
        list(preparacion),
        "contexto",
        Path("/proyecto"),
        max_turnos=turnos,
    )


def test_caso_correcto_con_evidencias_reales(caso):
    navegador = NavegadorFalso()
    cliente = ClienteGuion(
        [
            [llamada("pulsar", texto="Crear modelo")],
            [
                terminar(
                    "correcto",
                    [
                        "y = 2.0000 · x1 − 3.0000 · x2",
                        "Modelo creado correctamente.",
                    ],
                )
            ],
        ]
    )
    resultado = ejecutar(cliente, navegador, caso)
    assert resultado.estado == CORRECTO
    assert resultado.evidencias_no_encontradas == []
    assert navegador.acciones == [("pulsar", "Crear modelo")]
    assert len(resultado.pasos) == 1
    assert resultado.turnos == 2
    assert resultado.tokens == 20
    assert resultado.mensajes == ["ÉXITO: Modelo creado correctamente."]


def test_evidencia_inventada_queda_para_revisar(caso):
    cliente = ClienteGuion(
        [[terminar("correcto", ["R²: 1", "texto que nunca se vio"])]]
    )
    resultado = ejecutar(cliente, NavegadorFalso(), caso)
    assert resultado.estado == REVISAR
    assert resultado.estado_agente == "correcto"
    assert resultado.evidencias_no_encontradas == [
        "R²: 1",
        "texto que nunca se vio",
    ]


def test_sin_evidencias_queda_para_revisar(caso):
    cliente = ClienteGuion([[terminar("correcto", [])]])
    assert ejecutar(cliente, NavegadorFalso(), caso).estado == REVISAR


def test_fallido_con_evidencias(caso):
    cliente = ClienteGuion([[terminar("fallido", ["Crear modelo"])]])
    assert ejecutar(cliente, NavegadorFalso(), caso).estado == FALLIDO


def test_bloqueado_con_paso(caso):
    terminar_bloqueado = llamada(
        "terminar",
        estado="bloqueado",
        resultado_obtenido="No existe el botón Abrir",
        evidencias=[],
        paso_bloqueado=3,
    )
    resultado = ejecutar(
        ClienteGuion([[terminar_bloqueado]]), NavegadorFalso(), caso
    )
    assert resultado.estado == BLOQUEADO
    assert resultado.paso_bloqueado == 3


def test_estado_no_valido_queda_para_revisar(caso):
    cliente = ClienteGuion([[terminar("quizas", ["Crear modelo"])]])
    assert ejecutar(cliente, NavegadorFalso(), caso).estado == REVISAR


def test_sin_terminar_en_los_turnos_queda_bloqueado(caso):
    cliente = ClienteGuion([[llamada("escribir", campo="a", valor="1")]] * 5)
    resultado = ejecutar(cliente, NavegadorFalso(), caso, turnos=3)
    assert resultado.estado == BLOQUEADO
    assert "3 turnos" in resultado.resultado_obtenido
    assert resultado.turnos == 3


def test_error_de_accion_se_devuelve_al_agente(caso):
    cliente = ClienteGuion(
        [
            [llamada("pulsar", texto="Abrir")],
            [terminar("bloqueado", [])],
        ]
    )
    ejecutar(cliente, NavegadorFalso(), caso)
    ultimo = cliente.conversaciones[1][-1]
    assert ultimo["role"] == "tool"
    assert ultimo["content"].startswith("ERROR: No hay ningún elemento")
    # Tras la acción se le enseña la pantalla
    assert "PANTALLA:" in ultimo["content"]


def test_llamada_con_argumentos_mal_formados(caso):
    mala = Llamada("1", "pulsar", {}, "los argumentos no son JSON válido")
    cliente = ClienteGuion([[mala], [terminar("bloqueado", [])]])
    ejecutar(cliente, NavegadorFalso(), caso)
    assert "JSON" in cliente.conversaciones[1][-1]["content"]


def test_herramienta_desconocida(caso):
    cliente = ClienteGuion(
        [[llamada("borrar_todo")], [terminar("bloqueado", [])]]
    )
    ejecutar(cliente, NavegadorFalso(), caso)
    assert (
        "no existe la herramienta" in cliente.conversaciones[1][-1]["content"]
    )


def test_sin_llamadas_se_le_pide_una_herramienta(caso):
    cliente = ClienteGuion([[], [terminar("bloqueado", [])]])
    ejecutar(cliente, NavegadorFalso(), caso)
    assert "Usa una herramienta" in cliente.conversaciones[1][-1]["content"]


def test_cada_llamada_recibe_su_respuesta(caso):
    cliente = ClienteGuion(
        [
            [
                llamada("escribir", "a", campo="x1", valor="1"),
                llamada("escribir", "b", campo="x2", valor="2"),
            ],
            [terminar("bloqueado", [])],
        ]
    )
    ejecutar(cliente, NavegadorFalso(), caso)
    respuestas = []
    for mensaje in cliente.conversaciones[1]:
        if mensaje["role"] == "tool":
            respuestas.append(mensaje)
    assert respuestas[0]["tool_call_id"] == "a"
    assert respuestas[1]["tool_call_id"] == "b"
    # Solo la última respuesta del turno lleva la pantalla
    assert "PANTALLA:" not in respuestas[0]["content"]
    assert "PANTALLA:" in respuestas[1]["content"]


def test_solo_se_mandan_completas_las_ultimas_pantallas(caso):
    turnos = []
    for numero in range(5):
        turnos.append(
            [llamada("escribir", str(numero), campo="x", valor=str(numero))]
        )
    turnos.append([terminar("bloqueado", [])])
    cliente = ClienteGuion(turnos)
    ejecutar(cliente, NavegadorFalso(), caso)
    ultima = cliente.conversaciones[-1]
    completas = 0
    for mensaje in ultima:
        if "PANTALLA:" in str(mensaje.get("content")):
            completas += 1
    assert completas == agente.PANTALLAS_COMPLETAS
    # El caso sigue en el primer mensaje aunque se quite su pantalla
    assert "#### CP-47" in ultima[1]["content"]


def test_preparacion_en_el_mensaje_inicial(caso):
    previo = Caso(id="CP-46", titulo="Previo", texto="#### CP-46 pasos")
    cliente = ClienteGuion([[terminar("bloqueado", [])]])
    ejecutar(cliente, NavegadorFalso(), caso, preparacion=[previo])
    inicial = cliente.conversaciones[0][1]["content"]
    assert "PREPARACIÓN" in inicial
    assert inicial.index("#### CP-46") < inicial.index("#### CP-47")


def test_sistema_pide_no_improvisar(caso):
    cliente = ClienteGuion([[terminar("bloqueado", [])]])
    ejecutar(cliente, NavegadorFalso(), caso)
    sistema = cliente.conversaciones[0][0]
    assert sistema["role"] == "system"
    assert "no improvises" in sistema["content"]


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("y = 2.0000 · x1 − 3", "Y = 2.0000 * X1 - 3"),
        ('textbox "Semilla": "42"', "textbox Semilla: 42"),
        ("dos   espacios\n y salto", "dos espacios y salto"),
    ],
)
def test_normalizar(a, b):
    assert normalizar(a) == normalizar(b)
