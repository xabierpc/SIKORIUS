"""Historia #11: selección de columnas (CP-15 a CP-21)."""

from funcionales.sikorius_ui import COLUMNAS, FEATURES, TARGET


def test_cp15_selectores_con_las_columnas(d1):
    """CP-15. Los selectores muestran las columnas del dataset."""
    d1.cargar_d1()
    assert d1.opciones(FEATURES) == COLUMNAS
    assert d1.opciones(TARGET) == COLUMNAS


def test_cp16_seleccion_valida_varias_entradas(d1):
    """CP-16. Selección válida con varias entradas."""
    d1.cargar_d1()
    d1.seleccionar(
        ["median_income", "housing_median_age"], "median_house_value"
    )
    exitos = " ".join(d1.exitos())
    assert "median_income" in exitos
    assert "housing_median_age" in exitos
    assert "Salida: median_house_value" in exitos
    assert d1.habilitado("Separar datos")


def test_cp17_sin_entrada(d1):
    """CP-17. Confirmar sin columna de entrada."""
    d1.cargar_d1()
    d1.elegir(TARGET, "median_house_value")
    d1.pulsar("Confirmar selección")
    errores = " ".join(d1.errores()).lower()
    assert "entrada" in errores or "feature" in errores, errores
    assert not d1.habilitado("Separar datos")


def test_cp18_sin_salida(d1):
    """CP-18. Confirmar sin columna de salida."""
    d1.cargar_d1()
    d1.marcar(FEATURES, ["median_income"])
    d1.pulsar("Confirmar selección")
    errores = " ".join(d1.errores()).lower()
    assert "salida" in errores or "target" in errores, errores


def test_cp19_salida_no_puede_ser_entrada(d1):
    """CP-19. La salida no puede ser también entrada."""
    d1.cargar_d1()
    d1.elegir(TARGET, "median_house_value")
    d1.marcar(FEATURES, ["median_house_value"])
    if "median_house_value" in d1.marcadas(FEATURES):
        # La aplicación deja marcarla: al confirmar debe dar error
        d1.pulsar("Confirmar selección")
        assert d1.errores(), "Se esperaba un error: entrada y salida iguales"
        assert not d1.habilitado("Separar datos")


def test_cp20_columna_no_numerica(d1):
    """CP-20. Columna no numérica."""
    d1.cargar_d1()
    d1.seleccionar(["ocean_proximity"], "median_house_value")
    errores = " ".join(d1.errores())
    assert "ocean_proximity" in errores, errores
    assert not d1.habilitado("Separar datos")


def test_cp21_otro_dataset_borra_la_seleccion(d1):
    """CP-21. Cargar otro dataset borra la selección."""
    d1.cargar_d1()
    d1.seleccionar(["median_income"], "median_house_value")
    d1.cargar("lineal.csv", ["pruebas"])
    assert d1.marcadas(FEATURES) == []
    assert d1.marcadas(TARGET) == []
    assert d1.opciones(FEATURES) == ["x1", "x2", "y"]
    assert not d1.habilitado("Separar datos")
