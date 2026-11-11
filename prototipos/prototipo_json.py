"""Prototipo: guardar y cargar un modelo de regresión lineal con JSON.

Entrena un modelo con el núcleo de la aplicación, lo guarda en un archivo
.json con su información (columnas, fórmula, métricas y descripción), lo
carga, muestra esa información y comprueba que predice lo mismo.

JSON guarda datos, no objetos: al cargar se leen textos y números, se
validan y se reconstruye el ModeloLineal. Cargar un archivo no ejecuta
código.

Ejecución (desde la raíz del proyecto):
    uv run python prototipos/prototipo_json.py
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from sikorius.nucleo.errores import ErrorModelo
from sikorius.nucleo.importador import importar_datos
from sikorius.nucleo.modelo import (
    ModeloLineal,
    entrenar_modelo,
    formula_texto,
    metricas_modelo,
)
from sikorius.nucleo.preprocesado import ELIMINAR, aplicar_preprocesado
from sikorius.nucleo.separacion import separar_datos

RUTA_DATOS = Path(__file__).resolve().parents[1] / "data" / "housing.csv"
RUTA_MODELO = Path(__file__).resolve().parent / "modelo_housing.json"
TARGET = "median_house_value"
DESCRIPCION = "Modelo de ejemplo: precio de la vivienda en California."
FORMATO = "sikorius-modelo"
VERSION_FORMATO = 1


# ---------------------------------------------------------------- guardar
def guardar_modelo(ruta, modelo, metricas, descripcion=""):
    """Guarda el modelo y su información en un archivo JSON."""
    datos = {
        "formato": FORMATO,
        "version_formato": VERSION_FORMATO,
        "descripcion": descripcion,
        "formula": formula_texto(modelo),
        "modelo": {
            "features": list(modelo.features),
            "target": modelo.target,
            "coeficientes": list(modelo.coeficientes),
            "termino_independiente": modelo.termino_independiente,
        },
        # NaN no es JSON válido: se guarda como null
        "metricas": {
            conjunto: {
                nombre: None if math.isnan(valor) else valor
                for nombre, valor in valores.items()
            }
            for conjunto, valores in metricas.items()
        },
    }
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(
            datos, archivo, indent=2, ensure_ascii=False, allow_nan=False
        )


# ----------------------------------------------------------------- cargar
def cargar_modelo(ruta):
    """Lee el JSON, lo valida y devuelve (modelo, informacion)."""
    try:
        with open(ruta, encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except (OSError, json.JSONDecodeError):
        raise ErrorModelo("No se pudo leer el archivo del modelo.") from None

    if not isinstance(datos, dict) or datos.get("formato") != FORMATO:
        raise ErrorModelo("El archivo no es un modelo de SIKORIUS.")
    if datos.get("version_formato") != VERSION_FORMATO:
        raise ErrorModelo("Versión del formato desconocida.")

    parte = datos.get("modelo", {})
    features = parte.get("features")
    coeficientes = parte.get("coeficientes")
    if not isinstance(features, list) or not isinstance(coeficientes, list):
        raise ErrorModelo("Faltan las columnas o los coeficientes.")
    if len(features) != len(coeficientes):
        raise ErrorModelo("Hay distinto número de coeficientes y columnas.")

    modelo = ModeloLineal(
        features=features,
        target=parte.get("target"),
        coeficientes=[_numero(c) for c in coeficientes],
        termino_independiente=_numero(parte.get("termino_independiente")),
    )
    informacion = {
        # Se recalcula para que siempre cuadre con los coeficientes
        "formula": formula_texto(modelo),
        "descripcion": datos.get("descripcion", ""),
        "metricas": datos.get("metricas", {}),
    }
    return modelo, informacion


def _numero(valor):
    """Comprueba que el valor leído es un número finito."""
    # bool es subclase de int: true/false no son números válidos
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ErrorModelo("El modelo tiene un valor que no es un número.")
    if not math.isfinite(valor):
        raise ErrorModelo("El modelo tiene un valor infinito.")
    return float(valor)


# ------------------------------------------------------------- prototipo
def entrenar():
    """Mismo flujo que la prueba de concepto de la historia #13."""
    df = importar_datos(RUTA_DATOS)
    features = [
        c
        for c in df.columns
        if c != TARGET and pd.api.types.is_numeric_dtype(df[c])
    ]
    train, test = separar_datos(df, 20, 42)
    train, test, _ = aplicar_preprocesado(
        train, test, features + [TARGET], ELIMINAR
    )
    modelo = entrenar_modelo(train, features, TARGET)
    return modelo, metricas_modelo(modelo, train, test), test


def main():
    original, metricas, test = entrenar()

    guardar_modelo(RUTA_MODELO, original, metricas, DESCRIPCION)
    print(
        "Guardado en %s (%d bytes)\n"
        % (RUTA_MODELO.name, RUTA_MODELO.stat().st_size)
    )

    cargado, info = cargar_modelo(RUTA_MODELO)
    print("Descripción:", info["descripcion"])
    print("Entradas:", ", ".join(cargado.features))
    print("Salida:", cargado.target)
    print("Fórmula:", info["formula"])
    for conjunto, valores in info["metricas"].items():
        print(
            "  %-14s R² = %.4f   ECM = %.2f"
            % (conjunto, valores["r2"], valores["ecm"])
        )

    iguales = np.array_equal(original.predecir(test), cargado.predecir(test))
    print("\nMismas predicciones que el original: %s" % iguales)


if __name__ == "__main__":
    main()
