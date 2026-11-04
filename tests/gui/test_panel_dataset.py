"""Pruebas del panel de carga del dataset, sin servidor.

uv run pytest tests/gui/test_panel_dataset.py -v
"""

import asyncio
from pathlib import Path

import pytest
from nicegui import ui

from sikorius.gui.paneles import panel_dataset
from sikorius.gui.paneles.panel_dataset import PanelDataset, carpeta_inicial
from sikorius.nucleo.separacion import separar_datos


@pytest.fixture
def avisos(monkeypatch):
    """Recoge los ui.notify (mensaje, tipo) en lugar de mostrarlos."""
    lista = []

    def anotar(mensaje, **kw):
        lista.append((mensaje, kw.get("type")))

    monkeypatch.setattr(ui, "notify", anotar)
    return lista


def elegir_en_explorador(monkeypatch, ruta):
    """Hace que el explorador devuelva ruta sin abrir ningún diálogo."""

    async def explorador_falso(_carpeta):
        return ruta

    monkeypatch.setattr(panel_dataset, "seleccionar_archivo", explorador_falso)


# --- carpeta_inicial (antes en pagina.py, con el estado global) ---


def test_sin_datos_empieza_en_carpeta_personal(sesion):
    assert Path(carpeta_inicial(sesion)) == Path.home()


def test_no_depende_de_la_carpeta_de_ejecucion(sesion, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert Path(carpeta_inicial(sesion)) == Path.home()


def test_despues_de_cargar_empieza_en_su_carpeta(sesion, datos, tmp_path):
    carpeta = tmp_path / "Mis datos ñandú"
    carpeta.mkdir()
    sesion.cargar_dataset(datos, carpeta / "datos.csv")
    assert Path(carpeta_inicial(sesion)) == carpeta.resolve()


# --- Lo que muestra el panel ---


def test_sin_dataset(sesion):
    panel = PanelDataset(sesion)
    assert panel.etiqueta_ruta.text == "Ningún archivo cargado"
    assert panel.etiqueta_resumen.text == ""
    assert panel.tabla.tabla.rows == []


def test_se_actualiza_solo_al_cargar(sesion, datos):
    panel = PanelDataset(sesion)
    sesion.cargar_dataset(datos, "datos.csv")
    assert panel.etiqueta_ruta.text == str(Path("datos.csv").resolve())
    assert panel.etiqueta_resumen.text == "10 filas y 3 columnas"
    assert len(panel.tabla.tabla.rows) == 10


def test_al_recargar_la_pagina_muestra_lo_cargado(sesion, datos):
    sesion.cargar_dataset(datos, "datos.csv")
    panel = PanelDataset(sesion)
    assert panel.etiqueta_resumen.text == "10 filas y 3 columnas"
    assert len(panel.tabla.tabla.rows) == 10


def test_los_pasos_siguientes_no_redibujan_la_tabla(
    sesion, datos, monkeypatch
):
    panel = PanelDataset(sesion)
    sesion.cargar_dataset(datos, "datos.csv")
    veces = []
    monkeypatch.setattr(panel.tabla, "mostrar", veces.append)

    sesion.guardar_seleccion(["x1", "x2"], "y")
    entrenamiento, test = separar_datos(sesion.dataset.datos, 20, 42)
    sesion.guardar_separacion(entrenamiento, test, 20, 42)
    assert veces == []

    sesion.cargar_dataset(datos, "otro.csv")
    assert len(veces) == 1


# --- Botón "Cargar dataset" ---


def test_cargar_archivo_valido(sesion, tmp_path, monkeypatch, avisos):
    archivo = tmp_path / "pisos.csv"
    archivo.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
    elegir_en_explorador(monkeypatch, str(archivo))
    panel = PanelDataset(sesion)

    asyncio.run(panel.cargar())

    assert sesion.dataset.ruta == str(archivo.resolve())
    assert panel.etiqueta_resumen.text == "2 filas y 2 columnas"
    assert avisos == [("Dataset cargado correctamente", "positive")]


def test_cargar_archivo_malo_conserva_el_anterior(
    sesion, datos, tmp_path, monkeypatch, avisos
):
    sesion.cargar_dataset(datos, "datos.csv")
    anterior = sesion.dataset
    vacio = tmp_path / "vacio.csv"
    vacio.write_text("", encoding="utf-8")
    elegir_en_explorador(monkeypatch, str(vacio))
    panel = PanelDataset(sesion)

    asyncio.run(panel.cargar())

    assert sesion.dataset is anterior
    assert panel.etiqueta_resumen.text == "10 filas y 3 columnas"
    assert avisos[-1][1] == "negative"


def test_cerrar_el_explorador_no_cambia_nada(sesion, monkeypatch, avisos):
    elegir_en_explorador(monkeypatch, None)
    panel = PanelDataset(sesion)

    asyncio.run(panel.cargar())

    assert sesion.dataset is None
    assert avisos == []
