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

# Pantallas anteriores que se mandan completas. Las más antiguas se
# resumen para no gastar tokens con pantallas que ya no sirven.
PANTALLAS_COMPLETAS = 2
MARCA_PANTALLA = "\n\nPANTALLA:"
PANTALLA_OMITIDA = "\n\n[pantalla anterior omitida]"

SISTEMA = """Eres un probador de software. No conoces el código ni has \
participado en el desarrollo de la aplicación SIKORIUS. Ejecutas UN caso \
de prueba funcional siguiendo solo los pasos escritos y comparas lo que \
ves con el resultado esperado.

Cómo trabajas:
- En cada turno ves la pantalla como un árbol de accesibilidad: botones \
(button), pestañas (tab), campos (textbox) con su valor, desplegables \
(combobox), listas y diálogos. "[disabled]" significa deshabilitado. Los \
mensajes de la aplicación aparecen en "MENSAJES NUEVOS DE LA APLICACIÓN" \
(ÉXITO, AVISO o ERROR). Los gráficos se describen en "GRÁFICOS VISIBLES".
- Usa siempre una herramienta. Haz los pasos en orden.
- La aplicación está organizada en pestañas. Si un paso nombra un botón, \
campo o sección que no se ve, puedes cambiar de pestaña (pulsando su \
nombre o "Continuar") para llegar a él. En el explorador de archivos, \
navega por las carpetas pulsando sus nombres ("..": carpeta superior). \
Esto no cuenta como un paso extra.
- No hagas nada que el caso no pida: no cambies datos ni pulses botones \
"por si acaso".
- Si un paso no se puede seguir (el elemento no existe o no está claro qué \
hacer), no improvises: termina con estado "bloqueado" e indica el paso.
- Si hay una sección "Preparación", hazla primero, sin evaluarla: solo \
deja la aplicación en el estado que pide el caso.

Veredicto (herramienta "terminar"):
- "correcto" solo si TODO lo del resultado esperado coincide.
- "fallido" si algo no coincide: explica qué esperabas y qué has visto.
- Considera equivalentes diferencias solo de formato con el mismo valor: \
número de decimales (7 y 7.0000), "*" y "·", "-" y "−".
- En "evidencias" copia LITERALMENTE textos de la pantalla o de los \
mensajes (máximo 5). Se comprobará que existen."""


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
        tokens: Tokens consumidos (entrada + salida).
        segundos: Duración del caso.
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
    segundos: float = 0.0


def mensaje_inicial(caso, preparacion, contexto, carpeta_proyecto, pantalla):
    """Texto con el que empieza la conversación de un caso."""
    partes = [
        "CONTEXTO DEL PLAN (procedimientos, glosario y datos de prueba):",
        contexto,
        "",
        "La carpeta del proyecto es: " + str(carpeta_proyecto),
        "La carpeta data/ es: " + str(carpeta_proyecto / "data"),
        "",
        "La aplicación ya está recién abierta (PR-1 hecho).",
        "",
    ]
    if preparacion:
        partes.append(
            "PREPARACIÓN: antes del caso, haz los pasos de estos casos, en "
            "este orden, sin evaluarlos (no llames a 'terminar' al acabar "
            "la preparación):"
        )
        for previo in preparacion:
            partes.append("")
            partes.append(previo.texto)
        partes.append("")
        partes.append("Cuando termines la preparación, ejecuta este caso:")
    partes.append("CASO QUE HAY QUE EJECUTAR Y EVALUAR:")
    partes.append(caso.texto)
    # Línea en blanco + "PANTALLA:" (lo pone observar) forman la marca
    partes.append("")
    partes.append(pantalla)
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
):
    """Ejecuta un caso con el LLM y devuelve su ``Resultado``.

    Args:
        cliente: Cliente del LLM (``responder(mensajes, herramientas)``).
        navegador: ``Navegador`` con la aplicación recién abierta.
        reiniciar: Función que cierra y abre la aplicación.
        caso: ``Caso`` que se ejecuta.
        preparacion: Casos que se repiten antes (``Plan.preparacion``).
        contexto: Contexto del plan.
        carpeta_proyecto: ``Path`` de la raíz del repositorio.
        max_turnos: Llamadas al LLM permitidas.
    """
    inicio = time.monotonic()
    resultado = Resultado(
        caso=caso.id,
        titulo=caso.titulo,
        estado=BLOQUEADO,
        resultado_obtenido="",
    )
    mensajes = [
        {"role": "system", "content": SISTEMA},
        {
            "role": "user",
            "content": mensaje_inicial(
                caso,
                preparacion,
                contexto,
                carpeta_proyecto,
                navegador.observar(),
            ),
        },
    ]
    navegador.capturar("inicio")

    terminado = False
    while not terminado and resultado.turnos < max_turnos:
        resultado.turnos += 1
        _resumir_pantallas(mensajes)
        respuesta = cliente.responder(mensajes, herramientas.HERRAMIENTAS)
        resultado.tokens += respuesta.tokens
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

        for indice, llamada in enumerate(respuesta.llamadas):
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
            # La pantalla solo se añade tras la última acción del turno
            ultima = indice == len(respuesta.llamadas) - 1
            if ultima and not terminado:
                texto = texto + "\n\n" + navegador.observar()
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


def _resumir_pantallas(mensajes):
    """Deja completas solo las últimas pantallas de la conversación."""
    vistas = 0
    for mensaje in reversed(mensajes):
        contenido = mensaje.get("content")
        if not isinstance(contenido, str) or MARCA_PANTALLA not in contenido:
            continue
        if mensaje["role"] == "user" and contenido.startswith("CONTEXTO"):
            # El mensaje inicial conserva el caso; solo se quita su pantalla
            if vistas >= PANTALLAS_COMPLETAS:
                corte = contenido.rfind(MARCA_PANTALLA)
                mensaje["content"] = contenido[:corte] + PANTALLA_OMITIDA
            continue
        vistas += 1
        if vistas > PANTALLAS_COMPLETAS:
            corte = contenido.find(MARCA_PANTALLA)
            mensaje["content"] = contenido[:corte] + PANTALLA_OMITIDA
