# Investigación de persistencia de modelos: joblib y JSON

## 1. Objetivo

Elegir cómo guardará SIKORIUS un modelo de regresión lineal en un archivo y cómo lo recuperará después, junto con la información que la aplicación necesita mostrar:

- la **fórmula** del modelo;
- las **columnas de entrada** (`features`) y la **columna de salida** (`target`);
- las **métricas** (R² y ECM) de entrenamiento y de test;
- una **descripción** escrita por el usuario.

El modelo de la aplicación es `ModeloLineal` (`src/sikorius/nucleo/modelo.py`), elegido en la historia de regresión: numpy calcula los coeficientes y el modelo guarda `features`, `target`, `coeficientes` (tupla de `float`) y `termino_independiente` (`float`). No hay ningún objeto de scikit-learn.

## 2. Métodos investigados

Se han investigado dos métodos, como pide la historia: uno que ejecuta código al cargar (**joblib**) y otro que no (**JSON**).

### joblib

- Es la alternativa a `pickle` que recomienda scikit-learn. Por dentro usa `pickle`, pero guarda los arrays grandes de numpy de forma más eficiente y puede comprimir.
- Guarda **el objeto de Python completo**. En la prueba se guarda un diccionario con el `ModeloLineal` y su información:

  ```python
  joblib.dump({"modelo": modelo, "formula": ..., "metricas": ..., "descripcion": ...}, "modelo.joblib")
  datos = joblib.load("modelo.joblib")
  ```

- No está en el proyecto. Habría que añadirlo con `uv add joblib`.
- El archivo es binario y no se puede leer con un editor de texto.

### JSON (módulo `json` de la biblioteca estándar)

- Es un formato de texto. Solo admite textos, números, `true`/`false`, `null`, listas y diccionarios.
- No guarda el objeto: hay que decidir qué **datos** del modelo se guardan y reconstruir el `ModeloLineal` al cargar.
- En SIKORIUS eso es sencillo, porque el modelo ya son solo números y nombres de columnas:

  ```python
  json.dump({"modelo": {"features": [...], "coeficientes": [...], ...}, ...}, archivo, indent=2)
  datos = json.load(archivo)
  modelo = ModeloLineal(**datos["modelo"])   # en la prueba, después de validar
  ```

- No necesita instalar nada.

## 3. Comparativa

Resultados obtenidos con `prototipos/prototipo_json.py` y `prototipos/prototipo_joblib.py` sobre el modelo múltiple de viviendas (8 columnas de entrada). Las pruebas de compatibilidad se hicieron aparte durante la investigación.

| Aspecto | joblib | JSON |
|---|---|---|
| **Facilidad de uso** | `dump`/`load` en una línea cada uno, sin convertir nada. Pero hay que añadir la dependencia (`uv add joblib`). | `json.dump`/`json.load` en una línea cada uno. Hay que escribir la conversión modelo ↔ diccionario (unas 20 líneas) y conviene validar al cargar. No añade dependencias. |
| **Tamaño del archivo** | 783 bytes | 1 123 bytes (con `indent=2`) |
| **Legibilidad** | Binario. Solo se ven fragmentos sueltos (`sikorius.nucleo.modelo`, `ModeloLineal`, nombres de columnas...). | Texto que se abre con cualquier editor: se ven directamente la fórmula, los coeficientes, las métricas y la descripción. |
| **Seguridad al cargar archivos de origen desconocido** | **Insegura**: `joblib.load` puede ejecutar código arbitrario (apartado 4). | **Segura**: `json.load` solo devuelve datos y no ejecuta nada. Hay que validar esos datos (un JSON bien formado puede traer valores incorrectos). |
| **Compatibilidad con otras versiones** | El archivo depende del código: guarda la ruta `sikorius.nucleo.modelo.ModeloLineal`. Si la clase cambia de nombre o de módulo, el archivo deja de cargarse (`ModuleNotFoundError`, comprobado durante la investigación). scikit-learn y joblib no garantizan cargar archivos creados con otras versiones. | No depende de ninguna clase ni versión de librería. Solo depende de los nombres de los campos, que se controlan con `version_formato`. |
| **Guardar la información asociada** | Muy fácil: se mete todo en un diccionario, sea del tipo que sea. | Fácil: todo son textos y números. Una excepción: las métricas pueden valer `NaN`, que no es JSON válido, y se guardan como `null`. |

**Compatibilidad comprobada en la práctica:**

- Un archivo de joblib con un array de numpy, creado con Python 3.12, joblib 1.6.0 y numpy 2.5.4, se cargó sin problemas con Python 3.13 y joblib 1.3.2, y con Python 3.11 y numpy 1.25.2. En estas pruebas el problema no fue la versión de Python ni de numpy.
- El problema real apareció al **mover la clase del modelo** a otro módulo, algo normal mientras el proyecto se reorganiza por capas: el archivo de joblib ya no carga y el JSON sí.
- El JSON creado con Python 3.12 se leyó con Python 3.11 sin cambios.

**Predicciones:** con los dos métodos, el modelo cargado da **exactamente** las mismas predicciones que el original en las 4 080 filas de test (diferencia máxima 0). JSON guarda cada `float` con todos sus dígitos (`repr`), así que no se pierde precisión.

## 4. Riesgo de seguridad de pickle y joblib

### Por qué pueden ejecutar código

`pickle` no guarda solo datos: guarda **instrucciones para reconstruir el objeto**. Una clase puede definir el método `__reduce__` para indicar "al cargarme, llama a esta función con estos argumentos", y `pickle.load` lo hace sin preguntar. `joblib.load` usa `pickle` por dentro, así que tiene el mismo problema.

- La documentación oficial de Python lo advierte al principio del módulo `pickle`: el módulo *no es seguro*, solo se deben deserializar datos de confianza, y se pueden construir datos maliciosos que **ejecuten código arbitrario al deserializarse**.
- La guía de persistencia de modelos de scikit-learn repite el aviso para `pickle` y `joblib`: no se deben cargar archivos de origen no confiable. También indica que un modelo guardado con una versión de scikit-learn no tiene por qué cargarse con otra.
- La documentación de joblib advierte lo mismo para `joblib.load`.

### Ejemplo inofensivo (final de `prototipos/prototipo_joblib.py`)

Se define una clase cuyo `__reduce__` devuelve `(print, (MENSAJE,))`. Al cargar el archivo se llama a `print`, aunque el código que carga **no la llama**: solo hace `pickle.load(archivo)` o `joblib.load(ruta)`.

```python
class ArchivoTrampa:
    def __reduce__(self):
        # pickle guarda "al cargar, llama a print(...)" y lo obedece
        return (print, (">>> Código ejecutado al CARGAR el archivo <<<",))
```

El prototipo guarda un `ArchivoTrampa` con `pickle` y otro, dentro de un diccionario con aspecto de modelo, con `joblib`. Después los carga.

Resultado:

```
--- Ejemplo de seguridad ---
pickle.load ...
>>> Código ejecutado al CARGAR el archivo <<<
  devuelve: None
joblib.load ...
>>> Código ejecutado al CARGAR el archivo <<<
  devuelve: {'modelo': None, 'descripcion': 'normal'}
```

Observaciones:

- El mensaje aparece **antes** de que `load` devuelva nada: el código que carga solo llama a `pickle.load` o `joblib.load`, nunca a `print`.
- En el caso de joblib, el archivo **parece un modelo normal**: es un diccionario con una descripción. El código se ejecuta antes de que nadie pueda revisar su contenido.
- Con `print` no pasa nada, pero se podría haber usado `os.system` o `subprocess.run` y borrar archivos o descargar un programa.
- Con JSON no hay forma de escribir "llama a esta función": aunque el archivo contenga el texto `"print"`, `json.load` lo devuelve como un texto más dentro de un diccionario.

### Qué métodos no ejecutan código y qué limitaciones tienen

- **JSON** no ejecuta código al cargar. Sus limitaciones:
  - no guarda el objeto, así que hay que **reconstruir** el `ModeloLineal` a partir de los coeficientes;
  - hay que **validar** los datos leídos (que existan los campos, que los coeficientes sean números, que haya tantos coeficientes como columnas...), porque un archivo modificado puede traer cualquier cosa;
  - solo admite tipos básicos: los arrays de numpy hay que pasarlos a lista y `NaN`/`inf` no están permitidos en JSON estándar.
- **joblib** (y `pickle`) sí pueden ejecutar código. No hay forma segura de cargar un archivo de origen desconocido con ellos.

## 5. Método seleccionado: JSON

La historia pide elegir **el más fácil de usar de los dos**, con la seguridad como uno de los criterios. El equipo elige **JSON**, con extensión **`.json`**.

**Justificación:**

1. **Es el más fácil de usar en este proyecto.**
   - joblib es más corto para guardar un objeto arbitrario, como un modelo de scikit-learn, porque se guarda tal cual. Pero SIKORIUS no usa scikit-learn: su modelo ya son solo números y nombres de columnas. La "reconstrucción" que obliga a hacer JSON es una llamada a `ModeloLineal(...)`.
   - No hay que instalar nada (`json` es de la biblioteca estándar). Con joblib habría que añadir una dependencia solo para esto, después de haber elegido numpy precisamente para no añadirlas.
   - El archivo se puede **abrir y revisar con cualquier editor**, lo que facilita depurar, escribir tests y explicar el modelo.
   - Los errores son claros: si el archivo está mal, la validación dice qué campo falla. Con joblib, un archivo de otra versión da errores como `ModuleNotFoundError` sobre módulos internos.
2. **Es seguro.** Cargar un `.json` no puede ejecutar código, aunque el archivo venga de otra persona o se haya modificado. Esto importa porque la aplicación deja al usuario elegir cualquier archivo para cargar un modelo. Con joblib habría que confiar en que el usuario solo abra archivos de origen conocido.
3. **Es compatible a largo plazo.** El archivo no depende del nombre ni de la ubicación de la clase `ModeloLineal`, ni de la versión de Python o de numpy. El proyecto se está reorganizando por capas, y con joblib cualquier cambio de sitio de la clase rompería los modelos ya guardados.
4. **Guarda toda la información sin trucos**, salvo las métricas `NaN`, que se resuelven guardándolas como `null`.

**Inconvenientes asumidos:**

- Hay que mantener la conversión modelo ↔ diccionario y la validación (unas 70 líneas en `prototipo_json.py`, que se cubrirán con pruebas unitarias).
- El archivo ocupa algo más (1 123 frente a 783 bytes). Para un modelo lineal la diferencia no importa.
- Si en el futuro se añaden campos al modelo, hay que subir `version_formato` y decidir cómo leer los archivos antiguos.

**Aviso en el `README.md`:** no hace falta. JSON no ejecuta código al cargar, así que el criterio de aceptación que pide el aviso no se aplica.

## 6. Estructura del archivo

Ejemplo real generado por `prototipos/prototipo_json.py` (`prototipos/modelo_housing.json`, coeficientes abreviados):

```json
{
  "formato": "sikorius-modelo",
  "version_formato": 1,
  "descripcion": "Modelo de ejemplo: precio de la vivienda en California.",
  "formula": "median_house_value = -42190.3182 * longitude - 42052.1556 * latitude + ... - 3537030.9757",
  "modelo": {
    "features": ["longitude", "latitude", "housing_median_age", "total_rooms",
                 "total_bedrooms", "population", "households", "median_income"],
    "target": "median_house_value",
    "coeficientes": [-42190.31824780857, -42052.1556136299, ..., 40206.43198943905],
    "termino_independiente": -3537030.975656872
  },
  "metricas": {
    "entrenamiento": {"r2": 0.6397188361500733, "ecm": 4828367481.482713},
    "test": {"r2": 0.6234643165055632, "ecm": 4900825641.525146}
  }
}
```

| Campo | Tipo | Contenido |
|---|---|---|
| `formato` | texto | Siempre `"sikorius-modelo"`. Sirve para rechazar archivos JSON que no son modelos. |
| `version_formato` | entero | Versión de esta estructura (ahora `1`). Si cambia la estructura, se sube. |
| `descripcion` | texto | Descripción escrita por el usuario (puede estar vacía). |
| `formula` | texto | Fórmula legible, generada con `formula_texto`. Al cargar se vuelve a calcular a partir de los coeficientes, para que siempre cuadre con ellos. |
| `modelo.features` | lista de textos | Columnas de entrada, en el mismo orden que `coeficientes`. |
| `modelo.target` | texto | Columna de salida. |
| `modelo.coeficientes` | lista de números | Un coeficiente por columna de entrada. |
| `modelo.termino_independiente` | número | Término independiente. |
| `metricas.entrenamiento.r2`, `metricas.entrenamiento.ecm` | número o `null` | R² y ECM en entrenamiento. `null` si no se pudieron calcular (`NaN`). |
| `metricas.test.r2`, `metricas.test.ecm` | número o `null` | R² y ECM en test. |

Los nombres dentro de `modelo` son los mismos que los atributos de `ModeloLineal`, para no tener que traducirlos.

## 7. Cómo guardar y recuperar un modelo

Funciones `guardar_modelo` y `cargar_modelo` de `prototipos/prototipo_json.py`:

```python
from sikorius.nucleo.modelo import entrenar_modelo, metricas_modelo
from prototipo_json import cargar_modelo, guardar_modelo

# Guardar
modelo = entrenar_modelo(train, features, "median_house_value")
metricas = metricas_modelo(modelo, train, test)
ruta = "modelo_housing.json"
guardar_modelo(ruta, modelo, metricas, "Mi primer modelo")

# Recuperar
modelo, informacion = cargar_modelo(ruta)
print(informacion["formula"])
print(informacion["metricas"]["test"]["r2"])
modelo.predecir(datos_nuevos)
```

**Pasos para guardar:**

1. Convertir el modelo y su información en un diccionario con la estructura del apartado 6. Las tuplas se pasan a listas y las métricas `NaN` a `None`.
2. Abrir el archivo en modo texto con `encoding="utf-8"`.
3. Escribir con `json.dump(datos, archivo, indent=2, ensure_ascii=False, allow_nan=False)`.
   - `indent=2` para que sea legible;
   - `ensure_ascii=False` para que las tildes de la descripción se vean tal cual;
   - `allow_nan=False` para que nunca se escriba un `NaN` (no es JSON estándar).

**Pasos para recuperar:**

1. Leer con `json.load`. Si el archivo no existe o no es JSON, se lanza `ErrorModelo` con un mensaje claro.
2. Validar: `formato` y `version_formato` correctos, columnas y coeficientes presentes, coeficientes numéricos y finitos, y tantos coeficientes como columnas.
3. Construir el `ModeloLineal` con los datos validados.
4. Volver a calcular la fórmula y devolver `(modelo, informacion)`.

**Dónde iría en la aplicación (por capas):**

| Capa | Archivo | Qué hace |
|---|---|---|
| Lógica (`nucleo/`) | `nucleo/persistencia.py` (nuevo, a partir de `guardar_modelo` y `cargar_modelo` de `prototipo_json.py`) | `guardar_modelo` y `cargar_modelo`. Solo conoce `ModeloLineal` y archivos |
| Estado | `sesion.py` | Llama a `nucleo/persistencia.py` y guarda el modelo cargado en la sesión |
| Presentación (`gui/`) | Panel del modelo | Botones "Guardar modelo" / "Cargar modelo", selector de archivo y campo de descripción. No lee ni escribe archivos directamente |

## 8. Prueba de concepto

Dos scripts sin interfaz gráfica, uno por método, en `prototipos/` y separados del código de la aplicación. Cada uno entrena el modelo, lo guarda con su información, lo carga, muestra esa información y comprueba que predice lo mismo que el original. Reutilizan el núcleo de la aplicación (importación, separación, preprocesado y `entrenar_modelo`), con el mismo flujo que la prueba de concepto de la historia #13: 20 % de test, semilla 42, filas con valores inexistentes eliminadas y modelo múltiple con las 8 columnas numéricas.

```bash
uv run python prototipos/prototipo_json.py                    # JSON (elegido)
uv run --with joblib python prototipos/prototipo_joblib.py    # joblib + ejemplo de seguridad
```

joblib no se añade al proyecto: su prototipo se ejecuta con `uv run --with joblib`.

Salida con JSON:

```
Guardado en modelo_housing.json (1123 bytes)

Descripción: Modelo de ejemplo: precio de la vivienda en California.
Entradas: longitude, latitude, housing_median_age, total_rooms, total_bedrooms, population, households, median_income
Salida: median_house_value
Fórmula: median_house_value = -42190.3182 * longitude - 42052.1556 * latitude + 1184.1041 * housing_median_age - 7.3599 * total_rooms + 104.2865 * total_bedrooms - 43.0603 * population + 65.7621 * households + 40206.4320 * median_income - 3537030.9757
  entrenamiento  R² = 0.6397   ECM = 4828367481.48
  test           R² = 0.6235   ECM = 4900825641.53

Mismas predicciones que el original: True
```

Con joblib la salida es la misma, salvo el archivo (`modelo_housing.joblib`, 783 bytes), y al final se añade el ejemplo de seguridad del apartado 4. La fórmula y las métricas coinciden con las de la investigación de regresión.

**Validación del JSON.** Se comprobó que `cargar_modelo` rechaza, con un mensaje claro, un archivo que no es JSON, un JSON que no es un modelo de SIKORIUS, una versión de formato desconocida, un coeficiente de menos y un coeficiente escrito como texto (`"os.system('x')"`).

## 9. Dificultades encontradas y soluciones

| Dificultad | Solución |
|---|---|
| JSON no acepta tuplas ni arrays de numpy | `ModeloLineal` ya guarda `float` normales en tuplas. Se pasan a lista con `list(...)`. Con arrays habría que usar `.tolist()` |
| Las métricas pueden ser `NaN` (R² cuando la salida no varía). `json.dump` escribe `NaN` por defecto, que no es JSON estándar y otros programas no lo leen | Guardar `NaN` como `null`, leer `null` como `NaN` y usar `allow_nan=False` para detectar cualquier otro caso |
| `json.load` no ejecuta código, pero puede devolver cualquier cosa si el archivo se ha modificado | Validar cada campo antes de construir el modelo y lanzar `ErrorModelo` con un mensaje que la GUI pueda mostrar |
| `true`/`false` pasan la comprobación `isinstance(valor, int)` porque `bool` es subclase de `int` | Rechazar `bool` explícitamente al validar números |
| La fórmula guardada podría no cuadrar con los coeficientes si alguien edita el archivo | Guardarla para que el archivo sea legible, pero volver a calcularla al cargar |
| Por defecto, `json.dump` escribe las tildes de la descripción como `\u00e9` | `ensure_ascii=False` y abrir el archivo con `encoding="utf-8"` |
| El archivo de joblib depende de la ruta `sikorius.nucleo.modelo.ModeloLineal`, y el proyecto se está reorganizando | Comprobado durante la investigación: si la clase cambia de módulo, el archivo no carga. Es uno de los motivos para elegir JSON |
| Probar joblib sin añadirlo al proyecto | Ejecutar su prototipo con `uv run --with joblib`, como se hizo con scikit-learn en la historia de regresión |
| Hacer visible el riesgo de pickle sin hacer nada peligroso | Usar `print` como función en `__reduce__` y crear los archivos trampa en una carpeta temporal que se borra al terminar |

## 10. Archivos

- `prototipos/prototipo_json.py`: prototipo con JSON (método elegido). Guarda y carga con validación; sus funciones `guardar_modelo` y `cargar_modelo` son la base del futuro `nucleo/persistencia.py`.
- `prototipos/prototipo_joblib.py`: prototipo con joblib (descartado) y ejemplo inofensivo de ejecución de código al cargar con `pickle` y `joblib`.
- `prototipos/modelo_housing.json` y `prototipos/modelo_housing.joblib`: archivos que generan los prototipos. No se suben al repositorio.

## 11. Referencias

- Python, módulo `pickle` (advertencia de seguridad al principio de la página): https://docs.python.org/3/library/pickle.html
- Python, módulo `json`: https://docs.python.org/3/library/json.html
- scikit-learn, *Model persistence*: https://scikit-learn.org/stable/model_persistence.html
- joblib, *Persistence*: https://joblib.readthedocs.io/en/stable/persistence.html

Versiones usadas: Python 3.12, numpy 2.5.4 (las del `uv.lock` del proyecto) y, fuera del proyecto con `--with`, joblib 1.6.0. Para las pruebas de compatibilidad: Python 3.11 y 3.13, joblib 1.3.2 y numpy 1.25.2.
