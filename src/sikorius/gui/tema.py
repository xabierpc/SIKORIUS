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


# Forque (de Tup Wanders, licencia SIL OFL: ver recursos/fuentes/OFL.txt) es
# la fuente del logo. Solo tiene mayúsculas, sin tildes ni Ñ y sin paréntesis
# ni barras, así que se usa únicamente en textos fijos nuestros (títulos de
# paneles, pestañas y el nombre de la barra), todos escritos sin tildes, y
# siempre en mayúsculas. Los títulos son las etiquetas "text-lg
# font-semibold" (y "text-xl font-bold" la de la barra). La fuente solo tiene
# un grosor: con "font-weight: 400" el navegador no la engorda por su cuenta.
CSS_TEMA = """
@font-face {
    font-family: 'Forque';
    font-weight: 400;
    font-display: swap;
    src: url('/recursos/fuentes/Forque.ttf') format('truetype');
}
.text-lg.font-semibold, .text-xl.font-bold, .q-tab__label {
    font-family: 'Forque', sans-serif;
    font-weight: 400;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.text-lg.font-semibold { font-size: 1.35rem; line-height: 1.2; }
.text-xl.font-bold { font-size: 1.8rem; line-height: 1; }
.q-tab__label { font-size: 1.1rem; line-height: 1.2; }

/* Cabecera de la tabla de datos (opaca: las filas pasan por debajo). Lleva
   la fuente normal: los nombres de columna son del usuario y pueden tener
   tildes, Ñ o símbolos que Forque no trae. */
.sk-tabla thead tr th {
    background-color: #3f2d75 !important;
    color: #ffffff;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    border-bottom: 2px solid #8b5cf6;
}
"""

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
