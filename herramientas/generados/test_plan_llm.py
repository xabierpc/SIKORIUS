"""Pruebas funcionales del plan generadas por un LLM.

Generado por: openai/gpt-oss-120b (razonamiento low)
Fecha: 2026-11-25 17:51
Commit de la aplicación: ddb4723

Cada test es un caso del plan de pruebas (docs/plan_pruebas.md) con las
acciones que hizo el LLM y las comprobaciones de las evidencias que citó.
Se ejecuta sin LLM:

    uv run --group probador pytest herramientas/generados -v

Los tests van en orden y son aditivos: cada uno parte de lo que dejó el
anterior. Ejecútalos todos juntos y en este orden.

No edites este archivo a mano: se vuelve a generar con
herramientas/generar_script.py.
"""

import pytest


# Casos sin test (manuales, sin ejecutar, bloqueados o con error):
# CP-01 (No ejecutado), CP-02 (No ejecutado), CP-03 (No ejecutado), CP-04 (No ejecutado), CP-05 (No ejecutado), CP-06 (No ejecutado)


def test_sin_casos():
    pytest.skip("La ejecución no tiene casos generables")
