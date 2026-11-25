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

Para cada caso, el probador:

1. **Prepara los datos.** Crea los archivos de prueba F-1 a F-13 de la sección 2.2 del plan en `data/pruebas/` (`datos.py`). Siempre son los mismos, así que todas las ejecuciones parten de los mismos datos.
2. **Abre la aplicación recién arrancada** (procedimiento PR-1). Arranca `sikorius` en un puerto libre, sin abrir el navegador del usuario (`aplicacion.py` y `lanzador.py`). La aplicación conserva la sesión aunque se recargue la página, así que se reinicia antes de cada caso.
3. **Deja trabajar al agente.** En cada turno, el LLM recibe la pantalla y responde con una acción.
   - **Lo que ve:** el árbol de accesibilidad de la página, con botones (y si están deshabilitados), campos con su valor, desplegables, listas y diálogos. Recibe también los mensajes de la aplicación (éxito, aviso o error) y una descripción de los gráficos: ejes, leyenda y cada serie con su número de puntos. Los gráficos de ECharts se dibujan en un canvas que el árbol no ve, así que su configuración se lee a través de NiceGUI.
   - **Lo que puede hacer:** solo un catálogo cerrado de acciones: `pulsar`, `escribir`, `elegir`, `tecla`, `esperar`, `reiniciar_aplicacion` y, al final, `terminar` con su veredicto. No puede ejecutar código ni tocar archivos.
4. **Comprueba el veredicto.** El LLM tiene que citar como evidencias textos copiados literalmente de la pantalla. El código comprueba que cada uno aparece de verdad en lo que se ha visto durante el caso. Si alguno no aparece, el caso no se da por bueno y queda como **Revisar**.
5. **Guarda las pruebas de lo ocurrido.** Hace una captura de pantalla después de cada acción y reescribe el registro al terminar cada caso.

### Casos que continúan a otro

Si un caso empieza "con CP-55 ejecutado, sin cerrar la aplicación", el agente repite primero los pasos de CP-55 (y los de los casos de los que dependa este) como **preparación**, sin evaluarlos. Así cada caso se puede ejecutar por separado y empieza siempre con la aplicación recién abierta.

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
| `--repeticiones N` | Ejecuta cada caso N veces. Si los resultados no coinciden, el caso queda como "Revisar". |
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

## 4. Casos que no ejecuta el LLM

| Caso | Motivo |
|---|---|
| CP-44 | Hay que abrir el CSV con una hoja de cálculo. |
| CP-85, CP-86 | Que la ventana no se bloquee y se desplace con fluidez lo juzga una persona. |
| CP-88 | Hay que redimensionar la ventana del sistema operativo. |
| CP-89 a CP-92 | El asistente con LLM no está en `dev`. CP-92 además pide renombrar `.env`. |

CP-87 (pantalla de 1366 × 768) sí lo ejecuta el LLM: el navegador de las pruebas se abre siempre con ese tamaño.

Los casos que usan el dataset de ejemplo quedan como "No ejecutado" hasta que se rellenen sus valores en la sección 2.1 del plan. Los que usan los archivos creados para las pruebas (por ejemplo, `lineal.csv`) se pueden ejecutar desde ya.

---

## 5. Limitaciones y cómo se controlan

| Riesgo | Control |
|---|---|
| El LLM dice "correcto" sin haberlo comprobado | Tiene que citar evidencias literales, y el código comprueba que existen. Si no, el caso queda como "Revisar". |
| El LLM no responde siempre igual | Temperatura 0, opción `--repeticiones` y revisión humana de los casos fallidos, bloqueados y para revisar. |
| El LLM improvisa pasos | Las instrucciones le prohíben hacer lo que el caso no pide. Las acciones son un catálogo cerrado y todas quedan en el registro. |
| Un paso ambiguo | El agente termina como "Bloqueado" en ese paso, que es lo que la historia #29 pide detectar: el caso se reescribe. |
| Gasto de tokens | Solo se mandan completas las dos últimas pantallas, y el registro anota los tokens de cada caso. Con la capa gratuita de Groq puede hacer falta ejecutar el plan por bloques (`--casos`). |
| Límites de uso de Groq | El cliente espera y reintenta, cada vez el doble de tiempo. |

El LLM sustituye a la persona que **ejecuta** los pasos, no a la que revisa los resultados. Una persona del equipo revisa todos los casos fallidos, bloqueados y para revisar, y una muestra de los correctos (con las capturas).

---

## 6. Pruebas del probador

El probador tiene sus propios tests en `tests/herramientas/`, que se ejecutan con el resto (`uv run pytest`) y en GitHub Actions. Usan un LLM y un navegador falsos, así que no necesitan red, clave, Playwright ni la aplicación en marcha. Comprueban, entre otras cosas, que una evidencia inventada deja el caso en "Revisar", que el agente recibe los errores de sus acciones y que el plan real se lee entero.
