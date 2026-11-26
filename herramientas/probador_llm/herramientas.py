"""Herramientas que puede usar el agente y cómo se ejecutan.

El agente solo puede hacer lo que haría una persona delante de la pantalla:
pulsar, escribir, elegir en un desplegable, pulsar una tecla, esperar y
cerrar y volver a abrir la aplicación. Cuando ha terminado, llama a
``terminar`` con su veredicto.

Las definiciones siguen el formato de "tools" de la API de chat de OpenAI,
que es el que usa Groq.
"""

from probador_llm.navegador import TECLAS, ErrorAccion

TERMINAR = "terminar"
ESTADOS_AGENTE = ("correcto", "fallido", "bloqueado")


def _funcion(nombre, descripcion, propiedades, obligatorias):
    return {
        "type": "function",
        "function": {
            "name": nombre,
            "description": descripcion,
            "parameters": {
                "type": "object",
                "properties": propiedades,
                "required": obligatorias,
            },
        },
    }


HERRAMIENTAS = [
    _funcion(
        "pulsar",
        "Pulsa un botón, pestaña, opción, casilla o elemento de una lista "
        "(carpetas y archivos del explorador) por el texto que se ve.",
        {"texto": {"type": "string", "description": "Texto exacto"}},
        ["texto"],
    ),
    _funcion(
        "escribir",
        "Borra el contenido de un campo de texto y escribe un valor. Para "
        "dejar un campo vacío, escribe la cadena vacía.",
        {
            "campo": {"type": "string", "description": "Etiqueta del campo"},
            "valor": {"type": "string"},
        },
        ["campo", "valor"],
    ),
    _funcion(
        "elegir",
        "Abre un desplegable y elige una o varias opciones.",
        {
            "selector": {
                "type": "string",
                "description": "Etiqueta del desplegable",
            },
            "opciones": {"type": "array", "items": {"type": "string"}},
        },
        ["selector", "opciones"],
    ),
    _funcion(
        "tecla",
        "Pulsa una tecla del teclado.",
        {"nombre": {"type": "string", "enum": list(TECLAS)}},
        ["nombre"],
    ),
    _funcion(
        "esperar",
        "Espera unos segundos (máximo 10) sin hacer nada.",
        {"segundos": {"type": "number"}},
        ["segundos"],
    ),
    _funcion(
        "reiniciar_aplicacion",
        "Cierra la aplicación y la vuelve a abrir (procedimiento PR-1). "
        "Úsala solo cuando un paso lo pida.",
        {},
        [],
    ),
    _funcion(
        TERMINAR,
        "Termina el caso con el veredicto. Úsala una sola vez, al final.",
        {
            "estado": {"type": "string", "enum": list(ESTADOS_AGENTE)},
            "resultado_obtenido": {
                "type": "string",
                "description": "Qué ha mostrado la aplicación, comparado "
                "con el resultado esperado punto por punto",
            },
            "evidencias": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Hasta 5 textos copiados LITERALMENTE de la "
                "pantalla o de los mensajes que prueban el veredicto",
            },
            "paso_bloqueado": {
                "type": "integer",
                "description": "Solo si el estado es bloqueado: número del "
                "paso que no se pudo seguir",
            },
        },
        ["estado", "resultado_obtenido", "evidencias"],
    ),
]


def ejecutar(navegador, reiniciar, nombre, argumentos):
    """Ejecuta una herramienta (salvo ``terminar``) y describe qué ha pasado.

    Args:
        navegador: ``Navegador`` con la aplicación.
        reiniciar: Función sin argumentos que cierra y abre la aplicación.
        nombre: Nombre de la herramienta.
        argumentos: Diccionario con sus argumentos.

    Returns:
        Texto con el resultado, también si la acción no se ha podido hacer
        (el agente debe saberlo para decidir qué hacer).
    """
    try:
        if nombre == "pulsar":
            return navegador.pulsar(_texto(argumentos, "texto"))
        if nombre == "escribir":
            return navegador.escribir(
                _texto(argumentos, "campo"),
                str(argumentos.get("valor", "")),
            )
        if nombre == "elegir":
            opciones = argumentos.get("opciones")
            if isinstance(opciones, str):
                opciones = [opciones]
            if not opciones:
                return "ERROR: indica al menos una opción."
            return navegador.elegir(_texto(argumentos, "selector"), opciones)
        if nombre == "tecla":
            return navegador.tecla(_texto(argumentos, "nombre"))
        if nombre == "esperar":
            return navegador.esperar(argumentos.get("segundos", 1))
        if nombre == "reiniciar_aplicacion":
            reiniciar()
            return "Aplicación cerrada y abierta de nuevo."
    except ErrorAccion as error:
        return "ERROR: " + str(error)
    except (KeyError, TypeError, ValueError) as error:
        return "ERROR: argumentos no válidos (" + str(error) + ")."
    return "ERROR: no existe la herramienta " + str(nombre) + "."


def _texto(argumentos, clave):
    valor = argumentos[clave]
    if not isinstance(valor, str):
        raise TypeError("'" + clave + "' debe ser texto")
    return valor
