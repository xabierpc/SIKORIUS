"""Historia #22: predicciones (CP-75 a CP-81)."""

from funcionales.sikorius_ui import E1, S


def test_cp75_prediccion_sin_modelo(ui):
    """CP-75. Sin modelo no se puede predecir."""
    ui.reiniciar()
    assert "Modelo" not in ui.pestanas()
    assert not ui.hay_boton("Realizar predicción")


def test_cp76_prediccion_con_modelo_creado(ui):
    """CP-76. Predicción con un modelo creado: 2·2,5 − 3·1 + 5 = 7."""
    ui.modelo_lineal()
    assert ui.campos_prediccion() == ["x1", "x2"]
    assert ui.predecir({"x1": "2.5", "x2": "1"}) == "y = 7.0000"


def test_cp77_decimales_con_coma(ui):
    """CP-77. Decimales con coma: 2·2,5 − 3·0,5 + 5 = 8,5."""
    ui.modelo_lineal()
    assert ui.predecir({"x1": "2,5", "x2": "0,5"}) == "y = 8.5000"


def test_cp78_falta_un_valor(ui):
    """CP-78. Falta un valor."""
    ui.modelo_lineal()
    ui.olvidar_mensajes()
    ui.predecir({"x1": "", "x2": "1"})
    errores = " ".join(ui.errores())
    assert "x1" in errores, errores


def test_cp79_valor_no_numerico_y_correccion(ui):
    """CP-79. Valor no numérico y corrección: 2·1 − 3·2 + 5 = 1."""
    ui.modelo_lineal()
    ui.olvidar_mensajes()
    ui.predecir({"x1": "1", "x2": "abc"})
    errores = " ".join(ui.errores())
    assert "x2" in errores, errores
    assert ui.predecir({"x1": "1", "x2": "2"}) == "y = 1.0000"


def test_cp80_mismo_resultado_con_modelo_cargado(ui):
    """CP-80. Un modelo cargado predice lo mismo que el creado."""
    ui.modelo_lineal()
    ui.guardar_modelo("modelo_lineal")
    ui.reiniciar()
    ui.cargar_modelo("modelo_lineal.json")
    assert ui.predecir({"x1": "2.5", "x2": "1"}) == "y = 7.0000"


def test_cp81_campos_se_regeneran(d1):
    """CP-81. Con otro modelo, los campos cambian y se borra el resultado."""
    d1.modelo_lineal()
    assert d1.predecir({"x1": "2.5", "x2": "1"}) == "y = 7.0000"
    d1.cargar_d1()
    d1.seleccionar([E1], S)
    d1.separar()
    d1.crear_modelo()
    assert d1.campos_prediccion() == [E1]
    assert d1.resultado_prediccion() == ""
