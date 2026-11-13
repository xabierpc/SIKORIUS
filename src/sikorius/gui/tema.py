"""Colores de la interfaz: tema oscuro con morado y azul claro de marca.

Todos los tonos están aquí para cambiarlos en un solo sitio. Quasar usa
``primary`` para la cabecera, los botones y los campos activos, y
``positive``, ``negative``, ``warning`` e ``info`` para las notificaciones.
``dark`` es el color de las tarjetas y ``dark_page`` el del fondo.
"""

from nicegui import ui

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


def aplicar_tema():
    """Activa el modo oscuro y los colores en la página que se construye."""
    ui.dark_mode(True)
    ui.colors(**COLORES)
