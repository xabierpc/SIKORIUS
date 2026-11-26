"""Reproducción, sin LLM, de las acciones que hizo el agente.

Los scripts que genera ``generador.py`` usan esta clase: cada test es un
caso del plan con las acciones del agente (pulsar, escribir, elegir...) y
las comprobaciones de sus evidencias. No se llama a ningún LLM, así que se
ejecuta en segundos, sin clave y sin límites de uso.
"""

from probador_llm.agente import normalizar
from probador_llm.navegador import ErrorAccion, Navegador


class Reproductor:
    """La aplicación y el navegador compartidos por los tests generados.

    Los casos son aditivos, igual que al generarlos: la aplicación no se
    cierra entre tests salvo que el caso empezara con ella recién abierta.

    Attributes:
        aplicacion: ``Aplicacion`` en marcha.
        pagina: Página de Playwright.
        carpeta: Carpeta donde se guardan las capturas de cada caso.
        navegador: ``Navegador`` del caso actual.
    """

    def __init__(self, aplicacion, pagina, carpeta, fabrica=Navegador):
        self.aplicacion = aplicacion
        self.pagina = pagina
        self.carpeta = carpeta
        self._fabrica = fabrica
        self.navegador = None
        self._abierta = False

    def empezar(self, caso, reiniciar):
        """Prepara el inicio de un caso.

        Args:
            caso: Identificador del caso (para las capturas).
            reiniciar: True si el caso empezaba con la aplicación recién
                abierta. Si no, continúa con lo que dejó el caso anterior.
        """
        if reiniciar or not self._abierta or not self.aplicacion.en_marcha:
            self.reiniciar_aplicacion()
        self.navegador = self._fabrica(self.pagina, self.carpeta / caso)
        if not reiniciar:
            self.navegador.limpiar()
        self.navegador.observar()

    def reiniciar_aplicacion(self):
        """Cierra la aplicación y la vuelve a abrir."""
        self.aplicacion.reiniciar()
        self.pagina.goto(self.aplicacion.url)
        self.pagina.wait_for_load_state("networkidle")
        self.pagina.wait_for_timeout(1000)
        self._abierta = True

    def pulsar(self, texto):
        self._hacer(self.navegador.pulsar, texto)

    def escribir(self, campo, valor):
        self._hacer(self.navegador.escribir, campo, valor)

    def elegir(self, selector, opciones):
        self._hacer(self.navegador.elegir, selector, opciones)

    def tecla(self, nombre):
        self._hacer(self.navegador.tecla, nombre)

    def esperar(self, segundos):
        self._hacer(self.navegador.esperar, segundos)

    def comprobar(self, texto):
        """Comprueba que el texto se ha visto en la pantalla o en un mensaje.

        Vale cualquier momento del caso, porque los mensajes desaparecen a
        los pocos segundos.

        Raises:
            AssertionError: Si no se ha visto.
        """
        visto = normalizar(
            "\n".join(self.navegador.textos_vistos)
            + "\n"
            + "\n".join(self.navegador.mensajes)
        )
        if normalizar(texto) not in visto:
            raise AssertionError(
                'No aparece en pantalla: "'
                + texto
                + '". Mensajes de la aplicación: '
                + " | ".join(self.navegador.mensajes)
            )

    def _hacer(self, accion, *argumentos):
        try:
            accion(*argumentos)
        except ErrorAccion as error:
            raise AssertionError(str(error)) from error
        self.navegador.capturar(accion.__name__)
        self.navegador.observar()
