"""Pruebas del asistente con una LLM falsa: sin red ni clave.

uv run pytest tests/aplicacion/test_asistente.py -v
"""

import asyncio

import pandas as pd
import pytest

from sikorius.aplicacion.asistente import (
    MENSAJES_RECORDADOS,
    Asistente,
)
from sikorius.dominio.asistente import RespuestaAsistente
from sikorius.dominio.errores import ErrorAsistente
from sikorius.dominio.transformaciones import Operacion


def op(tipo, columna=None, operador=None, valor=None):
    return Operacion(
        tipo=tipo,
        columna=columna,
        operador=operador,
        valor=valor,
        nombre_nuevo=None,
    )


class LLMFalsa:
    """Devuelve las respuestas preparadas, en orden, y guarda lo recibido."""

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []

    async def responder(self, conversacion, contexto):
        self.llamadas.append((conversacion, contexto))
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


def respuesta(mensaje="Vale", *operaciones):
    return RespuestaAsistente(mensaje=mensaje, operaciones=list(operaciones))


def enviar(asistente, texto="hola", etapa=None):
    return asyncio.run(asistente.enviar(texto, etapa=etapa))


@pytest.fixture
def con_datos(sesion, datos):
    sesion.cargar_dataset(datos, "datos.csv")
    return sesion


def test_sin_llm_no_esta_disponible(sesion):
    asistente = Asistente(sesion, usar_groq=False)
    assert not asistente.disponible
    with pytest.raises(ErrorAsistente, match="GROQ_API_KEY"):
        enviar(asistente)


def test_texto_vacio(sesion):
    asistente = Asistente(sesion, LLMFalsa())
    with pytest.raises(ErrorAsistente):
        enviar(asistente, "   ")


def test_solo_explica(con_datos):
    llm = LLMFalsa(respuesta("El dataset tiene 10 filas"))
    asistente = Asistente(con_datos, llm)
    mensaje = enviar(asistente, "explícame", etapa="Datos")
    assert mensaje.texto == "El dataset tiene 10 filas"
    assert [m.rol for m in asistente.mensajes] == ["usuario", "asistente"]
    assert asistente.propuesta is None
    conversacion, contexto = llm.llamadas[0]
    assert conversacion == [{"role": "user", "content": "explícame"}]
    assert "10 filas" in contexto
    assert "pestaña: Datos" in contexto


def test_recuerda_la_conversacion_reciente(sesion):
    llm = LLMFalsa(*[respuesta(str(i)) for i in range(8)])
    asistente = Asistente(sesion, llm)
    for i in range(8):
        enviar(asistente, "p" + str(i))
    conversacion, _ = llm.llamadas[-1]
    assert len(conversacion) == MENSAJES_RECORDADOS
    assert conversacion[-1] == {"role": "user", "content": "p7"}
    assert conversacion[-2] == {"role": "assistant", "content": "6"}


def test_propone_sin_cambiar_la_sesion(con_datos, datos):
    llm = LLMFalsa(respuesta("Quito nulos", op("eliminar_filas_con_nulos")))
    asistente = Asistente(con_datos, llm)
    dataset = con_datos.dataset
    enviar(asistente)
    propuesta = asistente.propuesta
    assert propuesta.filas_antes == 10
    assert propuesta.filas_despues == 9
    assert con_datos.dataset is dataset


def test_confirmar_y_deshacer(sesion_separada, datos):
    llm = LLMFalsa(respuesta("Fuera x2", op("eliminar_columna", "x2")))
    asistente = Asistente(sesion_separada, llm)
    ruta = sesion_separada.dataset.ruta
    enviar(asistente)
    asistente.confirmar()
    assert list(sesion_separada.dataset.datos.columns) == ["x1", "y"]
    assert sesion_separada.dataset.ruta == ruta
    assert sesion_separada.seleccion is None  # se borran los pasos
    assert asistente.propuesta is None
    assert asistente.puede_deshacer()
    asistente.deshacer()
    pd.testing.assert_frame_equal(sesion_separada.dataset.datos, datos)
    assert not asistente.puede_deshacer()


def test_deshacer_varias_veces(con_datos, datos):
    llm = LLMFalsa(
        respuesta("1", op("eliminar_columna", "x2")),
        respuesta("2", op("eliminar_filas_con_nulos")),
    )
    asistente = Asistente(con_datos, llm)
    enviar(asistente)
    asistente.confirmar()
    enviar(asistente)
    asistente.confirmar()
    assert len(con_datos.dataset.datos) == 9
    asistente.deshacer()
    assert len(con_datos.dataset.datos) == 10
    assert list(con_datos.dataset.datos.columns) == ["x1", "y"]
    asistente.deshacer()
    pd.testing.assert_frame_equal(con_datos.dataset.datos, datos)


def test_cargar_otro_dataset_olvida_deshacer_y_propuesta(con_datos, datos):
    llm = LLMFalsa(
        respuesta("1", op("eliminar_columna", "x2")),
        respuesta("2", op("eliminar_columna", "x1")),
    )
    asistente = Asistente(con_datos, llm)
    enviar(asistente)
    asistente.confirmar()
    enviar(asistente)
    con_datos.cargar_dataset(datos, "otro.csv")
    assert not asistente.puede_deshacer()
    assert asistente.propuesta is None
    with pytest.raises(ErrorAsistente):
        asistente.deshacer()
    with pytest.raises(ErrorAsistente):
        asistente.confirmar()


def test_cambio_imposible_no_deja_propuesta(con_datos):
    llm = LLMFalsa(respuesta("Fuera", op("eliminar_columna", "no_existe")))
    asistente = Asistente(con_datos, llm)
    with pytest.raises(ErrorAsistente, match="no se puede aplicar"):
        enviar(asistente)
    assert asistente.propuesta is None
    assert con_datos.dataset is not None


def test_cambios_sin_dataset(sesion):
    llm = LLMFalsa(respuesta("Fuera", op("eliminar_duplicados")))
    with pytest.raises(ErrorAsistente, match="no hay ningún dataset"):
        enviar(Asistente(sesion, llm))


def test_error_de_la_llm_deja_la_pregunta(sesion):
    asistente = Asistente(sesion, LLMFalsa(ErrorAsistente("sin red")))
    with pytest.raises(ErrorAsistente, match="sin red"):
        enviar(asistente, "hola")
    assert [m.texto for m in asistente.mensajes] == ["hola"]


def test_descartar_y_borrar(con_datos):
    llm = LLMFalsa(respuesta("x", op("eliminar_duplicados")))
    asistente = Asistente(con_datos, llm)
    enviar(asistente)
    asistente.descartar()
    assert asistente.propuesta is None
    asistente.borrar_conversacion()
    assert asistente.mensajes == ()


def test_contexto_con_modelo(sesion_separada):
    sesion_separada.aplicar_preprocesado("eliminar")
    sesion_separada.crear_modelo()
    llm = LLMFalsa(respuesta())
    enviar(Asistente(sesion_separada, llm))
    _, contexto = llm.llamadas[0]
    assert "Modelo: y = " in contexto
    assert "R²" in contexto
