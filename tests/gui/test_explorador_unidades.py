"""Unidades de disco de Windows en el explorador de archivos.

En Linux y macOS no hay unidades; en Windows hay un botón por unidad para
poder pasar de C: a D:. Los tests simulan Windows, así que pasan en
cualquier sistema.
"""

import asyncio
from pathlib import Path

from nicegui import ui

from sikorius.gui.componentes import explorador_archivos as explorador


def test_sin_windows_no_hay_unidades(monkeypatch):
    monkeypatch.setattr(explorador, "_es_windows", lambda: False)
    assert explorador.unidades_disponibles() == []


def test_en_windows_devuelve_las_unidades_que_existen(monkeypatch):
    monkeypatch.setattr(explorador, "_es_windows", lambda: True)
    monkeypatch.setattr(Path, "exists", lambda self: str(self)[0] in "CD")
    unidades = explorador.unidades_disponibles()
    assert [str(u) for u in unidades] == ["C:\\", "D:\\"]


def test_en_windows_sin_unidades(monkeypatch):
    monkeypatch.setattr(explorador, "_es_windows", lambda: True)
    monkeypatch.setattr(Path, "exists", lambda self: False)
    assert explorador.unidades_disponibles() == []


def test_nombre_unidad():
    assert explorador.nombre_unidad(Path("C:\\")) == "C:"
    assert explorador.nombre_unidad("D:\\") == "D:"


# =============================================================================
# El diálogo: se abre en otra tarea, como al pulsar "Cargar dataset"
# =============================================================================


def _botones(cliente, texto):
    return [
        e
        for e in cliente.elements.values()
        if isinstance(e, ui.button) and e.text == texto
    ]


def _num_botones(cliente):
    return len(
        [e for e in cliente.elements.values() if isinstance(e, ui.button)]
    )


def _etiquetas(cliente):
    return [
        e.text for e in cliente.elements.values() if isinstance(e, ui.label)
    ]


def _pulsar(boton):
    for oyente in boton._event_listeners.values():
        if oyente.type == "click":
            oyente.handler(None)


def _ejecutar(contenedor, prueba):
    """Ejecuta la prueba asíncrona dentro de un contenedor: los tests no
    tienen página y NiceGUI necesita saber dónde crear los elementos."""

    async def principal():
        with contenedor:
            return await prueba()

    return asyncio.run(principal())


def _abrir_explorador(contenedor, carpeta):
    """Abre el explorador en otra tarea, como hace la página al pulsar
    "Cargar dataset" (cada tarea necesita entrar en el contenedor)."""

    async def abrir():
        with contenedor:
            return await explorador.seleccionar_archivo(carpeta)

    return asyncio.ensure_future(abrir())


def test_cada_boton_abre_su_unidad(monkeypatch, tmp_path):
    """Con dos unidades, cada botón abre la suya (y no la última)."""
    unidad_c = tmp_path / "C"
    unidad_d = tmp_path / "D"
    unidad_c.mkdir()
    unidad_d.mkdir()
    monkeypatch.setattr(
        explorador, "unidades_disponibles", lambda: [unidad_c, unidad_d]
    )
    monkeypatch.setattr(explorador, "nombre_unidad", lambda u: u.name + ":")
    contenedor = ui.column()
    cliente = contenedor.client

    async def prueba():
        tarea = _abrir_explorador(contenedor, Path.home())
        await asyncio.sleep(0)
        assert len(_botones(cliente, "C:")) == 1
        assert len(_botones(cliente, "D:")) == 1

        _pulsar(_botones(cliente, "C:")[-1])
        assert str(unidad_c) in _etiquetas(cliente)
        _pulsar(_botones(cliente, "D:")[-1])
        assert str(unidad_d) in _etiquetas(cliente)

        _pulsar(_botones(cliente, "Cancelar")[-1])
        return await tarea

    assert _ejecutar(contenedor, prueba) is None


def test_sin_unidades_no_hay_botones_de_unidad(monkeypatch, tmp_path):
    monkeypatch.setattr(explorador, "unidades_disponibles", lambda: [])
    contenedor = ui.column()
    cliente = contenedor.client

    async def prueba():
        antes = _num_botones(cliente)
        tarea = _abrir_explorador(contenedor, tmp_path)
        await asyncio.sleep(0)
        nuevos = _num_botones(cliente) - antes
        _pulsar(_botones(cliente, "Cancelar")[-1])
        await tarea
        return nuevos

    # Solo los de siempre: "carpeta personal" y "Cancelar"
    assert _ejecutar(contenedor, prueba) == 2
