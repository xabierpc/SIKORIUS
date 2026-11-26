"""Acciones de alto nivel sobre la interfaz de SIKORIUS para las pruebas.

Las pruebas funcionales (``test_*.py`` de esta carpeta) usan la clase
``Sikorius`` para manejar la aplicación como lo haría una persona: pulsar
botones por su texto, cargar archivos con el explorador, elegir columnas,
etc. Todo pasa por el navegador (Playwright): no se llama al código de la
aplicación.
"""

import re

# Recoge todos los mensajes emergentes (ui.notify) en window.__sk_mensajes,
# aunque desaparezcan a los pocos segundos. Se instala en cada carga de la
# página.
JS_OBSERVADOR = """
(() => {
  window.__sk_mensajes = [];
  const anotar = (nodo) => {
    if (!(nodo instanceof Element)) return;
    const avisos = nodo.matches('.q-notification')
      ? [nodo] : Array.from(nodo.querySelectorAll('.q-notification'));
    for (const aviso of avisos) {
      // Se guarda el elemento: su texto se lee después, cuando ya está
      // completo (al insertarlo, Quasar aún puede no haberlo pintado)
      if (!window.__sk_mensajes.includes(aviso)) {
        window.__sk_mensajes.push(aviso);
      }
    }
  };
  new MutationObserver((cambios) => {
    for (const cambio of cambios) cambio.addedNodes.forEach(anotar);
  }).observe(document, {childList: true, subtree: true});
})();
"""

# Configuración de los gráficos de ECharts visibles (ejes, leyenda, series)
JS_GRAFICOS = """() => {
  const salida = [];
  document.querySelectorAll('.nicegui-echart').forEach((div) => {
    if (div.offsetParent === null) return;
    const c = getElement(parseInt(div.id.slice(1)));
    if (!c || !c.chart) return;
    const o = c.chart.getOption();
    salida.push({
      ejeX: (o.xAxis || []).map((e) => e.name || ''),
      ejeY: (o.yAxis || []).map((e) => e.name || ''),
      leyenda: (o.legend || []).length > 0,
      series: (o.series || []).map((s) => ({
        nombre: s.name || '', tipo: s.type, puntos: (s.data || []).length,
      })),
    });
  });
  return salida;
}"""

TIPOS_MENSAJE = {
    "bg-negative": "error",
    "bg-warning": "aviso",
    "bg-positive": "exito",
}

# Tras cada acción se espera a que la pantalla deje de cambiar
INTERVALO = 200
ESPERA_MAXIMA = 20000


class Sikorius:
    """La aplicación abierta en una pestaña del navegador.

    Attributes:
        aplicacion: ``Aplicacion`` (proceso de SIKORIUS).
        pagina: Página de Playwright.
        capturas: Carpeta donde se guardan las capturas del test actual.
    """

    def __init__(self, aplicacion, pagina, capturas):
        self.aplicacion = aplicacion
        self.pagina = pagina
        self.carpeta_capturas = capturas
        self.capturas = capturas
        self.pagina.add_init_script(JS_OBSERVADOR)
        # Si algo no aparece, mejor fallar pronto que esperar 30 s
        self.pagina.set_default_timeout(10000)
        self._numero = 0

    # --- Aplicación ---

    def reiniciar(self):
        """Cierra la aplicación y la vuelve a abrir (procedimiento PR-1)."""
        self.aplicacion.reiniciar()
        self.pagina.goto(self.aplicacion.url)
        self.pagina.wait_for_load_state("networkidle")
        self.esperar()

    def empezar_test(self, nombre):
        """Deja la pantalla lista para un test sin cambiar los datos.

        Cierra diálogos y mensajes que hayan quedado de otro test y olvida
        los mensajes recogidos.
        """
        self.capturas = self.carpeta_capturas / nombre
        self._numero = 0
        if not self.aplicacion.en_marcha:
            self.reiniciar()
        for _ in range(3):
            if self.pagina.get_by_role("dialog").count() == 0:
                break
            self.pagina.keyboard.press("Escape")
            self.pagina.wait_for_timeout(300)
        self.pagina.evaluate(
            "document.querySelectorAll('.q-notification button')"
            ".forEach((b) => b.click())"
        )
        self.pagina.wait_for_timeout(300)
        self.pagina.evaluate("window.__sk_mensajes = []")

    def esperar(self):
        """Espera a que la aplicación termine de actualizar la pantalla."""
        self.pagina.wait_for_timeout(INTERVALO)
        anterior = self._foto()
        esperado = INTERVALO
        while esperado < ESPERA_MAXIMA:
            self.pagina.wait_for_timeout(INTERVALO)
            esperado = esperado + INTERVALO
            actual = self._foto()
            if actual == anterior:
                return
            anterior = actual

    def _foto(self):
        """Huella barata del estado de la pantalla para saber si cambia."""
        return self.pagina.evaluate(
            "() => document.body.innerText.length + '|' + "
            "document.getElementsByTagName('*').length + '|' + "
            "document.querySelectorAll('[disabled], .disabled').length"
        )

    def capturar(self, nombre):
        self._numero += 1
        self.capturas.mkdir(parents=True, exist_ok=True)
        archivo = "%02d_%s.png" % (self._numero, nombre)
        self.pagina.screenshot(path=str(self.capturas / archivo))

    # --- Mensajes ---

    def olvidar_mensajes(self):
        """Olvida los mensajes recogidos hasta ahora (por ejemplo, los de los
        pasos de preparación), para comprobar solo los siguientes."""
        self.pagina.evaluate("window.__sk_mensajes = []")

    def mensajes(self, tipo=None):
        """Mensajes emergentes desde el inicio del test: [(tipo, texto)]."""
        # Las copias vacías que Quasar crea al animar los mensajes antiguos
        # no tienen texto: se descartan
        crudos = self.pagina.evaluate(
            "() => (window.__sk_mensajes || []).map((a) => {"
            " const m = a.querySelector('.q-notification__message');"
            " return [a.className, m ? m.textContent : null]; })"
            ".filter((par) => par[1] !== null)"
        )
        salida = []
        for clases, texto in crudos:
            clase = "mensaje"
            for marca, nombre in TIPOS_MENSAJE.items():
                if marca in clases:
                    clase = nombre
            if tipo is None or clase == tipo:
                salida.append((clase, texto.strip()))
        return salida

    def textos(self, tipo):
        textos = []
        for _, texto in self.mensajes(tipo):
            textos.append(texto)
        return textos

    def errores(self):
        return self.textos("error")

    def exitos(self):
        return self.textos("exito")

    def avisos(self):
        return self.textos("aviso")

    # --- Elementos ---

    def visibles(self, localizador):
        elementos = []
        for indice in range(localizador.count()):
            elemento = localizador.nth(indice)
            if elemento.is_visible():
                elementos.append(elemento)
        return elementos

    def boton(self, texto, dentro=None):
        """El único botón visible con ese texto."""
        base = self.pagina
        if dentro is not None:
            base = dentro
        botones = self.visibles(
            base.get_by_role("button", name=texto, exact=True)
        )
        if len(botones) != 1:
            raise AssertionError(
                "Se esperaba un botón visible '"
                + texto
                + "' y hay "
                + str(len(botones))
            )
        return botones[0]

    def hay_boton(self, texto):
        return (
            len(
                self.visibles(
                    self.pagina.get_by_role("button", name=texto, exact=True)
                )
            )
            > 0
        )

    def habilitado(self, texto):
        return self.boton(texto).is_enabled()

    def pulsar(self, texto, dentro=None):
        self.boton(texto, dentro).click()
        self.esperar()
        self.capturar("pulsar")

    def pulsar_y_esperar_mensaje(self, texto):
        """Pulsa un botón que lanza una operación y espera su mensaje.

        Separar, preprocesar o crear el modelo con 20.640 filas tarda un
        poco sin que cambie nada en pantalla: se espera a que la aplicación
        muestre el mensaje del resultado (éxito, aviso o error).
        """
        antes = len(self.mensajes())
        boton = self.boton(texto)
        if not boton.is_enabled():
            # Deshabilitado: no hace nada (lo comprueba el test)
            boton.click(force=True)
            self.esperar()
            return
        boton.click()
        esperado = 0
        while esperado < ESPERA_MAXIMA and len(self.mensajes()) <= antes:
            self.pagina.wait_for_timeout(INTERVALO)
            esperado = esperado + INTERVALO
        self.esperar()
        self.capturar("pulsar")

    def pestanas(self):
        """Nombres de las pestañas visibles."""
        nombres = []
        for pestana in self.visibles(self.pagina.get_by_role("tab")):
            # textContent: el texto real, sin las mayúsculas del CSS
            nombres.append(" ".join(pestana.text_content().split()))
        return nombres

    def pestana(self, nombre):
        """Va a una pestaña ("Inicio", "Datos", "Modelo"...)."""
        pestanas = self.visibles(
            self.pagina.get_by_role("tab", name=nombre, exact=True)
        )
        if len(pestanas) != 1:
            raise AssertionError(
                "No se ve la pestaña '"
                + nombre
                + "'. Visibles: "
                + ", ".join(self.pestanas())
            )
        pestanas[0].click()
        self.esperar()

    def texto(self):
        """Todo el texto visible de la página."""
        return self.pagina.locator("body").inner_text()

    def dialogo(self):
        """El diálogo abierto (el último, si hay varios)."""
        dialogos = self.visibles(self.pagina.get_by_role("dialog"))
        if not dialogos:
            raise AssertionError("No hay ningún diálogo abierto")
        return dialogos[-1]

    def texto_dialogo(self):
        """Texto real del diálogo abierto (sin las mayúsculas del CSS)."""
        return " ".join(self.dialogo().text_content().split())

    def hay_dialogo(self):
        return len(self.visibles(self.pagina.get_by_role("dialog"))) > 0

    def campo(self, etiqueta, dentro=None):
        base = self.pagina
        if dentro is not None:
            base = dentro
        for rol in ("textbox", "spinbutton"):
            campos = self.visibles(
                base.get_by_role(rol, name=etiqueta, exact=True)
            )
            if len(campos) == 1:
                return campos[0]
        campos = self.visibles(base.get_by_label(etiqueta, exact=True))
        if len(campos) == 1:
            return campos[0]
        raise AssertionError("No hay un campo visible '" + etiqueta + "'")

    def escribir(self, etiqueta, valor, dentro=None):
        self.campo(etiqueta, dentro).fill(str(valor))
        self.esperar()

    # --- Explorador de archivos ---

    def entradas_explorador(self):
        """Nombres de las carpetas y archivos que muestra el explorador."""
        nombres = []
        etiquetas = self.dialogo().locator(".q-item__label")
        for indice in range(etiquetas.count()):
            nombres.append(etiquetas.nth(indice).inner_text().strip())
        return nombres

    def ir_a_carpeta(self, carpetas):
        """En el explorador abierto, va a ``data/<carpetas...>``.

        La aplicación de pruebas tiene ``data/`` como carpeta personal, así
        que se empieza pulsando el botón de la carpeta personal.
        """
        dialogo = self.dialogo()
        # El botón de la carpeta personal solo tiene el icono "home"
        icono = self.pagina.locator("i", has_text=re.compile("^home$"))
        dialogo.locator("button", has=icono).first.click()
        self.esperar()
        for carpeta in carpetas:
            self.pulsar_entrada(carpeta)

    def pulsar_entrada(self, nombre):
        """Pulsa una carpeta o archivo del explorador por su nombre."""
        exacto = re.compile("^\\s*" + re.escape(nombre) + "\\s*$")
        dialogo = self.dialogo()
        etiqueta = self.pagina.locator(".q-item__label", has_text=exacto)
        entradas = self.visibles(
            dialogo.get_by_role("listitem").filter(has=etiqueta)
        )
        if len(entradas) != 1:
            raise AssertionError(
                "El explorador no muestra '"
                + nombre
                + "'. Muestra: "
                + ", ".join(self.entradas_explorador())
            )
        entradas[0].click()
        self.esperar()

    def elegir_archivo(self, nombre):
        """Pulsa un archivo del explorador y espera a que la aplicación lo
        abra: que se cierre el explorador y salga su mensaje (éxito o
        error). Cargar un archivo grande tarda unos segundos sin que cambie
        nada en pantalla."""
        antes = len(self.mensajes())
        dialogos = len(self.visibles(self.pagina.get_by_role("dialog")))
        self.pulsar_entrada(nombre)
        esperado = 0
        while esperado < ESPERA_MAXIMA:
            abiertos = len(self.visibles(self.pagina.get_by_role("dialog")))
            if abiertos < dialogos and len(self.mensajes()) > antes:
                break
            self.pagina.wait_for_timeout(INTERVALO)
            esperado = esperado + INTERVALO
        self.esperar()

    def abrir_explorador_dataset(self, confirmar=True):
        """Pulsa "Subir dataset" (o "Cargar otro" si ya hay uno)."""
        if not self.hay_boton("Subir dataset") and not self.hay_boton(
            "Cargar otro"
        ):
            if "Datos" in self.pestanas():
                self.pestana("Datos")
            else:
                self.pestana("Inicio")
        if self.hay_boton("Subir dataset"):
            self.pulsar("Subir dataset")
        else:
            self.pulsar("Cargar otro")
        self._responder_confirmacion("Cambios sin guardar", confirmar)

    def cargar(self, archivo, carpetas=(), confirmar=True):
        """Carga un dataset de ``data/<carpetas>/<archivo>`` (PR-2)."""
        self.abrir_explorador_dataset(confirmar)
        if not self.hay_dialogo():
            return
        self.ir_a_carpeta(carpetas)
        self.elegir_archivo(archivo)
        self.capturar("cargar")

    def cargar_d1(self):
        """Carga el dataset de ejemplo en CSV (D-1)."""
        self.cargar("housing1.csv")

    def _responder_confirmacion(self, titulo, aceptar):
        """Si hay una confirmación con ese título, la acepta o la cancela."""
        if not self.hay_dialogo():
            return False
        dialogo = self.dialogo()
        # textContent: el texto real, sin las mayúsculas del CSS
        if titulo not in dialogo.text_content():
            return False
        if aceptar:
            botones = self.visibles(dialogo.get_by_role("button"))
            botones[-1].click()
        else:
            dialogo.get_by_role("button", name="Cancelar", exact=True).click()
        self.esperar()
        return True

    # --- Pestaña Datos ---

    def ruta(self):
        self.pestana("Datos")
        return self.pagina.locator(".font-mono").first.inner_text().strip()

    def resumen(self):
        self.pestana("Datos")
        resumen = self.pagina.get_by_text(
            re.compile(r"^\d+ filas y \d+ columnas$")
        )
        return resumen.first.inner_text().strip()

    def columnas_tabla(self):
        self.pestana("Datos")
        cabeceras = self.pagina.get_by_role("columnheader")
        nombres = []
        for cabecera in self.visibles(cabeceras):
            # Sin el texto de los iconos (la flecha de ordenar)
            texto = cabecera.evaluate(
                "(th) => Array.from(th.childNodes)"
                ".filter((n) => !(n instanceof Element && n.matches('i'))"
                ").map((n) => n.textContent).join('')"
            )
            nombres.append(texto.strip())
        return nombres

    # --- Columnas y separación ---

    def opciones(self, selector):
        """Opciones que ofrece un desplegable."""
        self.pestana("Variables y separacion")
        self.pagina.get_by_role("combobox", name=selector).click()
        self.pagina.wait_for_timeout(400)
        nombres = []
        for opcion in self.visibles(self.pagina.get_by_role("option")):
            nombres.append(opcion.inner_text().strip())
        self.pagina.keyboard.press("Escape")
        self.esperar()
        return nombres

    def marcadas(self, selector):
        """Opciones marcadas en un desplegable."""
        self.pestana("Variables y separacion")
        self.pagina.get_by_role("combobox", name=selector).click()
        self.pagina.wait_for_timeout(400)
        nombres = []
        for opcion in self.visibles(self.pagina.get_by_role("option")):
            if opcion.get_attribute("aria-selected") == "true":
                nombres.append(opcion.inner_text().strip())
        self.pagina.keyboard.press("Escape")
        self.esperar()
        return nombres

    def marcar(self, selector, opciones):
        """Deja marcadas exactamente esas opciones en el desplegable."""
        self.pestana("Variables y separacion")
        self.pagina.get_by_role("combobox", name=selector).click()
        self.pagina.wait_for_timeout(400)
        for opcion in self.visibles(self.pagina.get_by_role("option")):
            nombre = opcion.inner_text().strip()
            marcada = opcion.get_attribute("aria-selected") == "true"
            if marcada != (nombre in opciones):
                opcion.click()
                self.pagina.wait_for_timeout(150)
        self.pagina.keyboard.press("Escape")
        self.esperar()

    def elegir(self, selector, opcion):
        """Elige una opción de un desplegable simple."""
        self.pestana("Variables y separacion")
        self.pagina.get_by_role("combobox", name=selector).click()
        self.pagina.wait_for_timeout(400)
        candidatas = self.visibles(
            self.pagina.get_by_role("option", name=opcion, exact=True)
        )
        if len(candidatas) != 1:
            self.pagina.keyboard.press("Escape")
            raise AssertionError(
                "El desplegable '" + selector + "' no ofrece '" + opcion + "'"
            )
        candidatas[0].click()
        self.pagina.keyboard.press("Escape")
        self.esperar()

    def seleccionar(self, entradas, salida, confirmar=True):
        """Elige las columnas del modelo y las confirma (PR-3)."""
        self.marcar(FEATURES, list(entradas))
        self.elegir(TARGET, salida)
        if confirmar:
            self.pulsar_y_esperar_mensaje("Confirmar selección")

    def separar(self, porcentaje="20", semilla="42"):
        """Separa en entrenamiento y test (PR-4, por defecto 20 % y 42)."""
        self.pestana("Variables y separacion")
        if porcentaje is not None:
            self.escribir("Porcentaje de test (%)", porcentaje)
        if semilla is not None:
            self.escribir("Semilla", semilla)
        self.pulsar_y_esperar_mensaje("Separar datos")

    def resultado_separacion(self):
        self.pestana("Variables y separacion")
        texto = self.pagina.get_by_text(
            re.compile(r"^Entrenamiento: \d+ filas \| Test: \d+ filas$")
        )
        if texto.count() == 0:
            return None
        return texto.first.inner_text().strip()

    # --- Preprocesado ---

    def nulos(self):
        """Valores inexistentes por columna: {columna: (train, test)}."""
        self.pestana("Preprocesado")
        filas = {}
        for fila in self.visibles(self.pagina.locator("tbody tr")):
            celdas = fila.locator("td")
            if celdas.count() < 3:
                continue
            filas[celdas.nth(0).inner_text().strip()] = (
                int(celdas.nth(1).inner_text().strip()),
                int(celdas.nth(2).inner_text().strip()),
            )
        return filas

    def preprocesar(self, estrategia, constante=None):
        self.pestana("Preprocesado")
        self.pagina.get_by_role("radio", name=estrategia, exact=True).click()
        self.esperar()
        if constante is not None:
            self.escribir("Valor constante", constante)
        self.pulsar_y_esperar_mensaje("Aplicar preprocesado")

    # --- Modelo ---

    def puede_crear_modelo(self):
        """True si se puede pulsar "Crear modelo" (pestaña visible y botón
        habilitado)."""
        if "Modelo" not in self.pestanas():
            return False
        self.pestana("Modelo")
        if not self.hay_boton("Crear modelo"):
            return False
        return self.habilitado("Crear modelo")

    def hay_modelo(self):
        """True si se ve un modelo: fórmula y métricas en "Modelo"."""
        if "Modelo" not in self.pestanas():
            return False
        return self.formula() != ""

    def crear_modelo(self):
        self.pestana("Modelo")
        self.pulsar_y_esperar_mensaje("Crear modelo")

    def modelo_lineal(self):
        """Crea el modelo exacto de lineal.csv: y = 2·x1 − 3·x2 + 5."""
        self.cargar("lineal.csv", ["pruebas"])
        self.seleccionar(["x1", "x2"], "y")
        self.separar()
        self.crear_modelo()

    def formula(self):
        """La fórmula del modelo, con espacios normales, o "" si no hay."""
        self.pestana("Modelo")
        for linea in self.texto().splitlines():
            linea = " ".join(linea.replace("\xa0", " ").split())
            if re.match(r"^[^\s=]+ = ", linea):
                return linea
        return ""

    def metricas(self):
        """{"Entrenamiento": {"R²": "...", "ECM": "..."}, "Test": {...}}."""
        self.pestana("Modelo")
        texto = self.texto()
        metricas = {}
        for conjunto in ("Entrenamiento", "Test"):
            patron = re.compile(
                "^"
                + conjunto
                + "\\s*\\nR²:\\s*\\n?(.+?)\\s*\\nECM:\\s*\\n?(.+?)$",
                re.MULTILINE,
            )
            encontrado = patron.search(texto)
            if encontrado:
                metricas[conjunto] = {
                    "R²": encontrado.group(1).strip(),
                    "ECM": encontrado.group(2).strip(),
                }
        return metricas

    def graficos(self):
        self.pestana("Modelo")
        return self.pagina.evaluate(JS_GRAFICOS)

    def descripcion(self):
        self.pestana("Modelo")
        return self.campo("Descripción (opcional)").input_value()

    def escribir_descripcion(self, texto):
        self.pestana("Modelo")
        campo = self.campo("Descripción (opcional)")
        campo.fill(texto)
        campo.blur()
        self.esperar()

    def estado_guardado(self):
        self.pestana("Modelo")
        estado = self.pagina.get_by_text(
            re.compile(r"^(Sin guardar|Guardado en|Cambios sin guardar)")
        )
        if estado.count() == 0:
            return ""
        return estado.first.inner_text().strip()

    def guardar_modelo(self, nombre, carpetas=("pruebas",), sobrescribir=True):
        """Guarda el modelo en ``data/<carpetas>/<nombre>``.

        Returns:
            True si apareció la pregunta de sobrescribir.
        """
        self.pestana("Modelo")
        self.pulsar("Guardar modelo")
        if carpetas is not None:
            self.ir_a_carpeta(carpetas)
        self.escribir("Nombre del archivo", nombre, self.dialogo())
        self.pulsar("Guardar", self.dialogo())
        pregunta = self._responder_confirmacion(
            "El archivo ya existe", sobrescribir
        )
        if pregunta and not sobrescribir and self.hay_dialogo():
            # Se vuelve al diálogo de guardado: se cierra sin guardar
            self.pulsar("Cancelar", self.dialogo())
        self.esperar()
        return pregunta

    def carpeta_explorador(self):
        """Ruta de la carpeta que muestra el explorador o el diálogo."""
        etiqueta = self.dialogo().locator(".break-all").first
        return etiqueta.inner_text().strip()

    def archivos_en(self, *carpetas):
        """Nombres de los archivos de ``data/<carpetas>`` en el disco."""
        from probador_llm.ejecutor import RAIZ

        carpeta = RAIZ / "data"
        for parte in carpetas:
            carpeta = carpeta / parte
        nombres = []
        for ruta in carpeta.iterdir():
            if ruta.is_file():
                nombres.append(ruta.name)
        return sorted(nombres)

    def abrir_explorador_modelo(self, confirmar=True):
        if "Inicio" in self.pestanas():
            self.pestana("Inicio")
        self.pulsar("Cargar modelo")
        return self._responder_confirmacion("Cambios sin guardar", confirmar)

    def cargar_modelo(self, archivo, carpetas=("pruebas",), confirmar=True):
        """Carga un modelo guardado de ``data/<carpetas>/<archivo>``."""
        self.abrir_explorador_modelo(confirmar)
        if not self.hay_dialogo():
            return
        self.ir_a_carpeta(carpetas)
        self.elegir_archivo(archivo)
        self.capturar("cargar_modelo")

    def asegurar_modelo_guardado(self, nombre, descripcion=""):
        """Crea y guarda el modelo de lineal.csv si el archivo no existe."""
        self.modelo_lineal()
        if descripcion:
            self.escribir_descripcion(descripcion)
        self.guardar_modelo(nombre)

    # --- Predicción ---

    def tarjeta_prediccion(self):
        self.pestana("Modelo")
        tarjetas = self.visibles(
            self.pagina.locator(".q-card").filter(
                has=self.pagina.get_by_text("Prediccion", exact=True)
            )
        )
        if not tarjetas:
            return None
        return tarjetas[-1]

    def campos_prediccion(self):
        """Etiquetas de los campos de la sección de predicción."""
        tarjeta = self.tarjeta_prediccion()
        if tarjeta is None:
            return []
        nombres = []
        for etiqueta in self.visibles(tarjeta.locator(".q-field__label")):
            nombres.append(etiqueta.inner_text().strip())
        return nombres

    def predecir(self, valores):
        """Escribe los valores y pulsa "Realizar predicción".

        Returns:
            El texto del resultado, o "" si no hay.
        """
        self.pestana("Modelo")
        for columna, valor in valores.items():
            self.escribir(columna, valor)
        self.pulsar("Realizar predicción")
        return self.resultado_prediccion()

    def resultado_prediccion(self):
        self.pestana("Modelo")
        resultado = self.pagina.locator(".text-xl.font-medium.text-secondary")
        visibles = self.visibles(resultado)
        if not visibles:
            return ""
        return visibles[0].inner_text().strip()


FEATURES = "Features (selección múltiple)"
TARGET = "Target (columna de salida)"

# Estrategias de preprocesado (textos de la aplicación)
ELIMINAR = "Eliminar filas con valores inexistentes"
MEDIA = "Rellenar con la media (de entrenamiento)"
MEDIANA = "Rellenar con la mediana (de entrenamiento)"
CONSTANTE = "Rellenar con un valor constante"

# Datos del dataset de ejemplo (sección 2.1 del plan)
FILAS = 20640
COLUMNAS = [
    "longitude",
    "latitude",
    "housing_median_age",
    "total_rooms",
    "total_bedrooms",
    "population",
    "households",
    "median_income",
    "median_house_value",
    "ocean_proximity",
]
E1 = "median_income"
E2 = "housing_median_age"
S = "median_house_value"
C_NAN = "total_bedrooms"
N_NAN = 207
C_TXT = "ocean_proximity"
