"""Notificaciones comunes a todos los paneles.

Así todos los mensajes al usuario tienen el mismo aspecto y los tests pueden
interceptarlos sustituyendo ``ui.notify``.
"""

from nicegui import ui


def notificar_error(mensaje):
    """Mensaje rojo que se queda hasta que el usuario lo cierra."""
    ui.notify(
        str(mensaje), type="negative", multi_line=True, close_button="Cerrar"
    )


def notificar_aviso(mensaje):
    """Mensaje naranja: se puede seguir, pero conviene revisarlo."""
    ui.notify(
        str(mensaje), type="warning", multi_line=True, close_button="Cerrar"
    )


def notificar_exito(mensaje):
    """Mensaje verde que desaparece solo."""
    ui.notify(str(mensaje), type="positive", multi_line=True)
