"""Fórmula del modelo lista para mostrar: en texto o en HTML con colores.

Los números y los signos de cada término los calcula el dominio
(``terminos_formula``); aquí solo se decide cómo se escriben.
"""

import html

from sikorius.dominio.modelo import terminos_formula


def _formula(mod, marcar):
    """Construye la fórmula en una sola línea, lista para mostrar.

    ``marcar`` es la función que recibe el nombre de una columna y devuelve
    cómo se escribe: tal cual (texto) o con su color (HTML).

    Dentro de cada término los espacios son "espacios duros" (\u00a0): si la
    fórmula no cabe y se parte en varias líneas, solo se parte entre términos
    y nunca deja un signo solo al final de una línea.
    """
    duro = "\u00a0"
    terminos = []
    for posicion, (negativo, numero, columna) in enumerate(
        terminos_formula(mod)
    ):
        cuerpo = numero
        if columna is not None:
            cuerpo += duro + "·" + duro + marcar(str(columna))
        if posicion == 0:
            # El primer término lleva el signo pegado, solo si es negativo
            signo = "−" if negativo else ""
        else:
            signo = ("−" if negativo else "+") + duro
        terminos.append(signo + cuerpo)
    return marcar(str(mod.target)) + " = " + " ".join(terminos)


def _sin_marcar(nombre):
    return nombre


def texto_formula(mod):
    """La fórmula del modelo en una sola línea y sin colores.

    Ejemplo: ``y = 2.0000 · x1 − 3.0000 · x2 + 5.0000``.
    """
    return _formula(mod, _sin_marcar)


def html_formula(mod, colores):
    """La misma fórmula en HTML, con cada columna de su color.

    ``colores`` es {nombre de columna: color}. Los nombres vienen del
    usuario, así que se escapan: un nombre como ``<b>`` se ve tal cual y no
    se interpreta como HTML.
    """

    def marcar(nombre):
        seguro = html.escape(nombre)
        color = colores.get(nombre)
        if color is None:
            return seguro
        return (
            '<span style="color: '
            + color
            + '; font-weight: 700">'
            + seguro
            + "</span>"
        )

    return _formula(mod, marcar)
