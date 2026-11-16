"""Pruebas del panel de carga del dataset, sin servidor.

uv run pytest tests/gui/test_panel_dataset.py -v
"""

import asyncio
from pathlib import Path

import pytest
from nicegui import ui

from sikorius.dominio.separacion import separar_datos
from sikorius.gui.componentes import carga_modelo
from sikorius.gui.paneles import panel_dataset
from sikorius.gui.paneles.panel_dataset import PanelDataset, carpeta_inicial


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


# --- Botón "Cargar modelo" (historia #24) ---


def modelo_guardado(sesion_separada, ruta):
    """Crea y guarda un modelo con la sesión de los fixtures."""
    sesion_separada.aplicar_preprocesado("media")
    sesion_separada.crear_modelo()
    return sesion_separada.guardar_modelo(ruta)


def responder_confirmacion(monkeypatch, respuesta):
    """La confirmación responde sola; devuelve la lista de mensajes."""
    mensajes = []

    async def falsa(titulo, mensaje, texto_aceptar="Aceptar"):
        mensajes.append(mensaje)
        return respuesta

    monkeypatch.setattr(carga_modelo, "confirmar", falsa)
    return mensajes


def test_el_inicio_tiene_el_boton_cargar_modelo(sesion):
    panel = PanelDataset(sesion)
    assert panel.boton_cargar_modelo.text == "Cargar modelo"
    assert panel.boton_cargar_modelo.enabled


def test_con_datos_tambien_se_puede_cargar_un_modelo(sesion, datos):
    sesion.cargar_dataset(datos, "datos.csv")
    panel = PanelDataset(sesion)
    assert panel.boton_otro_modelo.text == "Cargar modelo"


def test_el_boton_carga_el_modelo(
    sesion, sesion_separada, tmp_path, monkeypatch, avisos
):
    ruta = modelo_guardado(sesion_separada, tmp_path / "m.json")

    async def explorador_falso(_carpeta, **kwargs):
        return str(ruta)

    monkeypatch.setattr(carga_modelo, "seleccionar_archivo", explorador_falso)
    panel = PanelDataset(sesion)

    asyncio.run(panel.cargar_modelo())

    assert sesion.modelo_cargado
    assert panel.inicio.visible  # no hay datos: sigue el inicio
    assert avisos[-1][1] == "positive"


def test_cargar_dataset_con_modelo_cargado_con_cambios_pregunta(
    sesion, sesion_separada, tmp_path, monkeypatch, avisos
):
    sesion.cargar_modelo(modelo_guardado(sesion_separada, tmp_path / "m.json"))
    sesion.guardar_descripcion("Cambiada")
    mensajes = responder_confirmacion(monkeypatch, False)
    archivo = tmp_path / "pisos.csv"
    archivo.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
    elegir_en_explorador(monkeypatch, str(archivo))
    panel = PanelDataset(sesion)

    asyncio.run(panel.cargar())

    assert len(mensajes) == 1
    assert sesion.modelo_cargado
    assert sesion.dataset is None


def test_si_confirma_el_dataset_sustituye_al_modelo_cargado(
    sesion, sesion_separada, tmp_path, monkeypatch, avisos
):
    sesion.cargar_modelo(modelo_guardado(sesion_separada, tmp_path / "m.json"))
    sesion.guardar_descripcion("Cambiada")
    responder_confirmacion(monkeypatch, True)
    archivo = tmp_path / "pisos.csv"
    archivo.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
    elegir_en_explorador(monkeypatch, str(archivo))
    panel = PanelDataset(sesion)

    asyncio.run(panel.cargar())

    assert sesion.modelo is None
    assert sesion.dataset is not None
    assert panel.contenido.visible


def test_modelo_cargado_sin_cambios_no_pregunta(
    sesion, sesion_separada, tmp_path, monkeypatch, avisos
):
    sesion.cargar_modelo(modelo_guardado(sesion_separada, tmp_path / "m.json"))
    mensajes = responder_confirmacion(monkeypatch, False)
    archivo = tmp_path / "pisos.csv"
    archivo.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
    elegir_en_explorador(monkeypatch, str(archivo))

    asyncio.run(PanelDataset(sesion).cargar())

    assert mensajes == []
    assert sesion.dataset is not None


def test_modelo_creado_sin_guardar_no_cambia_la_carga_de_datasets(
    sesion_separada, tmp_path, monkeypatch, avisos
):
    """La confirmación es solo para modelos cargados (criterio de #24)."""
    sesion_separada.aplicar_preprocesado("media")
    sesion_separada.crear_modelo()
    mensajes = responder_confirmacion(monkeypatch, False)
    archivo = tmp_path / "pisos.csv"
    archivo.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
    elegir_en_explorador(monkeypatch, str(archivo))

    asyncio.run(PanelDataset(sesion_separada).cargar())

    assert mensajes == []
    assert sesion_separada.modelo is None
