"""Tabla con scroll para revisar el dataset cargado."""

import pandas as pd
from nicegui import ui

# Tipos que el navegador recibe tal cual; el resto se muestra como texto
_TIPOS_JSON = (str, int, float, bool)


def _valor_para_tabla(valor):
    """Convierte un valor de pandas en algo que se pueda enviar al navegador.

    NaN y NaT ya llegan como None. Los bytes de un BLOB de SQLite se muestran
    como "<binario: N bytes>". Las fechas, horas, duraciones y cualquier otro
    tipo se muestran como texto.
    """
    if valor is None or isinstance(valor, _TIPOS_JSON):
        return valor
    if isinstance(valor, bytes):
        return "<binario: " + str(len(valor)) + " bytes>"
    return str(valor)


def dataframe_a_tabla(df):
    """Convierte un DataFrame en las columnas y filas que usa ui.table.

    Cada columna usa una clave interna (c0, c1, ...) porque Quasar interpreta
    los puntos de 'field' como rutas anidadas: una columna llamada 'precio.m2'
    se mostraría vacía. El nombre real de la columna va en 'label'. Los
    valores que faltan (NaN) se convierten en None porque NaN no es JSON
    válido.

    Returns:
        Tupla (columnas, filas) lista para ui.table.
    """
    columnas = []
    campos = []
    for i, nombre in enumerate(df.columns):
        campo = "c" + str(i)
        campos.append(campo)
        columnas.append(
            {
                "name": campo,
                "label": str(nombre),
                "field": campo,
                "align": "left",
                "sortable": True,
            }
        )

    valores = df.astype(object).where(pd.notna(df), None)
    filas = []
    for indice, fila in enumerate(valores.itertuples(index=False, name=None)):
        registro = {"_id": indice}
        for campo, valor in zip(campos, fila, strict=True):
            registro[campo] = _valor_para_tabla(valor)
        filas.append(registro)

    return columnas, filas


class TablaDatos:
    """Tabla que muestra todas las filas y columnas del dataset.

    - Scroll vertical: altura fija con 'virtual-scroll' (solo se dibujan las
      filas visibles, así aguanta datasets grandes).
    - Scroll horizontal: aparece solo cuando las columnas no caben.
    - Sin paginación (rowsPerPage = 0): se recorren todas las filas.
    """

    def __init__(self):
        self.tabla = (
            ui.table(
                columns=[],
                rows=[],
                row_key="_id",
                pagination={"rowsPerPage": 0},
            )
            .props("virtual-scroll flat bordered dense hide-pagination")
            .classes("w-full")
            .style("height: 40vh")
        )
        self.tabla.add_slot(
            "no-data",
            '<div class="w-full text-center text-gray-500">'
            "Todavía no se ha cargado ningún dataset</div>",
        )

    def mostrar(self, df):
        """Sustituye el contenido de la tabla por el del DataFrame."""
        columnas, filas = dataframe_a_tabla(df)
        self.tabla.columns = columnas
        self.tabla.rows = filas
