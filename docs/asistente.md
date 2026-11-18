# Asistente con LLM (Groq)

## Qué hace

- **Explica** el dataset (columnas, tipos, nulos, rangos) y el modelo
  (fórmula, coeficientes, R² y ECM) en lenguaje natural.
- **Propone cambios** al dataset cuando se le pide ("quita las filas con
  precio mayor que 500000", "elimina la columna id"). Nunca los aplica solo:
  se muestran en una tarjeta con lo que va a pasar ("se eliminan 37 filas")
  y el usuario elige *Aplicar* o *Descartar*. El botón ↶ deshace el último
  cambio aplicado.

Aplicar un cambio sustituye el dataset, así que, igual que al cargar otro
archivo, se borran la selección de columnas, la separación, el preprocesado
y el modelo. Si el modelo no está guardado, se pide confirmación.

## Cómo funciona

```
gui/paneles/panel_asistente.py   chat, propuesta, aplicar/deshacer
        │
aplicacion/asistente.py          conversación, prueba los cambios sobre
        │                        una copia, confirmar/deshacer
datos/cliente_groq.py            llamada a la API de Groq
        │
dominio/asistente.py             forma de la respuesta, instrucciones,
dominio/transformaciones.py      resumen del trabajo y catálogo de cambios
```

1. La aplicación manda a Groq las instrucciones, un **resumen** del trabajo
   (nombres y tipos de columnas, nulos, mínimo/máximo/media, selección y
   modelo) y los últimos mensajes. No se mandan las filas.
2. Groq contesta con **salida estructurada estricta**: un JSON que sigue
   siempre el esquema de `RespuestaAsistente` (un `mensaje` y una lista de
   `operaciones`). Se valida con Pydantic.
3. Las operaciones son de un **catálogo cerrado**
   (`dominio/transformaciones.py`): la LLM no escribe código ni toca los
   datos. Se prueban sobre una copia; si alguna falla, se avisa y no se
   cambia nada.

`aplicacion/asistente.py` solo conoce el protocolo `ClienteLLM` (un método
`responder`). Para usar otro proveedor basta con escribir otra clase con ese
método.

## Configuración

| Variable | Para qué |
|---|---|
| `GROQ_API_KEY` | Clave de Groq (obligatoria para activar el asistente) |
| `SIKORIUS_MODELO_GROQ` | Otro modelo (por defecto `openai/gpt-oss-20b`) |

Se leen del entorno o del archivo `.env` (ver `.env.example`). El modelo
elegido tiene que admitir salida estructurada estricta.

## Añadir una operación

1. Añade el nombre al `Literal` de `Operacion.tipo` y a `TIPOS`.
2. Escribe `_nueva(df, op)` que devuelva `(datos_nuevos, descripcion)` y
   regístrala en `_APLICAR`.
3. Explícasela a la LLM en `INSTRUCCIONES` (`dominio/asistente.py`).
4. Tests en `tests/dominio/test_transformaciones.py`.

## Tests

Ningún test usa la red: `tests/aplicacion/test_asistente.py` y
`tests/gui/test_panel_asistente.py` usan una LLM falsa, y
`tests/datos/test_cliente_groq.py` sustituye el SDK de Groq por uno falso.
