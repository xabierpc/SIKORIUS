"""Tests de la lectura del plan de pruebas del probador con LLM."""

from pathlib import Path

import pytest

from probador_llm.plan import (
    elegir_casos,
    leer_glosario,
    leer_plan,
    sustituir_glosario,
)

PLAN = """# Plan

### 1.2 Procedimientos comunes

**PR-1. Abrir la aplicación**

1. Ejecutar `uv run sikorius`.

### 1.3 Glosario de la interfaz

| Clave | Texto en la aplicación | Dónde |
|---|---|---|
| B_CREAR | Crear modelo | Pestaña "Modelo" |
| O_A / O_B | Opción A / Opción B | Opciones |
| EXT | `.json` | Extensión |
| minusculas | no es clave | - |

## 2. Datos de prueba

| D-1 (CSV) | `data/⟨dataset⟩.csv` |

## 3. Funcionalidades cubiertas

## 4. Casos de prueba

### 4.1 Grupo

#### CP-01. Primer caso
- **Precondiciones:** aplicación recién abierta (PR-1).
- **Pasos:**
  1. Pulsar **⟨B_CREAR⟩** y elegir **⟨O_B⟩**.
- **Resultado esperado:** se guarda `modelo⟨EXT⟩` con ⟨FILAS⟩ filas.

#### CP-02. Segundo caso
- **Precondiciones:** CP-01 ejecutado, sin cerrar la aplicación.
- **Resultado esperado:** nada.

### 4.2 Otro grupo

#### CP-03. Tercer caso
- **Precondiciones:** CP-02 ejecutado, sin cerrar la aplicación.

#### CP-04. Cuarto caso
- **Precondiciones:** aplicación recién abierta (PR-1). CP-01 ejecutado.
- **Pasos:** realizar los pasos 1 a 3 de CP-02.

---

## 5. Ejecución

Texto que no es de ningún caso.
"""


@pytest.fixture
def plan():
    return leer_plan(PLAN)


def test_glosario_lee_claves_simples_y_multiples():
    glosario = leer_glosario(PLAN)
    assert glosario["B_CREAR"] == "Crear modelo"
    assert glosario["O_A"] == "Opción A"
    assert glosario["O_B"] == "Opción B"


def test_glosario_quita_comillas_de_codigo():
    assert leer_glosario(PLAN)["EXT"] == ".json"


def test_glosario_ignora_cabecera_y_claves_no_validas():
    glosario = leer_glosario(PLAN)
    assert "Clave" not in glosario
    assert "minusculas" not in glosario


def test_glosario_vacio_si_no_hay_seccion():
    assert leer_glosario("# Plan sin glosario") == {}


def test_sustituir_glosario():
    texto = sustituir_glosario("Pulsar ⟨B_CREAR⟩", {"B_CREAR": "Crear"})
    assert texto == "Pulsar Crear"


def ids(casos):
    lista = []
    for caso in casos:
        lista.append(caso.id)
    return lista


def test_casos_en_orden(plan):
    assert list(plan.casos) == ["CP-01", "CP-02", "CP-03", "CP-04"]
    assert plan.casos["CP-01"].titulo == "Primer caso"


def test_texto_del_caso_con_glosario_sustituido(plan):
    texto = plan.casos["CP-01"].texto
    assert "Pulsar **Crear modelo** y elegir **Opción B**" in texto
    assert "modelo.json" in texto


def test_huecos_sin_rellenar(plan):
    assert plan.casos["CP-01"].huecos == ["FILAS"]
    assert plan.casos["CP-02"].huecos == []


def test_el_caso_no_incluye_titulos_de_seccion_ni_texto_posterior(plan):
    assert "4.2 Otro grupo" not in plan.casos["CP-02"].texto
    ultimo = plan.casos["CP-04"].texto
    assert "Ejecución" not in ultimo
    assert "Texto que no es" not in ultimo
    assert not ultimo.endswith("---")


def test_requisitos_y_misma_sesion(plan):
    assert plan.casos["CP-02"].requisitos == ["CP-01"]
    assert plan.casos["CP-02"].misma_sesion
    assert plan.casos["CP-04"].requisitos == ["CP-01"]
    assert not plan.casos["CP-04"].misma_sesion


def test_preparacion_encadenada(plan):
    preparacion = plan.preparacion(plan.casos["CP-03"])
    assert ids(preparacion) == ["CP-01", "CP-02"]


def test_preparacion_vacia_si_empieza_con_la_app_recien_abierta(plan):
    assert plan.preparacion(plan.casos["CP-04"]) == []


def test_casos_citados(plan):
    assert plan.casos["CP-04"].citados == ["CP-01", "CP-02"]
    assert plan.casos["CP-01"].citados == []


def test_referencias_excluyen_la_preparacion(plan):
    assert ids(plan.referencias(plan.casos["CP-04"])) == ["CP-01", "CP-02"]
    # CP-03 repite CP-01 y CP-02 como preparación: no son referencias
    assert plan.referencias(plan.casos["CP-03"]) == []


def test_contexto_compacto(plan):
    # PR-1 (abrir la aplicación) lo hace el probador
    assert "PR-1" not in plan.contexto
    # El glosario pasa a lista "texto: dónde", sin las claves
    assert "- Crear modelo: Pestaña" in plan.contexto
    assert "B_CREAR" not in plan.contexto
    assert "|" not in plan.contexto
    assert "Datos de prueba" in plan.contexto
    assert "CP-01" not in plan.contexto


def test_plan_sin_casos():
    with pytest.raises(ValueError):
        leer_plan("# Plan vacío")


@pytest.mark.parametrize(
    ("seleccion", "esperados"),
    [
        ("", ["CP-01", "CP-02", "CP-03", "CP-04"]),
        ("CP-03,cp-01", ["CP-01", "CP-03"]),
        ("CP-02:CP-03", ["CP-02", "CP-03"]),
        ("2:3, 4", ["CP-02", "CP-03", "CP-04"]),
    ],
)
def test_elegir_casos(plan, seleccion, esperados):
    elegidos = elegir_casos(plan, seleccion)
    assert ids(elegidos) == esperados


@pytest.mark.parametrize("seleccion", ["CP-09", "CP-01:CP-07", "abc"])
def test_elegir_casos_no_validos(plan, seleccion):
    with pytest.raises(ValueError):
        elegir_casos(plan, seleccion)


def test_el_plan_del_proyecto_se_lee():
    """El plan real tiene sus 93 casos y todos tienen resultado esperado."""
    ruta = Path(__file__).parents[2] / "docs" / "plan_pruebas.md"
    if not ruta.exists():
        pytest.skip("No hay docs/plan_pruebas.md")
    plan = leer_plan(ruta.read_text(encoding="utf-8"))
    assert len(plan.casos) == 93
    for caso in plan.casos.values():
        assert "**Resultado esperado:**" in caso.texto, caso.id
        # Las claves del glosario ya están sustituidas
        assert "⟨B_" not in caso.texto, caso.id
    # Los datos de la sección 2.1 ya están rellenados
    for caso in plan.casos.values():
        assert caso.huecos == [], caso.id


PLAN_ADITIVO = """
#### CP-01. Carga inicial
- **Precondiciones:** aplicación recién abierta (PR-1).

#### CP-02. Usa lo cargado
- **Precondiciones:** D-1 cargado.

#### CP-03. Continúa a CP-05
- **Precondiciones:** CP-05 ejecutado, sin cerrar la aplicación.

#### CP-04. Otro independiente
- **Precondiciones:** aplicación abierta, en el estado que dejó el anterior.

#### CP-05. Padre de CP-03
- **Precondiciones:** D-1 cargado.

#### CP-06. Continúa a CP-03
- **Precondiciones:** CP-03 ejecutado, sin cerrar la aplicación.
"""


def test_reinicio_solo_si_pide_la_aplicacion_recien_abierta():
    plan = leer_plan(PLAN_ADITIVO)
    assert plan.casos["CP-01"].reinicio
    assert not plan.casos["CP-02"].reinicio
    assert not plan.casos["CP-03"].reinicio
    assert not plan.casos["CP-04"].reinicio


def test_padre():
    plan = leer_plan(PLAN_ADITIVO)
    assert plan.padre(plan.casos["CP-03"]).id == "CP-05"
    assert plan.padre(plan.casos["CP-02"]) is None


def test_orden_encadena_cada_caso_tras_su_padre():
    plan = leer_plan(PLAN_ADITIVO)
    orden = plan.orden(list(plan.casos.values()))
    assert ids(orden) == ["CP-01", "CP-02", "CP-04", "CP-05", "CP-03", "CP-06"]


def test_orden_sin_el_padre_respeta_el_plan():
    plan = leer_plan(PLAN_ADITIVO)
    elegidos = [plan.casos["CP-03"], plan.casos["CP-04"]]
    assert ids(plan.orden(elegidos)) == ["CP-03", "CP-04"]


def test_orden_del_plan_del_proyecto():
    """Todos los casos salen una vez y cada cadena va seguida."""
    ruta = Path(__file__).parents[2] / "docs" / "plan_pruebas.md"
    if not ruta.exists():
        pytest.skip("No hay docs/plan_pruebas.md")
    plan = leer_plan(ruta.read_text(encoding="utf-8"))
    orden = ids(plan.orden(list(plan.casos.values())))
    assert sorted(orden) == sorted(plan.casos)
    assert orden[0] == "CP-01"
    for caso in plan.casos.values():
        padre = plan.padre(caso)
        if padre is not None:
            assert orden.index(caso.id) > orden.index(padre.id), caso.id
