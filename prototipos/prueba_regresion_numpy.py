"""Prueba de concepto: regresión lineal solo con numpy (sin GUI).

Mismo flujo que prueba_regresion_sklearn.py, pero sin scikit-learn: el
modelo se ajusta por mínimos cuadrados con ``numpy.linalg.lstsq`` y las
métricas (ECM y R²) se calculan a mano. Para la regresión simple se
muestra también ``numpy.polyfit``, que da el mismo resultado.

- Regresión simple:   median_house_value ~ median_income
- Regresión múltiple: median_house_value ~ todas las columnas numéricas

Ejecución (desde la raíz del proyecto):
    uv run python prototipos/prueba_regresion_numpy.py
    uv run python prototipos/prueba_regresion_numpy.py data/housing.xlsx
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from sikorius.nucleo.importador import importar_datos
from sikorius.nucleo.preprocesado import ELIMINAR, aplicar_preprocesado
from sikorius.nucleo.separacion import separar_datos

RUTA_DEFECTO = Path(__file__).resolve().parents[1] / "data" / "housing.csv"
TARGET = "median_house_value"
FEATURE_SIMPLE = "median_income"
PORCENTAJE_TEST = 20
SEMILLA = 42


def ajustar(x, y):
    """Ajusta y = x·coefs + intercepto por mínimos cuadrados.

    Se añade una columna de unos a x para que el término independiente
    sea un coeficiente más. lstsq resuelve min ||A·b - y||² sin invertir
    A^T·A, que es más estable numéricamente que la ecuación normal.

    Returns:
        Tupla (coefs, intercepto).
    """
    a = np.column_stack([np.ones(len(x)), x])
    b, *_ = np.linalg.lstsq(a, y, rcond=None)
    return b[1:], b[0]


def predecir(x, coefs, intercepto):
    return x @ coefs + intercepto


def ecm(y, prediccion):
    """Error cuadrático medio: media de (y - ŷ)²."""
    return np.mean((y - prediccion) ** 2)


def r2(y, prediccion):
    """Coeficiente de determinación: 1 - SS_res / SS_tot."""
    ss_res = np.sum((y - prediccion) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    return 1 - ss_res / ss_tot


def escribir_formula(coefs, intercepto, features, target):
    """Devuelve la fórmula del modelo con los nombres de las columnas."""
    formula = target + " = "
    primero = True
    for coef, nombre in zip(coefs, features, strict=True):
        formula += _termino("%.4f * %s" % (abs(coef), nombre), coef, primero)
        primero = False
    return formula + _termino("%.4f" % abs(intercepto), intercepto, primero)


def _termino(texto, valor, primero):
    """Añade el signo: "- 7.3599 * x" en vez de "+ -7.3599 * x"."""
    if primero:
        return texto if valor >= 0 else "-" + texto
    return (" + " if valor >= 0 else " - ") + texto


def probar_modelo(titulo, train, test, features, nueva_entrada):
    """Ajusta un modelo, lo evalúa en train y test y hace una predicción."""
    print("=" * 70)
    print(titulo)
    print("=" * 70)

    # numpy trabaja con arrays, no con DataFrames: los nombres de las
    # columnas se guardan aparte en ``features`` para la fórmula
    x_train = train[features].to_numpy(dtype=float)
    y_train = train[TARGET].to_numpy(dtype=float)
    x_test = test[features].to_numpy(dtype=float)
    y_test = test[TARGET].to_numpy(dtype=float)

    coefs, intercepto = ajustar(x_train, y_train)

    print("Fórmula:")
    print("  " + escribir_formula(coefs, intercepto, features, TARGET))

    pred_train = predecir(x_train, coefs, intercepto)
    pred_test = predecir(x_test, coefs, intercepto)
    ecm_train, r2_train = ecm(y_train, pred_train), r2(y_train, pred_train)
    ecm_test, r2_test = ecm(y_test, pred_test), r2(y_test, pred_test)
    print("Métricas:")
    # RECM = raíz del ECM: el error típico en las unidades de la salida
    print("  %-14s %18s %12s %8s" % ("Conjunto", "ECM", "RECM", "R²"))
    print(
        "  %-14s %18.2f %12.2f %8.4f"
        % ("Entrenamiento", ecm_train, ecm_train**0.5, r2_train)
    )
    print(
        "  %-14s %18.2f %12.2f %8.4f"
        % ("Test", ecm_test, ecm_test**0.5, r2_test)
    )

    x_nuevo = np.array([nueva_entrada[nombre] for nombre in features])
    prediccion = predecir(x_nuevo, coefs, intercepto)
    print("Predicción para una entrada nueva:")
    for nombre in features:
        print("  %s = %s" % (nombre, nueva_entrada[nombre]))
    print("  -> %s = %.2f" % (TARGET, prediccion))
    print()
    return coefs, intercepto


def main():
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else RUTA_DEFECTO

    # 1. Cargar los datos (módulo de importación, historia #10)
    df = importar_datos(ruta)
    print(
        "Dataset: %s (%d filas, %d columnas)\n"
        % (ruta.name, len(df), len(df.columns))
    )

    features_multiple = []
    for columna in df.columns:
        if columna != TARGET and pd.api.types.is_numeric_dtype(df[columna]):
            features_multiple.append(columna)

    # 2. Separar en entrenamiento y test (historia #41)
    train, test = separar_datos(df, PORCENTAJE_TEST, SEMILLA)
    print(
        "Separación: %d filas de entrenamiento, %d de test (semilla %d)"
        % (len(train), len(test), SEMILLA)
    )

    # Con NaN, lstsq falla con un error poco claro ("SVD did not converge
    # in Linear Least Squares"): hay que quitar esas filas antes
    columnas = features_multiple + [TARGET]
    train, test, resumen = aplicar_preprocesado(
        train, test, columnas, ELIMINAR
    )
    print(
        "Filas eliminadas por valores inexistentes: %d en entrenamiento,"
        " %d en test\n"
        % (
            resumen["train"]["filas_eliminadas"],
            resumen["test"]["filas_eliminadas"],
        )
    )

    # 3-6. Ajustar, fórmula, métricas y predicción
    coefs, intercepto = probar_modelo(
        "Regresión simple (numpy.linalg.lstsq)",
        train,
        test,
        [FEATURE_SIMPLE],
        {FEATURE_SIMPLE: 5.0},
    )

    # polyfit(x, y, 1) ajusta una recta: devuelve [pendiente, intercepto]
    pendiente, corte = np.polyfit(train[FEATURE_SIMPLE], train[TARGET], 1)
    coincide = np.isclose(pendiente, coefs[0]) and np.isclose(
        corte, intercepto
    )
    print(
        "Comprobación con numpy.polyfit: pendiente %.4f, intercepto %.4f"
        " (coincide con lstsq: %s)\n" % (pendiente, corte, coincide)
    )

    nueva = {}
    for nombre in features_multiple:
        nueva[nombre] = round(float(train[nombre].median()), 4)
    probar_modelo(
        "Regresión múltiple (numpy.linalg.lstsq)",
        train,
        test,
        features_multiple,
        nueva,
    )


if __name__ == "__main__":
    main()
