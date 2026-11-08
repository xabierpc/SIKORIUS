"""Prueba de concepto: regresión lineal con scikit-learn (sin GUI).

Construye dos modelos con el dataset de viviendas de California:

- Regresión simple:   median_house_value ~ median_income
- Regresión múltiple: median_house_value ~ todas las columnas numéricas

Pasos: cargar los datos con el módulo de importación, separar en
entrenamiento y test, quitar las filas con valores inexistentes, entrenar,
escribir la fórmula, calcular ECM y R² en los dos conjuntos y predecir un
valor nuevo.

scikit-learn no es dependencia del proyecto (el equipo eligió numpy, ver
docs/investigacion-regresion.md); se añade solo para esta ejecución con
--with. Desde la raíz del proyecto:
    uv run --with scikit-learn python prototipos/prueba_regresion_sklearn.py
"""

import sys
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

from sikorius.nucleo.importador import importar_datos
from sikorius.nucleo.preprocesado import ELIMINAR, aplicar_preprocesado
from sikorius.nucleo.separacion import separar_datos

RUTA_DEFECTO = Path(__file__).resolve().parents[1] / "data" / "housing.csv"
TARGET = "median_house_value"
FEATURE_SIMPLE = "median_income"
PORCENTAJE_TEST = 20
SEMILLA = 42


def escribir_formula(modelo, features, target):
    """Devuelve la fórmula del modelo con los nombres de las columnas."""
    formula = target + " = "
    primero = True
    for coef, nombre in zip(modelo.coef_, features, strict=True):
        formula += _termino("%.4f * %s" % (abs(coef), nombre), coef, primero)
        primero = False
    return formula + _termino(
        "%.4f" % abs(modelo.intercept_), modelo.intercept_, primero
    )


def _termino(texto, valor, primero):
    """Añade el signo: "- 7.3599 * x" en vez de "+ -7.3599 * x"."""
    if primero:
        return texto if valor >= 0 else "-" + texto
    return (" + " if valor >= 0 else " - ") + texto


def evaluar(modelo, x, y):
    """Devuelve (ECM, R²) del modelo sobre un conjunto."""
    prediccion = modelo.predict(x)
    return mean_squared_error(y, prediccion), r2_score(y, prediccion)


def probar_modelo(titulo, train, test, features, nueva_entrada):
    """Entrena un modelo, lo evalúa en train y test y hace una predicción."""
    print("=" * 70)
    print(titulo)
    print("=" * 70)

    modelo = LinearRegression()
    modelo.fit(train[features], train[TARGET])

    print("Fórmula:")
    print("  " + escribir_formula(modelo, features, TARGET))

    ecm_train, r2_train = evaluar(modelo, train[features], train[TARGET])
    ecm_test, r2_test = evaluar(modelo, test[features], test[TARGET])
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

    # Un DataFrame con los nombres de las columnas evita el aviso de sklearn
    # "X does not have valid feature names"
    x_nuevo = pd.DataFrame([nueva_entrada], columns=features)
    prediccion = modelo.predict(x_nuevo)[0]
    print("Predicción para una entrada nueva:")
    for nombre in features:
        print("  %s = %s" % (nombre, nueva_entrada[nombre]))
    print("  -> %s = %.2f" % (TARGET, prediccion))
    print()


def main():
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else RUTA_DEFECTO

    # 1. Cargar los datos (módulo de importación, historia #10)
    df = importar_datos(ruta)
    print(
        "Dataset: %s (%d filas, %d columnas)\n"
        % (ruta.name, len(df), len(df.columns))
    )

    # Entradas del modelo múltiple: columnas numéricas menos la salida
    # (ocean_proximity es texto y no se puede usar directamente)
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

    # LinearRegression no admite NaN: se eliminan esas filas en cada
    # conjunto con el módulo de preprocesado
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

    # 3-6. Entrenar, fórmula, métricas y predicción
    probar_modelo(
        "Regresión simple",
        train,
        test,
        [FEATURE_SIMPLE],
        {FEATURE_SIMPLE: 5.0},
    )

    # Para la entrada nueva se usa la mediana de cada columna en train
    nueva = {}
    for nombre in features_multiple:
        nueva[nombre] = round(float(train[nombre].median()), 4)
    probar_modelo("Regresión múltiple", train, test, features_multiple, nueva)


if __name__ == "__main__":
    main()
