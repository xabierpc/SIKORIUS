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

Seguimos la [PEP 8](https://peps.python.org/pep-0008/). El formato se aplica automáticamente con **autopep8**,
configurado en el `pyproject.toml`, así que todos formateamos igual.

- **Herramienta**:
- Instala la extensión **autopep8** de Microsoft en VS Code. El código se formatea al guardar.
- autopep8 corrige sangría, espacios, líneas en blanco y líneas largas. **No** ordena imports ni revisa los nombres: eso es responsabilidad de cada uno y se revisa en las Pull Requests.
- Para revisar desde la terminal: `uv run autopep8 --diff -r src tests` muestra lo que cambiaría sin tocar nada.

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
git switch -c feature/10-importacion-datos # crea la rama y se cambia a ella
```

### Trabajar y hacer commits

```bash
git status                  # revisa qué ha cambiado (¡sin archivos de datos!)
git add <archivos>
git commit -m "Añade lectura de ficheros CSV"
git push -u origin feature/10-importacion-datos   # el primer push; después basta con git push
```

### Actualizar la rama con los últimos cambios de dev

Antes de fusionar, incorpora a tu rama lo que otros hayan subido a `dev`:

```bash
git switch dev
git pull
git switch feature/10-importacion-datos
git merge dev
```

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
git merge --no-ff feature/10-importacion-datos
git push

```

### Publicar una release en main

Solo cuando `dev` tiene una versión estable, y de acuerdo con todo el grupo:

```bash
git switch main
git pull
git merge --no-ff dev
git push
```

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
