from pathlib import Path

from nicegui import ui


TITULO = 'SIKORIUS'

# Datos de ejemplo para la tabla (suficientes filas para que haga falta scroll)
COLUMNAS = [
    {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left', 'sortable': True},
    {'name': 'x', 'label': 'X', 'field': 'x', 'sortable': True},
    {'name': 'y', 'label': 'Y', 'field': 'y', 'sortable': True},
]
FILAS = []
for i in range(1, 51):
    FILAS.append({'id': i, 'x': i * 1.5, 'y': round(2 * i * 1.5 + 3, 2)})

OPCIONES = ['Raúl', 'Xabi', 'Pepe', 'Hugo']


def listar_carpeta(carpeta):
    # Devuelve el contenido de la carpeta: primero carpetas, luego archivos
    entradas = []
    try:
        for p in carpeta.iterdir():
            if not p.name.startswith('.'):
                entradas.append(p)
    except PermissionError:
        ui.notify('Sin permiso para abrir ' + str(carpeta), type='negative')
    entradas.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
    return entradas


async def selector_archivos(inicio):
    # Diálogo de selección de archivos hecho solo con NiceGUI.
    # Como el servidor corre en local, la ruta que devuelve es la real del disco.
    with ui.dialog() as dialogo, ui.card().classes('w-[600px] max-w-full'):
        ui.label('Selecciona un archivo').classes('text-lg font-semibold')
        etiqueta_carpeta = ui.label().classes('text-sm text-gray-500 break-all')
        with ui.scroll_area().classes('w-full h-80 border rounded'):
            lista = ui.list().classes('w-full').props('dense separator')
        with ui.row().classes('w-full justify-end'):
            ui.button('Cancelar', on_click=lambda: dialogo.submit(None)).props('flat')

    def accion(p):
        return lambda: abrir(p)

    def abrir(p):
        if p.is_dir():
            mostrar(p)
        else:
            dialogo.submit(str(p))

    def mostrar(carpeta):
        etiqueta_carpeta.set_text(str(carpeta))
        lista.clear()
        with lista:
            if carpeta.parent != carpeta:
                with ui.item(on_click=accion(carpeta.parent)):
                    with ui.item_section().props('avatar'):
                        ui.icon('arrow_upward')
                    with ui.item_section():
                        ui.item_label('..')
            for p in listar_carpeta(carpeta):
                if p.is_dir():
                    icono = 'folder'
                else:
                    icono = 'description'
                with ui.item(on_click=accion(p)):
                    with ui.item_section().props('avatar'):
                        ui.icon(icono)
                    with ui.item_section():
                        ui.item_label(p.name)

    mostrar(inicio)
    ruta = await dialogo
    dialogo.clear()
    return ruta


@ui.page('/')
async def index():
    # --- Título visible de la "ventana" ---
    with ui.header().classes('items-center'):
        ui.label(TITULO).classes('text-xl font-bold')

    ui.label('Hola Grupo').classes('text-2xl font-bold')

    # --- 1. Botón que abre el diálogo de archivos y muestra la ruta ---
    with ui.card().classes('w-full'):
        ui.label('Archivo').classes('text-lg font-semibold')
        etiqueta_ruta = ui.label('Ningún archivo seleccionado').classes('text-gray-500 break-all')

        async def elegir_archivo():
            ruta = await selector_archivos(Path.home())
            if ruta:
                etiqueta_ruta.set_text('Ruta: ' + ruta)
            else:
                etiqueta_ruta.set_text('Selección cancelada')

        ui.button('Abrir archivo', icon='folder_open', on_click=elegir_archivo)

    # --- 2. Tabla con scroll ---
    with ui.card().classes('w-full'):
        ui.label('Datos de ejemplo').classes('text-lg font-semibold')
        ui.table(columns=COLUMNAS, rows=FILAS, row_key='id') \
            .props('virtual-scroll flat bordered') \
            .classes('w-full') \
            .style('height: 250px')

    # --- 3. Desplegable + cuadro de texto + botón que muestra los valores ---
    with ui.card().classes('w-full'):
        ui.label('Entrada de datos').classes('text-lg font-semibold')
        with ui.row().classes('w-full items-end'):
            desplegable = ui.select(OPCIONES, value=OPCIONES[0], label='Trabajador').classes('w-64')
            entrada = ui.input(label='Introduce un número', placeholder='Ej: 4.2').classes('w-64')

        def mostrar_valores():
            texto = entrada.value
            if texto is None or texto.strip() == '':
                ui.notify('No has introducido ningún valor', type='warning')
            else:
                mensaje = 'Opción: ' + str(desplegable.value) + ' | Valor: ' + texto
                ui.notify(mensaje, type='positive')

        ui.button('Mostrar', icon='send', on_click=mostrar_valores)


if __name__ in {"__main__", "__mp_main__"}:
    # Abre el navegador local en http://localhost:8080; el título va en la pestaña
    ui.run(title=TITULO)