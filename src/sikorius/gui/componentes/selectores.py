"""Selectores de las columnas de entrada (features) y de salida (target).

Son componentes: no saben nada de la sesión ni del flujo de trabajo. Reciben
el DataFrame, muestran sus columnas y devuelven lo que ha elegido el
usuario. El panel de columnas los junta con el botón de confirmar.

El tipo de regresión no se elige aquí: la sesión lo deduce del número de
columnas de entrada (una -> simple, varias -> múltiple).
"""

from nicegui import ui


class SelectorFeatures:
    """
    Selector dinámico de columnas de entrada (features).

    - Permite elegir una o varias columnas.
    - Al cargar un dataset nuevo muestra sus columnas y limpia la selección
      anterior.
    """

    def __init__(self):
        self.columnas = []
        self.selector = None
        self.contenedor = ui.column().classes("w-full")
        self._construir_selector()

    def _construir_selector(self):
        """(Re)crea el ui.select sin selección previa."""
        self.contenedor.clear()
        with self.contenedor:
            self.selector = (
                ui.select(
                    options=self.columnas,
                    label="Features (selección múltiple)",
                    multiple=True,
                    value=[],
                    clearable=True,
                )
                .props("use-chips")
                .classes("w-full")
            )

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
        self._construir_selector()

    def obtener_seleccion(self):
        """Devuelve siempre una lista de features (vacía si no hay
        selección)."""
        valor = self.selector.value
        if valor is None:
            return []
        return list(valor)


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
