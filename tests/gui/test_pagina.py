"""Pruebas de los paneles trabajando juntos, sin servidor.

Los paneles no se llaman entre ellos: cada uno está suscrito a la sesión.
Estos tests montan todos los paneles sobre la misma sesión y comprueban
que, al cambiar un paso, los demás se actualizan solos (antes eso dependía
de callbacks como ``al_separar`` o ``al_aplicar``).

uv run pytest tests/gui/test_pagina.py -v
"""

import pytest
from nicegui import ui

from sikorius.gui.pagina import TITULOS, Pestanas, construir_pagina
from sikorius.gui.paneles.panel_columnas import PanelColumnas
from sikorius.gui.paneles.panel_dataset import PanelDataset
from sikorius.gui.paneles.panel_preprocesado import PanelPreprocesado
from sikorius.gui.paneles.panel_separacion import PanelSeparacion
from sikorius.nucleo.separacion import separar_datos


@pytest.fixture(autouse=True)
def sin_avisos(monkeypatch):
    """Los ui.notify no se muestran: solo interesan los paneles."""
    monkeypatch.setattr(ui, "notify", lambda *args, **kwargs: None)


class Pagina:
    """Los mismos paneles que coloca construir_pagina, a mano para poder
    mirarlos desde el test."""

    def __init__(self, sesion):
        self.dataset = PanelDataset(sesion)
        self.columnas = PanelColumnas(sesion)
        self.separacion = PanelSeparacion(sesion)
        self.preprocesado = PanelPreprocesado(sesion)


def test_construir_pagina_no_falla_y_se_puede_repetir(sesion_separada):
    """Abrir dos pestañas (o recargar) sobre la misma sesión."""
    construir_pagina(sesion_separada)
    construir_pagina(sesion_separada)
    # La sesión avisa a los paneles de las dos páginas sin fallar
    sesion_separada.aplicar_preprocesado("media")
    assert sesion_separada.preprocesado.estrategia == "media"


def test_todo_el_flujo_sin_conectar_paneles(sesion, datos):
    pagina = Pagina(sesion)

    # Cargar: se llenan los selectores; separar aún no está disponible
    sesion.cargar_dataset(datos, "datos.csv")
    assert pagina.columnas.features.columnas == ["x1", "x2", "y"]
    assert not pagina.separacion.boton_separar.enabled

    # Confirmar columnas: se habilita la separación
    pagina.columnas.features.selector.set_value(["x1", "x2"])
    pagina.columnas.target.selector.set_value("y")
    pagina.columnas.confirmar()
    assert pagina.separacion.boton_separar.enabled
    assert not pagina.preprocesado.tabla.visible

    # Separar: el preprocesado detecta los nulos sin que nadie lo llame
    pagina.separacion.separar()
    assert pagina.preprocesado.tabla.visible
    assert pagina.preprocesado.controles.visible

    # Aplicar: ya se podría crear el modelo
    pagina.preprocesado.estrategia.set_value("media")
    pagina.preprocesado.aplicar()
    assert sesion.puede_crear_modelo()


def test_cargar_otro_dataset_limpia_los_pasos(sesion_separada, datos):
    pagina = Pagina(sesion_separada)

    sesion_separada.cargar_dataset(datos, "otro.csv")

    assert pagina.columnas.etiqueta_seleccion.text == ""
    assert pagina.separacion.etiqueta_resultado.text == ""
    assert not pagina.separacion.boton_separar.enabled
    assert not pagina.preprocesado.tabla.visible


def test_al_recargar_cada_panel_muestra_su_paso(sesion, datos):
    antes = Pagina(sesion)
    sesion.cargar_dataset(datos, "datos.csv")
    antes.columnas.features.selector.set_value(["x1", "x2"])
    antes.columnas.target.selector.set_value("y")
    antes.columnas.confirmar()
    antes.separacion.entrada_porcentaje.set_value("30")
    antes.separacion.entrada_semilla.set_value("7")
    antes.separacion.separar()
    antes.preprocesado.estrategia.set_value("mediana")
    antes.preprocesado.aplicar()

    despues = Pagina(sesion)  # F5

    assert despues.dataset.etiqueta_resumen.text == "10 filas y 3 columnas"
    assert despues.columnas.features.obtener_seleccion() == ["x1", "x2"]
    assert despues.columnas.target.obtener_seleccion() == "y"
    assert despues.separacion.entrada_porcentaje.value == "30"
    assert despues.separacion.entrada_semilla.value == "7"
    assert despues.preprocesado.estrategia.value == "mediana"
    assert despues.preprocesado.aplicado.text.startswith("Aplicado:")


# =============================================================================
# Pestañas con desbloqueo progresivo
# =============================================================================


def pestanas_activas(pestanas):
    return [e for e, p in pestanas.pestanas.items() if p.enabled]


def test_pestanas_al_empezar_solo_datos(sesion):
    pestanas = Pestanas(sesion)
    assert pestanas_activas(pestanas) == ["datos"]
    assert pestanas.paneles.value == "datos"


def test_pestanas_se_desbloquean_con_el_flujo(sesion, datos):
    pestanas = Pestanas(sesion)
    sesion.cargar_dataset(datos, "datos.csv")
    assert pestanas_activas(pestanas) == ["datos", "variables"]
    sesion.guardar_seleccion(["x1", "x2"], "y")
    entrenamiento, test = separar_datos(sesion.dataset.datos, 20, 42)
    sesion.guardar_separacion(entrenamiento, test, 20, 42)
    assert pestanas_activas(pestanas) == ["datos", "variables", "preprocesado"]
    sesion.aplicar_preprocesado("media")
    assert pestanas_activas(pestanas) == list(TITULOS)


def test_pestanas_si_se_cierra_la_que_se_ve_se_va_a_la_ultima_abierta(
    sesion_separada, datos
):
    sesion_separada.aplicar_preprocesado("media")
    pestanas = Pestanas(sesion_separada)
    pestanas.paneles.set_value("modelo")

    sesion_separada.cargar_dataset(datos, "otro.csv")

    assert pestanas.paneles.value == "variables"


def test_pestanas_no_mueven_al_usuario_si_su_pestana_sigue_abierta(
    sesion_separada,
):
    pestanas = Pestanas(sesion_separada)
    pestanas.paneles.set_value("preprocesado")

    sesion_separada.aplicar_preprocesado("media")

    assert pestanas.paneles.value == "preprocesado"
