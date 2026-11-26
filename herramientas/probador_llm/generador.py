"""Generación del script de Playwright a partir de lo que hizo el LLM.

Cada caso ejecutado por el agente se convierte en un test de pytest con:

- sus acciones, en el mismo orden (las que dieron error se omiten, porque
  no cambiaron nada);
- una comprobación por cada evidencia que el agente citó y que el probador
  verificó en pantalla.

Los casos se escriben en el orden en que se ejecutaron, porque son
aditivos: cada uno parte de lo que dejó el anterior.
"""

import json

from probador_llm.agente import CORRECTO, FALLIDO, REVISAR

# Casos que se convierten en test. Los bloqueados y con error no: el caso
# siguiente empezó con la aplicación reiniciada, así que no dependen de él.
GENERABLES = (CORRECTO, FALLIDO, REVISAR)

ACCIONES = ("pulsar", "escribir", "elegir", "tecla", "esperar")

CABECERA = '''"""Pruebas funcionales del plan generadas por un LLM.

Generado por: {modelo}
Fecha: {fecha}
Commit de la aplicación: {commit}

Cada test es un caso del plan de pruebas (docs/plan_pruebas.md) con las
acciones que hizo el LLM y las comprobaciones de las evidencias que citó.
Se ejecuta sin LLM:

    uv run --group probador pytest herramientas/generados -v

Los tests van en orden y son aditivos: cada uno parte de lo que dejó el
anterior. Ejecútalos todos juntos y en este orden.

No edites este archivo a mano: se vuelve a generar con
herramientas/generar_script.py.
"""

import pytest

'''


def generar(resultados, datos_ejecucion):
    """Devuelve el código del script a partir de los resultados.

    Args:
        resultados: Lista de diccionarios de ``Resultado`` (como en
            ``resultados.json``), en el orden en que se ejecutaron.
        datos_ejecucion: Diccionario con modelo, fecha y commit.
    """
    partes = [
        CABECERA.format(
            modelo=datos_ejecucion.get("modelo", "desconocido"),
            fecha=datos_ejecucion.get("fecha", ""),
            commit=datos_ejecucion.get("commit", ""),
        )
    ]
    omitidos = []
    generados = 0
    for resultado in resultados:
        if resultado["estado"] not in GENERABLES:
            omitidos.append(
                resultado["caso"] + " (" + resultado["estado"] + ")"
            )
            continue
        partes.append(_test(resultado))
        generados += 1
    if omitidos:
        partes.append(
            "# Casos sin test (manuales, sin ejecutar, bloqueados o con "
            "error):\n# " + ", ".join(omitidos) + "\n"
        )
    if generados == 0:
        partes.append(
            "\ndef test_sin_casos():\n"
            '    pytest.skip("La ejecución no tiene casos generables")\n'
        )
    return "\n".join(partes)


def generar_desde_json(texto):
    """Genera el script desde el contenido de ``resultados.json``."""
    datos = json.loads(texto)
    return generar(datos["casos"], datos)


def _test(resultado):
    identificador = resultado["caso"]
    nombre = "test_" + identificador.lower().replace("-", "_")
    lineas = []
    if resultado["estado"] == FALLIDO:
        lineas.append(
            "@pytest.mark.xfail(reason="
            + _cadena("El LLM lo dio como fallido")
            + ", strict=False)"
        )
    lineas.append("def " + nombre + "(sikorius):")
    lineas.append(
        "    "
        + _cadena_docstring(
            identificador
            + ". "
            + resultado["titulo"]
            + "\n\n    Veredicto del LLM: "
            + resultado["estado"]
            + ". "
            + _una_linea(resultado["resultado_obtenido"])
        )
    )
    reiniciar = "True"
    if not resultado.get("reiniciado", True):
        reiniciar = "False"
    lineas.append(
        "    sikorius.empezar("
        + _cadena(identificador)
        + ", "
        + reiniciar
        + ")"
    )
    for paso in resultado.get("pasos", []):
        linea = _accion(paso)
        if linea:
            lineas.append("    " + linea)
    for evidencia in resultado.get("evidencias", []):
        if evidencia in resultado.get("evidencias_no_encontradas", []):
            continue
        lineas.append("    sikorius.comprobar(" + _cadena(evidencia) + ")")
    return "\n".join(lineas) + "\n"


def _accion(paso):
    """Línea de código de una acción, o "" si no se reproduce."""
    herramienta = paso["herramienta"]
    argumentos = paso.get("argumentos") or {}
    if str(paso.get("resultado", "")).startswith("ERROR"):
        return ""
    if herramienta == "reiniciar_aplicacion":
        return "sikorius.reiniciar_aplicacion()"
    if herramienta not in ACCIONES:
        return ""
    if herramienta == "pulsar":
        return "sikorius.pulsar(" + _cadena(argumentos.get("texto", "")) + ")"
    if herramienta == "escribir":
        return (
            "sikorius.escribir("
            + _cadena(argumentos.get("campo", ""))
            + ", "
            + _cadena(str(argumentos.get("valor", "")))
            + ")"
        )
    if herramienta == "elegir":
        opciones = argumentos.get("opciones") or []
        if isinstance(opciones, str):
            opciones = [opciones]
        textos = []
        for opcion in opciones:
            textos.append(_cadena(str(opcion)))
        return (
            "sikorius.elegir("
            + _cadena(argumentos.get("selector", ""))
            + ", ["
            + ", ".join(textos)
            + "])"
        )
    if herramienta == "tecla":
        return "sikorius.tecla(" + _cadena(argumentos.get("nombre", "")) + ")"
    segundos = argumentos.get("segundos", 1)
    if not isinstance(segundos, (int, float)):
        segundos = 1
    return "sikorius.esperar(" + repr(segundos) + ")"


def _cadena(texto):
    """Literal de Python para un texto (con comillas dobles)."""
    return json.dumps(str(texto), ensure_ascii=False)


def _cadena_docstring(texto):
    texto = texto.replace("\\", "\\\\").replace('"', '\\"')
    return '"""' + texto + '"""'


def _una_linea(texto):
    texto = " ".join(str(texto).split())
    if len(texto) > 300:
        texto = texto[:297] + "..."
    return texto
