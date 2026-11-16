"""Selectores de las columnas de entrada (features) y de salida (target).

Son componentes: no saben nada de la sesión ni del flujo de trabajo. Reciben
el DataFrame, muestran sus columnas y devuelven lo que ha elegido el
usuario. El panel de columnas los junta con el botón de confirmar.

El tipo de regresión no se elige aquí: la sesión lo deduce del número de
columnas de entrada (una -> simple, varias -> múltiple).
"""

import html
import json

from nicegui import ui

from sikorius.gui.tema import colores_columnas


def plantilla_chip(colores, quitable):
    """Plantilla Quasar del "chip" (recuadro ovalado) de cada columna elegida.

    Cada chip toma el color de su columna: borde del color y fondo del mismo
    color casi transparente ("40" al final de un color hex es un 25% de
    opacidad). Los colores se meten en la plantilla como un objeto de
    JavaScript, con las comillas escapadas para que un nombre de columna raro
    no rompa el atributo.
    """
    tabla = html.escape(json.dumps(colores), quote=True)
    color = "(" + tabla + ")[props.opt.label]"
    return (
        '<q-chip dense :removable="' + ("true" if quitable else "false") + '"'
        ' :tabindex="props.tabindex" text-color="white"'
        ' @remove="props.removeAtIndex(props.index)"'
        " :style=\"{border: '1px solid ' + " + color + ","
        " backgroundColor: " + color + " + '40'}\">"
        "{{ props.opt.label }}</q-chip>"
    )


class _SelectorColumnas:
    """Parte común de los dos selectores: un ``ui.select`` con las columnas
    del dataset, que se vuelve a crear vacío al cargar un dataset nuevo y
    que está deshabilitado mientras no hay columnas.

    Las subclases indican el texto, si se pueden elegir varias columnas y
    si los "chips" se pueden quitar, y pueden filtrar las opciones.
    """

    ETIQUETA = ""
    MULTIPLE = False
    QUITABLE = False

    def __init__(self):
        self.columnas = []
        self.selector = None
        self.contenedor = ui.column().classes("w-full")
        self._construir_selector()

    def _opciones(self):
        """Columnas que se ofrecen. Por defecto, todas."""
        return list(self.columnas)

    def _al_construir(self):
        """Gancho para configurar el selector recién creado."""

    def _construir_selector(self):
        """(Re)crea el ui.select sin selección previa."""
        self.contenedor.clear()
        with self.contenedor:
            self.selector = (
                ui.select(
                    options=self._opciones(),
                    label=self.ETIQUETA,
                    multiple=self.MULTIPLE,
                    value=[] if self.MULTIPLE else None,
                    clearable=True,
                )
                .props("use-chips")
                .classes("w-full")
            )
            self.selector.add_slot(
                "selected-item",
                plantilla_chip(colores_columnas(self.columnas), self.QUITABLE),
            )
            self._al_construir()

            if len(self.columnas) == 0:
                self.selector.disable()
            else:
                self.selector.enable()

    def _leer_columnas(self, df):
        self.columnas = [str(columna) for columna in df.columns]


class SelectorFeatures(_SelectorColumnas):
    """
    Selector dinámico de columnas de entrada (features).

    - Permite elegir una o varias columnas.
    - Al cargar un dataset nuevo muestra sus columnas y limpia la selección
      anterior.
    """

    ETIQUETA = "Features (selección múltiple)"
    MULTIPLE = True
    QUITABLE = True

    def cargar_columnas(self, df):
        """Muestra las columnas de un dataset nuevo y limpia la selección
        anterior."""
        self._leer_columnas(df)
        self._construir_selector()

    def obtener_seleccion(self):
        """Devuelve siempre una lista de features (vacía si no hay
        selección)."""
        valor = self.selector.value
        if valor is None:
            return []
        return list(valor)


class SelectorTarget(_SelectorColumnas):
    """
    Selector dinámico de columnas de salida (target).

    - Al cargar un dataset nuevo muestra sus columnas y limpia la selección.
    - Permite excluir columnas (las ya elegidas como features), para que
      una misma columna no sea entrada y salida a la vez.
    """

    ETIQUETA = "Target (columna de salida)"

    def __init__(self, al_abrir=None):
        self.al_abrir = al_abrir
        self.excluidas = []
        super().__init__()

    def _opciones(self):
        """Columnas disponibles como target (todas menos las excluidas)."""
        return [c for c in self.columnas if c not in self.excluidas]

    def _al_construir(self):
        if self.al_abrir is not None:
            self.selector.on("popup-show", lambda: self.al_abrir())

    def cargar_columnas(self, df):
        """Muestra las columnas de un dataset nuevo y limpia la selección
        anterior."""
        self._leer_columnas(df)
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
