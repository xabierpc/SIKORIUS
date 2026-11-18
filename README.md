# SIKORIUS

[![Tests](https://github.com/xabierpc/SIKORIUS/actions/workflows/tests.yml/badge.svg?branch=dev)](https://github.com/xabierpc/SIKORIUS/actions/workflows/tests.yml)

Aplicación de escritorio en Python para crear y visualizar modelos de regresión lineal simple y múltiple a partir de datos almacenados en archivos CSV, Excel y bases de datos SQLite, hacer predicciones y guardar los modelos para cargarlos más tarde, todo desde una interfaz gráfica.

El proyecto está en desarrollo. La versión actual es la **0.2.0**: prepara los datos y crea y evalúa modelos de regresión lineal.
## Funcionalidades de la versión 0.2.0

- **Cargar un dataset** desde un explorador de archivos: CSV, Excel (`.xlsx` y `.xls`, con una sola hoja con datos) y SQLite (`.sqlite` y `.db`, con una sola tabla), y verlo en una tabla.
- **Elegir las columnas del modelo**: una o varias columnas de entrada (*features*) y una de salida (*target*), solo entre las columnas numéricas.
- **Separar los datos en entrenamiento y test**, indicando el porcentaje de test y una semilla para que la separación se pueda repetir.
- **Detectar y tratar los valores nulos** de las columnas elegidas, en entrenamiento y en test: eliminar las filas, o rellenar con la media, la mediana o un valor constante.
- **Crear el modelo de regresión lineal** simple o múltiple con los datos de entrenamiento. Se crea automáticamente al aplicar el preprocesado, o con el botón "Crear modelo".
- **Ver la fórmula del modelo** con los nombres de las columnas, y añadirle una descripción opcional.
- **Evaluar el modelo**: R² y error cuadrático medio (ECM) en entrenamiento y en test.
- **Ver el gráfico del ajuste**: en regresión simple, los puntos y la recta del modelo; en múltiple, el valor real frente al predicho.
- **Guardar el modelo** en un archivo JSON (`.json`) elegido con un diálogo: guarda la fórmula, los coeficientes, las columnas, las métricas y la descripción, pero no los datos ni los gráficos.

Pendiente para próximas versiones: hacer predicciones y cargar modelos guardados.

## Requisitos

- [Git](https://git-scm.com/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

uv se encarga de instalar la versión de Python del proyecto (fijada en `.python-version`), crear el entorno virtual e instalar las dependencias. No hace falta instalar Python ni usar `pip`.

## Instalación

```bash
git clone https://github.com/xabierpc/SIKORIUS.git
cd SIKORIUS
uv sync
```

`uv sync` crea el entorno virtual en `.venv/` e instala exactamente las versiones indicadas en `uv.lock`.

También se puede descargar una versión publicada sin usar Git: en la página [Releases](https://github.com/xabierpc/SIKORIUS/releases) se descarga el archivo *Source code (zip)*, se descomprime y, dentro de la carpeta, se ejecuta `uv sync`.

Para desarrollar, el trabajo se hace desde la rama `dev` (`git switch dev`), como explica [CONTRIBUTING.md](CONTRIBUTING.md).

## Ejecución

```bash
uv run sikorius
```

## Asistente (opcional)

El botón flotante de abajo a la derecha abre un chat con una LLM de
[Groq](https://console.groq.com). Explica el dataset y el modelo, y puede
proponer cambios al dataset (eliminar o renombrar columnas, filtrar filas,
quitar duplicados, nulos o atípicos, convertir texto a número). Los cambios
se ven antes de aplicarlos y se pueden deshacer.

Para activarlo, copia `.env.example` como `.env` y pon tu clave
(`GROQ_API_KEY=...`). El `.env` no se sube al repositorio. Sin clave, la
aplicación funciona igual y el asistente sale desactivado. A Groq solo se le
mandan los nombres de las columnas, estadísticas resumidas y el modelo, no
las filas del dataset. Los tests usan una LLM falsa: no necesitan clave ni
red. Más detalles en [`docs/asistente.md`](docs/asistente.md).

## Tests

```bash
uv run pytest -q                                   # ejecutar los tests
uv run pytest --cov --cov-report=term-missing      # con cobertura
uv run ruff format --check src tests               # revisar el formato
uv run ruff check src tests                        # revisar el estilo
```

GitHub Actions ejecuta estas mismas comprobaciones en cada push a cualquier
rama y en cada pull request hacia `dev` o `main`
(`.github/workflows/tests.yml`). La insignia del principio indica si la
última ejecución en `dev` ha pasado. El funcionamiento del flujo está
explicado en [`docs/integracion-continua.md`](docs/integracion-continua.md).

## Datos

Los datasets y los modelos generados **no se suben al repositorio**. Cada desarrollador los guarda en local en la carpeta `data/` en la raíz del proyecto, que está excluida en el `.gitignore`.

## Estructura

Arquitectura en capas: `gui → aplicacion → datos → dominio`. Cada capa solo
importa las que tiene por debajo, y `tests/test_arquitectura.py` lo comprueba.

```
SIKORIUS/
├── src/sikorius/
│   ├── gui/             # Presentación (NiceGUI). Solo habla con la sesión
│   │   ├── componentes/ # Piezas reutilizables: tabla, explorador...
│   │   ├── paneles/     # Un panel por paso de la aplicación
│   │   └── pagina.py    # Coloca los paneles en la página
│   ├── aplicacion/      # Sesión (estado del flujo) y asistente
│   ├── datos/           # Importar datasets, guardar modelos y Groq
│   ├── dominio/         # Lógica sin interfaz ni archivos: columnas,
│   │                    # separación, preprocesado, modelo y los
│   │                    # cambios que puede proponer el asistente
│   └── app.py           # Punto de entrada
├── tests/               # Misma estructura que src/sikorius
│   ├── aplicacion/      # Tests de la sesión
│   ├── datos/           # Tests de importación y persistencia
│   ├── dominio/         # Tests de la lógica
│   ├── gui/             # Tests de la interfaz
│   ├── conftest.py      # Datos y sesiones comunes a los tests
│   └── test_arquitectura.py  # Vigila la separación en capas
├── docs/                # Documentación del proyecto
├── data/                # Datos locales (no se sube)
├── .github/workflows/   # Integración continua (GitHub Actions)
├── .vscode/             # Configuración compartida de VS Code
├── pyproject.toml       # Configuración, dependencias, ruff y pytest
├── uv.lock              # Versiones exactas de las dependencias
└── .python-version      # Versión de Python del proyecto
```

## Contribuir

Antes de empezar a trabajar, lee [CONTRIBUTING.md](CONTRIBUTING.md): modelo de ramas, guía de estilo, mensajes de commit y cómo añadir dependencias.