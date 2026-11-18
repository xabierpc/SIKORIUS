"""Asistente con LLM: conversación, cambios propuestos y deshacer.

Flujo de un cambio al dataset:

1. ``enviar`` manda la petición a la LLM junto con un resumen del trabajo
   actual. La LLM contesta con un mensaje y, si hace falta, una lista de
   operaciones del catálogo de ``dominio.transformaciones``.
2. Las operaciones se prueban sobre una copia: si alguna no se puede
   aplicar, se avisa y no hay propuesta. Si todas van bien, quedan como
   ``propuesta`` con una frase por cambio ("se eliminan 37 filas").
3. El usuario decide: ``confirmar`` sustituye el dataset de la sesión (y,
   como cualquier dataset nuevo, borra los pasos posteriores) y
   ``descartar`` la olvida.
4. ``deshacer`` vuelve al dataset anterior a la última confirmación.

No importa NiceGUI. La LLM concreta (Groq) se crea en ``datos``; aquí solo
se usa a través de ``ClienteLLM``, así en los tests se pasa una falsa.
"""

from dataclasses import dataclass
from typing import Protocol

from sikorius.datos.cliente_groq import VARIABLE_CLAVE, crear_cliente_groq
from sikorius.dominio.asistente import construir_contexto
from sikorius.dominio.errores import ErrorAsistente, ErrorTransformacion
from sikorius.dominio.transformaciones import aplicar_operaciones

# Mensajes anteriores (usuario y asistente) que se reenvían a la LLM para
# que recuerde la conversación
MENSAJES_RECORDADOS = 10
# Veces seguidas que se puede deshacer
MAXIMO_DESHACER = 10

MENSAJE_SIN_CLAVE = (
    "El asistente está desactivado. Para activarlo, crea un archivo .env en "
    "la carpeta del proyecto con la línea " + VARIABLE_CLAVE + "=tu_clave "
    "(la clave se saca gratis en console.groq.com) y vuelve a arrancar "
    "SIKORIUS."
)


class ClienteLLM(Protocol):
    """Lo que el asistente necesita de una LLM."""

    async def responder(self, conversacion, contexto):
        """Devuelve un ``RespuestaAsistente`` o lanza ``ErrorAsistente``."""


@dataclass(frozen=True, eq=False)
class Propuesta:
    """Cambios al dataset pendientes de confirmar.

    base es el ``Dataset`` de la sesión sobre el que se calcularon: si la
    sesión cambia de dataset, la propuesta deja de valer.
    """

    base: object
    operaciones: tuple
    descripciones: tuple
    datos: object  # DataFrame ya transformado
    filas_antes: int
    filas_despues: int


@dataclass(frozen=True)
class Mensaje:
    """Un mensaje del chat. rol es "usuario" o "asistente"."""

    rol: str
    texto: str


class Asistente:
    """Conversación con la LLM sobre el trabajo de una sesión."""

    def __init__(self, sesion, cliente=None, usar_groq=True):
        """
        Args:
            sesion: La ``Sesion`` de la aplicación.
            cliente: LLM a usar. Si es None y usar_groq es True, se crea
                el de Groq con la clave del entorno (si la hay).
            usar_groq: False para no buscar la clave (tests).
        """
        self.sesion = sesion
        if cliente is None and usar_groq:
            cliente = crear_cliente_groq()
        self._cliente = cliente
        self._mensajes = []
        self._propuesta = None
        # Pila de (Dataset anterior, Dataset que lo sustituyó)
        self._deshacer = []

    # --- Estado ---

    @property
    def disponible(self):
        """True si hay una LLM configurada."""
        return self._cliente is not None

    @property
    def mensajes(self):
        """Mensajes del chat, del más antiguo al más reciente."""
        return tuple(self._mensajes)

    @property
    def propuesta(self):
        """Cambios pendientes de confirmar (``Propuesta``) o None."""
        if (
            self._propuesta is not None
            and self.sesion.dataset is not self._propuesta.base
        ):
            self._propuesta = None
        return self._propuesta

    def puede_deshacer(self):
        """True si el dataset actual es el de la última confirmación.

        Si después se ha cargado otro archivo (o se ha borrado el dataset),
        lo que había antes ya no es "deshacer" y se olvida.
        """
        if not self._deshacer:
            return False
        _, puesto = self._deshacer[-1]
        if self.sesion.dataset is not puesto:
            self._deshacer.clear()
            return False
        return True

    # --- Conversación ---

    async def enviar(self, texto, etapa=None):
        """Manda una petición del usuario y espera la respuesta.

        Args:
            texto: Lo que ha escrito el usuario.
            etapa: Pestaña en la que está, para darle contexto a la LLM.

        Returns:
            El ``Mensaje`` del asistente, ya añadido al chat. Si propone
            cambios, quedan en ``propuesta``.

        Raises:
            ErrorAsistente: Si no hay LLM, falla la petición o los cambios
                propuestos no se pueden aplicar. El mensaje del usuario se
                queda en el chat; la respuesta no.
        """
        texto = (texto or "").strip()
        if texto == "":
            raise ErrorAsistente("Escribe algo para el asistente.")
        if not self.disponible:
            raise ErrorAsistente(MENSAJE_SIN_CLAVE)
        self._propuesta = None
        self._mensajes.append(Mensaje("usuario", texto))
        respuesta = await self._cliente.responder(
            self._conversacion(), self._contexto(etapa)
        )
        if respuesta.operaciones:
            self._propuesta = self._preparar(respuesta.operaciones)
        mensaje = Mensaje("asistente", respuesta.mensaje.strip())
        self._mensajes.append(mensaje)
        return mensaje

    def borrar_conversacion(self):
        """Empieza una conversación nueva (no deshace cambios)."""
        self._mensajes.clear()
        self._propuesta = None

    def _conversacion(self):
        recientes = self._mensajes[-MENSAJES_RECORDADOS:]
        resultado = []
        for mensaje in recientes:
            if mensaje.rol == "usuario":
                rol = "user"
            else:
                rol = "assistant"
            resultado.append({"role": rol, "content": mensaje.texto})
        return resultado

    def _contexto(self, etapa):
        sesion = self.sesion
        datos = None
        if sesion.dataset is not None:
            datos = sesion.dataset.datos
        seleccion = None
        if sesion.seleccion is not None:
            seleccion = (sesion.seleccion.features, sesion.seleccion.target)
        return construir_contexto(
            datos=datos,
            seleccion=seleccion,
            modelo=sesion.modelo,
            metricas=sesion.metricas_modelo(),
            etapa=etapa,
        )

    def _preparar(self, operaciones):
        """Prueba las operaciones sobre una copia del dataset."""
        if self.sesion.dataset is None:
            raise ErrorAsistente(
                "El asistente ha propuesto cambios, pero no hay ningún "
                "dataset cargado."
            )
        original = self.sesion.dataset.datos
        try:
            datos, descripciones = aplicar_operaciones(original, operaciones)
        except ErrorTransformacion as error:
            raise ErrorAsistente(
                "El asistente ha propuesto un cambio que no se puede "
                "aplicar. " + str(error)
            ) from error
        return Propuesta(
            self.sesion.dataset,
            tuple(operaciones),
            tuple(descripciones),
            datos,
            len(original),
            len(datos),
        )

    # --- Cambios ---

    def confirmar(self):
        """Aplica la propuesta: el dataset transformado sustituye al actual.

        Como al cargar cualquier dataset, se borran la selección de
        columnas, la separación, el preprocesado y el modelo.

        Raises:
            ErrorAsistente: Si no hay propuesta.
        """
        propuesta = self.propuesta
        if propuesta is None:
            raise ErrorAsistente("No hay cambios pendientes de aplicar.")
        anterior = self.sesion.dataset
        self._propuesta = None
        self.sesion.cargar_dataset(propuesta.datos, anterior.ruta)
        self._deshacer.append((anterior, self.sesion.dataset))
        del self._deshacer[:-MAXIMO_DESHACER]

    def descartar(self):
        """Olvida la propuesta sin cambiar nada."""
        self._propuesta = None

    def deshacer(self):
        """Vuelve al dataset que había antes de la última confirmación.

        Raises:
            ErrorAsistente: Si no hay nada que deshacer.
        """
        if not self.puede_deshacer():
            raise ErrorAsistente("No hay cambios del asistente que deshacer.")
        anterior, _ = self._deshacer.pop()
        self._propuesta = None
        self.sesion.cargar_dataset(anterior.datos, anterior.ruta)
        if self._deshacer:
            # El dataset recuperado es otro objeto: la entrada anterior de
            # la pila tiene que apuntar a él para poder seguir deshaciendo
            previo, _ = self._deshacer[-1]
            self._deshacer[-1] = (previo, self.sesion.dataset)
