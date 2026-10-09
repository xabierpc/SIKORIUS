# Práctica de Git

Cada miembro del grupo debe completar estos ejercicios al menos una vez. Material de apoyo: [GitHub Skills](https://skills.github.com/), [Pro Git (en español)](https://git-scm.com/book/es/v2) y la [documentación de uv](https://docs.astral.sh/uv/).

## 0. Preparar el entorno

```bash
git clone https://github.com/xabierpc/SIKORIUS.git
cd SIKORIUS
git switch dev
uv sync
uv run sikorius     # debe mostrar un saludo
```

## 1. Rama feature completa

1. Crea una rama desde `dev`: `git switch -c feature/0-presentacion-<tu-nombre>`.
2. Añade tu nombre a la tabla de [integrantes](#integrantes) y haz commit.
3. Súbela: `git push -u origin feature/0-presentacion-<tu-nombre>`.
4. Actualízala con `dev` (`git merge dev`), fusiónala en `dev` y elimínala, tal como indica [CONTRIBUTING.md](../CONTRIBUTING.md#3-flujo-de-trabajo).

## 2. Conflicto de fusión (por parejas)

1. Ambos crean una rama desde el mismo `dev`, por ejemplo `docs/conflicto-ana` y `docs/conflicto-luis`.
2. Los dos modifican **la misma línea** de este archivo: la frase de prueba de abajo.
3. El primero fusiona su rama en `dev` y hace `git push`.
4. El segundo actualiza su rama con `dev` (`git merge dev`): Git avisará del conflicto.
5. Resuélvelo (elige o combina las dos frases y borra las marcas `<<<<<<<`, `=======`, `>>>>>>>`), haz `git add` y `git commit`, y fusiona en `dev`.

Frase de prueba: Esta línea se usa para practicar conflictos de fusión.

## Integrantes

| Nombre | Rama feature hecha | Conflicto resuelto |
|--------|:------------------:|:------------------:|
|        |                    |                    |
