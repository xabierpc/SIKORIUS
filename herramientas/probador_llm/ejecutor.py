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
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from probador_llm import datos, generador, informe
from probador_llm.agente import (
    CORRECTO,
    ERROR,
    FALLIDO,
    REVISAR,
    Resultado,
    ejecutar_caso,
)
from probador_llm.aplicacion import Aplicacion
from probador_llm.cliente_groq import (
    MODELO_POR_DEFECTO,
    RAZONAMIENTO_POR_DEFECTO,
    ClienteGroq,
    ErrorClave,
    LimiteDiario,
    leer_clave,
)
from probador_llm.navegador import Navegador
from probador_llm.plan import elegir_casos, leer_plan

RAIZ = Path(__file__).resolve().parents[2]
PLAN_POR_DEFECTO = RAIZ / "docs" / "plan_pruebas.md"
SCRIPT_GENERADO = RAIZ / "herramientas" / "generados" / "test_plan_llm.py"

# Tamaño de la ventana del navegador: el mínimo que pide la historia #37
ANCHO = 1366
ALTO = 768

# Casos que no tiene sentido hacer con el LLM, con el motivo
MANUALES = {
    "CP-44": "Hay que abrir el CSV con una hoja de cálculo.",
    "CP-59": "Hay que abrir el modelo guardado (.json) con un editor de "
    "texto.",
    "CP-84": "Compara los mensajes de otros casos: se revisa con el "
    "registro de la ejecución.",
    "CP-85": "Que la ventana no se bloquee se juzga moviéndola a mano.",
    "CP-86": "La fluidez del desplazamiento la juzga una persona.",
    "CP-88": "Hay que redimensionar la ventana del sistema operativo.",
    "CP-89": "El asistente no está en dev: se prueba a mano.",
    "CP-90": "El asistente no está en dev: se prueba a mano.",
    "CP-91": "El asistente no está en dev: se prueba a mano.",
    "CP-92": "Hay que renombrar el archivo .env.",
}

# "| D-1 (CSV) | `data/archivo.csv` |" en la sección de datos de prueba
PATRON_DATASET = re.compile(r"^\|\s*(D-\d)[^|]*\|\s*`([^`]+)`", re.MULTILINE)
# Menciones a un dataset de ejemplo en un caso ("D-1", "F-11", que es una
# copia de D-1)
PATRON_MENCION = re.compile(r"\b(D-\d|F-11)\b")


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
        "--razonamiento",
        default=RAZONAMIENTO_POR_DEFECTO,
        choices=("low", "medium", "high"),
        help="Esfuerzo de razonamiento de los modelos gpt-oss. 'low' gasta "
        "menos tokens.",
    )
    analizador.add_argument(
        "--repeticiones",
        type=int,
        default=1,
        help="Veces que se ejecuta cada caso. Si los resultados no "
        "coinciden, el caso queda como 'Revisar'. Con más de una, cada "
        "caso se ejecuta por separado (reiniciando la aplicación).",
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
    cliente = ClienteGroq(
        clave, modelo=opciones.modelo, razonamiento=opciones.razonamiento
    )

    datos.preparar(RAIZ / "data", dataset_d1(texto_plan))
    rutas = datasets(texto_plan)

    if opciones.salida:
        salida = Path(opciones.salida).resolve()
    else:
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        salida = RAIZ / "data" / "pruebas_llm" / marca
    salida.mkdir(parents=True, exist_ok=True)

    datos_ejecucion = {
        "modelo": opciones.modelo
        + " (razonamiento "
        + opciones.razonamiento
        + ")",
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
    aplicacion = Aplicacion(
        RAIZ, salida / "aplicacion.log", carpeta_personal=RAIZ / "data"
    )
    with aplicacion, sync_playwright() as playwright:
        navegador = _lanzar_navegador(playwright, opciones)
        contexto_navegador = navegador.new_context(
            viewport={"width": ANCHO, "height": ALTO}, locale="es-ES"
        )
        sesion = Sesion(aplicacion, contexto_navegador.new_page())
        independientes = opciones.repeticiones > 1
        orden = plan.orden(casos)
        try:
            _ejecutar_todos(
                orden,
                sesion,
                cliente,
                plan,
                opciones,
                rutas,
                salida,
                resultados,
                datos_ejecucion,
                independientes,
            )
        except (ErrorClave, NavegadorCerrado) as error:
            print("Ejecución detenida: " + str(error), file=sys.stderr)
            if resultados:
                informe.escribir(salida, resultados, datos_ejecucion)
                escribir_script(resultados, datos_ejecucion, salida)
            return 1
        registro = salida / "registro.md"
        contexto_navegador.close()
        navegador.close()

    cuentas = informe.contar(resultados)
    resumen = []
    for estado, numero in cuentas.items():
        if numero:
            resumen.append(estado + " " + str(numero))
    print("Resumen: " + ", ".join(resumen))
    print("Registro: " + str(registro))
    script = escribir_script(resultados, datos_ejecucion, salida)
    print("Script de Playwright generado: " + str(script.relative_to(RAIZ)))
    print(
        "Para ejecutarlo sin LLM:\n  uv run --group probador pytest "
        "herramientas/generados -v"
    )
    if sesion.agotado:
        print(
            "Se ha agotado el límite diario de Groq. Para seguir otro día "
            "con los casos que faltan:\n  uv run --group probador python "
            "herramientas/probar_con_llm.py --casos "
            + ",".join(sesion.pendientes)
        )
        return 2
    return 0


def escribir_script(resultados, datos_ejecucion, salida):
    """Escribe el script de Playwright de la ejecución.

    Se guarda en ``herramientas/generados/test_plan_llm.py`` (para subirlo
    al repositorio) y una copia en la carpeta de la ejecución.
    """
    diccionarios = []
    for resultado in resultados:
        diccionarios.append(asdict(resultado))
    codigo = generador.generar(diccionarios, datos_ejecucion)
    SCRIPT_GENERADO.parent.mkdir(parents=True, exist_ok=True)
    SCRIPT_GENERADO.write_text(codigo, encoding="utf-8")
    (salida / "test_plan_llm.py").write_text(codigo, encoding="utf-8")
    return SCRIPT_GENERADO


def _ejecutar_todos(
    orden,
    sesion,
    cliente,
    plan,
    opciones,
    rutas,
    salida,
    resultados,
    datos_ejecucion,
    independientes,
):
    """Ejecuta los casos en orden y reescribe el registro tras cada uno.

    Los resultados se van añadiendo a ``resultados``, para que se conserven
    aunque la ejecución se detenga a medias.
    """
    for posicion, caso in enumerate(orden):
        resultado = _resultado_sin_ejecutar(
            caso, opciones, datasets_que_faltan(plan, caso, rutas)
        )
        if resultado is None and sesion.agotado:
            resultado = Resultado(
                caso=caso.id,
                titulo=caso.titulo,
                estado=informe.NO_EJECUTADO,
                resultado_obtenido="Límite diario de Groq agotado.",
            )
        if resultado is None:
            repeticiones = []
            for numero in range(max(1, opciones.repeticiones)):
                carpeta = salida / "capturas" / caso.id
                if numero > 0:
                    carpeta = carpeta / ("repeticion_" + str(numero + 1))
                repeticiones.append(
                    sesion.ejecutar(
                        cliente,
                        plan,
                        caso,
                        carpeta,
                        opciones.max_turnos,
                        independientes,
                    )
                )
            resultado = combinar(repeticiones)
        resultados.append(resultado)
        print(caso.id + ": " + resultado.estado, flush=True)
        informe.escribir(salida, resultados, datos_ejecucion)
        if sesion.agotado and sesion.pendientes is None:
            sesion.pendientes = []
            for pendiente in orden[posicion:]:
                sesion.pendientes.append(pendiente.id)


class Sesion:
    """La aplicación y la pestaña del navegador, compartidas entre casos.

    Los casos son aditivos: la aplicación no se cierra entre uno y otro, y
    cada caso parte de lo que dejó el anterior. Solo se reinicia cuando:

    - el caso pide la aplicación recién abierta;
    - es el primer caso, o el anterior terminó con un error del probador;
    - el caso continúa a otro ("sin cerrar la aplicación") que no es el que
      se acaba de ejecutar o que no terminó bien. Entonces, además, se
      repiten antes los pasos de ese otro caso (preparación).

    Attributes:
        ultimo: (id, estado) del último caso ejecutado, o None.
        agotado: True si Groq ha dicho que se ha agotado el límite diario.
        pendientes: Casos que faltaban cuando se agotó el límite.
    """

    def __init__(self, aplicacion, pagina):
        self.aplicacion = aplicacion
        self.pagina = pagina
        self.ultimo = None
        self.agotado = False
        self.pendientes = None

    def abrir(self):
        self.pagina.goto(self.aplicacion.url)
        self.pagina.wait_for_load_state("networkidle")
        self.pagina.wait_for_timeout(1000)

    def reiniciar(self):
        self.aplicacion.reiniciar()
        self.abrir()

    def ejecutar(self, cliente, plan, caso, carpeta, turnos, independiente):
        """Ejecuta un caso y devuelve su ``Resultado``."""
        try:
            continuar, preparacion = decidir_inicio(
                plan,
                caso,
                self.ultimo,
                self.aplicacion.en_marcha,
                independiente,
            )
            navegador = Navegador(self.pagina, carpeta)
            if continuar:
                navegador.limpiar()
                estado_inicial = (
                    "La aplicación sigue abierta tal como la dejó el caso "
                    "anterior (" + self.ultimo[0] + "). No la reinicies."
                )
            else:
                self.reiniciar()
                estado_inicial = (
                    "La aplicación está recién abierta (PR-1 hecho)."
                )
            resultado = ejecutar_caso(
                cliente,
                navegador,
                self.reiniciar,
                caso,
                preparacion,
                plan.contexto,
                RAIZ,
                max_turnos=turnos,
                referencias=plan.referencias(caso),
                estado_inicial=estado_inicial,
            )
            resultado.reiniciado = not continuar
        except ErrorClave:
            # Sin clave válida no se puede ejecutar ningún caso: se para
            raise
        except Exception as error:  # noqa: BLE001 - el resto de casos sigue
            if _navegador_cerrado(error):
                raise NavegadorCerrado(
                    "Se ha cerrado el navegador durante las pruebas."
                ) from error
            if isinstance(error, LimiteDiario):
                self.agotado = True
                return Resultado(
                    caso=caso.id,
                    titulo=caso.titulo,
                    estado=informe.NO_EJECUTADO,
                    resultado_obtenido="Límite diario de Groq agotado.",
                )
            resultado = Resultado(
                caso=caso.id,
                titulo=caso.titulo,
                estado=ERROR,
                resultado_obtenido="Error del probador: "
                + type(error).__name__
                + ": "
                + str(error).splitlines()[0],
            )
        self.ultimo = (caso.id, resultado.estado)
        return resultado


class NavegadorCerrado(Exception):
    """El navegador se ha cerrado: no se pueden ejecutar más casos."""


def _navegador_cerrado(error):
    return type(error).__name__ == "TargetClosedError" or (
        "has been closed" in str(error)
    )


# Estados del caso anterior con los que el siguiente puede continuar: la
# aplicación ha quedado en un estado conocido
CONTINUABLES = (CORRECTO, FALLIDO, REVISAR)


def decidir_inicio(plan, caso, ultimo, en_marcha, independiente=False):
    """Decide cómo empieza un caso.

    Args:
        plan: El plan.
        caso: El caso que se va a ejecutar.
        ultimo: (id, estado) del último caso ejecutado, o None.
        en_marcha: Si la aplicación está abierta.
        independiente: Si se pide ejecutar cada caso por separado (por
            ejemplo, al repetirlos): siempre se reinicia.

    Returns:
        (continuar, preparacion): ``continuar`` es True si se sigue con la
        aplicación tal como está; ``preparacion``, los casos cuyos pasos hay
        que repetir antes (solo si no se continúa).
    """
    anterior_bien = (
        ultimo is not None and en_marcha and ultimo[1] in CONTINUABLES
    )
    padre = plan.padre(caso)
    if padre is not None:
        if not independiente and anterior_bien and ultimo[0] == padre.id:
            return True, []
        return False, plan.preparacion(caso)
    if independiente or caso.reinicio or not anterior_bien:
        return False, []
    return True, []


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


def datasets(texto_plan):
    """Diccionario D-n -> ruta de los datasets de ejemplo según el plan."""
    rutas = {}
    for coincidencia in PATRON_DATASET.finditer(texto_plan):
        rutas[coincidencia.group(1)] = RAIZ / coincidencia.group(2)
    return rutas


def dataset_d1(texto_plan):
    """Ruta del dataset de ejemplo en CSV (D-1) si existe, o None."""
    ruta = datasets(texto_plan).get("D-1")
    if ruta is None or "⟨" in str(ruta) or not ruta.is_file():
        return None
    return ruta


def datasets_que_faltan(plan, caso, rutas):
    """Datasets de ejemplo que usa el caso (o su preparación) y no están.

    Un caso que usa un dataset que no está en ``data/`` no se puede
    ejecutar: el agente no lo encontraría y acabaría bloqueado.
    """
    textos = [caso.texto]
    for previo in plan.preparacion(caso):
        textos.append(previo.texto)
    for citado in plan.referencias(caso):
        textos.append(citado.texto)
    faltan = []
    for texto in textos:
        for mencion in PATRON_MENCION.findall(texto):
            if mencion == "F-11":
                mencion = "D-1"
            ruta = rutas.get(mencion)
            if ruta is None:
                continue
            if "⟨" in str(ruta) or not ruta.is_file():
                nombre = ruta.relative_to(RAIZ).as_posix()
                if nombre not in faltan:
                    faltan.append(nombre)
    return faltan


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


def _resultado_sin_ejecutar(caso, opciones, faltan):
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
    if faltan:
        return Resultado(
            caso=caso.id,
            titulo=caso.titulo,
            estado=informe.NO_EJECUTADO,
            resultado_obtenido="Falta el dataset de ejemplo: "
            + ", ".join(faltan)
            + " (cópialo en data/).",
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
