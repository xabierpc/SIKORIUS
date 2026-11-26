"""Historia #21: guardado del modelo (CP-57 a CP-64)."""

import json
import os

import pytest

from funcionales.sikorius_ui import E1, S
from probador_llm.ejecutor import RAIZ

PRUEBAS = RAIZ / "data" / "pruebas"
DESCRIPCION = "Modelo de prueba\nCreado con lineal.csv"


def modelo_con_descripcion(ui):
    ui.modelo_lineal()
    ui.escribir_descripcion(DESCRIPCION)


def test_cp57_guardar_solo_con_modelo(d1):
    """CP-57. "Guardar modelo" solo se puede usar cuando hay modelo."""
    d1.reiniciar()
    assert "Modelo" not in d1.pestanas()
    d1.cargar_d1()
    d1.seleccionar([E1], S)
    d1.separar()
    d1.pestana("Modelo")
    assert not d1.habilitado("Guardar modelo")
    d1.crear_modelo()
    assert d1.habilitado("Guardar modelo")


def test_cp58_guardar_con_descripcion(ui):
    """CP-58. Guardar un modelo con descripción (se añade la extensión)."""
    modelo_con_descripcion(ui)
    ui.olvidar_mensajes()
    ui.guardar_modelo("modelo_lineal")
    exitos = " ".join(ui.exitos())
    assert exitos.endswith("data/pruebas/modelo_lineal.json"), exitos
    assert (PRUEBAS / "modelo_lineal.json").is_file()


def test_cp59_contenido_del_archivo(ui):
    """CP-59. El archivo guarda el modelo y la descripción, no los datos."""
    modelo_con_descripcion(ui)
    ui.guardar_modelo("modelo_contenido")
    texto = (PRUEBAS / "modelo_contenido.json").read_text(encoding="utf-8")
    contenido = json.loads(texto)
    assert "Modelo de prueba" in texto
    assert "Creado con lineal.csv" in texto
    for columna in ("x1", "x2", "y"):
        assert '"' + columna + '"' in texto
    # Ni las filas del dataset ni imágenes: el archivo es pequeño
    assert len(texto) < 5000, len(texto)
    assert "7, 6, 11" not in texto and "[7, 6, 11" not in texto
    assert "base64" not in texto
    assert isinstance(contenido, dict)


def test_cp60_aviso_sin_descripcion(ui):
    """CP-60. Sin descripción se avisa, pero se puede guardar."""
    ui.modelo_lineal()
    ui.pestana("Modelo")
    ui.pulsar("Guardar modelo")
    assert "no tiene descripción" in ui.texto_dialogo()
    ui.ir_a_carpeta(["pruebas"])
    ui.escribir("Nombre del archivo", "sin_descripcion", ui.dialogo())
    ui.olvidar_mensajes()
    ui.pulsar("Guardar", ui.dialogo())
    ui._responder_confirmacion("El archivo ya existe", True)
    exitos = " ".join(ui.exitos())
    assert exitos.endswith("sin_descripcion.json"), exitos
    assert (PRUEBAS / "sin_descripcion.json").is_file()


def test_cp61_confirmar_sobrescritura(ui):
    """CP-61. Antes de sobrescribir se pide confirmación."""
    modelo_con_descripcion(ui)
    ui.guardar_modelo("modelo_lineal")
    ui.olvidar_mensajes()
    assert ui.guardar_modelo("modelo_lineal", sobrescribir=False)
    assert ui.exitos() == []
    assert ui.guardar_modelo("modelo_lineal", sobrescribir=True)
    exitos = " ".join(ui.exitos())
    assert exitos.endswith("modelo_lineal.json"), exitos


def test_cp62_cancelar_guardado(ui):
    """CP-62. Cerrar el diálogo de guardado no guarda nada."""
    ui.modelo_lineal()
    antes = ui.archivos_en("pruebas")
    ui.olvidar_mensajes()
    ui.pestana("Modelo")
    ui.pulsar("Guardar modelo")
    ui.pulsar("Cancelar", ui.dialogo())
    assert not ui.hay_dialogo()
    assert ui.mensajes() == []
    assert ui.archivos_en("pruebas") == antes


def test_cp63_ruta_con_caracteres_especiales(ui):
    """CP-63. Guardar en una carpeta con espacios, ñ y tildes."""
    ui.modelo_lineal()
    ui.olvidar_mensajes()
    ui.guardar_modelo("modelo año", ("pruebas", "carpeta ñandú á"))
    exitos = " ".join(ui.exitos())
    assert "carpeta ñandú á/modelo año.json" in exitos, exitos
    assert (PRUEBAS / "carpeta ñandú á" / "modelo año.json").is_file()


@pytest.mark.skipif(
    os.name == "nt" or os.geteuid() == 0,
    reason="Hace falta Linux o macOS sin ser root para quitar permisos",
)
def test_cp64_error_de_permisos(ui):
    """CP-64. Error claro si no se puede escribir, y luego se guarda bien."""
    ui.modelo_lineal()
    ui.olvidar_mensajes()
    ui.guardar_modelo("prohibido", ("pruebas", "solo_lectura"))
    errores = " ".join(ui.errores())
    assert errores, "Se esperaba un mensaje de error"
    assert "Traceback" not in errores
    assert not (PRUEBAS / "solo_lectura" / "prohibido.json").exists()
    ui.olvidar_mensajes()
    ui.guardar_modelo("reintento")
    assert " ".join(ui.exitos()).endswith("reintento.json")
