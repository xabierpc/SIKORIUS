from nicegui import ui

@ui.page('/')
async def index():
    ui.label('Hola Lázaro')
    
    # Botón
    a = ui.button('Tócame como te gusta')
    
    # Espera a que hagan clic
    await a.clicked()
    
    # Aparece el texto y el icono después del clic
    ui.label('Ooooooh si Lazarillo')
    
    # Icono animado que salta al aparecer
    ui.icon('thumb_up', color='primary').classes('text-5xl')
ui.run()