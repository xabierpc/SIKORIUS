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

### Crear una rama de trabajo

```bash
git switch dev
git pull                                   # trae lo último de dev
git switch -c feature/10-101-importacion-datos # crea la rama y se cambia a ella. El primer número corresponde a la historia y el segundo a la tarea correspondiente

```

### Trabajar y hacer commits

```bash
git status                  # revisa qué ha cambiado (¡sin archivos de datos!)
git add <archivos>
git commit -m "Añade lectura de ficheros CSV"
git push -u origin feature/10-101-importacion-datos   # el primer push; después basta con git push
```

### Actualizar la rama con los últimos cambios de dev

Antes de fusionar, incorpora a tu rama lo que otros hayan subido a `dev`:

```bash
git switch dev
git pull
git switch feature/10-101-importacion-datos
git merge dev
```

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

### Reglas de fusión según GitHub Actions

GitHub Actions ejecuta estas mismas comprobaciones en cada push a cualquier
rama (ver [`docs/integracion-continua.md`](docs/integracion-continua.md)).
Estas reglas sustituyen a las de fusionar solo con las pruebas en local:

- Una rama de trabajo (`feature`, `fix` o `docs`) solo se fusiona en `dev`
  si las comprobaciones pasan en local **y** su última ejecución en GitHub
  Actions ha terminado en verde. Se mira en la pestaña **Actions**,
  filtrando por la rama, o en el PR.
- Después de cada fusión en `dev`, se comprueba que la ejecución de GitHub
  Actions sobre `dev` también termina en verde. Si falla, se corrige en una
  rama `fix/<descripcion>` antes de fusionar ninguna otra rama.
- `dev` solo se fusiona en `main` si su última ejecución en GitHub Actions
  ha terminado en verde.


Si aparece un **conflicto**:

1. `git status` muestra los archivos en conflicto.
2. Abre cada archivo y busca las marcas `<<<<<<<`, `=======` y `>>>>>>>`. Entre `<<<<<<<` y `=======` está tu versión; entre `=======` y `>>>>>>>`, la de `dev`.
3. Deja el contenido correcto y borra las marcas.
4. `git add <archivo>` y después `git commit` para terminar la fusión.

Comprueba que el proyecto sigue funcionando (`uv run sikorius`) antes de continuar.

### Fusionar la rama en dev

Se puede hacer con un Pull Request en GitHub (base: `dev`) o en local:

```bash
git switch dev
git pull
git merge --no-ff feature/10-101-importacion-datos
git push

```

### Publicar una release en main

`main` solo recibe cambios desde `dev` al publicar una release. Los pasos
están en la sección [8. Procedimiento de release](#8-procedimiento-de-release).

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

## 8. Procedimiento de release

Una release es una versión de la aplicación publicada en GitHub. Seguimos el
[versionado semántico](https://semver.org/lang/es/) (`MAYOR.MENOR.PARCHE`):
mientras la versión empiece por `0.`, la aplicación está en desarrollo.

Los ejemplos usan la versión `0.1.0`; para otra versión, cambia el número en
todos los comandos.

### 1. Requisitos previos

- Todo el grupo está de acuerdo en publicar la versión.
- Las historias de usuario de la versión están fusionadas en `dev`.
- La última ejecución de GitHub Actions sobre `dev` está en verde.
- En local, desde `dev`, pasan todas las comprobaciones:

  ```bash
  git switch dev
  git pull
  uv sync
  uv run ruff format --check src tests
  uv run ruff check src tests
  uv run pytest -q
  ```

- Un miembro del grupo que **no haya implementado** esas historias ha probado
  la aplicación a mano (`uv run sikorius`) con los datasets de ejemplo de la
  asignatura. Los errores encontrados se corrigen en ramas `fix/` antes de
  seguir.
- El `README.md` describe las funcionalidades de la versión y cómo ejecutarla.

### 2. Actualizar la versión

El campo `version` del `pyproject.toml` tiene que ser el de la nueva versión:

```bash
grep '^version' pyproject.toml
```

Si no lo es, se cambia en una rama creada desde `dev` y se fusiona como
cualquier otra:

```bash
git switch -c fix/<numero>-version-0.1.0
# Cambia la línea a: version = "0.1.0"
uv lock
git add pyproject.toml uv.lock
git commit -m "Sube la versión a 0.1.0"
git push -u origin fix/<numero>-version-0.1.0
```

### 3. Fusionar dev en main

```bash
git switch main
git pull
git merge --no-ff dev -m "Publica la versión 0.1.0"
git diff dev            # no muestra nada: main y dev tienen el mismo código
git push
```

Si `main` está protegida y exige un pull request, en lugar de los comandos
anteriores se abre en GitHub un pull request de `dev` hacia `main`, se espera
a que GitHub Actions esté en verde y se fusiona con *Create a merge commit*.
Después: `git switch main` y `git pull`.

### 4. Crear y subir la etiqueta

La etiqueta se crea sobre el último commit de `main`, el de la fusión:

```bash
git switch main
git tag -a v0.1.0 -m "Versión 0.1.0"
git push origin v0.1.0
git show v0.1.0 --stat   # comprueba que apunta a la fusión
```

### 5. Crear la release en GitHub

1. En el repositorio, entra en **Releases** → **Draft a new release**.
2. En **Choose a tag**, elige `v0.1.0`.
3. Título: `v0.1.0`.
4. En la descripción, pega las notas de la versión (paso 6).
5. Mientras la aplicación no permita crear modelos, marca
   **Set as a pre-release**.
6. Pulsa **Publish release**.

### 6. Redactar las notas

Las notas se guardan en `docs/notas-v0.1.0.md` (en una rama `docs/` antes del
paso 3, para que entren en la versión) e incluyen:

- una descripción breve de la aplicación y del estado del proyecto;
- las funcionalidades incluidas y las correcciones, a partir de las ramas
  `feature/` y `fix/` fusionadas desde la versión anterior;
- las funcionalidades pendientes para próximas versiones;
- un enlace al `README.md` de la versión.

Para ver las ramas fusionadas desde la versión anterior (en la primera
versión, todas):

```bash
git log --first-parent --oneline --grep="^Merge branch" dev
git log --first-parent --oneline --grep="^Merge branch" v0.1.0..dev  # siguientes versiones
```

### 7. Comprobar la descarga

Un miembro del grupo descarga el código de la release en una carpeta nueva y
comprueba que se instala y arranca siguiendo el `README.md`:

1. En la página de la release, descarga **Source code (zip)**.
2. Descomprímelo en una carpeta nueva, fuera de tu clon del repositorio.
3. Dentro de la carpeta descomprimida (`SIKORIUS-0.1.0`):

   ```bash
   uv sync
   uv run sikorius
   ```

4. Carga un dataset y recorre las funcionalidades de la versión.

### 8. Después de la release

`main` y `dev` tienen el mismo código, y el desarrollo continúa en ramas
creadas desde `dev`. Las ramas y las etiquetas no se borran.
