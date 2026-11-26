"""CP-93. Flujo completo: cargar, crear, guardar, cargar y predecir."""

import re

from funcionales.sikorius_ui import C_NAN, E1, FEATURES, MEDIANA, TARGET, S
from probador_llm.ejecutor import RAIZ

ARCHIVO = RAIZ / "data" / "pruebas" / "flujo_completo.json"


def predicho(formula, valores):
    """Calcula a mano la predicción con la fórmula que muestra la app."""
    derecha = formula.split(" = ", 1)[1].replace("−", "-").replace("·", "*")
    total = 0.0
    for signo, coeficiente, variable in re.findall(
        r"([+-]?)\s*([\d.]+)(?:\s*\*\s*(\w+))?", derecha
    ):
        termino = float(coeficiente)
        if variable:
            termino = termino * float(valores[variable])
        if signo == "-":
            termino = -termino
        total = total + termino
    return total


def test_cp93_flujo_completo(d1):
    if ARCHIVO.exists():
        ARCHIVO.unlink()
    d1.reiniciar()
    d1.pulsar("Subir dataset")
    d1.ir_a_carpeta([])
    d1.elegir_archivo("housing1.csv")
    d1.marcar(FEATURES, [C_NAN, E1])
    d1.elegir(TARGET, S)
    d1.pulsar("Confirmar selección")
    d1.separar()
    d1.preprocesar(MEDIANA)
    d1.crear_modelo()
    formula = d1.formula()
    d1.escribir_descripcion("Flujo completo")
    d1.guardar_modelo("flujo_completo")
    valores = {C_NAN: "500", E1: "3.5"}
    resultado = d1.predecir(valores)
    assert d1.errores() == [], d1.errores()
    assert len(d1.exitos()) >= 6, d1.exitos()
    assert ARCHIVO.is_file()

    d1.reiniciar()
    d1.cargar_modelo("flujo_completo.json")
    assert d1.formula() == formula
    assert d1.descripcion() == "Flujo completo"
    assert d1.predecir(valores) == resultado

    a_mano = predicho(formula, valores)
    obtenido = float(resultado.split(" = ", 1)[1])
    # La fórmula muestra los coeficientes con 4 decimales
    assert abs(obtenido - a_mano) < 0.01 * max(1.0, abs(a_mano)), (
        resultado,
        a_mano,
    )
