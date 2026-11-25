"""Cliente del LLM de Groq para el agente.

Envía la conversación con las herramientas y devuelve las llamadas que
quiere hacer el modelo. El agente no depende de Groq: cualquier objeto con
el método ``responder(mensajes, herramientas)`` que devuelva una
``Respuesta`` sirve (los tests usan uno falso).

La clave se lee de la variable de entorno ``GROQ_API_KEY`` o, si no está,
del archivo ``.env`` de la raíz del proyecto (``GROQ_API_KEY=...``), que no
se sube al repositorio.
"""

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

MODELO_POR_DEFECTO = "openai/gpt-oss-120b"
VARIABLE_CLAVE = "GROQ_API_KEY"

# Reintentos si Groq responde que se ha superado el límite de uso
REINTENTOS = 6
ESPERA_INICIAL = 5.0


class ErrorClave(Exception):
    """No se ha encontrado la clave de la API."""


@dataclass
class Llamada:
    """Una herramienta que quiere usar el modelo.

    Attributes:
        id: Identificador que hay que devolver con el resultado.
        nombre: Nombre de la herramienta.
        argumentos: Diccionario con los argumentos.
        error: Mensaje si los argumentos no son JSON válido; None si lo son.
    """

    id: str
    nombre: str
    argumentos: dict
    error: str = None


@dataclass
class Respuesta:
    """Respuesta del modelo en un turno.

    Attributes:
        mensaje: Mensaje del asistente, listo para añadir a la conversación.
        llamadas: Herramientas que quiere usar, en orden.
        tokens: Tokens consumidos en este turno.
    """

    mensaje: dict
    llamadas: list = field(default_factory=list)
    tokens: int = 0


def leer_clave(raiz):
    """Busca la clave en el entorno o en ``<raiz>/.env``.

    Raises:
        ErrorClave: Si no está en ninguno de los dos sitios.
    """
    clave = os.environ.get(VARIABLE_CLAVE, "").strip()
    if clave:
        return clave
    archivo = Path(raiz) / ".env"
    if archivo.is_file():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea.startswith(VARIABLE_CLAVE):
                continue
            nombre, _, valor = linea.partition("=")
            if nombre.strip() == VARIABLE_CLAVE:
                valor = valor.strip().strip('"').strip("'")
                if valor:
                    return valor
    raise ErrorClave(
        "Falta la clave de Groq. Ponla en la variable de entorno "
        + VARIABLE_CLAVE
        + " o en el archivo .env de la raíz del proyecto ("
        + VARIABLE_CLAVE
        + "=...)."
    )


def convertir_respuesta(respuesta):
    """Pasa la respuesta del SDK (formato OpenAI) a una ``Respuesta``."""
    mensaje = respuesta.choices[0].message
    contenido = mensaje.content or ""
    para_conversacion = {"role": "assistant", "content": contenido}
    llamadas = []
    llamadas_crudas = mensaje.tool_calls or []
    if llamadas_crudas:
        para_conversacion["tool_calls"] = []
    for cruda in llamadas_crudas:
        para_conversacion["tool_calls"].append(
            {
                "id": cruda.id,
                "type": "function",
                "function": {
                    "name": cruda.function.name,
                    "arguments": cruda.function.arguments or "{}",
                },
            }
        )
        llamadas.append(_crear_llamada(cruda))
    tokens = 0
    if getattr(respuesta, "usage", None) is not None:
        tokens = respuesta.usage.total_tokens or 0
    return Respuesta(
        mensaje=para_conversacion, llamadas=llamadas, tokens=tokens
    )


def _crear_llamada(cruda):
    texto = cruda.function.arguments or "{}"
    try:
        argumentos = json.loads(texto)
    except json.JSONDecodeError:
        return Llamada(
            cruda.id,
            cruda.function.name,
            {},
            "los argumentos no son JSON válido: " + texto[:200],
        )
    if not isinstance(argumentos, dict):
        return Llamada(
            cruda.id,
            cruda.function.name,
            {},
            "los argumentos deben ser un objeto JSON",
        )
    return Llamada(cruda.id, cruda.function.name, argumentos)


class ClienteGroq:
    """Cliente de la API de chat de Groq con herramientas.

    Attributes:
        modelo: Nombre del modelo de Groq.
        temperatura: 0 para que las respuestas varíen lo menos posible.
    """

    def __init__(self, clave, modelo=MODELO_POR_DEFECTO, temperatura=0.0):
        # Se importa aquí: los tests y el resto del probador no necesitan
        # tener instalado el paquete groq
        import groq

        self._groq = groq
        self._cliente = groq.Groq(api_key=clave)
        self.modelo = modelo
        self.temperatura = temperatura

    def responder(self, mensajes, herramientas):
        """Pide al modelo la siguiente acción.

        Si se supera el límite de uso de Groq, espera y lo vuelve a
        intentar, cada vez el doble de tiempo.
        """
        espera = ESPERA_INICIAL
        for intento in range(REINTENTOS):
            try:
                respuesta = self._cliente.chat.completions.create(
                    model=self.modelo,
                    messages=mensajes,
                    tools=herramientas,
                    tool_choice="auto",
                    temperature=self.temperatura,
                )
                return convertir_respuesta(respuesta)
            except self._groq.RateLimitError:
                if intento == REINTENTOS - 1:
                    raise
                time.sleep(espera)
                espera = espera * 2
            except self._groq.BadRequestError as error:
                # A veces el modelo escribe una llamada mal formada y Groq
                # la rechaza: se le avisa para que lo intente otra vez
                if "tool" not in str(error).lower():
                    raise
                if intento == REINTENTOS - 1:
                    raise
                mensajes = list(mensajes) + [
                    {
                        "role": "user",
                        "content": "Tu última llamada a una herramienta no "
                        "era válida. Vuelve a intentarlo.",
                    }
                ]
        raise RuntimeError("No se ha obtenido respuesta del modelo")
