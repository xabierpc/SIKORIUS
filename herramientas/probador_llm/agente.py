"""Agente que ejecuta un caso de prueba con un LLM.

En cada turno el LLM ve la pantalla de la aplicación (como texto) y decide
la siguiente acción con una de las herramientas. Cuando termina, da su
veredicto con las evidencias: textos copiados de la pantalla.

El veredicto no se acepta a ciegas: el código comprueba que cada evidencia
aparece de verdad en lo que se ha visto durante el caso. Si alguna no
aparece, el caso queda como "Revisar" para que lo mire una persona.
"""

import time
from dataclasses import dataclass, field

from probador_llm import herramientas
from probador_llm.herramientas import TERMINAR

# Estados finales de un caso
CORRECTO = "Correcto"
FALLIDO = "Fallido"
BLOQUEADO = "Bloqueado"
REVISAR = "Revisar"
ERROR = "Error"

ESTADOS = {
    "correcto": CORRECTO,
    "fallido": FALLIDO,
    "bloqueado": BLOQUEADO,
}

# Turnos que se dejan al LLM, como máximo, para un caso
MAX_TURNOS = 40

# La pantalla actual va siempre en el último mensaje y no se guarda en la
# conversación. Así lo anterior no cambia entre turnos y Groq lo reutiliza
# de su caché: esos tokens no cuentan para los límites de uso.
CABECERA_PANTALLA = "PANTALLA ACTUAL:"

SISTEMA = """Eres un probador de software ajeno al proyecto: no conoces \
el código de la aplicación SIKORIUS. Ejecutas UN caso de prueba siguiendo \
solo sus pasos y comparas lo que ves con el resultado esperado.

- Al final de cada turno ves la pantalla actual como árbol de \
accesibilidad: button, tab, textbox (con su valor), combobox, listas y \
diálogos. "[disabled]" es deshabilitado. Los gráficos se describen en \
"GRÁFICOS". Los mensajes de la aplicación (ÉXITO, AVISO, ERROR) llegan \
con el resultado de cada acción.
- Usa siempre herramientas. Puedes pedir varias acciones en un mismo \
turno si no necesitas ver la pantalla entre ellas: ahorra turnos.
- La aplicación va por pestañas. Si un paso nombra algo que no se ve, ve a \
su pestaña (pulsando su nombre o "Continuar"). En el explorador de \
archivos, pulsa el nombre de una carpeta para entrar y ".." para subir.
- Los casos son aditivos: si la aplicación sigue como la dejó el caso \
anterior, no repitas lo hecho. Con la precondición "D-1 cargado", si D-1 \
ya es el dataset cargado (ruta en la pestaña Datos), no lo cargues.
- Si al cargar algo aparece una confirmación por cambios sin guardar y el \
caso no trata de eso, confírmala.
- No hagas nada que el caso no pida. Si un paso no se puede seguir, no \
improvises: termina con "bloqueado" e indica el paso.
- Si hay "PREPARACIÓN", hazla antes sin evaluarla.

Veredicto ("terminar"): "correcto" solo si TODO lo esperado coincide; \
"fallido" si algo no coincide (di qué esperabas y qué viste). Son \
equivalentes las diferencias solo de formato con el mismo valor (7 y \
7.0000, "*" y "·", "-" y "−"). En "evidencias" copia LITERALMENTE hasta 5 \
textos de la pantalla o de los mensajes: se comprobará que existen."""


@dataclass
class Paso:
    """Una acción del agente y lo que respondió la aplicación."""

    herramienta: str
    argumentos: dict
    resultado: str


@dataclass
class Resultado:
    """Resultado de ejecutar un caso.

    Attributes:
        caso: Identificador del caso.
        titulo: Título del caso.
        estado: Correcto, Fallido, Bloqueado, Revisar o Error.
        resultado_obtenido: Explicación del agente (o del error).
        evidencias: Textos que el agente cita como prueba.
        evidencias_no_encontradas: Evidencias que no estaban en pantalla.
        estado_agente: Veredicto original del agente, antes de comprobar
            las evidencias.
        paso_bloqueado: Paso que no se pudo seguir, si lo hay.
        pasos: Acciones realizadas.
        mensajes: Mensajes de la aplicación vistos durante el caso.
        turnos: Llamadas al LLM.
        tokens: Tokens que cuentan para los límites de Groq.
        tokens_cache: Tokens reutilizados de la caché (no cuentan).
        segundos: Duración del caso.
        reiniciado: True si el caso empezó con la aplicación recién abierta;
            False si continuó con lo que dejó el anterior.
    """

    caso: str
    titulo: str
    estado: str
    resultado_obtenido: str
    evidencias: list = field(default_factory=list)
    evidencias_no_encontradas: list = field(default_factory=list)
    estado_agente: str = ""
    paso_bloqueado: int = None
    pasos: list = field(default_factory=list)
    mensajes: list = field(default_factory=list)
    turnos: int = 0
    tokens: int = 0
    tokens_cache: int = 0
    segundos: float = 0.0
    reiniciado: bool = True


def instrucciones(contexto, carpeta_proyecto):
    """Mensaje de sistema: igual en todas las llamadas de la ejecución.

    Lleva las reglas, el contexto del plan y las carpetas. Como no cambia
    de un caso a otro, Groq lo reutiliza de su caché.
    """
    return (
        SISTEMA
        + "\n\nCONTEXTO DEL PLAN:\n"
        + contexto
        + "\n\nCarpeta del proyecto: "
        + str(carpeta_proyecto)
        + "\nCarpeta data/: "
        + str(carpeta_proyecto / "data")
    )


def mensaje_inicial(
    caso,
    preparacion,
    referencias=(),
    estado_inicial="La aplicación está recién abierta (PR-1 hecho).",
):
    """Primer mensaje de un caso: el caso y cómo empieza."""
    partes = [estado_inicial, ""]
    if referencias:
        partes.append(
            "CASOS CITADOS (solo como referencia: haz sus pasos únicamente "
            "si el caso que ejecutas lo pide):"
        )
        for citado in referencias:
            partes.append(citado.texto)
            partes.append("")
    if preparacion:
        partes.append(
            "PREPARACIÓN: antes del caso, haz los pasos de estos casos, en "
            "este orden, sin evaluarlos (no llames a 'terminar' al acabar "
            "la preparación):"
        )
        for previo in preparacion:
            partes.append(previo.texto)
            partes.append("")
        partes.append("Cuando termines la preparación, ejecuta este caso.")
    partes.append("CASO QUE HAY QUE EJECUTAR Y EVALUAR:")
    partes.append(caso.texto)
    return "\n".join(partes)


def ejecutar_caso(
    cliente,
    navegador,
    reiniciar,
    caso,
    preparacion,
    contexto,
    carpeta_proyecto,
    max_turnos=MAX_TURNOS,
    referencias=(),
    estado_inicial="La aplicación está recién abierta (PR-1 hecho).",
):
    """Ejecuta un caso con el LLM y devuelve su ``Resultado``.

    La conversación guarda las acciones y sus resultados (con los mensajes
    de la aplicación), pero no las pantallas: la pantalla actual se añade
    solo al final de cada llamada. Así lo anterior no cambia de un turno a
    otro y Groq lo reutiliza de su caché.

    Args:
        cliente: Cliente del LLM (``responder(mensajes, herramientas)``).
        navegador: ``Navegador`` con la aplicación abierta.
        reiniciar: Función que cierra y abre la aplicación.
        caso: ``Caso`` que se ejecuta.
        preparacion: Casos que se repiten antes (``Plan.preparacion``).
        contexto: Contexto del plan.
        carpeta_proyecto: ``Path`` de la raíz del repositorio.
        max_turnos: Llamadas al LLM permitidas.
        referencias: Casos citados por el caso (``Plan.referencias``).
        estado_inicial: Cómo está la aplicación al empezar (recién abierta
            o como la dejó el caso anterior).
    """
    inicio = time.monotonic()
    resultado = Resultado(
        caso=caso.id,
        titulo=caso.titulo,
        estado=BLOQUEADO,
        resultado_obtenido="",
    )
    mensajes = [
        {
            "role": "system",
            "content": instrucciones(contexto, carpeta_proyecto),
        },
        {
            "role": "user",
            "content": mensaje_inicial(
                caso, preparacion, referencias, estado_inicial
            ),
        },
    ]
    pantalla = navegador.observar()
    navegador.capturar("inicio")

    terminado = False
    while not terminado and resultado.turnos < max_turnos:
        resultado.turnos += 1
        envio = list(mensajes)
        envio.append(
            {"role": "user", "content": CABECERA_PANTALLA + "\n" + pantalla}
        )
        respuesta = cliente.responder(envio, herramientas.HERRAMIENTAS)
        resultado.tokens += respuesta.tokens
        resultado.tokens_cache += getattr(respuesta, "tokens_cache", 0)
        mensajes.append(respuesta.mensaje)
        if not respuesta.llamadas:
            mensajes.append(
                {
                    "role": "user",
                    "content": "Usa una herramienta: la siguiente acción o "
                    "'terminar' con el veredicto.",
                }
            )
            continue

        for llamada in respuesta.llamadas:
            if llamada.nombre == TERMINAR:
                _aplicar_veredicto(resultado, llamada.argumentos, navegador)
                texto = "Veredicto registrado."
                terminado = True
            elif terminado:
                texto = "Ignorado: el caso ya ha terminado."
            else:
                texto = _accion(navegador, reiniciar, llamada)
                resultado.pasos.append(
                    Paso(llamada.nombre, llamada.argumentos, texto)
                )
                navegador.capturar(llamada.nombre)
                # Se mira la pantalla tras cada acción para no perder los
                # mensajes, que desaparecen a los pocos segundos
                pantalla = navegador.observar()
                if navegador.nuevos:
                    texto = (
                        texto
                        + "\nMensajes de la aplicación: "
                        + " | ".join(navegador.nuevos)
                    )
            mensajes.append(
                {
                    "role": "tool",
                    "tool_call_id": llamada.id,
                    "content": texto,
                }
            )

    if not terminado:
        resultado.estado = BLOQUEADO
        resultado.resultado_obtenido = (
            "El agente no ha terminado en "
            + str(max_turnos)
            + " turnos. Revisa si algún paso es ambiguo."
        )
    resultado.mensajes = list(navegador.mensajes)
    resultado.segundos = round(time.monotonic() - inicio, 1)
    return resultado


def _accion(navegador, reiniciar, llamada):
    if llamada.error:
        return "ERROR: " + llamada.error
    try:
        return herramientas.ejecutar(
            navegador, reiniciar, llamada.nombre, llamada.argumentos
        )
    except Exception as error:  # noqa: BLE001 - se informa al agente
        return "ERROR al hacer la acción: " + str(error).splitlines()[0]


def _aplicar_veredicto(resultado, argumentos, navegador):
    estado = str(argumentos.get("estado", "")).lower()
    resultado.estado_agente = estado
    resultado.resultado_obtenido = str(
        argumentos.get("resultado_obtenido", "")
    )
    evidencias = argumentos.get("evidencias") or []
    if isinstance(evidencias, str):
        evidencias = [evidencias]
    resultado.evidencias = list(evidencias)
    paso = argumentos.get("paso_bloqueado")
    if isinstance(paso, int):
        resultado.paso_bloqueado = paso

    if estado not in ESTADOS:
        resultado.estado = REVISAR
        resultado.resultado_obtenido = (
            "Veredicto no válido (" + estado + "). "
        ) + resultado.resultado_obtenido
        return

    visto = normalizar(
        "\n".join(navegador.textos_vistos)
        + "\n"
        + "\n".join(navegador.mensajes)
    )
    for evidencia in resultado.evidencias:
        if normalizar(evidencia) not in visto:
            resultado.evidencias_no_encontradas.append(evidencia)

    if estado == "bloqueado":
        resultado.estado = BLOQUEADO
    elif not resultado.evidencias or resultado.evidencias_no_encontradas:
        # Sin pruebas reales, el veredicto lo confirma una persona
        resultado.estado = REVISAR
    else:
        resultado.estado = ESTADOS[estado]


def normalizar(texto):
    """Quita diferencias que no importan al comparar textos.

    Espacios repetidos, mayúsculas, comillas del árbol de accesibilidad y
    las variantes del signo menos y del punto de multiplicar.
    """
    texto = str(texto).lower()
    for original, cambio in (
        ("−", "-"),
        ("·", "*"),
        ('"', ""),
        ("'", ""),
        (" ", " "),
    ):
        texto = texto.replace(original, cambio)
    return " ".join(texto.split())
