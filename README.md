# SIKORIUS

Aplicación de escritorio en Python que permite crear y visualizar modelos de regresión lineal simple y múltiple a partir de datos almacenados en archivos CSV, Excel y bases de datos SQLite. Con ella se pueden hacer predicciones, así como guardar los modelos y cargarlos más tarde, todo desde una interfaz gráfica.

## Requisitos

- [Git](https://git-scm.com/)
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

## Datos

Los datasets y los modelos generados **no se suben al repositorio**. Cada desarrollador los guarda en local en la carpeta `data/` en la raíz del proyecto, que está excluida en el `.gitignore`.

## Estructura

```
SIKORIUS/
├── src/sikorius/     # Código fuente
├── docs/             # Documentación del proyecto
├── data/             # Datos locales (no se sube)
├── pyproject.toml    # Configuración del proyecto y dependencias
├── uv.lock           # Versiones exactas de las dependencias
└── .python-version   # Versión de Python del proyecto
```

## Contribuir

Antes de empezar a trabajar, lee [CONTRIBUTING.md](CONTRIBUTING.md): modelo de ramas, estilo de commits y cómo añadir dependencias.