"""Pruebas del cliente de Groq, sin red: el SDK se sustituye por uno falso.

uv run pytest tests/datos/test_cliente_groq.py -v
"""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from groq import APIConnectionError, AuthenticationError, RateLimitError

from sikorius.datos import cliente_groq
from sikorius.datos.cliente_groq import ClienteGroq, crear_cliente_groq
from sikorius.dominio.errores import ErrorAsistente

PETICION = httpx.Request("POST", "https://api.groq.com")


class SdkFalso:
    """Imita ``AsyncGroq``: guarda la petición y devuelve contenido fijo."""

    def __init__(self, contenido=None, error=None):
        self.peticiones = []
        self._contenido = contenido
        self._error = error
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._crear)
        )

    async def _crear(self, **kwargs):
        self.peticiones.append(kwargs)
        if self._error is not None:
            raise self._error
        mensaje = SimpleNamespace(content=self._contenido)
        return SimpleNamespace(choices=[SimpleNamespace(message=mensaje)])


def responder(sdk, conversacion=None, contexto="ctx"):
    cliente = ClienteGroq("clave", cliente=sdk)
    if conversacion is None:
        conversacion = [{"role": "user", "content": "hola"}]
    return asyncio.run(cliente.responder(conversacion, contexto))


def test_respuesta_valida():
    contenido = json.dumps(
        {
            "mensaje": "Quito duplicados",
            "operaciones": [
                {
                    "tipo": "eliminar_duplicados",
                    "columna": None,
                    "operador": None,
                    "valor": None,
                    "nombre_nuevo": None,
                }
            ],
        }
    )
    sdk = SdkFalso(contenido)
    respuesta = responder(sdk, contexto="Dataset: 3 filas")
    assert respuesta.mensaje == "Quito duplicados"
    assert respuesta.operaciones[0].tipo == "eliminar_duplicados"
    peticion = sdk.peticiones[0]
    assert peticion["model"] == cliente_groq.MODELO_DEFECTO
    formato = peticion["response_format"]
    assert formato["type"] == "json_schema"
    assert formato["json_schema"]["strict"] is True
    assert "Dataset: 3 filas" in peticion["messages"][1]["content"]
    assert peticion["messages"][-1] == {"role": "user", "content": "hola"}


@pytest.mark.parametrize("contenido", ["no es json", '{"mensaje": "x"}', None])
def test_respuesta_que_no_sigue_el_esquema(contenido):
    with pytest.raises(ErrorAsistente, match="no se entiende"):
        responder(SdkFalso(contenido))


def _respuesta_http(codigo):
    return httpx.Response(codigo, request=PETICION)


@pytest.mark.parametrize(
    "error, texto",
    [
        (
            AuthenticationError(
                "mal", response=_respuesta_http(401), body=None
            ),
            "no es válida",
        ),
        (
            RateLimitError("lento", response=_respuesta_http(429), body=None),
            "límite de uso",
        ),
        (APIConnectionError(request=PETICION), "conexión a internet"),
    ],
)
def test_errores_de_la_api(error, texto):
    with pytest.raises(ErrorAsistente, match=texto):
        responder(SdkFalso(error=error))


def test_sin_clave_no_hay_cliente(monkeypatch):
    monkeypatch.setattr(cliente_groq, "load_dotenv", lambda: None)
    monkeypatch.delenv(cliente_groq.VARIABLE_CLAVE, raising=False)
    assert crear_cliente_groq() is None


def test_con_clave_y_modelo_del_entorno(monkeypatch):
    monkeypatch.setattr(cliente_groq, "load_dotenv", lambda: None)
    monkeypatch.setenv(cliente_groq.VARIABLE_CLAVE, "gsk_prueba")
    monkeypatch.setenv(cliente_groq.VARIABLE_MODELO, "openai/gpt-oss-120b")
    cliente = crear_cliente_groq()
    assert cliente.modelo == "openai/gpt-oss-120b"
