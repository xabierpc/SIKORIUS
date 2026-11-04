"""Selectores de las columnas de entrada (features) y de salida (target).

Son componentes: no saben nada de la sesión ni del flujo de trabajo. Reciben
el DataFrame, muestran sus columnas y devuelven lo que ha elegido el
usuario. El panel de columnas los junta con el botón de confirmar.

El modo simple de ``SelectorFeatures`` solo lo usa la demo
``sikorius.datos_entrada_salida``; se quitará cuando se borre la demo.
"""

from nicegui import ui


class SelectorFeatures:
    """
    Selector dinámico de columnas de entrada (features).

    - Regresión simple   -> selección simple (una sola columna).
    - Regresión múltiple -> selección múltiple.
    - Al cargar un dataset nuevo muestra sus columnas y limpia la selección
      anterior.
    """

    SIMPLE = "simple"
    MULTIPLE = "multiple"

    def __init__(self, tipo_regresion="multiple"):
        self.columnas = []
        self.selector = None
        self.contenedor = ui.column().classes("w-full")
        self.cambiar_tipo_regresion(tipo_regresion)

    def _construir_selector(self):
        """(Re)crea el ui.select según el tipo de regresión, sin selección
        previa."""
        self.contenedor.clear()

        if self.tipo_regresion == self.MULTIPLE:
            es_multiple = True
            etiqueta = "Features (selección múltiple)"
            valor_inicial = []
        else:
            es_multiple = False
            etiqueta = "Feature (selección simple)"
            valor_inicial = None

        with self.contenedor:
            self.selector = ui.select(
                options=self.columnas,
                label=etiqueta,
                multiple=es_multiple,
                value=valor_inicial,
                clearable=True,
            ).classes("w-full")

            if es_multiple:
                self.selector.props("use-chips")

            if len(self.columnas) == 0:
                self.selector.disable()
            else:
                self.selector.enable()

    def cambiar_tipo_regresion(self, tipo_regresion):
        """Cambia entre selección simple y múltiple; limpia la selección."""
        if tipo_regresion != self.SIMPLE and tipo_regresion != self.MULTIPLE:
            raise ValueError(
                "Tipo de regresión no válido: " + str(tipo_regresion)
            )
        self.tipo_regresion = tipo_regresion
        self._construir_selector()

    def cargar_columnas(self, df):
        """Muestra las columnas de un dataset nuevo y limpia la selección
        anterior."""
        self.columnas = []
        for columna in df.columns:
            self.columnas.append(str(columna))
        self._construir_selector()

    def obtener_seleccion(self):
        """Devuelve siempre una lista de features (vacía si no hay
        selección)."""
        valor = self.selector.value
        if valor is None:
            return []
        if isinstance(valor, list):
            return list(valor)
        return [valor]


class SelectorTarget:
    """
    Selector dinámico de columnas de salida (target).

    - Al cargar un dataset nuevo muestra sus columnas y limpia la selección.
    - Permite excluir columnas (las ya elegidas como features), para que
      una misma columna no sea entrada y salida a la vez.
    """

    def __init__(self, al_abrir=None):
        self.al_abrir = al_abrir
        self.columnas = []
        self.excluidas = []
        self.selector = None
        self.contenedor = ui.column().classes("w-full")
        self._construir_selector()

    def _opciones(self):
        """Columnas disponibles como target (todas menos las excluidas)."""
        disponibles = []
        for columna in self.columnas:
            if columna not in self.excluidas:
                disponibles.append(columna)
        return disponibles

    def _construir_selector(self):
        """(Re)crea el ui.select sin selección previa."""
        self.contenedor.clear()
        with self.contenedor:
            self.selector = ui.select(
                options=self._opciones(),
                label="Target (columna de salida)",
                value=None,
                clearable=True,
            ).classes("w-full")

            if self.al_abrir is not None:
                self.selector.on("popup-show", lambda: self.al_abrir())

            if len(self.columnas) == 0:
                self.selector.disable()
            else:
                self.selector.enable()

    def cargar_columnas(self, df):
        """Muestra las columnas de un dataset nuevo y limpia la selección
        anterior."""
        self.columnas = []
        for columna in df.columns:
            self.columnas.append(str(columna))
        self.excluidas = []
        self._construir_selector()

    def excluir(self, columnas):
        """Quita de las opciones las columnas dadas (las elegidas como
        features)."""
        self.excluidas = list(columnas)
        self.selector.set_options(self._opciones())
        if self.selector.value in self.excluidas:
            self.selector.set_value(None)

    def obtener_seleccion(self):
        """Devuelve la columna elegida como target, o None si no hay
        ninguna."""
        return self.selector.value
