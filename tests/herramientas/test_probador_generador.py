"""Tests del script de Playwright generado a partir del LLM.

No necesitan Playwright ni la aplicación: el código generado se ejecuta
con un reproductor falso que anota las llamadas.
"""

import json
from pathlib import Path

import pytest

from probador_llm.generador import generar, generar_desde_json
from probador_llm.reproduccion import Reproductor

DATOS = {"modelo": "modelo-falso", "fecha": "2026-11-25", "commit": "abc"}


def resultado(caso, estado, pasos=(), evidencias=(), reiniciado=True):
    return {
        "caso": caso,
        "titulo": "Título de " + caso,
        "estado": estado,
        "resultado_obtenido": 'Se ve "la fórmula"',
        "evidencias": list(evidencias),
        "evidencias_no_encontradas": [],
        "pasos": list(pasos),
        "reiniciado": reiniciado,
    }


def paso(herramienta, resultado_paso="ok", **argumentos):
    return {
        "herramienta": herramienta,
        "argumentos": argumentos,
        "resultado": resultado_paso,
    }


class ReproductorAnotador:
    def __init__(self):
        self.llamadas = []

    def __getattr__(self, nombre):
        def anotar(*argumentos):
            self.llamadas.append((nombre, *argumentos))

        return anotar


def ejecutar_generado(codigo):
    """Ejecuta los tests del código generado con un reproductor falso."""
    espacio = {}
    exec(compile(codigo, "test_plan_llm.py", "exec"), espacio)
    sikorius = ReproductorAnotador()
    nombres = []
    for nombre, valor in espacio.items():
        if nombre.startswith("test_") and callable(valor):
            nombres.append(nombre)
            valor(sikorius)
    return nombres, sikorius.llamadas


def test_genera_acciones_y_comprobaciones():
    codigo = generar(
        [
            resultado(
                "CP-47",
                "Correcto",
                pasos=[
                    paso("pulsar", texto="Subir dataset"),
                    paso("elegir", selector="Target", opciones=["y"]),
                    paso("escribir", campo="x1", valor=2.5),
                    paso("tecla", nombre="Escape"),
                    paso("esperar", segundos=2),
                    paso("reiniciar_aplicacion"),
                ],
                evidencias=["y = 7.0000"],
            )
        ],
        DATOS,
    )
    nombres, llamadas = ejecutar_generado(codigo)
    assert nombres == ["test_cp_47"]
    assert llamadas == [
        ("empezar", "CP-47", True),
        ("pulsar", "Subir dataset"),
        ("elegir", "Target", ["y"]),
        ("escribir", "x1", "2.5"),
        ("tecla", "Escape"),
        ("esperar", 2),
        ("reiniciar_aplicacion",),
        ("comprobar", "y = 7.0000"),
    ]


def test_continua_sin_reiniciar():
    codigo = generar([resultado("CP-76", "Correcto", reiniciado=False)], DATOS)
    _, llamadas = ejecutar_generado(codigo)
    assert llamadas[0] == ("empezar", "CP-76", False)


def test_omite_acciones_con_error_y_evidencias_no_verificadas():
    datos = resultado(
        "CP-01",
        "Revisar",
        pasos=[
            paso("pulsar", "ERROR: No hay ningún elemento", texto="Abrir"),
            paso("pulsar", texto="Datos"),
        ],
        evidencias=["real", "inventada"],
    )
    datos["evidencias_no_encontradas"] = ["inventada"]
    _, llamadas = ejecutar_generado(generar([datos], DATOS))
    assert ("pulsar", "Abrir") not in llamadas
    assert ("pulsar", "Datos") in llamadas
    assert ("comprobar", "real") in llamadas
    assert ("comprobar", "inventada") not in llamadas


def test_solo_casos_con_veredicto():
    codigo = generar(
        [
            resultado("CP-01", "Correcto"),
            resultado("CP-02", "Bloqueado"),
            resultado("CP-03", "Error"),
            resultado("CP-04", "Manual"),
            resultado("CP-05", "No ejecutado"),
            resultado("CP-06", "Fallido"),
        ],
        DATOS,
    )
    nombres, _ = ejecutar_generado(codigo)
    assert nombres == ["test_cp_01", "test_cp_06"]
    assert "CP-02 (Bloqueado)" in codigo
    # Un caso fallido se marca como fallo esperado
    assert "xfail" in codigo


def test_textos_con_comillas_y_tildes():
    codigo = generar(
        [
            resultado(
                "CP-13",
                "Correcto",
                pasos=[paso("pulsar", texto='carpeta "ñandú" á\\b')],
                evidencias=['textbox "x1": 2,5'],
            )
        ],
        DATOS,
    )
    _, llamadas = ejecutar_generado(codigo)
    assert ("pulsar", 'carpeta "ñandú" á\\b') in llamadas
    assert ("comprobar", 'textbox "x1": 2,5') in llamadas


def test_cabecera_con_modelo_y_commit():
    codigo = generar([resultado("CP-01", "Correcto")], DATOS)
    assert "Generado por: modelo-falso" in codigo
    assert "Commit de la aplicación: abc" in codigo


def test_sin_casos_genera_un_test_que_se_salta():
    codigo = generar([resultado("CP-01", "Bloqueado")], DATOS)
    nombres = []
    espacio = {}
    exec(compile(codigo, "test_plan_llm.py", "exec"), espacio)
    for nombre in espacio:
        if nombre.startswith("test_"):
            nombres.append(nombre)
    assert nombres == ["test_sin_casos"]


def test_generar_desde_json():
    contenido = dict(DATOS)
    contenido["casos"] = [resultado("CP-01", "Correcto")]
    codigo = generar_desde_json(json.dumps(contenido))
    assert "def test_cp_01(sikorius):" in codigo


# --- Reproductor ---


class AplicacionFalsa:
    url = "http://falsa"

    def __init__(self):
        self.reinicios = 0
        self.en_marcha = False

    def reiniciar(self):
        self.reinicios += 1
        self.en_marcha = True


class PaginaFalsa:
    def goto(self, url):
        pass

    def wait_for_load_state(self, estado):
        pass

    def wait_for_timeout(self, milisegundos):
        pass


class NavegadorFalso:
    def __init__(self, pagina, carpeta):
        self.mensajes = []
        self.textos_vistos = []
        self.limpiado = False

    def limpiar(self):
        self.limpiado = True

    def observar(self):
        self.textos_vistos.append("- text: y = 7.0000")

    def capturar(self, nombre):
        pass

    def pulsar(self, texto):
        if texto == "Abrir":
            from probador_llm.navegador import ErrorAccion

            raise ErrorAccion('No hay ningún elemento "Abrir"')
        self.mensajes.append("ÉXITO: hecho")


def reproductor():
    return Reproductor(
        AplicacionFalsa(), PaginaFalsa(), Path("/tmp"), NavegadorFalso
    )


def test_reproductor_reinicia_solo_cuando_toca():
    sikorius = reproductor()
    sikorius.empezar("CP-01", False)  # primero: siempre arranca
    sikorius.empezar("CP-02", False)
    assert sikorius.aplicacion.reinicios == 1
    assert sikorius.navegador.limpiado
    sikorius.empezar("CP-03", True)
    assert sikorius.aplicacion.reinicios == 2


def test_reproductor_comprueba_lo_visto():
    sikorius = reproductor()
    sikorius.empezar("CP-01", True)
    sikorius.pulsar("Crear modelo")
    sikorius.comprobar("y = 7.0000")
    sikorius.comprobar("hecho")
    with pytest.raises(AssertionError, match="No aparece en pantalla"):
        sikorius.comprobar("y = 8.0000")


def test_reproductor_accion_imposible_falla_el_test():
    sikorius = reproductor()
    sikorius.empezar("CP-01", True)
    with pytest.raises(AssertionError, match="Abrir"):
        sikorius.pulsar("Abrir")
