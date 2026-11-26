"""Tests de las demás piezas del probador: datos, herramientas, cliente e
informe. No necesitan red, clave, Playwright ni la aplicación en marcha."""

import json
import os
import sqlite3
from types import SimpleNamespace

import pandas as pd
import pytest

from probador_llm import datos, ejecutor, herramientas, informe
from probador_llm.agente import CORRECTO, FALLIDO, REVISAR, Resultado
from probador_llm.cliente_groq import (
    VARIABLE_CLAVE,
    ErrorClave,
    convertir_respuesta,
    es_limite_diario,
    leer_clave,
    segundos_de_espera,
)
from probador_llm.navegador import ErrorAccion, compactar
from probador_llm.plan import leer_plan

# --- Datos de prueba ---


def test_preparar_crea_los_archivos(tmp_path):
    carpeta = datos.preparar(tmp_path)
    assert carpeta == tmp_path / "pruebas"
    for nombre in datos.ARCHIVOS_TEXTO:
        assert (carpeta / nombre).is_file(), nombre
    assert (carpeta / "vacio.csv").stat().st_size == 0


def test_lineal_cumple_la_formula(tmp_path):
    tabla = pd.read_csv(datos.preparar(tmp_path) / "lineal.csv")
    assert len(tabla) == 12
    esperado = 2 * tabla["x1"] - 3 * tabla["x2"] + 5
    assert (tabla["y"] == esperado).all()


def test_cinco_filas(tmp_path):
    tabla = pd.read_csv(datos.preparar(tmp_path) / "cinco_filas.csv")
    assert len(tabla) == 5


def test_nulos_total_tiene_x_vacia(tmp_path):
    tabla = pd.read_csv(datos.preparar(tmp_path) / "nulos_total.csv")
    assert len(tabla) == 10
    assert tabla["x"].isna().all()


@pytest.mark.parametrize(
    ("nombre", "tablas"), [("dos_tablas.db", 2), ("sin_tablas.db", 0)]
)
def test_bases_de_datos(tmp_path, nombre, tablas):
    carpeta = datos.preparar(tmp_path)
    conexion = sqlite3.connect(carpeta / nombre)
    try:
        filas = conexion.execute(
            "select name from sqlite_master where type = 'table'"
        ).fetchall()
    finally:
        conexion.close()
    assert len(filas) == tablas


def test_preparar_borra_los_modelos_de_ejecuciones_anteriores(tmp_path):
    carpeta = datos.preparar(tmp_path)
    (carpeta / "modelo_lineal.json").write_text("{}")
    datos.preparar(tmp_path)
    assert not (carpeta / "modelo_lineal.json").exists()


def test_carpeta_especial_con_copia_del_dataset(tmp_path):
    origen = tmp_path / "ejemplo.csv"
    origen.write_text("a,b\n1,2\n")
    carpeta = datos.preparar(tmp_path / "data", origen)
    copia = carpeta / datos.CARPETA_ESPECIAL / "ejemplo.csv"
    assert copia.read_text() == "a,b\n1,2\n"


@pytest.mark.skipif(os.name == "nt", reason="Permisos de Unix")
def test_carpeta_solo_lectura(tmp_path):
    carpeta = datos.preparar(tmp_path)
    modo = (carpeta / datos.CARPETA_SOLO_LECTURA).stat().st_mode
    assert not modo & 0o222
    # Se puede volver a preparar aunque la carpeta no tenga escritura
    datos.preparar(tmp_path)


# --- Herramientas ---


class NavegadorAnotador:
    def __init__(self):
        self.llamadas = []

    def pulsar(self, texto):
        self.llamadas.append(("pulsar", texto))
        return "ok"

    def escribir(self, campo, valor):
        self.llamadas.append(("escribir", campo, valor))
        return "ok"

    def elegir(self, selector, opciones):
        self.llamadas.append(("elegir", selector, opciones))
        return "ok"

    def tecla(self, nombre):
        raise ErrorAccion("Tecla no permitida")

    def esperar(self, segundos):
        self.llamadas.append(("esperar", segundos))
        return "ok"


def test_herramientas_se_despachan():
    navegador = NavegadorAnotador()
    reinicios = []
    ejecutar = herramientas.ejecutar
    ejecutar(navegador, None, "pulsar", {"texto": "Crear modelo"})
    ejecutar(navegador, None, "escribir", {"campo": "Semilla", "valor": 7})
    ejecutar(navegador, None, "elegir", {"selector": "T", "opciones": "y"})
    ejecutar(navegador, None, "esperar", {"segundos": 2})
    texto = ejecutar(
        navegador,
        lambda: reinicios.append(1),
        "reiniciar_aplicacion",
        {},
    )
    assert navegador.llamadas == [
        ("pulsar", "Crear modelo"),
        ("escribir", "Semilla", "7"),
        ("elegir", "T", ["y"]),
        ("esperar", 2),
    ]
    assert reinicios == [1]
    assert "abierta de nuevo" in texto


@pytest.mark.parametrize(
    ("nombre", "argumentos", "esperado"),
    [
        ("tecla", {"nombre": "F5"}, "ERROR: Tecla no permitida"),
        ("pulsar", {}, "ERROR: argumentos no válidos"),
        ("pulsar", {"texto": 3}, "ERROR: argumentos no válidos"),
        ("elegir", {"selector": "T", "opciones": []}, "ERROR: indica"),
        ("borrar", {}, "ERROR: no existe la herramienta"),
    ],
)
def test_errores_de_herramientas(nombre, argumentos, esperado):
    texto = herramientas.ejecutar(
        NavegadorAnotador(), None, nombre, argumentos
    )
    assert texto.startswith(esperado)


def test_definiciones_de_herramientas():
    nombres = []
    for definicion in herramientas.HERRAMIENTAS:
        assert definicion["type"] == "function"
        nombres.append(definicion["function"]["name"])
    assert "terminar" in nombres
    assert len(nombres) == len(set(nombres))


# --- Cliente de Groq ---


def respuesta_sdk(argumentos, contenido=None):
    funcion = SimpleNamespace(name="pulsar", arguments=argumentos)
    llamada = SimpleNamespace(id="c1", function=funcion)
    mensaje = SimpleNamespace(content=contenido, tool_calls=[llamada])
    return SimpleNamespace(
        choices=[SimpleNamespace(message=mensaje)],
        usage=SimpleNamespace(total_tokens=123),
    )


def test_convertir_respuesta():
    respuesta = convertir_respuesta(respuesta_sdk('{"texto": "Crear"}'))
    assert respuesta.tokens == 123
    assert respuesta.llamadas[0].nombre == "pulsar"
    assert respuesta.llamadas[0].argumentos == {"texto": "Crear"}
    assert respuesta.llamadas[0].error is None
    llamada = respuesta.mensaje["tool_calls"][0]
    assert llamada["id"] == "c1"
    assert llamada["function"]["arguments"] == '{"texto": "Crear"}'
    assert respuesta.mensaje["content"] == ""


@pytest.mark.parametrize("argumentos", ["{roto", "[1, 2]"])
def test_convertir_respuesta_con_argumentos_no_validos(argumentos):
    llamada = convertir_respuesta(respuesta_sdk(argumentos)).llamadas[0]
    assert llamada.argumentos == {}
    assert llamada.error


def test_tokens_de_cache_no_cuentan():
    respuesta = respuesta_sdk('{"texto": "Crear"}')
    respuesta.usage.prompt_tokens_details = SimpleNamespace(cached_tokens=100)
    convertida = convertir_respuesta(respuesta)
    assert convertida.tokens == 23
    assert convertida.tokens_cache == 100


@pytest.mark.parametrize(
    ("mensaje", "segundos"),
    [
        ("Please try again in 7.5s. Need more tokens?", 7.5),
        ("Please try again in 1m2.5s.", 62.5),
        ("sin indicación", None),
    ],
)
def test_segundos_de_espera(mensaje, segundos):
    assert segundos_de_espera(mensaje) == segundos


def test_limite_diario():
    assert es_limite_diario("on tokens per day (TPD): Limit 200000")
    assert es_limite_diario("on requests per day (RPD): Limit 1000")
    assert not es_limite_diario("on tokens per minute (TPM): Limit 8000")


# --- Pantalla compacta ---

ARBOL = """- banner:
  - img "SIKORIUS"
  - tab "Datos"
- main:
  - table:
    - rowgroup:
      - row "a b":
        - columnheader "a"
        - columnheader "b"
    - rowgroup:
      - row "1 2":
        - cell "1"
        - cell "2"
      - row "3 4":
        - cell "3"
        - cell "4"
      - row "5 6":
        - cell "5"
        - cell "6"
      - row "7 8":
        - cell "7"
        - cell "8"
      - row "9 10":
        - cell "9"
        - cell "10"
  - button "Cargar otro"
- alert:
  - text: Dataset cargado"""


def test_compactar_quita_imagenes_y_mensajes():
    texto = compactar(ARBOL)
    assert "img" not in texto
    assert "alert" not in texto
    assert 'tab "Datos"' in texto
    assert 'button "Cargar otro"' in texto


def test_compactar_recorta_las_tablas():
    texto = compactar(ARBOL)
    assert 'row "a b"' in texto
    assert 'row "5 6"' in texto
    assert 'row "7 8"' not in texto
    assert "2 filas más" in texto
    # Las celdas sobran: el nombre de la fila ya las incluye
    assert "cell" not in texto


def test_respuesta_sin_herramientas():
    mensaje = SimpleNamespace(content="Hola", tool_calls=None)
    respuesta = convertir_respuesta(
        SimpleNamespace(choices=[SimpleNamespace(message=mensaje)])
    )
    assert respuesta.llamadas == []
    assert "tool_calls" not in respuesta.mensaje


def test_leer_clave_del_entorno(tmp_path, monkeypatch):
    monkeypatch.setenv(VARIABLE_CLAVE, "clave-entorno")
    assert leer_clave(tmp_path) == "clave-entorno"


def test_leer_clave_del_env(tmp_path, monkeypatch):
    monkeypatch.delenv(VARIABLE_CLAVE, raising=False)
    (tmp_path / ".env").write_text(
        "OTRA=1\n" + VARIABLE_CLAVE + ' = "clave-archivo"\n'
    )
    assert leer_clave(tmp_path) == "clave-archivo"


def test_sin_clave(tmp_path, monkeypatch):
    monkeypatch.delenv(VARIABLE_CLAVE, raising=False)
    with pytest.raises(ErrorClave):
        leer_clave(tmp_path)


# --- Ejecutor e informe ---


def resultado(caso, estado):
    return Resultado(
        caso=caso,
        titulo="Título " + caso,
        estado=estado,
        resultado_obtenido="Se ve | la fórmula",
        evidencias=["y = 7.0000", "inventada"],
        evidencias_no_encontradas=["inventada"],
    )


def test_combinar_repeticiones_iguales():
    combinado = ejecutor.combinar(
        [resultado("CP-01", CORRECTO), resultado("CP-01", CORRECTO)]
    )
    assert combinado.estado == CORRECTO


def test_combinar_repeticiones_distintas():
    combinado = ejecutor.combinar(
        [resultado("CP-01", CORRECTO), resultado("CP-01", FALLIDO)]
    )
    assert combinado.estado == REVISAR
    assert "Correcto, Fallido" in combinado.resultado_obtenido


def test_dataset_d1_sin_rellenar():
    texto = "| D-1 (CSV) | `data/⟨dataset⟩.csv` |"
    assert ejecutor.dataset_d1(texto) is None


def test_datasets_del_plan():
    texto = (
        "| D-1 (CSV) | `data/a.csv` |\n| D-3 (SQLite) | `data/a.db`, tabla |"
    )
    rutas = ejecutor.datasets(texto)
    assert rutas["D-1"] == ejecutor.RAIZ / "data" / "a.csv"
    assert rutas["D-3"] == ejecutor.RAIZ / "data" / "a.db"


def test_datasets_que_faltan(tmp_path):
    plan = leer_plan(
        "#### CP-01. Uno\n- **Pasos:** PR-2 con D-1 y copia F-11.\n\n"
        "#### CP-02. Dos\n- **Pasos:** como CP-01.\n\n"
        "#### CP-03. Tres\n- **Pasos:** usa lineal.csv.\n"
    )
    existe = tmp_path / "a.csv"
    existe.write_text("x\n1\n")
    no_existe = ejecutor.RAIZ / "data" / "no_existe_nunca.csv"
    assert (
        ejecutor.datasets_que_faltan(
            plan, plan.casos["CP-01"], {"D-1": existe}
        )
        == []
    )
    faltan = ejecutor.datasets_que_faltan(
        plan, plan.casos["CP-02"], {"D-1": no_existe}
    )
    assert faltan == ["data/no_existe_nunca.csv"]
    assert (
        ejecutor.datasets_que_faltan(
            plan, plan.casos["CP-03"], {"D-1": no_existe}
        )
        == []
    )


PLAN_INICIO = """
#### CP-01. Recién abierta
- **Precondiciones:** aplicación recién abierta (PR-1).

#### CP-02. Continúa
- **Precondiciones:** D-1 cargado.

#### CP-03. Hijo de CP-02
- **Precondiciones:** CP-02 ejecutado, sin cerrar la aplicación.
"""


@pytest.mark.parametrize(
    ("caso", "ultimo", "en_marcha", "independiente", "esperado"),
    [
        # Primer caso: siempre se arranca
        ("CP-02", None, False, False, (False, [])),
        # Caso normal tras otro que fue bien: continúa
        ("CP-02", ("CP-01", CORRECTO), True, False, (True, [])),
        ("CP-02", ("CP-01", FALLIDO), True, False, (True, [])),
        # El anterior dejó la aplicación en un estado desconocido
        ("CP-02", ("CP-01", "Bloqueado"), True, False, (False, [])),
        ("CP-02", ("CP-01", "Error"), True, False, (False, [])),
        # La aplicación se ha cerrado
        ("CP-02", ("CP-01", CORRECTO), False, False, (False, [])),
        # Pide la aplicación recién abierta
        ("CP-01", ("CP-02", CORRECTO), True, False, (False, [])),
        # Ejecución independiente (repeticiones)
        ("CP-02", ("CP-01", CORRECTO), True, True, (False, [])),
        # Hijo justo después de su padre: continúa sin preparación
        ("CP-03", ("CP-02", CORRECTO), True, False, (True, [])),
        # Hijo sin su padre justo antes: se reinicia y se repite el padre
        ("CP-03", ("CP-01", CORRECTO), True, False, (False, ["CP-02"])),
        ("CP-03", ("CP-02", "Bloqueado"), True, False, (False, ["CP-02"])),
    ],
)
def test_decidir_inicio(caso, ultimo, en_marcha, independiente, esperado):
    plan = leer_plan(PLAN_INICIO)
    continuar, preparacion = ejecutor.decidir_inicio(
        plan, plan.casos[caso], ultimo, en_marcha, independiente
    )
    nombres = []
    for previo in preparacion:
        nombres.append(previo.id)
    assert (continuar, nombres) == esperado


class TargetClosedError(Exception):
    """Imita el error de Playwright cuando se cierra el navegador."""


@pytest.mark.parametrize(
    ("error", "cerrado"),
    [
        (TargetClosedError("Target page has been closed"), True),
        (RuntimeError("Browser has been closed"), True),
        (RuntimeError("Timeout 30000ms exceeded"), False),
    ],
)
def test_navegador_cerrado(error, cerrado):
    assert ejecutor._navegador_cerrado(error) == cerrado


def test_casos_manuales_existen_en_el_plan():
    for identificador in ejecutor.MANUALES:
        assert identificador.startswith("CP-")


def test_informe(tmp_path):
    resultados = [
        resultado("CP-01", CORRECTO),
        resultado("CP-02", informe.MANUAL),
    ]
    datos_ejecucion = {
        "modelo": "modelo-falso",
        "fecha": "2026-11-25 10:00",
        "commit": "abc1234",
        "plan": "docs/plan_pruebas.md",
    }
    ruta = informe.escribir(tmp_path, resultados, datos_ejecucion)
    texto = ruta.read_text(encoding="utf-8")
    assert "| Ejecutados por el LLM | 1 |" in texto
    assert "| Correcto | 1 |" in texto
    assert "| Manual | 1 |" in texto
    # Las barras del texto no rompen la tabla
    assert "Se ve \\| la fórmula" in texto
    assert "`inventada` ✘" in texto
    guardado = json.loads((tmp_path / "resultados.json").read_text())
    assert guardado["resumen"]["Correcto"] == 1
    assert guardado["casos"][0]["caso"] == "CP-01"
