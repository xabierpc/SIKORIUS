"""Valores que no son JSON en la tabla del dataset (fechas, BLOB...)."""

import decimal

import pandas as pd
from nicegui import json as njson

from sikorius.gui.componentes.tabla_datos import dataframe_a_tabla


def test_tipos_que_no_son_json_se_muestran_como_texto():
    df = pd.DataFrame(
        {
            "foto": [b"\x00\x01", None],
            "duracion": pd.to_timedelta([1, None], unit="h"),
            "fecha": pd.to_datetime(["2024-01-01", None]),
            "precio": [decimal.Decimal("1.50"), None],
        }
    )
    _, filas = dataframe_a_tabla(df)
    njson.dumps(filas)  # lo que hace NiceGUI al enviarlo: no debe fallar
    assert filas[0]["c0"] == "<binario: 2 bytes>"
    assert filas[0]["c1"] == "0 days 01:00:00"
    assert filas[0]["c2"] == "2024-01-01 00:00:00"
    assert filas[0]["c3"] == "1.50"
    assert filas[1]["c0"] is None
    assert filas[1]["c2"] is None


def test_los_numeros_siguen_siendo_numeros():
    df = pd.DataFrame({"x": [1, 2], "y": [1.5, None], "ok": [True, False]})
    _, filas = dataframe_a_tabla(df)
    assert filas[0]["c0"] == 1
    assert filas[0]["c1"] == 1.5
    assert filas[1]["c1"] is None
    assert filas[0]["c2"] is True
