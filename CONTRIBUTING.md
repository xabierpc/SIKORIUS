# Cómo contribuir a SIKORIUS

Esta guía recoge las normas que seguimos todos los miembros del grupo para trabajar en el repositorio.

## 1. Normas básicas

- Cada uno trabaja desde su propio clon local del repositorio.
- **Nunca se hacen commits directamente en `main` ni en `dev`.** Todo el trabajo se hace en ramas `feature/`, `fix/` o `docs/`.
- **Nunca se suben archivos de datos**: ni datasets, ni modelos generados, ni resultados.
- Los datos se guardan en local en la carpeta `data/` de la raíz del proyecto. Está excluida en el `.gitignore`, así que Git la ignora.
- Antes de cada commit, revisa con `git status` qué archivos vas a incluir y comprueba que no hay archivos de datos.
- El entorno virtual (`.venv/`) tampoco se sube.

## 2. Modelo de ramas

| Rama | Función |
|------|---------|
| `main` | Solo versiones estables. Únicamente recibe cambios desde `dev` al publicar una release. |
| `dev` | Rama de integración del desarrollo. Aquí se fusionan las ramas de trabajo terminadas. |
| `feature/<numero>-<descripcion>` | Una rama por historia de usuario o tarea. Se crea desde `dev`. |
| `fix/<descripcion>` | Una rama por corrección de errores. Se crea desde `dev`. |
| `docs/<descripcion>` | Una rama por cambio de documentación. Se crea desde `dev`. |

Formato de los nombres:

- En minúsculas, sin tildes ni espacios, con palabras separadas por guiones.
- En las `feature`, `<numero>` es el número de la historia de usuario o tarea.

Ejemplos: `feature/10-importacion-datos`, `fix/error-lectura-csv`, `docs/actualizar-readme`.

## 3. Flujo de trabajo

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

### Fusionar la rama en dev y eliminarla

Se puede hacer con un Pull Request en GitHub (base: `dev`) o en local:

```bash
git switch dev
git pull
git merge --no-ff feature/10-importacion-datos
git push

git branch -d feature/10-importacion-datos           # borra la rama local
git push origin --delete feature/10-importacion-datos # borra la rama en GitHub
```

### Publicar una release en main

Solo cuando `dev` tiene una versión estable, y de acuerdo con todo el grupo:

```bash
git switch main
git pull
git merge --no-ff dev
git push
```

## 4. Mensajes de commit

- En español, en presente y en modo indicativo: «Añade…», «Corrige…», «Elimina…».
- Primera línea breve (máximo unos 70 caracteres), sin punto final, que diga **qué** cambia.
- Si hace falta explicar el **porqué**, se deja una línea en blanco y se añade un párrafo.
- Un commit = un cambio lógico. Mejor varios commits pequeños que uno enorme.

## 5. Dependencias con uv

El proyecto se gestiona con [uv](https://docs.astral.sh/uv/). **No se usa `pip install`** ni se edita el entorno a mano.

- Tras clonar o al traer cambios que tocan dependencias: `uv sync`
- Añadir una dependencia: `uv add <paquete>` (por ejemplo, `uv add pandas`)
- Añadir una dependencia solo de desarrollo: `uv add --dev <paquete>` (por ejemplo, `uv add --dev pytest`)
- Quitar una dependencia: `uv remove <paquete>`
- Actualizar una dependencia: `uv lock --upgrade-package <paquete>` y después `uv sync`
- Ejecutar el proyecto o cualquier comando dentro del entorno: `uv run <comando>`

Al cambiar dependencias se modifican `pyproject.toml` y `uv.lock`: **se suben los dos en el mismo commit**, en una rama de trabajo como cualquier otro cambio. Así todos instalan exactamente las mismas versiones.

## 6. README y documentación

- La documentación del proyecto va en la carpeta `docs/`; el `README.md` contiene la descripción y las instrucciones de instalación y ejecución.
- Los cambios de documentación se hacen en una rama `docs/<descripcion>` creada desde `dev` y se fusionan en `dev` como cualquier otra rama.
- Si una `feature` cambia cómo se instala o se ejecuta el proyecto, actualiza el `README.md` en esa misma rama.
