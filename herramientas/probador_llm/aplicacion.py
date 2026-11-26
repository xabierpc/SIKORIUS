"""Arranque y parada de SIKORIUS durante las pruebas.

La aplicación guarda una sola sesión mientras está en marcha (recargar la
página no la borra). Para que cada caso empiece con la aplicación recién
abierta, como pide el procedimiento PR-1, se para y se vuelve a arrancar.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LANZADOR = Path(__file__).parent / "lanzador.py"

# Segundos que se espera como máximo a que la aplicación responda
ESPERA_MAXIMA = 60


class ErrorArranque(Exception):
    """La aplicación no ha llegado a responder."""


def puerto_libre():
    """Pide al sistema un puerto libre."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conexion:
        conexion.bind(("127.0.0.1", 0))
        return conexion.getsockname()[1]


class Aplicacion:
    """Proceso de SIKORIUS en marcha.

    Attributes:
        raiz: Carpeta raíz del repositorio (donde se ejecuta la app).
        puerto: Puerto en el que escucha.
        registro: Archivo donde se guarda lo que escribe la aplicación.
        carpeta_personal: Carpeta que la aplicación ve como carpeta
            personal (donde empieza el explorador). None: la real.
    """

    def __init__(self, raiz, registro, carpeta_personal=None):
        self.raiz = Path(raiz)
        self.registro = Path(registro)
        self.carpeta_personal = carpeta_personal
        self.puerto = None
        self._proceso = None
        self._salida = None

    @property
    def url(self):
        return "http://127.0.0.1:" + str(self.puerto)

    def arrancar(self):
        """Arranca la aplicación y espera a que responda.

        Raises:
            ErrorArranque: Si no responde a tiempo o se cierra sola.
        """
        self.parar()
        self.puerto = puerto_libre()
        self.registro.parent.mkdir(parents=True, exist_ok=True)
        # Se cierra en parar(): el proceso escribe en él mientras dura
        self._salida = open(self.registro, "a", encoding="utf-8")  # noqa: SIM115
        # La carpeta personal de la aplicación es data/: así el explorador
        # de archivos empieza ahí y el agente no tiene que bajar desde la
        # carpeta personal real (ahorra unas 8 acciones por carga)
        entorno = dict(os.environ)
        # Si se lanza desde pytest (script generado), NiceGUI vería esta
        # variable y creería que está en sus propios tests
        entorno.pop("PYTEST_CURRENT_TEST", None)
        if self.carpeta_personal is not None:
            entorno["HOME"] = str(self.carpeta_personal)
            entorno["USERPROFILE"] = str(self.carpeta_personal)
        self._proceso = subprocess.Popen(
            # -P: no añade la carpeta del lanzador a sys.path, para que sus
            # vecinos (plan.py, datos.py...) no tapen otros módulos
            [sys.executable, "-P", str(LANZADOR), str(self.puerto)],
            cwd=self.raiz,
            stdout=self._salida,
            stderr=subprocess.STDOUT,
            env=entorno,
        )
        limite = time.monotonic() + ESPERA_MAXIMA
        while time.monotonic() < limite:
            if self._proceso.poll() is not None:
                raise ErrorArranque(
                    "La aplicación se ha cerrado al arrancar. Mira "
                    + str(self.registro)
                )
            if _responde(self.url):
                return
            time.sleep(0.3)
        self.parar()
        raise ErrorArranque("La aplicación no responde en " + self.url)

    @property
    def en_marcha(self):
        return self._proceso is not None and self._proceso.poll() is None

    def reiniciar(self):
        """Cierra la aplicación y la vuelve a abrir (sesión nueva)."""
        self.arrancar()

    def parar(self):
        """Cierra la aplicación si está en marcha."""
        if self._proceso is not None:
            if self._proceso.poll() is None:
                self._proceso.terminate()
                try:
                    self._proceso.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self._proceso.kill()
                    self._proceso.wait()
            self._proceso = None
        if self._salida is not None:
            self._salida.close()
            self._salida = None

    def __enter__(self):
        return self

    def __exit__(self, *excepcion):
        self.parar()


def _responde(url):
    try:
        with urllib.request.urlopen(url, timeout=1):
            return True
    except (urllib.error.URLError, OSError):
        return False
