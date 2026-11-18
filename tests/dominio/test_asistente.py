"""Pruebas del resumen que se manda al asistente.

uv run pytest tests/dominio/test_asistente.py -v
"""

import numpy as np
import pandas as pd

from sikorius.dominio.asistente import (
    MAX_COLUMNAS_CONTEXTO,
    RespuestaAsistente,
    construir_contexto,
)
from sikorius.dominio.modelo import ModeloLineal


def test_sin_nada():
    texto = construir_contexto()
    assert "No hay ningún dataset" in texto
    assert "Todavía no hay modelo" in texto


def test_describe_columnas_sin_mandar_filas():
    df = pd.DataFrame(
        {"precio": [1.0, 2.0, np.nan], "ciudad": ["Secreta", "Lugo", "Lugo"]}
    )
    texto = construir_contexto(df, etapa="Datos")
    assert "3 filas, 2 columnas" in texto
    assert "«precio» (float64), nulos: 1, mín: 1, máx: 2" in texto
    assert "valores distintos: 2" in texto
    assert "Secreta" not in texto  # no se mandan los valores
    assert "pestaña: Datos" in texto


def test_datasets_muy_anchos_se_recortan():
    df = pd.DataFrame({str(i): [1] for i in range(MAX_COLUMNAS_CONTEXTO + 5)})
    assert "(y 5 columnas más)" in construir_contexto(df)


def test_modelo_y_metricas():
    modelo = ModeloLineal(("x",), "y", (2.0,), 1.0, "Pisos")
    metricas = {
        "entrenamiento": {"r2": 0.9, "ecm": 1.5},
        "test": {"r2": float("nan"), "ecm": 2.0},
    }
    texto = construir_contexto(
        seleccion=(("x",), "y"), modelo=modelo, metricas=metricas
    )
    assert "entrada «x»; salida «y»" in texto
    assert "y = " in texto
    assert "Descripción del modelo: Pisos" in texto
    assert "entrenamiento: R² = 0.9, ECM = 1.5" in texto
    assert "R² no disponible" in texto


def test_esquema_estricto():
    """Todos los campos obligatorios y sin campos extra (modo estricto)."""
    esquema = RespuestaAsistente.model_json_schema()
    assert esquema["additionalProperties"] is False
    assert set(esquema["required"]) == {"mensaje", "operaciones"}
    operacion = esquema["$defs"]["Operacion"]
    assert operacion["additionalProperties"] is False
    assert set(operacion["required"]) == set(operacion["properties"])
