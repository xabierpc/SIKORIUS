from nicegui import ui

from sikorius.estado import estado
from sikorius.preprocesado import (
    ErrorPreprocesado,
    aplicar_al_estado,
    texto_resumen,
)


def crear_boton_preprocesado(obtener_estrategia, obtener_constante,
                             al_aplicar=None):
    """Crea el botón "Aplicar preprocesado".

    Args:
        obtener_estrategia: Función sin argumentos que devuelve la
            estrategia elegida.
        obtener_constante: Función sin argumentos que devuelve el valor
            constante escrito.
        al_aplicar: Función opcional que se ejecuta tras aplicarlo con
            éxito.

    Returns:
        El botón creado.
    """
    def aplicar():
        try:
            resumen = aplicar_al_estado(
                estado, obtener_estrategia(), obtener_constante()
            )
        except ErrorPreprocesado as error:
            ui.notify(str(error), type="negative", multi_line=True)
            return
        ui.notify(texto_resumen(resumen), type="positive", multi_line=True)
        if al_aplicar is not None:
            al_aplicar()

    return ui.button("Aplicar preprocesado", on_click=aplicar)