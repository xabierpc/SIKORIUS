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
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

MODELO_POR_DEFECTO = "openai/gpt-oss-120b"
VARIABLE_CLAVE = "GROQ_API_KEY"

# Reintentos si Groq responde que se ha superado el límite por minuto
REINTENTOS = 8
ESPERA_INICIAL = 5.0

# Esfuerzo de razonamiento de los modelos gpt-oss: "low" gasta muchos
# menos tokens de salida y basta para seguir pasos
RAZONAMIENTO_POR_DEFECTO = "low"

# "Please try again in 7.5s" / "in 1m2.5s" en los errores de límite
PATRON_ESPERA = re.compile(r"try again in (?:(\d+)m)?([\d.]+)s")


class ErrorClave(Exception):
    """No se ha encontrado la clave de la API."""


class LimiteDiario(Exception):
    """Se han agotado los tokens o peticiones del día en Groq.

    No tiene sentido reintentar: hay que seguir otro día (o cambiar de
    plan en Groq). El probador para y guarda lo hecho.
    """


class PeticionDemasiadoGrande(Exception):
    """Una sola petición supera el límite de tokens por minuto."""


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
        tokens: Tokens que cuentan para los límites de Groq en este turno
            (los de entrada que no estaban en caché más los de salida).
        tokens_cache: Tokens de entrada reutilizados de la caché, que no
            cuentan para los límites.
    """

    mensaje: dict
    llamadas: list = field(default_factory=list)
    tokens: int = 0
    tokens_cache: int = 0


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
    cache = 0
    uso = getattr(respuesta, "usage", None)
    if uso is not None:
        tokens = uso.total_tokens or 0
        detalles = getattr(uso, "prompt_tokens_details", None)
        if detalles is not None:
            cache = getattr(detalles, "cached_tokens", 0) or 0
    return Respuesta(
        mensaje=para_conversacion,
        llamadas=llamadas,
        tokens=tokens - cache,
        tokens_cache=cache,
    )


def segundos_de_espera(mensaje):
    """Segundos que Groq pide esperar en un error de límite, o None."""
    coincidencia = PATRON_ESPERA.search(str(mensaje))
    if coincidencia is None:
        return None
    segundos = float(coincidencia.group(2))
    if coincidencia.group(1):
        segundos = segundos + 60 * int(coincidencia.group(1))
    return segundos


def es_limite_diario(mensaje):
    """True si el error es por el límite diario (tokens o peticiones)."""
    texto = str(mensaje).lower()
    return "per day" in texto or "(tpd)" in texto or "(rpd)" in texto


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

    def __init__(
        self,
        clave,
        modelo=MODELO_POR_DEFECTO,
        temperatura=0.0,
        razonamiento=RAZONAMIENTO_POR_DEFECTO,
    ):
        # Se importa aquí: los tests y el resto del probador no necesitan
        # tener instalado el paquete groq
        import groq

        self._groq = groq
        self._cliente = groq.Groq(api_key=clave)
        self.modelo = modelo
        self.temperatura = temperatura
        self.razonamiento = razonamiento

    def responder(self, mensajes, herramientas):
        """Pide al modelo la siguiente acción.

        Si se supera el límite por minuto, espera lo que indica Groq (o, si
        no lo indica, cada vez el doble) y lo vuelve a intentar.

        Raises:
            LimiteDiario: Si se han agotado los tokens o peticiones del día.
            PeticionDemasiadoGrande: Si la petición no cabe en el límite
                por minuto ni esperando.
        """
        opciones = {
            "model": self.modelo,
            "tools": herramientas,
            "tool_choice": "auto",
            "temperature": self.temperatura,
        }
        if self.modelo.startswith("openai/gpt-oss") and self.razonamiento:
            opciones["reasoning_effort"] = self.razonamiento
        espera = ESPERA_INICIAL
        for intento in range(REINTENTOS):
            try:
                respuesta = self._cliente.chat.completions.create(
                    messages=mensajes, **opciones
                )
                return convertir_respuesta(respuesta)
            except self._groq.APIStatusError as error:
                if error.status_code in (401, 403):
                    raise ErrorClave(
                        "Groq rechaza la clave ("
                        + str(error.status_code)
                        + "). "
                        "Revisa GROQ_API_KEY en el .env y que no haya una "
                        "variable GROQ_API_KEY antigua en la terminal."
                    ) from error
                if error.status_code == 413:
                    raise PeticionDemasiadoGrande(str(error)) from error
                if error.status_code == 429:
                    if es_limite_diario(error):
                        raise LimiteDiario(str(error)) from error
                    if intento == REINTENTOS - 1:
                        raise
                    pedida = segundos_de_espera(error)
                    if pedida is None:
                        time.sleep(espera)
                        espera = espera * 2
                    else:
                        print(
                            "  (límite por minuto de Groq: esperando "
                            + str(round(pedida + 1))
                            + " s)",
                            flush=True,
                        )
                        time.sleep(pedida + 1)
                    continue
                # A veces el modelo escribe una llamada mal formada y Groq
                # la rechaza: se le avisa para que lo intente otra vez
                if (
                    error.status_code != 400
                    or "tool" not in str(error).lower()
                ):
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
