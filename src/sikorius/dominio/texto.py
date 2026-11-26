"""Utilidades para mostrar números como texto."""


def formatear_numero(numero, decimales=None):
    """Escribe un número sin decimales innecesarios.

    20.0 -> "20", 12.5 -> "12.5"; con decimales=2, 87.456 -> "87.46".

    Args:
        numero: Número a escribir (cualquier valor que acepte ``float``).
        decimales: Si no es None, se redondea a ese número de decimales.

    Returns:
        El número como texto.

    Raises:
        ValueError, TypeError: Si ``numero`` no se puede convertir en
            float.
    """
    numero = float(numero)
    if decimales is not None:
        numero = round(numero, decimales)
    if numero.is_integer():
        return str(int(numero))
    return str(numero)
