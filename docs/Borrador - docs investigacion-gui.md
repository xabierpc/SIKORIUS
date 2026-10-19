# Investigación de librerías de interfaz gráfica (US 12)

> **Borrador** para `docs/investigacion-gui.md` del repositorio. Las partes marcadas con **[COMPLETAR]** dependen de la prueba de concepto de la tarea #100.
> Fuentes: webs y documentación oficiales de NiceGUI, Streamlit, y PyPI, consultadas el 16/10/2026 (enlaces al final).

## 1. Objetivo

Elegir la librería con la que se hará la interfaz gráfica de SIKORIUS. La aplicación tiene que permitir lo siguiente:

- cargar datos (CSV, Excel y SQLite) y verlos en una tabla;

- elegir columnas;

- crear un modelo de regresión lineal y ver su gráfico de Matplotlib;

- guardar el modelo, cargarlo y hacer predicciones.

El equipo ha decidido hacer una **interfaz web escrita solo en Python**. Por eso se comparan dos frameworks de ese tipo: **NiceGUI** y **Streamlit**.

## 2. Librerías investigadas

### NiceGUI

- **Qué es.**  

Framework de Python para crear interfaces que se ven en el navegador.

- **Cómo funciona.**
  - El servidor es Python: usa FastAPI, Starlette y Uvicorn.
  
  - La interfaz se dibuja con Vue y Quasar.

  - Ambas partes se comunican mediante una conexión abierta (WebSocket).
  
  - Cada elemento (botón, desplegable…) llama a una función de Python cuando el usuario interactúa con él, igual que en una aplicación de escritorio.
  
  - La aplicación entera se arranca con `ui.run()`.

- **Modo nativo.** Con `ui.run(native=True)`, la misma interfaz se abre en una **ventana propia del sistema** en lugar del
navegador. Para ello usa la librería pywebview.

- **Versión y licencia.** 3.18.0, licencia **MIT**, Python ≥ 3.10.

### Streamlit

- **Qué es.** Framework de Python de código abierto para crear aplicaciones de datos.

- **Cómo funciona.**
  - El programa es un script normal. Cada widget se declara como si fuera una variable.
  
  - Cada vez que el usuario toca un widget, Streamlit **vuelve a ejecutar el script entero de arriba abajo**.
  
  - Lo que haya que recordar entre ejecuciones se guarda en `st.session_state`.

  - Los cálculos costosos se pueden cachear con `@st.cache_data`.
- **Versión y licencia.** 1.66.0, licencia **Apache 2.0**, Python ≥ 3.11.

## 3. Tabla comparativa

| Criterio | NiceGUI | Streamlit |
| --- | --- | --- |
| **Windows / macOS / Linux** | Sí, en los tres (paquete independiente del sistema). En modo nativo, Windows necesita .NET Framework y Linux un WebKitGTK o Qt actualizado | Sí, en los tres: es un servidor web y la interfaz va en el navegador |
| **Licencia** | MIT (menos condiciones y orientada a proyectos pequeños) | Apache 2.0 (más orientada a proyectos empresariales) |
| **Documentación y comunidad** | Documentación con ejemplos ejecutables de cada elemento; Discord y Reddit. Más de 16.000 estrellas en GitHub | Documentación muy extensa (tutoriales, referencia de la API, chuleta), foro oficial, galería de aplicaciones y de componentes. |
| **Diálogo de selección de archivos** | En el navegador, `ui.upload`: entrega nombre y contenido, **no la ruta**; filtra tipos con `.props('accept=...')`. En modo nativo se puede abrir el diálogo del sistema a través de pywebview (`app.native.main_window`), que sí da la ruta | Solo `st.file_uploader`: filtra por extensión (`type=["csv", ...]`) y devuelve un objeto en memoria (`UploadedFile`) con `name`, `type` y `size`, **sin ruta en disco**. Límite por defecto de 200 MB por archivo |
| **Tabla con scroll** | `ui.table`, y `ui.aggrid` (AG Grid) con `ui.aggrid.from_pandas(df)` para crearla directamente desde un DataFrame | `st.dataframe(df)`: tabla interactiva a partir de un DataFrame |
| **Desplegable simple** | `ui.select(opciones)` | `st.selectbox` |
| **Selección múltiple** | `ui.select(opciones, multiple=True)` | `st.multiselect` |
| **Área de texto** | `ui.input`, `ui.textarea` | `st.text_input`, `st.text_area` |
| **Mensajes al usuario** | `ui.notify`, `ui.dialog` | `st.success`, `st.error`, `st.toast`, `st.dialog` |
| **Gráficos de Matplotlib** | `ui.matplotlib` y `ui.pyplot` | `st.pyplot(fig)` |
| **Guardar archivos** | En el navegador, `ui.download` (descarga). En modo nativo, diálogo de guardado del sistema vía pywebview | `st.download_button` (descarga; el navegador decide dónde se guarda) |
| **Tareas largas sin bloquear la interfaz** | `run.io_bound()` y `run.cpu_bound()` | El script espera a que termine; se puede mostrar `st.spinner` |
| **Pruebas automatizadas** | Simulador de pruebas con pytest que no necesita navegador | `AppTest` simula la aplicación en las pruebas |
| **Instalación con uv** | `uv add nicegui` | `uv add streamlit` |
| **Ejecución** | `uv run python <archivo>.py` (o el script del proyecto) | `uv run streamlit run <archivo>.py` |

## 4. Necesidades del proyecto que más pesan

1. **Rutas de archivo:**
   - La US 14 pide mostrar la ruta absoluta del archivo cargado.
   - Las US 21 y 24 piden un diálogo de guardado para elegir carpeta y nombre, y volver a proponer la misma ruta.
   - Un navegador no da rutas por seguridad. Por eso ninguna de las dos librerías lo cumple en modo navegador.
   - NiceGUI sí lo cumple en modo nativo. Streamlit no tiene un modo equivalente oficial.
2. **Flujo por pasos con estado:**
   - El orden es: cargar, elegir columnas, separar, preprocesar y crear el modelo.
   - Cada paso depende del anterior y se invalida si cambia uno anterior.
   - En **NiceGUI** cada botón llama a su función y el estado vive en variables normales.
   - En **Streamlit**, cada interacción reejecuta todo el script, y cada paso tiene que comprobar en `session_state` qué se hizo antes.
3. **Tablas grandes (US 14 y 37).** El dataset de ejemplo (housing) tiene 20.640 filas. Las dos librerías trabajan directamente con DataFrames de pandas.

 **[COMPLETAR comprobando en la prueba de concepto cómo responde cada tabla con el dataset completo.]**

**Riesgos de elegir NiceGUI:**

- A pesar de ser más efectivo a nivel de requisitos, el modo nativo depende de pywebview y del motor web del sistema: .NET en Windows y WebKitGTK o Qt en Linux.

- La comunidad es más pequeña que la de Streamlit.

**Dependencia añadida:** `uv add nicegui` (rama `feature/12-100-prueba-NiceGUI`). Si se usa el modo nativo, añadir también pywebview con `uv add pywebview`.

## 6. Prueba de concepto

Código en `prototipos/` (separado de `src/`, como pide la US). **[FALTA COMPLETAR con la prueba]** Debe incluir:

- [ ] Ventana con título.

- [ ] Botón que abre un diálogo de selección de archivos y muestra la ruta del archivo elegido.

- [ ] Tabla con scroll con datos de ejemplo (si el importador está disponible, las primeras filas de un archivo
cargado con él).

- [ ] Desplegable con varias opciones y cuadro de texto.

- [ ] Botón que muestra un mensaje con el valor introducido o seleccionado.

Cómo ejecutarla: 'uv run python src\sikorius\NiceGUI.py'

## 7. Dificultades encontradas y cómo se resolvieron

Con NiceGUI no se encontraron dificultades en las primeras pruebas puesto que hay mucha información proporcionada por
los desarrolladores de la interfaz en su página: https://nicegui.io/documentation .


## 8. Fuentes

- NiceGUI: [web](https://nicegui.io/) · [documentación](https://nicegui.io/documentation) · [modo nativo](https://nicegui.io/documentation/section_configuration_deployment) · [ui.aggrid](https://nicegui.io/documentation/aggrid) · [ui.upload](https://nicegui.io/documentation/upload) · [ui.select](https://nicegui.io/documentation/select) · [PyPI](https://pypi.org/project/nicegui/)
- Streamlit: [web](https://streamlit.io/) · [conceptos básicos](https://docs.streamlit.io/get-started/fundamentals/main-concepts) · [referencia de la API](https://docs.streamlit.io/develop/api-reference) · [st.file_uploader](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader) · [PyPI](https://pypi.org/project/streamlit/)
