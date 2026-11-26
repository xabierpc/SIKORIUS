"""Historia #26: valores inexistentes (CP-35 a CP-45)."""

import re

import pandas as pd

from funcionales.sikorius_ui import (
    C_NAN,
    CONSTANTE,
    E1,
    ELIMINAR,
    FILAS,
    MEDIA,
    MEDIANA,
    N_NAN,
    S,
)
from probador_llm.ejecutor import RAIZ


def preparar_con_nulos(ui):
    ui.cargar_d1()
    ui.seleccionar([C_NAN], S)
    ui.separar()


def suma_resumen(texto, clave):
    """Suma los números de "N filas eliminadas" o "N valores rellenados"."""
    total = 0
    for numero in re.findall(r"(\d+) " + clave, texto):
        total = total + int(numero)
    return total


def test_cp35_deteccion(d1):
    """CP-35. Detección de valores inexistentes por conjunto."""
    preparar_con_nulos(d1)
    nulos = d1.nulos()
    entrenamiento, test = nulos[C_NAN]
    assert entrenamiento + test == N_NAN
    assert nulos[S] == (0, 0)
    assert not d1.puede_crear_modelo()


def test_cp36_sin_nulos(d1):
    """CP-36. Sin valores inexistentes se puede continuar."""
    d1.cargar_d1()
    d1.seleccionar([E1], S)
    d1.separar()
    d1.pestana("Preprocesado")
    assert "No hay valores inexistentes" in d1.texto()
    assert d1.puede_crear_modelo()


def test_cp37_eliminar_filas(d1):
    """CP-37. Eliminar filas con valores inexistentes."""
    preparar_con_nulos(d1)
    d1.olvidar_mensajes()
    d1.preprocesar(ELIMINAR)
    resumen = " ".join(d1.exitos())
    assert suma_resumen(resumen, "filas eliminadas") == N_NAN, resumen
    assert d1.nulos()[C_NAN] == (0, 0) or "Aplicado" in d1.texto()
    assert d1.puede_crear_modelo()


def comprobar_relleno(ui, estrategia, constante=None):
    preparar_con_nulos(ui)
    antes = ui.resultado_separacion()
    ui.olvidar_mensajes()
    ui.preprocesar(estrategia, constante)
    resumen = " ".join(ui.exitos())
    assert suma_resumen(resumen, "valores rellenados") == N_NAN, resumen
    assert suma_resumen(resumen, "filas eliminadas") == 0, resumen
    assert ui.resultado_separacion() == antes
    assert ui.puede_crear_modelo()


def test_cp38_media(d1):
    """CP-38. Rellenar con la media."""
    comprobar_relleno(d1, MEDIA)


def test_cp39_mediana(d1):
    """CP-39. Rellenar con la mediana."""
    comprobar_relleno(d1, MEDIANA)


def test_cp40_constante(d1):
    """CP-40. Rellenar con un valor constante (campo solo habilitado con esa
    opción)."""
    preparar_con_nulos(d1)
    d1.pestana("Preprocesado")
    d1.pagina.get_by_role("radio", name=ELIMINAR, exact=True).click()
    d1.esperar()
    assert not d1.campo("Valor constante").is_enabled()
    d1.pagina.get_by_role("radio", name=CONSTANTE, exact=True).click()
    d1.esperar()
    assert d1.campo("Valor constante").is_enabled()
    d1.escribir("Valor constante", "0")
    d1.olvidar_mensajes()
    d1.pulsar_y_esperar_mensaje("Aplicar preprocesado")
    resumen = " ".join(d1.exitos())
    assert suma_resumen(resumen, "valores rellenados") == N_NAN, resumen


def test_cp41_constante_no_numerica(d1):
    """CP-41. Constante no numérica y corrección."""
    preparar_con_nulos(d1)
    nulos = d1.nulos()
    d1.pestana("Preprocesado")
    d1.pagina.get_by_role("radio", name=CONSTANTE, exact=True).click()
    d1.esperar()
    campo = d1.campo("Valor constante")
    d1.olvidar_mensajes()
    campo.fill("")
    campo.press_sequentially("abc")
    d1.esperar()
    d1.pulsar_y_esperar_mensaje("Aplicar preprocesado")
    # El campo es numérico: o no admite letras (queda vacío) o da error.
    # En los dos casos no se aplica nada y hay un mensaje sobre la constante.
    assert d1.exitos() == []
    errores = " ".join(d1.errores() + d1.avisos()).lower()
    assert "constante" in errores or "valor" in errores, errores
    assert d1.nulos() == nulos
    d1.escribir("Valor constante", "5")
    d1.olvidar_mensajes()
    d1.pulsar_y_esperar_mensaje("Aplicar preprocesado")
    resumen = " ".join(d1.exitos())
    assert suma_resumen(resumen, "valores rellenados") == N_NAN, resumen


def test_cp42_eliminacion_que_vacia(ui):
    """CP-42. Una eliminación que vaciaría un conjunto no se aplica."""
    ui.cargar("nulos_total.csv", ["pruebas"])
    ui.seleccionar(["x"], "y")
    ui.separar()
    nulos = ui.nulos()
    ui.olvidar_mensajes()
    ui.preprocesar(ELIMINAR)
    assert ui.avisos() or ui.errores(), "Se esperaba un aviso"
    assert ui.exitos() == []
    assert ui.nulos() == nulos
    assert not ui.puede_crear_modelo()


def test_cp43_repetir_separacion_obliga_a_preprocesar(d1):
    """CP-43. Repetir la separación obliga a repetir el preprocesado."""
    comprobar_relleno(d1, MEDIA)
    d1.separar("30")
    entrenamiento, test = d1.nulos()[C_NAN]
    assert entrenamiento + test == N_NAN
    assert not d1.puede_crear_modelo()


def test_cp44_archivo_original_sin_cambios(d1):
    """CP-44. El preprocesado no modifica el archivo original."""
    preparar_con_nulos(d1)
    d1.preprocesar(MEDIA)
    datos = pd.read_csv(RAIZ / "data" / "housing1.csv")
    assert len(datos) == FILAS
    assert int(datos[C_NAN].isna().sum()) == N_NAN


def test_cp45_crear_modelo_deshabilitado_con_nulos(d1):
    """CP-45. Con valores inexistentes no se puede crear el modelo."""
    preparar_con_nulos(d1)
    assert not d1.puede_crear_modelo()
