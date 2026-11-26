"""Ejecuta el plan de pruebas funcionales con un LLM.

Uso, desde la raíz del repositorio:

    uv run --group probador python herramientas/probar_con_llm.py
    uv run --group probador python herramientas/probar_con_llm.py --casos CP-47
    uv run --group probador python herramientas/probar_con_llm.py --help

Al ejecutar este archivo, su carpeta (herramientas/) queda en sys.path, así
que el paquete probador_llm se importa sin instalarlo.
"""

import sys

from probador_llm.ejecutor import main

if __name__ == "__main__":
    sys.exit(main())
