# SIKORIUS v0.1.0

Primera versión publicada de SIKORIUS, una aplicación de escritorio en Python
para crear modelos de regresión lineal a partir de datos en CSV, Excel y
SQLite desde una interfaz gráfica (NiceGUI).

**Estado del proyecto:** en desarrollo. Esta versión cubre la preparación de
los datos, pero todavía no crea modelos, por eso se publica como *pre-release*.

## Funcionalidades

- Carga de datasets CSV, Excel (`.xlsx`, `.xls`) y SQLite (`.sqlite`, `.db`)
  desde un explorador de archivos, y vista de los datos en una tabla (US 10, 14).
- Elección de las columnas de entrada (*features*) y de salida (*target*),
  solo entre columnas numéricas (US 11).
- Separación de los datos en entrenamiento y test con porcentaje y semilla
  configurables (US 41).
- Detección de valores nulos en entrenamiento y test, y tratamiento:
  eliminar filas, o rellenar con la media, la mediana o un valor constante
  (US 26).
- Interfaz por paneles, con los datos y las columnas a la izquierda y la
  separación y el preprocesado a la derecha (tareas 114 y 115).

## Correcciones

- Importador: lee CSV con distintos separadores y decimales, y avisa con un
  mensaje claro si un Excel tiene datos en varias hojas o una base SQLite
  tiene varias tablas, en lugar de leer solo la primera.
- Tabla de datos: ya no falla con fechas, BLOB ni intervalos de tiempo.
- Explorador de archivos: muestra las unidades en Windows.
- Separación: el tamaño del conjunto de test se calcula sin errores de
  redondeo.
- Preprocesado y selección de columnas: se mantienen al recargar la página y
  los avisos reflejan el estado real.

## Cambios internos

- Arquitectura por capas (`nucleo` → `sesion` → `gui`), con un test que
  comprueba que se respeta.
- Formato y estilo con ruff, e integración continua con GitHub Actions
  (ruff y pytest con cobertura).

## Pendiente para próximas versiones

- Crear el modelo de regresión lineal simple y múltiple, y ver su fórmula y
  su gráfica.
- Evaluar el modelo con los datos de test.
- Hacer predicciones con el modelo.
- Guardar los modelos y cargarlos más tarde.

## Instalación y uso

Consulta el [README de esta versión](https://github.com/xabierpc/SIKORIUS/blob/v0.1.0/README.md).
