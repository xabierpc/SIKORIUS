"""Tests de la sesión: cascada de pasos, avisos y preprocesado.

Ejecutar con: uv run pytest tests/test_sesion.py
"""

import pandas as pd


def test_cargar_dataset_borra_los_pasos_posteriores(sesion_separada):
    sesion_separada.cargar_dataset(pd.DataFrame({"a": [1, 2]}), "otro.csv")
    assert sesion_separada.seleccion is None
    assert sesion_separada.separacion is None
    assert sesion_separada.preprocesado is None


def test_nueva_seleccion_conserva_el_dataset(sesion_separada):
    datos = sesion_separada.dataset.datos
    sesion_separada.guardar_seleccion(["x1"], "y")
    assert sesion_separada.dataset.datos is datos
    assert sesion_separada.separacion is None


def test_tipo_de_regresion_segun_numero_de_entradas(sesion_con_seleccion):
    assert sesion_con_seleccion.seleccion.tipo_regresion == "multiple"
    sesion_con_seleccion.guardar_seleccion(["x1"], "y")
    assert sesion_con_seleccion.seleccion.tipo_regresion == "simple"


def test_avisa_en_cada_cambio_hasta_cancelar(sesion, datos):
    avisos = []
    cancelar = sesion.al_cambiar(lambda: avisos.append("cambio"))
    sesion.cargar_dataset(datos, "datos.csv")
    cancelar()
    sesion.cargar_dataset(datos, "datos.csv")
    assert len(avisos) == 1


def test_preprocesado_con_media_permite_crear_el_modelo(sesion_separada):
    assert not sesion_separada.puede_crear_modelo()
    sesion_separada.aplicar_preprocesado("media")
    assert sesion_separada.puede_crear_modelo()
