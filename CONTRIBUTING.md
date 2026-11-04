# Cómo contribuir a SIKORIUS

Esta guía recoge las normas que seguimos todos los miembros del grupo para trabajar en el repositorio.

## 1. Normas básicas

- Cada uno trabaja desde su propio clon local del repositorio.
- **Nunca se hacen commits directamente en `main` ni en `dev`.** Todo el trabajo se hace en ramas `feature/`, `fix/` o `docs/`.
- **Nunca se suben archivos de datos**: ni datasets, ni modelos generados, ni resultados.
- Los datos se guardan en local en la carpeta `data/` de la raíz del proyecto. Está incluida en el `.gitignore`, así que Git la ignora.
- Antes de cada commit, revisa con `git status` qué archivos vas a incluir y comprueba que no hay archivos de datos.
- El entorno virtual (`.venv/`) tampoco se sube.

## 2. Guía de estilo de código (PEP 8)

Seguimos la [PEP 8](https://peps.python.org/pep-0008/). El formato y la
revisión se hacen con **ruff**, configurado en el `pyproject.toml`, así que
todos formateamos igual.

- **Herramienta**:
- Instala la extensión **Ruff** (Astral Software) en VS Code y desactiva
  autopep8 si la tenías. El archivo `.vscode/settings.json` del repo ya
  configura Ruff como formateador, formatea al guardar y ordena los imports.
- Elige el intérprete del proyecto: `Ctrl+Shift+P` → "Python: Select
  Interpreter" → `.venv`.
- Desde la terminal:
  - `uv run ruff format src tests` formatea el código.
  - `uv run ruff check src tests` busca errores y avisos de estilo;
    con `--fix` corrige los que sabe corregir solo.
- Ruff no parte cadenas, comentarios ni docstrings largos: esas líneas
  hay que cortarlas a mano.

- **Nombres** (en español, sin tildes ni ñ):
- Variables, funciones y métodos: `snake_case`. P. ej.: `calcular_metricas`, `datos_procesados`.
- Clases: `CapWords`. P. ej.: `ProcesadorCSV`.
- Constantes: `MAYÚSCULAS_CON_GUION_BAJO`. P. ej.: `MAX_ITERACIONES = 100`.
- Módulos: minúsculas y cortos. P. ej.: `datos.py`.
- Uso interno: con guion bajo delante. P. ej.: `_validar_columnas()`.

- **Formato**:
- Indentación de 4 espacios, nunca tabuladores.
- Líneas de 79 caracteres como máximo. Para partir una línea se usan paréntesis, no `\`.
- Dos líneas en blanco entre funciones y clases; una entre métodos.
- Espacios alrededor de los operadores y después de las comas. Sin espacios dentro de paréntesis ni en `=` de argumentos con nombre: `f(x=1)`.

- **Imports**:
- Uno por línea, en tres bloques separados por una línea en blanco: biblioteca estándar, terceros y propios
(`from sikorius.datos import ...`). Dentro de cada bloque, en orden alfabético.

- **Comentarios**
- Solo cuando expliquen el *porqué*, no lo que ya dice el código.
- Docstring (`"""..."""`) en cada módulo, clase y función pública.

## 3. Modelo de ramas

| Rama | Función |
| ------ | --------- |
| `main` | Solo versiones estables. Únicamente recibe cambios desde `dev` al publicar una release. |
| `dev` | Rama de integración del desarrollo. Aquí se fusionan las ramas de trabajo terminadas. |
| `feature/<numero>-<descripcion>` | Una rama por historia de usuario o tarea. Se crea desde `dev`. |
| `fix/<descripcion>` | Una rama por corrección de errores. Se crea desde `dev`. |
| `docs/<descripcion>` | Una rama por cambio de documentación. Se crea desde `dev`. |

Formato de los nombres:

- En minúsculas, sin tildes ni espacios, con palabras separadas por guiones.
- En las `feature`, `<numero>` es el número de la historia de usuario o tarea.

Ejemplos: `feature/10-importacion-datos`, `fix/error-lectura-csv`, `docs/actualizar-readme`.

## 4. Flujo de trabajo

### Clonar el repositorio

```bash
git clone https://github.com/xabierpc/SIKORIUS.git
cd SIKORIUS
git switch dev
```

### Crear el entorno y probarlo

```bash
uv sync
uv run sikorius
```

### Configurar Git (una sola vez, después de clonar)

```bash
git config pull.ff only                     # git pull nunca crea fusiones por su cuenta
git config core.editor "code --wait"        # editor para los mensajes de fusión
```

Y crea el archivo `.git/hooks/pre-commit` con este contenido, para que Git
no te deje hacer commits en `dev` ni en `main` por despiste:

```sh
#!/bin/sh
rama=$(git branch --show-current)
if [ "$rama" = "dev" ] || [ "$rama" = "main" ]; then
    echo "No hagas commits en $rama: crea antes una rama (git switch -c fix/...)" >&2
    exit 1
fi
```

En Linux y macOS, dale permiso de ejecución: `chmod +x .git/hooks/pre-commit`.

### Crear una rama de trabajo

```bash
git switch dev
git pull                                        # trae lo último de dev
git switch -c feature/10-101-importacion-datos  # crea la rama y se cambia a ella
```

El primer número es el de la historia de usuario y el segundo, el de la tarea.

### Trabajar y hacer commits

```bash
git branch --show-current   # comprueba que estás en tu rama, NO en dev
git status                  # revisa qué ha cambiado (¡sin archivos de datos!)
git add <archivos>
git commit -m "Añade lectura de ficheros CSV"
git push -u origin feature/10-101-importacion-datos   # el primer push; después basta con git push
```

Un cambio solo pertenece a una rama cuando haces el commit: si cambias de
rama antes, los archivos modificados se van contigo. Haz el commit **antes**
de volver a `dev`, y el primer `push` **después** del primer commit, para no
subir una rama vacía.

### Actualizar la rama con los últimos cambios de dev

Antes de fusionar, incorpora a tu rama lo que otros hayan subido a `dev`:

```bash
git switch dev
git pull
git switch feature/10-101-importacion-datos
git merge dev
```

Si aparece un **conflicto**:

1. `git status` muestra los archivos en conflicto.
2. Abre cada archivo y busca las marcas `<<<<<<<`, `=======` y `>>>>>>>`. Entre `<<<<<<<` y `=======` está tu versión; entre `=======` y `>>>>>>>`, la de `dev`.
3. Deja el contenido correcto y borra las marcas.
4. `git add <archivo>` y después `git commit` para terminar la fusión.

### Comprobar antes de fusionar

Antes de fusionar en `dev`, estos comandos tienen que salir sin errores:

```bash
uv run ruff format --check src tests   # el formato está aplicado
uv run ruff check src tests            # sin avisos
uv run pytest -q                       # todos los tests pasan
uv run sikorius                        # la aplicación arranca
```

Para ver qué partes del código cubren los tests:
`uv run pytest --cov --cov-report=term-missing`.

### Fusionar la rama en dev

Las ramas se fusionan en `dev` **siempre con un Pull Request** en GitHub;
`dev` y `main` no admiten `git push` directo.

1. Sube tu rama (`git push`) y abre un Pull Request con **base: `dev`**.
2. Espera a que la integración continua (GitHub Actions, check
   **"Ruff y pytest"**) salga en verde. Si sale en rojo, corrige en tu rama
   y vuelve a hacer `git push`: el Pull Request se actualiza solo.
3. Fusiónalo con **"Create a merge commit"**, que equivale a
   `git merge --no-ff`.
4. Actualiza tu `dev` local:

```bash
git switch dev
git pull
```

### Publicar una release en main

Solo cuando `dev` tiene una versión estable, y de acuerdo con todo el grupo:
se abre un Pull Request con **base: `main`** y **compare: `dev`**, se espera a
que la integración continua salga en verde y se fusiona con
**"Create a merge commit"**.

**Las ramas no se eliminan, ni en local ni en GitHub, para conservar el historial del trabajo.**

## 5. Mensajes de commit

- En español, en presente y en modo indicativo: «Añade…», «Corrige…», «Elimina…».
- Primera línea breve (máximo 70 caracteres), sin punto final, que diga **qué** cambia.
- Si hace falta explicar el **porqué**, se deja una línea en blanco y se añade un párrafo.
- Un commit = un cambio lógico. Mejor varios commits pequeños que uno enorme.

## 6. Dependencias con uv

El proyecto se gestiona con [uv](https://docs.astral.sh/uv/). **No se usa `pip install`** ni se edita el entorno a mano.

- Tras clonar o al traer cambios que tocan dependencias: `uv sync`
- Añadir una dependencia: `uv add <paquete>` (por ejemplo, `uv add pandas`)
- Añadir una dependencia solo de desarrollo: `uv add --dev <paquete>` (por ejemplo, `uv add --dev pytest`)
- Quitar una dependencia: `uv remove <paquete>`
- Actualizar una dependencia: `uv lock --upgrade-package <paquete>` y después `uv sync`
- Ejecutar el proyecto o cualquier comando dentro del entorno: `uv run <comando>`

Al cambiar dependencias se modifican `pyproject.toml` y `uv.lock`: **se suben los dos en el mismo commit**, en una rama de trabajo como cualquier otro cambio. Así todos instalan exactamente las mismas versiones.

## 7. README y documentación

- La documentación del proyecto va en la carpeta `docs/`; el `README.md` contiene la descripción y las instrucciones de instalación y ejecución.
- Los cambios de documentación se hacen en una rama `docs/<descripcion>` creada desde `dev` y se fusionan en `dev` como cualquier otra rama.
- Si una `feature` cambia cómo se instala o se ejecuta el proyecto, actualiza el `README.md` en esa misma rama.
