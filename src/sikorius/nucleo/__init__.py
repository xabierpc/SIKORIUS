"""SIKORIUS: modelos de regresión lineal con interfaz gráfica."""

from importlib.metadata import PackageNotFoundError, version

# La versión se define solo en pyproject.toml; aquí se lee de los metadatos
# del paquete instalado para no tener que mantenerla en dos sitios.
try:
    __version__ = version("sikorius")
except PackageNotFoundError:
    # El código se está ejecutando sin instalar el paquete (p. ej. desde una
    # copia de src/ sin pasar por uv).
    __version__ = "0.0.0"
