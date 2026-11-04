"""Base común de los paneles de la página."""

from nicegui import ui


class Panel:
    """Panel que se vuelve a pintar cada vez que cambia la sesión.

    Las subclases crean sus controles en ``__init__`` y al final llaman a
    ``super().__init__(sesion)``, que suscribe el panel a la sesión y lo
    pinta por primera vez. Así, al recargar la página, cada panel muestra lo
    que ya estaba hecho.

    Las subclases tienen que implementar ``actualizar``, que lee la sesión y
    pone los controles en el estado que corresponde. No recibe argumentos:
    se llama igual cambie el paso que cambie.
    """

    def __init__(self, sesion):
        self.sesion = sesion
        cancelar = sesion.al_cambiar(self.actualizar)
        # Al cerrar la pestaña, la sesión deja de avisar a este panel
        ui.context.client.on_delete(cancelar)
        self.actualizar()

    def actualizar(self):
        raise NotImplementedError
