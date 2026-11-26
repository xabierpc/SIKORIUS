"""Preparación de las pruebas funcionales con Playwright.

Arranca SIKORIUS y un navegador una sola vez para todas las pruebas, con:

- los archivos de prueba del plan (F-1 a F-14) en ``data/pruebas/``;
- ``data/`` como carpeta personal de la aplicación, para que el
  explorador de archivos empiece ahí;
- la ventana de 1366 × 768 (historia #37).

Cada prueba recibe ``ui`` (ver ``sikorius_ui.Sikorius``) y prepara su
propio estado: si una falla, las siguientes no se ven afectadas.

Ejecución, desde la raíz del repositorio:

    uv run --group probador pytest herramientas/funcionales -v

Variables de entorno opcionales:

- ``SIKORIUS_VER=1``: muestra la ventana del navegador.
- ``SIKORIUS_CHROME=1``: usa el Google Chrome instalado en vez del
  Chromium de Playwright.

Las capturas de cada prueba quedan en ``data/pruebas_funcionales/<fecha>/``.
"""

import os
from datetime import datetime

import pytest

from funcionales.sikorius_ui import Sikorius
from probador_llm import datos, ejecutor
from probador_llm.aplicacion import Aplicacion

DATASETS = ("housing1.csv", "housing.xlsx", "housing.db")


def _activada(nombre):
    return os.environ.get(nombre, "") not in ("", "0")


@pytest.fixture(scope="session")
def _sikorius():
    playwright_api = pytest.importorskip(
        "playwright.sync_api",
        reason="Instala el grupo probador: uv sync --group probador",
    )
    raiz = ejecutor.RAIZ
    plan = ejecutor.PLAN_POR_DEFECTO.read_text(encoding="utf-8")
    datos.preparar(raiz / "data", ejecutor.dataset_d1(plan))
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    salida = raiz / "data" / "pruebas_funcionales" / marca
    aplicacion = Aplicacion(
        raiz, salida / "aplicacion.log", carpeta_personal=raiz / "data"
    )
    with aplicacion, playwright_api.sync_playwright() as playwright:
        opciones = {"headless": not _activada("SIKORIUS_VER")}
        if _activada("SIKORIUS_CHROME"):
            opciones["channel"] = "chrome"
        navegador = playwright.chromium.launch(**opciones)
        contexto = navegador.new_context(
            viewport={"width": ejecutor.ANCHO, "height": ejecutor.ALTO},
            locale="es-ES",
        )
        sikorius = Sikorius(
            aplicacion, contexto.new_page(), salida / "capturas"
        )
        sikorius.reiniciar()
        yield sikorius
        contexto.close()
        navegador.close()


@pytest.fixture
def ui(_sikorius, request):
    """La aplicación lista para una prueba (sin diálogos ni mensajes)."""
    _sikorius.empezar_test(request.node.name)
    yield _sikorius
    _sikorius.capturar("final")


@pytest.fixture
def d1(ui):
    """Exige que los datasets de ejemplo estén en data/."""
    faltan = []
    for nombre in DATASETS:
        if not (ejecutor.RAIZ / "data" / nombre).is_file():
            faltan.append("data/" + nombre)
    if faltan:
        pytest.skip("Faltan los datasets de ejemplo: " + ", ".join(faltan))
    return ui
