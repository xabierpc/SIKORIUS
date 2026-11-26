"""Historia #24: recuperación del modelo (CP-65 a CP-74)."""

from funcionales.sikorius_ui import FILAS
from probador_llm.ejecutor import RAIZ

PRUEBAS = RAIZ / "data" / "pruebas"
DESCRIPCION = "Modelo de prueba\nCreado con lineal.csv"
FORMULA = "y = 2.0000 · x1 − 3.0000 · x2 + 5.0000"


def guardar(ui, nombre, descripcion=DESCRIPCION):
    """Crea el modelo de lineal.csv y lo guarda en data/pruebas/."""
    ui.modelo_lineal()
    if descripcion:
        ui.escribir_descripcion(descripcion)
    ui.guardar_modelo(nombre)


def test_cp65_cargar_modelo_al_iniciar(ui):
    """CP-65. Cargar un modelo con la aplicación recién abierta."""
    guardar(ui, "modelo_lineal")
    ui.reiniciar()
    ui.cargar_modelo("modelo_lineal.json")
    exitos = " ".join(ui.exitos())
    assert "Modelo cargado de" in exitos and "modelo_lineal.json" in exitos
    assert ui.pestanas() == ["Inicio", "Modelo"]
    assert ui.formula() == FORMULA
    assert set(ui.metricas()) == {"Entrenamiento", "Test"}
    assert ui.descripcion() == DESCRIPCION
    assert ui.graficos() == []
    assert ui.campos_prediccion() == ["x1", "x2"]
    assert ui.habilitado("Realizar predicción")


def test_cp66_explorador_de_modelos(ui):
    """CP-66. El diálogo de carga solo muestra modelos (.json)."""
    guardar(ui, "modelo_lineal")
    ui.abrir_explorador_modelo()
    ui.ir_a_carpeta(["pruebas"])
    entradas = ui.entradas_explorador()
    assert "modelo_lineal.json" in entradas
    for nombre in entradas:
        assert not nombre.endswith((".csv", ".db", ".xlsx")), nombre


def test_cp67_modelo_sin_descripcion(ui):
    """CP-67. Un modelo guardado sin descripción se carga con ella vacía."""
    guardar(ui, "sin_descripcion", descripcion="")
    ui.olvidar_mensajes()
    ui.cargar_modelo("sin_descripcion.json")
    assert "Modelo cargado de" in " ".join(ui.exitos())
    assert ui.descripcion() == ""


def test_cp68_cancelar_carga_de_modelo(d1):
    """CP-68. Cancelar la carga del modelo deja todo como estaba."""
    d1.cargar_d1()
    d1.olvidar_mensajes()
    d1.abrir_explorador_modelo()
    d1.pulsar("Cancelar", d1.dialogo())
    assert d1.errores() == []
    assert d1.ruta().endswith("data/housing1.csv")
    assert d1.resumen().startswith(str(FILAS) + " filas")


def test_cp69_modelo_danado(ui):
    """CP-69. Un modelo dañado da error y se conserva el que había."""
    guardar(ui, "modelo_lineal")
    ui.cargar_modelo("modelo_lineal.json")
    ui.olvidar_mensajes()
    ui.cargar_modelo("modelo_roto.json")
    assert ui.errores(), "Se esperaba un mensaje de error"
    assert ui.formula() == FORMULA
    assert ui.descripcion() == DESCRIPCION


def test_cp70_modelo_incompleto(ui):
    """CP-70. Un modelo incompleto da error; después se carga uno bueno."""
    guardar(ui, "modelo_lineal")
    ui.olvidar_mensajes()
    ui.cargar_modelo("modelo_incompleto.json")
    assert ui.errores(), "Se esperaba un mensaje de error"
    ui.olvidar_mensajes()
    ui.cargar_modelo("modelo_lineal.json")
    assert "Modelo cargado de" in " ".join(ui.exitos())
    assert ui.formula() == FORMULA


def test_cp71_solo_la_descripcion_es_editable(ui):
    """CP-71. En un modelo cargado solo se puede cambiar la descripción."""
    guardar(ui, "modelo_lineal")
    ui.cargar_modelo("modelo_lineal.json")
    ui.pestana("Modelo")
    editables = []
    for campo in ui.visibles(ui.pagina.get_by_role("textbox")):
        if campo.is_editable():
            editables.append(campo)
    etiquetas = []
    for campo in editables:
        etiquetas.append(campo.evaluate("(e) => e.closest('label').innerText"))
    texto_etiquetas = " ".join(etiquetas)
    # Editables: la descripción y los campos de predicción (x1, x2)
    assert "Descripción (opcional)" in texto_etiquetas
    assert "R²" not in texto_etiquetas and "=" not in texto_etiquetas
    assert len(editables) == 3, etiquetas
    ui.escribir_descripcion(DESCRIPCION + " (revisado)")
    assert ui.estado_guardado().startswith("Cambios sin guardar")


def test_cp72_volver_a_guardar_modelo_cargado(ui):
    """CP-72. Guardar de nuevo un modelo cargado con otra descripción."""
    guardar(ui, "modelo_revisado")
    ui.cargar_modelo("modelo_revisado.json")
    metricas = ui.metricas()
    ui.escribir_descripcion(DESCRIPCION + " (revisado)")
    ui.pestana("Modelo")
    ui.pulsar("Guardar modelo")
    assert ui.carpeta_explorador().endswith("data/pruebas")
    nombre = ui.campo("Nombre del archivo", ui.dialogo()).input_value()
    assert nombre == "modelo_revisado.json"
    ui.pulsar("Guardar", ui.dialogo())
    assert ui._responder_confirmacion("El archivo ya existe", True)
    assert ui.estado_guardado().startswith("Guardado en")
    ui.reiniciar()
    ui.cargar_modelo("modelo_revisado.json")
    assert ui.descripcion().endswith("(revisado)")
    assert ui.formula() == FORMULA
    assert ui.metricas() == metricas


def test_cp73_confirmar_si_hay_cambios_sin_guardar(ui):
    """CP-73. Cargar un modelo con otro sin guardar pide confirmación."""
    guardar(ui, "modelo_lineal")
    ui.modelo_lineal()
    assert ui.abrir_explorador_modelo(confirmar=False)
    assert not ui.hay_dialogo()
    assert len(ui.graficos()) == 1
    ui.cargar_modelo("modelo_lineal.json", confirmar=True)
    assert ui.pestanas() == ["Inicio", "Modelo"]
    assert ui.graficos() == []


def test_cp74_dataset_tras_modelo_cargado(d1):
    """CP-74. Cargar un dataset después de un modelo cargado."""
    guardar(d1, "modelo_lineal")
    d1.cargar_modelo("modelo_lineal.json")
    d1.cargar_d1()
    for pestana in ("Datos", "Variables y separacion"):
        assert pestana in d1.pestanas()
    assert d1.resumen().startswith(str(FILAS) + " filas")
    assert not d1.hay_modelo()
