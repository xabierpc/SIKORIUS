"""Estado del flujo de trabajo de SIKORIUS.

Guarda el resultado de cada paso (dataset, columnas, separación y
preprocesado) y, cuando cambia un paso, borra los posteriores porque ya no
corresponden. No importa NiceGUI: la interfaz se entera de los cambios
suscribiéndose con ``al_cambiar``.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from sikorius.nucleo import modelo, preprocesado
from sikorius.nucleo.columnas import resolver_columnas
from sikorius.nucleo.errores import ErrorModelo, ErrorPreprocesado

# Orden del flujo: cambiar un paso borra todos los que van detrás
PASOS = ("dataset", "seleccion", "separacion", "preprocesado", "modelo")


@dataclass(frozen=True, eq=False)
class Dataset:
    datos: pd.DataFrame
    ruta: str


@dataclass(frozen=True)
class Seleccion:
    features: tuple
    target: str

    @property
    def tipo_regresion(self):
        if len(self.features) == 1:
            return "simple"
        return "multiple"


@dataclass(frozen=True, eq=False)
class Separacion:
    entrenamiento: pd.DataFrame
    test: pd.DataFrame
    porcentaje_test: float
    semilla: int


@dataclass(frozen=True, eq=False)
class Preprocesado:
    entrenamiento: pd.DataFrame
    test: pd.DataFrame
    estrategia: str
    resumen: dict


class Sesion:
    """Resultado de cada paso del flujo y aviso de cambios a la interfaz."""

    def __init__(self):
        self.dataset = None
        self.seleccion = None
        self.separacion = None
        self.preprocesado = None
        self.modelo = None
        self._oyentes = []

    # --- Avisos ---

    def al_cambiar(self, funcion):
        """Llama a funcion() cada vez que cambie algún paso.

        Returns:
            Función sin argumentos que cancela la suscripción.
        """
        self._oyentes.append(funcion)

        def cancelar():
            if funcion in self._oyentes:
                self._oyentes.remove(funcion)

        return cancelar

    def _avisar(self):
        for funcion in list(self._oyentes):
            funcion()

    def _borrar_desde(self, paso):
        """Borra paso y todos los que van detrás en el flujo."""
        for nombre in PASOS[PASOS.index(paso) :]:
            setattr(self, nombre, None)

    # --- Pasos del flujo ---

    def cargar_dataset(self, datos, ruta):
        """Sustituye el dataset. Las columnas elegidas antes ya no valen."""
        self._borrar_desde("seleccion")
        self.dataset = Dataset(datos, str(Path(ruta).resolve()))
        self._avisar()

    def guardar_seleccion(self, features, target):
        """Guarda una selección ya validada. Obliga a repetir la separación."""
        self._borrar_desde("separacion")
        self.seleccion = Seleccion(tuple(features), target)
        self._avisar()

    def guardar_separacion(
        self, entrenamiento, test, porcentaje_test, semilla
    ):
        """Guarda los conjuntos y borra el preprocesado y el modelo."""
        self._borrar_desde("preprocesado")
        self.separacion = Separacion(
            entrenamiento, test, porcentaje_test, semilla
        )
        self._avisar()

    def aplicar_preprocesado(self, estrategia, constante=None):
        """Preprocesa los conjuntos de la separación actual.

        Raises:
            ErrorPreprocesado: Si faltan pasos previos o el preprocesado
                falla. En ese caso la sesión no cambia.
        """
        if self.seleccion is None:
            raise ErrorPreprocesado(
                "Confirma primero la selección de columnas."
            )
        if self.separacion is None:
            raise ErrorPreprocesado("Separa primero en entrenamiento y test.")
        entrenamiento, test, resumen = preprocesado.aplicar_preprocesado(
            self.separacion.entrenamiento,
            self.separacion.test,
            self.columnas_modelo(),
            estrategia,
            constante,
        )
        self._borrar_desde("preprocesado")
        self.preprocesado = Preprocesado(
            entrenamiento, test, estrategia, resumen
        )
        self._avisar()
        return resumen

    def crear_modelo(self):
        """Entrena el modelo con el entrenamiento actual y lo guarda.

        El modelo nuevo sustituye al anterior, si lo había.

        Returns:
            El ModeloLineal creado.

        Raises:
            ErrorModelo: Si faltan pasos previos, quedan valores
                inexistentes o el modelo no se puede ajustar. En ese caso
                la sesión no cambia.
        """
        motivo = self.motivo_no_crear_modelo()
        if motivo is not None:
            raise ErrorModelo(motivo)
        entrenamiento, _ = self.conjuntos_actuales()
        *features, target = self.columnas_modelo()
        self.modelo = modelo.entrenar_modelo(entrenamiento, features, target)
        self._avisar()
        return self.modelo

    def guardar_descripcion(self, texto):
        """Guarda la descripción del modelo actual.

        Raises:
            ErrorModelo: Si todavía no hay modelo.
        """
        if self.modelo is None:
            raise ErrorModelo("Crea primero el modelo para poder describirlo.")
        self.modelo.descripcion = "" if texto is None else str(texto)

    # --- Consultas ---

    def columnas_modelo(self):
        """Columnas reales de entrada seguidas de la de salida."""
        nombres = list(self.seleccion.features) + [self.seleccion.target]
        return resolver_columnas(self.dataset.datos, nombres)

    def conjuntos_actuales(self):
        """(entrenamiento, test) más recientes: preprocesados si los hay."""
        if self.preprocesado is not None:
            return self.preprocesado.entrenamiento, self.preprocesado.test
        return self.separacion.entrenamiento, self.separacion.test

    def detectar_nulos(self):
        """Nulos por columna en train y test, o None si aún no hay
        selección y separación."""
        if self.seleccion is None or self.separacion is None:
            return None
        entrenamiento, test = self.conjuntos_actuales()
        return preprocesado.detectar_nulos_conjuntos(
            entrenamiento, test, self.columnas_modelo()
        )

    def puede_crear_modelo(self):
        """True si hay separación y no quedan valores inexistentes."""
        deteccion = self.detectar_nulos()
        if deteccion is None:
            return False
        return not preprocesado.hay_nulos(deteccion)

    def motivo_no_crear_modelo(self):
        """Explica por qué todavía no se puede crear el modelo.

        Returns:
            El texto de lo que falta, o None si ya se puede crear.
        """
        if self.seleccion is None:
            return "Confirma primero la selección de columnas."
        if self.separacion is None:
            return "Separa primero en entrenamiento y test."
        if not self.puede_crear_modelo():
            return (
                "Quedan valores inexistentes en las columnas "
                "seleccionadas: trátalos con el preprocesado antes de "
                "crear el modelo."
            )
        return None