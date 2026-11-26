# Plan de pruebas funcionales — SIKORIUS

Historia de usuario: **#29 Creación y ejecución de un plan de pruebas funcionales antes de la release**

Este documento recoge los casos de prueba funcionales de la aplicación SIKORIUS. Cada caso comprueba la aplicación **desde el punto de vista del usuario**, usando solo la interfaz gráfica y sin mirar el código.

---

## 0. Antes de usar este plan

### 0.1 Tareas del equipo antes de la ejecución (no las hace quien ejecuta)

1. Copiar los datasets de ejemplo en `data/` (sección 2).
2. Si cambia algún texto de la interfaz, actualizarlo **solo en el glosario** (sección 1.3). Los casos usan los nombres del glosario.
3. Borrar esta sección 0.1 una vez completada.

### 0.2 Instrucciones para quien ejecuta las pruebas

- Sigue **solo** los pasos escritos. Si no puedes seguir un paso sin preguntar, para, anótalo en el registro (sección 6) y avisa al equipo: el caso se reescribe antes de continuar.
- Los casos son **aditivos**: se ejecutan en orden y cada uno parte de lo que dejó el anterior, sin cerrar la aplicación. Sus precondiciones indican cómo empieza:
  - **Aplicación recién abierta (PR-1):** se cierra y se vuelve a abrir la aplicación. Solo en los casos que necesitan la pantalla inicial vacía.
  - **D-1 cargado:** el dataset de ejemplo D-1 se carga una vez (CP-01) y se reutiliza. Si el dataset cargado es otro, se vuelve a cargar D-1.
  - **D-1 recién cargado:** se carga D-1 de nuevo aunque ya esté cargado, para empezar sin selecciones.
  - **En el estado que dejó el caso anterior:** el caso carga lo que necesita por sí mismo.
  - **CP-xx ejecutado, sin cerrar la aplicación:** el caso continúa justo donde terminó CP-xx, que se ejecuta inmediatamente antes. Si CP-xx no se ha ejecutado, se hacen antes sus pasos.
- Si al cargar un dataset o un modelo aparece una pregunta de confirmación por cambios sin guardar y el caso no trata de eso, se confirma.
- Si al terminar un caso queda un diálogo abierto, se cierra con **⟨B_CANCELAR⟩** o `Esc` antes del siguiente.
- Compara lo que ves con el **Resultado esperado**. Si todo coincide, el caso es **Correcto**. Si algo no coincide, el caso es **Fallido** y anotas lo que has visto.
- No ejecutes casos de funcionalidades que hayas implementado tú.

---

## 1. Entorno de prueba

### 1.1 Versión que se prueba

- Rama: `dev`, con todas las historias de la release final ya fusionadas.
- Antes de empezar, en la raíz del repositorio:
  1. Ejecutar `git switch dev` y después `git pull`.
  2. Ejecutar `uv sync`.
  3. Ejecutar `uv run pytest`. **Todas las pruebas deben pasar.** Si alguna falla, no se ejecuta este plan.

### 1.2 Procedimientos comunes

Algunos casos repiten los mismos pasos iniciales. Para no copiarlos en cada caso, se escriben aquí una sola vez. Cuando un caso dice "Realizar PR-2", hay que hacer todos los pasos de PR-2 en orden.

**PR-1. Abrir la aplicación**

1. Si la aplicación ya está abierta, cerrar la pestaña del navegador y, en la terminal donde se ejecuta, pulsar `Ctrl+C`.
2. En una terminal, en la carpeta raíz del repositorio, ejecutar `uv run sikorius`.
3. Abrir en el navegador la dirección `http://localhost:8080`.
4. Comprobar que aparece la pantalla de inicio de SIKORIUS, con los botones "Subir dataset" y "Cargar modelo".

**PR-2. Cargar un dataset** (se indica el archivo en cada caso; por defecto, D-1)

1. Pulsar el botón **⟨B_CARGAR_DATOS⟩** (en la pestaña "Inicio"; si ya hay un dataset, "Cargar otro" en la pestaña "Datos").
2. En el explorador de archivos, ir a la carpeta `data/` del proyecto. Para moverse, se pulsa el nombre de una carpeta para entrar en ella y `..` para subir a la carpeta superior. El explorador empieza en la carpeta personal o en la del último archivo abierto.
3. Pulsar el nombre del archivo indicado (se abre al pulsarlo).

**PR-3. Seleccionar columnas** (se indican las columnas en cada caso; por defecto, entrada `median_income` y salida `median_house_value`)

1. Ir a la pestaña "Variables y separacion" (botón **Continuar** o la pestaña). En la sección **⟨S_COLUMNAS⟩**, en el selector **⟨C_ENTRADAS⟩**, marcar las columnas de entrada indicadas.
2. En el selector **⟨C_SALIDA⟩**, elegir la columna de salida indicada.
3. Pulsar el botón **⟨B_CONFIRMAR⟩**.

**PR-4. Separar con los valores por defecto**

1. En la sección **⟨S_SEPARACION⟩**, comprobar que **⟨C_PORCENTAJE⟩** vale `20` y **⟨C_SEMILLA⟩** vale `⟨SEMILLA_DEF⟩` (los valores por defecto). Si un caso anterior los cambió, escribir `20` y `⟨SEMILLA_DEF⟩`.
2. Pulsar el botón **⟨B_SEPARAR⟩**.

**PR-5. Crear el modelo**

1. Ir a la pestaña "Modelo" (botón **Continuar** o la pestaña).
2. Pulsar el botón **⟨B_CREAR_MODELO⟩**.

### 1.3 Glosario de la interfaz

La aplicación está organizada en **pestañas**, en la barra de arriba: "Inicio", "Datos", "Variables y separacion", "Preprocesado" y "Modelo". Cada pestaña aparece cuando se completa la anterior, y el botón **Continuar** (arriba a la derecha) lleva a la siguiente. Si un paso nombra un botón o un campo que no se ve, hay que ir a la pestaña donde está (columna "Dónde").

| Clave | Texto en la aplicación | Dónde |
|---|---|---|
| B_CARGAR_DATOS | Subir dataset | Botón de la pestaña "Inicio". Si ya hay un dataset cargado, se usa el botón "Cargar otro" de la pestaña "Datos". |
| B_CANCELAR | Cancelar | Botón de los diálogos |
| L_RUTA | ruta del archivo | Texto encima de la tabla, en la pestaña "Datos" |
| T_DATOS | tabla de datos | Pestaña "Datos" |
| L_TAMANO | "N filas y M columnas" | Texto debajo de la ruta, en la pestaña "Datos" |
| S_COLUMNAS | Columnas del modelo | Sección de la pestaña "Variables y separacion" |
| C_ENTRADAS | Features (selección múltiple) | Desplegable de "Columnas del modelo" |
| C_SALIDA | Target (columna de salida) | Desplegable de "Columnas del modelo" |
| B_CONFIRMAR | Confirmar selección | Botón de "Columnas del modelo" |
| S_SEPARACION | Entrenamiento y test | Sección de la pestaña "Variables y separacion" |
| C_PORCENTAJE | Porcentaje de test (%) | Campo de "Entrenamiento y test" (por defecto, 20) |
| C_SEMILLA | Semilla | Campo de "Entrenamiento y test" |
| SEMILLA_DEF | 42 | Valor por defecto de la semilla |
| B_SEPARAR | Separar datos | Botón de "Entrenamiento y test" |
| S_PREPROCESADO | Preprocesado | Pestaña "Preprocesado" |
| O_ELIMINAR / O_MEDIA / O_MEDIANA / O_CONSTANTE | Eliminar filas con valores inexistentes / Rellenar con la media (de entrenamiento) / Rellenar con la mediana (de entrenamiento) / Rellenar con un valor constante | Opciones de "Preprocesado" |
| C_CONSTANTE | Valor constante | Campo de "Preprocesado" |
| B_PREPROCESAR | Aplicar preprocesado | Botón de "Preprocesado". Al aplicarlo también se crea el modelo. |
| B_CREAR_MODELO | Crear modelo | Botón de la pestaña "Modelo" |
| G_AJUSTE | gráfico del ajuste | Pestaña "Modelo", a la izquierda de las métricas |
| L_FORMULA | fórmula del modelo | Pestaña "Modelo", encima del gráfico |
| T_METRICAS | tarjetas "Entrenamiento" y "Test" con R² y ECM | Pestaña "Modelo", a la derecha del gráfico |
| C_DESCRIPCION | Descripción (opcional) | Área de texto de la pestaña "Modelo" |
| B_GUARDAR_MODELO | Guardar modelo | Botón de la pestaña "Modelo" |
| B_CARGAR_MODELO | Cargar modelo | Botón de la pestaña "Inicio" |
| B_GUARDAR | Guardar | Botón del diálogo de guardado |
| C_NOMBRE_ARCHIVO | Nombre del archivo | Campo del diálogo de guardado |
| EXT | .json | Extensión de los modelos guardados |
| S_PREDICCION | Prediccion | Sección de la pestaña "Modelo", debajo del modelo |
| B_PREDECIR | Realizar predicción | Botón de "Prediccion" |
| L_RESULTADO | resultado de la predicción | Texto debajo del botón "Realizar predicción" |
| BARRA_ESTADO | indicador de guardado ("Sin guardar", "Guardado en ...") | Junto al botón "Guardar modelo" |
| AVISO | mensajes emergentes | Mensajes que aparecen en la ventana: verdes (éxito), naranjas (aviso) y rojos (error) |
| DEC | 4 | Decimales de la fórmula y de la predicción |

La fórmula se escribe con "·" para multiplicar y "−" para restar, por ejemplo `y = 2.0000 · x1 − 3.0000 · x2 + 5.0000`.


---

## 2. Datos de prueba

Los archivos de datos **no están en el repositorio**. Quien ejecuta las pruebas copia los tres datasets de ejemplo (`housing1.csv`, `housing.xlsx` y `housing.db`) en la carpeta local `data/` del proyecto (si no existe, la crea).

### 2.1 Datasets de ejemplo proporcionados

Los tres archivos contienen **los mismos datos** en formatos distintos. Antes de empezar, abre cada uno con una hoja de cálculo (o con un visor de SQLite) y comprueba que coinciden con esta tabla.

| Dato | Valor |
|---|---|
| D-1 (CSV) | `data/housing1.csv` |
| D-2 (Excel) | `data/housing.xlsx` |
| D-3 (SQLite) | `data/housing.db`, con una sola tabla llamada `california_housing_dataset` |
| Número de filas (sin contar el encabezado) | 20640 |
| Número de columnas | 10 |
| Nombres de todas las columnas, en orden | longitude, latitude, housing_median_age, total_rooms, total_bedrooms, population, households, median_income, median_house_value, ocean_proximity |
| Columna de entrada principal `E1` (numérica, sin valores vacíos) | median_income |
| Segunda columna de entrada `E2` (numérica, sin valores vacíos) | housing_median_age |
| Columna de salida `S` (numérica, sin valores vacíos) | median_house_value |
| Columna numérica con valores vacíos `C_NAN` | total_bedrooms, con 207 celdas vacías |
| Columna no numérica `C_TXT` | ocean_proximity |
| Filas de test con porcentaje 20 y semilla por defecto | 4128 (entrenamiento: 16512) |
| Filas de test con porcentaje 1 | 207 (entrenamiento: 20433) |
| Filas de test con porcentaje 99 | 20434 (entrenamiento: 206) |

> Regla de la aplicación (historia #41): filas de test = `FILAS × porcentaje / 100` **redondeado hacia arriba**; entrenamiento = el resto. Por ejemplo, 1 % de 20640 = 206,4 → 207 filas de test.

### 2.2 Archivos creados para las pruebas

Estos archivos los crea quien ejecuta las pruebas, **una sola vez y antes de empezar**, siguiendo estas instrucciones. Se guardan en la carpeta `data/pruebas/` (crearla si no existe). No se suben al repositorio (la carpeta `data/` está en el `.gitignore`).

Para crear un archivo de texto: abrir un editor de texto plano (por ejemplo, VS Code), pegar el contenido indicado **sin espacios al principio de las líneas** y guardarlo con el nombre indicado.

| Id | Archivo | Cómo crearlo | Para qué se usa |
|---|---|---|---|
| F-1 | `data/pruebas/vacio.csv` | Crear un archivo de texto sin ningún contenido (0 bytes) y guardarlo con ese nombre. | Archivo vacío |
| F-2 | `data/pruebas/solo_cabecera.csv` | Contenido: una sola línea `a,b` | Archivo sin datos |
| F-3 | `data/pruebas/falso.xlsx` | Contenido: `esto no es un excel` | Archivo dañado |
| F-4 | `data/pruebas/falso.db` | Contenido: `esto no es una base de datos` | Archivo dañado |
| F-5 | `data/pruebas/dos_tablas.db` | Ejecutar en la raíz del repositorio: `uv run python -c "import sqlite3; c = sqlite3.connect('data/pruebas/dos_tablas.db'); c.execute('create table a (x real)'); c.execute('create table b (y real)'); c.execute('insert into a values (1)'); c.execute('insert into b values (2)'); c.commit()"` | SQLite con más de una tabla |
| F-6 | `data/pruebas/sin_tablas.db` | Ejecutar: `uv run python -c "import sqlite3; c = sqlite3.connect('data/pruebas/sin_tablas.db'); c.execute('create table t (x real)'); c.execute('drop table t'); c.commit()"` | SQLite sin tablas |
| F-7 | `data/pruebas/notas.txt` | Contenido: `hola` | Extensión no permitida |
| F-8 | `data/pruebas/cuatro_filas.csv` | Contenido (ver bloque F-8) | Dataset con menos de 5 filas |
| F-9 | `data/pruebas/lineal.csv` | Contenido (ver bloque F-9) | Modelo con resultado exacto conocido |
| F-10 | `data/pruebas/nulos_total.csv` | Contenido (ver bloque F-10) | Eliminación que deja un conjunto vacío |
| F-11 | `data/pruebas/carpeta ñandú á/` | Crear una carpeta con ese nombre exacto (con espacios, ñ y tildes) y copiar dentro D-1. | Rutas con caracteres especiales |
| F-12 | `data/pruebas/modelo_roto.json` | Contenido: `{ esto no es json` | Modelo dañado |
| F-13 | `data/pruebas/modelo_incompleto.json` | Contenido: `{"descripcion": "falta todo lo demás"}` | Modelo al que le falta información |
| F-14 | `data/pruebas/cinco_filas.csv` | Contenido (ver bloque F-14) | Separación que deja vacío un conjunto |

**Bloque F-8** (`cuatro_filas.csv`):

```
x,y
1,2
2,4
3,6
4,8
```

**Bloque F-14** (`cinco_filas.csv`):

```
x,y
1,2
2,4
3,6
4,8
5,10
```

**Bloque F-9** (`lineal.csv`). Cumple exactamente `y = 2·x1 − 3·x2 + 5`:

```
x1,x2,y
1,0,7
2,1,6
3,0,11
4,2,7
5,1,12
6,3,8
7,0,19
8,2,15
9,1,20
10,4,13
11,2,21
12,3,20
```

**Bloque F-10** (`nulos_total.csv`). La columna `x` está vacía en todas las filas:

```
x,y
,1
,2
,3
,4
,5
,6
,7
,8
,9
,10
```

---

## 3. Funcionalidades cubiertas

| Funcionalidad | Historias | Casos |
|---|---|---|
| Carga de datos y tabla | #10, #14 | CP-01 a CP-14 |
| Selección de columnas | #11 | CP-15 a CP-21 |
| Separación en entrenamiento y test | #41 | CP-22 a CP-34 |
| Preprocesado de valores inexistentes | #26 | CP-35 a CP-45 |
| Creación del modelo, gráfico, fórmula y métricas | #16 | CP-46 a CP-53 |
| Descripción del modelo | #33 | CP-54 a CP-56 |
| Guardado del modelo | #21 | CP-57 a CP-64 |
| Recuperación del modelo y edición de la descripción | #24 | CP-65 a CP-74 |
| Predicciones | #22 | CP-75 a CP-81 |
| Experiencia de usuario | #37 | CP-82 a CP-88 |
| Asistente con LLM (funcionalidad añadida por el equipo) | — | CP-89 a CP-92 |
| Flujo completo | Todas | CP-93 |

---

## 4. Casos de prueba

### 4.1 Carga de datos (#10, #14)

#### CP-01. Carga de un CSV válido
- **Historia:** #14, #10
- **Objetivo:** comprobar que se carga un CSV y se muestran su ruta y todos sus datos.
- **Precondiciones:** aplicación recién abierta (PR-1).
- **Datos de prueba:** D-1.
- **Pasos:**
  1. Pulsar el botón **⟨B_CARGAR_DATOS⟩**.
  2. En el explorador de archivos, ir a la carpeta `data/` del proyecto.
  3. Seleccionar D-1 (el archivo se abre al pulsar su nombre).
- **Resultado esperado:**
  - La etiqueta **⟨L_RUTA⟩** muestra la ruta absoluta de D-1, que termina en `data/housing1.csv`.
  - La tabla **⟨T_DATOS⟩** tiene como encabezado las 10 columnas de la sección 2.1, en el mismo orden.
  - **⟨L_TAMANO⟩** indica 20640 filas y 10 columnas.
  - No aparece ningún mensaje de error.

#### CP-02. Carga de un Excel válido
- **Historia:** #14, #10
- **Objetivo:** comprobar que se carga un archivo `.xlsx` con los mismos datos que el CSV.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior.
- **Datos de prueba:** D-2.
- **Pasos:**
  1. Realizar PR-2 con el archivo D-2.
- **Resultado esperado:** igual que CP-01, pero la ruta termina en `data/housing.xlsx`. La tabla muestra 20640 filas y 10 columnas con los mismos nombres.

#### CP-03. Carga de una base de datos SQLite válida
- **Historia:** #14, #10
- **Objetivo:** comprobar que se carga la única tabla de una base de datos SQLite sin indicar su nombre.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior.
- **Datos de prueba:** D-3.
- **Pasos:**
  1. Realizar PR-2 con el archivo D-3.
- **Resultado esperado:** igual que CP-01, pero la ruta termina en `data/housing.db`. La aplicación no pide el nombre de la tabla.

#### CP-04. Las columnas numéricas se cargan como números
- **Historia:** #10, #11
- **Objetivo:** comprobar que las columnas numéricas no se importan como texto.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; columnas `median_income` y `median_house_value`.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Realizar PR-3 con entrada `median_income` y salida `median_house_value`.
- **Resultado esperado:** aparece un mensaje de éxito que nombra `median_income` como entrada y `median_house_value` como salida. No aparece ningún error de "columna no numérica".

#### CP-05. El explorador solo muestra los tipos permitidos
- **Historia:** #14
- **Objetivo:** comprobar que el explorador filtra las extensiones no compatibles.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior. Existen F-7 (`notas.txt`) y F-1 (`vacio.csv`) en `data/pruebas/`.
- **Datos de prueba:** F-1, F-7.
- **Pasos:**
  1. Pulsar el botón **⟨B_CARGAR_DATOS⟩**.
  2. En el explorador de archivos, ir a la carpeta `data/pruebas/`.
- **Resultado esperado:** en la lista aparece `vacio.csv` y **no** aparece `notas.txt`. Solo se ven carpetas y archivos con extensión `.csv`, `.xlsx`, `.xls`, `.sqlite` o `.db`.

#### CP-06. Cerrar el explorador sin elegir archivo
- **Historia:** #14
- **Objetivo:** comprobar que cancelar no produce errores ni cambia el estado.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Pulsar de nuevo el botón **⟨B_CARGAR_DATOS⟩**.
  3. En el explorador, pulsar **⟨B_CANCELAR⟩** (o la tecla `Esc`).
- **Resultado esperado:** no aparece ningún mensaje de error. La ruta y la tabla siguen mostrando D-1 con 20640 filas.

#### CP-07. Archivo vacío
- **Historia:** #14, #10
- **Objetivo:** comprobar el mensaje de error con un archivo vacío.
- **Precondiciones:** aplicación recién abierta (PR-1).
- **Datos de prueba:** F-1 (`vacio.csv`).
- **Pasos:**
  1. Pulsar el botón **⟨B_CARGAR_DATOS⟩**.
  2. Ir a la carpeta `data/pruebas/`, seleccionar `vacio.csv` (el archivo se abre al pulsar su nombre).
- **Resultado esperado:** aparece un mensaje de error que indica que el archivo no contiene datos. La tabla sigue vacía. La aplicación sigue funcionando (el botón **⟨B_CARGAR_DATOS⟩** sigue habilitado).

#### CP-08. Archivo con encabezado y sin datos
- **Historia:** #14, #10
- **Objetivo:** comprobar el error con un CSV que solo tiene encabezado.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior.
- **Datos de prueba:** F-2 (`solo_cabecera.csv`).
- **Pasos:**
  1. Pulsar el botón **⟨B_CARGAR_DATOS⟩**.
  2. Ir a `data/pruebas/`, seleccionar `solo_cabecera.csv` (el archivo se abre al pulsar su nombre).
- **Resultado esperado:** aparece un mensaje de error que indica que el archivo no contiene datos.

#### CP-09. Excel dañado conserva los datos anteriores
- **Historia:** #14, #10
- **Objetivo:** comprobar que tras un error se conservan los datos cargados antes.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1 y F-3 (`falso.xlsx`).
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Pulsar el botón **⟨B_CARGAR_DATOS⟩**.
  3. Ir a `data/pruebas/`, seleccionar `falso.xlsx` (el archivo se abre al pulsar su nombre).
- **Resultado esperado:** aparece un mensaje de error que indica que el archivo está dañado o no corresponde a su extensión. La ruta sigue siendo la de D-1 y la tabla sigue mostrando 20640 filas.

#### CP-10. Base de datos dañada
- **Historia:** #14, #10
- **Objetivo:** comprobar el error con un `.db` que no es una base de datos.
- **Precondiciones:** aplicación recién abierta (PR-1).
- **Datos de prueba:** F-4 (`falso.db`).
- **Pasos:**
  1. Pulsar el botón **⟨B_CARGAR_DATOS⟩**.
  2. Ir a `data/pruebas/`, seleccionar `falso.db` (el archivo se abre al pulsar su nombre).
- **Resultado esperado:** aparece un mensaje de error que indica que el archivo está dañado o no se puede leer. La tabla sigue vacía.

#### CP-11. SQLite con dos tablas
- **Historia:** #14, #10
- **Objetivo:** comprobar el error con una base de datos con más de una tabla.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior.
- **Datos de prueba:** F-5 (`dos_tablas.db`).
- **Pasos:**
  1. Pulsar el botón **⟨B_CARGAR_DATOS⟩**.
  2. Ir a `data/pruebas/`, seleccionar `dos_tablas.db` (el archivo se abre al pulsar su nombre).
- **Resultado esperado:** aparece un mensaje de error que indica que la base de datos contiene más de una tabla.

#### CP-12. SQLite sin tablas
- **Historia:** #14, #10
- **Objetivo:** comprobar el error con una base de datos sin tablas.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior.
- **Datos de prueba:** F-6 (`sin_tablas.db`).
- **Pasos:**
  1. Pulsar el botón **⟨B_CARGAR_DATOS⟩**.
  2. Ir a `data/pruebas/`, seleccionar `sin_tablas.db` (el archivo se abre al pulsar su nombre).
- **Resultado esperado:** aparece un mensaje de error que indica que la base de datos no contiene ninguna tabla.

#### CP-13. Ruta con espacios, ñ y tildes
- **Historia:** #14, #10
- **Objetivo:** comprobar la carga desde una carpeta con caracteres especiales.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior. Existe la carpeta F-11 con una copia de D-1.
- **Datos de prueba:** F-11.
- **Pasos:**
  1. Pulsar el botón **⟨B_CARGAR_DATOS⟩**.
  2. Ir a `data/pruebas/carpeta ñandú á/`, seleccionar `housing1.csv` (el archivo se abre al pulsar su nombre).
- **Resultado esperado:** la ruta mostrada contiene `carpeta ñandú á` escrito correctamente. La tabla muestra 20640 filas. No hay errores.

#### CP-14. Cargar un segundo dataset sustituye la tabla
- **Historia:** #14
- **Objetivo:** comprobar que un nuevo archivo sustituye ruta y datos.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1 y F-9 (`lineal.csv`).
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Pulsar el botón **⟨B_CARGAR_DATOS⟩**.
  3. Ir a `data/pruebas/`, seleccionar `lineal.csv` (el archivo se abre al pulsar su nombre).
- **Resultado esperado:** la ruta termina en `data/pruebas/lineal.csv`. La tabla tiene exactamente las columnas `x1`, `x2`, `y` y 12 filas. No queda ninguna columna de D-1.

### 4.2 Selección de columnas (#11)

#### CP-15. Los selectores muestran las columnas del dataset
- **Historia:** #11
- **Objetivo:** comprobar que los selectores se rellenan al cargar datos.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Abrir el selector **⟨C_ENTRADAS⟩**.
  3. Cerrarlo y abrir el selector **⟨C_SALIDA⟩**.
- **Resultado esperado:** ambos selectores, identificados con su etiqueta, contienen las 10 columnas de la sección 2.1.

#### CP-16. Selección válida con varias entradas
- **Historia:** #11
- **Objetivo:** comprobar la confirmación de una selección múltiple.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; entradas `median_income` y `housing_median_age`; salida `median_house_value`.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Realizar PR-3 marcando `median_income` y `housing_median_age` como entradas y `median_house_value` como salida.
- **Resultado esperado:** aparece un mensaje de éxito que nombra `median_income` y `housing_median_age` como entradas y `median_house_value` como salida. El botón **⟨B_SEPARAR⟩** queda habilitado.

#### CP-17. Confirmar sin columna de entrada
- **Historia:** #11
- **Objetivo:** comprobar el error cuando falta la entrada.
- **Precondiciones:** D-1 recién cargado: el paso «Realizar PR-2 con D-1» se hace siempre, aunque D-1 ya esté cargado, para empezar sin selecciones.
- **Datos de prueba:** D-1; salida `median_house_value`.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. En el selector **⟨C_SALIDA⟩**, elegir `median_house_value`. No marcar ninguna entrada.
  3. Pulsar **⟨B_CONFIRMAR⟩**.
- **Resultado esperado:** aparece un mensaje de error que indica que falta seleccionar al menos una columna de entrada. El botón **⟨B_SEPARAR⟩** sigue deshabilitado.

#### CP-18. Confirmar sin columna de salida
- **Historia:** #11
- **Objetivo:** comprobar el error cuando falta la salida.
- **Precondiciones:** D-1 recién cargado: el paso «Realizar PR-2 con D-1» se hace siempre, aunque D-1 ya esté cargado, para empezar sin selecciones.
- **Datos de prueba:** D-1; entrada `median_income`.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. En el selector **⟨C_ENTRADAS⟩**, marcar `median_income`. No elegir salida.
  3. Pulsar **⟨B_CONFIRMAR⟩**.
- **Resultado esperado:** aparece un mensaje de error que indica que falta seleccionar la columna de salida.

#### CP-19. La salida no puede ser también entrada
- **Historia:** #11
- **Objetivo:** comprobar que una columna no puede ser entrada y salida a la vez.
- **Precondiciones:** D-1 recién cargado: el paso «Realizar PR-2 con D-1» se hace siempre, aunque D-1 ya esté cargado, para empezar sin selecciones.
- **Datos de prueba:** D-1; columna `median_house_value`.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. En el selector **⟨C_SALIDA⟩**, elegir `median_house_value`.
  3. Abrir el selector **⟨C_ENTRADAS⟩** e intentar marcar `median_house_value`.
- **Resultado esperado:** `median_house_value` no aparece o no se puede marcar en **⟨C_ENTRADAS⟩**. Si la aplicación permite marcarla, al pulsar **⟨B_CONFIRMAR⟩** aparece un mensaje de error que indica que entrada y salida deben ser distintas.

#### CP-20. Columna no numérica
- **Historia:** #11
- **Objetivo:** comprobar el error al elegir una columna de texto.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; entrada `ocean_proximity`; salida `median_house_value`.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Realizar PR-3 con entrada `ocean_proximity` y salida `median_house_value`.
- **Resultado esperado:** aparece un mensaje de error que nombra la columna `ocean_proximity` como no utilizable en un modelo de regresión lineal. El botón **⟨B_SEPARAR⟩** sigue deshabilitado.

#### CP-21. Cargar otro dataset borra la selección
- **Historia:** #11
- **Objetivo:** comprobar que los selectores se actualizan y se vacían al cargar otro archivo.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1 y F-9.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Realizar PR-3 con entrada `median_income` y salida `median_house_value`.
  3. Pulsar **⟨B_CARGAR_DATOS⟩**, ir a `data/pruebas/`, seleccionar `lineal.csv` (el archivo se abre al pulsar su nombre).
  4. Abrir el selector **⟨C_ENTRADAS⟩**.
- **Resultado esperado:** ningún selector tiene columnas marcadas. El selector **⟨C_ENTRADAS⟩** solo ofrece `x1`, `x2` e `y`. El botón **⟨B_SEPARAR⟩** está deshabilitado.

### 4.3 Separación en entrenamiento y test (#41)

#### CP-22. Separar no está disponible antes de confirmar columnas
- **Historia:** #41
- **Objetivo:** comprobar el orden del flujo.
- **Precondiciones:** D-1 recién cargado: el paso «Realizar PR-2 con D-1» se hace siempre, aunque D-1 ya esté cargado, para empezar sin selecciones.
- **Datos de prueba:** D-1.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Observar el botón **⟨B_SEPARAR⟩** sin confirmar ninguna selección.
- **Resultado esperado:** el botón **⟨B_SEPARAR⟩** está deshabilitado. No se puede llegar a los botones **⟨B_PREPROCESAR⟩** ni **⟨B_CREAR_MODELO⟩**: están deshabilitados o en pestañas que aún no aparecen.

#### CP-23. Separación con valores por defecto
- **Historia:** #41
- **Objetivo:** comprobar la separación 80/20.
- **Precondiciones:** aplicación recién abierta (PR-1).
- **Datos de prueba:** D-1; entrada `median_income`; salida `median_house_value`.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Realizar PR-3.
  3. Comprobar que **⟨C_PORCENTAJE⟩** muestra `20` y **⟨C_SEMILLA⟩** muestra `⟨SEMILLA_DEF⟩`.
  4. Pulsar **⟨B_SEPARAR⟩**.
- **Resultado esperado:** aparece un mensaje de confirmación. La interfaz muestra 16512 filas de entrenamiento y 4128 filas de test. La suma es 20640.

#### CP-24. Porcentaje 0 (valor límite)
- **Historia:** #41
- **Objetivo:** comprobar que se rechaza el porcentaje 0.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; porcentaje `0`.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Realizar PR-3.
  3. En **⟨C_PORCENTAJE⟩**, borrar el valor actual y escribir `0`.
  4. Pulsar **⟨B_SEPARAR⟩**.
- **Resultado esperado:** aparece un mensaje de error que indica que el porcentaje debe estar entre 1 y 99. No se muestran tamaños de conjuntos. **⟨B_CREAR_MODELO⟩** sigue deshabilitado.

#### CP-25. Porcentaje 1 (valor límite)
- **Historia:** #41
- **Objetivo:** comprobar que se acepta el porcentaje 1.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; porcentaje `1`.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Realizar PR-3.
  3. En **⟨C_PORCENTAJE⟩**, borrar el valor actual y escribir `1`.
  4. Pulsar **⟨B_SEPARAR⟩**.
- **Resultado esperado:** mensaje de confirmación. Test: 207 filas. Entrenamiento: 20433 filas.

#### CP-26. Porcentaje 99 (valor límite)
- **Historia:** #41
- **Objetivo:** comprobar que se acepta el porcentaje 99.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; porcentaje `99`.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Realizar PR-3.
  3. En **⟨C_PORCENTAJE⟩**, borrar el valor actual y escribir `99`.
  4. Pulsar **⟨B_SEPARAR⟩**.
- **Resultado esperado:** mensaje de confirmación. Test: 20434 filas. Entrenamiento: 206 filas.

#### CP-27. Porcentaje 100 (valor límite)
- **Historia:** #41
- **Objetivo:** comprobar que se rechaza el porcentaje 100.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; porcentaje `100`.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Realizar PR-3.
  3. En **⟨C_PORCENTAJE⟩**, borrar el valor actual y escribir `100`.
  4. Pulsar **⟨B_SEPARAR⟩**.
- **Resultado esperado:** mensaje de error que indica que el porcentaje debe estar entre 1 y 99. No se muestran tamaños. **⟨B_CREAR_MODELO⟩** sigue deshabilitado.

#### CP-28. Porcentaje no numérico o negativo
- **Historia:** #41
- **Objetivo:** comprobar que se rechazan valores no válidos.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; porcentajes `abc`, `-5` y campo vacío.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Realizar PR-3.
  3. En **⟨C_PORCENTAJE⟩**, borrar el valor y escribir `abc`. Pulsar **⟨B_SEPARAR⟩**. Anotar el mensaje.
  4. Borrar el valor y escribir `-5`. Pulsar **⟨B_SEPARAR⟩**. Anotar el mensaje.
  5. Borrar el valor y dejar el campo vacío. Pulsar **⟨B_SEPARAR⟩**. Anotar el mensaje.
- **Resultado esperado:** en los tres intentos aparece un mensaje de error sobre el porcentaje y no se realiza la separación. (Si el campo no deja escribir letras, el paso 3 se da por correcto.)

#### CP-29. Semilla no entera
- **Historia:** #41
- **Objetivo:** comprobar que se rechaza una semilla con decimales o texto.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; semillas `3.5` y `abc`.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Realizar PR-3.
  3. En **⟨C_SEMILLA⟩**, borrar el valor y escribir `3.5`. Pulsar **⟨B_SEPARAR⟩**.
  4. Borrar el valor y escribir `abc`. Pulsar **⟨B_SEPARAR⟩**.
- **Resultado esperado:** en ambos intentos aparece un mensaje de error que indica que la semilla debe ser un número entero.

#### CP-30. Misma semilla, misma separación
- **Historia:** #41
- **Objetivo:** comprobar que la separación es reproducible.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior.
- **Datos de prueba:** F-9 (`lineal.csv`); entradas `x1`, `x2`; salida `y`; semilla `7`.
- **Pasos:**
  1. Realizar PR-2 con `data/pruebas/lineal.csv`.
  2. Realizar PR-3 con entradas `x1` y `x2` y salida `y`.
  3. En **⟨C_SEMILLA⟩**, escribir `7`. Pulsar **⟨B_SEPARAR⟩**.
  4. Realizar PR-5. Anotar la fórmula y el ECM de test.
  5. Pulsar de nuevo **⟨B_SEPARAR⟩** (semilla `7`) y realizar PR-5. Anotar el ECM de test.
- **Resultado esperado:** los tamaños de los conjuntos son iguales en ambas separaciones y los valores anotados coinciden exactamente.

#### CP-31. Dataset con menos de 5 filas
- **Historia:** #41
- **Objetivo:** comprobar el error con un dataset demasiado pequeño.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior.
- **Datos de prueba:** F-8 (`cuatro_filas.csv`); entrada `x`; salida `y`.
- **Pasos:**
  1. Realizar PR-2 con `data/pruebas/cuatro_filas.csv`.
  2. Realizar PR-3 con entrada `x` y salida `y`.
  3. Pulsar **⟨B_SEPARAR⟩**.
- **Resultado esperado:** mensaje de error que explica que el dataset debe tener al menos 5 filas. No se realiza la separación.

#### CP-32. Porcentaje que deja vacío el conjunto de entrenamiento
- **Historia:** #41
- **Objetivo:** comprobar el error si un conjunto quedaría vacío.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior.
- **Datos de prueba:** F-14 (`cinco_filas.csv`, 5 filas); porcentaje `99`.
- **Pasos:**
  1. Realizar PR-2 con `data/pruebas/cinco_filas.csv`.
  2. Realizar PR-3 con entrada `x` y salida `y`.
  3. En **⟨C_PORCENTAJE⟩**, escribir `99`. Pulsar **⟨B_SEPARAR⟩**.
- **Resultado esperado:** mensaje de error que explica que con ese porcentaje el conjunto de entrenamiento quedaría vacío (99 % de 5 filas, redondeado hacia arriba, son 5 filas de test). No se realiza la separación.

#### CP-33. Repetir la separación descarta el modelo
- **Historia:** #41, #16
- **Objetivo:** comprobar que una nueva separación invalida el modelo anterior.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; porcentaje `30`.
- **Pasos:**
  1. Realizar PR-2 con D-1, PR-3 y PR-4.
  2. Realizar PR-5. Comprobar que aparece la fórmula.
  3. En **⟨C_PORCENTAJE⟩**, escribir `30`. Pulsar **⟨B_SEPARAR⟩**.
- **Resultado esperado:** la fórmula, las métricas y el gráfico desaparecen (o se marcan como no válidos). Las secciones de predicción y guardado quedan deshabilitadas hasta crear un nuevo modelo.

#### CP-34. Cambiar las columnas obliga a separar de nuevo
- **Historia:** #41
- **Objetivo:** comprobar que una nueva selección invalida la separación.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1.
- **Pasos:**
  1. Realizar PR-2 con D-1, PR-3 y PR-4.
  2. Realizar PR-3 con entradas `median_income` y `housing_median_age` y salida `median_house_value`.
- **Resultado esperado:** ya no se muestran los tamaños de los conjuntos y **⟨B_CREAR_MODELO⟩** está deshabilitado hasta volver a pulsar **⟨B_SEPARAR⟩**.

### 4.4 Preprocesado de valores inexistentes (#26)

> En los casos CP-35 a CP-43 se usa la entrada `total_bedrooms` y la salida `median_house_value`.

#### CP-35. Detección de valores inexistentes
- **Historia:** #26
- **Objetivo:** comprobar el recuento de valores vacíos por conjunto.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; entrada `total_bedrooms`; salida `median_house_value`.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Realizar PR-3 con entrada `total_bedrooms` y salida `median_house_value`.
  3. Realizar PR-4.
  4. En la sección **⟨S_PREPROCESADO⟩**, leer los recuentos de entrenamiento y test de `total_bedrooms`.
- **Resultado esperado:** se muestran por separado los valores inexistentes de entrenamiento y de test para `total_bedrooms`, y su suma es 207. Para `median_house_value` se muestra 0 en ambos. **⟨B_CREAR_MODELO⟩** está deshabilitado.

#### CP-36. Sin valores inexistentes se puede continuar
- **Historia:** #26
- **Objetivo:** comprobar el aviso cuando no hay nada que preprocesar.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; entrada `median_income`; salida `median_house_value`.
- **Pasos:**
  1. Realizar PR-2 con D-1, PR-3 y PR-4.
- **Resultado esperado:** la sección **⟨S_PREPROCESADO⟩** indica que no hay valores inexistentes. **⟨B_CREAR_MODELO⟩** está habilitado sin aplicar preprocesado.

#### CP-37. Eliminar filas
- **Historia:** #26
- **Objetivo:** comprobar la eliminación de filas con valores vacíos.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; entrada `total_bedrooms`; salida `median_house_value`.
- **Pasos:**
  1. Realizar PR-2 con D-1, PR-3 (entrada `total_bedrooms`, salida `median_house_value`) y PR-4.
  2. En **⟨S_PREPROCESADO⟩**, elegir la opción **⟨O_ELIMINAR⟩**.
  3. Pulsar **⟨B_PREPROCESAR⟩**.
- **Resultado esperado:** mensaje de éxito con las filas eliminadas en cada conjunto, que suman 207. Los recuentos de valores inexistentes pasan a 0. **⟨B_CREAR_MODELO⟩** queda habilitado.

#### CP-38. Rellenar con la media
- **Historia:** #26
- **Objetivo:** comprobar el relleno con la media.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; entrada `total_bedrooms`; salida `median_house_value`.
- **Pasos:**
  1. Realizar PR-2, PR-3 (entrada `total_bedrooms`, salida `median_house_value`) y PR-4.
  2. Elegir **⟨O_MEDIA⟩** y pulsar **⟨B_PREPROCESAR⟩**.
- **Resultado esperado:** mensaje de éxito con los valores rellenados en cada conjunto, que suman 207. Los tamaños de los conjuntos no cambian. Los recuentos pasan a 0 y **⟨B_CREAR_MODELO⟩** queda habilitado.

#### CP-39. Rellenar con la mediana
- **Historia:** #26
- **Objetivo:** comprobar el relleno con la mediana.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen). Datos: como CP-38.
- **Pasos:**
  1. Realizar PR-2, PR-3 (entrada `total_bedrooms`, salida `median_house_value`) y PR-4.
  2. Elegir **⟨O_MEDIANA⟩** y pulsar **⟨B_PREPROCESAR⟩**.
- **Resultado esperado:** igual que CP-38.

#### CP-40. Rellenar con un valor constante
- **Historia:** #26
- **Objetivo:** comprobar el relleno con una constante, incluido el separador decimal.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen). Datos: como CP-38; constante `0`.
- **Pasos:**
  1. Realizar PR-2, PR-3 (entrada `total_bedrooms`, salida `median_house_value`) y PR-4.
  2. Antes de elegir la opción, comprobar si el campo **⟨C_CONSTANTE⟩** está habilitado.
  3. Elegir **⟨O_CONSTANTE⟩**.
  4. En **⟨C_CONSTANTE⟩**, escribir `0`.
  5. Pulsar **⟨B_PREPROCESAR⟩**.
- **Resultado esperado:** en el paso 2 el campo está deshabilitado; tras el paso 3, habilitado. Mensaje de éxito con 207 valores rellenados en total. Recuentos a 0.

#### CP-41. Constante no numérica
- **Historia:** #26
- **Objetivo:** comprobar el error con una constante no válida.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen). Datos: como CP-38; constante `abc`.
- **Pasos:**
  1. Realizar PR-2, PR-3 (entrada `total_bedrooms`, salida `median_house_value`) y PR-4.
  2. Elegir **⟨O_CONSTANTE⟩**, escribir `abc` en **⟨C_CONSTANTE⟩** y pulsar **⟨B_PREPROCESAR⟩**.
  3. Borrar `abc`, escribir `5` y pulsar **⟨B_PREPROCESAR⟩**.
- **Resultado esperado:** tras el paso 2, mensaje de error sobre la constante y los recuentos siguen como antes. Tras el paso 3, mensaje de éxito y recuentos a 0.

#### CP-42. Eliminación que vaciaría un conjunto
- **Historia:** #26
- **Objetivo:** comprobar el aviso si la eliminación deja un conjunto vacío.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior.
- **Datos de prueba:** F-10 (`nulos_total.csv`); entrada `x`; salida `y`.
- **Pasos:**
  1. Realizar PR-2 con `data/pruebas/nulos_total.csv`.
  2. Realizar PR-3 con entrada `x` y salida `y`.
  3. Realizar PR-4.
  4. Elegir **⟨O_ELIMINAR⟩** y pulsar **⟨B_PREPROCESAR⟩**.
- **Resultado esperado:** aviso que indica que la eliminación dejaría vacío un conjunto. No se aplica el cambio: los recuentos siguen igual y **⟨B_CREAR_MODELO⟩** sigue deshabilitado.

#### CP-43. Repetir la separación obliga a repetir el preprocesado
- **Historia:** #26, #41
- **Objetivo:** comprobar que el preprocesado se invalida al separar de nuevo.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen). Datos: como CP-38; porcentaje `30`.
- **Pasos:**
  1. Realizar CP-38 completo.
  2. En **⟨C_PORCENTAJE⟩**, escribir `30` y pulsar **⟨B_SEPARAR⟩**.
- **Resultado esperado:** los recuentos vuelven a mostrar valores inexistentes (suma 207) y **⟨B_CREAR_MODELO⟩** queda deshabilitado.

#### CP-44. El archivo original no se modifica
- **Historia:** #26
- **Objetivo:** comprobar que el preprocesado no cambia el archivo en disco.
- **Precondiciones:** CP-37 ejecutado.
- **Datos de prueba:** D-1.
- **Pasos:**
  1. Cerrar la aplicación (PR-1, paso 1).
  2. Abrir D-1 con una hoja de cálculo y contar las celdas vacías de `total_bedrooms`.
- **Resultado esperado:** hay 207 celdas vacías y 20640 filas, igual que antes de las pruebas.

#### CP-45. Crear modelo deshabilitado con valores inexistentes
- **Historia:** #26, #16
- **Objetivo:** comprobar que no se puede crear el modelo con valores vacíos.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen). Datos: como CP-35.
- **Pasos:**
  1. Realizar los pasos 1 a 3 de CP-35.
  2. Intentar pulsar **⟨B_CREAR_MODELO⟩**.
- **Resultado esperado:** el botón está deshabilitado y no ocurre nada al pulsarlo.

### 4.5 Creación del modelo (#16)

#### CP-46. Crear modelo deshabilitado sin separación
- **Historia:** #16
- **Objetivo:** comprobar las condiciones del botón **⟨B_CREAR_MODELO⟩**.
- **Precondiciones:** aplicación recién abierta (PR-1).
- **Datos de prueba:** D-1.
- **Pasos:**
  1. Observar **⟨B_CREAR_MODELO⟩**.
  2. Realizar PR-2 con D-1 y observarlo.
  3. Realizar PR-3 y observarlo.
  4. Realizar PR-4 y observarlo.
- **Resultado esperado:** en los pasos 1, 2 y 3 no se puede usar (está deshabilitado o su pestaña aún no aparece); en el paso 4, tras ir a la pestaña "Modelo", está habilitado.

#### CP-47. Modelo con resultado exacto (regresión múltiple)
- **Historia:** #16
- **Objetivo:** comprobar fórmula, coeficiente negativo y métricas con un resultado conocido.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior.
- **Datos de prueba:** F-9 (`lineal.csv`); entradas `x1`, `x2`; salida `y`.
- **Pasos:**
  1. Realizar PR-2 con `data/pruebas/lineal.csv`.
  2. Realizar PR-3 con entradas `x1` y `x2` y salida `y`.
  3. Realizar PR-4.
  4. Realizar PR-5.
- **Resultado esperado:**
  - Mensaje de éxito.
  - **⟨L_FORMULA⟩** muestra `y = 2 * x1 - 3 * x2 + 5`, con ⟨DEC⟩ decimales en cada número (es decir, `y = 2.0000 · x1 − 3.0000 · x2 + 5.0000`). El coeficiente de `x2` aparece **restando**, nunca como `+ -3`.
  - **⟨T_METRICAS⟩** muestra R² = 1 y ECM = 0 (redondeados) en las columnas de entrenamiento y de test.

#### CP-48. Gráfico de regresión simple
- **Historia:** #16
- **Objetivo:** comprobar el gráfico con una sola entrada.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; entrada `median_income`; salida `median_house_value`.
- **Pasos:**
  1. Realizar PR-2 con D-1, PR-3, PR-4 y PR-5.
- **Resultado esperado:** **⟨G_AJUSTE⟩** aparece dentro de la ventana y muestra: puntos de entrenamiento y de test en colores o formas distintos, una recta de ajuste, una leyenda que identifica los tres elementos, el eje X con el nombre `median_income` y el eje Y con el nombre `median_house_value`. **⟨L_FORMULA⟩** tiene la forma `median_house_value = <número> * median_income ± <número>`.

#### CP-49. Gráfico de regresión múltiple
- **Historia:** #16
- **Objetivo:** comprobar el gráfico de real frente a predicho.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1; entradas `median_income`, `housing_median_age`; salida `median_house_value`.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Realizar PR-3 con entradas `median_income` y `housing_median_age` y salida `median_house_value`.
  3. Realizar PR-4 y PR-5.
- **Resultado esperado:** el gráfico muestra puntos de entrenamiento y test diferenciados, la recta en la que valor real y predicho coinciden, una leyenda, y los ejes etiquetados "Valor real" y "Valor predicho". La fórmula incluye `median_income` y `housing_median_age`.

#### CP-50. Métricas por conjunto
- **Historia:** #16
- **Objetivo:** comprobar que se distinguen las métricas de entrenamiento y test.
- **Precondiciones:** CP-48 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** los de CP-48.
- **Pasos:**
  1. Observar **⟨T_METRICAS⟩**.
- **Resultado esperado:** hay un valor de R² y uno de ECM para entrenamiento y otro par para test, claramente etiquetados. R² ≤ 1 y ECM ≥ 0 en ambos.

#### CP-51. Un nuevo modelo sustituye al anterior
- **Historia:** #16
- **Objetivo:** comprobar que al crear otro modelo se actualiza todo.
- **Precondiciones:** CP-50 ejecutado, sin cerrar la aplicación. Anotar la fórmula.
- **Datos de prueba:** entradas `median_income`, `housing_median_age`.
- **Pasos:**
  1. Realizar PR-3 con entradas `median_income` y `housing_median_age` y salida `median_house_value`.
  2. Realizar PR-4 y PR-5.
- **Resultado esperado:** la fórmula, el gráfico y las métricas cambian: la fórmula contiene ahora `housing_median_age` y el gráfico es de tipo real frente a predicho.

#### CP-52. Con datos preprocesados se puede crear el modelo
- **Historia:** #16, #26
- **Objetivo:** comprobar la integración preprocesado → modelo.
- **Precondiciones:** CP-38 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** los de CP-38.
- **Pasos:**
  1. Ir a la pestaña "Modelo". Si el modelo no se ha creado al aplicar el preprocesado, realizar PR-5.
- **Resultado esperado:** mensaje de éxito «Modelo creado correctamente.» (al aplicar el preprocesado, la aplicación ya crea el modelo); se muestran fórmula con `total_bedrooms`, gráfico y métricas.

#### CP-53. Error durante la creación del modelo
- **Historia:** #16
- **Objetivo:** comprobar que la aplicación sigue funcionando si el modelo no se puede crear.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior.
- **Datos de prueba:** F-10 (`nulos_total.csv`); constante `0`.
- **Pasos:**
  1. Realizar PR-2 con `data/pruebas/nulos_total.csv`, PR-3 (entrada `x`, salida `y`) y PR-4.
  2. Elegir **⟨O_CONSTANTE⟩**, escribir `0` y pulsar **⟨B_PREPROCESAR⟩** (la columna `x` queda con todos los valores iguales).
  3. Realizar PR-5.
- **Resultado esperado:** la aplicación crea el modelo (con coeficiente 0 para `x`) o muestra un mensaje de error explicativo. En ningún caso se cierra, se queda bloqueada ni muestra una traza de Python.

### 4.6 Descripción del modelo (#33)

#### CP-54. Descripción deshabilitada sin modelo
- **Historia:** #33
- **Objetivo:** comprobar que el área de descripción solo está disponible con modelo.
- **Precondiciones:** aplicación recién abierta (PR-1).
- **Datos de prueba:** ninguno.
- **Pasos:**
  1. Buscar el área **⟨C_DESCRIPCION⟩** e intentar escribir en ella.
- **Resultado esperado:** el área está oculta o deshabilitada y no se puede escribir.

#### CP-55. Escribir una descripción de varias líneas
- **Historia:** #33
- **Objetivo:** comprobar que la descripción admite varias líneas y se indica como opcional.
- **Precondiciones:** CP-79 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** texto `Modelo de prueba` (línea 1) y `Creado con lineal.csv` (línea 2).
- **Pasos:**
  1. Hacer clic en **⟨C_DESCRIPCION⟩**.
  2. Escribir `Modelo de prueba`, pulsar `Enter` y escribir `Creado con lineal.csv`.
- **Resultado esperado:** el área indica que la descripción es opcional y muestra las dos líneas escritas.

#### CP-56. Un modelo nuevo vacía la descripción
- **Historia:** #33
- **Objetivo:** comprobar que la descripción pertenece a cada modelo.
- **Precondiciones:** CP-64 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** los de CP-47.
- **Pasos:**
  1. Realizar PR-4 y PR-5.
- **Resultado esperado:** **⟨C_DESCRIPCION⟩** aparece vacía.

### 4.7 Guardado del modelo (#21)

#### CP-57. Guardar modelo deshabilitado sin modelo
- **Historia:** #21
- **Objetivo:** comprobar el estado del botón.
- **Precondiciones:** aplicación recién abierta (PR-1).
- **Datos de prueba:** D-1.
- **Pasos:**
  1. Observar **⟨B_GUARDAR_MODELO⟩**.
  2. Realizar PR-2, PR-3 y PR-4 y observarlo.
  3. Realizar PR-5 y observarlo.
- **Resultado esperado:** en los pasos 1 y 2 no se puede usar (está deshabilitado o su pestaña aún no aparece); en el paso 3 está habilitado.

#### CP-58. Guardar un modelo con descripción
- **Historia:** #21
- **Objetivo:** comprobar el guardado y la extensión automática.
- **Precondiciones:** CP-55 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** nombre `modelo_lineal` (sin extensión); carpeta `data/pruebas/`.
- **Pasos:**
  1. Pulsar **⟨B_GUARDAR_MODELO⟩**.
  2. En el diálogo, ir a la carpeta `data/pruebas/`.
  3. En **⟨C_NOMBRE_ARCHIVO⟩**, escribir `modelo_lineal`.
  4. Pulsar **⟨B_GUARDAR⟩**.
- **Resultado esperado:** mensaje de confirmación con la ruta completa, que termina en `data/pruebas/modelo_lineal⟨EXT⟩`. El archivo existe en esa carpeta.

#### CP-59. Contenido del archivo guardado
- **Historia:** #21
- **Objetivo:** comprobar qué información se guarda y qué no.
- **Precondiciones:** CP-58 ejecutado.
- **Datos de prueba:** `data/pruebas/modelo_lineal⟨EXT⟩`.
- **Pasos:**
  1. Abrir el archivo con un editor de texto.
- **Resultado esperado:** el archivo contiene los coeficientes y el término independiente, la fórmula, las columnas `x1`, `x2` y `y`, R² y ECM de entrenamiento y test, y la descripción `Modelo de prueba` / `Creado con lineal.csv`. **No** contiene las filas de datos de `lineal.csv` (por ejemplo, no aparece la secuencia de valores `7, 6, 11, 7, 12…`) ni imágenes.

#### CP-60. Aviso con descripción vacía
- **Historia:** #21
- **Objetivo:** comprobar el aviso sin bloquear el guardado.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior.
- **Datos de prueba:** F-9; nombre `sin_descripcion`.
- **Pasos:**
  1. Realizar PR-2 con `data/pruebas/lineal.csv`, PR-3 (entradas `x1`, `x2`; salida `y`), PR-4 y PR-5.
  2. Sin escribir descripción, pulsar **⟨B_GUARDAR_MODELO⟩**.
  3. Ir a `data/pruebas/`, escribir `sin_descripcion` y pulsar **⟨B_GUARDAR⟩**. Si aparece un aviso que pide confirmar, confirmar.
- **Resultado esperado:** aparece un aviso de que la descripción está vacía, pero el modelo se guarda y aparece la confirmación con la ruta de `sin_descripcion⟨EXT⟩`.

#### CP-61. Confirmación al sobrescribir
- **Historia:** #21
- **Objetivo:** comprobar que se pide confirmación antes de sobrescribir.
- **Precondiciones:** CP-58 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** nombre `modelo_lineal`.
- **Pasos:**
  1. Pulsar **⟨B_GUARDAR_MODELO⟩**, ir a `data/pruebas/`, escribir `modelo_lineal` y pulsar **⟨B_GUARDAR⟩**.
  2. En la pregunta de confirmación, elegir **⟨B_CANCELAR⟩**.
  3. Repetir el paso 1 y, esta vez, confirmar la sobrescritura.
- **Resultado esperado:** en el paso 1 aparece una pregunta de confirmación. Tras cancelar, no se guarda nada. Tras confirmar, aparece el mensaje de confirmación con la ruta.

#### CP-62. Cerrar el diálogo sin guardar
- **Historia:** #21
- **Objetivo:** comprobar que cancelar no guarda nada ni produce errores.
- **Precondiciones:** CP-61 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** ninguno.
- **Pasos:**
  1. Pulsar **⟨B_GUARDAR_MODELO⟩**.
  2. Pulsar **⟨B_CANCELAR⟩** (o `Esc`).
- **Resultado esperado:** no aparece ningún mensaje de error ni de confirmación. No se crea ningún archivo nuevo.

#### CP-63. Guardar en una ruta con caracteres especiales
- **Historia:** #21
- **Objetivo:** comprobar el guardado en carpetas con espacios, ñ y tildes.
- **Precondiciones:** CP-62 ejecutado, sin cerrar la aplicación. Existe F-11.
- **Datos de prueba:** carpeta `data/pruebas/carpeta ñandú á/`; nombre `modelo año`.
- **Pasos:**
  1. Pulsar **⟨B_GUARDAR_MODELO⟩**.
  2. Ir a `data/pruebas/carpeta ñandú á/`, escribir `modelo año` y pulsar **⟨B_GUARDAR⟩**.
- **Resultado esperado:** confirmación con la ruta escrita correctamente. El archivo `modelo año⟨EXT⟩` existe en esa carpeta.

#### CP-64. Error de permisos al guardar
- **Historia:** #21
- **Objetivo:** comprobar el error si no se puede escribir en la carpeta.
- **Precondiciones:** CP-63 ejecutado, sin cerrar la aplicación. Crear la carpeta `data/pruebas/solo_lectura/` y quitarle el permiso de escritura: en Linux o macOS, `chmod a-w data/pruebas/solo_lectura`; en Windows, botón derecho → Propiedades → marcar "Solo lectura" (si Windows no lo respeta, usar una carpeta protegida como `C:\Windows`).
- **Datos de prueba:** nombre `prohibido`.
- **Pasos:**
  1. Pulsar **⟨B_GUARDAR_MODELO⟩**.
  2. Ir a `data/pruebas/solo_lectura/`, escribir `prohibido` y pulsar **⟨B_GUARDAR⟩**.
  3. Pulsar de nuevo **⟨B_GUARDAR_MODELO⟩**, ir a `data/pruebas/`, escribir `reintento` y pulsar **⟨B_GUARDAR⟩**.
- **Resultado esperado:** en el paso 2, mensaje de error claro sobre los permisos, sin traza de Python. En el paso 3, el guardado funciona.
- **Al terminar:** devolver los permisos (`chmod u+w data/pruebas/solo_lectura`).

### 4.8 Recuperación del modelo (#24)

#### CP-65. Cargar un modelo al iniciar la aplicación
- **Historia:** #24
- **Objetivo:** comprobar que se muestra la información del modelo y se ocultan las secciones de datos.
- **Precondiciones:** aplicación recién abierta (PR-1). CP-58 ejecutado (existe `modelo_lineal.json`).
- **Datos de prueba:** `data/pruebas/modelo_lineal⟨EXT⟩`.
- **Pasos:**
  1. Pulsar **⟨B_CARGAR_MODELO⟩**.
  2. Ir a `data/pruebas/`, seleccionar `modelo_lineal⟨EXT⟩` (el archivo se abre al pulsar su nombre).
- **Resultado esperado:**
  - Mensaje de confirmación de carga.
  - Fórmula `y = 2 * x1 - 3 * x2 + 5` (con ⟨DEC⟩ decimales).
  - Entradas `x1`, `x2` y salida `y`.
  - R² y ECM de entrenamiento y test diferenciados.
  - **⟨C_DESCRIPCION⟩** contiene `Modelo de prueba` y `Creado con lineal.csv`.
  - No se ven la tabla de datos, la selección de columnas, la separación, el preprocesado ni el gráfico.
  - La sección **⟨S_PREDICCION⟩** está habilitada.

#### CP-66. El diálogo filtra por la extensión de los modelos
- **Historia:** #24
- **Objetivo:** comprobar el filtro del diálogo de carga.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior. Existen en `data/pruebas/` archivos `.csv` y `.json`.
- **Datos de prueba:** carpeta `data/pruebas/`.
- **Pasos:**
  1. Pulsar **⟨B_CARGAR_MODELO⟩**.
  2. Ir a `data/pruebas/`.
- **Resultado esperado:** se ven los archivos `⟨EXT⟩` y no los `.csv` ni los `.db`.

#### CP-67. Modelo guardado sin descripción
- **Historia:** #24
- **Objetivo:** comprobar que un modelo sin descripción se carga con el área vacía.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior. CP-60 ejecutado.
- **Datos de prueba:** `data/pruebas/sin_descripcion⟨EXT⟩`.
- **Pasos:**
  1. Pulsar **⟨B_CARGAR_MODELO⟩**, ir a `data/pruebas/`, seleccionar `sin_descripcion⟨EXT⟩` (el archivo se abre al pulsar su nombre).
- **Resultado esperado:** mensaje de confirmación. **⟨C_DESCRIPCION⟩** aparece vacía.

#### CP-68. Cancelar la carga del modelo
- **Historia:** #24
- **Objetivo:** comprobar que cancelar mantiene el estado.
- **Precondiciones:** D-1 cargado. Si ya es el dataset cargado, el paso «Realizar PR-2 con D-1» se salta (puede haber selecciones o un modelo de un caso anterior: los pasos del caso los sustituyen).
- **Datos de prueba:** D-1.
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Pulsar **⟨B_CARGAR_MODELO⟩** y, en el diálogo, pulsar **⟨B_CANCELAR⟩**.
- **Resultado esperado:** sin mensajes de error. La tabla sigue mostrando D-1.

#### CP-69. Modelo dañado
- **Historia:** #24
- **Objetivo:** comprobar el error con un archivo que no es un modelo.
- **Precondiciones:** CP-65 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** F-12 (`modelo_roto.json`).
- **Pasos:**
  1. Pulsar **⟨B_CARGAR_MODELO⟩**, ir a `data/pruebas/`, seleccionar `modelo_roto.json` (el archivo se abre al pulsar su nombre).
- **Resultado esperado:** mensaje de error claro (archivo dañado o con formato no válido). Se sigue mostrando el modelo de CP-65 sin cambios.

#### CP-70. Modelo incompleto
- **Historia:** #24
- **Objetivo:** comprobar el error si al archivo le falta información.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior.
- **Datos de prueba:** F-13 (`modelo_incompleto.json`), y después `modelo_lineal⟨EXT⟩`.
- **Pasos:**
  1. Pulsar **⟨B_CARGAR_MODELO⟩**, ir a `data/pruebas/`, seleccionar `modelo_incompleto.json` (el archivo se abre al pulsar su nombre).
  2. Pulsar **⟨B_CARGAR_MODELO⟩**, seleccionar `modelo_lineal⟨EXT⟩` (el archivo se abre al pulsar su nombre).
- **Resultado esperado:** en el paso 1, mensaje de error que indica que falta información del modelo. En el paso 2, el modelo se carga correctamente.

#### CP-71. Solo la descripción es editable
- **Historia:** #24
- **Objetivo:** comprobar qué se puede modificar en un modelo cargado.
- **Precondiciones:** CP-69 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** ninguno.
- **Pasos:**
  1. Intentar escribir en la fórmula, en los nombres de las columnas y en las métricas.
  2. Escribir al final de **⟨C_DESCRIPCION⟩** el texto ` (revisado)`.
- **Resultado esperado:** la fórmula, las columnas y las métricas no se pueden modificar. La descripción sí. Tras el paso 2, la **⟨BARRA_ESTADO⟩** indica que hay cambios sin guardar.

#### CP-72. Volver a guardar un modelo cargado con nueva descripción
- **Historia:** #24, #21
- **Objetivo:** comprobar que se guarda la nueva descripción sin cambiar el resto.
- **Precondiciones:** CP-71 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** `data/pruebas/modelo_lineal⟨EXT⟩`.
- **Pasos:**
  1. Pulsar **⟨B_GUARDAR_MODELO⟩**.
  2. Comprobar la carpeta y el nombre que propone el diálogo.
  3. Pulsar **⟨B_GUARDAR⟩** y confirmar la sobrescritura.
  4. Realizar PR-1.
  5. Pulsar **⟨B_CARGAR_MODELO⟩**, seleccionar `data/pruebas/modelo_lineal⟨EXT⟩` (el archivo se abre al pulsar su nombre).
- **Resultado esperado:** en el paso 2 se proponen `data/pruebas/` y `modelo_lineal⟨EXT⟩`. En el paso 3 se pide confirmación y, tras guardar, la barra de estado deja de indicar cambios sin guardar. En el paso 5, la descripción termina en `(revisado)` y la fórmula y las métricas son las mismas que en CP-65.

#### CP-73. Confirmación al sustituir un modelo con cambios sin guardar
- **Historia:** #24
- **Objetivo:** comprobar que no se pierde un modelo sin guardar sin avisar.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior.
- **Datos de prueba:** F-9; `modelo_lineal⟨EXT⟩`.
- **Pasos:**
  1. Realizar PR-2 con `data/pruebas/lineal.csv`, PR-3 (entradas `x1`, `x2`; salida `y`), PR-4 y PR-5. No guardar.
  2. Pulsar **⟨B_CARGAR_MODELO⟩**, seleccionar `modelo_lineal⟨EXT⟩` (el archivo se abre al pulsar su nombre).
  3. En la pregunta, elegir **⟨B_CANCELAR⟩**.
  4. Repetir el paso 2 y confirmar.
- **Resultado esperado:** en el paso 2 aparece una pregunta de confirmación. Tras cancelar, sigue el modelo creado con su gráfico. Tras confirmar, se muestra el modelo cargado.

#### CP-74. Cargar un dataset después de un modelo cargado
- **Historia:** #24
- **Objetivo:** comprobar que vuelven las secciones de datos.
- **Precondiciones:** CP-72 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** D-1.
- **Pasos:**
  1. Realizar PR-2 con D-1. Si aparece una pregunta de confirmación, confirmar.
- **Resultado esperado:** vuelven a verse la tabla (20640 filas), la selección de columnas, la separación y el preprocesado. El modelo cargado se descarta: la predicción y el guardado quedan deshabilitados.

### 4.9 Predicciones (#22)

#### CP-75. Predicción deshabilitada sin modelo
- **Historia:** #22
- **Objetivo:** comprobar el estado de la sección sin modelo.
- **Precondiciones:** aplicación recién abierta (PR-1).
- **Datos de prueba:** ninguno.
- **Pasos:**
  1. Buscar la sección **⟨S_PREDICCION⟩** e intentar usarla.
- **Resultado esperado:** la sección está oculta o deshabilitada.

#### CP-76. Predicción con un modelo creado
- **Historia:** #22
- **Objetivo:** comprobar campos, cálculo y formato del resultado.
- **Precondiciones:** CP-47 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** `x1 = 2.5`, `x2 = 1`.
- **Pasos:**
  1. En **⟨S_PREDICCION⟩**, comprobar qué campos aparecen.
  2. En el campo `x1`, escribir `2.5`.
  3. En el campo `x2`, escribir `1`.
  4. Pulsar **⟨B_PREDECIR⟩**.
- **Resultado esperado:** en el paso 1 hay exactamente dos campos, etiquetados `x1` y `x2`. **⟨L_RESULTADO⟩** muestra `y = 7` con ⟨DEC⟩ decimales (cálculo: 2·2,5 − 3·1 + 5 = 7).

#### CP-77. Decimales con coma
- **Historia:** #22
- **Objetivo:** comprobar que se acepta la coma como separador decimal.
- **Precondiciones:** CP-76 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** `x1 = 2,5`, `x2 = 0,5`.
- **Pasos:**
  1. Escribir `2,5` en `x1` y `0,5` en `x2`.
  2. Pulsar **⟨B_PREDECIR⟩**.
- **Resultado esperado:** `y = 8.5` con ⟨DEC⟩ decimales (2·2,5 − 3·0,5 + 5 = 8,5).

#### CP-78. Falta un valor
- **Historia:** #22
- **Objetivo:** comprobar el error si falta un valor.
- **Precondiciones:** CP-77 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** `x1` vacío, `x2 = 1`.
- **Pasos:**
  1. Borrar el contenido de `x1` y escribir `1` en `x2`.
  2. Pulsar **⟨B_PREDECIR⟩**.
- **Resultado esperado:** mensaje de error que nombra `x1` como variable sin valor.

#### CP-79. Valor no numérico y corrección
- **Historia:** #22
- **Objetivo:** comprobar el error con texto y que se puede corregir.
- **Precondiciones:** CP-78 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** `x1 = 1`, `x2 = abc`; después `x2 = 2`.
- **Pasos:**
  1. Escribir `1` en `x1` y `abc` en `x2`. Pulsar **⟨B_PREDECIR⟩**.
  2. Cambiar `x2` a `2`. Pulsar **⟨B_PREDECIR⟩**.
- **Resultado esperado:** en el paso 1, mensaje de error que nombra `x2` como valor no válido. En el paso 2, `y = 1` (2·1 − 3·2 + 5 = 1).

#### CP-80. Mismo resultado con un modelo cargado
- **Historia:** #22, #24
- **Objetivo:** comprobar que un modelo cargado predice igual que el creado.
- **Precondiciones:** aplicación abierta, en el estado que dejó el caso anterior. CP-58 ejecutado.
- **Datos de prueba:** `modelo_lineal⟨EXT⟩`; `x1 = 2.5`, `x2 = 1`.
- **Pasos:**
  1. Pulsar **⟨B_CARGAR_MODELO⟩**, seleccionar `data/pruebas/modelo_lineal⟨EXT⟩` (el archivo se abre al pulsar su nombre).
  2. Escribir `2.5` en `x1` y `1` en `x2`. Pulsar **⟨B_PREDECIR⟩**.
- **Resultado esperado:** `y = 7` con ⟨DEC⟩ decimales, igual que en CP-76.

#### CP-81. Los campos se regeneran con otro modelo
- **Historia:** #22
- **Objetivo:** comprobar que los campos se adaptan al modelo y se borra el resultado anterior.
- **Precondiciones:** CP-56 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** D-1; entrada `median_income`; salida `median_house_value`.
- **Pasos:**
  1. Realizar PR-2 con D-1, PR-3, PR-4 y PR-5.
  2. Observar **⟨S_PREDICCION⟩**.
- **Resultado esperado:** solo hay un campo, etiquetado `median_income`. El resultado `y = 7` ya no se muestra.

### 4.10 Experiencia de usuario (#37)

#### CP-82. Indicación inicial y pasos ordenados
- **Historia:** #37
- **Objetivo:** comprobar que la interfaz guía al usuario.
- **Precondiciones:** aplicación recién abierta (PR-1).
- **Datos de prueba:** ninguno.
- **Pasos:**
  1. Observar la ventana sin hacer nada.
- **Resultado esperado:** se muestra una indicación de cómo empezar (cargar un dataset o cargar un modelo). Las secciones aparecen en el orden del flujo con sus etiquetas. Los botones de los pasos aún no disponibles están deshabilitados.

#### CP-83. Barra de estado
- **Historia:** #37
- **Objetivo:** comprobar que el estado se muestra en todo momento.
- **Precondiciones:** aplicación recién abierta (PR-1).
- **Datos de prueba:** D-1.
- **Pasos:**
  1. Leer la **⟨BARRA_ESTADO⟩**.
  2. Realizar PR-2 con D-1 y leerla.
  3. Realizar PR-3, PR-4 y PR-5 y leerla.
- **Resultado esperado:** en el paso 1 no hay archivo ni modelo; en el paso 2 aparece el nombre del archivo; en el paso 3 indica que hay un modelo creado con cambios sin guardar.

#### CP-84. Mensajes coherentes y sin trazas de Python
- **Historia:** #37
- **Objetivo:** comprobar el formato de los mensajes.
- **Precondiciones:** haber ejecutado CP-01, CP-07, CP-27 y CP-79.
- **Datos de prueba:** mensajes observados en esos casos.
- **Pasos:**
  1. Comparar dónde y cómo aparecieron los mensajes de éxito y de error en esos casos.
- **Resultado esperado:** todos los mensajes aparecen en el mismo tipo de componente (**⟨AVISO⟩**). Ninguno contiene `Traceback`, `Error:` seguido de nombres de clases de Python ni mensajes en inglés de librerías.

#### CP-85. Indicador durante la carga de un archivo grande
- **Historia:** #37
- **Objetivo:** comprobar que la ventana no se bloquea al cargar.
- **Precondiciones:** aplicación recién abierta (PR-1).
- **Datos de prueba:** D-2 (el formato más lento).
- **Pasos:**
  1. Realizar PR-2 con D-2.
  2. Mientras carga, intentar mover la ventana del navegador y observar los botones.
- **Resultado esperado:** aparece un indicador de carga en curso. La ventana se puede mover y no aparece como "no responde". Los botones que iniciarían otra operación están deshabilitados durante la carga.

#### CP-86. Tabla grande fluida
- **Historia:** #37
- **Objetivo:** comprobar la navegación por un dataset de más de 20.000 filas.
- **Precondiciones:** aplicación recién abierta (PR-1).
- **Datos de prueba:** D-1 (20640 filas).
- **Pasos:**
  1. Realizar PR-2 con D-1.
  2. Desplazarse por la tabla hasta la última fila (con la rueda del ratón, la barra de desplazamiento o los controles de página).
- **Resultado esperado:** el desplazamiento no se bloquea. Se puede llegar a la última fila, que coincide con la última fila del archivo abierto en una hoja de cálculo.

#### CP-87. Ventana de 1366 × 768
- **Historia:** #37
- **Objetivo:** comprobar que todo es visible en una pantalla pequeña.
- **Precondiciones:** CP-51 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** ninguno.
- **Pasos:**
  1. Ajustar la ventana del navegador a 1366 × 768 píxeles (en Chrome: `F12` → icono de dispositivo → escribir 1366 y 768).
  2. Recorrer la página.
- **Resultado esperado:** ningún elemento queda cortado ni superpuesto, y todos los botones se pueden pulsar.

#### CP-88. Redimensionar la ventana
- **Historia:** #37
- **Objetivo:** comprobar que la distribución se adapta.
- **Precondiciones:** CP-48 ejecutado.
- **Datos de prueba:** ninguno.
- **Pasos:**
  1. Reducir el ancho de la ventana a la mitad de la pantalla.
  2. Volver a maximizarla.
- **Resultado esperado:** los elementos se reorganizan sin quedar cortados ni superpuestos en ambos tamaños.

### 4.11 Asistente con LLM (funcionalidad añadida)

> Ejecutar solo si el asistente está fusionado en `dev`. Requiere un archivo `.env` en la raíz del repositorio con la clave de Groq (ver `README.md`).

#### CP-89. Explicación del modelo
- **Historia:** — (funcionalidad añadida)
- **Objetivo:** comprobar que el asistente explica el modelo actual.
- **Precondiciones:** CP-47 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** pregunta `¿Qué significa el R² de este modelo?`.
- **Pasos:**
  1. Pulsar el botón flotante del asistente.
  2. Escribir la pregunta y enviarla.
- **Resultado esperado:** el asistente responde en español y menciona el valor de R² que aparece en **⟨T_METRICAS⟩**.

#### CP-90. Transformación propuesta y confirmada
- **Historia:** — (funcionalidad añadida)
- **Objetivo:** comprobar que una transformación solo se aplica tras confirmarla.
- **Precondiciones:** aplicación recién abierta (PR-1) y PR-2 con D-1.
- **Datos de prueba:** petición `Elimina la columna ocean_proximity`.
- **Pasos:**
  1. Abrir el asistente, escribir la petición y enviarla.
  2. Observar la tabla antes de confirmar.
  3. Confirmar la propuesta.
- **Resultado esperado:** en el paso 2 la tabla sigue teniendo 10 columnas. Tras confirmar, tiene 9 columnas y `ocean_proximity` ya no aparece. El archivo D-1 en disco no cambia.

#### CP-91. Deshacer una transformación
- **Historia:** — (funcionalidad añadida)
- **Objetivo:** comprobar el botón de deshacer.
- **Precondiciones:** CP-90 ejecutado, sin cerrar la aplicación.
- **Datos de prueba:** ninguno.
- **Pasos:**
  1. En el asistente, pulsar el botón de deshacer.
- **Resultado esperado:** la tabla vuelve a tener 10 columnas, incluida `ocean_proximity`.

#### CP-92. Sin clave de API
- **Historia:** — (funcionalidad añadida)
- **Objetivo:** comprobar que la aplicación funciona sin clave.
- **Precondiciones:** renombrar `.env` a `.env.bak` y realizar PR-1.
- **Datos de prueba:** pregunta `Hola`.
- **Pasos:**
  1. Abrir el asistente, escribir `Hola` y enviarlo.
  2. Realizar PR-2 con D-1.
- **Resultado esperado:** el asistente muestra un mensaje claro de que no está configurado, sin trazas. La carga de datos del paso 2 funciona con normalidad.
- **Al terminar:** renombrar `.env.bak` a `.env`.

### 4.12 Flujo completo

#### CP-93. Cargar, crear, guardar, cargar y predecir
- **Historia:** #14, #11, #41, #26, #16, #33, #21, #24, #22
- **Objetivo:** recorrer el flujo completo de la aplicación.
- **Precondiciones:** aplicación recién abierta (PR-1). No existe `data/pruebas/flujo_completo.json` (borrarlo si existe).
- **Datos de prueba:** D-1; entradas `total_bedrooms` y `median_income`; salida `median_house_value`; descripción `Flujo completo`; valores de predicción `500` para `total_bedrooms` y `3.5` para `median_income`.
- **Pasos:**
  1. Pulsar **⟨B_CARGAR_DATOS⟩**, ir a `data/`, seleccionar D-1 (el archivo se abre al pulsar su nombre).
  2. En **⟨C_ENTRADAS⟩**, marcar `total_bedrooms` y `median_income`.
  3. En **⟨C_SALIDA⟩**, elegir `median_house_value`.
  4. Pulsar **⟨B_CONFIRMAR⟩**.
  5. Pulsar **⟨B_SEPARAR⟩** sin cambiar porcentaje ni semilla.
  6. En **⟨S_PREPROCESADO⟩**, elegir **⟨O_MEDIANA⟩** y pulsar **⟨B_PREPROCESAR⟩**.
  7. Pulsar **⟨B_CREAR_MODELO⟩**. Anotar la fórmula.
  8. En **⟨C_DESCRIPCION⟩**, escribir `Flujo completo`.
  9. Pulsar **⟨B_GUARDAR_MODELO⟩**, ir a `data/pruebas/`, escribir `flujo_completo` y pulsar **⟨B_GUARDAR⟩**.
  10. En **⟨S_PREDICCION⟩**, escribir `500` y `3.5` y pulsar **⟨B_PREDECIR⟩**. Anotar el resultado.
  11. Cerrar y volver a abrir la aplicación (PR-1).
  12. Pulsar **⟨B_CARGAR_MODELO⟩**, ir a `data/pruebas/`, seleccionar `flujo_completo⟨EXT⟩` (el archivo se abre al pulsar su nombre).
  13. En **⟨S_PREDICCION⟩**, escribir los mismos valores del paso 10 y pulsar **⟨B_PREDECIR⟩**.
- **Resultado esperado:**
  - Cada paso muestra su mensaje de éxito, sin errores.
  - En el paso 12, la fórmula es idéntica a la anotada en el paso 7 y la descripción es `Flujo completo`.
  - El resultado del paso 13 es idéntico al del paso 10 y coincide con el valor calculado a mano con la fórmula anotada.

---

## 5. Ejecución

- Las pruebas se ejecutan sobre `dev` (sección 1.1), después de que pasen todas las pruebas automatizadas, en el orden del plan. Un caso que continúa a otro («CP-xx ejecutado, sin cerrar la aplicación») se ejecuta justo después de CP-xx. Los casos están automatizados con Playwright en `herramientas/funcionales/` (ver [pruebas_funcionales.md](pruebas_funcionales.md)); también se pueden ejecutar con un LLM (ver [pruebas_con_llm.md](pruebas_con_llm.md)).
- Cada caso lo ejecuta un miembro que no haya implementado la funcionalidad probada.
- Cada error encontrado se registra en Taiga como tarea de corrección dentro de la historia #29, indicando el caso que lo detectó, los pasos para reproducirlo y el resultado obtenido. Se corrige en una rama `fix/<número de la tarea>-<descripción>` creada desde `dev`.
- Tras las correcciones, se vuelven a ejecutar los casos fallidos y CP-93.

---

## 6. Registro de ejecución

Copiar esta tabla una vez por ejecución (primera ejecución y reejecución).

**Ejecución n.º:** ___  **Commit de `dev`:** ___

| Caso | Resultado obtenido (solo si difiere del esperado) | Estado (Correcto / Fallido) | Ejecutado por | Fecha | Tarea de Taiga |
|---|---|---|---|---|---|
| CP-01 | | | | | |
| CP-02 | | | | | |
| CP-03 | | | | | |
| CP-04 | | | | | |
| CP-05 | | | | | |
| CP-06 | | | | | |
| CP-07 | | | | | |
| CP-08 | | | | | |
| CP-09 | | | | | |
| CP-10 | | | | | |
| CP-11 | | | | | |
| CP-12 | | | | | |
| CP-13 | | | | | |
| CP-14 | | | | | |
| CP-15 | | | | | |
| CP-16 | | | | | |
| CP-17 | | | | | |
| CP-18 | | | | | |
| CP-19 | | | | | |
| CP-20 | | | | | |
| CP-21 | | | | | |
| CP-22 | | | | | |
| CP-23 | | | | | |
| CP-24 | | | | | |
| CP-25 | | | | | |
| CP-26 | | | | | |
| CP-27 | | | | | |
| CP-28 | | | | | |
| CP-29 | | | | | |
| CP-30 | | | | | |
| CP-31 | | | | | |
| CP-32 | | | | | |
| CP-33 | | | | | |
| CP-34 | | | | | |
| CP-35 | | | | | |
| CP-36 | | | | | |
| CP-37 | | | | | |
| CP-38 | | | | | |
| CP-39 | | | | | |
| CP-40 | | | | | |
| CP-41 | | | | | |
| CP-42 | | | | | |
| CP-43 | | | | | |
| CP-44 | | | | | |
| CP-45 | | | | | |
| CP-46 | | | | | |
| CP-47 | | | | | |
| CP-48 | | | | | |
| CP-49 | | | | | |
| CP-50 | | | | | |
| CP-51 | | | | | |
| CP-52 | | | | | |
| CP-53 | | | | | |
| CP-54 | | | | | |
| CP-55 | | | | | |
| CP-56 | | | | | |
| CP-57 | | | | | |
| CP-58 | | | | | |
| CP-59 | | | | | |
| CP-60 | | | | | |
| CP-61 | | | | | |
| CP-62 | | | | | |
| CP-63 | | | | | |
| CP-64 | | | | | |
| CP-65 | | | | | |
| CP-66 | | | | | |
| CP-67 | | | | | |
| CP-68 | | | | | |
| CP-69 | | | | | |
| CP-70 | | | | | |
| CP-71 | | | | | |
| CP-72 | | | | | |
| CP-73 | | | | | |
| CP-74 | | | | | |
| CP-75 | | | | | |
| CP-76 | | | | | |
| CP-77 | | | | | |
| CP-78 | | | | | |
| CP-79 | | | | | |
| CP-80 | | | | | |
| CP-81 | | | | | |
| CP-82 | | | | | |
| CP-83 | | | | | |
| CP-84 | | | | | |
| CP-85 | | | | | |
| CP-86 | | | | | |
| CP-87 | | | | | |
| CP-88 | | | | | |
| CP-89 | | | | | |
| CP-90 | | | | | |
| CP-91 | | | | | |
| CP-92 | | | | | |
| CP-93 | | | | | |

**Resumen:** ejecutados ___ · correctos ___ · fallidos ___
