# ADR-0003: SQL explícito con asyncpg, sin ORM

- **Estado:** Aceptado
- **Fecha:** 2026-11

## Contexto

Las consultas importantes del proyecto usan funciones de TimescaleDB (`time_bucket`,
agregados continuos), `LATERAL JOIN`, `FILTER`, `ON CONFLICT` con índices parciales y
arreglos (`TEXT[]` con índice GIN). Todo el código es asíncrono (asyncio).

## Decisión

- Driver **asyncpg**, el más rápido para PostgreSQL en Python asíncrono.
- **Todo el SQL vive en `db.py`**: el resto del código llama funciones con nombre
  (`open_incident`, `toggle_subscription`...) y nunca arma SQL.
- Siempre parámetros (`$1`, `$2`), nunca concatenación: imposible la inyección SQL.
- Operaciones concurrentes resueltas **en una sola sentencia atómica** (por ejemplo,
  alternar una suscripción) o con `SELECT ... FOR UPDATE` dentro de una transacción.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| SQLAlchemy ORM | Las consultas clave igual habría que escribirlas en SQL; agrega una capa que esconde lo que de verdad se ejecuta. |
| SQLModel / Tortoise | Mismo problema y menos maduros para TimescaleDB. |

## Consecuencias

- El SQL es legible y se puede copiar a `psql` para depurar.
- asyncpg no publica tipos: mypy trata sus objetos como `Any` (ver `pyproject.toml`).
  Se compensa con pruebas de integración contra una base real (`tests/integration/`).
