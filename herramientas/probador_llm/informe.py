"""Informe de una ejecución: registro, resumen y detalle de cada caso.

Genera dos archivos en la carpeta de la ejecución:

- ``registro.md``: la tabla del registro de ejecución (sección 6 del plan)
  rellenada, el resumen y el detalle de cada caso (pasos, mensajes y
  evidencias). Es lo que se revisa y se copia al informe de pruebas.
- ``resultados.json``: lo mismo en JSON, por si se quiere procesar.
"""

import json
from dataclasses import asdict
from datetime import datetime

from probador_llm.agente import (
    BLOQUEADO,
    CORRECTO,
    ERROR,
    FALLIDO,
    REVISAR,
)

MANUAL = "Manual"
NO_EJECUTADO = "No ejecutado"
ORDEN_ESTADOS = (
    CORRECTO,
    FALLIDO,
    BLOQUEADO,
    REVISAR,
    ERROR,
    MANUAL,
    NO_EJECUTADO,
)


def contar(resultados):
    """Número de casos en cada estado (todos los estados, aunque sea 0)."""
    cuentas = {}
    for estado in ORDEN_ESTADOS:
        cuentas[estado] = 0
    for resultado in resultados:
        cuentas[resultado.estado] = cuentas.get(resultado.estado, 0) + 1
    return cuentas


def escribir(carpeta, resultados, datos_ejecucion):
    """Escribe ``registro.md`` y ``resultados.json`` en ``carpeta``.

    Args:
        carpeta: ``Path`` de la ejecución.
        resultados: Lista de ``Resultado``, en el orden del plan.
        datos_ejecucion: Diccionario con modelo, commit, fecha, etc.

    Returns:
        La ruta de ``registro.md``.
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    datos = dict(datos_ejecucion)
    datos["resumen"] = contar(resultados)
    casos = []
    for resultado in resultados:
        casos.append(asdict(resultado))
    datos["casos"] = casos
    (carpeta / "resultados.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ruta = carpeta / "registro.md"
    ruta.write_text(texto_registro(resultados, datos), encoding="utf-8")
    return ruta


def texto_registro(resultados, datos):
    """Markdown del registro de ejecución."""
    lineas = []
    lineas.append("# Registro de ejecución de las pruebas funcionales")
    lineas.append("")
    lineas.append("- **Ejecutado por:** LLM `" + datos["modelo"] + "`")
    lineas.append("- **Fecha:** " + datos["fecha"])
    lineas.append("- **Commit de la aplicación:** `" + datos["commit"] + "`")
    lineas.append("- **Plan:** `" + datos["plan"] + "`")
    lineas.append("")
    lineas.append("## Resumen")
    lineas.append("")
    cuentas = datos["resumen"]
    ejecutados = len(resultados) - cuentas[MANUAL] - cuentas[NO_EJECUTADO]
    lineas.append("| Estado | Casos |")
    lineas.append("|---|---|")
    lineas.append("| Ejecutados por el LLM | " + str(ejecutados) + " |")
    for estado in ORDEN_ESTADOS:
        lineas.append("| " + estado + " | " + str(cuentas[estado]) + " |")
    lineas.append("")
    lineas.append(
        "**Revisar**: el LLM dio un veredicto, pero alguna evidencia que "
        "citó no aparece en la pantalla; lo confirma una persona. "
        "**Bloqueado**: no pudo seguir algún paso; probablemente hay que "
        "reescribir el caso. **Manual**: caso que no se ejecuta con el LLM. "
        "**No ejecutado**: faltan valores del plan por rellenar."
    )
    lineas.append("")
    lineas.append("## Registro")
    lineas.append("")
    lineas.append(
        "| Caso | Resultado obtenido | Estado | Ejecutado por | Fecha |"
    )
    lineas.append("|---|---|---|---|---|")
    for resultado in resultados:
        lineas.append(
            "| "
            + resultado.caso
            + " | "
            + _celda(resultado.resultado_obtenido)
            + " | "
            + resultado.estado
            + " | LLM | "
            + datos["fecha"][:10]
            + " |"
        )
    lineas.append("")
    lineas.append("## Detalle de cada caso")
    for resultado in resultados:
        lineas.extend(_detalle(resultado))
    lineas.append("")
    return "\n".join(lineas)


def _detalle(resultado):
    lineas = ["", "### " + resultado.caso + ". " + resultado.titulo, ""]
    lineas.append("- **Estado:** " + resultado.estado)
    if resultado.estado_agente:
        lineas.append("- **Veredicto del LLM:** " + resultado.estado_agente)
    if resultado.paso_bloqueado is not None:
        lineas.append("- **Paso bloqueado:** " + str(resultado.paso_bloqueado))
    lineas.append("- **Resultado obtenido:** " + resultado.resultado_obtenido)
    if resultado.evidencias:
        lineas.append("- **Evidencias:**")
        for evidencia in resultado.evidencias:
            marca = "✔"
            if evidencia in resultado.evidencias_no_encontradas:
                marca = "✘ no aparece en pantalla"
            lineas.append("  - `" + evidencia + "` " + marca)
    if resultado.mensajes:
        lineas.append("- **Mensajes de la aplicación:**")
        for mensaje in resultado.mensajes:
            lineas.append("  - " + _una_linea(mensaje))
    if resultado.pasos:
        lineas.append("- **Acciones:**")
        for numero, paso in enumerate(resultado.pasos, start=1):
            lineas.append(
                "  "
                + str(numero)
                + ". "
                + paso.herramienta
                + " "
                + json.dumps(paso.argumentos, ensure_ascii=False)
                + " → "
                + _una_linea(paso.resultado)
            )
    lineas.append(
        "- **Turnos:** "
        + str(resultado.turnos)
        + " · **Tokens:** "
        + str(resultado.tokens)
        + " · **Duración:** "
        + str(resultado.segundos)
        + " s · **Capturas:** `capturas/"
        + resultado.caso
        + "/`"
    )
    return lineas


def fecha_actual():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _una_linea(texto):
    return " ".join(str(texto).split())


def _celda(texto):
    texto = _una_linea(texto).replace("|", "\\|")
    if len(texto) > 160:
        texto = texto[:157] + "..."
    return texto
