"""Diálogo de confirmación con dos botones: aceptar o cancelar."""

from nicegui import ui


async def confirmar(titulo, mensaje, texto_aceptar="Aceptar"):
    """Pregunta al usuario y espera a que conteste.

    Args:
        titulo: Texto en negrita de la cabecera.
        mensaje: Explicación de lo que va a pasar si acepta.
        texto_aceptar: Texto del botón que confirma.

    Returns:
        True si el usuario acepta. False si cancela o cierra el diálogo
        (Escape o clic fuera).
    """
    with ui.dialog() as dialogo, ui.card().classes("w-[450px] max-w-full"):
        ui.label(titulo).classes("text-lg font-semibold")
        ui.label(mensaje).classes("break-words")
        with ui.row().classes("w-full justify-end"):
            ui.button(
                "Cancelar", on_click=lambda: dialogo.submit(False)
            ).props("flat")
            ui.button(texto_aceptar, on_click=lambda: dialogo.submit(True))
    respuesta = await dialogo
    dialogo.delete()
    return respuesta is True
