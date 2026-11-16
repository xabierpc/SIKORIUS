"""Gráfico del ajuste del modelo (ECharts).

Convierte los datos que prepara ``Sesion.datos_ajuste`` (puntos de
entrenamiento y test y la recta) en las opciones de ``ui.echart``. Los
colores salen de ``tema.COLORES_GRAFICO``.
"""

from sikorius.gui.tema import COLORES_GRAFICO


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
            "nameTextStyle": {
                "color": COLORES_GRAFICO["texto"],
                "align": "left",
            },
        }
    else:
        nombre_eje = {
            "nameLocation": "middle",
            "nameGap": 32,
            "nameTextStyle": {"color": COLORES_GRAFICO["texto"]},
        }
    return {
        "type": "value",
        "name": str(nombre),
        **nombre_eje,
        "scale": True,  # no obliga a que el eje empiece en 0
        "axisLabel": {"color": COLORES_GRAFICO["texto"]},
        "axisLine": {"lineStyle": {"color": COLORES_GRAFICO["lineas"]}},
        "splitLine": {"lineStyle": {"color": COLORES_GRAFICO["lineas"]}},
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
        datos: Diccionario devuelto por ``Sesion.datos_ajuste``.

    Returns:
        Diccionario de opciones para ``ui.echart``.
    """
    return {
        "backgroundColor": "transparent",
        "tooltip": {
            "trigger": "item",
            ":formatter": JS_TOOLTIP,
            "backgroundColor": COLORES_GRAFICO["fondo_tooltip"],
            "borderColor": COLORES_GRAFICO["lineas"],
            "textStyle": {"color": COLORES_GRAFICO["texto_claro"]},
        },
        "legend": {
            "top": 0,
            "textStyle": {"color": COLORES_GRAFICO["texto"]},
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
                "itemStyle": {"color": COLORES_GRAFICO["entrenamiento"]},
                "data": _puntos(datos["entrenamiento"]),
            },
            {
                "name": "Test",
                "dimensions": _dimensiones(datos),
                "type": "scatter",
                "symbol": "diamond",
                "symbolSize": 11,
                "itemStyle": {"color": COLORES_GRAFICO["test"]},
                "data": _puntos(datos["test"]),
            },
            {
                "name": datos["etiqueta_recta"],
                "dimensions": _dimensiones(datos),
                "type": "line",
                "showSymbol": False,
                "lineStyle": {
                    "type": "dashed",
                    "color": COLORES_GRAFICO["recta"],
                },
                "itemStyle": {"color": COLORES_GRAFICO["recta"]},
                "data": _puntos(datos["recta"]),
            },
        ],
    }
