# SIKORIUS v1.0.0

Versión final de SIKORIUS, una aplicación en Python para crear y visualizar
modelos de regresión lineal simple y múltiple a partir de datos en CSV, Excel
y SQLite, hacer predicciones y guardar los modelos, todo desde una interfaz
gráfica que se abre en el navegador (NiceGUI).

**Estado del proyecto:** estable y completo. Es la primera versión que no se
publica como *pre-release*.

## Funcionalidades principales

- Carga de datasets CSV, Excel y SQLite y vista de los datos en una tabla.
- Elección de las columnas de entrada y de salida.
- Separación en entrenamiento y test con porcentaje y semilla.
- Detección y tratamiento de valores inexistentes.
- Creación del modelo de regresión lineal simple y múltiple, con su fórmula,
  sus métricas (R² y ECM) y el gráfico del ajuste.
- Descripción del modelo.
- Guardado del modelo en JSON y carga posterior.
- Predicciones con el modelo creado o cargado.

## Cambios desde la versión 0.2.0

Agrupados según las ramas `feature/` y `fix/` fusionadas en `dev` desde la
versión anterior.

### Funcionalidades

- Guardado del modelo en un archivo JSON, con diálogo para elegir dónde (US 21).
- Carga de un modelo guardado: núcleo, sesión, botón en la interfaz y tests
  (US 24).
- Predicciones con un modelo creado o cargado, con su panel en la pestaña del
  modelo (US 22).
- Mejora de la interfaz y de la experiencia de usuario: tema oscuro, página
  inicial, pestañas que aparecen a medida que se completan los pasos, nueva
  tipografía, columnas elegidas coloreadas, gráfico interactivo y favicon
  (US 37).
- Pestaña **Inicio** con los botones **Subir dataset** y **Cargar modelo**, y
  pestañas centradas en la barra superior (tarea 168).
- Botón **Continuar** para pasar a la pestaña siguiente (tarea 169).
- Plan de pruebas funcionales automatizado con Playwright y con un LLM
  (US 29).

### Correcciones

- Color del aviso cuando el modelo no tiene descripción (US 37).
- Gráfico del modelo más grande (tarea 170).
- Orden de las métricas R² y ECM en el panel del modelo (tarea 171).
- Nombres de las columnas mostrados tal como están en el dataset (tarea 172).
- Separación del código en capas (`gui` → `aplicacion` → `datos` →
  `dominio`), con la interfaz pasando siempre por la sesión (tarea 115).
- Segunda refactorización: lectura del archivo de modelo en funciones
  pequeñas, estado del archivo agrupado y eliminación de código sin uso
  (tarea 141).

### Documentación

- Revisión completa de la documentación para la versión final: README con
  formato de los datos, guía de uso y limitaciones; estructura del código;
  docstrings de la lógica; pruebas de usabilidad e instalación (US 31).

## Limitaciones conocidas

- Solo se lee una hoja de Excel y una tabla de SQLite; si hay más, la
  aplicación avisa.
- Solo se pueden usar columnas numéricas como entrada y salida.
- Columnas cuyo nombre solo se distingue por el tipo (por ejemplo, `1`
  numérico y `"1"` texto) aparecen repetidas en los selectores y no se pueden
  elegir por separado.
- La aplicación está pensada para usarse en local por una persona.
- Un modelo cargado no muestra el gráfico del ajuste, porque el archivo no
  guarda los datos.

## Instalación y uso

Consulta el [README de esta versión](https://github.com/xabierpc/SIKORIUS/blob/v1.0.0/README.md).