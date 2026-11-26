"""Manejo de la interfaz de SIKORIUS en el navegador con Playwright.

Es la parte que "ve" y "toca" la aplicación. No sabe nada del LLM: recibe
acciones con el texto que se ve en pantalla (el nombre de un botón, la
etiqueta de un campo) y devuelve lo que ha pasado.

Lo que se ve de la página es su árbol de accesibilidad
(``aria_snapshot``): botones con su texto y si están deshabilitados,
campos con su etiqueta y su valor, diálogos, listas y mensajes. Es lo mismo
que lee un lector de pantalla y ocupa mucho menos que una captura.
"""

import re
from pathlib import Path

# Roles en los que se busca el texto de "pulsar", por orden. Si el texto
# está en un botón y también en otro sitio, gana el botón.
ROLES_PULSABLES = (
    "button",
    "tab",
    "radio",
    "checkbox",
    "option",
    "listitem",
    "link",
)

# Teclas que puede pulsar el agente
TECLAS = ("Enter", "Escape", "Tab", "PageDown", "PageUp", "End", "Home")

# Tras cada acción se espera a que la pantalla deje de cambiar: se compara
# cada INTERVALO ms y se da por quieta cuando no cambia en ese tiempo. Si
# sigue cambiando (por ejemplo, cargando un archivo grande), se espera como
# mucho ESPERA_MAXIMA ms.
ESPERA_MINIMA = 300
INTERVALO = 400
ESPERA_MAXIMA = 20000

# Tamaño máximo del texto de la pantalla que se manda al LLM
MAX_CARACTERES = 5000

# Filas de cada tabla que se mandan al LLM (la cabecera aparte)
FILAS_TABLA = 3

# Mensajes de NiceGUI (ui.notify) que aún se ven en la página
SELECTOR_MENSAJES = ".q-notification"

# Lee de una vez la clase y el texto de cada mensaje visible
JS_MENSAJES = """() => Array.from(
  document.querySelectorAll('.q-notification')
).map((n) => {
  const m = n.querySelector('.q-notification__message');
  return [n.className, m ? m.innerText : ''];
})"""

# Lee la configuración de cada gráfico visible de ECharts
JS_GRAFICOS = """() => {
  const salida = [];
  document.querySelectorAll('.nicegui-echart').forEach((div) => {
    if (div.offsetParent === null) return;
    const componente = getElement(parseInt(div.id.slice(1)));
    if (!componente || !componente.chart) return;
    const o = componente.chart.getOption();
    const nombres = (ejes) =>
      (ejes || []).map((e) => e.name || '(sin nombre)');
    const series = (o.series || []).map(
      (s) => '"' + (s.name || '(sin nombre)') + '" (' + s.type + ', '
        + (s.data || []).length + ' puntos)');
    salida.push('Eje X: ' + nombres(o.xAxis).join(', ')
      + ' | Eje Y: ' + nombres(o.yAxis).join(', ')
      + ' | Leyenda: ' + ((o.legend || []).length > 0 ? 'sí' : 'no')
      + ' | Series: ' + (series.join('; ') || 'ninguna'));
  });
  return salida;
}"""


class ErrorAccion(Exception):
    """La acción no se puede hacer: el texto no está o está repetido.

    El mensaje se le devuelve al agente para que vea qué ha fallado.
    """


class Navegador:
    """Una pestaña del navegador con SIKORIUS abierto.

    Attributes:
        pagina: Página de Playwright.
        carpeta: Carpeta donde se guardan las capturas.
        mensajes: Todos los mensajes de la aplicación vistos desde que se
            creó el navegador, en orden y sin repetir.
        nuevos: Mensajes que han aparecido desde la última observación.
        textos_vistos: Todo el texto de pantalla observado, para comprobar
            después que las evidencias del agente son reales.
    """

    def __init__(self, pagina, carpeta):
        self.pagina = pagina
        self.carpeta = Path(carpeta)
        self.carpeta.mkdir(parents=True, exist_ok=True)
        self.mensajes = []
        self.nuevos = []
        self.textos_vistos = []
        self._capturas = 0

    # --- Observar ---

    def observar(self):
        """Devuelve el texto de la pantalla (sin los mensajes).

        Los mensajes nuevos de la aplicación quedan en ``nuevos`` (y se
        acumulan en ``mensajes``), porque el agente los recibe junto al
        resultado de cada acción. El texto se guarda también en
        ``textos_vistos`` para comprobar después las evidencias.
        """
        arbol = self.pagina.locator("body").aria_snapshot()
        self.nuevos = self._recoger_mensajes()
        partes = [compactar(arbol)]
        graficos = self.describir_graficos()
        if graficos:
            partes.append("GRÁFICOS:")
            for grafico in graficos:
                partes.append("- " + grafico)
        texto = "\n".join(partes)
        # Para las evidencias se guarda el árbol completo
        self.textos_vistos.append(arbol + "\n" + texto)
        if len(texto) > MAX_CARACTERES:
            texto = (
                texto[:MAX_CARACTERES]
                + "\n[... pantalla recortada: hay más elementos debajo]"
            )
        return texto

    def _recoger_mensajes(self):
        """Lee los mensajes visibles y devuelve los que no se habían visto."""
        nuevos = []
        for texto in self._leer_mensajes():
            if texto not in self.mensajes:
                self.mensajes.append(texto)
                nuevos.append(texto)
        return nuevos

    def limpiar(self):
        """Deja la pantalla lista para el siguiente caso sin cambiar datos.

        Cierra los diálogos abiertos (Escape) y los mensajes que siguen en
        pantalla, para que no se mezclen con los del caso siguiente.
        """
        for _ in range(3):
            if self.pagina.get_by_role("dialog").count() == 0:
                break
            self.pagina.keyboard.press("Escape")
            self.pagina.wait_for_timeout(300)
        botones = self.pagina.locator(SELECTOR_MENSAJES + " button")
        for indice in range(botones.count() - 1, -1, -1):
            try:
                botones.nth(indice).click(timeout=1000)
            except Exception:  # noqa: BLE001 - ya se ha cerrado sola
                continue
        self.pagina.wait_for_timeout(400)

    def _leer_mensajes(self):
        """Textos de los mensajes visibles, con su tipo delante.

        Se leen todos de una vez con JavaScript: los mensajes desaparecen
        solos y, leyéndolos uno a uno, alguno podía irse a mitad.
        """
        textos = []
        for clases, texto in self.pagina.evaluate(JS_MENSAJES):
            texto = texto.strip()
            if texto:
                textos.append(_tipo_mensaje(clases) + ": " + texto)
        return textos

    def describir_graficos(self):
        """Describe con texto los gráficos de ECharts que se ven.

        Los gráficos se dibujan en un canvas, que el árbol de accesibilidad
        no ve. Se lee su configuración a través de ``getElement`` de
        NiceGUI: títulos de los ejes, leyenda y cada serie con su tipo y su
        número de puntos.
        """
        try:
            descripciones = self.pagina.evaluate(JS_GRAFICOS)
        except Exception:  # noqa: BLE001 - sin gráficos o sin NiceGUI
            return []
        return descripciones

    def capturar(self, nombre):
        """Guarda una captura de la página y devuelve su ruta."""
        self._capturas += 1
        archivo = "%02d_%s.png" % (self._capturas, _limpiar(nombre))
        ruta = self.carpeta / archivo
        self.pagina.screenshot(path=str(ruta), full_page=True)
        return ruta

    # --- Acciones ---

    def pulsar(self, texto):
        """Pulsa el elemento (botón, pestaña, opción...) con ese texto.

        Un botón deshabilitado no se pulsa: se devuelve que lo está, que
        también es información útil para la prueba.
        """
        elemento = self._buscar_pulsable(texto)
        if not elemento.is_enabled():
            return 'El elemento "' + texto + '" está deshabilitado.'
        elemento.click()
        self._esperar()
        return 'Pulsado "' + texto + '".'

    def escribir(self, campo, valor):
        """Borra el campo con esa etiqueta y escribe el valor."""
        elemento = self._buscar_campo(campo)
        if not elemento.is_enabled():
            return 'El campo "' + campo + '" está deshabilitado.'
        elemento.fill(str(valor))
        self._esperar()
        return 'Escrito "' + str(valor) + '" en "' + campo + '".'

    def elegir(self, selector, opciones):
        """Abre un desplegable y marca las opciones indicadas.

        En los desplegables de selección múltiple se marcan todas las de la
        lista; en los simples se usa la primera.
        """
        elemento = self._unico(
            self.pagina.get_by_role("combobox", name=selector),
            "un desplegable llamado " + _entre_comillas(selector),
        )
        if not elemento.is_enabled():
            return 'El desplegable "' + selector + '" está deshabilitado.'
        elemento.click()
        self.pagina.wait_for_timeout(300)
        elegidas = []
        for opcion in opciones:
            candidata = self.pagina.get_by_role(
                "option", name=opcion, exact=True
            )
            if candidata.count() == 0:
                self.pagina.keyboard.press("Escape")
                raise ErrorAccion(
                    'El desplegable "'
                    + selector
                    + '" no tiene la opción "'
                    + opcion
                    + '". Opciones: '
                    + self._opciones_visibles()
                )
            candidata.first.click()
            elegidas.append(opcion)
            self.pagina.wait_for_timeout(200)
        self.pagina.keyboard.press("Escape")
        self._esperar()
        return 'Elegido en "' + selector + '": ' + ", ".join(elegidas) + "."

    def tecla(self, nombre):
        """Pulsa una tecla del teclado."""
        if nombre not in TECLAS:
            raise ErrorAccion(
                "Tecla no permitida. Se puede usar: " + ", ".join(TECLAS)
            )
        self.pagina.keyboard.press(nombre)
        self._esperar()
        return "Pulsada la tecla " + nombre + "."

    def esperar(self, segundos):
        """Espera sin hacer nada (máximo 10 segundos)."""
        segundos = max(0.5, min(float(segundos), 10.0))
        self.pagina.wait_for_timeout(int(segundos * 1000))
        return "Esperados " + str(segundos) + " segundos."

    # --- Búsqueda de elementos ---

    def _buscar_pulsable(self, texto):
        for rol in ROLES_PULSABLES:
            candidatos = self._visibles(
                self.pagina.get_by_role(rol, name=texto, exact=True)
            )
            if len(candidatos) == 1:
                return candidatos[0]
            if len(candidatos) > 1:
                # Varios iguales: si hay un diálogo abierto, el de dentro
                dentro = self._visibles(
                    self.pagina.get_by_role("dialog").get_by_role(
                        rol, name=texto, exact=True
                    )
                )
                if len(dentro) == 1:
                    return dentro[0]
                raise ErrorAccion(
                    'Hay varios elementos "'
                    + texto
                    + '". Indica uno que sea único.'
                )
        # Las entradas de las listas (carpetas y archivos del explorador)
        # no tienen nombre accesible y su texto incluye el del icono: se
        # buscan por el texto de su etiqueta
        exacto = re.compile("^\\s*" + re.escape(texto) + "\\s*$")
        etiqueta = self.pagina.locator(".q-item__label", has_text=exacto)
        candidatos = self._visibles(
            self.pagina.get_by_role("listitem").filter(has=etiqueta)
        )
        if len(candidatos) == 1:
            return candidatos[0]
        candidatos = self._visibles(self.pagina.get_by_text(texto, exact=True))
        if len(candidatos) == 1:
            return candidatos[0]
        if len(candidatos) > 1:
            raise ErrorAccion(
                'Hay varios textos "' + texto + '". Indica uno que sea único.'
            )
        raise ErrorAccion(
            'No hay ningún elemento visible con el texto "'
            + texto
            + '". Revisa la pantalla: puede que esté en otra pestaña.'
        )

    def _buscar_campo(self, campo):
        for rol in ("textbox", "spinbutton"):
            candidatos = self._visibles(
                self.pagina.get_by_role(rol, name=campo, exact=True)
            )
            if len(candidatos) == 1:
                return candidatos[0]
        candidatos = self._visibles(self.pagina.get_by_label(campo))
        if len(candidatos) == 1:
            return candidatos[0]
        raise ErrorAccion(
            'No hay ningún campo visible con la etiqueta "' + campo + '".'
        )

    def _unico(self, localizador, descripcion):
        candidatos = self._visibles(localizador)
        if len(candidatos) == 1:
            return candidatos[0]
        if not candidatos:
            raise ErrorAccion("No hay " + descripcion + " visible.")
        raise ErrorAccion("Hay varios elementos: " + descripcion + ".")

    @staticmethod
    def _visibles(localizador):
        visibles = []
        for indice in range(localizador.count()):
            elemento = localizador.nth(indice)
            if elemento.is_visible():
                visibles.append(elemento)
        return visibles

    def _opciones_visibles(self):
        nombres = []
        opciones = self.pagina.get_by_role("option")
        for indice in range(opciones.count()):
            nombres.append(opciones.nth(indice).inner_text().strip())
        return ", ".join(nombres)

    def _esperar(self):
        """Espera a que la aplicación termine de actualizar la pantalla."""
        self.pagina.wait_for_timeout(ESPERA_MINIMA)
        anterior = self.pagina.locator("body").aria_snapshot()
        esperado = ESPERA_MINIMA
        while esperado < ESPERA_MAXIMA:
            self.pagina.wait_for_timeout(INTERVALO)
            esperado = esperado + INTERVALO
            actual = self.pagina.locator("body").aria_snapshot()
            if actual == anterior:
                return
            anterior = actual


def compactar(arbol):
    """Reduce el árbol de accesibilidad para gastar menos tokens.

    - Quita las imágenes (no aportan nada a las pruebas).
    - Quita los mensajes ("alert"), que se mandan aparte.
    - De cada tabla deja la cabecera y las primeras filas, e indica cuántas
      se han omitido.
    """
    lineas = arbol.splitlines()
    salida = []
    indice = 0
    filas = {}
    while indice < len(lineas):
        linea = lineas[indice]
        sangria = len(linea) - len(linea.lstrip())
        contenido = linea.strip()
        if contenido.startswith("- img") or contenido.startswith("- alert"):
            indice = _saltar_hijos(lineas, indice, sangria)
            continue
        if contenido.startswith("- rowgroup"):
            filas[sangria + 2] = 0
        if contenido.startswith("- row") and sangria in filas:
            filas[sangria] += 1
            if filas[sangria] > FILAS_TABLA:
                omitidas = 0
                while indice < len(lineas):
                    actual = lineas[indice]
                    nivel = len(actual) - len(actual.lstrip())
                    if nivel < sangria:
                        break
                    if nivel == sangria and actual.strip().startswith("- row"):
                        omitidas += 1
                    indice += 1
                salida.append(
                    " " * sangria
                    + "- (... "
                    + str(omitidas)
                    + " filas más que no se muestran)"
                )
                continue
            # De cada fila basta su nombre, que ya lleva el texto de las
            # celdas: se quitan las celdas una a una
            salida.append(linea.rstrip(":"))
            indice = _saltar_hijos(lineas, indice, sangria)
            continue
        salida.append(linea)
        indice += 1
    return "\n".join(salida)


def _saltar_hijos(lineas, indice, sangria):
    """Índice de la primera línea después de ``lineas[indice]`` y sus hijos."""
    indice += 1
    while indice < len(lineas):
        actual = lineas[indice]
        if len(actual) - len(actual.lstrip()) <= sangria:
            break
        indice += 1
    return indice


def _tipo_mensaje(clases):
    """Traduce las clases de un mensaje de Quasar a éxito, aviso o error."""
    if "bg-negative" in clases:
        return "ERROR"
    if "bg-warning" in clases:
        return "AVISO"
    if "bg-positive" in clases:
        return "ÉXITO"
    return "MENSAJE"


def _entre_comillas(texto):
    return '"' + texto + '"'


def _limpiar(nombre):
    """Convierte un texto en un trozo válido de nombre de archivo."""
    letras = []
    for letra in nombre.lower():
        if letra.isalnum():
            letras.append(letra)
        else:
            letras.append("_")
    return "".join(letras)[:40]
