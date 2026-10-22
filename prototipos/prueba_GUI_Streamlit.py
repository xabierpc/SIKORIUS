import subprocess
import sys
import tempfile
from pathlib import Path
import pandas as pd
import streamlit as st

try:
    from sikorius.importador import ErrorImportacion, importar_datos
except ImportError:
    importar_datos = None


TITULO = 'SIKORIUS'
EXTENSIONES = ['csv', 'xlsx', 'xls', 'db', 'sqlite']
FILAS_TABLA = 100
OPCIONES = ['Raúl', 'Xabi', 'Pepe', 'Hugo']

# Diálogo nativo de Tkinter.
CODIGO_DIALOGO = '''
import tkinter as tk
from tkinter import filedialog
raiz = tk.Tk()
raiz.withdraw()
raiz.attributes("-topmost", True)
print(filedialog.askopenfilename(
    title="Selecciona un archivo",
    filetypes=[("Datos", "*.csv *.xlsx *.xls *.db *.sqlite"), ("Todos", "*.*")]))
'''


def datos_ejemplo():
    # Mismos datos que la prueba que hicimos de NiceGUI (suficientes filas para que haya scroll)
    filas = [{'id': i, 'x': i * 1.5, 'y': round(2 * i * 1.5 + 3, 2)} for i in range(1, 51)]
    return pd.DataFrame(filas)


def dialogo_nativo():
    """Abre el diálogo del sistema y devuelve la ruta, o None si se cancela.
    Solo funciona si el servidor corre en el mismo ordenador que el navegador.
    """
    try:
        resultado = subprocess.run([sys.executable, '-c', CODIGO_DIALOGO],
                                   capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return None
    if resultado.returncode != 0:
        st.error('No se pudo abrir el diálogo de Tkinter:\n\n' + resultado.stderr.strip())
        return None
    return resultado.stdout.strip() or None


def importar(ruta):
    try:
        return importar_datos(ruta)
    except ErrorImportacion as e:
        st.error(str(e))
        return None


def importar_subido(archivo):
    # El importador necesita una ruta, pero st.file_uploader solo da los bytes:
    # se guardan en un temporal con la misma extensión.
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / archivo.name
        ruta.write_bytes(archivo.getvalue())
        return importar(ruta)


@st.dialog('Valores seleccionados')
def mostrar_mensaje(opcion, texto):
    st.write(f'**Opción:** {opcion}')
    st.write(f'**Valor:** {texto}')


#Título de la "ventana" (pestaña del navegador) y de la página
st.set_page_config(page_title=TITULO, layout='wide')
st.title(TITULO)

# El estado sobrevive a las reejecuciones solo si se guarda en session_state
if 'ruta' not in st.session_state:
    st.session_state.ruta = None

#1. Selección de archivos
st.subheader('Archivo')
col_nativo, col_subida = st.columns(2)

with col_nativo:
    st.markdown('**Opción A: diálogo nativo (Tkinter)**')
    if st.button('Abrir archivo', icon=':material/folder_open:'):
        ruta = dialogo_nativo()
        if ruta:
            st.session_state.ruta = ruta
    if st.session_state.ruta:
        st.success('Ruta: ' + st.session_state.ruta)
    else:
        st.caption('Ningún archivo seleccionado')

with col_subida:
    st.markdown('**Opción B: widget de Streamlit**')
    subido = st.file_uploader('Sube un archivo', type=EXTENSIONES)
    if subido:
        # El navegador solo envía el nombre y el contenido
        st.info(f'Nombre: {subido.name} ({subido.size} bytes). La ruta real no está disponible.')

#2. Tabla con scroll
st.subheader('Datos')
df = None
if importar_datos is None:
    st.caption('Importador no disponible: se muestran datos de ejemplo.')
elif subido:
    df = importar_subido(subido)
    origen = subido.name
elif st.session_state.ruta:
    df = importar(st.session_state.ruta)
    origen = st.session_state.ruta

if df is None:
    df = datos_ejemplo()
    origen = 'datos de ejemplo'

st.caption(f'Primeras {min(FILAS_TABLA, len(df))} de {len(df)} filas de {origen}')
st.dataframe(df.head(FILAS_TABLA), height=300)

#3. Desplegable + cuadro de texto + botón que muestra los valores
st.subheader('Entrada de datos')
col_select, col_texto = st.columns(2)
opcion = col_select.selectbox('Trabajador', OPCIONES)
texto = col_texto.text_input('Introduce un número', placeholder='Ej: 4.2')

if st.button('Mostrar', icon=':material/send:'):
    if texto.strip():
        mostrar_mensaje(opcion, texto)
    else:
        st.warning('No has introducido ningún valor')
