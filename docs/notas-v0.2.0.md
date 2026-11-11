# SIKORIUS v0.2.0

Segunda versión publicada de SIKORIUS, una aplicación de escritorio en Python
para crear modelos de regresión lineal a partir de datos en CSV, Excel y
SQLite desde una interfaz gráfica (NiceGUI).

**Estado del proyecto:** en desarrollo. Esta versión ya crea y evalúa modelos
de regresión lineal, pero todavía no permite hacer predicciones ni guardar y
cargar modelos, por eso se publica como *pre-release*.

## Funcionalidades

- Creación del modelo de regresión lineal simple y múltiple por mínimos
  cuadrados, con los datos de entrenamiento (US 16, tarea 116).
- Fórmula del modelo con los nombres de las columnas (US 16, tarea 118).
- Evaluación del modelo: R² y error cuadrático medio (ECM) en entrenamiento y
  en test (US 16, tarea 119).
- Gráfico del ajuste: en regresión simple, los puntos y la recta del modelo;
  en múltiple, el valor real frente al predicho (US 16, tarea 117).
- Descripción opcional del modelo (US 33).
- Al aplicar el preprocesado, el modelo se crea automáticamente.

## Correcciones

- Panel del modelo: la lógica pasa al núcleo (`nucleo/modelo.py`) y el panel
  solo muestra el resultado; el botón "Crear modelo" solo se habilita cuando
  no quedan valores inexistentes (tarea 121).
- Panel de preprocesado: el aviso de valores inexistentes desaparece una vez
  aplicado el preprocesado (tareas 129-131).

## Documentación y cambios internos

- Investigación y prototipos de modelos lineales (US 13).
- Investigación y prototipos de la persistencia de modelos (US 20).
- La integración continua se ejecuta en cada push a cualquier rama y en los
  pull requests hacia `dev` y `main` (US 64).

## Pendiente para próximas versiones

- Hacer predicciones con el modelo.
- Guardar los modelos y cargarlos más tarde (US 20).

## Instalación y uso

Consulta el [README de esta versión](https://github.com/xabierpc/SIKORIUS/blob/v0.2.0/README.md).
