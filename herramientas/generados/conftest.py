"""Preparación de los tests generados por el LLM (test_plan_llm.py).

Arranca SIKORIUS y un navegador con Playwright una sola vez para todos los
tests, igual que cuando se generaron: con los archivos de prueba en
``data/pruebas/``, ``data/`` como carpeta personal y la ventana de
1366 × 768.

Ejecución, desde la raíz del repositorio:

    uv run --group probador pytest herramientas/generados -v

Variables de entorno opcionales:

- ``SIKORIUS_VER=1``: muestra la ventana del navegador.
- ``SIKORIUS_CHROME=1``: usa el Google Chrome instalado en vez del
  Chromium de Playwright.

Las capturas de cada test quedan en ``data/pruebas_script/<fecha>/``.
"""

import os
from datetime import datetime

import pytest

from probador_llm import datos, ejecutor
from probador_llm.aplicacion import Aplicacion
from probador_llm.reproduccion import Reproductor


def _activada(nombre):
    return os.environ.get(nombre, "") not in ("", "0")


@pytest.fixture(scope="session")
def sikorius():
    """``Reproductor`` con la aplicación y el navegador en marcha."""
    playwright_api = pytest.importorskip(
        "playwright.sync_api",
        reason="Instala el grupo probador: uv sync --group probador",
    )
    raiz = ejecutor.RAIZ
    plan = ejecutor.PLAN_POR_DEFECTO.read_text(encoding="utf-8")
    datos.preparar(raiz / "data", ejecutor.dataset_d1(plan))
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    salida = raiz / "data" / "pruebas_script" / marca
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
        yield Reproductor(aplicacion, contexto.new_page(), salida / "capturas")
        contexto.close()
        navegador.close()
