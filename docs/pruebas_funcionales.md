# Pruebas funcionales automatizadas (Playwright)

Historia de usuario: **#29 Creación y ejecución de un plan de pruebas funcionales antes de la release**

Los casos del [plan de pruebas](plan_pruebas.md) están automatizados con [Playwright](https://playwright.dev/python/) en [`herramientas/funcionales/`](../herramientas/funcionales/). Cada prueba maneja SIKORIUS en un navegador real como lo haría una persona: pulsa botones por su texto, carga archivos con el explorador, elige columnas y comprueba lo que se ve en pantalla. No llama al código de la aplicación.

---

## 1. Cómo se ejecutan

### Preparación (una vez)

```bash
uv sync --group probador
uv run --group probador playwright install chromium
```

Si ya tienes Google Chrome instalado, puedes saltarte el segundo comando y usar `SIKORIUS_CHROME=1` (ver más abajo).

Copia los datasets de ejemplo en la carpeta `data/` del proyecto, que no se sube al repositorio:

```
data/housing1.csv
data/housing.xlsx
data/housing.db
```

Si faltan, las pruebas que los usan se saltan y lo indican.

### Ejecución

Desde la raíz del repositorio:

```bash
# Todas las pruebas
uv run --group probador pytest herramientas/funcionales -v

# Una historia
uv run --group probador pytest herramientas/funcionales/test_03_separacion.py -v

# Un caso
uv run --group probador pytest herramientas/funcionales -v -k cp47

# Viendo el navegador
SIKORIUS_VER=1 uv run --group probador pytest herramientas/funcionales -v

# Con el Google Chrome instalado
SIKORIUS_CHROME=1 uv run --group probador pytest herramientas/funcionales -v
```

En fish, las variables se ponen igual (`SIKORIUS_VER=1 uv run ...`).

Las capturas de pantalla de cada prueba quedan en `data/pruebas_funcionales/<fecha>/capturas/<prueba>/`, y lo que escribe la aplicación, en `aplicacion.log` de esa misma carpeta.

Estas pruebas no se ejecutan con `uv run pytest` ni en GitHub Actions: necesitan un navegador y los datasets de ejemplo.

---

## 2. Cómo funcionan

- **Una sola aplicación y un solo navegador** para todas las pruebas (`conftest.py`). Antes de empezar se crean los archivos de prueba F-1 a F-14 del plan en `data/pruebas/`. La aplicación usa `data/` como carpeta personal, así que el explorador de archivos empieza ahí. La ventana mide 1366 × 768, el mínimo que pide la historia #37.
- **Cada prueba prepara su propio estado** con las acciones de `sikorius_ui.py`: `cargar`, `seleccionar`, `separar`, `preprocesar`, `crear_modelo`, `guardar_modelo`, `cargar_modelo`, `predecir`... Así, si una prueba falla, las demás no se ven afectadas. Solo se reinicia la aplicación en los casos que piden la pantalla inicial vacía.
- **Las comprobaciones son las del resultado esperado del plan**: textos de la pantalla, mensajes de la aplicación (se recogen todos, aunque desaparezcan a los pocos segundos), botones habilitados, pestañas visibles, la configuración del gráfico, los archivos guardados en el disco...
- **Esperas**: tras cada acción se espera a que la pantalla deje de cambiar. En las operaciones que tardan sin que cambie nada (cargar, separar, preprocesar o crear el modelo con 20.640 filas) se espera al mensaje de la aplicación.

---

## 3. Casos y pruebas

| Historia | Archivo | Casos |
|---|---|---|
| #10, #14 Carga de datos | `test_01_carga.py` | CP-01 a CP-14 |
| #11 Selección de columnas | `test_02_columnas.py` | CP-15 a CP-21 |
| #41 Separación | `test_03_separacion.py` | CP-22 a CP-34 |
| #26 Preprocesado | `test_04_preprocesado.py` | CP-35 a CP-45 |
| #16, #33 Modelo y descripción | `test_05_modelo.py` | CP-46 a CP-56 |
| #21 Guardado | `test_06_guardado.py` | CP-57 a CP-64 |
| #24 Recuperación | `test_07_recuperacion.py` | CP-65 a CP-74 |
| #22 Predicción | `test_08_prediccion.py` | CP-75 a CP-81 |
| #37 Experiencia de usuario | `test_09_experiencia.py` | CP-82 a CP-88 |
| Flujo completo | `test_10_flujo.py` | CP-93 |

Cada prueba se llama como su caso (`test_cp47_modelo_exacto`) y su docstring repite el título del plan. Algunos casos parecidos comparten prueba: CP-24 y CP-27, CP-25 y CP-26, CP-48 y CP-50, CP-49 y CP-51.

Casos que el plan hace a mano y aquí se comprueban con código:

- **CP-44**: el archivo original sigue teniendo 20.640 filas y 207 vacíos (se lee con pandas).
- **CP-59**: el archivo guardado contiene el modelo y la descripción, y no los datos.
- **CP-84**: ningún mensaje de la aplicación contiene trazas ni textos de Python.
- **CP-86**: se llega a la última fila de la tabla y coincide con la última del CSV.
- **CP-87 y CP-88**: a 1366 × 768 y a media pantalla no hay desplazamiento horizontal, ni botones cortados o tapados.

### Casos que no se automatizan

| Caso | Motivo |
|---|---|
| CP-85 | Hay que mover la ventana mientras carga un archivo: se prueba a mano (la prueba aparece como saltada). |
| CP-89 a CP-92 | El asistente con LLM no está en `dev`. |

CP-64 (error de permisos) se salta en Windows y si se ejecuta como root, porque en esos casos no se puede quitar el permiso de escritura de una carpeta.

---

## 4. Diferencias con el plan encontradas al automatizar

- **CP-52.** Al aplicar el preprocesado, la aplicación ya crea el modelo (lo indica el README). El plan pedía pulsar después "Crear modelo" y esperar el mensaje en ese momento. Se ha corregido el plan: el mensaje «Modelo creado correctamente.» aparece al aplicar el preprocesado.
