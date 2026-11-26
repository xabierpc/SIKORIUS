"""Historia #37: experiencia de usuario (CP-82 a CP-88)."""

import pandas as pd
import pytest

from funcionales.sikorius_ui import E1, E2, S
from probador_llm.ejecutor import RAIZ

PALABRAS_DE_PYTHON = (
    "Traceback",
    "Exception",
    "Error:",
    "NoneType",
    "invalid literal",
    "could not convert",
    "KeyError",
    "ValueError",
)


def sin_desbordes(ui):
    """Comprueba que nada se sale de la ventana ni queda tapado."""
    ancho = ui.pagina.evaluate("() => document.documentElement.clientWidth")
    total = ui.pagina.evaluate("() => document.documentElement.scrollWidth")
    assert total <= ancho, "Hay desplazamiento horizontal: " + str(total)
    for boton in ui.visibles(ui.pagina.get_by_role("button")):
        caja = boton.bounding_box()
        if caja is None or caja["width"] == 0:
            continue
        assert caja["x"] >= 0 and caja["x"] + caja["width"] <= ancho + 1, (
            boton.inner_text()
        )
        # Que nada tape el centro del botón
        boton.scroll_into_view_if_needed()
        caja = boton.bounding_box()
        encima = ui.pagina.evaluate(
            "([x, y, b]) => { const e = document.elementFromPoint(x, y);"
            " return e !== null && (b.contains(e) || e.contains(b)); }",
            [
                caja["x"] + caja["width"] / 2,
                caja["y"] + caja["height"] / 2,
                boton.element_handle(),
            ],
        )
        assert encima, "Botón tapado: " + boton.inner_text()


def test_cp82_indicacion_inicial_y_orden(d1):
    """CP-82. Al empezar se indica qué hacer y los pasos van en orden."""
    d1.reiniciar()
    assert d1.hay_boton("Subir dataset")
    assert d1.hay_boton("Cargar modelo")
    d1.cargar_d1()
    assert d1.pestanas()[:3] == ["Inicio", "Datos", "Variables y separacion"]
    # En "Variables" no se puede continuar sin confirmar las columnas
    d1.pestana("Variables y separacion")
    assert not d1.habilitado("Continuar")
    assert not d1.habilitado("Separar datos")
    d1.seleccionar([E1], S)
    d1.separar()
    assert d1.pestanas() == [
        "Inicio",
        "Datos",
        "Variables y separacion",
        "Preprocesado",
        "Modelo",
    ]


def test_cp83_estado(d1):
    """CP-83. Se indica qué archivo hay y si el modelo está sin guardar."""
    d1.reiniciar()
    assert "Datos" not in d1.pestanas()
    d1.cargar_d1()
    assert d1.ruta().endswith("housing1.csv")
    d1.seleccionar([E1], S)
    d1.separar()
    d1.crear_modelo()
    assert d1.estado_guardado() == "Sin guardar"


def test_cp84_mensajes_coherentes(d1):
    """CP-84. Mensajes de éxito y error sin trazas ni textos de Python."""
    d1.cargar_d1()
    d1.cargar("vacio.csv", ["pruebas"])
    d1.cargar_d1()
    d1.seleccionar([E1], S)
    d1.separar("100")
    d1.modelo_lineal()
    d1.predecir({"x1": "1", "x2": "abc"})
    mensajes = d1.mensajes()
    tipos = set()
    for tipo, texto in mensajes:
        tipos.add(tipo)
        for palabra in PALABRAS_DE_PYTHON:
            assert palabra not in texto, texto
    assert {"exito", "error"} <= tipos, mensajes


@pytest.mark.skip(reason="Manual: hay que mover la ventana mientras carga")
def test_cp85_indicador_de_carga():
    """CP-85. Indicador durante la carga de un archivo grande."""


def test_cp86_tabla_grande(d1):
    """CP-86. Se puede llegar a la última fila de la tabla grande."""
    d1.cargar_d1()
    d1.pestana("Datos")
    contenedor = d1.pagina.locator(".q-table__middle").first
    for _ in range(10):
        contenedor.evaluate("(e) => { e.scrollTop = e.scrollHeight; }")
        d1.pagina.wait_for_timeout(300)
    filas = d1.visibles(d1.pagina.locator("tbody tr"))
    ultima = filas[-1].locator("td")
    valores = []
    for indice in range(ultima.count()):
        valores.append(ultima.nth(indice).inner_text().strip())
    datos = pd.read_csv(RAIZ / "data" / "housing1.csv")
    esperada = datos.iloc[-1]
    assert valores[-1] == str(esperada["ocean_proximity"]), valores
    assert float(valores[0]) == float(esperada["longitude"]), valores


def test_cp87_ventana_1366x768(d1):
    """CP-87. A 1366 × 768 no hay nada cortado ni tapado."""
    d1.cargar_d1()
    d1.seleccionar([E1, E2], S)
    d1.separar()
    d1.crear_modelo()
    for pestana in ("Inicio", "Datos", "Variables y separacion", "Modelo"):
        d1.pestana(pestana)
        sin_desbordes(d1)


def test_cp88_redimensionar(d1):
    """CP-88. Al estrechar la ventana y volver, todo se reorganiza."""
    d1.cargar_d1()
    d1.seleccionar([E1], S)
    d1.separar()
    d1.crear_modelo()
    tamano = d1.pagina.viewport_size
    try:
        d1.pagina.set_viewport_size({"width": 683, "height": tamano["height"]})
        d1.esperar()
        for pestana in ("Datos", "Modelo"):
            d1.pestana(pestana)
            ancho = d1.pagina.evaluate(
                "() => document.documentElement.clientWidth"
            )
            total = d1.pagina.evaluate(
                "() => document.documentElement.scrollWidth"
            )
            assert total <= ancho, (
                pestana + ": " + str(total) + " > " + str(ancho)
            )
    finally:
        d1.pagina.set_viewport_size(tamano)
        d1.esperar()
    d1.pestana("Modelo")
    sin_desbordes(d1)
