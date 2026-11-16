"""Panel para crear y evaluar el modelo de regresión lineal.

También muestra un modelo cargado de un archivo (historia #24): fórmula,
métricas y descripción, pero no el gráfico ni el botón de crear, porque
el archivo no tiene datos.
"""

import html
import math
from pathlib import Path

from nicegui import ui

from sikorius.gui.avisos import notificar_error, notificar_exito
from sikorius.gui.componentes import dialogo_guardado
from sikorius.gui.paneles.base import Panel
from sikorius.gui.tema import colores_columnas
from sikorius.nucleo import modelo
from sikorius.nucleo.errores import ErrorModelo, ErrorPersistencia
from sikorius.nucleo.persistencia import EXTENSION
from sikorius.nucleo.texto import formatear_numero

DECIMALES_METRICAS = 4

# Colores del gráfico: los mismos de la marca (ver tema.py)
COLOR_ENTRENAMIENTO = "#8b5cf6"
COLOR_TEST = "#7dd3fc"
COLOR_RECTA = "#eeeeee"
COLOR_TEXTO = "#c9c4e0"
COLOR_LINEAS = "rgba(255, 255, 255, 0.12)"
COLOR_FONDO_TOOLTIP = "#1b1730"
COLOR_TEXTO_CLARO = "#eeeeee"

AVISO_SIN_DESCRIPCION = (
    "El modelo no tiene descripción. Puedes guardarlo igualmente, pero "
    "después será más difícil saber para qué se creó."
)


def texto_metrica(valor):
    """Ejemplo: "0.9816". Si no se puede calcular, "no calculable"."""
    if math.isnan(valor):
        return "no calculable"
    return formatear_numero(valor, DECIMALES_METRICAS)


def _formula(mod, marcar):
    """Construye la fórmula en una sola línea, lista para mostrar.

    ``marcar`` es la función que recibe el nombre de una columna y devuelve
    cómo se escribe: tal cual (texto) o con su color (HTML).

    Dentro de cada término los espacios son "espacios duros" (\u00a0): si la
    fórmula no cabe y se parte en varias líneas, solo se parte entre términos
    y nunca deja un signo solo al final de una línea.
    """
    duro = "\u00a0"
    terminos = []
    for posicion, (negativo, numero, columna) in enumerate(
        modelo.terminos_formula(mod)
    ):
        cuerpo = numero
        if columna is not None:
            cuerpo += duro + "·" + duro + marcar(str(columna))
        if posicion == 0:
            # El primer término lleva el signo pegado, solo si es negativo
            signo = "−" if negativo else ""
        else:
            signo = ("−" if negativo else "+") + duro
        terminos.append(signo + cuerpo)
    return marcar(str(mod.target)) + " = " + " ".join(terminos)


def _sin_marcar(nombre):
    return nombre


def texto_formula(mod):
    """La fórmula del modelo en una sola línea y sin colores.

    Ejemplo: ``y = 2.0000 · x1 − 3.0000 · x2 + 5.0000``.
    """
    return _formula(mod, _sin_marcar)


def html_formula(mod, colores):
    """La misma fórmula en HTML, con cada columna de su color.

    ``colores`` es {nombre de columna: color}. Los nombres vienen del
    usuario, así que se escapan: un nombre como ``<b>`` se ve tal cual y no
    se interpreta como HTML.
    """

    def marcar(nombre):
        seguro = html.escape(nombre)
        color = colores.get(nombre)
        if color is None:
            return seguro
        return (
            '<span style="color: '
            + color
            + '; font-weight: 700">'
            + seguro
            + "</span>"
        )

    return _formula(mod, marcar)


def _dimensiones(datos):
    """Nombres de las dos coordenadas de cada punto, para el tooltip."""
    return [str(datos["etiqueta_x"]), str(datos["etiqueta_y"])]


def _puntos(par):
    """Pareja (xs, ys) como lista de [x, y], que es lo que lee ECharts."""
    return [
        [x, y] for x, y in zip(par[0].tolist(), par[1].tolist(), strict=True)
    ]


def _eje(nombre, vertical):
    """Eje numérico. El nombre del eje vertical va horizontal, encima del
    eje: a su lado van las cifras, y como cambian de largo según el
    modelo, un nombre allí acabaría pisándolas."""
    if vertical:
        nombre_eje = {
            "nameLocation": "end",
            "nameGap": 14,
            "nameTextStyle": {"color": COLOR_TEXTO, "align": "left"},
        }
    else:
        nombre_eje = {
            "nameLocation": "middle",
            "nameGap": 32,
            "nameTextStyle": {"color": COLOR_TEXTO},
        }
    return {
        "type": "value",
        "name": str(nombre),
        **nombre_eje,
        "scale": True,  # no obliga a que el eje empiece en 0
        "axisLabel": {"color": COLOR_TEXTO},
        "axisLine": {"lineStyle": {"color": COLOR_LINEAS}},
        "splitLine": {"lineStyle": {"color": COLOR_LINEAS}},
    }


# Al pasar el ratón por un punto: nombre del conjunto y las dos coordenadas,
# cada una con el nombre de su eje. Es JavaScript (la clave empieza por ":"
# para que NiceGUI lo envíe como función y no como texto). Los nombres de
# los ejes llegan en "dimensionNames", que sale de "dimensions" de la serie.
JS_TOOLTIP = """
(punto) => {
    const numero = (v) => Number(v).toLocaleString(
        'en-US', {maximumFractionDigits: 4}
    );
    return '<b>' + punto.seriesName + '</b><br/>'
        + punto.dimensionNames[0] + ': ' + numero(punto.value[0]) + '<br/>'
        + punto.dimensionNames[1] + ': ' + numero(punto.value[1]);
}
"""


def opciones_grafico(datos):
    """Opciones de ECharts para el gráfico del ajuste.

    Args:
        datos: Diccionario devuelto por ``modelo.datos_ajuste``.

    Returns:
        Diccionario de opciones para ``ui.echart``.
    """
    return {
        "backgroundColor": "transparent",
        "tooltip": {
            "trigger": "item",
            ":formatter": JS_TOOLTIP,
            "backgroundColor": COLOR_FONDO_TOOLTIP,
            "borderColor": COLOR_LINEAS,
            "textStyle": {"color": COLOR_TEXTO_CLARO},
        },
        "legend": {
            "top": 0,
            "textStyle": {"color": COLOR_TEXTO},
        },
        "grid": {
            "left": 16,
            "right": 24,
            "top": 72,
            "bottom": 40,
            "containLabel": True,
        },
        "xAxis": _eje(datos["etiqueta_x"], vertical=False),
        "yAxis": _eje(datos["etiqueta_y"], vertical=True),
        "series": [
            {
                "name": "Entrenamiento",
                "dimensions": _dimensiones(datos),
                "type": "scatter",
                "symbolSize": 9,
                "itemStyle": {"color": COLOR_ENTRENAMIENTO},
                "data": _puntos(datos["entrenamiento"]),
            },
            {
                "name": "Test",
                "dimensions": _dimensiones(datos),
                "type": "scatter",
                "symbol": "diamond",
                "symbolSize": 11,
                "itemStyle": {"color": COLOR_TEST},
                "data": _puntos(datos["test"]),
            },
            {
                "name": datos["etiqueta_recta"],
                "dimensions": _dimensiones(datos),
                "type": "line",
                "showSymbol": False,
                "lineStyle": {"type": "dashed", "color": COLOR_RECTA},
                "itemStyle": {"color": COLOR_RECTA},
                "data": _puntos(datos["recta"]),
            },
        ],
    }


def destino_inicial(sesion):
    """Carpeta y nombre que propone el diálogo de guardado.

    - Si el modelo ya se guardó, el mismo archivo (para volver a
      guardarlo hay que confirmar que se sobrescribe).
    - Si no, la carpeta del dataset y "modelo_<nombre del dataset>.json".
    - Sin dataset, la carpeta personal y "modelo.json".

    Returns:
        Tupla (carpeta como ``Path``, nombre del archivo).
    """
    if sesion.ruta_modelo is not None:
        ruta = Path(sesion.ruta_modelo)
        return ruta.parent, ruta.name
    if sesion.dataset is not None:
        ruta = Path(sesion.dataset.ruta)
        return ruta.parent, "modelo_" + ruta.stem + EXTENSION
    return Path.home(), "modelo" + EXTENSION


def texto_estado_guardado(sesion):
    """Si el modelo actual está guardado y dónde, o "" si no hay modelo.

    Ejemplos: "Sin guardar", "Guardado en /ruta/modelo.json" o "Cambios
    sin guardar (guardado antes en /ruta/modelo.json)".
    """
    if sesion.modelo is None:
        return ""
    if sesion.ruta_modelo is None:
        return "Sin guardar"
    if sesion.modelo_sin_guardar:
        return (
            "Cambios sin guardar (guardado antes en %s)" % sesion.ruta_modelo
        )
    return "Guardado en " + sesion.ruta_modelo


def aviso_antes_de_guardar(mod):
    """Aviso del diálogo de guardado si falta la descripción, o None."""
    descripcion = mod.descripcion
    if descripcion is None or descripcion.strip() == "":
        return AVISO_SIN_DESCRIPCION
    return None


class PanelModelo(Panel):
    """Botón de creación, fórmula, métricas y gráfico de ajuste."""

    def __init__(self, sesion):
        with ui.card().classes("w-full"):
            ui.label("Modelo").classes("text-lg font-semibold")
            self.aviso = ui.label("").classes("text-sm opacity-70")
            with ui.row().classes("items-center gap-2"):
                self.boton = ui.button("Crear modelo", on_click=self.crear)
                self.boton_guardar = ui.button(
                    "Guardar modelo", icon="save", on_click=self.guardar
                ).props("outline")
                self.estado_guardado = ui.label("").classes(
                    "text-sm opacity-70 break-all"
                )

            self.resultados = ui.column().classes("w-full mt-4 gap-6")
            with self.resultados:
                # La fórmula ocupa todo el ancho para que quepa en una línea
                self.formula = ui.html("", sanitize=False).classes(
                    "text-xl text-center w-full break-words"
                )
                # Mitad izquierda: gráfico. Mitad derecha: las métricas,
                # centradas. "basis-0 grow" reparte el ancho a partes
                # iguales y "min-w-0" deja encoger cada mitad.
                with ui.row().classes("w-full items-center no-wrap gap-6"):
                    self.grafico = ui.echart(
                        {"xAxis": {}, "yAxis": {}, "series": []}
                    ).classes("basis-0 grow min-w-0 h-96")
                    with ui.column().classes(
                        "basis-0 grow min-w-0 items-center gap-8"
                    ):
                        # Una tarjeta por conjunto:
                        # {"entrenamiento": (R², ECM), ...}
                        self.metricas = {}
                        with ui.row().classes("gap-4 justify-center"):
                            for clave, titulo in (
                                ("entrenamiento", "Entrenamiento"),
                                ("test", "Test"),
                            ):
                                self.metricas[clave] = self._tarjeta(titulo)

                self.descripcion = ui.textarea(
                    label="Descripción (opcional)",
                    placeholder="En qué consiste el modelo y para qué se creó",
                    on_change=self._cambiar_descripcion,
                ).classes("w-full")
                self.descripcion.props("autogrow")

        # Modelo que se ve ahora. La sesión avisa también por cambios que
        # no son del modelo (por ejemplo, al guardarlo), y redibujar el
        # gráfico en cada aviso sería lento y no cambiaría nada.
        self._mostrado = None
        # True mientras el diálogo de guardado está abierto: un segundo clic
        # en "Guardar modelo" no abre otro diálogo encima.
        self._guardando = False
        super().__init__(sesion)

    @staticmethod
    def _tarjeta(titulo):
        """Tarjeta con las métricas de un conjunto.

        Returns:
            Tupla (etiqueta del R², etiqueta del ECM) para rellenarlas.
        """
        with (
            ui.card()
            .props("flat bordered")
            .classes("items-center gap-0 px-6 py-4 bg-white/5")
        ):
            ui.label(titulo).classes("text-lg font-semibold text-secondary")
            ui.label("R²").classes("text-xs opacity-70 mt-2")
            r2 = ui.label("").classes("text-2xl font-bold")
            ui.label("ECM").classes("text-xs opacity-70 mt-2")
            ecm = ui.label("").classes("text-lg break-all")
        return r2, ecm

    def actualizar(self):
        """Habilita/deshabilita la creación y muestra el modelo."""
        # Con un modelo cargado no hay datos: no se puede crear otro
        cargado = self.sesion.modelo_cargado
        self.boton.set_visibility(not cargado)
        motivo = self.sesion.motivo_no_crear_modelo()
        if cargado:
            self.aviso.set_visibility(False)
            self.boton.disable()
        elif motivo is not None:
            self.aviso.set_text(motivo)
            self.aviso.set_visibility(True)
            self.boton.disable()
        else:
            self.aviso.set_visibility(False)
            self.boton.enable()

        if self.sesion.modelo is not None:
            if self.sesion.modelo is not self._mostrado:
                self._mostrar_resultados()
                self._mostrado = self.sesion.modelo
            self.resultados.set_visibility(True)
        else:
            self._mostrado = None
            self.resultados.set_visibility(False)

        if self.sesion.modelo is not None and not self._guardando:
            self.boton_guardar.enable()
        else:
            self.boton_guardar.disable()
        self._mostrar_estado_guardado()

    def _mostrar_estado_guardado(self):
        texto = texto_estado_guardado(self.sesion)
        self.estado_guardado.set_text(texto)
        self.estado_guardado.set_visibility(texto != "")

    def _mostrar_resultados(self):
        """Escribe la fórmula y las métricas y dibuja el gráfico.

        De un modelo cargado no hay gráfico: el archivo no tiene datos.
        """
        mod = self.sesion.modelo
        cargado = self.sesion.modelo_cargado

        # Cada columna con el color que tiene en los selectores y la tabla.
        # Un modelo cargado no tiene dataset: se usan sus propias columnas.
        if cargado:
            columnas = list(mod.features) + [mod.target]
        else:
            columnas = self.sesion.dataset.datos.columns
        colores = colores_columnas(columnas)
        self.formula.set_content(html_formula(mod, colores))

        metricas = self.sesion.metricas_modelo()
        for clave, (r2, ecm) in self.metricas.items():
            r2.set_text(texto_metrica(metricas[clave]["r2"]))
            ecm.set_text(texto_metrica(metricas[clave]["ecm"]))

        # La descripción es del modelo, no del campo: al cambiar de modelo
        # (o al recargar la página) el campo muestra la del modelo actual.
        if self.descripcion.value != mod.descripcion:
            self.descripcion.set_value(mod.descripcion)

        self.grafico.set_visibility(not cargado)
        if cargado:
            return
        entrenamiento, test = self.sesion.conjuntos_actuales()
        datos = modelo.datos_ajuste(mod, entrenamiento, test)
        self.grafico.options.update(opciones_grafico(datos))
        self.grafico.update()

    def _cambiar_descripcion(self, evento):
        """Cada cambio del campo se guarda en la descripción del modelo."""
        mod = self.sesion.modelo
        if mod is None or evento.value == mod.descripcion:
            return
        self.sesion.guardar_descripcion(evento.value)
        # La sesión no avisa por la descripción (se escribe letra a letra):
        # el estado de guardado se actualiza aquí.
        self._mostrar_estado_guardado()

    def crear(self):
        """Crea el modelo. Si falla, la sesión no cambia y se avisa."""
        try:
            self.sesion.crear_modelo()
        except ErrorModelo as error:
            notificar_error(error)
            return
        notificar_exito("Modelo creado correctamente.")

    async def guardar(self):
        """Pide la ruta con el diálogo y guarda el modelo en ella.

        Si el usuario cierra el diálogo no pasa nada. Si el guardado falla
        se muestra el error y se puede volver a intentar.
        """
        if self._guardando:
            return  # ya hay un diálogo de guardado abierto
        mod = self.sesion.modelo
        if mod is None:
            notificar_error("Crea primero el modelo para poder guardarlo.")
            return
        self._guardando = True
        self.boton_guardar.disable()
        try:
            carpeta, nombre = destino_inicial(self.sesion)
            ruta = await dialogo_guardado.elegir_ruta_guardado(
                carpeta, nombre, aviso_antes_de_guardar(mod)
            )
        finally:
            self._guardando = False
            self.actualizar()
        if ruta is None:
            return  # el usuario cerró el diálogo: no se guarda nada
        if self.sesion.modelo is not mod:
            # Desde otra pestaña se puede cambiar o borrar el modelo con el
            # diálogo abierto: no se guarda uno distinto del que se veía.
            notificar_error(
                "El modelo ha cambiado mientras elegías el archivo. "
                "Revísalo y vuelve a guardarlo."
            )
            return
        try:
            guardada = self.sesion.guardar_modelo(ruta)
        except ErrorPersistencia as error:
            notificar_error(error)
            return
        notificar_exito("Modelo guardado en " + str(guardada))
