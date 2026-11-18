"""Conexión con la API de Groq para el asistente.

Es el único archivo que sabe que la LLM es de Groq: la capa de aplicación
solo espera un objeto con el método ``responder`` (ver
``aplicacion.asistente.ClienteLLM``). Para cambiar de proveedor basta con
escribir otra clase con ese método.

La clave se lee de la variable de entorno ``GROQ_API_KEY``, o del archivo
``.env`` de la carpeta desde la que se arranca la aplicación. El ``.env``
no se sube al repositorio (está en .gitignore).
"""

import os

from dotenv import load_dotenv
from groq import AsyncGroq, GroqError
from pydantic import ValidationError

from sikorius.dominio.asistente import INSTRUCCIONES, RespuestaAsistente
from sikorius.dominio.errores import ErrorAsistente

VARIABLE_CLAVE = "GROQ_API_KEY"
VARIABLE_MODELO = "SIKORIUS_MODELO_GROQ"
# Uno de los modelos de Groq con salida estructurada estricta: la
# respuesta sigue siempre el esquema de RespuestaAsistente.
MODELO_DEFECTO = "openai/gpt-oss-20b"
SEGUNDOS_ESPERA = 60


class ClienteGroq:
    """Pide a una LLM de Groq la respuesta del asistente."""

    def __init__(self, clave, modelo=MODELO_DEFECTO, cliente=None):
        self.modelo = modelo
        # cliente se puede pasar en los tests para no usar la red
        if cliente is None:
            cliente = AsyncGroq(api_key=clave, timeout=SEGUNDOS_ESPERA)
        self._cliente = cliente

    async def responder(self, conversacion, contexto):
        """Envía la conversación y devuelve la respuesta validada.

        Args:
            conversacion: Lista de ``{"role": "user" | "assistant",
                "content": texto}``, de la más antigua a la más reciente.
            contexto: Resumen del trabajo actual
                (``dominio.asistente.construir_contexto``).

        Returns:
            Un ``RespuestaAsistente``.

        Raises:
            ErrorAsistente: Si la API falla o la respuesta no sigue el
                esquema.
        """
        mensajes = [
            {"role": "system", "content": INSTRUCCIONES},
            {
                "role": "system",
                "content": "Situación actual de SIKORIUS:\n" + contexto,
            },
        ]
        mensajes.extend(conversacion)
        try:
            respuesta = await self._cliente.chat.completions.create(
                model=self.modelo,
                messages=mensajes,
                temperature=0.2,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "respuesta_asistente",
                        "strict": True,
                        "schema": RespuestaAsistente.model_json_schema(),
                    },
                },
            )
        except GroqError as error:
            raise ErrorAsistente(_explicar_error(error)) from error
        contenido = respuesta.choices[0].message.content
        try:
            return RespuestaAsistente.model_validate_json(contenido or "")
        except ValidationError as error:
            raise ErrorAsistente(
                "El asistente ha devuelto una respuesta que no se entiende. "
                "Prueba a decirlo de otra forma."
            ) from error


def _explicar_error(error):
    """Mensaje para el usuario según el tipo de error de Groq."""
    nombre = type(error).__name__
    if nombre == "AuthenticationError":
        return "La clave de Groq no es válida. Revisa " + VARIABLE_CLAVE + "."
    if nombre == "RateLimitError":
        return (
            "Se ha alcanzado el límite de uso de Groq. Espera un poco y "
            "vuelve a intentarlo."
        )
    if nombre in ("APIConnectionError", "APITimeoutError"):
        return "No se puede conectar con Groq. Revisa la conexión a internet."
    return "Groq ha devuelto un error: " + str(error)


def crear_cliente_groq():
    """Cliente de Groq con la clave del entorno, o None si no hay clave.

    Sin clave la aplicación funciona igual: el asistente sale desactivado
    y explica cómo configurarlo.
    """
    load_dotenv()
    clave = os.environ.get(VARIABLE_CLAVE, "").strip()
    if clave == "":
        return None
    modelo = os.environ.get(VARIABLE_MODELO, "").strip() or MODELO_DEFECTO
    return ClienteGroq(clave, modelo)
