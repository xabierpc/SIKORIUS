"""Arranque de la aplicación."""

from nicegui import ui


def main():
    """Arranca la interfaz gráfica en el navegador."""
    import sikorius.gui.pagina  # noqa: F401  registra la página "/"

    ui.run(title="SIKORIUS", reload=False)
