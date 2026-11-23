# PanaStatus

Monitor público de disponibilidad de servicios web de Panamá: bancos, gobierno, universidades y servicios globales.

- **Checker** cada 1–5 min: código HTTP, latencia y días de vigencia del certificado SSL.
- **Incidentes**: se abren con 2 fallas seguidas y se cierran al recuperarse, con duración.
- **Bot de Telegram** con suscripciones por servicio (también en grupos).
- **API** de solo lectura (`/api/docs`) y **página pública de estado** (`/`).

## Arquitectura

```
config/services.yaml ──► worker ──► PostgreSQL + TimescaleDB ◄── api (FastAPI) ◄── página web
                           │                    ▲
                           └──► Telegram ◄──────┴────────── bot (comandos)
```

| Módulo | Responsabilidad |
|---|---|
| `checker.py` | Una revisión HTTP → `CheckResult` (sin DB ni alertas) |
| `state.py` | Máquina de estados pura: caída / recuperación / lentitud |
| `worker.py` | Bucle por servicio: revisar → guardar → evaluar → notificar |
| `notifier.py` | Envío de avisos a Telegram (admin + suscriptores) |
| `db.py` | Todo el SQL |
| `api.py` | API REST + página estática |
| `bot.py` | Comandos del bot |

## Correr en local

Necesitas Docker y [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env        # y completa los valores
docker compose up -d --build
docker compose logs -f worker
```

- Página: http://localhost:8000
- API: http://localhost:8000/api/docs

Desarrollo sin Docker (solo con la DB en Docker):

```bash
uv sync
docker compose up -d db
uv run python -m panastatus.worker --once   # revisa todo una vez, sin DB
uv run pytest
```

## Monitoreo responsable

Solo revisamos páginas públicas, sin login, y como máximo una petición cada 1 a 5 minutos por servicio (el código lo valida). No descargamos el cuerpo de la página: el certificado SSL se lee de la misma conexión, sin peticiones extra.

Cada petición se identifica con la convención de los bots profesionales:

```
PanaStatusBot/0.1 (+https://<dominio>/bot.html; panastatus.contacto@gmail.com)
```

La página [`/bot.html`](web/bot.html) explica a los administradores de los sitios qué hace el bot, cuánto tráfico genera y cómo pedir la exclusión. Las exclusiones se atienden en un máximo de 48 horas: se marca `enabled: false` en `config/services.yaml` con un comentario que indica la fecha y el motivo.
