# SIKORIUS

Aplicación de escritorio en Python que permite crear y visualizar modelos de regresión lineal simple y múltiple a partir de datos almacenados en archivos CSV, Excel y bases de datos SQLite. Con ella se pueden hacer predicciones, así como guardar los modelos y cargarlos más tarde, todo desde una interfaz gráfica.

## Requisitos

- [Git](https://git-scm.com/) 
- [Investigación de librerías de interfaz gráfica](documentacion_gui.md): comparación entre NiceGUI y Streamlit y por qué se eligió NiceGUI (US 12).
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

uv se encarga de instalar la versión de Python del proyecto (fijada en `.python-version`), crear el entorno virtual e instalar las dependencias. No hace falta instalar Python ni usar `pip`.

## Instalación

```bash
git clone https://github.com/xabierpc/SIKORIUS.git
cd SIKORIUS
git switch dev
uv sync
```

`uv sync` crea el entorno virtual en `.venv/` e instala exactamente las versiones indicadas en `uv.lock`.

## Ejecución

```bash
uv run sikorius
```
## Tests

```bash
uv run pytest -q                                   # ejecutar los tests
uv run pytest --cov --cov-report=term-missing      # con cobertura
uv run ruff check src tests                        # revisar el estilo
```

## Datos

Los datasets y los modelos generados **no se suben al repositorio**. Cada desarrollador los guarda en local en la carpeta `data/` en la raíz del proyecto, que está excluida en el `.gitignore`.

## Estructura

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
│   └── gui/             # Tests de la interfaz
├── docs/                # Documentación del proyecto
├── data/                # Datos locales (no se sube)
├── .vscode/             # Configuración compartida de VS Code
├── pyproject.toml       # Configuración, dependencias, ruff y pytest
├── uv.lock              # Versiones exactas de las dependencias
└── .python-version      # Versión de Python del proyecto

## Contribuir

Antes de empezar a trabajar, lee [CONTRIBUTING.md](CONTRIBUTING.md): modelo de ramas, estilo de commits y cómo añadir dependencias.