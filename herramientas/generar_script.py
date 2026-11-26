"""Genera el script de Playwright desde una ejecución anterior con el LLM.

No llama al LLM: lee el ``resultados.json`` de la ejecución y escribe
``herramientas/generados/test_plan_llm.py``. Sin argumentos, usa la última
ejecución de ``data/pruebas_llm/``.

Uso, desde la raíz del repositorio:

    uv run python herramientas/generar_script.py
    uv run python herramientas/generar_script.py \
        data/pruebas_llm/<fecha>/resultados.json
"""

import sys
from pathlib import Path

from probador_llm.ejecutor import RAIZ, SCRIPT_GENERADO
from probador_llm.generador import generar_desde_json


def ultima_ejecucion():
    carpeta = RAIZ / "data" / "pruebas_llm"
    candidatas = sorted(carpeta.glob("*/resultados.json"))
    if not candidatas:
        return None
    return candidatas[-1]


def main(argumentos):
    if argumentos:
        ruta = Path(argumentos[0])
    else:
        ruta = ultima_ejecucion()
        if ruta is None:
            print("No hay ejecuciones en data/pruebas_llm/", file=sys.stderr)
            return 1
    codigo = generar_desde_json(ruta.read_text(encoding="utf-8"))
    SCRIPT_GENERADO.parent.mkdir(parents=True, exist_ok=True)
    SCRIPT_GENERADO.write_text(codigo, encoding="utf-8")
    print("Generado desde " + str(ruta))
    print("Script: " + str(SCRIPT_GENERADO.relative_to(RAIZ)))
    print(
        "Para ejecutarlo: uv run --group probador pytest "
        "herramientas/generados -v"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
