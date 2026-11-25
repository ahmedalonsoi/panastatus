# PanaStatus

Monitor público de disponibilidad de servicios web de Panamá (bancos, gobierno, UTP, servicios globales).
Proyecto de portafolio para un puesto de Analista de Soluciones (Soporte de Aplicaciones, Observabilidad y Confiabilidad).
Yo (Ahmed) debo entender cada pieza: explica las decisiones importantes y deja el código claro y comentado.

## Qué hace
- Checker: revisa cada servicio cada 1–5 min (HTTP, latencia, vigencia SSL). Caída confirmada = 2 fallas seguidas.
- Incidentes: se abren al confirmar caída, se cierran al recuperarse, con duración.
- Bot de Telegram público: /start, /servicios (suscribirse con botones), /estado [servicio], /missuscripciones, /silencio, /stop. Avisos de caída, recuperación y lentitud. Funciona en grupos.
- Página pública de estado: banner general, servicios por categoría, barra de 90 días, latencia 24 h, incidentes.
- API FastAPI solo lectura + /health, con límite de peticiones.
- Post-mortems: borrador con IA para incidentes > 15 min, revisado por el admin.

## Stack
Python 3.12 + uv, asyncio, httpx, Pydantic · FastAPI · python-telegram-bot · PostgreSQL + TimescaleDB ·
Front: Next.js + TypeScript + Tailwind (export estático servido por Caddy) · OpenTelemetry → Grafana Alloy → Prometheus + Loki → Grafana ·
Docker Compose + Caddy (HTTPS) · GitHub Actions + GHCR + Ruff + pytest · OpenTofu · Oracle Cloud Always Free (ARM) · Power BI para reportes · API de Claude (post-mortems).

## Tablas
services, checks (hypertable), incidents, postmortems, subscribers (solo chat_id y suscripciones).
Esquema `reporting` (vistas para Power BI, rol powerbi_reader). Cambios de esquema: nueva migración en db/migrations/ (nunca editar una aplicada).

## Reglas
- Monitoreo responsable: solo páginas públicas, sin login, 1 petición cada 1–5 min, User-Agent identificable con contacto.
- Secretos solo en .env (nunca en git) y GitHub Secrets.
- Servicios definidos en config/services.yaml.

## Plan
Fase 1 Base: checker + PostgreSQL/TimescaleDB + Docker Compose + alertas al admin.
Fase 2 Producto: bot con suscripciones, API, página pública.
Fase 3 Producción: nube con OpenTofu, CI/CD, HTTPS, observabilidad interna. → Lanzamiento público.
Fase 4 Análisis: post-mortems con IA, Power BI, README.

## Estado (2026-11-24)
Fases 1–4 implementadas en código. Decisión: **sin nube por ahora** (no hay acceso a la cuenta de Oracle). El proyecto se
presenta como local con Docker Compose + capturas en el README (docs/img/). El código de OpenTofu/despliegue se conserva
para retomarlo. Siguiente: repo en GitHub (sin desplegar; `DEPLOY_ENABLED` sin definir). Opcional: ANTHROPIC_API_KEY, .pbix.

## Convenciones de trabajo
- Una rama por cambio, commits convencionales en español (feat:, fix:, chore:...), merge --no-ff a main. Sin push sin permiso.
- Antes de commit: `uv run ruff check . && uv run ruff format . && uv run pytest` y, si se tocó frontend/, `npm run lint && npm run build`.
- Versiones fijadas (imágenes, acciones por SHA, npm save-exact).
