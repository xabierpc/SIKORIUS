"""Comparativa: el mismo modelo con scikit-learn, statsmodels y numpy.

Ajusta la regresión múltiple de la prueba de concepto con las tres
opciones investigadas y comprueba que dan los mismos coeficientes y
métricas. Sirve de apoyo a docs/investigacion-regresion.md.

statsmodels y scikit-learn no son dependencias del proyecto; se añaden
solo para esta ejecución con --with:
    uv run --with statsmodels --with scikit-learn python \
        prototipos/comparativa_regresion.py
"""

from pathlib import Path

import numpy as np
import statsmodels.api as sm
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

from sikorius.nucleo.importador import importar_datos
from sikorius.nucleo.preprocesado import ELIMINAR, aplicar_preprocesado
from sikorius.nucleo.separacion import separar_datos

RUTA = Path(__file__).resolve().parents[1] / "data" / "housing.csv"
TARGET = "median_house_value"
FEATURES = ["longitude", "latitude", "housing_median_age", "total_rooms",
            "total_bedrooms", "population", "households", "median_income"]


def con_sklearn(x_train, y_train, x_test):
    modelo = LinearRegression().fit(x_train, y_train)
    return modelo.intercept_, modelo.coef_, modelo.predict(x_test)


def con_statsmodels(x_train, y_train, x_test):
    # statsmodels no añade el término independiente: hay que pedirlo
    modelo = sm.OLS(y_train, sm.add_constant(x_train)).fit()
    prediccion = modelo.predict(sm.add_constant(x_test))
    return modelo.params.iloc[0], modelo.params.iloc[1:].to_numpy(), prediccion


def con_numpy(x_train, y_train, x_test):
    # Columna de unos para el término independiente; lstsq resuelve
    # min ||A·b - y||² sin necesidad de invertir A^T·A
    a = np.column_stack([np.ones(len(x_train)), x_train])
    b, *_ = np.linalg.lstsq(a, y_train, rcond=None)
    prediccion = np.column_stack([np.ones(len(x_test)), x_test]) @ b
    return b[0], b[1:], prediccion


def main():
    df = importar_datos(RUTA)
    train, test = separar_datos(df, 20, 42)
    train, test, _ = aplicar_preprocesado(
        train, test, FEATURES + [TARGET], ELIMINAR)

    print("%-12s %16s %16s %8s"
          % ("Librería", "Intercepto", "coef. income", "R² test"))
    resultados = {}
    for nombre, funcion in (("sklearn", con_sklearn),
                            ("statsmodels", con_statsmodels),
                            ("numpy", con_numpy)):
        intercepto, coefs, prediccion = funcion(
            train[FEATURES], train[TARGET], test[FEATURES])
        r2 = r2_score(test[TARGET], prediccion)
        resultados[nombre] = (intercepto, coefs,
                              mean_squared_error(test[TARGET], prediccion))
        print("%-12s %16.4f %16.4f %8.4f"
              % (nombre, intercepto, coefs[-1], r2))

    referencia = resultados["sklearn"]
    for nombre, (intercepto, coefs, ecm) in resultados.items():
        iguales = (np.isclose(intercepto, referencia[0])
                   and np.allclose(coefs, referencia[1])
                   and np.isclose(ecm, referencia[2]))
        print("%s coincide con sklearn: %s" % (nombre, iguales))

    # Lo que solo da statsmodels: el resumen estadístico completo
    print()
    print(sm.OLS(train[TARGET], sm.add_constant(train[FEATURES])).fit()
          .summary().tables[1])


if __name__ == "__main__":
    main()
