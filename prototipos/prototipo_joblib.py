"""Prototipo: guardar y cargar un modelo de regresión lineal con joblib.

Entrena un modelo con el núcleo de la aplicación, lo guarda en un archivo
.joblib con su información (columnas, fórmula, métricas y descripción), lo
carga, muestra esa información y comprueba que predice lo mismo.

Al final incluye un ejemplo INOFENSIVO del riesgo de seguridad: un objeto
que, al cargarse con ``pickle.load`` o ``joblib.load``, imprime un mensaje
sin que el código que carga lo llame. Un archivo malicioso podría usar
``os.system`` en lugar de ``print``. Por eso solo se deben cargar
archivos .joblib de origen conocido.

joblib no es dependencia del proyecto. Ejecución (desde la raíz):
    uv run --with joblib python prototipos/prototipo_joblib.py
"""

import pickle
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sikorius.nucleo.importador import importar_datos
from sikorius.nucleo.modelo import (
    entrenar_modelo,
    formula_texto,
    metricas_modelo,
)
from sikorius.nucleo.preprocesado import ELIMINAR, aplicar_preprocesado
from sikorius.nucleo.separacion import separar_datos

RUTA_DATOS = Path(__file__).resolve().parents[1] / "data" / "housing.csv"
RUTA_MODELO = Path(__file__).resolve().parent / "modelo_housing.joblib"
TARGET = "median_house_value"
DESCRIPCION = "Modelo de ejemplo: precio de la vivienda en California."


# ---------------------------------------------------------------- guardar
def guardar_modelo(ruta, modelo, metricas, descripcion=""):
    """Guarda el objeto ModeloLineal completo junto con su información."""
    datos = {
        "modelo": modelo,
        "formula": formula_texto(modelo),
        "metricas": metricas,
        "descripcion": descripcion,
    }
    joblib.dump(datos, ruta)


# ----------------------------------------------------------------- cargar
def cargar_modelo(ruta):
    """Carga el archivo y devuelve (modelo, informacion)."""
    datos = joblib.load(ruta)
    modelo = datos.pop("modelo")
    return modelo, datos


# ------------------------------------------------- ejemplo de seguridad
class ArchivoTrampa:
    """Objeto que, al deserializarse, llama a ``print``."""

    def __reduce__(self):
        # pickle guarda "al cargar, llama a print(...)" y lo obedece
        return (print, (">>> Código ejecutado al CARGAR el archivo <<<",))


def ejemplo_seguridad():
    """Carga un archivo trampa con pickle y con joblib."""
    with tempfile.TemporaryDirectory() as carpeta:
        ruta_pickle = Path(carpeta) / "trampa.pkl"
        ruta_joblib = Path(carpeta) / "trampa.joblib"
        ruta_pickle.write_bytes(pickle.dumps(ArchivoTrampa()))
        joblib.dump(
            {"modelo": ArchivoTrampa(), "descripcion": "normal"}, ruta_joblib
        )

        print("pickle.load ...")
        with open(ruta_pickle, "rb") as archivo:
            print("  devuelve:", pickle.load(archivo))
        print("joblib.load ...")
        print("  devuelve:", joblib.load(ruta_joblib))


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

    print("\n--- Ejemplo de seguridad ---")
    ejemplo_seguridad()


if __name__ == "__main__":
    main()
