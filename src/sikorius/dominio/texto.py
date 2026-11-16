"""Utilidades para mostrar números como texto."""


def formatear_numero(numero, decimales=None):
    """20.0 -> "20", 12.5 -> "12.5"; con decimales=2, 87.456 -> "87.46"."""
    numero = float(numero)
    if decimales is not None:
        numero = round(numero, decimales)
    if numero.is_integer():
        return str(int(numero))
    return str(numero)
