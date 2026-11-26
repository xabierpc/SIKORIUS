# Estructura del código

Este documento explica cómo está organizado el código de SIKORIUS, qué hace cada módulo y cómo se relaciona la lógica con la interfaz gráfica. Está pensado para quien llega nuevo al proyecto y quiere saber dónde tocar.

## 1. Arquitectura en capas

El paquete `src/sikorius/` se divide en cuatro capas. Cada una solo puede importar las que tiene por debajo:

```
gui  ──►  aplicacion  ──►  datos  ──►  dominio
```

| Capa | Responsabilidad | No puede importar |
|---|---|---|
| `dominio/` | Lógica pura: columnas, separación, preprocesado, modelo y predicción. Trabaja con DataFrames y números, sin archivos ni interfaz. | `nicegui`, `gui`, `aplicacion`, `datos` |
| `datos/` | Leer datasets de archivos y guardar y cargar modelos en JSON. | `nicegui`, `gui`, `aplicacion` |
| `aplicacion/` | La sesión: guarda el estado del flujo y ofrece a la GUI las operaciones de cada paso. | `nicegui`, `gui` |
| `gui/` | Interfaz con NiceGUI: pinta el estado de la sesión y le pasa lo que hace el usuario. | `datos` (los archivos se leen y escriben siempre a través de la sesión) |

La GUI sí puede usar del dominio tipos, constantes, errores y funciones de formato (por ejemplo, `dominio.errores` o `dominio.prediccion.texto_prediccion`).

`tests/test_arquitectura.py` comprueba estas reglas en cada ejecución de los tests:

```bash
uv run pytest tests/test_arquitectura.py -v
```

## 2. Módulos

### Punto de entrada

| Módulo | Qué hace |
|---|---|
| `app.py` | `main()`: crea una única `Sesion` y arranca NiceGUI con `ui.run()`. Es el comando `uv run sikorius` (definido en `[project.scripts]` del `pyproject.toml`). |
| `__main__.py` | Permite arrancar también con `uv run python -m sikorius`. |

### `dominio/`

| Módulo | Qué hace |
|---|---|
| `errores.py` | Excepciones esperadas (`ErrorImportacion`, `ErrorSeleccion`, `ErrorSeparacion`, `ErrorPreprocesado`, `ErrorModelo`, `ErrorPersistencia`, `ErrorPrediccion`). Todas heredan de `ErrorSikorius` y su mensaje se muestra tal cual al usuario. |
| `columnas.py` | Valida la selección de columnas de entrada y salida (`validar_seleccion`) y traduce los nombres del selector a las columnas reales. |
| `separacion.py` | Interpreta el porcentaje de test y la semilla y separa el dataset en entrenamiento y test. |
| `preprocesado.py` | Detecta los valores inexistentes y los trata: eliminar filas o rellenar con media, mediana o constante (calculadas con entrenamiento). |
| `modelo.py` | `ModeloLineal` (coeficientes calculados con numpy por mínimos cuadrados), métricas R² y ECM, fórmula y datos para el gráfico del ajuste. |
| `prediccion.py` | Interpreta los valores escritos por el usuario y calcula la predicción. |
| `texto.py` | Formato de números para mostrarlos. |

### `datos/`

| Módulo | Qué hace |
|---|---|
| `formatos.py` | Extensiones admitidas (`.csv`, `.xlsx`, `.xls`, `.sqlite`, `.db`). |
| `importador.py` | `importar_datos(ruta)`: lee CSV, Excel o SQLite y devuelve un DataFrame, o lanza `ErrorImportacion` con un mensaje claro. |
| `persistencia.py` | `guardar_modelo` y `cargar_modelo` en JSON (formato `sikorius-modelo`, extensión `.json`). Al cargar valida todo y nunca ejecuta código del archivo. |

### `aplicacion/`

| Módulo | Qué hace |
|---|---|
| `sesion.py` | Clase `Sesion`. Guarda el resultado de cada paso (`PASOS`: dataset, selección, separación, preprocesado, modelo) y, al cambiar uno, borra los que van detrás. Decide qué pestañas (`ETAPAS`) están disponibles. Avisa a la GUI de cada cambio. |
| `__init__.py` | Reexporta las constantes de formatos que necesita la GUI, para que no importe `datos/`. |

### `gui/`

| Módulo | Qué hace |
|---|---|
| `pagina.py` | Construye la página: la barra con las pestañas y el botón **Continuar**, y un panel por pestaña. |
| `paneles/base.py` | Clase `Panel`: se suscribe a la sesión y llama a `actualizar()` en cada cambio. |
| `paneles/panel_inicio.py` | Pestaña **Inicio**: logo y botones **Subir dataset** y **Cargar modelo**. |
| `paneles/panel_dataset.py` | Pestaña **Datos**: ruta, tamaño y tabla del dataset; botón **Cargar otro**. |
| `paneles/panel_columnas.py` | **Columnas del modelo**: selectores de features y target y **Confirmar selección**. |
| `paneles/panel_separacion.py` | **Entrenamiento y test**: porcentaje, semilla y **Separar datos**. |
| `paneles/panel_preprocesado.py` | **Preprocesado**: tabla de valores inexistentes, estrategia y **Aplicar preprocesado**. |
| `paneles/panel_modelo.py` | **Modelo**: fórmula, métricas, gráfico, descripción, **Crear modelo** y **Guardar modelo**. |
| `paneles/panel_prediccion.py` | **Prediccion**: un campo por entrada y **Realizar predicción**. |
| `componentes/` | Piezas reutilizables: explorador de archivos, diálogo de guardado, confirmación, tabla, selectores, fórmula, gráfico y la lógica de los botones de carga (`carga_dataset.py`, `carga_modelo.py`). |
| `avisos.py`, `tema.py`, `recursos/` | Notificaciones, colores, CSS, logo y fuente. |

## 3. Relación entre la lógica y la interfaz

La GUI nunca guarda estado propio ni llama directamente a `dominio/` o `datos/` para hacer un paso: todo pasa por la sesión.

```
  Usuario pulsa un botón
          │
          ▼
  gui/paneles/panel_X.py ── llama a ──► Sesion.<operación>()
                                            │
                                            ├─► dominio/… (cálculo)
                                            ├─► datos/…   (archivos)
                                            │
                                    guarda el resultado y
                                    borra los pasos siguientes
                                            │
                                            ▼
                                   Sesion._avisar()
                                            │
          ┌─────────────────────────────────┘
          ▼
  Cada Panel.actualizar() lee la sesión y se vuelve a pintar
```

- Si la operación falla, la sesión lanza un `ErrorSikorius`, **no cambia nada**, y el panel muestra el mensaje con `avisos.notificar_error`.
- Como el estado está en la sesión y no en los paneles, al recargar la página cada panel muestra lo que ya estaba hecho.
- Gracias a esta separación, `dominio/`, `datos/` y la sesión se prueban sin abrir la interfaz.

Ejemplo, separar los datos:

1. `PanelSeparacion` lee los campos y llama a `sesion.separar(texto_porcentaje, texto_semilla)`.
2. La sesión usa `dominio.separacion` para interpretar los valores y separar, guarda los conjuntos y borra el preprocesado y el modelo anteriores.
3. La sesión avisa; `PanelSeparacion` muestra los tamaños, `PanelPreprocesado` recalcula los valores inexistentes y `Pestanas` activa **Continuar**.

## 4. Tests

`tests/` tiene la misma estructura que `src/sikorius/`: `tests/dominio/`, `tests/datos/`, `tests/aplicacion/` y `tests/gui/`. Los datos y sesiones comunes están en `tests/conftest.py`. Cómo ejecutarlos: [CONTRIBUTING.md](../CONTRIBUTING.md#comprobar-antes-de-fusionar).

### Pruebas funcionales

`herramientas/` está fuera del paquete (`src/`) y no forma parte de la aplicación. Contiene las pruebas funcionales del plan de pruebas: `herramientas/funcionales/` (Playwright) y `herramientas/probador_llm/` (agente con un LLM). Sus dependencias están en el grupo `probador` del `pyproject.toml`, y sus propios tests en `tests/herramientas/`. Ver [`pruebas-funcionales.md`](pruebas-funcionales.md) y [`pruebas_con_llm.md`](pruebas_con_llm.md).

## 5. Dónde añadir una funcionalidad nueva

1. La lógica, en `dominio/` (o en `datos/` si lee o escribe archivos), con sus tests.
2. Una operación en `Sesion` que la use y guarde el resultado.
3. Un panel o componente en `gui/` que llame a esa operación y se pinte en `actualizar()`.
