"""Lectura del plan de pruebas (docs/plan_pruebas.md).

Separa el plan en casos de prueba y prepara el texto que recibe el agente:

- Sustituye las claves del glosario (``⟨B_CREAR_MODELO⟩``) por el texto que
  se ve en la aplicación ("Crear modelo").
- Detecta los huecos que el equipo aún no ha rellenado (``⟨FILAS⟩``): un
  caso con huecos no se puede ejecutar.
- Detecta de qué casos depende cada uno, según sus precondiciones.
"""

import re
from dataclasses import dataclass, field

# "#### CP-07. Título del caso"
PATRON_CASO = re.compile(r"^#### (CP-\d+)\. (.+)$", re.MULTILINE)
# Cualquier cosa entre ⟨ y ⟩
PATRON_HUECO = re.compile("⟨([^⟩]+)⟩")
# "CP-58 ejecutado" en las precondiciones
PATRON_REQUISITO = re.compile(r"(CP-\d+) ejecutado")
# Cualquier mención a otro caso ("como CP-35", "los pasos 1 a 3 de CP-35")
PATRON_MENCION_CASO = re.compile(r"CP-\d+")
# Clave del glosario: mayúsculas y guiones bajos
PATRON_CLAVE = re.compile(r"^[A-Z][A-Z0-9_]*$")

TITULO_GLOSARIO = "### 1.3"

# Párrafos del contexto que solo sirven a quien prepara las pruebas a mano
SIN_INTERES = (
    "Para crear un archivo de texto",
    "Estos archivos los crea",
    "Algunos casos repiten",
    "Los archivos de datos",
    "Los tres archivos contienen",
    "**Bloque",
)
TITULO_CONTEXTO = "### 1.2"
TITULO_FIN_CONTEXTO = "## 3."


@dataclass
class Caso:
    """Un caso de prueba del plan.

    Attributes:
        id: Identificador, por ejemplo "CP-07".
        titulo: Título del caso.
        texto: Texto completo del caso, con el glosario ya sustituido.
        requisitos: Casos que deben haberse ejecutado antes (por ejemplo,
            porque crean un archivo que este caso usa).
        misma_sesion: True si el caso continúa con la aplicación tal como
            la dejó su primer requisito ("sin cerrar la aplicación").
        huecos: Valores que el equipo aún no ha rellenado.
        citados: Otros casos que el texto menciona (por ejemplo, "como
            CP-35"). El agente recibe su texto como referencia.
        reinicio: True si el caso necesita la aplicación recién abierta.
            Si no, continúa con lo que dejó el caso anterior.
    """

    id: str
    titulo: str
    texto: str
    requisitos: list = field(default_factory=list)
    misma_sesion: bool = False
    huecos: list = field(default_factory=list)
    citados: list = field(default_factory=list)
    reinicio: bool = False

    @property
    def numero(self):
        return int(self.id.split("-")[1])


@dataclass
class Plan:
    """El plan de pruebas ya preparado para el agente.

    Attributes:
        casos: Diccionario id -> Caso, en el orden del plan.
        contexto: Procedimientos comunes, glosario y datos de prueba, que
            el agente necesita para entender los casos.
        glosario: Diccionario clave -> texto de la aplicación.
    """

    casos: dict
    contexto: str
    glosario: dict

    def orden(self, casos):
        """Orden en que se ejecutan los casos elegidos.

        Es el orden del plan, salvo que un caso que continúa a otro ("CP-47
        ejecutado, sin cerrar la aplicación") se ejecuta justo después de
        él, aunque en el plan esté más adelante o más atrás. Así continúa
        exactamente donde lo dejó el anterior, sin repetir sus pasos.
        """
        elegidos = []
        for caso in casos:
            elegidos.append(caso.id)
        hijos = {}
        for caso in casos:
            padre = self.padre(caso)
            if padre is not None and padre.id in elegidos:
                hijos.setdefault(padre.id, []).append(caso)
        orden = []
        emitidos = set()

        def emitir(caso):
            if caso.id in emitidos:
                return
            emitidos.add(caso.id)
            orden.append(caso)
            for hijo in hijos.get(caso.id, []):
                emitir(hijo)

        for caso in casos:
            padre = self.padre(caso)
            if padre is not None and padre.id in elegidos:
                # Se ejecuta cuando le toque a su padre
                continue
            emitir(caso)
        # Por si hubiera un ciclo en el plan: no se pierde ningún caso
        for caso in casos:
            emitir(caso)
        return orden

    def padre(self, caso):
        """Caso al que continúa ``caso`` sin cerrar la aplicación, o None."""
        if not caso.misma_sesion or not caso.requisitos:
            return None
        return self.casos.get(caso.requisitos[0])

    def referencias(self, caso):
        """Casos citados por ``caso`` que no se repiten como preparación."""
        preparacion = self.preparacion(caso)
        referencias = []
        for identificador in caso.citados:
            citado = self.casos.get(identificador)
            if citado is not None and citado not in preparacion:
                referencias.append(citado)
        return referencias

    def preparacion(self, caso):
        """Casos que hay que repetir antes de ``caso`` en la misma sesión.

        Si un caso empieza "con CP-55 ejecutado, sin cerrar la aplicación",
        con la aplicación recién abierta primero hay que hacer CP-55 (y, si
        CP-55 también continúa a otro, ese otro antes). Se devuelven en el
        orden en que hay que hacerlos.
        """
        cadena = []
        actual = caso
        while actual.misma_sesion and actual.requisitos:
            anterior = self.casos.get(actual.requisitos[0])
            if anterior is None or anterior in cadena:
                break
            cadena.insert(0, anterior)
            actual = anterior
        return cadena


def leer_glosario(texto):
    """Lee la tabla del glosario (sección 1.3).

    Las filas tienen la forma ``| CLAVE | texto | tipo |``. Una fila puede
    tener varias claves separadas por " / ", con sus textos en el mismo
    orden ("O_MEDIA / O_MEDIANA | Media / Mediana").

    Returns:
        Diccionario clave -> texto. Si no hay glosario, vacío.
    """
    glosario = {}
    inicio = texto.find(TITULO_GLOSARIO)
    if inicio < 0:
        return glosario
    fin = texto.find("\n#", inicio + len(TITULO_GLOSARIO))
    if fin < 0:
        fin = len(texto)
    for linea in texto[inicio:fin].splitlines():
        celdas = _celdas(linea)
        if len(celdas) < 2:
            continue
        claves = _partir(celdas[0])
        valores = _partir(celdas[1])
        if len(claves) != len(valores):
            continue
        for clave, valor in zip(claves, valores, strict=True):
            if PATRON_CLAVE.match(clave):
                glosario[clave] = _quitar_comillas(valor)
    return glosario


def sustituir_glosario(texto, glosario):
    """Cambia cada ``⟨CLAVE⟩`` del glosario por su texto."""
    for clave, valor in glosario.items():
        texto = texto.replace("⟨" + clave + "⟩", valor)
    return texto


def leer_plan(texto):
    """Lee el plan completo.

    Args:
        texto: Contenido de ``docs/plan_pruebas.md``.

    Returns:
        Un ``Plan`` con los casos y el contexto.

    Raises:
        ValueError: Si el texto no contiene ningún caso de prueba.
    """
    glosario = leer_glosario(texto)
    sustituido = sustituir_glosario(texto, glosario)

    contexto = ""
    inicio = sustituido.find(TITULO_CONTEXTO)
    fin = sustituido.find(TITULO_FIN_CONTEXTO)
    if inicio >= 0 and fin > inicio:
        contexto = compactar_contexto(sustituido[inicio:fin].strip())

    coincidencias = list(PATRON_CASO.finditer(sustituido))
    if not coincidencias:
        raise ValueError("El plan no contiene casos de prueba (#### CP-..)")

    casos = {}
    for indice, coincidencia in enumerate(coincidencias):
        principio = coincidencia.start()
        if indice + 1 < len(coincidencias):
            final = coincidencias[indice + 1].start()
        else:
            final = _fin_de_casos(sustituido, principio)
        bloque = sustituido[principio:final].strip()
        # Se quitan los separadores de sección que quedan al final
        bloque = re.sub(r"\n(---|###[^\n]*|>[^\n]*|\s)*$", "", bloque)
        casos[coincidencia.group(1)] = _crear_caso(
            coincidencia.group(1), coincidencia.group(2).strip(), bloque
        )
    return Plan(casos=casos, contexto=contexto, glosario=glosario)


def compactar_contexto(texto):
    """Quita del contexto lo que el agente no necesita, para gastar menos.

    - El procedimiento PR-1 (abrir la aplicación): lo hace el probador.
    - Las tablas pasan a listas: del glosario, "texto: dónde"; de los
      archivos creados, "F-n: ruta (para qué)".
    - Los bloques de código con el contenido de los archivos y las
      instrucciones para crearlos: los crea el probador.
    """
    lineas = texto.splitlines()
    salida = []
    en_codigo = False
    en_pr1 = False
    for linea in lineas:
        limpia = linea.strip()
        if limpia.startswith("```"):
            en_codigo = not en_codigo
            continue
        if en_codigo:
            continue
        if limpia.startswith("**PR-1."):
            en_pr1 = True
            continue
        if en_pr1:
            if limpia.startswith("**PR-") or limpia.startswith("#"):
                en_pr1 = False
            else:
                continue
        if limpia == "---" or limpia.startswith(SIN_INTERES):
            continue
        celdas = _celdas(linea)
        if celdas:
            fila = _fila_compacta(celdas)
            if fila:
                salida.append(fila)
            continue
        if limpia or (salida and salida[-1] != ""):
            salida.append(linea.rstrip())
    return "\n".join(salida).strip()


def _fila_compacta(celdas):
    """Una fila de tabla como línea de lista, o "" si es cabecera."""
    primera = celdas[0]
    if not primera or set(primera) <= set("-: "):
        return ""
    if primera in ("Clave", "Dato", "Id", "Caso"):
        return ""
    if PATRON_CLAVE.match(primera) or " / " in primera:
        # Glosario: la clave ya está sustituida en los casos
        if len(celdas) >= 3 and celdas[2]:
            return "- " + celdas[1] + ": " + celdas[2]
        return "- " + celdas[1]
    if re.match(r"^F-\d+$", primera) and len(celdas) >= 4:
        return "- " + primera + ": " + celdas[1] + " (" + celdas[3] + ")"
    resto = []
    for celda in celdas[1:]:
        if celda and celda != "-":
            resto.append(celda)
    return "- " + primera + ": " + "; ".join(resto)


def elegir_casos(plan, seleccion):
    """Devuelve los casos indicados, en el orden del plan.

    Args:
        plan: El plan leído.
        seleccion: Texto como "CP-01,CP-05" o "CP-30:CP-40", o mezclas
            separadas por comas. Vacío o None: todos.

    Raises:
        ValueError: Si se pide un caso que no existe.
    """
    if not seleccion:
        return list(plan.casos.values())
    numeros = set()
    for parte in seleccion.split(","):
        parte = parte.strip().upper()
        if not parte:
            continue
        if ":" in parte:
            desde, hasta = parte.split(":", 1)
            for numero in range(_numero(desde), _numero(hasta) + 1):
                numeros.add(numero)
        else:
            numeros.add(_numero(parte))
    elegidos = []
    existentes = set()
    for caso in plan.casos.values():
        existentes.add(caso.numero)
        if caso.numero in numeros:
            elegidos.append(caso)
    for numero in sorted(numeros):
        if numero not in existentes:
            raise ValueError("No existe el caso CP-%02d" % numero)
    return elegidos


def _crear_caso(identificador, titulo, bloque):
    precondiciones = ""
    for linea in bloque.splitlines():
        if "**Precondiciones" in linea:
            precondiciones = linea
            break
    requisitos = PATRON_REQUISITO.findall(precondiciones)
    misma_sesion = "sin cerrar la aplicación" in precondiciones
    reinicio = "recién abierta" in precondiciones and not misma_sesion
    huecos = []
    for hueco in PATRON_HUECO.findall(bloque):
        if hueco not in huecos:
            huecos.append(hueco)
    citados = []
    for mencion in PATRON_MENCION_CASO.findall(bloque):
        if mencion != identificador and mencion not in citados:
            citados.append(mencion)
    return Caso(
        id=identificador,
        titulo=titulo,
        texto=bloque,
        requisitos=requisitos,
        misma_sesion=misma_sesion,
        huecos=huecos,
        citados=citados,
        reinicio=reinicio,
    )


def _fin_de_casos(texto, desde):
    """Posición donde acaba el último caso: la siguiente sección "## "."""
    siguiente = re.search(r"^## ", texto[desde:], re.MULTILINE)
    if siguiente is None:
        return len(texto)
    return desde + siguiente.start()


def _celdas(linea):
    linea = linea.strip()
    if not linea.startswith("|"):
        return []
    celdas = []
    for celda in linea.strip("|").split("|"):
        celdas.append(celda.strip())
    return celdas


def _partir(celda):
    partes = []
    for parte in celda.split(" / "):
        partes.append(parte.strip())
    return partes


def _quitar_comillas(valor):
    if len(valor) >= 2 and valor[0] == "`" and valor[-1] == "`":
        return valor[1:-1]
    return valor


def _numero(texto):
    texto = texto.strip().upper()
    if texto.startswith("CP-"):
        texto = texto[3:]
    if not texto.isdigit():
        raise ValueError("Caso no válido: " + texto)
    return int(texto)
