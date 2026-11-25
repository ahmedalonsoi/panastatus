# Guía de contribución

## Requisitos

| Herramienta | Versión | Para qué |
|---|---|---|
| Docker + Docker Compose | reciente | Levantar todo el sistema |
| [uv](https://docs.astral.sh/uv/) | 0.13+ | Python 3.12 y dependencias del backend |
| Node.js | 24 LTS (trae npm 11) | Frontend |

## Puesta en marcha

```bash
cp .env.example .env          # complétalo (ver comentarios del archivo)
docker compose up -d --build  # todo el sistema: http://localhost:8080
uv sync                       # entorno de Python para pruebas y herramientas
uv tool install pre-commit && pre-commit install   # revisiones antes de cada commit
```

Frontend con recarga en vivo (la API en Docker o con `uv run uvicorn panastatus.api:app`):

```bash
cd frontend && npm ci && npm run dev   # http://localhost:3000
```

## Comandos

| Qué | Comando |
|---|---|
| Pruebas unitarias + cobertura | `uv run pytest -m "not integration" --cov` |
| Pruebas de integración (DB real) | ver abajo |
| Estilo y errores | `uv run ruff check . && uv run ruff format .` |
| Tipos | `uv run mypy` |
| Frontend | `cd frontend && npm run lint && npm run typecheck && npm test && npm run build` |
| Revisar todos los servicios una vez | `uv run python -m panastatus.worker --once` |
| Todo lo de pre-commit | `pre-commit run --all-files` |

### Pruebas de integración

Necesitan una base **vacía y desechable** (cada prueba borra las tablas):

```bash
docker compose exec db psql -U panastatus -c "CREATE DATABASE panastatus_test"
docker compose run --rm -e PGDATABASE=panastatus_test migrate
TEST_DATABASE_URL=postgresql://<usuario>:<clave>@localhost:5432/panastatus_test \
  uv run pytest -m integration
```

## Flujo de trabajo

1. **Una rama por cambio**: `feat/...`, `fix/...`, `docs/...`, `chore/...`.
2. **Commits convencionales en español**: `feat(bot): comando /silencio`,
   `fix(worker): cerrar incidentes al pausar`. El cuerpo explica el *por qué*.
3. Antes del commit: pruebas, lint y tipos en verde (pre-commit lo hace por ti).
4. Pull request con la plantilla completa. CI debe pasar: Python, integración,
   frontend, infraestructura y secretos.
5. Merge con `--no-ff` para conservar la historia de cada rama.

## Convenciones

- **SQL** solo en `src/panastatus/db.py`, siempre con parámetros.
- **Lógica de negocio pura** (sin red ni DB) donde se pueda, como `state.py`: se prueba
  fácil y sin mocks.
- **Esquema de la base**: nueva migración `db/migrations/00N_descripcion.sql`.
  **Nunca** edites una migración ya aplicada.
- **Versiones fijas**: imágenes por etiqueta exacta, acciones por SHA, npm con
  `save-exact`.
- **Decisiones importantes**: un ADR nuevo en `docs/adr/`.
- **Comentarios** que expliquen el *por qué*, no el *qué*.

## Agregar un servicio

1. Verifica que la URL sea **pública** y responda con una sola petición `GET`.
2. Agrégalo a `config/services.yaml` (el `id` no se cambia después: es la llave en la
   base y en las suscripciones).
3. `uv run python -m panastatus.worker --once` para comprobar que responde bien.
4. Respeta las [reglas de monitoreo responsable](docs/adr/0009-monitoreo-responsable.md).
