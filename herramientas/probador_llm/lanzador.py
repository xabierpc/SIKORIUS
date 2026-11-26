"""Arranca SIKORIUS para las pruebas: sin abrir el navegador y en un puerto.

``sikorius.app.main`` llama a ``ui.run``, que abre una pestaña del navegador
del usuario y usa el puerto 8080. Aquí se cambia ``ui.run`` antes de llamar
a ``main`` para que no abra nada y use el puerto que se le pasa, sin tocar
el código de la aplicación.

Uso: python lanzador.py <puerto>
"""

import sys

from nicegui import ui


def main():
    puerto = int(sys.argv[1])
    original = ui.run

    def run(*args, **kwargs):
        kwargs["show"] = False
        kwargs["port"] = puerto
        kwargs["reload"] = False
        original(*args, **kwargs)

    ui.run = run

    from sikorius.app import main as main_sikorius

    main_sikorius()


if __name__ == "__main__":
    main()
