"""Pruebas de los paneles trabajando juntos, sin servidor.

Los paneles no se llaman entre ellos: cada uno está suscrito a la sesión.
Estos tests montan todos los paneles sobre la misma sesión y comprueban
que, al cambiar un paso, los demás se actualizan solos (antes eso dependía
de callbacks como ``al_separar`` o ``al_aplicar``).

uv run pytest tests/gui/test_pagina.py -v
"""

import pandas as pd
import pytest
from nicegui import ui

from sikorius.dominio.separacion import separar_datos
from sikorius.gui.componentes.selectores import plantilla_chip
from sikorius.gui.componentes.tabla_datos import (
    TablaDatos,
    dataframe_a_tabla,
    titulo_columna,
)
from sikorius.gui.pagina import TITULOS, Pestanas, construir_pagina
from sikorius.gui.paneles.panel_columnas import PanelColumnas
from sikorius.gui.paneles.panel_dataset import PanelDataset, alto_tabla
from sikorius.gui.paneles.panel_preprocesado import PanelPreprocesado
from sikorius.gui.paneles.panel_separacion import PanelSeparacion
from sikorius.gui.tema import PALETA_COLUMNAS, colores_columnas, tinte


@pytest.fixture(autouse=True)
def sin_avisos(monkeypatch):
    """Los ui.notify no se muestran: solo interesan los paneles."""
    monkeypatch.setattr(ui, "notify", lambda *args, **kwargs: None)


class Pagina:
    """Los mismos paneles que coloca construir_pagina, a mano para poder
    mirarlos desde el test."""

    def __init__(self, sesion):
        self.dataset = PanelDataset(sesion)
        self.columnas = PanelColumnas(sesion)
        self.separacion = PanelSeparacion(sesion)
        self.preprocesado = PanelPreprocesado(sesion)


def test_construir_pagina_no_falla_y_se_puede_repetir(sesion_separada):
    """Abrir dos pestañas (o recargar) sobre la misma sesión."""
    construir_pagina(sesion_separada)
    construir_pagina(sesion_separada)
    # La sesión avisa a los paneles de las dos páginas sin fallar
    sesion_separada.aplicar_preprocesado("media")
    assert sesion_separada.preprocesado.estrategia == "media"


def test_todo_el_flujo_sin_conectar_paneles(sesion, datos):
    pagina = Pagina(sesion)

    # Cargar: se llenan los selectores; separar aún no está disponible
    sesion.cargar_dataset(datos, "datos.csv")
    assert pagina.columnas.features.columnas == ["x1", "x2", "y"]
    assert not pagina.separacion.boton_separar.enabled

    # Confirmar columnas: se habilita la separación
    pagina.columnas.features.selector.set_value(["x1", "x2"])
    pagina.columnas.target.selector.set_value("y")
    pagina.columnas.confirmar()
    assert pagina.separacion.boton_separar.enabled
    assert not pagina.preprocesado.tabla.visible

    # Separar: el preprocesado detecta los nulos sin que nadie lo llame
    pagina.separacion.separar()
    assert pagina.preprocesado.tabla.visible
    assert pagina.preprocesado.controles.visible

    # Aplicar: ya se podría crear el modelo
    pagina.preprocesado.estrategia.set_value("media")
    pagina.preprocesado.aplicar()
    assert sesion.puede_crear_modelo()


def test_cargar_otro_dataset_limpia_los_pasos(sesion_separada, datos):
    pagina = Pagina(sesion_separada)

    sesion_separada.cargar_dataset(datos, "otro.csv")

    assert pagina.columnas.etiqueta_seleccion.text == ""
    assert pagina.separacion.etiqueta_resultado.text == ""
    assert not pagina.separacion.boton_separar.enabled
    assert not pagina.preprocesado.tabla.visible


def test_al_recargar_cada_panel_muestra_su_paso(sesion, datos):
    antes = Pagina(sesion)
    sesion.cargar_dataset(datos, "datos.csv")
    antes.columnas.features.selector.set_value(["x1", "x2"])
    antes.columnas.target.selector.set_value("y")
    antes.columnas.confirmar()
    antes.separacion.entrada_porcentaje.set_value("30")
    antes.separacion.entrada_semilla.set_value("7")
    antes.separacion.separar()
    antes.preprocesado.estrategia.set_value("mediana")
    antes.preprocesado.aplicar()

    despues = Pagina(sesion)  # F5

    assert despues.dataset.etiqueta_resumen.text == "10 filas y 3 columnas"
    assert despues.columnas.features.obtener_seleccion() == ["x1", "x2"]
    assert despues.columnas.target.obtener_seleccion() == "y"
    assert despues.separacion.entrada_porcentaje.value == "30"
    assert despues.separacion.entrada_semilla.value == "7"
    assert despues.preprocesado.estrategia.value == "mediana"
    assert despues.preprocesado.aplicado.text.startswith("Aplicado:")


# =============================================================================
# Pestañas con desbloqueo progresivo
# =============================================================================


def pestanas_activas(pestanas):
    return [e for e, p in pestanas.pestanas.items() if p.visible]


def test_pestanas_al_empezar_solo_datos(sesion):
    pestanas = Pestanas(sesion)
    assert pestanas_activas(pestanas) == ["datos"]
    assert pestanas.paneles.value == "datos"


def test_las_pestanas_bloqueadas_no_se_ven_y_se_animan(sesion):
    pestanas = Pestanas(sesion)
    assert not pestanas.pestanas["modelo"].visible
    for pestana in pestanas.pestanas.values():
        assert "sk-pestana" in pestana.classes


def test_pestanas_se_desbloquean_con_el_flujo(sesion, datos):
    pestanas = Pestanas(sesion)
    sesion.cargar_dataset(datos, "datos.csv")
    assert pestanas_activas(pestanas) == ["datos", "variables"]
    sesion.guardar_seleccion(["x1", "x2"], "y")
    entrenamiento, test = separar_datos(sesion.dataset.datos, 20, 42)
    sesion.guardar_separacion(entrenamiento, test, 20, 42)
    assert pestanas_activas(pestanas) == ["datos", "variables", "preprocesado"]
    sesion.aplicar_preprocesado("media")
    assert pestanas_activas(pestanas) == list(TITULOS)


def test_pestanas_si_se_cierra_la_que_se_ve_se_va_a_la_ultima_abierta(
    sesion_separada, datos
):
    sesion_separada.aplicar_preprocesado("media")
    pestanas = Pestanas(sesion_separada)
    pestanas.paneles.set_value("modelo")

    sesion_separada.cargar_dataset(datos, "otro.csv")

    assert pestanas.paneles.value == "variables"


def test_pestanas_no_mueven_al_usuario_si_su_pestana_sigue_abierta(
    sesion_separada,
):
    pestanas = Pestanas(sesion_separada)
    pestanas.paneles.set_value("preprocesado")

    sesion_separada.aplicar_preprocesado("media")

    assert pestanas.paneles.value == "preprocesado"


# =============================================================================
# Pantalla de inicio
# =============================================================================


def test_sin_dataset_se_ve_el_inicio_y_no_la_tabla(sesion):
    panel = PanelDataset(sesion)
    assert panel.inicio.visible
    assert not panel.contenido.visible
    assert panel.boton_cargar.text == "Subir dataset"


def test_al_cargar_un_dataset_el_inicio_desaparece(sesion, datos):
    panel = PanelDataset(sesion)

    sesion.cargar_dataset(datos, "datos.csv")

    assert not panel.inicio.visible
    assert panel.contenido.visible
    assert panel.etiqueta_resumen.text == "10 filas y 3 columnas"
    assert len(panel.tabla.tabla.rows) == 10


def test_al_recargar_con_dataset_no_se_ve_el_inicio(sesion, datos):
    sesion.cargar_dataset(datos, "datos.csv")

    panel = PanelDataset(sesion)  # F5

    assert not panel.inicio.visible
    assert panel.contenido.visible


def test_el_logo_se_incrusta_con_su_animacion(sesion):
    panel = PanelDataset(sesion)
    html = [e for e in panel.inicio if isinstance(e, ui.html)]
    assert len(html) == 1
    assert "<svg" in html[0].content
    assert "sk-morado" in html[0].content


def test_se_puede_cargar_otro_dataset_desde_la_tabla(sesion, datos):
    sesion.cargar_dataset(datos, "datos.csv")
    panel = PanelDataset(sesion)
    assert panel.boton_otro.text == "Cargar otro"
    sesion.cargar_dataset(datos.iloc[:4], "otro.csv")
    assert panel.etiqueta_resumen.text == "4 filas y 3 columnas"
    assert panel.contenido.visible


# =============================================================================
# Barra superior y tamaño de la tabla
# =============================================================================


def test_la_barra_no_se_ve_en_la_pantalla_de_inicio(sesion, datos):
    pestanas = Pestanas(sesion)
    assert not pestanas.header.value

    sesion.cargar_dataset(datos, "datos.csv")

    assert pestanas.header.value


def test_la_tabla_pequena_no_deja_hueco_debajo():
    # 10 filas + cabecera: 11 * 28.5 = 313.5 px, más los bordes
    assert alto_tabla(10) == "min(70vh, 317px)"


def test_la_tabla_grande_se_limita_al_70_por_ciento_de_la_pantalla():
    assert alto_tabla(20000).startswith("min(70vh, ")


# =============================================================================
# Tabla visual: títulos de columna y alineación
# =============================================================================


@pytest.mark.parametrize(
    "nombre, esperado",
    [
        ("metros_cuadrados", "Metros cuadrados"),
        ("precio", "Precio"),
        ("IVA", "IVA"),  # solo se toca la primera letra
        ("año_de_venta", "Año de venta"),
        ("_oculta", "Oculta"),
        (2020, "2020"),
        ("", ""),
    ],
)
def test_titulo_columna(nombre, esperado):
    assert titulo_columna(nombre) == esperado


def test_la_tabla_muestra_titulos_legibles_y_guarda_el_nombre_real():
    df = pd.DataFrame({"metros_cuadrados": [1.0], "precio": [2.0]})

    columnas, filas = dataframe_a_tabla(df)

    assert [c["label"] for c in columnas] == ["Metros cuadrados", "Precio"]
    assert [c["real"] for c in columnas] == ["metros_cuadrados", "precio"]
    # Los datos siguen enlazados por la clave interna, no por el título
    assert filas[0]["c0"] == 1.0
    assert filas[0]["c1"] == 2.0


def test_los_datos_de_la_tabla_van_centrados():
    columnas, _ = dataframe_a_tabla(pd.DataFrame({"a": [1], "b": ["x"]}))
    assert [c["align"] for c in columnas] == ["center", "center"]


# =============================================================================
# Color por columna elegida
# =============================================================================


def test_cada_columna_tiene_su_color_segun_su_posicion():
    colores = colores_columnas(["a", "b", "c"])
    assert colores == {
        "a": PALETA_COLUMNAS[0],
        "b": PALETA_COLUMNAS[1],
        "c": PALETA_COLUMNAS[2],
    }


def test_si_hay_mas_columnas_que_colores_se_repiten():
    nombres = [str(i) for i in range(len(PALETA_COLUMNAS) + 1)]
    colores = colores_columnas(nombres)
    assert colores[nombres[-1]] == PALETA_COLUMNAS[0]


def test_la_paleta_no_repite_colores():
    assert len(set(PALETA_COLUMNAS)) == len(PALETA_COLUMNAS)


def test_el_chip_usa_el_color_de_su_columna_y_escapa_los_nombres():
    plantilla = plantilla_chip({'hab"s': "#38bdf8"}, True)
    assert "#38bdf8" in plantilla
    assert 'hab"s' not in plantilla  # las comillas van escapadas
    assert "removable" in plantilla


def test_tinte_pasa_de_hex_a_rgba():
    assert tinte("#38bdf8", 0.2) == "rgba(56, 189, 248, 0.2)"


def test_la_tabla_tine_solo_las_columnas_indicadas(datos):
    tabla = TablaDatos()
    tabla.mostrar(datos)
    tabla.colorear({"x2": "#38bdf8"})
    por_nombre = {c["real"]: c for c in tabla.tabla.columns}
    assert "rgba(56, 189, 248" in por_nombre["x2"]["style"]
    assert por_nombre["x2"]["color"] == "#38bdf8"
    assert "style" not in por_nombre["x1"]
    tabla.colorear({})
    assert all("style" not in c for c in tabla.tabla.columns)


def colores_de_la_tabla(panel):
    """{columna: color} de las columnas teñidas de la tabla de datos."""
    return {
        c["real"]: c["color"]
        for c in panel.tabla.tabla.columns
        if "color" in c
    }


def test_la_tabla_de_datos_tine_las_columnas_confirmadas(sesion, datos):
    panel = PanelDataset(sesion)
    sesion.cargar_dataset(datos, "datos.csv")
    assert colores_de_la_tabla(panel) == {}

    sesion.guardar_seleccion(["x1", "x2"], "y")

    colores = colores_columnas(datos.columns)
    assert colores_de_la_tabla(panel) == colores


def test_la_tabla_de_datos_solo_tine_lo_elegido(sesion, datos):
    panel = PanelDataset(sesion)
    sesion.cargar_dataset(datos, "datos.csv")
    sesion.guardar_seleccion(["x2"], "y")
    assert set(colores_de_la_tabla(panel)) == {"x2", "y"}


def test_al_cargar_otro_dataset_se_quitan_los_colores(sesion, datos):
    panel = PanelDataset(sesion)
    sesion.cargar_dataset(datos, "datos.csv")
    sesion.guardar_seleccion(["x1"], "y")

    sesion.cargar_dataset(datos, "otro.csv")

    assert colores_de_la_tabla(panel) == {}


def test_al_recargar_la_pagina_la_tabla_ya_sale_teñida(sesion_separada):
    panel = PanelDataset(sesion_separada)
    assert colores_de_la_tabla(panel) != {}


def test_la_tabla_no_se_vuelve_a_enviar_si_los_colores_no_cambian(
    sesion, datos
):
    panel = PanelDataset(sesion)
    sesion.cargar_dataset(datos, "datos.csv")
    sesion.guardar_seleccion(["x1"], "y")
    columnas = panel.tabla.tabla.columns

    sesion._avisar()  # un aviso cualquiera de la sesión

    assert panel.tabla.tabla.columns is columnas


# =============================================================================
# Modelo cargado de un archivo (historia #24)
# =============================================================================


def guardar_modelo_de(sesion_separada, ruta):
    sesion_separada.aplicar_preprocesado("media")
    sesion_separada.crear_modelo()
    return sesion_separada.guardar_modelo(ruta)


def test_al_cargar_un_modelo_solo_quedan_datos_y_modelo(
    sesion, sesion_separada, tmp_path
):
    ruta = guardar_modelo_de(sesion_separada, tmp_path / "m.json")
    pestanas = Pestanas(sesion)

    sesion.cargar_modelo(ruta)

    assert pestanas_activas(pestanas) == ["datos", "modelo"]
    assert pestanas.paneles.value == "modelo"
    assert pestanas.header.value


def test_con_datos_cargar_un_modelo_oculta_las_secciones_de_datos(
    sesion_separada, tmp_path
):
    ruta = guardar_modelo_de(sesion_separada, tmp_path / "m.json")
    pestanas = Pestanas(sesion_separada)
    pestanas.paneles.set_value("variables")

    sesion_separada.cargar_modelo(ruta)

    assert pestanas_activas(pestanas) == ["datos", "modelo"]
    assert pestanas.paneles.value == "modelo"


def test_tras_cargar_el_usuario_puede_ir_a_datos(
    sesion, sesion_separada, tmp_path
):
    ruta = guardar_modelo_de(sesion_separada, tmp_path / "m.json")
    pestanas = Pestanas(sesion)
    sesion.cargar_modelo(ruta)
    pestanas.paneles.set_value("datos")

    # Guardar el modelo avisa a los paneles: no se vuelve a saltar
    sesion.guardar_modelo(tmp_path / "copia.json")

    assert pestanas.paneles.value == "datos"


def test_al_recargar_con_modelo_cargado_se_ve_el_modelo(
    sesion, sesion_separada, tmp_path
):
    sesion.cargar_modelo(
        guardar_modelo_de(sesion_separada, tmp_path / "m.json")
    )
    pestanas = Pestanas(sesion)  # F5
    assert pestanas.paneles.value == "modelo"
    assert pestanas.header.value


def test_cargar_un_dataset_vuelve_a_mostrar_las_secciones(
    sesion, sesion_separada, tmp_path, datos
):
    sesion.cargar_modelo(
        guardar_modelo_de(sesion_separada, tmp_path / "m.json")
    )
    pestanas = Pestanas(sesion)
    panel = PanelDataset(sesion)

    sesion.cargar_dataset(datos, "datos.csv")

    assert pestanas_activas(pestanas) == ["datos", "variables"]
    assert pestanas.paneles.value == "variables"
    assert panel.contenido.visible


def test_construir_pagina_con_modelo_cargado(
    sesion, sesion_separada, tmp_path
):
    sesion.cargar_modelo(
        guardar_modelo_de(sesion_separada, tmp_path / "m.json")
    )
    construir_pagina(sesion)
    sesion.guardar_descripcion("Otra")
    assert sesion.modelo_sin_guardar
