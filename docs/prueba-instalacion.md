# Prueba de instalación con una persona ajena al equipo

Comprueba que una persona que no conoce el proyecto puede clonar el repositorio, instalar el entorno con uv y ejecutar la aplicación siguiendo solo el [`README.md`](../README.md), sin ayuda.

## Datos de la prueba

| Dato | Valor |
|---|---|
| Persona | (nombre), ajena al equipo |
| Fecha | 26/11/2026 |
| Repositorio | https://github.com/xabierpc/SIKORIUS, rama `main`, commit `575fe30` |
| Sistema | Linux, sin el proyecto instalado antes |
| uv | 0.11.32 |
| Criterio | Seguir solo el `README.md`, sin preguntar al equipo |

## Resultado

**Correcto.** La aplicación se instaló y funcionó a la primera, sin ayuda y sin preguntar.

| Paso | Resultado |
|---|---|
| `git clone https://github.com/xabierpc/SIKORIUS.git` | Correcto |
| `uv sync` | Correcto: instala las versiones exactas de `uv.lock` |
| `uv run sikorius` | Correcto: la aplicación responde en `http://localhost:8080` |
| Flujo completo con CSV, Excel y SQLite | Correcto: carga, columnas, separación, preprocesado, modelo, fórmula, R² y ECM, y gráfico |
| `uv run pytest -q` | Correcto: todos los tests pasan (1 fallo conocido marcado como `xfail`) |
| `uv run ruff format --check src tests` y `uv run ruff check src tests` | Correcto: sin errores |

## Mejoras de la documentación

La persona completó todos los pasos sin problemas. Aun así, propuso mejoras del README, que se han aplicado:

| Propuesta | Cambio en el `README.md` |
|---|---|
| No decía dónde se abre la aplicación ni cómo se cierra | Se indica la dirección `http://localhost:8080`, que se cierra con `Ctrl+C` y qué hacer si el puerto 8080 está ocupado |
| No había datos con los que probarla | Se describe el formato de los archivos y se incluye un CSV de ejemplo para copiar (no se sube ningún dataset al repositorio) |
| La carpeta `data/` no existe al clonar | Se indica que hay que crearla y que el explorador se abre en la carpeta personal |
| Decía que solo se ofrecen columnas numéricas, pero los selectores muestran todas | Se explica que la aplicación avisa al confirmar si se elige una columna no numérica |
| La insignia de los tests apuntaba a `dev` | Ahora apunta a `main` |
| No indicaba con qué versión de uv se ha probado | Se indica que está probado en Linux con uv 0.11 y 0.13 |

## No comprobado

- Windows y macOS.
- La descarga del ZIP desde la página *Releases*.