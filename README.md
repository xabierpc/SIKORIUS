# SIKORIUS

[![Tests](https://github.com/xabierpc/SIKORIUS/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/xabierpc/SIKORIUS/actions/workflows/tests.yml)

Aplicación en Python para crear y visualizar modelos de regresión lineal simple y múltiple a partir de datos almacenados en archivos CSV, Excel y bases de datos SQLite, hacer predicciones y guardar los modelos para cargarlos más tarde, todo desde una interfaz gráfica que se abre en el navegador.

La versión actual es la **1.0.0**, la versión final del proyecto.

## Funcionalidades

- **Cargar un dataset** CSV, Excel o SQLite con un explorador de archivos y verlo en una tabla.
- **Elegir las columnas del modelo**: una o varias columnas de entrada (*features*) y una de salida (*target*). Solo se admiten columnas numéricas: si se elige otra, la aplicación avisa al confirmar.
- **Separar los datos en entrenamiento y test**, con el porcentaje de test y una semilla para que la separación se pueda repetir.
- **Detectar y tratar los valores inexistentes** de las columnas elegidas: eliminar las filas, o rellenar con la media, la mediana o un valor constante.
- **Crear el modelo de regresión lineal** simple o múltiple con los datos de entrenamiento.
- **Ver la fórmula del modelo**, sus métricas (R² y error cuadrático medio, ECM) en entrenamiento y test, y el gráfico del ajuste.
- **Añadir una descripción** al modelo.
- **Guardar el modelo** en un archivo `.json` y **cargarlo** más tarde.
- **Hacer predicciones** con el modelo creado o cargado.

## Requisitos

- [Git](https://git-scm.com/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Un navegador web (la interfaz se abre en él).

Probado en Linux con uv 0.11 y 0.13.

uv se encarga de instalar la versión de Python del proyecto (fijada en `.python-version`), crear el entorno virtual e instalar las dependencias. No hace falta instalar Python ni usar `pip`.

Para comprobar que uv está instalado, abre una terminal nueva y ejecuta `uv --version`. Si no se reconoce el comando, cierra y vuelve a abrir la terminal después de instalarlo.

## Instalación

```bash
git clone https://github.com/xabierpc/SIKORIUS.git
cd SIKORIUS
uv sync
```

`uv sync` descarga Python si hace falta, crea el entorno virtual en `.venv/` e instala exactamente las versiones indicadas en `uv.lock`. La primera vez tarda un poco.

También se puede descargar una versión publicada sin usar Git: en la página [Releases](https://github.com/xabierpc/SIKORIUS/releases) se descarga el archivo *Source code (zip)*, se descomprime y, dentro de la carpeta, se ejecuta `uv sync`.

## Ejecución

Desde la carpeta del proyecto:

```bash
uv run sikorius
```

La aplicación abre una pestaña del navegador en <http://localhost:8080>. Si no se abre sola, escribe esa dirección en el navegador. Para cerrar la aplicación, pulsa `Ctrl+C` en la terminal.

La aplicación usa siempre el puerto 8080. Si al arrancar aparece un error de dirección en uso (*address already in use*), es que ya hay otro programa en ese puerto, normalmente otra ejecución de SIKORIUS: ciérrala y vuelve a ejecutar `uv run sikorius`.

## Formato de los archivos de datos

La aplicación acepta estos archivos:

| Formato | Extensiones | Condiciones |
|---|---|---|
| CSV | `.csv` | La **primera fila** contiene los nombres de las columnas. El separador puede ser coma (`,`), punto y coma (`;`) o tabulador; con punto y coma, el decimal es la coma (`1,5`). Codificación UTF-8 o Windows-1252. |
| Excel | `.xlsx`, `.xls` | La **primera fila** contiene los nombres de las columnas. Solo **una hoja** con datos (las hojas vacías no molestan). |
| SQLite | `.sqlite`, `.db` | La base de datos contiene **una sola tabla**. La aplicación la lee entera, sin pedir su nombre. |

Además:

- Las columnas de entrada y de salida del modelo deben ser **numéricas**. El archivo puede tener otras columnas (texto, fechas…): se ven en la tabla y aparecen en los selectores, pero si se eligen, al pulsar **Confirmar selección** la aplicación avisa de que no son numéricas.
- Puede haber **valores inexistentes** (celdas vacías). No hace falta quitarlos antes: la aplicación los detecta y permite tratarlos en el paso de preprocesado.
- Hacen falta al menos 5 filas para separar los datos en entrenamiento y test.

El repositorio no incluye datasets. Para probar la aplicación, guarda este ejemplo en un archivo `ejemplo.csv` y cárgalo:

```csv
superficie,habitaciones,ciudad,precio
80,3,Coruña,150000
95,4,Vigo,
60,2,Coruña,110000
120,4,Lugo,210000
70,2,Vigo,125000
100,3,Lugo,180000
85,3,Coruña,
110,4,Vigo,195000
```

## Guía de uso

La aplicación se divide en pestañas que se abren a medida que se completa cada paso. El botón **Continuar** de la barra superior lleva al paso siguiente cuando el actual está completo, y las pestañas sirven para volver atrás. Cambiar un paso borra los que van detrás (por ejemplo, elegir otras columnas obliga a separar los datos otra vez).

1. **Inicio.** Pulsa **Subir dataset** y elige el archivo en el explorador, que se abre en tu carpeta personal, o **Cargar modelo** para abrir un modelo guardado (paso 7).
2. **Datos.** Se ven la ruta del archivo, el número de filas y columnas y la tabla. Con **Cargar otro** se cambia de dataset.
3. **Variables y separacion.**
   - En **Columnas del modelo**, elige una o varias columnas en **Features (selección múltiple)** y una en **Target (columna de salida)**, y pulsa **Confirmar selección**.
   - En **Entrenamiento y test**, escribe el **Porcentaje de test (%)** (entre 1 y 99) y la **Semilla** (un entero, 0 o mayor), y pulsa **Separar datos**. Con la misma semilla, la separación sale siempre igual.
4. **Preprocesado.** La tabla muestra cuántos valores inexistentes tiene cada columna elegida en entrenamiento y en test. Elige la **Estrategia de tratamiento** (eliminar filas, o rellenar con la media, la mediana o un **Valor constante**) y pulsa **Aplicar preprocesado**. La media y la mediana se calculan solo con los datos de entrenamiento. Al aplicarlo se crea el modelo.
5. **Modelo.** Se ven la fórmula, las métricas R² y ECM de entrenamiento y test y el gráfico del ajuste: en regresión simple, los puntos y la recta; en múltiple, el valor real frente al predicho. El botón **Crear modelo** vuelve a crearlo si hace falta. En **Descripción (opcional)** se puede explicar para qué es el modelo.
6. **Guardar modelo.** Pulsa **Guardar modelo**, elige la carpeta, escribe el **Nombre del archivo** y pulsa **Guardar**. La extensión `.json` se añade sola. El archivo guarda la fórmula, los coeficientes, las columnas, las métricas y la descripción, pero **no los datos** ni los gráficos.
7. **Cargar modelo.** En **Inicio**, pulsa **Cargar modelo** y elige un archivo `.json` guardado con SIKORIUS. Se abre directamente la pestaña **Modelo** con su fórmula, métricas y descripción (sin gráfico, porque los datos no se guardan). Si el modelo actual tiene cambios sin guardar, la aplicación pide confirmación antes de sustituirlo.
8. **Prediccion.** En la pestaña **Modelo**, escribe un valor para cada columna de entrada (se admite punto o coma decimal) y pulsa **Realizar predicción** o `Intro`. El resultado aparece como `<salida> = <valor>`.

### Mensajes de error frecuentes

| Mensaje | Qué hacer |
|---|---|
| *El archivo no contiene datos* | El archivo está vacío o solo tiene la fila de nombres. |
| *El archivo está dañado o no es CSV válido* / *…no es un excel válido* | El archivo no corresponde a su extensión o está corrupto. Ábrelo con su programa y vuelve a guardarlo. |
| *Hay filas con más campos que el encabezado* | Alguna fila del CSV tiene más separadores que la primera. Corrígela. |
| *El libro tiene datos en más de una hoja* | Deja los datos en una sola hoja del Excel. |
| *La base de datos contiene más de una tabla* / *…no contiene ninguna tabla* | Deja una sola tabla en la base SQLite. |
| *Estas columnas no son numéricas y no se pueden usar en una regresión lineal* | Elige solo columnas numéricas. |
| *El porcentaje de test debe ser un número entre 1 y 99* / *La semilla debe ser un número entero (0 o mayor)* | Corrige el valor del formulario de separación. |
| *El archivo … está dañado o no es un modelo guardado con SIKORIUS* | Solo se pueden cargar archivos `.json` guardados con la aplicación. |

## Seguridad de los modelos guardados

Los modelos se guardan en **JSON**, un formato de texto. Al cargarlos, la aplicación solo lee datos y los comprueba antes de usarlos: **nunca ejecuta código del archivo**. Por eso se eligió JSON y no `pickle` ni `joblib`, que sí pueden ejecutar código al cargar (ver [`docs/investigacion-persistencia.md`](docs/investigacion-persistencia.md)).

## Limitaciones conocidas

- Solo se lee **una hoja** de Excel y **una tabla** de SQLite; si hay más, la aplicación avisa en lugar de elegir una.
- Solo se pueden usar columnas **numéricas** como entrada y salida. Las categóricas habría que convertirlas a números antes.
- Columnas cuyo nombre solo se distingue por el tipo (por ejemplo, `1` numérico y `"1"` texto) aparecen repetidas en los selectores y no se pueden elegir por separado.
- La aplicación está pensada para usarse **en local por una persona**: si se abre en otra pestaña o se recarga, se ve el mismo trabajo.
- Un modelo cargado no muestra el gráfico del ajuste, porque el archivo no guarda los datos.

## Datos

Los datasets y los modelos guardados **no se suben al repositorio**. Cada desarrollador los guarda en local en la carpeta `data/` en la raíz del proyecto, que está excluida en el `.gitignore`. Esa carpeta no viene al clonar: hay que crearla (`mkdir data`).

## Desarrollo

Para desarrollar, el trabajo se hace desde la rama `dev` (`git switch dev`), como explica [CONTRIBUTING.md](CONTRIBUTING.md): modelo de ramas, guía de estilo, mensajes de commit, dependencias con uv y procedimiento de release.

### Tests

```bash
uv run pytest -q                                   # ejecutar los tests
uv run pytest --cov --cov-report=term-missing      # con cobertura
uv run ruff format --check src tests               # revisar el formato
uv run ruff check src tests                        # revisar el estilo
```

Las pruebas funcionales del plan de pruebas, que manejan la aplicación en un navegador, se ejecutan aparte: ver [`docs/pruebas_funcionales.md`](docs/pruebas_funcionales.md).

GitHub Actions ejecuta estas mismas comprobaciones en cada push a cualquier rama y en cada pull request hacia `dev` o `main` (`.github/workflows/tests.yml`). La insignia del principio indica si la última ejecución en `main` ha pasado. El funcionamiento del flujo está explicado en [`docs/integracion-continua.md`](docs/integracion-continua.md).

### Estructura

Arquitectura en capas: `gui → aplicacion → datos → dominio`. Cada capa solo importa las que tiene por debajo, y `tests/test_arquitectura.py` lo comprueba. La descripción de cada módulo está en [`docs/estructura-codigo.md`](docs/estructura-codigo.md).

```
SIKORIUS/
├── src/sikorius/
│   ├── gui/             # Presentación (NiceGUI). Solo habla con la sesión
│   │   ├── componentes/ # Piezas reutilizables: tabla, explorador...
│   │   ├── paneles/     # Un panel por paso de la aplicación
│   │   └── pagina.py    # Coloca los paneles en la página
│   ├── aplicacion/      # Sesión: estado del flujo y operaciones de la GUI
│   ├── datos/           # Importar datasets y guardar y cargar modelos
│   ├── dominio/         # Lógica sin interfaz ni archivos: columnas,
│   │                    # separación, preprocesado, modelo, predicción
│   └── app.py           # Punto de entrada
├── tests/               # Misma estructura que src/sikorius
├── docs/                # Documentación del proyecto
├── prototipos/          # Pruebas de concepto de las investigaciones
├── herramientas/        # Pruebas funcionales (Playwright y LLM), fuera del paquete
├── data/                # Datos locales (no se sube; se crea a mano)
├── .github/workflows/   # Integración continua (GitHub Actions)
├── .vscode/             # Configuración compartida de VS Code
├── pyproject.toml       # Configuración, dependencias, ruff y pytest
├── uv.lock              # Versiones exactas de las dependencias
└── .python-version      # Versión de Python del proyecto
```

### Documentación

Índice completo en [`docs/README.md`](docs/README.md).