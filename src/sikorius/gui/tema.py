"""Colores de la interfaz.

Todos los tonos están aquí para cambiarlos en un solo sitio. Quasar usa
``primary`` para la cabecera, los botones y los campos activos, y
``positive``, ``negative``, ``warning`` e ``info`` para las notificaciones.
"""

from nicegui import ui

COLORES = {
    "primary": "#1f5f66",  # verde petróleo: cabecera, botones, foco
    "secondary": "#5a8a8f",
    "accent": "#d9944a",  # ámbar, para resaltar algo puntual
    "positive": "#2e7d55",
    "negative": "#b83a32",
    "warning": "#c98a12",
    "info": "#3b7597",
}

# Fondo de la página: gris verdoso muy claro para que las tarjetas blancas
# se distingan sin necesidad de bordes.
FONDO = "#eef2f1"


def aplicar_tema():
    """Aplica los colores a la página que se está construyendo."""
    ui.colors(**COLORES)
    ui.query("body").style("background-color: " + FONDO)
