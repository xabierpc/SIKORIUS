"""Pruebas del diálogo de guardado del modelo, sin servidor (#21).

El diálogo se crea pero no se abre: se prueban sus botones llamando a sus
métodos, igual que en los tests de los paneles. Que se vea bien en pantalla
se comprueba a mano.

    uv run pytest tests/gui/test_dialogo_guardado.py -v
"""

import asyncio
from pathlib import Path

import pytest
from nicegui import ui

from sikorius.gui.componentes.dialogo_guardado import (
    CARACTERES_PROHIBIDOS,
    DialogoGuardado,
    carpeta_valida,
    es_modelo,
    motivo_nombre_no_valido,
    ruta_destino,
)
from sikorius.gui.componentes.explorador_archivos import listar_carpeta

# =============================================================================
# Utilidades
# =============================================================================


@pytest.fixture
def avisos(monkeypatch):
    """Recoge los ui.notify (mensaje, tipo) en lugar de mostrarlos."""
    lista = []

    def anotar(mensaje, **kw):
        lista.append((mensaje, kw.get("type")))

    monkeypatch.setattr(ui, "notify", anotar)
    return lista


def respuesta_fija(respuesta, preguntas):
    """Confirmación falsa: anota la pregunta y contesta siempre igual."""

    async def preguntar(titulo, mensaje, texto_aceptar):
        preguntas.append((titulo, mensaje, texto_aceptar))
        return respuesta

    return preguntar


def nombres_lista(dialogo):
    """Textos de las entradas que se ven en la lista del diálogo."""
    textos = []
    for elemento in dialogo.lista.descendants():
        if isinstance(elemento, ui.item_label):
            textos.append(elemento.text)
    return textos


@pytest.fixture
def carpeta_rara(tmp_path):
    carpeta = tmp_path / "Mis modelos ñandú" / "acción y canción"
    carpeta.mkdir(parents=True)
    return carpeta


# =============================================================================
# Funciones sin interfaz
# =============================================================================


@pytest.mark.parametrize(
    "nombre", ["m.json", "M.JSON", "modelo ñ.Json", "a b.json"]
)
def test_es_modelo(nombre):
    assert es_modelo(nombre)
    assert es_modelo(Path(nombre))


@pytest.mark.parametrize(
    "nombre", ["datos.csv", "m.json.bak", "json", "m.txt", "m"]
)
def test_no_es_modelo(nombre):
    assert not es_modelo(nombre)


@pytest.mark.parametrize(
    "nombre",
    ["modelo", "modelo.json", "Mi modelo ñ", "año 2026 (v2)", "  m  "],
)
def test_nombres_validos(nombre):
    assert motivo_nombre_no_valido(nombre) is None


@pytest.mark.parametrize("nombre", ["", "   ", None, "\t"])
def test_nombre_vacio(nombre):
    assert "Escribe un nombre" in motivo_nombre_no_valido(nombre)


@pytest.mark.parametrize("nombre", [".", ".."])
def test_nombres_especiales(nombre):
    assert "no es un nombre" in motivo_nombre_no_valido(nombre)


@pytest.mark.parametrize("caracter", list(CARACTERES_PROHIBIDOS))
def test_caracteres_prohibidos(caracter):
    motivo = motivo_nombre_no_valido("mo" + caracter + "delo")
    assert "no puede contener" in motivo


def test_las_barras_no_permiten_salir_de_la_carpeta():
    assert motivo_nombre_no_valido("../otro") is not None
    assert motivo_nombre_no_valido("sub/modelo") is not None
    assert motivo_nombre_no_valido("sub\\modelo") is not None


@pytest.mark.parametrize(
    ("nombre", "esperado"),
    [
        ("modelo", "modelo.json"),
        ("modelo.json", "modelo.json"),
        ("modelo.JSON", "modelo.JSON"),
        ("modelo.v2", "modelo.v2.json"),
        ("  con espacios  ", "con espacios.json"),
        ("año ñoño", "año ñoño.json"),
    ],
)
def test_ruta_destino_anade_la_extension(tmp_path, nombre, esperado):
    assert ruta_destino(tmp_path, nombre) == tmp_path / esperado


def test_ruta_destino_con_carpeta_rara(carpeta_rara):
    ruta = ruta_destino(str(carpeta_rara), "modelo")
    assert ruta == carpeta_rara / "modelo.json"


def test_carpeta_valida(tmp_path):
    assert carpeta_valida(tmp_path) == tmp_path.resolve()
    assert carpeta_valida(str(tmp_path)) == tmp_path.resolve()
    assert carpeta_valida(tmp_path / "no_existe") == Path.home()
    assert carpeta_valida(None) == Path.home()


def test_listar_solo_carpetas_y_modelos(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "b.json").write_text("{}", encoding="utf-8")
    (tmp_path / "A.JSON").write_text("{}", encoding="utf-8")
    (tmp_path / "datos.csv").write_text("x\n1\n", encoding="utf-8")
    (tmp_path / ".oculto.json").write_text("{}", encoding="utf-8")

    entradas = listar_carpeta(tmp_path, es_modelo)

    assert [r.name for r in entradas] == ["sub", "A.JSON", "b.json"]


def test_listar_sigue_filtrando_datasets_por_defecto(tmp_path):
    (tmp_path / "m.json").write_text("{}", encoding="utf-8")
    (tmp_path / "datos.csv").write_text("x\n1\n", encoding="utf-8")
    assert [r.name for r in listar_carpeta(tmp_path)] == ["datos.csv"]


# =============================================================================
# Lo que muestra el diálogo
# =============================================================================


def test_empieza_en_la_carpeta_con_el_nombre_propuesto(carpeta_rara):
    dialogo = DialogoGuardado(carpeta_rara, "modelo_pisos.json")
    assert dialogo.carpeta == carpeta_rara.resolve()
    assert dialogo.etiqueta_carpeta.text == str(carpeta_rara.resolve())
    assert dialogo.nombre.value == "modelo_pisos.json"
    assert dialogo.resultado is None


def test_carpeta_inicial_inexistente_empieza_en_la_personal(tmp_path):
    dialogo = DialogoGuardado(tmp_path / "borrada", "m.json")
    assert dialogo.carpeta == Path.home()


def test_lista_carpetas_y_modelos(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "viejo.json").write_text("{}", encoding="utf-8")
    (tmp_path / "datos.csv").write_text("x\n1\n", encoding="utf-8")

    dialogo = DialogoGuardado(tmp_path, "m.json")

    assert nombres_lista(dialogo) == ["..", "sub", "viejo.json"]


def test_carpeta_vacia_lo_dice(tmp_path):
    dialogo = DialogoGuardado(tmp_path, "m.json")
    assert "No hay carpetas ni modelos" in nombres_lista(dialogo)


def test_sin_aviso_no_se_ve(tmp_path):
    dialogo = DialogoGuardado(tmp_path, "m.json")
    assert not dialogo.aviso.visible


def test_con_aviso_se_ve(tmp_path):
    dialogo = DialogoGuardado(tmp_path, "m.json", aviso="Sin descripción")
    assert dialogo.aviso.visible
    assert dialogo.aviso.text == "Sin descripción"


def test_entrar_en_una_subcarpeta(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "dentro.json").write_text("{}", encoding="utf-8")
    dialogo = DialogoGuardado(tmp_path, "m.json")

    dialogo._abrir(tmp_path / "sub")

    assert dialogo.carpeta == tmp_path / "sub"
    assert "dentro.json" in nombres_lista(dialogo)


def test_pulsar_un_modelo_pone_su_nombre(tmp_path):
    (tmp_path / "viejo.json").write_text("{}", encoding="utf-8")
    dialogo = DialogoGuardado(tmp_path, "m.json")

    dialogo._abrir(tmp_path / "viejo.json")

    assert dialogo.nombre.value == "viejo.json"
    assert dialogo.carpeta == tmp_path.resolve()


def test_carpeta_sin_permiso_avisa_y_no_se_mueve(
    tmp_path, monkeypatch, avisos
):
    dialogo = DialogoGuardado(tmp_path, "m.json")

    def sin_permiso(*args):
        raise PermissionError

    monkeypatch.setattr(
        "sikorius.gui.componentes.dialogo_guardado.listar_carpeta",
        sin_permiso,
    )
    dialogo.mostrar(tmp_path / "bloqueada")

    assert dialogo.carpeta == tmp_path.resolve()
    assert avisos[0][1] == "negative"
    assert "Sin permiso" in avisos[0][0]


# =============================================================================
# Botón "Guardar"
# =============================================================================


def test_guardar_devuelve_la_ruta_con_extension(tmp_path, avisos):
    dialogo = DialogoGuardado(tmp_path, "")
    dialogo.nombre.set_value("mi modelo")

    asyncio.run(dialogo.aceptar())

    assert dialogo.resultado == tmp_path.resolve() / "mi modelo.json"
    assert avisos == []


def test_guardar_no_duplica_la_extension(tmp_path):
    dialogo = DialogoGuardado(tmp_path, "modelo.json")
    asyncio.run(dialogo.aceptar())
    assert dialogo.resultado.name == "modelo.json"


def test_guardar_en_carpeta_con_tildes_y_enie(carpeta_rara):
    dialogo = DialogoGuardado(carpeta_rara, "Modelo ñ")
    asyncio.run(dialogo.aceptar())
    assert dialogo.resultado == carpeta_rara.resolve() / "Modelo ñ.json"


def test_guardar_en_la_carpeta_a_la_que_se_navega(tmp_path):
    (tmp_path / "destino").mkdir()
    dialogo = DialogoGuardado(tmp_path, "m")
    dialogo.mostrar(tmp_path / "destino")
    asyncio.run(dialogo.aceptar())
    assert dialogo.resultado == tmp_path / "destino" / "m.json"


@pytest.mark.parametrize("nombre", ["", "   ", "a/b", "a:b"])
def test_nombre_no_valido_avisa_y_sigue_abierto(tmp_path, avisos, nombre):
    dialogo = DialogoGuardado(tmp_path, nombre)
    asyncio.run(dialogo.aceptar())
    assert dialogo.resultado is None
    assert len(avisos) == 1
    assert avisos[0][1] == "negative"


def test_nombre_de_una_carpeta_existente(tmp_path, avisos):
    (tmp_path / "carpeta.json").mkdir()
    dialogo = DialogoGuardado(tmp_path, "carpeta")
    asyncio.run(dialogo.aceptar())
    assert dialogo.resultado is None
    assert "carpeta" in avisos[0][0]


def test_archivo_nuevo_no_pide_confirmacion(tmp_path):
    preguntas = []
    dialogo = DialogoGuardado(
        tmp_path, "nuevo", preguntar=respuesta_fija(True, preguntas)
    )
    asyncio.run(dialogo.aceptar())
    assert preguntas == []
    assert dialogo.resultado is not None


def test_archivo_existente_pide_confirmacion(tmp_path):
    (tmp_path / "viejo.json").write_text("{}", encoding="utf-8")
    preguntas = []
    dialogo = DialogoGuardado(
        tmp_path, "viejo", preguntar=respuesta_fija(True, preguntas)
    )

    asyncio.run(dialogo.aceptar())

    assert len(preguntas) == 1
    titulo, mensaje, boton = preguntas[0]
    assert "ya existe" in titulo
    assert "viejo.json" in mensaje
    assert boton == "Sobrescribir"
    assert dialogo.resultado == tmp_path.resolve() / "viejo.json"


def test_archivo_existente_con_otras_mayusculas_en_la_extension(tmp_path):
    (tmp_path / "viejo.JSON").write_text("{}", encoding="utf-8")
    preguntas = []
    dialogo = DialogoGuardado(
        tmp_path, "viejo.JSON", preguntar=respuesta_fija(True, preguntas)
    )
    asyncio.run(dialogo.aceptar())
    assert len(preguntas) == 1


def test_no_sobrescribir_deja_el_dialogo_abierto(tmp_path):
    (tmp_path / "viejo.json").write_text("{}", encoding="utf-8")
    dialogo = DialogoGuardado(
        tmp_path, "viejo", preguntar=respuesta_fija(False, [])
    )

    asyncio.run(dialogo.aceptar())
    assert dialogo.resultado is None

    # Se puede elegir otro nombre sin cerrar
    dialogo.nombre.set_value("otro")
    asyncio.run(dialogo.aceptar())
    assert dialogo.resultado == tmp_path.resolve() / "otro.json"
    assert (tmp_path / "viejo.json").read_text(encoding="utf-8") == "{}"


def test_el_dialogo_no_escribe_nada(tmp_path):
    dialogo = DialogoGuardado(tmp_path, "m")
    asyncio.run(dialogo.aceptar())
    assert list(tmp_path.iterdir()) == []


# =============================================================================
# Botón "Cancelar"
# =============================================================================


def test_cancelar_no_elige_nada(tmp_path):
    dialogo = DialogoGuardado(tmp_path, "m")
    dialogo.cancelar()
    assert dialogo.resultado is None
    assert list(tmp_path.iterdir()) == []
