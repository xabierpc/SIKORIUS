"""Historia #41: separación en entrenamiento y test (CP-22 a CP-34)."""

import pytest

from funcionales.sikorius_ui import E1, E2, S


def preparar(ui):
    ui.cargar_d1()
    ui.seleccionar([E1], S)


def test_cp22_separar_antes_de_confirmar(d1):
    """CP-22. Separar no está disponible antes de confirmar columnas."""
    d1.cargar_d1()
    d1.pestana("Variables y separacion")
    assert not d1.habilitado("Separar datos")
    assert "Preprocesado" not in d1.pestanas()
    assert not d1.puede_crear_modelo()


def test_cp23_valores_por_defecto(d1):
    """CP-23. Separación con valores por defecto (20 % y semilla 42)."""
    d1.reiniciar()
    preparar(d1)
    assert d1.campo("Porcentaje de test (%)").input_value() == "20"
    assert d1.campo("Semilla").input_value() == "42"
    d1.pulsar("Separar datos")
    assert d1.exitos(), "Se esperaba un mensaje de confirmación"
    assert d1.resultado_separacion() == (
        "Entrenamiento: 16512 filas | Test: 4128 filas"
    )


@pytest.mark.parametrize("porcentaje", ["0", "100"])
def test_cp24_cp27_porcentaje_fuera_de_rango(d1, porcentaje):
    """CP-24 y CP-27. Porcentajes 0 y 100 (valores límite no válidos)."""
    preparar(d1)
    d1.separar(porcentaje)
    errores = " ".join(d1.errores())
    assert "1" in errores and "99" in errores, errores
    assert d1.resultado_separacion() is None
    assert not d1.puede_crear_modelo()


@pytest.mark.parametrize(
    ("porcentaje", "esperado"),
    [
        ("1", "Entrenamiento: 20433 filas | Test: 207 filas"),
        ("99", "Entrenamiento: 206 filas | Test: 20434 filas"),
    ],
)
def test_cp25_cp26_porcentaje_limite_valido(d1, porcentaje, esperado):
    """CP-25 y CP-26. Porcentajes 1 y 99 (valores límite válidos)."""
    preparar(d1)
    d1.separar(porcentaje)
    assert d1.exitos(), "Se esperaba un mensaje de confirmación"
    assert d1.resultado_separacion() == esperado


@pytest.mark.parametrize("porcentaje", ["abc", "-5", ""])
def test_cp28_porcentaje_no_valido(d1, porcentaje):
    """CP-28. Porcentaje no numérico, negativo o vacío."""
    preparar(d1)
    d1.separar(porcentaje)
    errores = " ".join(d1.errores()).lower()
    assert "porcentaje" in errores, errores
    assert d1.resultado_separacion() is None


@pytest.mark.parametrize("semilla", ["3.5", "abc"])
def test_cp29_semilla_no_entera(d1, semilla):
    """CP-29. Semilla no entera."""
    preparar(d1)
    d1.separar("20", semilla)
    errores = " ".join(d1.errores()).lower()
    assert "semilla" in errores and "entero" in errores, errores


def test_cp30_misma_semilla_misma_separacion(ui):
    """CP-30. Misma semilla, misma separación."""
    ui.cargar("lineal.csv", ["pruebas"])
    ui.seleccionar(["x1", "x2"], "y")
    ui.separar("20", "7")
    primera = ui.resultado_separacion()
    ui.crear_modelo()
    formula = ui.formula()
    metricas = ui.metricas()
    ui.separar("20", "7")
    assert ui.resultado_separacion() == primera
    ui.crear_modelo()
    assert ui.formula() == formula
    assert ui.metricas() == metricas


def test_cp31_menos_de_5_filas(ui):
    """CP-31. Dataset con menos de 5 filas."""
    ui.cargar("cuatro_filas.csv", ["pruebas"])
    ui.seleccionar(["x"], "y")
    ui.separar()
    errores = " ".join(ui.errores())
    assert "5" in errores, errores
    assert ui.resultado_separacion() is None


def test_cp32_conjunto_vacio(ui):
    """CP-32. Un porcentaje que deja vacío el entrenamiento."""
    ui.cargar("cinco_filas.csv", ["pruebas"])
    ui.seleccionar(["x"], "y")
    ui.separar("99")
    errores = " ".join(ui.errores()).lower()
    assert "vac" in errores, errores
    assert ui.resultado_separacion() is None


def test_cp33_repetir_separacion_descarta_modelo(d1):
    """CP-33. Repetir la separación descarta el modelo."""
    preparar(d1)
    d1.separar()
    d1.crear_modelo()
    assert d1.hay_modelo()
    d1.separar("30")
    assert not d1.hay_modelo()
    if "Modelo" in d1.pestanas():
        d1.pestana("Modelo")
        assert not d1.habilitado("Guardar modelo")
        assert not d1.hay_boton("Realizar predicción")


def test_cp34_cambiar_columnas_obliga_a_separar(d1):
    """CP-34. Cambiar las columnas obliga a separar de nuevo."""
    preparar(d1)
    d1.separar()
    d1.seleccionar([E1, E2], S)
    assert d1.resultado_separacion() is None
    assert not d1.puede_crear_modelo()
