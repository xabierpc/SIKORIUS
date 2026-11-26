"""Pruebas de la pantalla de inicio, sin servidor.

uv run pytest tests/gui/test_panel_inicio.py -v
"""

import asyncio

import pytest
from nicegui import ui

from sikorius.gui.componentes import carga_dataset, carga_modelo
from sikorius.gui.pagina import Pestanas
from sikorius.gui.paneles.panel_inicio import PanelInicio


@pytest.fixture
def avisos(monkeypatch):
    """Recoge los ui.notify (mensaje, tipo) en lugar de mostrarlos."""
    lista = []

    def anotar(mensaje, **kw):
        lista.append((mensaje, kw.get("type")))

    monkeypatch.setattr(ui, "notify", anotar)
    return lista


def elegir_dataset(monkeypatch, ruta):
    """El explorador de datasets devuelve ruta sin abrir ningún diálogo."""

    async def explorador_falso(_carpeta):
        return ruta

    monkeypatch.setattr(carga_dataset, "seleccionar_archivo", explorador_falso)


def elegir_modelo(monkeypatch, ruta):
    """El explorador de modelos devuelve ruta sin abrir ningún diálogo."""

    async def explorador_falso(_carpeta, **kwargs):
        return ruta

    monkeypatch.setattr(carga_modelo, "seleccionar_archivo", explorador_falso)


def modelo_guardado(sesion_separada, ruta):
    sesion_separada.aplicar_preprocesado("media")
    sesion_separada.crear_modelo()
    return sesion_separada.guardar_modelo(ruta)


def test_tiene_los_dos_botones(sesion):
    panel = PanelInicio(sesion)
    assert panel.boton_cargar.text == "Subir dataset"
    assert panel.boton_cargar_modelo.text == "Cargar modelo"
    assert panel.boton_cargar.enabled
    assert panel.boton_cargar_modelo.enabled


def test_subir_dataset_lo_carga_y_lleva_a_datos(
    sesion, tmp_path, monkeypatch, avisos
):
    archivo = tmp_path / "pisos.csv"
    archivo.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
    elegir_dataset(monkeypatch, str(archivo))
    pestanas = Pestanas(sesion)
    panel = PanelInicio(sesion)

    asyncio.run(panel.cargar())

    assert sesion.dataset.ruta == str(archivo.resolve())
    assert pestanas.paneles.value == "datos"
    assert avisos == [("Dataset cargado correctamente", "positive")]


def test_cerrar_el_explorador_se_queda_en_el_inicio(
    sesion, monkeypatch, avisos
):
    elegir_dataset(monkeypatch, None)
    pestanas = Pestanas(sesion)

    asyncio.run(PanelInicio(sesion).cargar())

    assert sesion.dataset is None
    assert pestanas.paneles.value == "inicio"
    assert avisos == []


def test_un_archivo_malo_se_queda_en_el_inicio(
    sesion, tmp_path, monkeypatch, avisos
):
    vacio = tmp_path / "vacio.csv"
    vacio.write_text("", encoding="utf-8")
    elegir_dataset(monkeypatch, str(vacio))
    pestanas = Pestanas(sesion)

    asyncio.run(PanelInicio(sesion).cargar())

    assert sesion.dataset is None
    assert pestanas.paneles.value == "inicio"
    assert avisos[-1][1] == "negative"


def test_cargar_modelo_lleva_a_modelo_y_no_a_datos(
    sesion, sesion_separada, tmp_path, monkeypatch, avisos
):
    ruta = modelo_guardado(sesion_separada, tmp_path / "m.json")
    elegir_modelo(monkeypatch, str(ruta))
    pestanas = Pestanas(sesion)

    asyncio.run(PanelInicio(sesion).cargar_modelo())

    assert sesion.modelo_cargado
    assert pestanas.paneles.value == "modelo"
    assert not pestanas.pestanas["datos"].visible
    assert pestanas.pestanas["inicio"].visible
    assert avisos[-1][1] == "positive"


def test_desde_el_inicio_un_dataset_sustituye_al_modelo_cargado(
    sesion, sesion_separada, tmp_path, monkeypatch, avisos
):
    sesion.cargar_modelo(modelo_guardado(sesion_separada, tmp_path / "m.json"))
    archivo = tmp_path / "pisos.csv"
    archivo.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
    elegir_dataset(monkeypatch, str(archivo))
    pestanas = Pestanas(sesion)
    pestanas.paneles.set_value("inicio")

    asyncio.run(PanelInicio(sesion).cargar())

    assert not sesion.modelo_cargado
    assert pestanas.paneles.value == "datos"
