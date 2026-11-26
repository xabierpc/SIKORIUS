"""Historias #10 y #14: carga de datos y tabla (CP-01 a CP-14)."""

from funcionales.sikorius_ui import COLUMNAS, FILAS


def comprobar_d1(ui, final_ruta):
    assert ui.ruta().endswith(final_ruta)
    assert ui.columnas_tabla() == COLUMNAS
    assert ui.resumen() == str(FILAS) + " filas y 10 columnas"
    assert ui.errores() == []


def test_cp01_carga_csv(d1):
    """CP-01. Carga de un CSV válido."""
    ui = d1
    ui.reiniciar()
    ui.pulsar("Subir dataset")
    ui.ir_a_carpeta([])
    ui.elegir_archivo("housing1.csv")
    comprobar_d1(ui, "data/housing1.csv")


def test_cp02_carga_excel(d1):
    """CP-02. Carga de un Excel válido."""
    d1.cargar("housing.xlsx")
    comprobar_d1(d1, "data/housing.xlsx")


def test_cp03_carga_sqlite(d1):
    """CP-03. Carga de una base de datos SQLite válida, sin pedir la tabla."""
    d1.cargar("housing.db")
    assert not d1.hay_dialogo()
    comprobar_d1(d1, "data/housing.db")


def test_cp04_columnas_numericas(d1):
    """CP-04. Las columnas numéricas se cargan como números."""
    d1.cargar_d1()
    d1.seleccionar(["median_income"], "median_house_value")
    exitos = " ".join(d1.exitos())
    assert "Entrada: median_income" in exitos
    assert "Salida: median_house_value" in exitos
    assert d1.errores() == []


def test_cp05_explorador_filtra_tipos(ui):
    """CP-05. El explorador solo muestra los tipos permitidos."""
    ui.abrir_explorador_dataset()
    ui.ir_a_carpeta(["pruebas"])
    entradas = ui.entradas_explorador()
    assert "vacio.csv" in entradas
    assert "notas.txt" not in entradas
    for nombre in entradas:
        if "." in nombre and nombre != "..":
            extension = nombre.rsplit(".", 1)[1].lower()
            assert extension in ("csv", "xlsx", "xls", "sqlite", "db"), nombre


def test_cp06_cancelar_explorador(d1):
    """CP-06. Cerrar el explorador sin elegir archivo."""
    d1.cargar_d1()
    d1.abrir_explorador_dataset()
    d1.pulsar("Cancelar", d1.dialogo())
    assert not d1.hay_dialogo()
    assert d1.errores() == []
    assert d1.ruta().endswith("data/housing1.csv")
    assert d1.resumen().startswith(str(FILAS) + " filas")


def test_cp07_archivo_vacio(ui):
    """CP-07. Archivo vacío: error y la aplicación sigue funcionando."""
    ui.reiniciar()
    ui.cargar("vacio.csv", ["pruebas"])
    assert ui.errores(), "Se esperaba un mensaje de error"
    assert "Datos" not in ui.pestanas(), "La tabla debería seguir vacía"
    assert ui.habilitado("Subir dataset")


def test_cp08_solo_cabecera(ui):
    """CP-08. Archivo con encabezado y sin datos."""
    ui.cargar("solo_cabecera.csv", ["pruebas"])
    assert ui.errores(), "Se esperaba un mensaje de error"


def test_cp09_excel_danado_conserva_datos(d1):
    """CP-09. Un Excel dañado da error y se conservan los datos anteriores."""
    d1.cargar_d1()
    d1.cargar("falso.xlsx", ["pruebas"])
    assert d1.errores(), "Se esperaba un mensaje de error"
    assert d1.ruta().endswith("data/housing1.csv")
    assert d1.resumen().startswith(str(FILAS) + " filas")


def test_cp10_base_de_datos_danada(ui):
    """CP-10. Base de datos dañada."""
    ui.reiniciar()
    ui.cargar("falso.db", ["pruebas"])
    assert ui.errores(), "Se esperaba un mensaje de error"
    assert "Datos" not in ui.pestanas(), "La tabla debería seguir vacía"


def test_cp11_sqlite_dos_tablas(ui):
    """CP-11. SQLite con dos tablas."""
    ui.cargar("dos_tablas.db", ["pruebas"])
    errores = " ".join(ui.errores()).lower()
    assert "más de una tabla" in errores, errores


def test_cp12_sqlite_sin_tablas(ui):
    """CP-12. SQLite sin tablas."""
    ui.cargar("sin_tablas.db", ["pruebas"])
    errores = " ".join(ui.errores()).lower()
    assert "tabla" in errores, errores


def test_cp13_ruta_con_caracteres_especiales(d1):
    """CP-13. Ruta con espacios, ñ y tildes."""
    d1.cargar("housing1.csv", ["pruebas", "carpeta ñandú á"])
    assert "carpeta ñandú á" in d1.ruta()
    assert d1.resumen().startswith(str(FILAS) + " filas")
    assert d1.errores() == []


def test_cp14_segundo_dataset_sustituye(d1):
    """CP-14. Cargar un segundo dataset sustituye la tabla."""
    d1.cargar_d1()
    d1.cargar("lineal.csv", ["pruebas"])
    assert d1.ruta().endswith("data/pruebas/lineal.csv")
    assert d1.columnas_tabla() == ["x1", "x2", "y"]
    assert d1.resumen() == "12 filas y 3 columnas"
