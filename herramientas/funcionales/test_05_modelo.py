"""Historias #16 y #33: creación del modelo y descripción (CP-46 a CP-56)."""

from funcionales.sikorius_ui import C_NAN, E1, E2, MEDIA, S


def numero(texto):
    return float(texto.replace(",", "."))


def test_cp46_crear_modelo_solo_tras_separar(d1):
    """CP-46. "Crear modelo" no se puede usar hasta separar los datos."""
    d1.reiniciar()
    assert not d1.puede_crear_modelo()
    d1.cargar_d1()
    assert not d1.puede_crear_modelo()
    d1.seleccionar([E1], S)
    assert not d1.puede_crear_modelo()
    d1.separar()
    assert d1.puede_crear_modelo()


def test_cp47_modelo_exacto(ui):
    """CP-47. Modelo con resultado exacto (y = 2·x1 − 3·x2 + 5)."""
    ui.cargar("lineal.csv", ["pruebas"])
    ui.seleccionar(["x1", "x2"], "y")
    ui.separar()
    ui.olvidar_mensajes()
    ui.crear_modelo()
    assert "Modelo creado correctamente." in ui.exitos()
    formula = ui.formula()
    assert formula == "y = 2.0000 · x1 − 3.0000 · x2 + 5.0000", formula
    assert "+ -" not in formula and "+ −" not in formula
    metricas = ui.metricas()
    for conjunto in ("Entrenamiento", "Test"):
        assert numero(metricas[conjunto]["R²"]) == 1, metricas
        assert numero(metricas[conjunto]["ECM"]) == 0, metricas


def test_cp48_cp50_grafico_simple_y_metricas(d1):
    """CP-48 y CP-50. Gráfico de regresión simple y métricas por conjunto."""
    d1.cargar_d1()
    d1.seleccionar([E1], S)
    d1.separar()
    d1.crear_modelo()
    graficos = d1.graficos()
    assert len(graficos) == 1
    grafico = graficos[0]
    assert grafico["leyenda"]
    assert grafico["ejeX"] == [E1]
    assert grafico["ejeY"] == [S]
    tipos = {}
    for serie in grafico["series"]:
        tipos[serie["nombre"]] = serie["tipo"]
    assert tipos.get("Entrenamiento") == "scatter", tipos
    assert tipos.get("Test") == "scatter", tipos
    assert "line" in tipos.values(), tipos
    assert d1.formula().startswith(S + " = ")
    assert E1 in d1.formula()
    metricas = d1.metricas()
    for conjunto in ("Entrenamiento", "Test"):
        assert numero(metricas[conjunto]["R²"]) <= 1
        assert numero(metricas[conjunto]["ECM"]) >= 0


def test_cp49_cp51_grafico_multiple_sustituye(d1):
    """CP-49 y CP-51. Regresión múltiple: real frente a predicho, y el nuevo
    modelo sustituye al anterior."""
    d1.cargar_d1()
    d1.seleccionar([E1], S)
    d1.separar()
    d1.crear_modelo()
    formula_simple = d1.formula()
    metricas_simple = d1.metricas()
    d1.seleccionar([E1, E2], S)
    d1.separar()
    d1.crear_modelo()
    formula = d1.formula()
    assert formula != formula_simple
    assert E1 in formula and E2 in formula
    assert d1.metricas() != metricas_simple
    grafico = d1.graficos()[0]
    ejes = grafico["ejeX"] + grafico["ejeY"]
    assert "Valor real" in ejes and "Valor predicho" in ejes, ejes
    assert grafico["leyenda"]
    nombres = []
    for serie in grafico["series"]:
        nombres.append(serie["nombre"])
    assert "Entrenamiento" in nombres and "Test" in nombres, nombres


def test_cp52_modelo_con_datos_preprocesados(d1):
    """CP-52. Con datos preprocesados se crea el modelo (al aplicar el
    preprocesado la aplicación ya lo crea)."""
    d1.cargar_d1()
    d1.seleccionar([C_NAN], S)
    d1.separar()
    d1.olvidar_mensajes()
    d1.preprocesar(MEDIA)
    if not d1.hay_modelo():
        d1.crear_modelo()
    assert "Modelo creado correctamente." in d1.exitos()
    assert C_NAN in d1.formula()
    assert len(d1.graficos()) == 1
    assert set(d1.metricas()) == {"Entrenamiento", "Test"}


def test_cp53_entrada_constante(ui):
    """CP-53. Una entrada con todos los valores iguales no rompe la app."""
    ui.cargar("nulos_total.csv", ["pruebas"])
    ui.seleccionar(["x"], "y")
    ui.separar()
    ui.preprocesar("Rellenar con un valor constante", "0")
    if ui.puede_crear_modelo():
        ui.crear_modelo()
    assert ui.exitos() or ui.errores()
    texto = ui.texto()
    assert "Traceback" not in texto
    for mensaje in ui.errores():
        assert "Traceback" not in mensaje
    # La aplicación sigue respondiendo
    ui.pestana("Inicio")
    assert ui.hay_boton("Subir dataset") or "Datos" in ui.pestanas()


def test_cp54_descripcion_sin_modelo(ui):
    """CP-54. Sin modelo, la descripción no se puede escribir."""
    ui.reiniciar()
    assert "Modelo" not in ui.pestanas()
    textos = ui.visibles(
        ui.pagina.get_by_role("textbox", name="Descripción (opcional)")
    )
    assert textos == []


def test_cp55_descripcion_varias_lineas(ui):
    """CP-55. Descripción de varias líneas."""
    ui.modelo_lineal()
    campo = ui.campo("Descripción (opcional)")
    campo.click()
    campo.press_sequentially("Modelo de prueba")
    campo.press("Enter")
    campo.press_sequentially("Creado con lineal.csv")
    ui.esperar()
    assert ui.descripcion() == "Modelo de prueba\nCreado con lineal.csv"


def test_cp56_modelo_nuevo_vacia_descripcion(ui):
    """CP-56. Un modelo nuevo empieza sin descripción."""
    ui.modelo_lineal()
    ui.escribir_descripcion("Descripción del modelo anterior")
    ui.separar()
    ui.crear_modelo()
    assert ui.descripcion() == ""
