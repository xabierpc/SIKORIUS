"""Estado del flujo de trabajo de SIKORIUS.

Guarda el resultado de cada paso (dataset, columnas, separación y
preprocesado) y, cuando cambia un paso, borra los posteriores porque ya no
corresponden. También puede tener un modelo cargado de un archivo, sin
ningún dato (historia #24). No importa NiceGUI: la interfaz se entera de
los cambios suscribiéndose con ``al_cambiar``.
"""

import copy
from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

from sikorius.datos import importador, persistencia
from sikorius.dominio import modelo, prediccion, preprocesado, separacion
from sikorius.dominio.columnas import resolver_columnas, validar_seleccion
from sikorius.dominio.errores import (
    ErrorModelo,
    ErrorPersistencia,
    ErrorPreprocesado,
    ErrorSeleccion,
    ErrorSeparacion,
)

# Etapas de la interfaz (pestañas), en orden
ETAPAS = ("inicio", "datos", "variables", "preprocesado", "modelo")
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


@dataclass(frozen=True)
class ArchivoModelo:
    """Lo que la sesión sabe del archivo del modelo actual.

    Attributes:
        ruta: Archivo en el que se guardó el modelo por última vez, o None
            si todavía no se ha guardado.
        sin_guardar: True si el modelo ha cambiado desde entonces (un modelo
            recién creado aún no se ha guardado; cambiar la descripción
            también es un cambio).
        metricas: Métricas leídas del archivo de un modelo cargado. Un
            modelo cargado no tiene datos con los que recalcularlas; con
            uno creado es None.
    """

    ruta: str | None = None
    sin_guardar: bool = False
    metricas: dict | None = None


class Sesion:
    """Resultado de cada paso del flujo y aviso de cambios a la interfaz.

    El estado se lee con propiedades (``sesion.modelo``, ``sesion.dataset``…)
    pero solo se cambia con los métodos de cada paso. Así nadie se puede
    saltar el borrado de los pasos posteriores ni el aviso a la interfaz.
    """

    def __init__(self):
        self._dataset = None
        self._seleccion = None
        self._separacion = None
        self._preprocesado = None
        self._modelo = None
        self._archivo = ArchivoModelo()
        self._oyentes = []

    # --- Estado (solo lectura) ---

    @property
    def dataset(self):
        """Dataset cargado (``Dataset``) o None."""
        return self._dataset

    @property
    def seleccion(self):
        """Columnas confirmadas (``Seleccion``) o None."""
        return self._seleccion

    @property
    def separacion(self):
        """Conjuntos de entrenamiento y test (``Separacion``) o None."""
        return self._separacion

    @property
    def preprocesado(self):
        """Preprocesado aplicado (``Preprocesado``) o None."""
        return self._preprocesado

    @property
    def modelo(self):
        """Modelo actual (``ModeloLineal``) o None."""
        return self._modelo

    @property
    def ruta_modelo(self):
        """Archivo en el que se guardó el modelo por última vez, o None."""
        return self._archivo.ruta

    @property
    def modelo_sin_guardar(self):
        """True si el modelo actual tiene cambios que no están guardados."""
        return self._archivo.sin_guardar

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
        """Borra paso y todos los que van detrás en el flujo.

        Cada paso se borra con su propia línea (y no con ``setattr`` y el
        nombre en texto) para que, si se renombra un atributo, el error
        salte al momento en vez de dejar de borrarse sin avisar.
        """
        desde = PASOS.index(paso)  # ValueError si el paso no existe
        if desde <= PASOS.index("dataset"):
            self._dataset = None
        if desde <= PASOS.index("seleccion"):
            self._seleccion = None
        if desde <= PASOS.index("separacion"):
            self._separacion = None
        if desde <= PASOS.index("preprocesado"):
            self._preprocesado = None
        # El modelo va siempre detrás: cualquier cambio lo borra, y sin
        # modelo no hay nada que guardar
        self._modelo = None
        self._archivo = ArchivoModelo()

    # --- Pasos del flujo ---

    def importar_dataset(self, ruta):
        """Lee el archivo de datos y lo carga como dataset actual.

        Raises:
            ErrorImportacion: Si el archivo no se puede leer. En ese caso
                la sesión no cambia.
        """
        datos = importador.importar_datos(ruta)
        self.cargar_dataset(datos, ruta)

    def cargar_dataset(self, datos, ruta):
        """Sustituye el dataset. Las columnas elegidas antes ya no valen."""
        self._borrar_desde("seleccion")
        self._dataset = Dataset(datos, str(Path(ruta).resolve()))
        self._avisar()

    def confirmar_seleccion(self, features, target):
        """Valida la selección elegida en la interfaz y, si es correcta, la
        guarda.

        Raises:
            ErrorSeleccion: Si no hay dataset o la selección no es válida.
                En ese caso la sesión no cambia.
        """
        if self.dataset is None:
            raise ErrorSeleccion("Carga primero un dataset.")
        validar_seleccion(self.dataset.datos, features, target)
        self.guardar_seleccion(features, target)

    def guardar_seleccion(self, features, target):
        """Guarda una selección ya validada. Obliga a repetir la separación."""
        self._borrar_desde("separacion")
        self._seleccion = Seleccion(tuple(features), target)
        self._avisar()

    def guardar_separacion(
        self, entrenamiento, test, porcentaje_test, semilla
    ):
        """Guarda los conjuntos y borra el preprocesado y el modelo."""
        self._borrar_desde("preprocesado")
        self._separacion = Separacion(
            entrenamiento, test, porcentaje_test, semilla
        )
        self._avisar()

    def separar(self, texto_porcentaje, texto_semilla):
        """Separa el dataset con los valores escritos en el formulario.

        Interpreta el porcentaje de test y la semilla, separa y guarda los
        conjuntos.

        Raises:
            ErrorSeparacion: Si falta la selección de columnas, los valores
                no son válidos o no se puede separar. En ese caso la sesión
                no cambia.
        """
        if self.seleccion is None:
            raise ErrorSeparacion("Confirma primero la selección de columnas.")
        porcentaje = separacion.interpretar_porcentaje(texto_porcentaje)
        semilla = separacion.interpretar_semilla(texto_semilla)
        entrenamiento, test = separacion.separar_datos(
            self.dataset.datos, porcentaje, semilla
        )
        self.guardar_separacion(entrenamiento, test, porcentaje, semilla)

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
        self._preprocesado = Preprocesado(
            entrenamiento, test, estrategia, resumen
        )
        self._avisar()
        return resumen

    def preprocesar_y_crear_modelo(self, estrategia, constante=None):
        """Aplica el preprocesado y, con los datos ya tratados, crea el
        modelo.

        Returns:
            Tupla ``(resumen, error)``. ``resumen`` es el de
            ``aplicar_preprocesado``. ``error`` es None si el modelo se ha
            creado, o el ``ErrorModelo`` que explica por qué no: en ese
            caso el preprocesado sí se conserva.

        Raises:
            ErrorPreprocesado: Si el preprocesado no se puede aplicar (o
                ``AvisoPreprocesado``). En ese caso la sesión no cambia.
        """
        resumen = self.aplicar_preprocesado(estrategia, constante)
        try:
            self.crear_modelo()
        except ErrorModelo as error:
            return resumen, error
        return resumen, None

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
        self._modelo = modelo.entrenar_modelo(entrenamiento, features, target)
        self._archivo = replace(self._archivo, ruta=None, sin_guardar=True)
        self._avisar()
        return self.modelo

    def guardar_descripcion(self, texto):
        """Guarda la descripción del modelo actual.

        Raises:
            ErrorModelo: Si todavía no hay modelo.
        """
        if self.modelo is None:
            raise ErrorModelo("Crea primero el modelo para poder describirlo.")
        if texto is None:
            texto = ""
        texto = str(texto)
        if texto != self.modelo.descripcion:
            self.modelo.descripcion = texto
            self._archivo = replace(self._archivo, sin_guardar=True)

    def guardar_modelo(self, ruta):
        """Guarda el modelo actual, con sus métricas, en un archivo JSON.

        Escribe exactamente en ruta (sobrescribe si ya existe): añadir la
        extensión y pedir confirmación es cosa de la interfaz.

        Returns:
            La ruta absoluta del archivo guardado, como ``Path``.

        Raises:
            ErrorPersistencia: Si no hay modelo o no se puede escribir el
                archivo. En ese caso la sesión no cambia.
        """
        if self.modelo is None:
            raise ErrorPersistencia(
                "Crea primero el modelo para poder guardarlo."
            )
        guardada = persistencia.guardar_modelo(
            self.modelo, self.metricas_modelo(), ruta
        )
        self._archivo = replace(
            self._archivo, ruta=str(guardada), sin_guardar=False
        )
        self._avisar()
        return guardada

    def cargar_modelo(self, ruta):
        """Sustituye todo el trabajo por un modelo guardado en un archivo.

        El archivo no tiene datos, así que se borran el dataset y todos los
        pasos. El modelo queda como guardado en ruta, sin cambios: para
        volver a guardarlo se propone ese mismo archivo. Pedir confirmación
        si el modelo anterior tenía cambios es cosa de la interfaz.

        Returns:
            El ModeloLineal cargado.

        Raises:
            ErrorPersistencia: Si el archivo no se puede leer o no es un
                modelo válido. En ese caso la sesión no cambia.
        """
        cargado, metricas = persistencia.cargar_modelo(ruta)
        self._borrar_desde("dataset")
        self._modelo = cargado
        self._archivo = ArchivoModelo(
            ruta=str(Path(ruta).resolve()), metricas=metricas
        )
        self._avisar()
        return cargado

    def predecir(self, valores):
        """Predice la salida con el modelo actual, creado o cargado.

        No cambia la sesión: se puede llamar las veces que se quiera.

        Args:
            valores: Diccionario ``{columna: valor}`` con un valor por cada
                columna de entrada del modelo, como número o como texto
                ("3.5" o "3,5").

        Returns:
            El valor predicho, como float, sin redondear.

        Raises:
            ErrorPrediccion: Si no hay modelo, falta algún valor o alguno
                no es un número.
        """
        return prediccion.predecir(self.modelo, valores)

    # --- Consultas ---

    @property
    def modelo_cargado(self):
        """True si el modelo actual se cargó de un archivo (no hay datos)."""
        return self.modelo is not None and self._archivo.metricas is not None

    def columnas_modelo(self):
        """Columnas reales de entrada seguidas de la de salida."""
        nombres = list(self.seleccion.features) + [self.seleccion.target]
        return resolver_columnas(self.dataset.datos, nombres)

    def conjuntos_actuales(self):
        """(entrenamiento, test) más recientes: preprocesados si los hay."""
        if self.preprocesado is not None:
            return self.preprocesado.entrenamiento, self.preprocesado.test
        return self.separacion.entrenamiento, self.separacion.test

    def metricas_modelo(self):
        """R² y ECM del modelo actual en entrenamiento y test.

        De un modelo cargado se devuelven las métricas del archivo, porque
        no hay datos con los que calcularlas.

        Returns:
            El diccionario de ``modelo.metricas_modelo``, o None si no hay
            modelo.
        """
        if self.modelo is None:
            return None
        if self.modelo_cargado:
            return copy.deepcopy(self._archivo.metricas)
        entrenamiento, test = self.conjuntos_actuales()
        return modelo.metricas_modelo(self.modelo, entrenamiento, test)

    def detectar_nulos(self):
        """Nulos por columna en train y test, o None si aún no hay
        selección y separación."""
        if self.seleccion is None or self.separacion is None:
            return None
        entrenamiento, test = self.conjuntos_actuales()
        return preprocesado.detectar_nulos_conjuntos(
            entrenamiento, test, self.columnas_modelo()
        )

    def detectar_nulos_originales(self):
        """Nulos por columna en los conjuntos de la separación, antes del
        preprocesado, o None si aún no hay selección y separación.

        Así, después de preprocesar, se siguen viendo los valores que había
        y se puede cambiar de estrategia.
        """
        if self.seleccion is None or self.separacion is None:
            return None
        return preprocesado.detectar_nulos_conjuntos(
            self.separacion.entrenamiento,
            self.separacion.test,
            self.columnas_modelo(),
        )

    def datos_ajuste(self):
        """Puntos y recta del gráfico del ajuste del modelo actual.

        Returns:
            El diccionario de ``modelo.datos_ajuste``, o None si no hay
            modelo o el modelo se cargó de un archivo (no hay datos).
        """
        if self.modelo is None or self.modelo_cargado:
            return None
        entrenamiento, test = self.conjuntos_actuales()
        return modelo.datos_ajuste(self.modelo, entrenamiento, test)

    def hay_cambios_sin_guardar(self):
        """True si hay un modelo con cambios que se perderían al cargar otro
        dataset u otro modelo (recién creado o con la descripción cambiada).
        """
        return self._modelo is not None and self._archivo.sin_guardar

    def puede_crear_modelo(self):
        """True si hay separación y no quedan valores inexistentes."""
        deteccion = self.detectar_nulos()
        if deteccion is None:
            return False
        return not preprocesado.hay_nulos(deteccion)

    def etapas_disponibles(self):
        """Etapas de la interfaz que ya se pueden abrir, en orden.

        "inicio" siempre; "datos" y "variables" con un dataset cargado;
        "preprocesado" con los datos separados; "modelo" cuando ya se puede
        crear (sin valores inexistentes: si no había nada que tratar, se
        abre a la vez que "preprocesado"). Con un modelo cargado de un
        archivo no hay datos con los que trabajar: solo "inicio" (para
        empezar de nuevo) y "modelo".
        """
        if self.modelo_cargado:
            return ("inicio", "modelo")
        disponibles = ["inicio"]
        if self.dataset is not None:
            disponibles += ["datos", "variables"]
        if self.separacion is not None:
            disponibles.append("preprocesado")
        if self.puede_crear_modelo():
            disponibles.append("modelo")
        return tuple(disponibles)

    def siguiente_etapa(self, actual):
        """Etapa a la que lleva "Continuar" desde ``actual``.

        Cada etapa se abre al completar los pasos de la anterior (ver
        ``etapas_disponibles``), así que se puede continuar justo cuando la
        siguiente ya está disponible. Con un modelo cargado de un archivo,
        desde "Inicio" se continúa a "Modelo".

        Returns:
            El nombre de la siguiente etapa, o None si aún no se puede
            continuar (faltan pasos o ``actual`` es la última).
        """
        disponibles = self.etapas_disponibles()
        if actual not in disponibles:
            return None
        posicion = disponibles.index(actual) + 1
        if posicion == len(disponibles):
            return None
        return disponibles[posicion]

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
