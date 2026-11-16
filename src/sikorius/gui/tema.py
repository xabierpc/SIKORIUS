"""Colores de la interfaz: tema oscuro con morado y azul claro de marca.

Todos los tonos están aquí para cambiarlos en un solo sitio. Quasar usa
``primary`` para la cabecera, los botones y los campos activos, y
``positive``, ``negative``, ``warning`` e ``info`` para las notificaciones.
``dark`` es el color de las tarjetas y ``dark_page`` el del fondo.
"""

from pathlib import Path

from nicegui import app, ui

# Carpeta con la fuente y el logo; se sirve en /recursos
CARPETA_RECURSOS = Path(__file__).parent / "recursos"

COLORES = {
    "primary": "#8b5cf6",  # morado de marca: botones, pestaña activa, foco
    "secondary": "#7dd3fc",  # azul claro de marca: títulos y detalles
    "accent": "#c4b5fd",  # lavanda, para resaltar algo puntual
    "dark": "#1b1730",  # tarjetas
    "dark_page": "#0f0c1d",  # fondo de la página
    "positive": "#34d399",
    "negative": "#f87171",
    "warning": "#fbbf24",
    "info": "#7dd3fc",
}

# Colores del gráfico del ajuste. Los puntos usan los dos colores de marca.
COLORES_GRAFICO = {
    "entrenamiento": COLORES["primary"],
    "test": COLORES["secondary"],
    "recta": "#eeeeee",
    "texto": "#c9c4e0",
    "texto_claro": "#eeeeee",
    "lineas": "rgba(255, 255, 255, 0.12)",
    "fondo_tooltip": COLORES["dark"],
}

# Un color por columna, para reconocerla de un vistazo en los selectores, en
# la tabla y en la fórmula. Son tonos claros que se distinguen sobre el fondo
# oscuro y que no se parecen al morado de marca. Cada columna toma el de su
# posición en el dataset (si hay más columnas que colores, se repiten), así
# su color no cambia al elegir o quitar otras.
PALETA_COLUMNAS = (
    "#38bdf8",  # azul
    "#34d399",  # verde
    "#fbbf24",  # ámbar
    "#fb7185",  # rosa fuerte
    "#fb923c",  # naranja
    "#2dd4bf",  # turquesa
    "#f472b6",  # rosa
    "#a3e635",  # lima
)


def colores_columnas(columnas):
    """Diccionario {nombre de columna: color} con el color de cada una."""
    colores = {}
    for posicion, nombre in enumerate(columnas):
        colores[str(nombre)] = PALETA_COLUMNAS[posicion % len(PALETA_COLUMNAS)]
    return colores


def tinte(color, opacidad):
    """Versión casi transparente de un color "#rrggbb", para teñir fondos.

    Ejemplo: tinte("#38bdf8", 0.2) -> "rgba(56, 189, 248, 0.2)".
    """
    rojo = int(color[1:3], 16)
    verde = int(color[3:5], 16)
    azul = int(color[5:7], 16)
    return (
        "rgba("
        + str(rojo)
        + ", "
        + str(verde)
        + ", "
        + str(azul)
        + ", "
        + str(opacidad)
        + ")"
    )


# Todo el CSS propio de la interfaz está en recursos/estilos.css: la fuente
# Forque de los títulos, la cabecera de la tabla, la animación de las
# pestañas y la del botón de inicio.
CSS_TEMA = (CARPETA_RECURSOS / "estilos.css").read_text(encoding="utf-8")

_recursos_publicados = False


def _publicar_recursos():
    """Sirve la carpeta de recursos en /recursos (basta hacerlo una vez)."""
    global _recursos_publicados
    if not _recursos_publicados:
        app.add_static_files("/recursos", CARPETA_RECURSOS)
        _recursos_publicados = True


def aplicar_tema():
    """Activa el modo oscuro, los colores y la fuente en la página que se
    construye."""
    _publicar_recursos()
    ui.dark_mode(True)
    ui.colors(**COLORES)
    ui.add_css(CSS_TEMA)
