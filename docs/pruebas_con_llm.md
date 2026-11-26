# Pruebas funcionales con un LLM

Historia de usuario: **#29 Creación y ejecución de un plan de pruebas funcionales antes de la release**

Los casos del [plan de pruebas](plan_pruebas.md) los ejecuta un **agente con un LLM**: un modelo de lenguaje que maneja SIKORIUS en el navegador, igual que lo haría una persona ajena al proyecto. Sigue solo los pasos escritos de cada caso, compara lo que ve con el resultado esperado y rellena el registro de ejecución.

El código está en [`herramientas/probador_llm/`](../herramientas/probador_llm/), fuera del paquete de la aplicación (`src/`).

---

## 1. Cómo funciona

```
docs/plan_pruebas.md ──► plan.py ──► un caso, con el glosario sustituido
                                          │
                     ┌────────────────────┘
                     ▼
   ┌──────────── agente.py ─────────────┐
   │  1. Ve la pantalla (texto)         │◄──── navegador.py (Playwright)
   │  2. El LLM elige una acción        │────► pulsar / escribir / elegir...
   │  3. Repite hasta "terminar"        │
   │  4. Se comprueban sus evidencias   │
   └────────────────────────────────────┘
                     │
                     ▼
     informe.py ──► data/pruebas_llm/<fecha>/registro.md + capturas
```

Los casos del plan son **aditivos**, como las historias: cada uno parte de lo que dejó el anterior. El probador:

1. **Prepara los datos.** Crea los archivos de prueba F-1 a F-14 de la sección 2.2 del plan en `data/pruebas/` (`datos.py`). Siempre son los mismos, así que todas las ejecuciones parten de los mismos datos.
2. **Abre la aplicación una vez** y la mantiene abierta entre casos (`aplicacion.py` y `lanzador.py`). La arranca en un puerto libre, sin abrir el navegador del usuario, y con `data/` como carpeta personal, para que el explorador de archivos empiece ahí.
3. **Sube el dataset al principio.** El primer caso (CP-01) es el LLM subiendo D-1. Los casos con la precondición «D-1 cargado» lo reutilizan sin volver a cargarlo.
4. **Ordena los casos encadenados.** Un caso que continúa a otro («CP-47 ejecutado, sin cerrar la aplicación») se ejecuta justo después de él. Por ejemplo: CP-47 (crear el modelo) → CP-76 a CP-79 (predicciones) → CP-55 (descripción) → CP-58 (guardar)...
5. **Solo reinicia la aplicación cuando hace falta:** si el caso pide la aplicación recién abierta (por ejemplo, para comprobar que un botón está deshabilitado antes de cargar nada) o si el caso anterior acabó bloqueado o con error, porque la aplicación ha quedado en un estado desconocido. En todo el plan son 12 reinicios.
6. **Deja trabajar al agente.** En cada turno, el LLM recibe la pantalla y responde con una acción.
   - **Lo que ve:** el árbol de accesibilidad de la página, con botones (y si están deshabilitados), campos con su valor, desplegables, listas y diálogos. Recibe también los mensajes de la aplicación (éxito, aviso o error) y una descripción de los gráficos: ejes, leyenda y cada serie con su número de puntos. Los gráficos de ECharts se dibujan en un canvas que el árbol no ve, así que su configuración se lee a través de NiceGUI.
   - **Lo que puede hacer:** solo un catálogo cerrado de acciones: `pulsar`, `escribir`, `elegir`, `tecla`, `esperar`, `reiniciar_aplicacion` y, al final, `terminar` con su veredicto. No puede ejecutar código ni tocar archivos.
7. **Comprueba el veredicto.** El LLM tiene que citar como evidencias textos copiados literalmente de la pantalla. El código comprueba que cada uno aparece de verdad en lo que se ha visto durante el caso. Si alguno no aparece, el caso no se da por bueno y queda como **Revisar**.
8. **Limpia la pantalla entre casos.** Cierra los diálogos y los mensajes que queden abiertos, sin tocar los datos.
9. **Guarda las pruebas de lo ocurrido.** Hace una captura de pantalla después de cada acción y reescribe el registro al terminar cada caso.

### Si un caso encadenado no puede continuar

Si el caso al que continúa no se ha ejecutado justo antes (porque no estaba entre los elegidos con `--casos`) o terminó bloqueado o con error, se reinicia la aplicación y el agente repite antes los pasos de ese caso como **preparación**, sin evaluarlos.

Si un caso cita otro («como CP-35», «los pasos 1 a 3 de CP-35»), el agente recibe también el texto del caso citado, como referencia.

### Estados de un caso

| Estado | Significado |
|---|---|
| Correcto | Todo coincide con el resultado esperado y las evidencias existen. |
| Fallido | Algo no coincide. El registro dice qué esperaba y qué vio. Se crea una tarea de corrección en Taiga. |
| Bloqueado | El agente no pudo seguir algún paso (o se le acabaron los turnos). Probablemente hay que reescribir el caso, como pide la historia #29. |
| Revisar | El veredicto no está respaldado por lo que se vio, o varias repeticiones dieron resultados distintos. Lo confirma una persona. |
| Error | Falló el propio probador (por ejemplo, la aplicación no arrancó). |
| Manual | Caso que no tiene sentido hacer con el LLM (ver sección 4). |
| No ejecutado | Al caso le faltan valores del plan por rellenar (`⟨...⟩`). |

---

## 2. Instalación

Las dependencias del probador están en un grupo aparte (`probador`), así que no se instalan con la aplicación ni en GitHub Actions:

```bash
uv sync --group probador
uv run --group probador playwright install chromium
```

Si ya tienes Google Chrome instalado, puedes saltarte el segundo comando y usar la opción `--chrome`.

La clave de Groq se lee de la variable de entorno `GROQ_API_KEY` o del archivo `.env` de la raíz del proyecto, que no se sube al repositorio:

```
GROQ_API_KEY=tu_clave
```

---

## 3. Uso

Desde la raíz del repositorio:

```bash
# Todo el plan
uv run --group probador python herramientas/probar_con_llm.py

# Algunos casos
uv run --group probador python herramientas/probar_con_llm.py --casos CP-47,CP-76
uv run --group probador python herramientas/probar_con_llm.py --casos CP-22:CP-34

# Viendo el navegador mientras trabaja
uv run --group probador python herramientas/probar_con_llm.py --casos CP-47 --ver
```

| Opción | Para qué sirve |
|---|---|
| `--casos` | Casos a ejecutar. Por defecto, todos. |
| `--modelo` | Modelo de Groq. Por defecto, `openai/gpt-oss-120b`. |
| `--razonamiento` | Esfuerzo de razonamiento de los modelos gpt-oss: `low` (por defecto), `medium` o `high`. Más alto gasta más tokens. |
| `--repeticiones N` | Ejecuta cada caso N veces. Si los resultados no coinciden, el caso queda como "Revisar". Con más de una, cada caso se ejecuta por separado, reiniciando la aplicación (más lento). |
| `--max-turnos` | Acciones máximas por caso (por defecto, 40). |
| `--chrome` | Usa el Google Chrome instalado en vez del Chromium de Playwright. |
| `--ver` | Muestra la ventana del navegador. |
| `--permitir-huecos` | Ejecuta también casos con valores del plan sin rellenar. |
| `--salida` | Carpeta de resultados. Por defecto, `data/pruebas_llm/<fecha>/`. |

### Resultados

En `data/pruebas_llm/<fecha>/` (dentro de `data/`, así que no se suben al repositorio):

- `registro.md`: resumen, la tabla del registro de ejecución y el detalle de cada caso, con sus acciones, los mensajes de la aplicación y las evidencias marcadas con ✔ o ✘.
- `resultados.json`: lo mismo en JSON.
- `capturas/CP-xx/`: una captura después de cada acción.
- `aplicacion.log`: lo que ha escrito la aplicación.

El registro se puede copiar al informe de pruebas de `docs/`.

---

## 4. Script de Playwright generado por el LLM

Al terminar, el probador convierte lo que hizo el LLM en un **script de Playwright** normal: `herramientas/generados/test_plan_llm.py`. Cada caso es un test de pytest con:

- las acciones del LLM, en el mismo orden (`sikorius.pulsar("Crear modelo")`, `sikorius.elegir(...)`...), sin las que dieron error;
- una comprobación por cada evidencia que citó y que el probador verificó en pantalla (`sikorius.comprobar("y = 7.0000")`).

Ese script **se ejecuta sin LLM**: no necesita clave, no gasta tokens y tarda segundos. Sirve para repetir las pruebas funcionales tras cada cambio (pruebas de regresión):

```bash
uv run --group probador pytest herramientas/generados -v
```

Con `SIKORIUS_VER=1` delante se ve el navegador, y con `SIKORIUS_CHROME=1` se usa el Google Chrome instalado. Las capturas quedan en `data/pruebas_script/<fecha>/`.

- Solo se generan tests de los casos con veredicto (correcto, fallido o para revisar). Los fallidos se marcan con `xfail` (fallo esperado).
- Los tests van en orden y son aditivos, como los casos: hay que ejecutarlos todos juntos.
- Para generar el script desde una ejecución anterior, sin volver a llamar al LLM:

  ```bash
  uv run python herramientas/generar_script.py
  uv run python herramientas/generar_script.py data/pruebas_llm/<fecha>/resultados.json
  ```

  Sin argumentos, usa la última ejecución.
- El script no se edita a mano: se vuelve a generar. Está excluido de ruff en `pyproject.toml`.

## 5. Casos que no ejecuta el LLM

| Caso | Motivo |
|---|---|
| CP-44 | Hay que abrir el CSV con una hoja de cálculo. |
| CP-59 | Hay que abrir el modelo guardado (`.json`) con un editor de texto. |
| CP-84 | Compara los mensajes de otros casos: se revisa con el registro de la ejecución. |
| CP-85, CP-86 | Que la ventana no se bloquee y se desplace con fluidez lo juzga una persona. |
| CP-88 | Hay que redimensionar la ventana del sistema operativo. |
| CP-89 a CP-92 | El asistente con LLM no está en `dev`. CP-92 además pide renombrar `.env`. |

CP-87 (pantalla de 1366 × 768) sí lo ejecuta el LLM: el navegador de las pruebas se abre siempre con ese tamaño.

Los casos que usan los datasets de ejemplo (`housing1.csv`, `housing.xlsx` y `housing.db`) quedan como "No ejecutado" si esos archivos no están en `data/`: hay que copiarlos ahí antes de ejecutar. Los que usan los archivos creados para las pruebas (por ejemplo, `lineal.csv`) se ejecutan siempre.

---

## 6. Limitaciones y cómo se controlan

| Riesgo | Control |
|---|---|
| El LLM dice "correcto" sin haberlo comprobado | Tiene que citar evidencias literales, y el código comprueba que existen. Si no, el caso queda como "Revisar". |
| El LLM no responde siempre igual | Temperatura 0, opción `--repeticiones` y revisión humana de los casos fallidos, bloqueados y para revisar. |
| El LLM improvisa pasos | Las instrucciones le prohíben hacer lo que el caso no pide. Las acciones son un catálogo cerrado y todas quedan en el registro. |
| Un paso ambiguo | El agente termina como "Bloqueado" en ese paso, que es lo que la historia #29 pide detectar: el caso se reescribe. |
| Gasto de tokens | Ver la sección 7. |
| Un fallo arrastra a los siguientes | Si un caso acaba bloqueado o con error, el siguiente empieza con la aplicación reiniciada; los casos encadenados repiten antes los pasos que necesitan. |
| Límites de uso de Groq | Ver la sección 7. |

El LLM sustituye a la persona que **ejecuta** los pasos, no a la que revisa los resultados. Una persona del equipo revisa todos los casos fallidos, bloqueados y para revisar, y una muestra de los correctos (con las capturas).

---

## 7. Límites de Groq y gasto de tokens

El plan gratuito de Groq limita los tokens por minuto (8.000 con `gpt-oss-120b`) y por día (200.000). Para gastar lo menos posible:

- **Caché de Groq.** Las instrucciones, el glosario y los datos de prueba van en el mensaje de sistema, que es igual en todas las llamadas. La conversación de cada caso solo crece por el final y la pantalla actual va siempre en el último mensaje, sin guardarse. Así Groq reutiliza de su caché todo lo anterior, y esos tokens no cuentan para los límites.
- **Pantalla compacta.** Se quitan imágenes y mensajes, y de cada tabla solo se mandan la cabecera y tres filas.
- **Contexto compacto.** Del plan solo se manda lo que necesita el agente: procedimientos, glosario en forma de lista y datos de prueba.
- **Menos turnos.** El agente puede pedir varias acciones en un mismo turno, los casos no repiten lo que ya hizo el anterior y el explorador empieza en `data/`.
- **Razonamiento bajo** (`--razonamiento low`), que genera muchos menos tokens de salida.

Si Groq pide esperar por el límite por minuto, el probador espera lo que indica y avisa en la terminal. Si se agota el límite diario, para, guarda el registro y escribe el comando para seguir otro día con los casos que faltan.

El registro indica, por caso y en total, los tokens que cuentan para los límites y los reutilizados de la caché. Con el plan gratuito puede que el plan entero no quepa en un día; en ese caso se termina al día siguiente con el comando que escribe el probador.

## 8. Pruebas del probador

El probador tiene sus propios tests en `tests/herramientas/`, que se ejecutan con el resto (`uv run pytest`) y en GitHub Actions. Usan un LLM y un navegador falsos, así que no necesitan red, clave, Playwright ni la aplicación en marcha. Comprueban, entre otras cosas, que una evidencia inventada deja el caso en "Revisar", que el agente recibe los errores de sus acciones, que el plan real se lee entero y que el script generado reproduce las acciones y comprobaciones del LLM.
