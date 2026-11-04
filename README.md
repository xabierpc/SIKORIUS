# SIKORIUS

[![Tests](https://github.com/xabierpc/SIKORIUS/actions/workflows/tests.yml/badge.svg?branch=dev)](https://github.com/xabierpc/SIKORIUS/actions/workflows/tests.yml)

Aplicación de escritorio en Python para crear y visualizar modelos de regresión lineal simple y múltiple a partir de datos almacenados en archivos CSV, Excel y bases de datos SQLite, hacer predicciones y guardar los modelos para cargarlos más tarde, todo desde una interfaz gráfica.

El proyecto está en desarrollo. La versión actual es la **0.1.0**: prepara los datos, pero todavía no crea modelos.

## Funcionalidades de la versión 0.1.0

- **Cargar un dataset** desde un explorador de archivos: CSV, Excel (`.xlsx` y `.xls`, con una sola hoja con datos) y SQLite (`.sqlite` y `.db`, con una sola tabla), y verlo en una tabla.
- **Elegir las columnas del modelo**: una o varias columnas de entrada (*features*) y una de salida (*target*), solo entre las columnas numéricas.
- **Separar los datos en entrenamiento y test**, indicando el porcentaje de test y una semilla para que la separación se pueda repetir.
- **Detectar y tratar los valores nulos** de las columnas elegidas, en entrenamiento y en test: eliminar las filas, o rellenar con la media, la mediana o un valor constante.

Pendiente para próximas versiones: crear el modelo de regresión lineal y ver su fórmula y su gráfica, evaluarlo, hacer predicciones, y guardar y cargar modelos.

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

## Tests

```bash
uv run pytest -q                                   # ejecutar los tests
uv run pytest --cov --cov-report=term-missing      # con cobertura
uv run ruff format --check src tests               # revisar el formato
uv run ruff check src tests                        # revisar el estilo
```

GitHub Actions ejecuta estas mismas comprobaciones en cada push y pull
request a `dev` y `main` (`.github/workflows/tests.yml`). La insignia del
principio indica si la última ejecución en `dev` ha pasado.

## Datos

Los datasets y los modelos generados **no se suben al repositorio**. Cada desarrollador los guarda en local en la carpeta `data/` en la raíz del proyecto, que está excluida en el `.gitignore`.

## Estructura

```
SIKORIUS/
├── src/sikorius/
│   ├── nucleo/          # Lógica sin interfaz: importar, columnas,
│   │                    # separación, preprocesado
│   ├── gui/
│   │   ├── componentes/ # Piezas reutilizables: tabla, explorador...
│   │   ├── paneles/     # Un panel por paso de la aplicación
│   │   └── pagina.py    # Coloca los paneles en la página
│   ├── sesion.py        # Estado de la sesión de trabajo
│   └── app.py           # Punto de entrada
├── tests/
│   ├── nucleo/          # Tests de la lógica
│   ├── gui/             # Tests de la interfaz
│   ├── conftest.py      # Datos y sesiones comunes a los tests
│   └── test_*.py        # Tests de la sesión y de la separación en capas
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