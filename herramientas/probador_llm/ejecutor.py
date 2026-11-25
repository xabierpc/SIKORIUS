"""Ejecución del plan de pruebas completo con el LLM.

Para cada caso: arranca SIKORIUS recién abierta, abre una pestaña nueva
del navegador, deja que el agente haga el caso y guarda el resultado. El
registro se reescribe después de cada caso, así que si la ejecución se
corta se conserva lo hecho hasta entonces.
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from probador_llm import datos, informe
from probador_llm.agente import ERROR, REVISAR, Resultado, ejecutar_caso
from probador_llm.aplicacion import Aplicacion
from probador_llm.cliente_groq import (
    MODELO_POR_DEFECTO,
    ClienteGroq,
    leer_clave,
)
from probador_llm.navegador import Navegador
from probador_llm.plan import elegir_casos, leer_plan

RAIZ = Path(__file__).resolve().parents[2]
PLAN_POR_DEFECTO = RAIZ / "docs" / "plan_pruebas.md"

# Tamaño de la ventana del navegador: el mínimo que pide la historia #37
ANCHO = 1366
ALTO = 768

# Casos que no tiene sentido hacer con el LLM, con el motivo
MANUALES = {
    "CP-44": "Hay que abrir el CSV con una hoja de cálculo.",
    "CP-85": "Que la ventana no se bloquee se juzga moviéndola a mano.",
    "CP-86": "La fluidez del desplazamiento la juzga una persona.",
    "CP-88": "Hay que redimensionar la ventana del sistema operativo.",
    "CP-89": "El asistente no está en dev: se prueba a mano.",
    "CP-90": "El asistente no está en dev: se prueba a mano.",
    "CP-91": "El asistente no está en dev: se prueba a mano.",
    "CP-92": "Hay que renombrar el archivo .env.",
}

# "| D-1 (CSV) | `data/archivo.csv` |" en la sección de datos de prueba
PATRON_D1 = re.compile(r"^\|\s*D-1[^|]*\|\s*`([^`]+)`", re.MULTILINE)


def argumentos(lista=None):
    analizador = argparse.ArgumentParser(
        prog="probar_con_llm",
        description="Ejecuta los casos del plan de pruebas con un LLM.",
    )
    analizador.add_argument(
        "--plan", default=str(PLAN_POR_DEFECTO), help="Plan de pruebas"
    )
    analizador.add_argument(
        "--casos",
        default="",
        help="Casos a ejecutar: 'CP-01,CP-05' o 'CP-30:CP-40'. Por "
        "defecto, todos.",
    )
    analizador.add_argument(
        "--modelo", default=MODELO_POR_DEFECTO, help="Modelo de Groq"
    )
    analizador.add_argument(
        "--repeticiones",
        type=int,
        default=1,
        help="Veces que se ejecuta cada caso. Si los resultados no "
        "coinciden, el caso queda como 'Revisar'.",
    )
    analizador.add_argument(
        "--max-turnos", type=int, default=40, help="Turnos por caso"
    )
    analizador.add_argument(
        "--salida",
        default="",
        help="Carpeta de resultados. Por defecto, data/pruebas_llm/<fecha>/",
    )
    analizador.add_argument(
        "--chrome",
        action="store_true",
        help="Usa el Google Chrome instalado en vez del Chromium de "
        "Playwright",
    )
    analizador.add_argument(
        "--ver",
        action="store_true",
        help="Muestra la ventana del navegador mientras se prueba",
    )
    analizador.add_argument(
        "--permitir-huecos",
        action="store_true",
        help="Ejecuta también casos con valores del plan sin rellenar",
    )
    return analizador.parse_args(lista)


def main(lista=None):
    opciones = argumentos(lista)
    ruta_plan = Path(opciones.plan).resolve()
    texto_plan = ruta_plan.read_text(encoding="utf-8")
    plan = leer_plan(texto_plan)
    casos = elegir_casos(plan, opciones.casos)

    clave = leer_clave(RAIZ)
    cliente = ClienteGroq(clave, modelo=opciones.modelo)

    datos.preparar(RAIZ / "data", dataset_d1(texto_plan))

    if opciones.salida:
        salida = Path(opciones.salida).resolve()
    else:
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        salida = RAIZ / "data" / "pruebas_llm" / marca
    salida.mkdir(parents=True, exist_ok=True)

    datos_ejecucion = {
        "modelo": opciones.modelo,
        "fecha": informe.fecha_actual(),
        "commit": commit_actual(),
        "plan": str(ruta_plan.relative_to(RAIZ)),
    }
    _avisar_requisitos(casos)

    # Se importa aquí para que el resto del probador (y sus tests) no
    # necesiten Playwright instalado
    from playwright.sync_api import sync_playwright

    resultados = []
    registro = None
    aplicacion = Aplicacion(RAIZ, salida / "aplicacion.log")
    with aplicacion, sync_playwright() as playwright:
        navegador = _lanzar_navegador(playwright, opciones)
        for caso in casos:
            resultado = _resultado_sin_ejecutar(caso, opciones)
            if resultado is None:
                repeticiones = []
                for numero in range(max(1, opciones.repeticiones)):
                    carpeta = salida / "capturas" / caso.id
                    if numero > 0:
                        carpeta = carpeta / ("repeticion_" + str(numero + 1))
                    repeticiones.append(
                        _ejecutar(
                            navegador,
                            aplicacion,
                            cliente,
                            plan,
                            caso,
                            carpeta,
                            opciones.max_turnos,
                        )
                    )
                resultado = combinar(repeticiones)
            resultados.append(resultado)
            print(caso.id + ": " + resultado.estado, flush=True)
            registro = informe.escribir(salida, resultados, datos_ejecucion)
        navegador.close()

    cuentas = informe.contar(resultados)
    resumen = []
    for estado, numero in cuentas.items():
        if numero:
            resumen.append(estado + " " + str(numero))
    print("Resumen: " + ", ".join(resumen))
    print("Registro: " + str(registro))
    return 0


def _ejecutar(navegador, aplicacion, cliente, plan, caso, carpeta, turnos):
    contexto_navegador = navegador.new_context(
        viewport={"width": ANCHO, "height": ALTO}, locale="es-ES"
    )
    pagina = contexto_navegador.new_page()

    def abrir():
        pagina.goto(aplicacion.url)
        pagina.wait_for_load_state("networkidle")
        pagina.wait_for_timeout(1000)

    def reiniciar():
        aplicacion.reiniciar()
        abrir()

    try:
        aplicacion.arrancar()
        abrir()
        return ejecutar_caso(
            cliente,
            Navegador(pagina, carpeta),
            reiniciar,
            caso,
            plan.preparacion(caso),
            plan.contexto,
            RAIZ,
            max_turnos=turnos,
        )
    except Exception as error:  # noqa: BLE001 - el resto de casos sigue
        return Resultado(
            caso=caso.id,
            titulo=caso.titulo,
            estado=ERROR,
            resultado_obtenido="Error del probador: "
            + type(error).__name__
            + ": "
            + str(error).splitlines()[0],
        )
    finally:
        contexto_navegador.close()


def combinar(repeticiones):
    """Junta varias ejecuciones del mismo caso en un solo resultado.

    Si todas tienen el mismo estado, se devuelve la primera. Si no, el
    caso queda como "Revisar": el LLM no es fiable en ese caso.
    """
    primera = repeticiones[0]
    estados = []
    for repeticion in repeticiones:
        estados.append(repeticion.estado)
    if len(set(estados)) <= 1:
        return primera
    primera.estado = REVISAR
    primera.resultado_obtenido = (
        "Resultados distintos en "
        + str(len(repeticiones))
        + " ejecuciones ("
        + ", ".join(estados)
        + "). "
        + primera.resultado_obtenido
    )
    return primera


def dataset_d1(texto_plan):
    """Ruta del dataset de ejemplo en CSV (D-1) según el plan, o None."""
    coincidencia = PATRON_D1.search(texto_plan)
    if coincidencia is None or "⟨" in coincidencia.group(1):
        return None
    ruta = RAIZ / coincidencia.group(1)
    if ruta.is_file():
        return ruta
    return None


def commit_actual():
    try:
        salida = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "desconocido"
    return salida.stdout.strip()


def _resultado_sin_ejecutar(caso, opciones):
    """Resultado de un caso que no se ejecuta, o None si se ejecuta."""
    if caso.id in MANUALES:
        return Resultado(
            caso=caso.id,
            titulo=caso.titulo,
            estado=informe.MANUAL,
            resultado_obtenido=MANUALES[caso.id],
        )
    if caso.huecos and not opciones.permitir_huecos:
        return Resultado(
            caso=caso.id,
            titulo=caso.titulo,
            estado=informe.NO_EJECUTADO,
            resultado_obtenido="Faltan valores del plan sin rellenar: "
            + ", ".join(caso.huecos),
        )
    return None


def _avisar_requisitos(casos):
    elegidos = set()
    for caso in casos:
        elegidos.add(caso.id)
    for caso in casos:
        for requisito in caso.requisitos:
            if requisito not in elegidos and not caso.misma_sesion:
                print(
                    "Aviso: "
                    + caso.id
                    + " necesita que "
                    + requisito
                    + " se haya ejecutado antes (crea archivos que usa).",
                    file=sys.stderr,
                )


def _lanzar_navegador(playwright, opciones):
    if opciones.chrome:
        return playwright.chromium.launch(
            channel="chrome", headless=not opciones.ver
        )
    return playwright.chromium.launch(headless=not opciones.ver)
