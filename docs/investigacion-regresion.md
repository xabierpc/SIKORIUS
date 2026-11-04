# Investigación de librerías de regresión lineal

## 1. Objetivo

Elegir la librería con la que SIKORIUS creará los modelos de regresión lineal y aprender a entrenar, interpretar y evaluar un modelo antes de integrarlo en la aplicación.

La aplicación necesita lo siguiente de la librería:

- crear modelos de regresión lineal **simple** (una entrada) y **múltiple** (varias entradas);
- obtener los **coeficientes** y el **término independiente** para mostrar la fórmula del modelo;
- calcular el **error cuadrático medio (ECM)** y el **coeficiente de determinación (R²)**;
- hacer **predicciones** con valores nuevos;
- instalarse en el proyecto con `uv add`.

## 2. Opciones investigadas

Se han probado tres opciones. Las tres resuelven el mismo problema, que es el ajuste por mínimos cuadrados ordinarios, pero con enfoques distintos.

### scikit-learn (`LinearRegression`)

- Es una librería de aprendizaje automático. Todos sus modelos tienen la misma interfaz: `fit(X, y)` para entrenar y `predict(X)` para predecir.
- Después de entrenar, el modelo guarda los coeficientes en `coef_` y el término independiente en `intercept_`. El término independiente se calcula por defecto.
- Acepta directamente un DataFrame de pandas, tanto con una columna como con varias. La regresión simple y la múltiple se crean igual.
- Las métricas están en `sklearn.metrics`, por ejemplo `mean_squared_error` y `r2_score`.
- Su documentación tiene guía de usuario, referencia de la API y muchos ejemplos.

### statsmodels (`OLS`)

- Es una librería de estadística. Está pensada para analizar el modelo, más que para predecir.
- Hay que añadir a mano la columna del término independiente con `sm.add_constant(X)`. Si se olvida, el modelo pasa por el origen y no avisa.
- Los coeficientes están en `params`, y el primero es la constante.
- Su punto fuerte es `summary()`: muestra el error estándar, el estadístico t, el p-valor y el intervalo de confianza de cada coeficiente, además del R² y el R² ajustado.
- Para calcular el ECM sobre el conjunto de test no tiene una función tan directa. Hay que predecir y calcularlo a mano, o usar `statsmodels.tools.eval_measures.mse`.
- La documentación está orientada a quien ya sabe estadística.

### numpy (`numpy.linalg.lstsq` / `numpy.polyfit`)

- Resuelve directamente el problema de mínimos cuadrados $\min_b \lVert A b - y \rVert^2$.
- `polyfit` solo sirve para una entrada, es decir, para la regresión simple. Para la múltiple hay que usar `lstsq` y construir a mano la matriz $A$ con una columna de unos para el término independiente.
- Devuelve un vector de números sin nombres de columna. La predicción y las métricas se programan a mano.
- No necesita ninguna dependencia nueva, porque numpy ya está en el proyecto.

## 3. Comparativa

| Aspecto | scikit-learn | statsmodels | numpy |
|---|---|---|---|
| Facilidad de uso y documentación | Alta: `fit`/`predict`, guía con ejemplos para principiantes | Media: hay que conocer conceptos estadísticos | Media-baja: hay que montar la matriz a mano |
| Regresión simple y múltiple | El mismo código para las dos | El mismo código, pero hay que añadir la constante | `polyfit` solo para la simple; `lstsq` para las dos |
| Coeficientes y término independiente | `coef_` e `intercept_` por separado | `params`, con la constante incluida | Vector sin nombres; la posición 0 es la constante |
| Métricas de error | `mean_squared_error`, `r2_score`, `mean_absolute_error`... | R² en el resumen; ECM de test a mano o con `eval_measures` | Todo a mano |
| Instalación con uv | `uv add scikit-learn` (añade scipy, joblib, threadpoolctl y narwhals) | `uv add statsmodels` (añade scipy, patsy y formulaic) | Ya instalada |
| Valor añadido | Interfaz común con otros modelos y utilidades de ML | Inferencia estadística (p-valores, intervalos) | Ninguna dependencia nueva |

Para comprobar que las tres opciones dan el mismo resultado, se ajustó el modelo múltiple con cada una (`prototipos/comparativa_regresion.py`). Los coeficientes, el término independiente y el R² de test coinciden:

| Librería | Término independiente | Coef. `median_income` | R² test |
|---|---|---|---|
| scikit-learn | -3 537 030.9757 | 40 206.4320 | 0.6235 |
| statsmodels | -3 537 030.9757 | 40 206.4320 | 0.6235 |
| numpy | -3 537 030.9757 | 40 206.4320 | 0.6235 |

Por tanto, la elección no depende de la precisión del resultado. Depende de la comodidad de uso y de lo que cada librería ofrece alrededor del modelo.

## 4. Librería seleccionada: numpy

El equipo ha elegido **numpy**, que es también la librería que usa el código de la historia de creación del modelo.

**Justificación:**

1. **No añade dependencias.** numpy ya está en el proyecto, porque la usan la separación en entrenamiento y test y el preprocesado. scikit-learn añadiría cinco paquetes más (entre ellos scipy), y statsmodels también varios, solo para una operación que numpy ya resuelve.
2. **Da exactamente el mismo resultado.** Como muestra la comparativa del apartado 3, `lstsq` obtiene los mismos coeficientes, término independiente y métricas que scikit-learn y statsmodels.
3. **Sirve para la regresión simple y la múltiple.** Se usa `lstsq` con la misma función en los dos casos: solo cambia el número de columnas de la matriz.
4. **Lo que hay que programar a mano es poco y sencillo.**
   - Predicción: `x @ coefs + intercepto`.
   - ECM: `np.mean((y - pred) ** 2)`.
   - R²: `1 - SS_res / SS_tot`.
   - Los nombres de las columnas para la fórmula ya los tiene la aplicación, porque son la selección de columnas confirmada por el usuario.
5. **Se entiende qué hace el modelo.** El código refleja directamente la definición matemática de mínimos cuadrados y de cada métrica, lo que ayuda a aprender a interpretar el modelo, que es uno de los objetivos de la historia.
6. **Es fácil guardar el modelo.** El modelo son solo los coeficientes, el término independiente y los nombres de las columnas, así que se puede guardar en un archivo de texto (por ejemplo, JSON) sin depender de `pickle` ni de la versión de ninguna librería.

**Inconvenientes asumidos:**

- Hay que mantener funciones propias de métricas y de predicción. Al ser pocas líneas, se cubren con pruebas unitarias.
- Hay que construir a mano la columna de unos para el término independiente.
- Si quedan valores inexistentes, `lstsq` da un error poco claro. La aplicación ya lo evita, porque el botón "Crear modelo" solo se habilita cuando no quedan valores inexistentes.

**Opciones descartadas:**

- **scikit-learn** era la opción más cómoda: tiene métricas ya hechas y una interfaz `fit`/`predict`. Pero sus ventajas no compensan añadir una dependencia grande para un único modelo lineal.
- **statsmodels**: su valor añadido (p-valores e intervalos de confianza) no forma parte de los requisitos de la aplicación.

**Dependencia del proyecto:** numpy ya estaba añadida con uv (`numpy>=2.5.4` en `pyproject.toml`), así que no hace falta ningún `uv add`. scikit-learn se llegó a añadir durante la investigación y se quitó al elegir numpy:

```bash
uv remove scikit-learn
```

`pyproject.toml` y `uv.lock` quedan como estaban antes de la investigación.

## 5. Prueba de concepto

**Script:** `prototipos/prueba_regresion_numpy.py`. No tiene interfaz gráfica y está separado del código de la aplicación.

```bash
uv run python prototipos/prueba_regresion_numpy.py                    # data/housing.csv
uv run python prototipos/prueba_regresion_numpy.py data/housing.xlsx  # u otro formato
```

Como referencia, la misma prueba hecha con scikit-learn está en `prototipos/prueba_regresion_sklearn.py` y da los mismos resultados. Ese script se ejecuta con `uv run --with scikit-learn ...`.

**Datos:** dataset de viviendas de California (`data/housing.csv`, también en `.xlsx` y `.db`), con 20 640 filas y 10 columnas. La salida es `median_house_value`, el valor mediano de la vivienda en dólares.

### Pasos

1. **Cargar los datos** con `importar_datos` del módulo de importación (historia #10). El resultado es el mismo con CSV, Excel o SQLite.
2. **Separar en entrenamiento y test** con `separar_datos` (historia #41): 20 % de test y semilla 42, que da 16 512 filas de entrenamiento y 4 128 de test.
3. **Quitar las filas con valores inexistentes** con `aplicar_preprocesado(..., "eliminar")`. `total_bedrooms` tiene 207 valores vacíos: se eliminan 159 filas de entrenamiento y 48 de test.
4. **Entrenar** con `numpy.linalg.lstsq` sobre el conjunto de entrenamiento, añadiendo una columna de unos para el término independiente. Se crean dos modelos:
   - simple: `median_house_value ~ median_income`;
   - múltiple: `median_house_value ~` las 8 columnas numéricas restantes.
   En el modelo simple se comprueba además que `numpy.polyfit(x, y, 1)` da la misma recta.
5. **Escribir la fórmula** con los coeficientes, el término independiente y los nombres de las columnas. Los coeficientes negativos se escriben restando.
6. **Calcular ECM y R²** en entrenamiento y en test con sus fórmulas, porque numpy no tiene funciones de métricas. También se muestra la RECM, que es la raíz del ECM.
7. **Predecir** un valor nuevo.

### Resultados

**Regresión simple**

```
median_house_value = 41989.5863 * median_income + 44572.3766
```

| Conjunto | ECM | RECM | R² |
|---|---|---|---|
| Entrenamiento | 7 036 748 889.56 | 83 885.33 | 0.4749 |
| Test | 6 908 723 901.70 | 83 118.73 | 0.4692 |

Predicción: con `median_income = 5.0`, el modelo da `median_house_value = 254 520.31`.

**Regresión múltiple**

```
median_house_value = -42190.3182 * longitude - 42052.1556 * latitude
                     + 1184.1041 * housing_median_age - 7.3599 * total_rooms
                     + 104.2865 * total_bedrooms - 43.0603 * population
                     + 65.7621 * households + 40206.4320 * median_income
                     - 3537030.9757
```

| Conjunto | ECM | RECM | R² |
|---|---|---|---|
| Entrenamiento | 4 828 367 481.48 | 69 486.46 | 0.6397 |
| Test | 4 900 825 641.52 | 70 005.90 | 0.6235 |

Predicción: con la mediana de entrenamiento de cada columna, el modelo da `median_house_value = 204 847.52`.

### Interpretación

**Coeficientes**

- Cada coeficiente indica cuánto cambia la predicción de la salida cuando esa entrada aumenta en 1 unidad.
- En el modelo simple, por cada unidad más de `median_income` el valor estimado de la vivienda sube unos 41 990 $. En este dataset los ingresos suelen expresarse en decenas de miles de dólares, pero la fuente del dataset no está documentada en el proyecto.
- En el modelo múltiple, cada coeficiente mide el efecto de su columna **manteniendo fijas las demás**. Por eso no se pueden leer por separado.
  - Ejemplo: `total_rooms` tiene coeficiente negativo y `total_bedrooms` positivo. Las dos columnas están muy relacionadas entre sí (colinealidad), y el modelo reparte el efecto entre ellas.
  - El signo de un coeficiente no indica por sí solo una relación causal.

**Término independiente**

- Es la predicción cuando todas las entradas valen 0.
- En el modelo múltiple vale -3.5 millones, que no tiene sentido real, porque una longitud y una latitud de 0 están fuera de California. Es un valor que el modelo necesita para ajustar la recta o el hiperplano, no un dato que haya que interpretar.

**ECM y RECM**

- El ECM es la media de los errores al cuadrado. Está en dólares², así que su valor absoluto es difícil de leer.
- La RECM vuelve a las unidades de la salida: el modelo múltiple se equivoca en unos 70 000 $ de media, frente a unos 83 000 $ del simple.

**R²**

- Es la proporción de la variabilidad de la salida que explica el modelo. Vale 1 si el modelo es perfecto y 0 si no mejora a predecir siempre la media.
- El modelo simple explica en torno al 47 % y el múltiple en torno al 63 %. Añadir columnas mejora el modelo.

**Diferencia entre entrenamiento y test**

- Las métricas de test miden cómo funciona el modelo con datos que no ha visto, es decir, su capacidad de generalización.
- En los dos modelos, entrenamiento y test son muy parecidos: el R² baja menos de 0.02. Por tanto, **no hay sobreajuste**.
- Que el R² sea moderado indica más bien lo contrario, **subajuste**: una relación lineal no capta todo el comportamiento de los precios.
  - Por ejemplo, `median_house_value` está limitado a 500 001 $ (965 filas tienen exactamente ese valor), y una recta no puede reproducir ese tope.
- En el modelo simple, el ECM de test es algo menor que el de entrenamiento. Es casualidad del reparto aleatorio y con otra semilla podría ser al revés.

## 6. Dificultades encontradas y soluciones

| Dificultad | Solución |
|---|---|
| `total_bedrooms` tiene 207 valores inexistentes. Con ellos, `lstsq` falla con un error poco claro (`SVD did not converge in Linear Least Squares`), y scikit-learn también los rechaza (`Input X contains NaN`) | Eliminar esas filas en cada conjunto, después de separar, con el módulo de preprocesado |
| `ocean_proximity` es texto y no se puede usar en una regresión lineal | Usar solo columnas numéricas como entradas, igual que exige la validación de la selección de columnas |
| numpy trabaja con arrays sin nombres de columna, y hacen falta para la fórmula | Guardar aparte la lista de columnas de entrada, en el mismo orden que las columnas de la matriz |
| numpy no tiene funciones de ECM ni R² | Programarlas a partir de su definición y comprobar que coinciden con las de scikit-learn (`prototipos/comparativa_regresion.py`) |
| Al predecir con una lista, scikit-learn avisa: `X does not have valid feature names` (prototipo de scikit-learn) | Pasar la entrada nueva como un DataFrame con los mismos nombres de columna que en el entrenamiento |
| La fórmula salía como `+ -7.3599 * total_rooms` | Escribir el signo de cada término según el signo del coeficiente |
| El ECM tiene valores enormes (miles de millones) y no se entienden | Mostrar también la RECM, que está en dólares |
| En statsmodels, el modelo sin `add_constant` no tiene término independiente y no avisa. Con numpy pasa lo mismo si se olvida la columna de unos | Añadir siempre la columna de unos en la función de ajuste, no en quien la llama |
| Para probar scikit-learn y statsmodels no se quería añadirlos al proyecto | Ejecutar esos scripts con `uv run --with ...`, que instala la librería solo para esa ejecución |

## 7. Archivos

- `prototipos/prueba_regresion_numpy.py`: prueba de concepto con la librería elegida, numpy. Usa `lstsq` para la simple y la múltiple, `polyfit` como comprobación en la simple, y calcula el ECM y el R² a mano.
- `prototipos/prueba_regresion_sklearn.py`: la misma prueba con scikit-learn, como referencia. Se ejecuta con `uv run --with scikit-learn python prototipos/prueba_regresion_sklearn.py`.
- `prototipos/comparativa_regresion.py`: el mismo modelo con scikit-learn, statsmodels y numpy. Se ejecuta con `uv run --with statsmodels --with scikit-learn python prototipos/comparativa_regresion.py`.
- `data/housing.csv`, `data/housing.xlsx`, `data/housing.db`: datos de ejemplo. Son locales y no se suben al repositorio.

## 8. Referencias

- scikit-learn, *Linear Models*: https://scikit-learn.org/stable/modules/linear_model.html
- scikit-learn, *Metrics and scoring*: https://scikit-learn.org/stable/modules/model_evaluation.html
- statsmodels, *Linear Regression*: https://www.statsmodels.org/stable/regression.html
- NumPy, `numpy.linalg.lstsq`: https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html
- NumPy, `numpy.polyfit`: https://numpy.org/doc/stable/reference/generated/numpy.polyfit.html

Versiones usadas en la prueba: numpy 2.5.4 (la del `uv.lock` del proyecto) y Python 3.12. Fuera del proyecto, con `--with`: scikit-learn 1.9.1 y statsmodels 0.15.0.
