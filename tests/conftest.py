"""Fixtures comunes de los tests de SIKORIUS."""

import numpy as np
import pandas as pd
import pytest

from sikorius.nucleo.separacion import separar_datos
from sikorius.sesion import Sesion


@pytest.fixture
def datos():
    return pd.DataFrame(
        {
            "x1": [1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            "x2": [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0, 5.0, 3.0],
            "y": [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0],
        }
    )


@pytest.fixture
def sesion():
    return Sesion()


@pytest.fixture
def sesion_con_seleccion(sesion, datos):
    sesion.cargar_dataset(datos, "datos.csv")
    sesion.guardar_seleccion(["x1", "x2"], "y")
    return sesion


@pytest.fixture
def sesion_separada(sesion_con_seleccion):
    entrenamiento, test = separar_datos(
        sesion_con_seleccion.dataset.datos, 20, 42
    )
    sesion_con_seleccion.guardar_separacion(entrenamiento, test, 20, 42)
    return sesion_con_seleccion
