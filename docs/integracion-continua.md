# Integración continua con GitHub Actions

El repositorio tiene un flujo de trabajo de GitHub Actions en
`.github/workflows/tests.yml`. Su objetivo es comprobar que el código
funciona en un entorno limpio, distinto de la máquina de cada desarrollador,
antes de fusionar una rama en `dev`.

## Cuándo se ejecuta

```yaml
on:
  push:
    branches: ["**"]
  pull_request:
    branches: [main, dev]
```

- **`push` a cualquier rama** (`"**"` incluye también las ramas con `/`,
  como `feature/64-integracion-continua`). Cada vez que alguien hace
  `git push`, GitHub ejecuta el flujo sobre el último commit subido.
- **`pull_request` hacia `dev` o `main`**. Al abrir o actualizar un PR, el
  flujo se ejecuta sobre el resultado de fusionar la rama con la de destino,
  así se ve antes de fusionar si la combinación funciona.

Una rama con un PR abierto ejecuta el flujo dos veces por cada push (una por
cada evento). Es normal.

## Qué hace cada paso

El flujo tiene un único trabajo, `tests` («Ruff y pytest»), que se ejecuta
en una máquina virtual nueva de Ubuntu (`runs-on: ubuntu-latest`). La
máquina empieza vacía en cada ejecución.

| Paso | Qué hace |
|------|----------|
| **Descargar el código** (`actions/checkout`) | Copia el repositorio, en el commit que ha lanzado la ejecución, a la máquina virtual. |
| **Instalar uv** (`astral-sh/setup-uv`) | Instala uv. La versión de la acción está fijada por su hash para que no cambie sin que lo sepamos. `enable-cache: true` guarda los paquetes descargados entre ejecuciones para que tarde menos. |
| **Instalar las dependencias** (`uv sync --locked`) | Crea el entorno virtual con la versión de Python de `.python-version` (3.12) y las dependencias exactas de `uv.lock`. Con `--locked` falla si `uv.lock` no corresponde con `pyproject.toml`, es decir, si alguien añadió una dependencia y no subió el `uv.lock` actualizado. |
| **Comprobar el formato** (`uv run ruff format --check src tests`) | Falla si algún archivo no tiene el formato de ruff. No cambia nada; en local se arregla con `uv run ruff format src tests`. |
| **Comprobar el estilo** (`uv run ruff check src tests`) | Falla si ruff encuentra avisos de estilo o errores comunes (imports sin usar, variables sin definir…). |
| **Pasar los tests** (`uv run pytest -q --cov --cov-report=term-missing`) | Ejecuta todas las pruebas de `tests/` y muestra la cobertura de cada módulo. Si falla algún test, el paso y la ejecución fallan. |

Los pasos van en orden y, si uno falla, los siguientes no se ejecutan.

## Cómo consultar el resultado

1. En GitHub, abrir la pestaña **Actions** del repositorio.
2. Cada fila es una ejecución. Muestra el mensaje del commit, la **rama** y
   un icono: verde (✓) si todo ha pasado, rojo (✗) si algo ha fallado,
   amarillo si aún se está ejecutando. Se puede filtrar por rama con el
   desplegable *Branch*.
3. Al entrar en una ejecución y después en el trabajo **Ruff y pytest** se
   ven todos los pasos. El que ha fallado tiene una ✗; al desplegarlo
   aparece la salida del comando.
4. Si ha fallado **Pasar los tests**, pytest muestra al final un resumen
   `FAILED tests/ruta/test_archivo.py::nombre_del_test`, con el archivo y
   el test concreto que ha fallado. Más arriba está el detalle del error.

El resultado también aparece junto a cada commit (en la lista de commits y en
los PR) y en la insignia del `README.md`, que muestra el estado de `dev`.

## Problemas entre local y GitHub Actions

Causas típicas de que una prueba pase en local y falle en GitHub, y cómo
evitarlas:

- **Pruebas que leen archivos de `data/`.** Esa carpeta está en el
  `.gitignore`, así que no existe en GitHub. Las pruebas crean sus propios
  datos (con `tmp_path` y las fixtures de `tests/conftest.py`) en vez de
  leer datasets locales.
- **Rutas escritas a mano.** Una ruta como `"tests\\datos\\x.csv"` funciona
  en Windows pero no en Linux. Se usa `pathlib.Path`, relativa al archivo o
  a `tmp_path`.
- **Interfaz gráfica sin pantalla.** El servidor de GitHub no tiene pantalla.
  Los módulos de `nucleo/` no importan NiceGUI, y `tests/test_arquitectura.py`
  lo comprueba. Las pruebas de `tests/gui/` crean los paneles sin arrancar
  el servidor ni abrir el navegador, y sustituyen con `monkeypatch` lo que
  necesitaría una página real (como `ui.notify`).
- **`uv.lock` desactualizado.** `uv sync --locked` falla si se añade una
  dependencia con `uv add` y no se sube `uv.lock`. Se soluciona subiendo
  `pyproject.toml` y `uv.lock` en el mismo commit.
- **Formato sin aplicar.** Si en local solo se pasa `pytest`, el paso de ruff
  puede fallar en GitHub. Antes de subir se ejecutan las cuatro
  comprobaciones del `CONTRIBUTING.md`.

Al configurar la integración continua (historia #64) todas las pruebas
existentes pasaron a la primera en GitHub Actions, porque ya seguían estas
reglas. Si en el futuro aparece un caso nuevo, se añade aquí con su causa y
su solución.

## Comprobación de que detecta errores

Para comprobar que el flujo detecta fallos se subió una prueba que falla a
propósito a una rama creada solo para eso, se verificó en **Actions** que la
ejecución salía en rojo y se borró la rama sin fusionarla:

```bash
git switch dev
git switch -c feature/64-prueba-ci-fallo
printf 'def test_falla_a_proposito():\n    assert False\n' > tests/test_falla.py
git add tests/test_falla.py
git commit -m "Añade una prueba que falla a propósito"
git push -u origin feature/64-prueba-ci-fallo
# En Actions: la ejecución de esta rama sale en rojo en «Pasar los tests»
git switch dev
git branch -D feature/64-prueba-ci-fallo
git push origin --delete feature/64-prueba-ci-fallo
```

Esta rama es la única excepción a la regla de no borrar ramas del
`CONTRIBUTING.md`: no contiene trabajo que haya que conservar.

## Reglas de fusión

Las reglas de fusión según el resultado de GitHub Actions están en el
`CONTRIBUTING.md`, en la sección «Comprobar antes de fusionar».
